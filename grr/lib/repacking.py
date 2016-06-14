#!/usr/bin/env python
"""Client repacking library."""

import os
import zipfile

from grr.lib import build
from grr.lib import config_lib


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
        repack_config = config_lib.CONFIG.CopyConfig()
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

  def RepackTemplate(self,
                     template,
                     output_dir,
                     upload=False,
                     token=None,
                     signer=None,
                     context=None):
    """Repack binaries based on the configuration.

    We repack all templates in the templates directory. We expect to find only
    functioning templates, all other files should be removed. Each template
    contains a build.yaml that specifies how it was built and how it should be
    repacked.

    Args:
      template: ltemplate path string
      output_dir: Output files will be put in this directory.
      upload: If specified we also upload the repacked binary into the
      token: Token to use when uploading to the datastore.
      signer: Signer object
      context: Array of context strings

    Returns:
      A list of output installers generated.
    """
    orig_config = config_lib.CONFIG
    repack_config = RepackConfig()
    template_path = os.path.join(
        config_lib.CONFIG["ClientBuilder.template_dir"], template)
    print "Repacking template: %s" % template_path
    config_lib.CONFIG = repack_config.GetConfigFromTemplate(template_path)

    result_path = None
    try:
      repack_context = config_lib.CONFIG["Template.build_context"]
      if context:
        repack_context.extend(context)
      output_path = os.path.join(output_dir,
                                 config_lib.CONFIG.Get(
                                     "ClientRepacker.output_filename",
                                     context=repack_context))

      try:
        builder_obj = self.GetRepacker(context=repack_context, signer=signer)
        result_path = builder_obj.MakeDeployableBinary(template_path,
                                                       output_path)
      except Exception as e:  # pylint: disable=broad-except
        print "Repacking template %s failed: %s" % (template_path, e)

      if result_path:
        print "Repacked into %s" % result_path
        if upload:
          # We delay import here so we don't have to import the entire server
          # codebase and do full server init if we're just building and
          # repacking clients. This codepath is used by config_updater
          # initialize
          # pylint: disable=g-import-not-at-top
          from grr.lib import maintenance_utils
          # pylint: enable=g-import-not-at-top
          dest = config_lib.CONFIG.Get("Executables.installer",
                                       context=repack_context)
          maintenance_utils.UploadSignedConfigBlob(
              open(result_path).read(100 * 1024 * 1024),
              dest,
              client_context=repack_context,
              token=token)
      else:
        print "Failed to repack %s." % template_path
    finally:
      config_lib.CONFIG = orig_config

    return result_path

  def RepackAllTemplates(self, upload=False, token=None):
    """Repack all the templates in ClientBuilder.template_dir."""
    for template in os.listdir(config_lib.CONFIG["ClientBuilder.template_dir"]):
      self.RepackTemplate(
          template,
          os.path.join(config_lib.CONFIG["ClientBuilder.executables_dir"],
                       "installers"),
          upload=upload,
          token=token)
      # If it's windows also repack a debug version.
      if template.endswith(".exe.zip"):
        print "Repacking as debug installer: %s." % template
        self.RepackTemplate(
            template,
            os.path.join(config_lib.CONFIG["ClientBuilder.executables_dir"],
                         "installers"),
            upload=upload,
            token=token,
            context=["DebugClientBuild Context"])
