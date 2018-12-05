#!/usr/bin/env python
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import logging
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile


from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues
import yaml

# pylint: disable=g-import-not-at-top,unused-import
# This is a workaround so we don't need to maintain the whole PyInstaller
# codebase as a full-fledged dependency.
try:
  # pytype: disable=import-error
  from PyInstaller import __main__ as PyInstallerMain
  # pytype: enable=import-error
except ImportError:
  # We ignore this failure since most people running the code don't build their
  # own clients and printing an error message causes confusion.  Those building
  # their own clients will need PyInstaller installed.
  pass

from google.protobuf import descriptor_pool
from google.protobuf import text_format

from fleetspeak.src.client.daemonservice.proto.fleetspeak_daemonservice import config_pb2 as fs_config_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2

from grr_response_core import config
from grr_response_core import version
from grr_response_core.config import contexts
from grr_response_core.lib import config_lib
from grr_response_core.lib import config_validator_base
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
# Pull in local config validators.
from grr_response_core.lib.local import plugins
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto

# pylint: enable=g-import-not-at-top,unused-import


class BuildError(Exception):
  pass


class BuilderBase(object):
  """A base class for builder / repacker that provides utility functions."""

  def __init__(self, context=None):
    self.context = context or config.CONFIG.context[:]
    self.context = [contexts.CLIENT_BUILD_CONTEXT] + self.context

  def GenerateDirectory(self,
                        input_dir=None,
                        output_dir=None,
                        replacements=None):
    input_dir = utils.NormalizePath(input_dir)
    output_dir = utils.NormalizePath(output_dir)
    replacements = replacements or []

    for (root, _, files) in os.walk(input_dir):
      for filename in files:
        in_file = utils.JoinPath(root, filename)
        out_file = in_file.replace(input_dir, output_dir)
        for (s, replacement) in replacements:
          out_file = out_file.replace(s, replacement)
        utils.EnsureDirExists(os.path.dirname(out_file))
        self.GenerateFile(in_file, out_file)

  def GenerateFile(self, input_filename=None, output_filename=None):
    """Generates a file from a template, interpolating config values."""
    if input_filename is None:
      input_filename = output_filename + ".in"
    if output_filename[-3:] == ".in":
      output_filename = output_filename[:-3]
    logging.debug("Generating file %s from %s", output_filename, input_filename)

    with io.open(input_filename, "r") as fd:
      data = fd.read()

    with io.open(output_filename, "w") as fd:
      fd.write(config.CONFIG.InterpolateValue(data, context=self.context))


