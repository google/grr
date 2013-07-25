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
import sys
import time
import zipfile

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class PathTypeInfo(type_info.String):
  """A path to a file or a directory."""

  def __init__(self, must_exist=True, **kwargs):
    self.must_exist = must_exist
    super(PathTypeInfo, self).__init__(**kwargs)

  def Validate(self, value):
    value = super(PathTypeInfo, self).Validate(value)
    if self.must_exist and not os.access(value, os.R_OK):
      raise type_info.TypeValueError(
          "Path %s does not exist for %s" % (value, self.name))

    return value

  def FromString(self, string):
    return os.path.normpath(string)


# PyInstaller build configuration.
config_lib.DEFINE_option(PathTypeInfo(
    name="PyInstaller.path", must_exist=False,
    default="c:/grr_build/pyinstaller/pyinstaller.py",
    help="Path to the main pyinstaller.py file."))

config_lib.DEFINE_option(PathTypeInfo(
    name="PyInstaller.pathex", must_exist=False,
    default="", help="Additional paths for searching for libraries."))

config_lib.DEFINE_bool(
    "ClientBuilder.console", default=False,
    help="Should the application be built as a console program. "
    "This aids debugging in windows.")

config_lib.DEFINE_string(
    name="PyInstaller.spec",
    help="The spec file contents to use for building the client.",
    default=r"""
# By default build in one dir mode.
a = Analysis\(
    ["%(ClientBuilder.source)/grr/client/client.py"],
    pathex=%(PyInstaller.pathex),
    hiddenimports=[],
    hookspath=None\)
pyz = PYZ\(
    a.pure\)
exe = EXE\(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name='build/%(Client.binary_name)',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    version='%(PyInstaller.build_dir)/version.txt',
    icon='%(PyInstaller.build_dir)/grr.ico'\)

coll = COLLECT\(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='%(PyInstaller.output_basename)'\)
""")

config_lib.DEFINE_string(
    name="PyInstaller.distpath",
    help=("Passed to PyInstaller as the --distpath flag. This sets the output "
          "directory for PyInstaller."),
    default="./dist")

config_lib.DEFINE_string(
    name="PyInstaller.version",
    help="The version.txt file contents to use for building the client.",
    default=r"""
VSVersionInfo\(
  ffi=FixedFileInfo\(
    filevers=\(%(Client.version_major), %(Client.version_minor),
               %(Client.version_revision), %(Client.version_release)\),
    prodvers=\(%(Client.version_major), %(Client.version_minor),
               %(Client.version_revision), %(Client.version_release)\),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=\(0, 0\)
    \),
  kids=[
    StringFileInfo\(
      [
      StringTable\(
        '040904B0',
        [StringStruct\('CompanyName', "%(Client.company_name)"\),
        StringStruct\('FileDescription', "%(Client.description)"\),
        StringStruct\('FileVersion', '%(Client.version_string)'\),
        StringStruct\('InternalName', '%(Client.description)' \),
        StringStruct\('OriginalFilename', '%(ClientBuilder.package_name)' \)]\),
      ]\),
  VarFileInfo\([VarStruct\('Translation', [1033, 1200]\)]\)
  ]
\)
""")

config_lib.DEFINE_bytes(
    "PyInstaller.icon",
    "%(%(ClientBuilder.source)/grr/gui/static/images/grr.ico|file)",
    "The icon file contents to use for building the client.")

config_lib.DEFINE_string(
    "PyInstaller.build_dir",
    "./build",
    "The path to the build directory.")

config_lib.DEFINE_string(
    "PyInstaller.dist_dir",
    "./dist/",
    "The path to the build directory.")

config_lib.DEFINE_string(
    name="PyInstaller.output_basename",
    default="%(Client.name)_%(Client.version_string)_%(Client.arch)",
    help="The base name of the output package.")


config_lib.DEFINE_string(
    name="ClientBuilder.source",
    default=os.path.normpath(os.path.dirname(__file__) + "/../.."),
    help="The location of the source tree.")

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.nanny_source_dir", must_exist=True,
    default="%(ClientBuilder.source)/grr/client/nanny/",
    help="Path to the windows nanny VS solution file."))

config_lib.DEFINE_choice(
    name="ClientBuilder.build_type",
    default="Release",
    choices=["Release", "Debug"],
    help="Type of build (Debug, Release)")

