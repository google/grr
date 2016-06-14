#!/usr/bin/env python
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""
import cStringIO
import logging
import os
import shutil
import struct
import subprocess
import zipfile

import yaml

# pylint: disable=g-import-not-at-top
# This is a workaround so we don't need to maintain the whole PyInstaller
# codebase as a full-fledged dependency.
try:
  from PyInstaller import __main__ as PyInstallerMain
except ImportError:
  # We ignore this failure since most people running the code don't build their
  # own clients and printing an error message causes confusion.  Those building
  # their own clients will need PyInstaller installed.
  pass

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client

# pylint: enable=g-import-not-at-top


class BuilderBase(object):
  """A base class for builder / repacker that provides utility functions."""

  def __init__(self, context=None):
    self.context = context or config_lib.CONFIG.context[:]
    self.context = ["ClientBuilder Context"] + self.context

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
    data = open(input_filename, "rb").read()
    logging.debug("Generating file %s from %s", output_filename, input_filename)

    with open(output_filename, "wb") as fd:
      fd.write(config_lib.CONFIG.InterpolateValue(data, context=self.context))


class ClientBuilder(BuilderBase):
  """A client builder is responsible for building the binary template.

  This is an abstract client builder class, used by the OS specific
  implementations. Note that client builders typically run on the target
  operating system.
  """
  REQUIRED_BUILD_YAML_KEYS = set(["Client.build_environment",
                                  "Client.build_time", "Template.build_type",
                                  "Template.build_context",
                                  "Template.version_major",
                                  "Template.version_minor",
                                  "Template.version_revision",
                                  "Template.version_release", "Template.arch"])

  def MakeBuildDirectory(self):
    """Prepares the build directory."""
    # Create the build directory and let pyinstaller loose on it.
    self.build_dir = config_lib.CONFIG.Get("PyInstaller.build_dir",
                                           context=self.context)
    self.work_path = config_lib.CONFIG.Get("PyInstaller.workpath_dir",
                                           context=self.context)

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
    self.CleanDirectory(config_lib.CONFIG.Get("PyInstaller.distpath",
                                              context=self.context))

    logging.info("Copying pyinstaller support files")
    self.spec_file = os.path.join(self.build_dir, "grr.spec")

    with open(self.spec_file, "wb") as fd:
      fd.write(config_lib.CONFIG.Get("PyInstaller.spec", context=self.context))

    with open(os.path.join(self.build_dir, "version.txt"), "wb") as fd:
      fd.write(config_lib.CONFIG.Get("PyInstaller.version",
                                     context=self.context))

    with open(os.path.join(self.build_dir, "grr.ico"), "wb") as fd:
      fd.write(config_lib.CONFIG.Get("PyInstaller.icon", context=self.context))

    # We expect the onedir output at this location.
    self.output_dir = os.path.join(
        config_lib.CONFIG.Get("PyInstaller.distpath",
                              context=self.context),
        "grr-client")

    # Pyinstaller doesn't handle unicode strings.
    args = ["--distpath", str(config_lib.CONFIG.Get("PyInstaller.distpath",
                                                    context=self.context)),
            "--workpath", str(config_lib.CONFIG.Get("PyInstaller.workpath_dir",
                                                    context=self.context)),
            str(self.spec_file)]
    logging.info("Running pyinstaller: %s", args)
    PyInstallerMain.run(pyi_args=[utils.SmartStr(x) for x in args])

    # Clear out some crud that pyinstaller includes.
    for path in ["tcl", "tk", "pytz"]:
      dir_path = os.path.join(self.output_dir, path)
      try:
        shutil.rmtree(dir_path)
        os.mkdir(dir_path)
        # Create an empty file so the directories get put in the installers.
        with open(os.path.join(dir_path, path), "wb"):
          pass
      except OSError:
        pass

    version_ini = config_lib.Resource().Filter("version.ini")
    if not os.path.exists(version_ini):
      raise RuntimeError("Couldn't find version_ini in virtual env root: %s" %
                         version_ini)
    shutil.copy(version_ini, os.path.join(self.output_dir, "version.ini"))

    with open(os.path.join(self.output_dir, "build.yaml"), "w") as fd:
      self.WriteBuildYaml(fd)

  def WriteBuildYaml(self, fd):
    """Write build spec to fd."""
    output = {
        "Client.build_environment":
            str(rdf_client.Uname.FromCurrentSystem().signature()),
        "Client.build_time": str(rdfvalue.RDFDatetime().Now()),
        "Template.build_type":
            str(config_lib.CONFIG.Get("ClientBuilder.build_type",
                                      context=self.context)),
        "Template.build_context": self.context,
        "Template.version_major": str(config_lib.CONFIG.Get(
            "Source.version_major", context=self.context)),
        "Template.version_minor": str(config_lib.CONFIG.Get(
            "Source.version_minor", context=self.context)),
        "Template.version_revision":
            str(config_lib.CONFIG.Get("Source.version_revision",
                                      context=self.context)),
        "Template.version_release":
            str(config_lib.CONFIG.Get("Source.version_release",
                                      context=self.context)),
        "Template.arch": str(config_lib.CONFIG.Get("Client.arch",
                                                   context=self.context))
    }

    if set(output.keys()) != self.REQUIRED_BUILD_YAML_KEYS:
      raise RuntimeError("Bad build.yaml: expected %s, got %s" %
                         (self.REQUIRED_BUILD_YAML_KEYS, output.keys()))
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
    self.template_file = output_file or config_lib.CONFIG.Get(
        "ClientBuilder.template_path",
        context=self.context)
    utils.EnsureDirExists(os.path.dirname(self.template_file))

  def MakeZip(self, input_dir, output_file):
    """Creates a ZIP archive of the files in the input directory.

    Args:
      input_dir: the name of the input directory.
      output_file: the name of the output ZIP archive without extension.
    """
    logging.info("Generating zip template file at %s", output_file)
    basename, _ = os.path.splitext(output_file)
    shutil.make_archive(basename,
                        "zip",
                        base_dir=".",
                        root_dir=input_dir,
                        verbose=True)