class ClientBuilder(BuilderBase):
  """A client builder is responsible for building the binary template.

  This is an abstract client builder class, used by the OS specific
  implementations. Note that client builders typically run on the target
  operating system.
  """
  REQUIRED_BUILD_YAML_KEYS = set([
      "Client.build_environment", "Client.build_time", "Template.build_type",
      "Template.build_context", "Template.version_major",
      "Template.version_minor", "Template.version_revision",
      "Template.version_release", "Template.arch"
  ])

  def __init__(self, context=None):
    super(ClientBuilder, self).__init__(context=context)
    self.build_dir = ""

  def MakeBuildDirectory(self):
    """Prepares the build directory."""
    # Create the build directory and let pyinstaller loose on it.
    self.build_dir = config.CONFIG.Get(
        "PyInstaller.build_dir", context=self.context)
    self.work_path = config.CONFIG.Get(
        "PyInstaller.workpath_dir", context=self.context)

    self.CleanDirectory(self.build_dir)
    self.CleanDirectory(self.work_path)

  def CleanDirectory(self, directory):
    logging.info("Clearing directory %s", directory)
    try:
      shutil.rmtree(directory)
    except OSError:
      pass

    utils.EnsureDirExists(directory)

  def BuildWithPyInstaller(self):
    """Use pyinstaller to build a client package."""
    self.CleanDirectory(
        config.CONFIG.Get("PyInstaller.distpath", context=self.context))

    logging.info("Copying pyinstaller support files")
    self.spec_file = os.path.join(self.build_dir, "grr.spec")

    with open(self.spec_file, "wb") as fd:
      fd.write(config.CONFIG.Get("PyInstaller.spec", context=self.context))

    with open(os.path.join(self.build_dir, "version.txt"), "wb") as fd:
      fd.write(config.CONFIG.Get("PyInstaller.version", context=self.context))

    shutil.copy(
        src=config.CONFIG.Get("PyInstaller.icon_path", context=self.context),
        dst=os.path.join(self.build_dir, u"grr.ico"))

    # We expect the onedir output at this location.
    self.output_dir = os.path.join(
        config.CONFIG.Get("PyInstaller.distpath", context=self.context),
        "grr-client")

    # Pyinstaller doesn't handle unicode strings.
    args = [
        "--distpath",
        str(config.CONFIG.Get("PyInstaller.distpath", context=self.context)),
        "--workpath",
        str(
            config.CONFIG.Get("PyInstaller.workpath_dir",
                              context=self.context)),
        str(self.spec_file)
    ]
    logging.info("Running pyinstaller: %s", args)
    PyInstallerMain.run(pyi_args=[utils.SmartStr(x) for x in args])

    # Clear out some crud that pyinstaller includes.
    for path in ["tcl", "tk", "pytz"]:
      dir_path = os.path.join(self.output_dir, path)
      try:
        shutil.rmtree(dir_path)
      except OSError:
        logging.error("Unable to remove directory: %s", dir_path)

      try:
        os.mkdir(dir_path)
      except OSError:
        logging.error("Unable to create directory: %s", dir_path)

      file_path = os.path.join(dir_path, path)
      try:
        # Create an empty file so the directories get put in the installers.
        with open(file_path, "wb"):
          pass
      except IOError:
        logging.error("Unable to create file: %s", file_path)

    version_ini = version.VersionPath()
    shutil.copy(version_ini, os.path.join(self.output_dir, "version.ini"))

    with open(os.path.join(self.output_dir, "build.yaml"), "wb") as fd:
      self.WriteBuildYaml(fd)

  def WriteBuildYaml(self, fd, build_timestamp=True):
    """Write build spec to fd."""
    output = {
        "Client.build_environment":
            rdf_client.Uname.FromCurrentSystem().signature(),
        "Template.build_type":
            config.CONFIG.Get("ClientBuilder.build_type", context=self.context),
        "Template.version_major":
            config.CONFIG.Get("Source.version_major", context=self.context),
        "Template.version_minor":
            config.CONFIG.Get("Source.version_minor", context=self.context),
        "Template.version_revision":
            config.CONFIG.Get("Source.version_revision", context=self.context),
        "Template.version_release":
            config.CONFIG.Get("Source.version_release", context=self.context),
        "Template.arch":
            config.CONFIG.Get("Client.arch", context=self.context)
    }

    if build_timestamp:
      output["Client.build_time"] = rdfvalue.RDFDatetime.Now()
    else:
      self.REQUIRED_BUILD_YAML_KEYS.remove("Client.build_time")

    for key, value in iteritems(output):
      output[key] = str(value)

    output["Template.build_context"] = self.context

    output_keys = set(iterkeys(output))
    if output_keys != self.REQUIRED_BUILD_YAML_KEYS:
      raise RuntimeError("Bad build.yaml: expected %s, got %s" %
                         (self.REQUIRED_BUILD_YAML_KEYS, output_keys))
    fd.write(yaml.dump(output))

  def CopyMissingModules(self):
    """Copy any additional DLLs that cant be found."""

  def MakeExecutableTemplate(self, output_file=None):
    """Create the executable template.

    Args:
      output_file: string filename where we will write the template.

    The client is build in two phases. First an executable template is created
    with the client binaries contained inside a zip file. Then the installation
    package is created by appending the SFX extractor to this template and
    writing a config file into the zip file.

    This technique allows the client build to be carried out once on the
    supported platform (e.g. windows with MSVS), but the deployable installer
    can be build on any platform which supports python.

    Subclasses for each OS do the actual work, we just make sure the output
    directory is set up correctly here.
    """
    self.template_file = output_file or config.CONFIG.Get(
        "ClientBuilder.template_path", context=self.context)
    utils.EnsureDirExists(os.path.dirname(self.template_file))

  def MakeZip(self, input_dir, output_file):
    """Creates a ZIP archive of the files in the input directory.

    Args:
      input_dir: the name of the input directory.
      output_file: the name of the output ZIP archive without extension.
    """
    logging.info("Generating zip template file at %s", output_file)
    basename, _ = os.path.splitext(output_file)
    # TODO(user):pytype: incorrect make_archive() definition in typeshed.
    # pytype: disable=wrong-arg-types
    shutil.make_archive(
        basename, "zip", base_dir=".", root_dir=input_dir, verbose=True)
    # pytype: enable=wrong-arg-types