config_lib.DEFINE_string(name="ClientBuilder.template_extension",
                         default=".zip",
                         help="The extension to appear on templates.")


config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.template_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)"
        "/templates/%(Client.arch)/%(Client.version_string)/"
        "%(PyInstaller.output_basename)%(ClientBuilder.template_extension)"),
    help="The full path to the executable template file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.executables_path", must_exist=False,
    default="%(ClientBuilder.source)/grr/executables",
    help="The path to the grr executables directory."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.output_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)"
        "/installers/%(Client.arch)/%(Client.version_string)/"
        "%(PyInstaller.output_basename)"
        "%(ClientBuilder.output_extension)"),
    help="The full path to the generated installer file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.generated_config_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)"
        "/config/%(PyInstaller.output_basename).yaml"),
    help="The full path to where we write a generated config."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.unzipsfx_stub", must_exist=False,
    default=("%(ClientBuilder.executables_path)/%(Client.platform)"
             "/templates/unzipsfx/unzipsfx-%(Client.arch).exe"),
    help="The full path to the zip self extracting stub."))

config_lib.DEFINE_string(
    name="ClientBuilder.config_filename",
    default="%(Client.binary_name).yaml",
    help=("The name of the configuration file which will be embedded in the "
          "deployable binary."))

config_lib.DEFINE_string(
    name="ClientBuilder.autorun_command_line",
    default=("%(Client.binary_name) --install "
             "--config %(ClientBuilder.config_filename)"),
    help=("The command that the installer will execute after "
          "unpacking the package."))

config_lib.DEFINE_list(
    name="ClientBuilder.installer_plugins",
    default=[],
    help="Plugins that will copied to the client installation file and run "
    "at install time.")

config_lib.DEFINE_list(
    name="ClientBuilder.plugins",
    default=[],
    help="Plugins that will copied to the client installation file and run when"
    "the client is running.")

config_lib.DEFINE_string(
    name="ClientBuilder.client_logging_filename",
    default="%(Logging.path)/GRRlog.txt",
    help="Filename for logging, to be copied to Client section in the client "
    "that gets built.")

config_lib.DEFINE_string(
    name="ClientBuilder.client_logging_path",
    default="/tmp",
    help="Filename for logging, to be copied to Client section in the client "
    "that gets built.")

config_lib.DEFINE_list(
    name="ClientBuilder.client_logging_engines",
    default=["stderr", "file"],
    help="Enabled logging engines, to be copied to Logging.engines in client "
    "configuration.")

config_lib.DEFINE_string(
    name="ClientBuilder.client_installer_logfile",
    default="%(Logging.path)/%(Client.name)_installer.txt",
    help="Logfile for logging the client installation process, to be copied to"
    " Installer.logfile in client built.")

config_lib.DEFINE_string(
    name="ClientBuilder.maintainer",
    default="GRR <grr-dev@googlegroups.com>",
    help="The client package's maintainer.")

config_lib.DEFINE_string(
    name="ClientBuilder.debian_build_time",
    default=time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
    help="The build time put into the debian package. Needs to be formatted"
    " like the output of 'date -R'.")

config_lib.DEFINE_string(
    name="ClientBuilder.debian_version",
    default="%(Client.version_numeric)",
    help="The version of the debian package.")

config_lib.DEFINE_string(
    name="ClientBuilder.debian_package_base",
    default=("%(ClientBuilder.package_name)_"
             "%(ClientBuilder.debian_version)_%(Client.arch)"),
    help="The filename of the debian package without extension.")

config_lib.DEFINE_string(
    name="ClientBuilder.package_name",
    default="%(Client.name)",
    help="The debian package name.")