# Register builders into this module's namespace.
ClientBuilder.classes = globals()


class ClientRepacker(BuilderBase):
  """Takes the binary template and producing an installer.

  Note that this should be runnable on all operating systems.
  """

  CONFIG_SECTIONS = ["CA", "Client", "Logging", "Config", "Nanny", "Installer"]

  # Config options that should never make it to a deployable binary.
  SKIP_OPTION_LIST = ["Client.private_key"]

  def __init__(self, context=None, signer=None):
    super(ClientRepacker, self).__init__(context=context)
    self.signer = signer

  def GetClientConfig(self, context, validate=True):
    """Generates the client config file for inclusion in deployable binaries."""
    with utils.TempDirectory() as tmp_dir:
      # Make sure we write the file in yaml format.
      filename = os.path.join(tmp_dir,
                              config_lib.CONFIG.Get(
                                  "ClientBuilder.config_filename",
                                  context=context))

      new_config = config_lib.CONFIG.MakeNewConfig()
      new_config.Initialize(reset=True, data="")
      new_config.SetWriteBack(filename)

      # Only copy certain sections to the client. We enumerate all
      # defined options and then resolve those from the config in the
      # client's context. The result is the raw option as if the
      # client read our config file.
      for descriptor in sorted(config_lib.CONFIG.type_infos,
                               key=lambda x: x.name):
        if descriptor.name in self.SKIP_OPTION_LIST:
          continue

        if descriptor.section in self.CONFIG_SECTIONS:
          value = config_lib.CONFIG.GetRaw(descriptor.name,
                                           context=context,
                                           default=None)

          if value is not None:
            logging.debug("Copying config option to client: %s",
                          descriptor.name)

            new_config.SetRaw(descriptor.name, value)

      new_config.Set("Client.deploy_time", str(rdfvalue.RDFDatetime().Now()))
      new_config.Write()

      if validate:
        self.ValidateEndConfig(new_config)

      return open(filename, "rb").read()

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Given a generated client config, attempt to check for common errors."""
    errors = []

    location = config.Get("Client.server_urls", context=self.context)
    if not location:
      errors.append("Empty Client.server_urls")

    for url in location:
      if not url.startswith("http"):
        errors.append("Bad Client.server_urls specified %s" % url)

    key_data = config.GetRaw("Client.executable_signing_public_key",
                             default=None,
                             context=self.context)
    if key_data is None:
      errors.append("Missing Client.executable_signing_public_key.")
    elif not key_data.startswith("-----BEGIN PUBLIC"):
      errors.append("Invalid Client.executable_signing_public_key: %s" %
                    key_data)

    certificate = config.GetRaw("CA.certificate",
                                default=None,
                                context=self.context)
    if certificate is None or not certificate.startswith("-----BEGIN CERTIF"):
      errors.append("CA certificate missing from config.")

    for bad_opt in ["Client.private_key"]:
      if config.Get(bad_opt, context=self.context, default=""):
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

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Windows specific config validations."""
    errors = super(WindowsClientRepacker, self).ValidateEndConfig(
        config, errors_fatal=errors_fatal)

    for path in config.GetRaw("Client.tempdir_roots"):
      if path.startswith("/"):
        errors.append(
            "Client.tempdir_root %s starts with /, probably has Unix path." %
            path)

    if config.GetRaw("Logging.path").startswith("/"):
      errors.append("Logging.path starts with /, probably has Unix path. %s" %
                    config["Logging.path"])

    if "Windows\\" in config.GetRaw("Logging.path"):
      errors.append("Windows in Logging.path, you probably want "
                    "%(WINDIR|env) instead")

    if not config["Client.binary_name"].endswith(".exe"):
      errors.append("Missing .exe extension on binary_name %s" %
                    config["Client.binary_name"])

    if not config["Nanny.binary"].endswith(".exe"):
      errors.append("Missing .exe extension on nanny_binary")

    if errors_fatal and errors:
      for error in errors:
        logging.error("Build Config Error: %s", error)
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def InterpolateVariableInBinary(self, stream, parameter):
    """Replace magic strings in the binary with config parameters."""
    pattern = "<---------------- %s ------------------->" % parameter
    pattern = pattern.encode("utf_16_le")

    replacement = config_lib.CONFIG.Get(parameter, context=self.context)
    replacement = utils.SmartStr(replacement + "\x00").encode("utf_16_le")
    replacement = replacement[:len(pattern)]

    # Pad to the end of the string with nulls.
    replacement += "\x00" * (len(pattern) - len(replacement))

    start = 0
    while 1:
      offset = stream.getvalue().find(pattern, start)
      if offset < 0:
        return

      stream.seek(offset)
      stream.write(replacement)

  def Sign(self, inbuf):
    if self.signer:
      return self.signer.SignBuffer(inbuf)
    return inbuf

  def MakeDeployableBinary(self, template_path, output_path):
    """Repackage the template zip with the installer."""
    context = self.context + ["Client Context"]

    zip_data = cStringIO.StringIO()
    output_zip = zipfile.ZipFile(zip_data,
                                 mode="w",
                                 compression=zipfile.ZIP_DEFLATED)

    z_template = zipfile.ZipFile(open(template_path, "rb"))

    completed_files = []  # Track which files we've copied already.

    # Change the name of the main binary to the configured name.
    client_bin_name = config_lib.CONFIG.Get("Client.binary_name",
                                            context=context)

    extension = ""
    if "windows" == config_lib.CONFIG.Get("Client.platform", context=context):
      extension = ".exe"

    # The template always has the same binary name.
    bin_name = z_template.getinfo("grr-client" + extension)
    bin_dat = cStringIO.StringIO()
    bin_dat.write(z_template.read(bin_name))

    # Set output to console on binary if needed.
    SetPeSubsystem(bin_dat,
                   console=config_lib.CONFIG.Get("ClientBuilder.console",
                                                 context=context))

    # Interpolate resource strings.
    for parameter in ["Client.company_name", "Client.description",
                      "Client.name", "Template.version_string",
                      "ClientBuilder.package_name"]:
      self.InterpolateVariableInBinary(bin_dat, parameter)

    output_zip.writestr(client_bin_name, self.Sign(bin_dat.getvalue()))

    CopyFileInZip(z_template, "%s.manifest" % bin_name.filename, output_zip,
                  "%s.manifest" % client_bin_name)
    completed_files.append(bin_name.filename)
    completed_files.append("%s.manifest" % bin_name.filename)

    # Change the name of the service binary to the configured name.
    service_template = z_template.getinfo("GRRservice.exe")

    service_bin_dat = cStringIO.StringIO()
    service_bin_dat.write(z_template.read(service_template))

    # Set output to console on service binary if needed.
    SetPeSubsystem(service_bin_dat,
                   console=config_lib.CONFIG.Get("ClientBuilder.console",
                                                 context=context))

    service_bin_name = config_lib.CONFIG.Get("Nanny.service_binary_name",
                                             context=context)
    output_zip.writestr(service_bin_name, self.Sign(service_bin_dat.getvalue()))
    completed_files.append(service_template.filename)

    # Copy the rest of the files from the template to the new zip.  Current
    # practice is to only sign the grr client and nanny executables, not the
    # dlls.
    for template_file in z_template.namelist():
      if template_file not in completed_files:
        CopyFileInZip(z_template, template_file, output_zip)

    output_zip.close()

    return self.MakeSelfExtractingZip(zip_data.getvalue(), output_path)

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

    src_zip = zipfile.ZipFile(cStringIO.StringIO(payload_data), mode="r")
    zip_data = cStringIO.StringIO()
    output_zip = zipfile.ZipFile(zip_data,
                                 mode="w",
                                 compression=zipfile.ZIP_DEFLATED)

    config_file_name = config_lib.CONFIG.Get("ClientBuilder.config_filename",
                                             context=context)
    # Copy the rest of the files from the package to the new zip.
    for template_file in src_zip.namelist():
      if template_file != config_file_name:
        # Avoid writing the config file twice if we're repacking a binary that
        # has already been run through deployment. We write it in the next step,
        # so no need to copy over from the original here.
        CopyFileInZip(src_zip, template_file, output_zip)

    client_config_content = self.GetClientConfig(context)

    output_zip.writestr(config_file_name,
                        client_config_content,
                        compress_type=zipfile.ZIP_STORED)

    # The zip file comment is used by the self extractor to run
    # the installation script
    output_zip.comment = "$AUTORUN$>%s" % config_lib.CONFIG.Get(
        "ClientBuilder.autorun_command_line",
        context=context)

    output_zip.close()

    utils.EnsureDirExists(os.path.dirname(output_path))
    with open(output_path, "wb") as fd:
      # First write the installer stub
      stub_data = cStringIO.StringIO()
      unzipsfx_stub = config_lib.CONFIG.Get("ClientBuilder.unzipsfx_stub",
                                            context=context)
      stub_raw = open(unzipsfx_stub, "rb").read()

      # Check stub has been compiled with the requireAdministrator manifest.
      if "level=\"requireAdministrator" not in stub_raw:
        raise RuntimeError("Bad unzip binary in use. Not compiled with the"
                           "requireAdministrator manifest option.")

      stub_data.write(stub_raw)

      # If in verbose mode, modify the unzip bins PE header to run in console
      # mode for easier debugging.
      SetPeSubsystem(stub_data,
                     console=config_lib.CONFIG.Get("ClientBuilder.console",
                                                   context=context))

      # Now patch up the .rsrc section to contain the payload.
      end_of_file = zip_data.tell() + stub_data.tell()

      # This is the IMAGE_SECTION_HEADER.Name which is also the start of
      # IMAGE_SECTION_HEADER.
      offset_to_rsrc = stub_data.getvalue().find(".rsrc")

      # IMAGE_SECTION_HEADER.PointerToRawData is a 32 bit int.
      stub_data.seek(offset_to_rsrc + 20)
      start_of_rsrc_section = struct.unpack("<I", stub_data.read(4))[0]

      # Adjust IMAGE_SECTION_HEADER.SizeOfRawData to span from the old start to
      # the end of file.
      stub_data.seek(offset_to_rsrc + 16)
      stub_data.write(struct.pack("<I", end_of_file - start_of_rsrc_section))

      # Concatenate stub and zip file.
      out_data = cStringIO.StringIO()
      out_data.write(stub_data.getvalue())
      out_data.write(zip_data.getvalue())

      # Then write the actual output file.
      fd.write(self.Sign(out_data.getvalue()))

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

  def GenerateDPKGFiles(self, template_path):
    """Generates the files needed by dpkg-buildpackage."""

    # Rename the generated binaries to the correct name.
    template_binary_dir = os.path.join(template_path, "dist/debian/grr-client")
    package_name = config_lib.CONFIG.Get("ClientBuilder.package_name",
                                         context=self.context)
    target_binary_dir = os.path.join(
        template_path,
        "dist/debian/%s%s" % (package_name,
                              config_lib.CONFIG.Get("ClientBuilder.target_dir",
                                                    context=self.context)))
    if package_name == "grr-client":
      # Need to rename the template path or the move will fail.
      shutil.move(template_binary_dir, "%s-template" % template_binary_dir)
      template_binary_dir = "%s-template" % template_binary_dir

    utils.EnsureDirExists(os.path.dirname(target_binary_dir))
    shutil.move(template_binary_dir, target_binary_dir)

    shutil.move(
        os.path.join(target_binary_dir, "grr-client"),
        os.path.join(target_binary_dir,
                     config_lib.CONFIG.Get("Client.binary_name",
                                           context=self.context)))

    deb_in_dir = os.path.join(template_path, "dist/debian/debian.in/")

    self.GenerateDirectory(deb_in_dir,
                           os.path.join(template_path, "dist/debian"),
                           [("grr-client", package_name)])

    # Generate directories for the /usr/sbin link.
    utils.EnsureDirExists(os.path.join(template_path, "dist/debian/%s/usr/sbin"
                                       % package_name))

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
      target_dir = config_lib.CONFIG.Get("ClientBuilder.target_dir",
                                         context=self.context).lstrip("/")
      agent_dir = os.path.join(template_dir,
                               "debian",
                               config_lib.CONFIG.Get(
                                   "ClientBuilder.package_name",
                                   context=self.context),
                               target_dir)

      with open(
          os.path.join(agent_dir,
                       config_lib.CONFIG.Get("ClientBuilder.config_filename",
                                             context=self.context)),
          "wb") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(
          os.path.join(agent_dir,
                       config_lib.CONFIG.Get("Client.binary_name",
                                             context=self.context)),
          0755)

      arch = config_lib.CONFIG.Get("Template.arch", context=self.context)

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

        filename_base = config_lib.CONFIG.Get(
            "ClientBuilder.debian_package_base",
            context=self.context)
        output_base = config_lib.CONFIG.Get("ClientRepacker.output_basename",
                                            context=self.context)
        utils.EnsureDirExists(os.path.dirname(output_path))

        for extension in [".changes", config_lib.CONFIG.Get(
            "ClientBuilder.output_extension",
            context=self.context)]:
          input_name = "%s%s" % (filename_base, extension)
          output_name = "%s%s" % (output_base, extension)

          shutil.move(
              os.path.join(tmp_dir, input_name), os.path.join(
                  os.path.dirname(output_path), output_name))

        logging.info("Created package %s", output_path)
        return output_path
      finally:
        try:
          os.chdir(old_working_dir)
        except OSError:
          pass


