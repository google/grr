#!/usr/bin/env python
"""Client repacking library."""

import getpass
import logging
import os
import platform
import sys
import zipfile

from grr import config
from grr.lib import build
from grr.lib import config_lib
from grr.lib.builders import signing


class RepackConfig(object):

  def Validate(self, config_data, template_path):
    if set(config_data.keys()) != build.ClientBuilder.REQUIRED_BUILD_YAML_KEYS:
      raise RuntimeError("Bad build.yaml from %s: expected %s, got %s" %
                         (template_path,
                          build.ClientBuilder.REQUIRED_BUILD_YAML_KEYS,
                          config_data.keys()))

  def GetConfigFromTemplate(self, template_path):
    """Apply build.yaml settings from the template."""
    with zipfile.ZipFile(template_path) as template_zip:
      build_yaml = None
      for name in template_zip.namelist():
        if name.endswith("build.yaml"):
          build_yaml = name
          break
      if not build_yaml:
        raise RuntimeError("Couldn't find build.yaml in %s" % template_path)
      with template_zip.open(build_yaml) as buildfile:
        repack_config = config.CONFIG.CopyConfig()
        parser = config_lib.YamlParser(fd=buildfile)
        config_data = parser.RawData()
        self.Validate(config_data, template_path)
        repack_config.MergeData(config_data)
    return repack_config