class ClientBuilder(object):
  """Abstract client builder class, used by the OS specific implementations."""

  CONFIG_SECTIONS = ["CA", "Client", "Logging", "Config", "Nanny", "Installer"]

  # Config options that should never make it to a deployable binary.
  SKIP_OPTION_LIST = ["Client.certificate", "Client.private_key"]

  def __init__(self, context=None):
    self.context = context or config_lib.CONFIG.context[:]
    self.context = ["ClientBuilder Context"] + self.context

  def FindLibraryPaths(self):
    """Figure out where distorm is so PyInstaller can find it."""
    logging.info("Searching for external libraries.")
    librarypaths = ["."]
    try:
      import distorm3  # pylint: disable=g-import-not-at-top
      librarypaths.append(os.path.dirname(distorm3.__file__))
    except ImportError:
      logging.warn("Distorm not found - expect reduced functionality.")

    config_lib.CONFIG.Set("PyInstaller.pathex", repr(librarypaths))

    try:
      from volatility import session  # pylint: disable=g-import-not-at-top
      _ = session
    except ImportError:
      logging.warn("Volatility Tech Preview was not found. "
                   "Client side Memory Analysis will not be available.")

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Given a generated client config, attempt to check for common errors."""
    errors = []
    location = config.Get("Client.location", context=self.context)
    if not location.startswith("http"):
      errors.append("Bad Client.location specified %s" % location)

    keys = ["Client.executable_signing_public_key",
            "Client.driver_signing_public_key"]
    for key in keys:
      key_data = config.Get(key, default=None, context=self.context)
      if key_data is None:
        errors.append("Missing private %s." % key)
        continue
      if not key_data.startswith("-----BEGIN PUBLIC"):
        errors.append("Invalid private %s" % key)

    certificate = config.Get("CA.certificate", default=None,
                             context=self.context)
    if (certificate is None or
        not certificate.startswith("-----BEGIN CERTIF")):
      errors.append("CA certificate missing from config.")

    for bad_opt in ["Client.certificate", "Client.private_key"]:
      if config.Get(bad_opt, context=self.context, default=""):
        errors.append("Client cert in conf, this should be empty at deployment"
                      " %s" % bad_opt)

    if errors_fatal and errors:
      for error in errors:
        print "Build Config Error: %s" % error
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def MakeBuildDirectory(self):
    """Prepares the build directory."""
    # Create the build directory and let pyinstaller loose on it.
    self.build_dir = config_lib.CONFIG.Get("PyInstaller.build_dir",
                                           context=self.context)
    self.CleanDirectory(self.build_dir)

  def CleanDirectory(self, directory):
    logging.info("Clearing directory %s", directory)
    try:
      shutil.rmtree(directory)
    except OSError:
      pass

    self.EnsureDirExists(directory)

  def EnsureDirExists(self, path):
    try:
      os.makedirs(path)
    except OSError:
      pass

  def BuildWithPyInstaller(self):
    """Use pyinstaller to build a client package."""
    self.CleanDirectory(config_lib.CONFIG.Get("PyInstaller.dist_dir",
                                              context=self.context))
    self.FindLibraryPaths()

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
        config_lib.CONFIG.Get("PyInstaller.dist_dir", context=self.context),
        config_lib.CONFIG.Get("PyInstaller.output_basename",
                              context=self.context))

    subprocess.check_call([sys.executable,
                           config_lib.CONFIG.Get("PyInstaller.path",
                                                 context=self.context),
                           "--distpath",
                           config_lib.CONFIG.Get("PyInstaller.distpath",
                                                 context=self.context),
                           self.spec_file,
                          ])

  def MakeExecutableTemplate(self):
    """Create the executable template.

    The client is build in two phases. First an executable template is created
    with the client binaries contained inside a zip file. Then the installation
    package is created by appending the SFX extractor to this template and
    writing a config file into the zip file.

    This technique allows the client build to be carried out once on the
    supported platform (e.g. windows with MSVS), but the deployable installer
    can be build on any platform which supports python.
    """
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()

    self.EnsureDirExists(os.path.dirname(
        config_lib.CONFIG.Get("ClientBuilder.template_path",
                              context=self.context)))

    output_file = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                        context=self.context)
    logging.info("Generating zip template file at %s", output_file)
    self.MakeZip(self.output_dir, output_file)

  def GetClientConfig(self, context):
    """Generates the client config file for inclusion in deployable binaries."""
    with utils.TempDirectory() as tmp_dir:
      # Make sure we write the file in yaml format.
      filename = os.path.join(
          tmp_dir, config_lib.CONFIG.Get(
              "ClientBuilder.config_filename", context=context))

      new_config = config_lib.CONFIG.MakeNewConfig()
      new_config.SetWriteBack(filename)

      new_config.Set("Client.build_time",
                     str(rdfvalue.RDFDatetime().Now()))

      # Only copy certain sections to the client. We enumerate all
      # defined options and then resolve those from the config in the
      # client's context. The result is the raw option as if the
      # client read our config file.
      for descriptor in sorted(config_lib.CONFIG.type_infos,
                               key=lambda x: x.name):
        if descriptor.name in self.SKIP_OPTION_LIST:
          continue

        if descriptor.section in self.CONFIG_SECTIONS:
          value = config_lib.CONFIG.GetRaw(
              descriptor.name, context=context,
              default=None)

          if value is not None:
            logging.debug("Copying config option to client: %s",
                          descriptor.name)

            new_config.SetRaw(descriptor.name, value)

      new_config.Write()

      self.ValidateEndConfig(new_config)

      return open(filename, "rb").read()

  def GenerateDirectory(self, input_dir=None, output_dir=None,
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
        self.EnsureDirExists(os.path.dirname(out_file))
        self.GenerateFile(in_file, out_file)

  def GenerateFile(self, input_filename=None, output_filename=None):
    """Generates a file from a template, interpolating config values."""
    if input_filename is None:
      input_filename = output_filename + ".in"
    if output_filename[-3:] == ".in":
      output_filename = output_filename[:-3]
    data = open(input_filename, "rb").read()
    print "Generating file %s from %s" % (output_filename, input_filename)

    with open(output_filename, "wb") as fd:
      fd.write(config_lib.CONFIG.InterpolateValue(data, context=self.context))

  def MakeZip(self, input_dir, output_file):
    """Creates a ZIP archive of the files in the input directory.

    Args:
      input_dir: the name of the input directory.
      output_file: the name of the output ZIP archive without extension.
    """
    basename, _ = os.path.splitext(output_file)
    shutil.make_archive(basename, "zip",
                        base_dir=".",
                        root_dir=input_dir,
                        verbose=True)


class WindowsClientBuilder(ClientBuilder):
  """Builder class for the Windows client."""

  def __init__(self, context=None):
    super(WindowsClientBuilder, self).__init__(context=context)
    self.context.append("Target:Windows")

  def BuildNanny(self):
    """Use VS2010 to build the windows Nanny service."""
    logging.info("Copying Nanny build files.")
    self.nanny_dir = os.path.join(self.build_dir, "grr/client/nanny")

    shutil.copytree(config_lib.CONFIG.Get("ClientBuilder.nanny_source_dir",
                                          context=self.context), self.nanny_dir)

    build_type = config_lib.CONFIG.Get(
        "ClientBuilder.build_type", context=self.context)

    vs_arch = config_lib.CONFIG.Get("ClientBuilder.vs_arch", default=None,
                                    context=self.context)

    # We have to set up the Visual Studio environment first and then call
    # msbuild.
    env_script = config_lib.CONFIG.Get("ClientBuilder.vs_env_script",
                                       default=None, context=self.context)

    if vs_arch is None or env_script is None or not os.path.exists(env_script):
      raise RuntimeError("no such Visual Studio script: %s" % env_script)

    subprocess.check_call(
        "cmd /c \"\"%s\" && cd \"%s\" && msbuild /p:Configuration=%s\"" % (
            env_script, self.nanny_dir, build_type))

    shutil.copy(
        os.path.join(self.nanny_dir, vs_arch, build_type, "GRRNanny.exe"),
        os.path.join(self.output_dir,
                     config_lib.CONFIG.Get("Nanny.service_binary_name",
                                           context=self.context)))

  def MakeExecutableTemplate(self):
    """Windows templates also include the nanny."""
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.BuildNanny()

    self.EnsureDirExists(os.path.dirname(
        config_lib.CONFIG.Get("ClientBuilder.template_path",
                              context=self.context)))

    output_file = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                        context=self.context)
    logging.info("Generating zip template file at %s", output_file)
    self.MakeZip(self.output_dir, output_file)

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Windows specific config validations."""
    errors = super(WindowsClientBuilder, self).ValidateEndConfig(
        config, errors_fatal=errors_fatal)

    if config.GetRaw("Logging.path").startswith("/"):
      errors.append("Logging.path starts with /, probably has Unix path. %s" %
                    config["Logging.path"])

    if "Windows\\" in config.GetRaw("Logging.path"):
      errors.append("Windows in Logging.path, you probably want "
                    "%(WINDIR|env) instead")

    if not config["Client.binary_name"].endswith(".exe"):
      errors.append("Missing .exe extension on binary_name %s" %
                    config["Client.binary_name"])

    if not config["Nanny.nanny_binary"].endswith(".exe"):
      errors.append("Missing .exe extension on nanny_binary")

    if errors_fatal and errors:
      for error in errors:
        print "Build Config Error: %s" % error
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def MakeDeployableBinary(self, template_path, output_path=None):
    """Repackage the template zip with the installer."""
    if output_path is None:
      output_path = config_lib.CONFIG.Get("ClientBuilder.output_path",
                                          context=self.context)

    context = self.context + ["Client Context"]
    client_config_content = self.GetClientConfig(context)

    zip_data = cStringIO.StringIO()
    output_zip = zipfile.ZipFile(
        zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    z_template = zipfile.ZipFile(open(template_path, "rb"))

    completed_files = []  # Track which files we've copied already.

    # Change the name of the main binary to the configured name.
    client_bin_name = config_lib.CONFIG.Get(
        "Client.binary_name", context=context)
    try:
      bin_name = z_template.getinfo(client_bin_name)
    except KeyError:
      bin_name = z_template.getinfo("GRR.exe")
    bin_dat = cStringIO.StringIO()
    bin_dat.write(z_template.read(bin_name))
    # Set output to console on binary if needed.
    SetPeSubsystem(bin_dat, console=config_lib.CONFIG.Get(
        "ClientBuilder.console", context=context))

    output_zip.writestr(client_bin_name, bin_dat.getvalue())

    CopyFileInZip(z_template, "%s.manifest" % bin_name.filename, output_zip,
                  "%s.manifest" % client_bin_name)
    completed_files.append(bin_name.filename)
    completed_files.append("%s.manifest" % bin_name.filename)

    # Change the name of the service binary to the configured name.
    service_bin_name = config_lib.CONFIG.Get("Nanny.service_binary_name",
                                             context=context)
    try:
      bin_name = z_template.getinfo(service_bin_name)
    except KeyError:
      bin_name = z_template.getinfo("GRRservice.exe")

    # Set output to console on service binary if needed.
    service_bin_dat = cStringIO.StringIO()
    service_bin_dat.write(z_template.read(bin_name))
    SetPeSubsystem(service_bin_dat,
                   console=config_lib.CONFIG.Get("ClientBuilder.console",
                                                 context=context))

    output_zip.writestr(bin_name, service_bin_dat.getvalue())
    completed_files.append(bin_name.filename)

    # Copy the rest of the files from the template to the new zip.
    for template_file in z_template.namelist():
      if template_file not in completed_files:
        CopyFileInZip(z_template, template_file, output_zip)

    # The zip file comment is used by the self extractor to run
    # the installation script
    output_zip.comment = "$AUTORUN$>%s" % config_lib.CONFIG.Get(
        "ClientBuilder.autorun_command_line", context=context)

    # Add any additional plugins to the deployment binary.
    plugins = (config_lib.CONFIG.Get(
        "ClientBuilder.plugins", context=context) +
               config_lib.CONFIG.Get(
                   "ClientBuilder.installer_plugins", context=context))

    for plugin in plugins:
      output_zip.writestr(os.path.basename(plugin),
                          open(plugin, "rb").read(), zipfile.ZIP_STORED)

    output_zip.writestr(
        config_lib.CONFIG.Get(
            "ClientBuilder.config_filename", context=context),
        client_config_content, compress_type=zipfile.ZIP_STORED)

    output_zip.close()

    self.EnsureDirExists(os.path.dirname(output_path))
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
      SetPeSubsystem(
          stub_data,
          console=config_lib.CONFIG.Get(
              "ClientBuilder.console", context=context))

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

      # Now write the file out. Stub data first.
      fd.write(stub_data.getvalue())

      # Then append the payload zip file.
      fd.write(zip_data.getvalue())

    logging.info("Deployable binary generated at %s", output_path)
    return output_path


class DarwinClientBuilder(ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  def __init__(self, context=None):
    """Initialize the Mac OS X client builder."""
    super(DarwinClientBuilder, self).__init__(context=context)
    self.context.append("Target:Darwin")

  def MakeExecutableTemplate(self):
    """Create the executable template.

    This technique allows the client build to be carried out once on the
    supported platform (e.g. windows with MSVS), but the deployable installer
    can be build on any platform which supports python.
    """
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.BuildInstallerPkg()

  # WARNING: change with care since the PackageMaker files are fragile!
  def BuildInstallerPkg(self):
    """Builds a package (.pkg) using PackageMaker."""
    build_files_dir = os.path.join(self.src_dir, "config", "macosx", "client")
    pmdoc_dir = os.path.join(build_files_dir, "grr.pmdoc")

    plist_dir = config_lib.CONFIG.Get(
        "ClientBuildDarwin.plist_binary_directory", context=self.context)
    plist_name = config_lib.CONFIG.Get("ClientBuildDarwin.plist_filename",
                                       context=self.context)

    out_build_files_dir = build_files_dir.replace(self.src_dir, self.build_dir)
    out_pmdoc_dir = os.path.join(self.build_dir, "%s.pmdoc" % plist_dir)

    self.EnsureDirExists(out_build_files_dir)
    self.EnsureDirExists(out_pmdoc_dir)
    self.EnsureDirExists(config_lib.CONFIG.Get("ClientBuildDarwin.package_dir",
                                               context=self.context))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "grr.plist.in"),
        output_filename=os.path.join(self.build_dir, plist_name))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "index.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "index.xml"))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "01%s.xml" % plist_dir))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "01grr-contents.xml"),
        output_filename=os.path.join(out_pmdoc_dir,
                                     "01%s-contents.xml" % plist_dir))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "02com.xml.in"),
        output_filename=os.path.join(out_pmdoc_dir, "02com.xml"))
    self.GenerateFile(
        input_filename=os.path.join(pmdoc_dir, "02com-contents.xml"),
        output_filename=os.path.join(out_pmdoc_dir, "02com-contents.xml"))

    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "preinstall.sh.in"),
        output_filename=os.path.join(self.build_dir, "preinstall.sh"))
    self.GenerateFile(
        input_filename=os.path.join(build_files_dir, "postinstall.sh.in"),
        output_filename=os.path.join(self.build_dir, "postinstall.sh"))

    # Generate a config file.
    with open(os.path.join(
        config_lib.CONFIG.Get("PyInstaller.build_dir", context=self.context),
        config_lib.CONFIG.Get("PyInstaller.output_basename",
                              context=self.context),
        config_lib.CONFIG.Get("PyInstaller.config_filename",
                              context=self.context)), "wb") as fd:
      fd.write(self.GetClientConfig(("Client Context", "Platform:Darwin")))

    print "Fixing file ownership and permissions"
    command = ["sudo", "chown", "-R", "root:wheel", self.build_dir]

    # Change the owner, group and permissions of the binaries
    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    command = ["sudo", "chmod", "-R", "755", self.build_dir]

    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    pkg = "%s-%s.pkg" % (
        config_lib.CONFIG.Get("ClientBuildDarwin.package_maker_name",
                              context=self.context),
        config_lib.CONFIG.Get("Client.version_string", context=self.context))

    command = [
        config_lib.CONFIG.Get("ClientBuildDarwin.package_maker_path",
                              context=self.context),
        "--doc", out_pmdoc_dir, "--out",
        os.path.join(config_lib.CONFIG.Get("ClientBuildDarwin.package_dir",
                                           context=self.context), pkg)]
    subprocess.call(command)

  def MakeDeployableBinary(self, template_path, output_path=None):
    """This will add the config to the client template."""
    if output_path is None:
      output_path = config_lib.CONFIG.Get("ClientBuilder.output_path",
                                          context=self.context)

    context = self.context + ["Client Context"]
    self.EnsureDirExists(os.path.dirname(output_path))
    client_config_data = self.GetClientConfig(context)
    shutil.copyfile(template_path, output_path)
    zip_file = zipfile.ZipFile(output_path, mode="a")
    zip_info = zipfile.ZipInfo(filename="config.txt")
    zip_file.writestr(zip_info, client_config_data)
    zip_file.close()
    return output_path