class ClientRepacker(BuilderBase):
  """Takes the binary template and producing an installer.

  Note that this should be runnable on all operating systems.
  """

  CONFIG_SECTIONS = [
      "CA", "Client", "ClientRepacker", "Logging", "Config", "Nanny",
      "Installer", "Template"
  ]

  # Config options that should never make it to a deployable binary.
  SKIP_OPTION_LIST = ["Client.private_key"]

  def __init__(self, context=None, signer=None):
    super(ClientRepacker, self).__init__(context=context)
    self.signer = signer
    self.signed_template = False

  def GetClientConfig(self, context, validate=True, deploy_timestamp=True):
    """Generates the client config file for inclusion in deployable binaries."""
    with utils.TempDirectory() as tmp_dir:
      # Make sure we write the file in yaml format.
      filename = os.path.join(
          tmp_dir,
          config.CONFIG.Get("ClientBuilder.config_filename", context=context))

      new_config = config.CONFIG.MakeNewConfig()
      new_config.Initialize(reset=True, data="")
      new_config.SetWriteBack(filename)

      # Only copy certain sections to the client. We enumerate all
      # defined options and then resolve those from the config in the
      # client's context. The result is the raw option as if the
      # client read our config file.
      client_context = context[:]
      while contexts.CLIENT_BUILD_CONTEXT in client_context:
        client_context.remove(contexts.CLIENT_BUILD_CONTEXT)
      for descriptor in sorted(config.CONFIG.type_infos, key=lambda x: x.name):
        if descriptor.name in self.SKIP_OPTION_LIST:
          continue

        if descriptor.section in self.CONFIG_SECTIONS:
          value = config.CONFIG.GetRaw(
              descriptor.name, context=client_context, default=None)

          if value is not None:
            logging.debug("Copying config option to client: %s",
                          descriptor.name)

            new_config.SetRaw(descriptor.name, value)

      if config.CONFIG.Get("ClientBuilder.fleetspeak_enabled", context=context):
        new_config.Set("Client.fleetspeak_enabled", True)

      if deploy_timestamp:
        deploy_time_string = unicode(rdfvalue.RDFDatetime.Now())
        new_config.Set("Client.deploy_time", deploy_time_string)
      new_config.Write()

      if validate:
        self.ValidateEndConfig(new_config)

      private_validator = config.CONFIG.Get(
          "ClientBuilder.private_config_validator_class", context=context)
      if private_validator:
        try:
          validator = config_validator_base.PrivateConfigValidator.classes[
              private_validator]()
        except KeyError:
          logging.error(
              "Couldn't find config validator class %s, "
              "you probably need to copy it into lib/local", private_validator)
          raise
        validator.ValidateEndConfig(new_config, self.context)

      return io.open(filename, "r").read()

  def ValidateEndConfig(self, config_obj, errors_fatal=True):
    """Given a generated client config, attempt to check for common errors."""
    errors = []

    if not config.CONFIG["ClientBuilder.fleetspeak_enabled"]:
      location = config_obj.Get("Client.server_urls", context=self.context)
      if not location:
        errors.append("Empty Client.server_urls")

      for url in location:
        if not url.startswith("http"):
          errors.append("Bad Client.server_urls specified %s" % url)

    key_data = config_obj.GetRaw(
        "Client.executable_signing_public_key",
        default=None,
        context=self.context)
    if key_data is None:
      errors.append("Missing Client.executable_signing_public_key.")
    elif not key_data.startswith("-----BEGIN PUBLIC"):
      errors.append(
          "Invalid Client.executable_signing_public_key: %s" % key_data)
    else:
      rsa_key = rdf_crypto.RSAPublicKey()
      rsa_key.ParseFromHumanReadable(key_data)
      logging.info(
          "Executable signing key successfully parsed from config (%d-bit)",
          rsa_key.KeyLen())

    if not config.CONFIG["ClientBuilder.fleetspeak_enabled"]:
      certificate = config_obj.GetRaw(
          "CA.certificate", default=None, context=self.context)
      if certificate is None or not certificate.startswith("-----BEGIN CERTIF"):
        errors.append("CA certificate missing from config.")

    for bad_opt in ["Client.private_key"]:
      if config_obj.Get(bad_opt, context=self.context, default=""):
        errors.append("Client cert in conf, this should be empty at deployment"
                      " %s" % bad_opt)

    if errors_fatal and errors:
      for error in errors:
        logging.error("Build Config Error: %s", error)
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def MakeDeployableBinary(self, template_path, output_path):
    """Use the template to create a customized installer."""