class TemplateRepacker(object):
  """Repacks client templates into OS installers."""

  def GetRepacker(self, context, signer=None):
    """Get the appropriate client deployer based on the selected flags."""
    if "Target:Darwin" in context:
      deployer_class = build.DarwinClientRepacker
    elif "Target:Windows" in context:
      deployer_class = build.WindowsClientRepacker
    elif "Target:LinuxDeb" in context:
      deployer_class = build.LinuxClientRepacker
    elif "Target:LinuxRpm" in context:
      deployer_class = build.CentosClientRepacker
    else:
      raise RuntimeError("Bad build context: %s" % context)

    return deployer_class(context=context, signer=signer)

  def GetSigningPassword(self):
    if sys.stdin.isatty():
      print "Enter passphrase for code signing:"
      return getpass.getpass()
    else:
      passwd = sys.stdin.readline().strip()
      if not passwd:
        raise RuntimeError("Expected signing password on stdin, got nothing.")
      return passwd

  def GetSigner(self, context):
    if "Target:Windows" not in context and "Target:LinuxRpm" not in context:
      raise RuntimeError(
          "Signing only supported on windows and linux rpms. Neither target in"
          " context: %s" % context)

    if "Target:Windows" in context:
      system = platform.system()
      if system == "Linux":
        cert = config.CONFIG.Get(
            "ClientBuilder.windows_signing_cert", context=context)
        key = config.CONFIG.Get(
            "ClientBuilder.windows_signing_key", context=context)
        app_name = config.CONFIG.Get(
            "ClientBuilder.windows_signing_application_name", context=context)
        passwd = self.GetSigningPassword()
        return signing.WindowsOsslsigncodeCodeSigner(cert, key, passwd,
                                                     app_name)
      elif system == "Windows":
        signing_cmd = config.CONFIG.Get(
            "ClientBuilder.signtool_signing_cmd", context=context)
        verification_cmd = config.CONFIG.Get(
            "ClientBuilder.signtool_verification_cmd", context=context)
        return signing.WindowsSigntoolCodeSigner(signing_cmd, verification_cmd)
      else:
        raise RuntimeError("Signing not supported on platform: %s" % system)
    elif "Target:LinuxRpm" in context:
      pub_keyfile = config.CONFIG.Get(
          "ClientBuilder.rpm_signing_key_public_keyfile", context=context)
      gpg_name = config.CONFIG.Get(
          "ClientBuilder.rpm_gpg_name", context=context)
      passwd = self.GetSigningPassword()
      return signing.RPMCodeSigner(passwd, pub_keyfile, gpg_name)

  def SignTemplate(self, template_path, output_file, context=None):
    if not template_path.endswith(".exe.zip"):
      raise RuntimeError(
          "Signing templates is only worthwhile for windows, rpms are signed "
          "at the package level and signing isn't supported for others.")
    context.append("Target:Windows")
    signer = self.GetSigner(context)
    z_in = zipfile.ZipFile(open(template_path, "rb"))
    with zipfile.ZipFile(
        output_file, mode="w", compression=zipfile.ZIP_DEFLATED) as z_out:
      build.CreateNewZipWithSignedLibs(
          z_in, z_out, skip_signing_files=[], signer=signer)

  def RepackTemplate(self,
                     template_path,
                     output_dir,
                     upload=False,
                     token=None,
                     sign=False,
                     context=None,
                     signed_template=False):
    """Repack binaries based on the configuration.

    We repack all templates in the templates directory. We expect to find only
    functioning templates, all other files should be removed. Each template
    contains a build.yaml that specifies how it was built and how it should be
    repacked.

    Args:
      template_path: template path string
      output_dir: Output files will be put in this directory.
      upload: If specified we also upload the repacked binary into the
      token: Token to use when uploading to the datastore.
      sign: If true, we want to digitally sign the installer.
      context: Array of context strings
      signed_template: If true, the libraries in the template are already
      signed. This is only used for windows when repacking the template multiple
      times.

    Returns:
      A list of output installers generated.
    """
    orig_config = config.CONFIG
    repack_config = RepackConfig()
    print "Repacking template: %s" % template_path
    config.CONFIG = repack_config.GetConfigFromTemplate(template_path)

    result_path = None
    try:
      repack_context = config.CONFIG["Template.build_context"]
      if context:
        repack_context.extend(context)

      output_path = os.path.join(output_dir,
                                 config.CONFIG.Get(
                                     "ClientRepacker.output_filename",
                                     context=repack_context))

      print "Using context: %s and labels: %s" % (
          repack_context,
          config.CONFIG.Get("Client.labels", context=repack_context))
      try:
        signer = None
        if sign:
          signer = self.GetSigner(repack_context)
        builder_obj = self.GetRepacker(context=repack_context, signer=signer)
        builder_obj.signed_template = signed_template
        result_path = builder_obj.MakeDeployableBinary(template_path,
                                                       output_path)
      except Exception:  # pylint: disable=broad-except
        logging.exception("Repacking template %s failed:", template_path)

      if result_path:
        print "Repacked into %s" % result_path
        if upload:
          # We delay import here so we don't have to import the entire server
          # codebase and do full server init if we're just building and
          # repacking clients. This codepath is used by config_updater
          # initialize
          # pylint: disable=g-import-not-at-top
          from grr.server.grr_response_server import maintenance_utils
          # pylint: enable=g-import-not-at-top
          dest = config.CONFIG.Get(
              "Executables.installer", context=repack_context)
          maintenance_utils.UploadSignedConfigBlob(
              open(result_path, "rb").read(100 * 1024 * 1024),
              dest,
              client_context=repack_context,
              token=token)
      else:
        print "Failed to repack %s." % template_path
    finally:
      config.CONFIG = orig_config

    return result_path

  def RepackAllTemplates(self, upload=False, token=None):
    """Repack all the templates in ClientBuilder.template_dir."""
    for template in os.listdir(config.CONFIG["ClientBuilder.template_dir"]):
      template_path = os.path.join(config.CONFIG["ClientBuilder.template_dir"],
                                   template)

      self.RepackTemplate(
          template_path,
          os.path.join(config.CONFIG["ClientBuilder.executables_dir"],
                       "installers"),
          upload=upload,
          token=token)
      # If it's windows also repack a debug version.
      if template_path.endswith(".exe.zip"):
        print "Repacking as debug installer: %s." % template_path
        self.RepackTemplate(
            template_path,
            os.path.join(config.CONFIG["ClientBuilder.executables_dir"],
                         "installers"),
            upload=upload,
            token=token,
            context=["DebugClientBuild Context"])