class CentosClientRepacker(LinuxClientRepacker):
  """Repackages Linux RPM templates."""

  def Sign(self, rpm_filename):
    if self.signer:
      return self.signer.AddSignatureToRPM(rpm_filename)

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

      target_binary_dir = "%s%s" % (rpm_build_dir, config_lib.CONFIG.Get(
          "ClientBuilder.target_dir",
          context=self.context))

      utils.EnsureDirExists(os.path.dirname(target_binary_dir))
      try:
        shutil.rmtree(target_binary_dir)
      except OSError:
        pass
      shutil.move(template_binary_dir, target_binary_dir)
      client_name = config_lib.CONFIG.Get("Client.name", context=self.context)
      client_binary_name = config_lib.CONFIG.Get("Client.binary_name",
                                                 context=self.context)
      if client_binary_name != "grr-client":
        shutil.move(
            os.path.join(target_binary_dir, "grr-client"),
            os.path.join(target_binary_dir, client_binary_name))

      spec_filename = os.path.join(rpm_specs_dir, "%s.spec" % client_name)
      self.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/grr.spec.in"), spec_filename)

      initd_target_filename = os.path.join(rpm_build_dir, "etc/init.d",
                                           client_name)

      utils.EnsureDirExists(os.path.dirname(initd_target_filename))
      self.GenerateFile(
          os.path.join(tmp_dir, "dist/rpmbuild/grr-client.initd.in"),
          initd_target_filename)

      # Create a client config.
      client_context = ["Client Context"] + self.context
      client_config_content = self.GetClientConfig(client_context)

      with open(
          os.path.join(target_binary_dir,
                       config_lib.CONFIG.Get("ClientBuilder.config_filename",
                                             context=self.context)),
          "wb") as fd:
        fd.write(client_config_content)

      # Undo all prelinking for libs or the rpm might have checksum mismatches.
      logging.info("Undoing prelinking.")
      prelink = "/usr/sbin/prelink"
      if os.access(prelink, os.X_OK):
        libs = os.path.join(target_binary_dir, "lib*")
        # This returns non-zero if there are no prelinked binaries so we can't
        # check_call.
        subprocess.call("%s -u %s 2>/dev/null" % (prelink, libs), shell=True)
      else:
        raise RuntimeError("Can't execute %s, skipping." % prelink)

      # Set the daemon to executable.
      os.chmod(os.path.join(target_binary_dir, client_binary_name), 0755)

      client_arch = config_lib.CONFIG.Get("Template.arch", context=self.context)
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

      client_version = config_lib.CONFIG.Get("Template.version_string",
                                             context=self.context)
      rpm_filename = os.path.join(rpm_rpms_dir, client_arch, "%s-%s-1.%s.rpm" %
                                  (client_name, client_version, client_arch))

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
    data = signer.SignBuffer(data)
  to_zip.writestr(to_name, data)


def SetPeSubsystem(fd, console=True):
  """Takes file like obj and returns (offset, value) for the PE subsystem."""
  current_pos = fd.tell()
  fd.seek(0x3c)  # _IMAGE_DOS_HEADER.e_lfanew
  header_offset = struct.unpack("<I", fd.read(4))[0]
  # _IMAGE_NT_HEADERS.OptionalHeader.Subsystem ( 0x18 + 0x44)
  subsystem_offset = header_offset + 0x5c
  fd.seek(subsystem_offset)
  if console:
    fd.write("\x03")
  else:
    fd.write("\x02")
  fd.seek(current_pos)