class WindowsClientRepacker(ClientRepacker):
  """Repackages windows installers."""

  def ValidateEndConfig(self, config_obj, errors_fatal=True):
    """Windows specific config validations."""
    errors = super(WindowsClientRepacker, self).ValidateEndConfig(
        config_obj, errors_fatal=errors_fatal)

    install_dir = config_obj["Client.install_path"]
    for path in config_obj["Client.tempdir_roots"]:
      if path.startswith("/"):
        errors.append(
            "Client.tempdir_root %s starts with /, probably has Unix path." %
            path)
      if not path.startswith(install_dir):
        errors.append(
            "Client.tempdir_root %s is not inside the install_dir %s, this is "
            "a security risk" % ((path, install_dir)))

    if config_obj.Get("Logging.path").startswith("/"):
      errors.append("Logging.path starts with /, probably has Unix path. %s" %
                    config_obj["Logging.path"])

    if "Windows\\" in config_obj.GetRaw("Logging.path"):
      errors.append("Windows in Logging.path, you probably want "
                    "%(WINDIR|env) instead")

    if not config_obj["Client.binary_name"].endswith(".exe"):
      errors.append("Missing .exe extension on binary_name %s" %
                    config_obj["Client.binary_name"])

    if not config_obj["Nanny.binary"].endswith(".exe"):
      errors.append("Missing .exe extension on nanny_binary")

    if errors_fatal and errors:
      for error in errors:
        logging.error("Build Config Error: %s", error)
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def MakeDeployableBinary(self, template_path, output_path):
    """Repackage the template zip with the installer."""
    context = self.context + ["Client Context"]

    zip_data = io.BytesIO()
    output_zip = zipfile.ZipFile(
        zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    z_template = zipfile.ZipFile(open(template_path, "rb"))

    # Track which files we've copied already.
    completed_files = [
        "grr-client.exe", "GRRservice.exe", "dbg_grr-client.exe",
        "dbg_GRRservice.exe"
    ]

    # Change the name of the main binary to the configured name.
    client_bin_name = config.CONFIG.Get("Client.binary_name", context=context)

    console_build = config.CONFIG.Get("ClientBuilder.console", context=context)
    if console_build:
      client_filename = "dbg_grr-client.exe"
      service_filename = "dbg_GRRservice.exe"
    else:
      client_filename = "grr-client.exe"
      service_filename = "GRRservice.exe"

    bin_name = z_template.getinfo(client_filename)
    output_zip.writestr(client_bin_name, z_template.read(bin_name))

    CopyFileInZip(z_template, "grr-client.exe.manifest", output_zip,
                  "%s.manifest" % client_bin_name)
    completed_files.append("grr-client.exe.manifest")

    # Change the name of the service binary to the configured name.
    service_template = z_template.getinfo(service_filename)

    service_bin_name = config.CONFIG.Get(
        "Nanny.service_binary_name", context=context)
    output_zip.writestr(service_bin_name, z_template.read(service_template))

    if config.CONFIG["ClientBuilder.fleetspeak_enabled"]:
      self._GenerateFleetspeakServiceConfig(output_zip)

    if self.signed_template:
      # If the template libs were already signed we can skip signing
      CreateNewZipWithSignedLibs(
          z_template, output_zip, ignore_files=completed_files)
    else:
      CreateNewZipWithSignedLibs(
          z_template,
          output_zip,
          ignore_files=completed_files,
          signer=self.signer)
    output_zip.close()

    return self.MakeSelfExtractingZip(zip_data.getvalue(), output_path)

  def _GenerateFleetspeakServiceConfig(self, zip_file):
    orig_fs_config_path = config.CONFIG["ClientBuilder.fleetspeak_config_path"]
    final_fs_config_fname = config.CONFIG[
        "Client.fleetspeak_unsigned_config_fname"]
    if orig_fs_config_path.endswith(".in"):
      logging.info("Interpolating %s", orig_fs_config_path)
      logging.warning("Backslashes will be naively re-escaped after "
                      "interpolation. If this is not desired, use a Fleetspeak "
                      "config file without the '.in' extension.")
      with utils.TempDirectory() as temp_dir:
        temp_fs_config_path = os.path.join(temp_dir, final_fs_config_fname)
        with io.open(orig_fs_config_path, "r") as source:
          with io.open(temp_fs_config_path, "w") as dest:
            interpolated = config.CONFIG.InterpolateValue(
                source.read(), context=self.context)
            dest.write(re.sub(r"\\", r"\\\\", interpolated))
        self._ValidateFleetspeakServiceConfig(temp_fs_config_path)
        zip_file.write(temp_fs_config_path, final_fs_config_fname)
    else:
      self._ValidateFleetspeakServiceConfig(orig_fs_config_path)
      zip_file.write(orig_fs_config_path, final_fs_config_fname)

  def _ValidateFleetspeakServiceConfig(self, config_path):
    """Validates a Fleetspeak service config.

    Checks that the given file is a valid TextFormat representation of
    a Fleetspeak service config proto.

    Args:
      config_path: Path to the config file.

    Raises:
      BuildError: If the config is not valid.
    """
    with open(config_path, "rb") as f:
      pool = descriptor_pool.DescriptorPool()
      pool.AddDescriptor(fs_config_pb2.Config.DESCRIPTOR)
      parsed_config = text_format.Parse(
          f.read(), fs_system_pb2.ClientServiceConfig(), descriptor_pool=pool)
      if parsed_config.factory != "Daemon":
        raise BuildError(
            "Fleetspeak config does not have the expected factory type.")
      daemon_cfg = fs_config_pb2.Config()
      parsed_config.config.Unpack(daemon_cfg)
      if not daemon_cfg.argv:
        raise BuildError(
            "Fleetspeak daemon service config does not specify command line "
            "args.")

  def MakeSelfExtractingZip(self, payload_data, output_path):
    """Repack the installer into the payload.

    Args:
      payload_data: data payload for zip file
      output_path: filename for the zip output
    Raises:
      RuntimeError: if the ClientBuilder.unzipsfx_stub doesn't require admin.
    Returns:
      output_path: filename string of zip output file
    """
    context = self.context + ["Client Context"]

    src_zip = zipfile.ZipFile(io.BytesIO(payload_data), mode="r")
    zip_data = io.BytesIO()
    output_zip = zipfile.ZipFile(
        zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    config_file_name = config.CONFIG.Get(
        "ClientBuilder.config_filename", context=context)
    # Copy the rest of the files from the package to the new zip.
    for template_file in src_zip.namelist():
      if template_file != config_file_name:
        # Avoid writing the config file twice if we're repacking a binary that
        # has already been run through deployment. We write it in the next step,
        # so no need to copy over from the original here.
        CopyFileInZip(src_zip, template_file, output_zip)

    client_config_content = self.GetClientConfig(context)

    output_zip.writestr(
        config_file_name,
        client_config_content.encode("utf-8"),
        compress_type=zipfile.ZIP_STORED)

    # The zip file comment is used by the self extractor to run the installation
    # script. Comment has to be `bytes` object because `zipfile` module is not
    # smart enough to properly handle `unicode` objects. We use the `encode`
    # method instead of `SmartStr` because we expect this option to be an
    # `unicode` object and in case it is not, we want it to blow up.
    output_zip.comment = b"$AUTORUN$>%s" % config.CONFIG.Get(
        "ClientBuilder.autorun_command_line", context=context).encode("utf-8")

    output_zip.close()

    utils.EnsureDirExists(os.path.dirname(output_path))
    with open(output_path, "wb") as fd:
      # First write the installer stub
      stub_data = io.BytesIO()
      unzipsfx_stub = config.CONFIG.Get(
          "ClientBuilder.unzipsfx_stub", context=context)
      stub_raw = open(unzipsfx_stub, "rb").read()

      # Check stub has been compiled with the requireAdministrator manifest.
      if b"level=\"requireAdministrator" not in stub_raw:
        raise RuntimeError("Bad unzip binary in use. Not compiled with the"
                           "requireAdministrator manifest option.")

      stub_data.write(stub_raw)

      # If in verbose mode, modify the unzip bins PE header to run in console
      # mode for easier debugging.
      SetPeSubsystem(
          stub_data,
          console=config.CONFIG.Get("ClientBuilder.console", context=context))

      # Now patch up the .rsrc section to contain the payload.
      end_of_file = zip_data.tell() + stub_data.tell()

      # This is the IMAGE_SECTION_HEADER.Name which is also the start of
      # IMAGE_SECTION_HEADER.
      offset_to_rsrc = stub_data.getvalue().find(b".rsrc")

      # IMAGE_SECTION_HEADER.PointerToRawData is a 32 bit int.
      stub_data.seek(offset_to_rsrc + 20)
      start_of_rsrc_section = struct.unpack("<I", stub_data.read(4))[0]

      # Adjust IMAGE_SECTION_HEADER.SizeOfRawData to span from the old start to
      # the end of file.
      stub_data.seek(offset_to_rsrc + 16)
      stub_data.write(struct.pack("<I", end_of_file - start_of_rsrc_section))

      # Concatenate stub and zip file.
      out_data = io.BytesIO()
      out_data.write(stub_data.getvalue())
      out_data.write(zip_data.getvalue())

      # Then write the actual output file.
      fd.write(out_data.getvalue())

    if self.signer:
      self.signer.SignFile(output_path)

    logging.info("Deployable binary generated at %s", output_path)

    return output_path


class DarwinClientRepacker(ClientRepacker):
  """Repackage OSX clients."""

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template."""
    context = self.context + ["Client Context"]
    utils.EnsureDirExists(os.path.dirname(output_path))

    client_config_data = self.GetClientConfig(context)
    shutil.copyfile(template_path, output_path)
    zip_file = zipfile.ZipFile(output_path, mode="a")
    zip_info = zipfile.ZipInfo(filename="config.yaml")
    zip_file.writestr(zip_info, client_config_data)
    zip_file.close()
    return output_path


class LinuxClientRepacker(ClientRepacker):
  """Repackage Linux templates."""

  # TODO(user):pytype: incorrect shutil.move() definition in typeshed.
  # pytype: disable=wrong-arg-types
  def GenerateDPKGFiles(self, template_path):
    """Generates the files needed by dpkg-buildpackage."""

    # Rename the generated binaries to the correct name.
    template_binary_dir = os.path.join(template_path, "dist/debian/grr-client")
    package_name = config.CONFIG.Get(
        "ClientBuilder.package_name", context=self.context)
    target_binary_dir = os.path.join(
        template_path, "dist/debian/%s%s" %
        (package_name,
         config.CONFIG.Get("ClientBuilder.target_dir", context=self.context)))
    if package_name == "grr-client":
      # Need to rename the template path or the move will fail.
      shutil.move(template_binary_dir, "%s-template" % template_binary_dir)
      template_binary_dir = "%s-template" % template_binary_dir

    utils.EnsureDirExists(os.path.dirname(target_binary_dir))
    shutil.move(template_binary_dir, target_binary_dir)

    shutil.move(
        os.path.join(target_binary_dir, "grr-client"),
        os.path.join(
            target_binary_dir,
            config.CONFIG.Get("Client.binary_name", context=self.context)))

    deb_in_dir = os.path.join(template_path, "dist/debian/debian.in/")

    self.GenerateDirectory(deb_in_dir, os.path.join(
        template_path, "dist/debian"), [("grr-client", package_name)])

    # Generate directories for the /usr/sbin link.
    utils.EnsureDirExists(
        os.path.join(template_path, "dist/debian/%s/usr/sbin" % package_name))

    # Generate the nanny template. This only exists from client version 3.1.2.5
    # onwards.
    if config.CONFIG["Template.version_numeric"] >= 3125:
      self.GenerateFile(
          os.path.join(target_binary_dir, "nanny.sh.in"),
          os.path.join(target_binary_dir, "nanny.sh"))

    # Generate the upstart template.
    self.GenerateFile(
        os.path.join(template_path, "dist/debian/upstart.in/grr-client.conf"),
        os.path.join(template_path, "dist/debian/%s.upstart" % package_name))

    # Generate the initd template. The init will not run if it detects upstart
    # is present.
    self.GenerateFile(
        os.path.join(template_path, "dist/debian/initd.in/grr-client"),
        os.path.join(template_path, "dist/debian/%s.init" % package_name))

    # Generate the systemd unit file.
    self.GenerateFile(
        os.path.join(template_path,
                     "dist/debian/systemd.in/grr-client.service"),
        os.path.join(template_path, "dist/debian/%s.service" % package_name))

    # Clean up the template dirs.
    shutil.rmtree(deb_in_dir)
    shutil.rmtree(os.path.join(template_path, "dist/debian/upstart.in"))
    shutil.rmtree(os.path.join(template_path, "dist/debian/initd.in"))
    shutil.rmtree(os.path.join(template_path, "dist/debian/systemd.in"))

  # pytype: enable=wrong-arg-types

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template and create a .deb."""
    buildpackage_binary = "/usr/bin/dpkg-buildpackage"
    if not os.path.exists(buildpackage_binary):
      logging.error("dpkg-buildpackage not found, unable to repack client.")
      return

    with utils.TempDirectory() as tmp_dir:
      template_dir = os.path.join(tmp_dir, "dist")
      utils.EnsureDirExists(template_dir)

      zf = zipfile.ZipFile(template_path)
      for name in zf.namelist():
        dirname = os.path.dirname(name)
        utils.EnsureDirExists(os.path.join(template_dir, dirname))
        with open(os.path.join(template_dir, name), "wb") as fd:
          fd.write(zf.read(name))

      # Generate the dpkg files.
      self.GenerateDPKGFiles(tmp_dir)

      # Create a client config.
      client_context = ["Client Context"] + self.context
      client_config_content = self.GetClientConfig(client_context)

      # We need to strip leading /'s or .join will ignore everything that comes
      # before it.
      target_dir = config.CONFIG.Get(
          "ClientBuilder.target_dir", context=self.context).lstrip("/")
      agent_dir = os.path.join(
          template_dir, "debian",
          config.CONFIG.Get("ClientBuilder.package_name", context=self.context),
          target_dir)

      with open(
          os.path.join(
              agent_dir,
              config.CONFIG.Get(
                  "ClientBuilder.config_filename", context=self.context)),
          "wb") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(
          os.path.join(
              agent_dir,
              config.CONFIG.Get("Client.binary_name", context=self.context)),
          0o755)

      arch = config.CONFIG.Get("Template.arch", context=self.context)

      try:
        old_working_dir = os.getcwd()
      except OSError:
        old_working_dir = os.environ.get("HOME", "/tmp")

      try:
        os.chdir(template_dir)
        command = [buildpackage_binary, "-uc", "-d", "-b", "-a%s" % arch]

        try:
          subprocess.check_output(command, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
          if "Failed to sign" not in e.output:
            logging.error("Error calling %s.", command)
            logging.error(e.output)
            raise

        filename_base = config.CONFIG.Get(
            "ClientBuilder.debian_package_base", context=self.context)
        output_base = config.CONFIG.Get(
            "ClientRepacker.output_basename", context=self.context)
      finally:
        try:
          os.chdir(old_working_dir)
        except OSError:
          pass

      utils.EnsureDirExists(os.path.dirname(output_path))

      for extension in [
          ".changes",
          config.CONFIG.Get(
              "ClientBuilder.output_extension", context=self.context)
      ]:
        input_name = "%s%s" % (filename_base, extension)
        output_name = "%s%s" % (output_base, extension)

        # TODO(user):pytype: incorrect move() definition in typeshed.
        # pytype: disable=wrong-arg-types
        shutil.move(
            os.path.join(tmp_dir, input_name),
            os.path.join(os.path.dirname(output_path), output_name))
        # pytype: enable=wrong-arg-types

      logging.info("Created package %s", output_path)
      return output_path


class CentosClientRepacker(LinuxClientRepacker):
  """Repackages Linux RPM templates."""

  def Sign(self, rpm_filename):
    if self.signer:
      return self.signer.AddSignatureToRPMs([rpm_filename])

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template and create a .rpm."""

    rpmbuild_binary = "/usr/bin/rpmbuild"
    if not os.path.exists(rpmbuild_binary):
      logging.error("rpmbuild not found, unable to repack client.")
      return

    with utils.TempDirectory() as tmp_dir:
      template_dir = os.path.join(tmp_dir, "dist")
      utils.EnsureDirExists(template_dir)

      zf = zipfile.ZipFile(template_path)
      for name in zf.namelist():
        dirname = os.path.dirname(name)
        utils.EnsureDirExists(os.path.join(template_dir, dirname))
        with open(os.path.join(template_dir, name), "wb") as fd:
          fd.write(zf.read(name))

      # Set up a RPM building environment.

      rpm_root_dir = os.path.join(tmp_dir, "rpmbuild")

      rpm_build_dir = os.path.join(rpm_root_dir, "BUILD")
      utils.EnsureDirExists(rpm_build_dir)

      rpm_buildroot_dir = os.path.join(rpm_root_dir, "BUILDROOT")
      utils.EnsureDirExists(rpm_buildroot_dir)

      rpm_rpms_dir = os.path.join(rpm_root_dir, "RPMS")
      utils.EnsureDirExists(rpm_rpms_dir)

      rpm_specs_dir = os.path.join(rpm_root_dir, "SPECS")
      utils.EnsureDirExists(rpm_specs_dir)

      template_binary_dir = os.path.join(tmp_dir, "dist/rpmbuild/grr-client")

      target_binary_dir = "%s%s" % (
          rpm_build_dir,
          config.CONFIG.Get("ClientBuilder.target_dir", context=self.context))

      utils.EnsureDirExists(os.path.dirname(target_binary_dir))
      try:
        shutil.rmtree(target_binary_dir)
      except OSError:
        pass
      # TODO(user):pytype: incorrect move() definition in typeshed.
      # pytype: disable=wrong-arg-types
      shutil.move(template_binary_dir, target_binary_dir)
      # pytype: enable=wrong-arg-types

      client_name = config.CONFIG.Get("Client.name", context=self.context)
      client_binary_name = config.CONFIG.Get(
          "Client.binary_name", context=self.context)
      if client_binary_name != "grr-client":
        # TODO(user):pytype: incorrect move() definition in typeshed.
        # pytype: disable=wrong-arg-types
        shutil.move(
            os.path.join(target_binary_dir, "grr-client"),
            os.path.join(target_binary_dir, client_binary_name))
        # pytype: enable=wrong-arg-types

      # Generate spec
      spec_filename = os.path.join(rpm_specs_dir, "%s.spec" % client_name)
      self.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/grr.spec.in"), spec_filename)

      initd_target_filename = os.path.join(rpm_build_dir, "etc/init.d",
                                           client_name)

      # Generate init.d
      utils.EnsureDirExists(os.path.dirname(initd_target_filename))
      self.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/grr-client.initd.in"),
          initd_target_filename)

      # Generate systemd unit
      if config.CONFIG["Template.version_numeric"] >= 3125:
        systemd_target_filename = os.path.join(rpm_build_dir,
                                               "usr/lib/systemd/system/",
                                               "%s.service" % client_name)

        utils.EnsureDirExists(os.path.dirname(systemd_target_filename))
        self.GenerateFile(
            os.path.join(tmp_dir, "dist/rpmbuild/grr-client.service.in"),
            systemd_target_filename)

        # Generate prelinking blacklist file
        prelink_target_filename = os.path.join(
            rpm_build_dir, "etc/prelink.conf.d", "%s.conf" % client_name)

        utils.EnsureDirExists(os.path.dirname(prelink_target_filename))
        self.GenerateFile(
            os.path.join(tmp_dir, "dist/rpmbuild/prelink_blacklist.conf.in"),
            prelink_target_filename)

      # Create a client config.
      client_context = ["Client Context"] + self.context
      client_config_content = self.GetClientConfig(client_context)

      with open(
          os.path.join(
              target_binary_dir,
              config.CONFIG.Get(
                  "ClientBuilder.config_filename", context=self.context)),
          "wb") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(os.path.join(target_binary_dir, client_binary_name), 0o755)

      client_arch = config.CONFIG.Get("Template.arch", context=self.context)
      if client_arch == "amd64":
        client_arch = "x86_64"

      command = [
          rpmbuild_binary, "--define", "_topdir " + rpm_root_dir, "--target",
          client_arch, "--buildroot", rpm_buildroot_dir, "-bb", spec_filename
      ]
      try:
        subprocess.check_output(command, stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError as e:
        logging.error("Error calling %s.", command)
        logging.error(e.output)
        raise

      client_version = config.CONFIG.Get(
          "Template.version_string", context=self.context)
      rpm_filename = os.path.join(
          rpm_rpms_dir, client_arch,
          "%s-%s-1.%s.rpm" % (client_name, client_version, client_arch))

      utils.EnsureDirExists(os.path.dirname(output_path))
      shutil.move(rpm_filename, output_path)

      logging.info("Created package %s", output_path)
      self.Sign(output_path)
      return output_path


def CopyFileInZip(from_zip, from_name, to_zip, to_name=None, signer=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
  if signer:
    logging.debug("Signing %s", from_name)
    data = signer.SignBuffer(data)
  to_zip.writestr(to_name, data)


def CreateNewZipWithSignedLibs(z_in,
                               z_out,
                               ignore_files=None,
                               signer=None,
                               skip_signing_files=None):
  """Copies files from one zip to another, signing all qualifying files."""
  ignore_files = ignore_files or []
  skip_signing_files = skip_signing_files or []
  extensions_to_sign = [".sys", ".exe", ".dll", ".pyd"]
  to_sign = []
  for template_file in z_in.namelist():
    if template_file not in ignore_files:
      extension = os.path.splitext(template_file)[1].lower()
      if (signer and template_file not in skip_signing_files and
          extension in extensions_to_sign):
        to_sign.append(template_file)
      else:
        CopyFileInZip(z_in, template_file, z_out)

  temp_files = {}
  for filename in to_sign:
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, "wb") as temp_fd:
      temp_fd.write(z_in.read(filename))
    temp_files[filename] = path

  try:
    signer.SignFiles(itervalues(temp_files))
  except AttributeError:
    for f in itervalues(temp_files):
      signer.SignFile(f)

  for filename, tempfile_path in iteritems(temp_files):
    z_out.writestr(filename, open(tempfile_path, "rb").read())


def SetPeSubsystem(fd, console=True):
  """Takes file like obj and returns (offset, value) for the PE subsystem."""
  current_pos = fd.tell()
  fd.seek(0x3c)  # _IMAGE_DOS_HEADER.e_lfanew
  header_offset = struct.unpack("<I", fd.read(4))[0]
  # _IMAGE_NT_HEADERS.OptionalHeader.Subsystem ( 0x18 + 0x44)
  subsystem_offset = header_offset + 0x5c
  fd.seek(subsystem_offset)
  if console:
    fd.write(b"\x03")
  else:
    fd.write(b"\x02")
  fd.seek(current_pos)