class LinuxClientBuilder(ClientBuilder):
  """Builder class for the Linux client."""

  def __init__(self, context=None):
    super(LinuxClientBuilder, self).__init__(context=context)
    self.context.append("Target:Linux")

  def MakeExecutableTemplate(self):
    self.MakeBuildDirectory()
    self.CleanDirectory(config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                              context=self.context))
    self.BuildWithPyInstaller()
    self.BuildInstallerPkg()

  def BuildInstallerPkg(self):
    """This builds the .deb package."""

    dpkg_dir = config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                     context=self.context)
    src_dir = config_lib.CONFIG.Get("PyInstaller.build_root_dir",
                                    context=self.context)
    # Copy files needed for dpkg-buildpackage.
    self.GenerateDirectory(
        os.path.join(src_dir, "grr/config/debian/dpkg_client/"),
        dpkg_dir,
        [("grr-client", config_lib.CONFIG.Get("ClientBuilder.package_name",
                                              context=self.context))])
    # Generate directories for the /usr/sbin link.
    self.EnsureDirExists(os.path.join(
        dpkg_dir, "debian/%s/usr/sbin" %
        config_lib.CONFIG.Get("ClientBuilder.package_name",
                              context=self.context)))

    # Generate the upstart template.
    self.GenerateFile(
        os.path.join(src_dir, "grr/config/debian/upstart/grr-client.conf"),
        os.path.join(dpkg_dir, "debian/%s.upstart" %
                     config_lib.CONFIG.Get("ClientBuilder.package_name",
                                           context=self.context)))

    # Now zip up the template.
    template_path = config_lib.CONFIG.Get("ClientBuilder.template_path",
                                          context=self.context)
    self.EnsureDirExists(os.path.dirname(template_path))
    zf = zipfile.ZipFile(template_path, "w")
    oldwd = os.getcwd()
    os.chdir(config_lib.CONFIG.Get("PyInstaller.dpkg_root",
                                   context=self.context))
    for root, _, files in os.walk("debian"):
      for f in files:
        zf.write(os.path.join(root, f))
    zf.close()
    os.chdir(oldwd)

  def MakeDeployableBinary(self, template_path, output_path=None):
    """This will add the config to the client template and create a .deb."""
    if output_path is None:
      output_path = config_lib.CONFIG.Get("ClientBuilder.output_path",
                                          context=self.context)

    with utils.TempDirectory() as tmp_dir:
      template_dir = os.path.join(tmp_dir, "dist")
      self.EnsureDirExists(template_dir)

      zf = zipfile.ZipFile(template_path)
      for name in zf.namelist():
        dirname = os.path.dirname(name)
        self.EnsureDirExists(os.path.join(template_dir, dirname))
        with open(os.path.join(template_dir, name), "wb") as fd:
          fd.write(zf.read(name))

      # Create a client config.
      client_config_content = self.GetClientConfig(
          ("Client Context", "Platform:Linux"))
      # We need to strip leading /'s or .join will ignore everything that comes
      # before it.
      target_dir = config_lib.CONFIG.Get("ClientBuilder.target_dir",
                                         context=self.context).lstrip("/")
      agent_dir = os.path.join(
          template_dir, "debian",
          config_lib.CONFIG.Get("ClientBuilder.package_name",
                                context=self.context),
          target_dir)

      with open(os.path.join(agent_dir,
                             config_lib.CONFIG.Get(
                                 "ClientBuilder.config_filename",
                                 context=self.context)),
                "wb") as fd:
        fd.write(client_config_content)

      # Set the daemon to executable.
      os.chmod(os.path.join(
          agent_dir, config_lib.CONFIG.Get(
              "Client.binary_name", context=self.context)),
               0755)

      buildpackage_binary = "/usr/bin/dpkg-buildpackage"
      if not os.path.exists(buildpackage_binary):
        print "dpkg-buildpackage not found, unable to repack client."
        return

      oldwd = os.getcwd()
      os.chdir(template_dir)
      command = [buildpackage_binary, "-b"]
      subprocess.call(command)
      os.chdir(oldwd)

      filename_base = config_lib.CONFIG.Get("ClientBuilder.debian_package_base",
                                            context=self.context)
      package_name = "%s%s" % (
          filename_base, config_lib.CONFIG.Get(
              "ClientBuilder.output_extension",
              context=self.context))
      changes = "%s%s" % (filename_base, ".changes")
      changes_output = "%s.changes" % (config_lib.CONFIG.Get(
          "PyInstaller.output_basename", context=self.context))

      self.EnsureDirExists(os.path.dirname(output_path))
      shutil.move(os.path.join(tmp_dir, package_name), output_path)
      shutil.move(os.path.join(tmp_dir, changes),
                  os.path.join(os.path.dirname(output_path), changes_output))
      print "Created package %s" % output_path
      return output_path


def CopyFileInZip(from_zip, from_name, to_zip, to_name=None):
  """Read a file from a ZipFile and write it to a new ZipFile."""
  data = from_zip.read(from_name)
  if to_name is None:
    to_name = from_name
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
