#!/usr/bin/env python
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""
import cStringIO
import logging
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

from grr.client import conf as flags

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import type_info


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
    default="c:/build/pyinstaller/pyinstaller.py",
    help="Path to the main pyinstaller.py file."))

config_lib.DEFINE_bool(
    "PyInstaller.console", default=True,
    help="Should the application be built as a console program.")

config_lib.DEFINE_option(PathTypeInfo(
    name="PyInstaller.support_path", must_exist=True,
    default="%(ClientBuilder.source)/grr/config/pyinstaller/client",
    help="Path that contains pyinstaller support files."))

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
    console=%(PyInstaller.console),
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
        StringStruct\('OriginalFilename', '%(Client.name)' \)]\),
      ]\),
  VarFileInfo\([VarStruct\('Translation', [1033, 1200]\)]\)
  ]
\)
""")

config_lib.DEFINE_string(
    "PyInstaller.icon",
    "%(%(ClientBuilder.source)/grr/gui/static/images/grr.ico|file)",
    "The icon file contents to use for building the client.")

config_lib.DEFINE_string(
    "PyInstaller.build_dir",
    "./build",
    "The path to the build directory.")

config_lib.DEFINE_string(
    name="PyInstaller.output_basename",
    default="%(Client.name)_%(Client.version_string)_%(ClientBuilder.arch)",
    help="The base name of the output package.")


config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuildWindows.nanny_source_dir", must_exist=True,
    default="%(ClientBuilder.source)/grr/client/nanny/",
    help="Path to the windows nanny VS solution file."))

config_lib.DEFINE_choice(
    name="ClientBuildWindows.build_type",
    default="Release",
    choices=["Release", "Debug"],
    help="Type of build (Debug, Release)")


config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.template_path", must_exist=False,
    default=(
        "%(ClientBuilder.source)/grr/executables/%(ClientBuilder.platform)"
        "/templates/%(ClientBuilder.arch)/%(Client.version_string)/"
        "%(Client.name)_%(Client.version_string)_%(ClientBuilder.arch)."
        "%(ClientBuilder.template_extension)"),
    help="The full path to the executable template file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.output_path", must_exist=False,
    default=(
        "%(ClientBuilder.source)/grr/executables/%(ClientBuilder.platform)"
        "/installers/%(ClientBuilder.arch)/%(Client.version_string)/"
        "%(Client.name)_%(Client.version_string)_%(ClientBuilder.arch)."
        "%(ClientBuilder.output_extension)"),
    help="The full path to the executable template file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.generated_config_path", must_exist=False,
    default=(
        "%(ClientBuilder.source)/grr/executables/%(ClientBuilder.platform)"
        "/config/%(Client.name)_%(Client.version_string)_"
        "%(ClientBuilder.arch).conf"),
    help="The full path to where we write a generated config."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.unzipsfx_stub", must_exist=False,
    default=("%(ClientBuilder.source)/grr/executables/%(ClientBuilder.platform)"
             "/templates/unzipsfx/unzipsfx-%(ClientBuilder.arch).exe"),
    help="The full path to the zip self extracting stub."))

config_lib.DEFINE_string(
    name="ClientBuilder.config_filename",
    default="%(Client.binary_name).conf",
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

config_lib.DEFINE_bool(
    name="ClientBuilder.zip_sfx_console_enabled",
    default=False,
    help="If true, when repacking we will modify the sfx zip binary to be a "
    "console mode application so it will output its progress.")


class ClientBuilder(object):
  """Abstract client builder class, used by the OS specific implementations."""

  COMPONENT_NAME = "ClientBuilder"
  CONFIG_SECTIONS = ["CA", "Client", "Logging"]

  BUILD_OPTION_MAP = [
      ("ClientBuilder.installer_plugins", "Installer.plugins"),
      ("ClientBuilder.installer_logfile", "Installer.logfile"),
      ("ClientBuilder.client_logging_path", "Logging.path"),
      ("ClientBuilder.client_logging_filename", "Logging.filename"),
      ("ClientBuilder.client_logging_engines", "Logging.engines"),
      ("ClientBuilder.plugins", "Client.plugins")]

  # Config options that should never make it to a deployable binary.
  SKIP_OPTION_LIST = ["Client.certificate", "Client.private_key"]

  def FindLibraryPaths(self):
    """Figure out where distorm is so PyInstaller can find it."""
    logging.info("Searching for external libraries.")
    librarypaths = ["."]
    try:
      import distorm3  # pylint: disable=g-import-not-at-top
      librarypaths.append(os.path.dirname(distorm3.__file__))
    except ImportError:
      logging.warn("Distorm not found - expect reduced functionality.")

    config_lib.CONFIG.SetEnv("PyInstaller.pathex", repr(librarypaths))

    try:
      from volatility import session  # pylint: disable=g-import-not-at-top
      _ = session
    except ImportError:
      logging.warn("Volatility Tech Preview was not found. "
                   "Client side Memory Analysis will not be available.")

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Given a generated client config, attempt to check for common errors."""
    errors = []
    if not config["Client.location"].startswith("http"):
      errors.append("Bad Client.location specified %s" %
                    config["Client.location"])

    keys = ["Client.executable_signing_public_key",
            "Client.driver_signing_public_key"]
    for key in keys:
      if not config[key].startswith("-----BEGIN PUBLIC"):
        errors.append("Missing or corrupt private %s" % key)

    if not config["CA.certificate"].startswith("-----BEGIN CERTIF"):
      errors.append("CA certificate missing from config.")

    for bad_opt in ["Client.certificate", "Client.private_key"]:
      if config[bad_opt] is not None:
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
    self.build_dir = config_lib.CONFIG["PyInstaller.build_dir"]

    logging.info("Clearing build directory %s", self.build_dir)
    try:
      shutil.rmtree(self.build_dir)
    except OSError:
      pass

    self.EnsureDirExists(self.build_dir)

  def EnsureDirExists(self, path):
    try:
      os.makedirs(path)
    except OSError:
      pass

  def BuildWithPyInstaller(self):
    """Use pyinstaller to build a client package."""
    self.FindLibraryPaths()

    logging.info("Copying pyinstaller support files")
    self.spec_file = os.path.join(self.build_dir, "grr.spec")

    with open(self.spec_file, "wb") as fd:
      fd.write(config_lib.CONFIG["PyInstaller.spec"])

    with open(os.path.join(self.build_dir, "version.txt"), "wb") as fd:
      fd.write(config_lib.CONFIG["PyInstaller.version"])

    with open(os.path.join(self.build_dir, "grr.ico"), "wb") as fd:
      fd.write(config_lib.CONFIG["PyInstaller.icon"])

    # We expect the onedir output at this location.
    self.output_dir = os.path.join(
        config_lib.CONFIG["PyInstaller.build_dir"],
        config_lib.CONFIG["PyInstaller.output_basename"])

    subprocess.check_call([sys.executable,
                           config_lib.CONFIG["PyInstaller.path"],
                           self.spec_file])

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
        config_lib.CONFIG["ClientBuilder.template_path"]))

    output_file = config_lib.CONFIG["ClientBuilder.template_path"]
    logging.info("Generating zip template file at %s", output_file)
    self.MakeZip(self.output_dir, output_file)

  def GetClientConfig(self):
    """Generates the client config file for inclusion in deployable binaries."""
    new_config = config_lib.GrrConfigManager()
    new_config.Initialize(data="")

    config_lib.CONFIG.Set("Client.build_time", str(rdfvalue.RDFDatetime()))

    # Only copy certain sections to the client.
    for section, data in config_lib.CONFIG.raw_data.items():
      if section not in self.CONFIG_SECTIONS:
        continue
      new_config.raw_data[section] = data

    # Copy config options from the ClientBuilder to the resulting config.
    for src_option, target_option in self.BUILD_OPTION_MAP:
      if config_lib.CONFIG[src_option]:
        config_lib.CONFIG.SetRaw(target_option,
                                 config_lib.CONFIG.GetRaw(src_option))

    # Remove any unwanted options as the last thing we do.
    for item in self.SKIP_OPTION_LIST:
      section, option = item.split(".", 1)
      if section in new_config.raw_data:
        if option in new_config.raw_data[section]:
          del new_config.raw_data[section][option]

    fd = cStringIO.StringIO()
    new_config.WriteToFD(fd)
    fd.seek(0)
    return fd.read()

  def BackupClientConfig(self, output_path):
    new_config_data = self.GetClientConfig()

    if output_path:
      if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))
      with open(output_path, mode="wb") as fd:
        fd.write(new_config_data)
    return output_path

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

  COMPONENT_NAME = "ClientBuildWindows"

  # Additional sections to be copied to the windows client configuration file.
  CONFIG_SECTIONS = (ClientBuilder.CONFIG_SECTIONS + ["NannyWindows"])

  def BuildNanny(self):
    """Use VS2010 to build the windows Nanny service."""
    logging.info("Copying Nanny build files.")
    self.nanny_dir = os.path.join(self.build_dir, "grr/client/nanny")

    shutil.copytree(config_lib.CONFIG["ClientBuildWindows.nanny_source_dir"],
                    self.nanny_dir)

    if config_lib.CONFIG["ClientBuilder.arch"] == "i386":
      vs_arch = "Win32"
      env_script = os.path.join(
          config_lib.CONFIG["ClientBuildWindows.vs_dir"],
          "VC", "bin", "vcvars32.bat")

    elif config_lib.CONFIG["ClientBuilder.arch"] == "amd64":
      vs_arch = "x64"
      env_script = os.path.join(
          config_lib.CONFIG["ClientBuildWindows.vs_dir"],
          "VC", "bin", "amd64", "vcvars64.bat")

    else:
      raise RuntimeError("unsupported architecture: %s" %
                         self.conf["Temp.arch"])

    # if cmd cannot find env_script and it contains spaces cmd will only show
    # the part up to space.
    if not os.path.exists(env_script):
      raise RuntimeError("no such Visual Studio script: %s" % env_script)

    build_type = config_lib.CONFIG["ClientBuildWindows.build_type"]
    subprocess.check_call(
        "cmd /c \"\"%s\" && cd \"%s\" && msbuild /p:Configuration=%s\"" % (
            env_script, self.nanny_dir, build_type))

    shutil.copy(
        os.path.join(self.nanny_dir, vs_arch, build_type, "GRRNanny.exe"),
        os.path.join(self.output_dir,
                     config_lib.CONFIG["NannyWindows.service_binary_name"]))

  def MakeExecutableTemplate(self):
    """Windows templates also include the nanny."""
    self.MakeBuildDirectory()
    self.BuildWithPyInstaller()
    self.BuildNanny()

    self.EnsureDirExists(os.path.dirname(
        config_lib.CONFIG["ClientBuilder.template_path"]))

    output_file = config_lib.CONFIG["ClientBuilder.template_path"]
    logging.info("Generating zip template file at %s", output_file)
    self.MakeZip(self.output_dir, output_file)

  def ValidateEndConfig(self, config, errors_fatal=True):
    """Windows specific config validations."""
    errors = super(WindowsClientBuilder, self).ValidateEndConfig(
        config, errors_fatal=errors_fatal)

    if config.GetRaw("Logging.path").startswith("/"):
      errors.append("Logging.path starts with /, probably has Unix path. %s" %
                    config["Logging.path"])
    if "Windows\\" in config["Logging.path"]:
      errors.append("Windows in Logging.path, you probably want "
                    "%(WINDIR|env) instead")
    if not config["Client.binary_name"].endswith(".exe"):
      errors.append("Missing .exe extension on binary_name %s" %
                    config["Client.binary_name"])
    if not config["NannyWindows.nanny_binary"].endswith(".exe"):
      errors.append("Missing .exe extension on nanny_binary")

    if errors_fatal and errors:
      for error in errors:
        print "Build Config Error: %s" % error
      raise RuntimeError("Bad configuration generated. Terminating.")
    else:
      return errors

  def MakeDeployableBinary(self, template_path, output_path):
    """Repackage the template zip with the installer."""
    client_config_content = self.GetClientConfig()

    # Attempt to load and validate our generated config to detect any errors.
    tmp_conf = tempfile.mkstemp(suffix="conf")[1]
    config_out = self.BackupClientConfig(output_path=tmp_conf)
    tmp_client_config = config_lib.LoadConfig(config_obj=None,
                                              config_file=config_out)
    errors = self.ValidateEndConfig(tmp_client_config, errors_fatal=True)
    os.unlink(tmp_conf)
    for error in errors:
      logging.error(error)

    zip_data = cStringIO.StringIO()
    z = zipfile.ZipFile(zip_data, mode="w", compression=zipfile.ZIP_DEFLATED)

    z_template = zipfile.ZipFile(open(template_path, "rb"))

    completed_files = []  # Track which files we've copied already.

    # Change the name of the main binary to the configured name.
    client_bin_name = config_lib.CONFIG["Client.binary_name"]
    try:
      bin_name = z_template.getinfo(client_bin_name)
    except KeyError:
      bin_name = z_template.getinfo("GRR.exe")
    bin_dat = cStringIO.StringIO()
    bin_dat.write(z_template.read(bin_name))
    # Set output to console on binary if needed.
    SetPeSubsystem(bin_dat, console=config_lib.CONFIG["PyInstaller.console"])
    z.writestr(client_bin_name, bin_dat.getvalue())
    CopyFileInZip(z_template, "%s.manifest" % bin_name.filename, z,
                  "%s.manifest" % client_bin_name)
    completed_files.append(bin_name.filename)
    completed_files.append("%s.manifest" % bin_name.filename)

    # Change the name of the service binary to the configured name.
    service_bin_name = config_lib.CONFIG["NannyWindows.service_binary_name"]
    try:
      bin_name = z_template.getinfo(service_bin_name)
    except KeyError:
      bin_name = z_template.getinfo("GRRservice.exe")
    CopyFileInZip(z_template, bin_name, z, service_bin_name)
    completed_files.append(bin_name.filename)

    # Copy the rest of the files from the template to the new zip.
    for template_file in z_template.namelist():
      if template_file not in completed_files:
        CopyFileInZip(z_template, template_file, z)

    # The zip file comment is used by the self extractor to run
    # the installation script
    z.comment = "$AUTORUN$>%s" % config_lib.CONFIG[
        "ClientBuilder.autorun_command_line"]

    # Add any additional plugins to the deployment binary.
    plugins = (config_lib.CONFIG["ClientBuilder.plugins"] +
               config_lib.CONFIG["ClientBuilder.installer_plugins"])

    for plugin in plugins:
      z.writestr(os.path.basename(plugin),
                 open(plugin, "rb").read(), zipfile.ZIP_STORED)

    # Add any additional plugins to the deployment binary.
    for plugin in config_lib.CONFIG["ClientBuilder.plugins"]:
      z.writestr(os.path.basename(plugin),
                 open(plugin, "rb").read(), zipfile.ZIP_STORED)

    z.writestr(config_lib.CONFIG["ClientBuilder.config_filename"],
               client_config_content, compress_type=zipfile.ZIP_STORED)

    z.close()

    self.EnsureDirExists(os.path.dirname(output_path))
    with open(output_path, "wb") as fd:
      # First write the installer stub
      stub_data = cStringIO.StringIO()
      stub_raw = open(
          config_lib.CONFIG["ClientBuilder.unzipsfx_stub"], "rb").read()

      # Check stub has been compiled with the requireAdministrator manifest.
      if "level=\"requireAdministrator" not in stub_raw:
        raise RuntimeError("Bad unzip binary in use. Not compiled with the"
                           "requireAdministrator manifest option.")

      stub_data.write(stub_raw)

      # If in verbose mode, modify the unzip bins PE header to run in console
      # mode for easier debugging.
      SetPeSubsystem(
          stub_data,
          console=config_lib.CONFIG["ClientBuilder.zip_sfx_console_enabled"])

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

  COMPONENT_NAME = "ClientBuildDarwin"

  # Only these sections will be copied to the deployable binary.
  CONFIG_SECTIONS = (ClientBuilder.CONFIG_SECTIONS +
                     ["ClientDarwin", "Nanny"])

  def __init__(self):
    """Initialize the Mac OS X client builder."""
    super(DarwinClientBuilder, self).__init__()
    self.build_dir = config_lib.CONFIG["ClientBuildDarwin.build_dest_dir"]
    self.src_dir = config_lib.CONFIG["ClientBuildDarwin.build_src_dir"]

  def GenerateFile(self, input_filename=None, output_filename=None):
    """Generates a file from a template, interpolating config values."""
    if input_filename is None:
      input_filename = output_filename + ".in"
    data = open(input_filename, "rb").read()
    print "Generating file %s from %s" % (output_filename, input_filename)

    with open(output_filename, "wb") as fd:
      fd.write(config_lib.CONFIG.InterpolateValue(data))

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

    plist_dir = config_lib.CONFIG["ClientBuildDarwin.plist_binary_directory"]
    plist_name = config_lib.CONFIG["ClientBuildDarwin.plist_filename"]

    out_build_files_dir = build_files_dir.replace(self.src_dir, self.build_dir)
    out_pmdoc_dir = os.path.join(self.build_dir, "%s.pmdoc" % plist_dir)

    self.EnsureDirExists(out_build_files_dir)
    self.EnsureDirExists(out_pmdoc_dir)
    self.EnsureDirExists(config_lib.CONFIG["ClientBuildDarwin.package_dir"])

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
        config_lib.CONFIG["PyInstaller.build_dir"],
        config_lib.CONFIG["PyInstaller.output_basename"],
        config_lib.CONFIG["PyInstaller.config_name"]), "wb") as fd:
      fd.write(self.GetClientConfig())

    print "Fixing file ownership and permissions"
    command = ["sudo", "chown", "-R", "root:wheel", self.build_dir]

    # Change the owner, group and permissions of the binaries
    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    command = ["sudo", "chmod", "-R", "755", self.build_dir]

    print "Running: %s" % " ".join(command)
    subprocess.call(command)

    pkg = "%s-%s.pkg" % (
        config_lib.CONFIG["ClientBuildDarwin.package_maker_name"],
        config_lib.CONFIG["Client.version_string"])

    command = [
        config_lib.CONFIG["ClientBuildDarwin.package_maker_path"],
        "--doc", out_pmdoc_dir, "--out",
        os.path.join(config_lib.CONFIG["ClientBuildDarwin.package_dir"], pkg)]
    subprocess.call(command)

  def MakeDeployableBinary(self, template_path, output_path):
    """This will add the config to the client template."""
    self.EnsureDirExists(os.path.dirname(output_path))
    client_config_data = self.GetClientConfig()
    shutil.copyfile(template_path, output_path)
    zip_file = zipfile.ZipFile(output_path, mode="a")
    zip_info = zipfile.ZipInfo(filename="config.txt")
    zip_file.writestr(zip_info, client_config_data)
    zip_file.close()
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


def GetTemplateVersions(executables_dir="./executables"):
  """Yields a list of templates based on filename regex.

  Args:
    executables_dir: Directory containing template directory structure.

  Yields:
    Tuples of template_path, platform, name, version, arch
  """
  template_re = re.compile("^(?P<name>.*)_(?P<version>.*)_"
                           r"(?P<arch>amd64|i386)\.(zip|template)$")

  for plat in ["windows", "linux", "darwin"]:
    tmpl_dir = os.path.join(executables_dir, plat.lower())
    for dirpath, _, filenames in os.walk(tmpl_dir):
      for filename in filenames:
        full_path = os.path.join(dirpath, filename)
        tmatch = template_re.match(filename)
        if tmatch:
          name, version, arch, _ = tmatch.groups()
          yield (full_path, plat, name, version, arch)


def RepackAllBinaries(executables_dir="./executables"):
  """Repack binaries based on the configuration.

  Args:
    executables_dir: Base directory where templates are kept.

  Returns:
    A list of tuples containing (output_file, platform, architecture)
  """
  built = []
  for dat in GetTemplateVersions(executables_dir):
    # Clean out the config in case others have polluted it.

    tmpl_path, plat, name, version, arch = dat
    print "\n## Repacking %s %s %s %s client" % (name, plat, arch, version)

    n_name = config_lib.CONFIG["Client.name"]
    plat = plat.title()
    if plat == "Windows":
      builder = WindowsClientBuilder()
      final_filename = "%s_%s_%s.exe" % (n_name, version, arch)
    elif plat == "Darwin":
      builder = DarwinClientBuilder()
      final_filename = "%s_%s_%s.pkg" % (n_name, version, arch)
    else:
      logging.error("No currently supported builder for platform %s", plat)
      continue

    # Modify the running config to be clean, and use the builders environment.
    config_lib.LoadConfig(config_lib.CONFIG, config_file=flags.FLAGS.config,
                          secondary_configs=flags.FLAGS.secondary_configs,
                          component_section=builder.COMPONENT_NAME,
                          execute_sections=flags.FLAGS.config_execute)

    # Setup the config for the build.
    config_lib.CONFIG.Set("ClientBuilder.platform", plat.lower())
    config_lib.CONFIG.Set("ClientBuilder.arch", arch)
    config_lib.CONFIG.Set("ClientBuilder.template_path", tmpl_path)
    config_lib.CONFIG.Set("Client.version_string", version)

    plat = plat.lower()
    installer_path = os.path.join(executables_dir, plat, "installers")
    if not os.path.exists(installer_path):
      os.makedirs(installer_path)
    installer_path = os.path.join(installer_path, final_filename)

    template_path = config_lib.CONFIG["ClientBuilder.template_path"]
    config_out = builder.BackupClientConfig(
        output_path=config_lib.CONFIG["ClientBuilder.generated_config_path"])
    out = builder.MakeDeployableBinary(template_path, installer_path)
    built.append((out, config_out, plat, arch))
    print "Packed to %s" % out

    # Restore the config back to its previous state.
    startup.ConfigInit()

  return built
