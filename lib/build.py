#!/usr/bin/env python
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""
import cStringIO
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from grr.lib import config_lib
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
    name="PyInstaller.path", must_exist=True,
    default="c:/build/pyinstaller/pyinstaller.py",
    help="Path to the main pyinstaller.py file."))

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
        "%(Client.name)_%(Client.version_string)_%(ClientBuilder.arch).zip"),
    help="The full path to the executable template zip file."))


config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.unzipsfx_stub", must_exist=True,
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

config_lib.DEFINE_string(
    name="ClientBuilder.output",
    default="%(Client.name)_%(Client.version_string)_%(ClientBuilder.arch).exe",
    help="The filename to write the deployable binary.")


class ClientBuilder(object):
  """Abstract client builder class, used by the OS specific implementations."""

  COMPONENT_NAME = "ClientBuilder"

  CONFIG_SECTIONS = ["CA", "Client", "Nanny", "Logging", "ClientBuilder"]

  def __init__(self):
    config_lib.CONFIG.ExecuteSection(self.COMPONENT_NAME)

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

  def MakeDeployableBinary(self, output):
    """Repackage the template zip with the installer."""
    template_path = config_lib.CONFIG["ClientBuilder.template_path"]

    zip_data = cStringIO.StringIO()
    zip_data.write(open(template_path, "rb").read())

    z = zipfile.ZipFile(zip_data, mode="a")

    # The zip file comment is used by the self extractor to run
    # the installation script
    z.comment = "$AUTORUN$>%s" % config_lib.CONFIG[
        "ClientBuilder.autorun_command_line"]

    # Add any additional plugins to the deployment binary.
    for plugin in config_lib.CONFIG["ClientBuilder.plugins"]:
      z.writestr(os.path.basename(plugin),
                 open(plugin, "rb").read(), zipfile.ZIP_STORED)

    z.writestr(config_lib.CONFIG["ClientBuilder.config_filename"],
               self.GetClientConfig(), compress_type=zipfile.ZIP_STORED)

    z.close()

    with open(output, "wb") as fd:
      # First write the installer stub
      stub_data = open(
          config_lib.CONFIG["ClientBuilder.unzipsfx_stub"], "rb").read()

      fd.write(stub_data)

      # Then append the payload zip file.
      fd.write(zip_data.getvalue())

  def GetClientConfig(self):
    """Generates the client config file for inclusion in deployable binaries."""
    fd, new_config_filename = tempfile.mkstemp()
    os.close(fd)

    new_config = config_lib.GrrConfigManager()
    new_config.Initialize(new_config_filename)

    # Only copy certain sections to the client.
    for section, data in config_lib.CONFIG.raw_data.items():
      if section not in self.CONFIG_SECTIONS:
        continue

      new_config.raw_data[section] = data

    new_config.Write()

    try:
      with open(new_config_filename, "rb") as fd:
        return fd.read()

    finally:
      os.unlink(new_config_filename)

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
  CONFIG_SECTIONS = (ClientBuilder.CONFIG_SECTIONS +
                     ["NannyWindows", "ClientBuildWindows"])

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


# TODO(user): Make this work again
class DarwinClientBuilder(ClientBuilder):
  """Builder class for the Mac OS X (Darwin) client."""

  def __init__(self, source, build_files_dir, build_dir, build_time,
               pyinstaller, config, architecture, packagemaker):
    """Initialize the Mac OS X client builder.

    Args:
      source: the path to the source directory.
      build_files_dir: the (root) directory that contains the (input) build
                       file.
      build_dir: the build (root) directory.
      build_time: string containing the build time.
      pyinstaller: the location of the pyinstaller.py script.
      config: the configuration (config_lib.ConfigManager).
      architecture: string containing the architecture to build for,
                    e.g. i386 or amd64.
      packagemaker: string containing the location of the PackageMaker
                    executable.
    """
    super(DarwinClientBuilder, self).__init__(
        source, build_files_dir, build_dir, build_time, pyinstaller, config,
        architecture)

    self.installers = os.path.join(
        self.conf["Temp.source"], "executables", "macosx", "templates",
        "packagemaker")

    self.packagemaker = packagemaker

  def BuildInstallerLaunchDaemonsPlist(self):
    """Builds a LaunchDaemons plist."""
    build_files_dir = os.path.join(self.build_files_dir, "macosx", "client")

    plist_file = os.path.join(build_files_dir, "grr.plist")
    self.GenerateFile(plist_file)
    plist_dest = "%(ClientBuildDarwin.plist_filename)s" % self.conf
    shutil.copy(plist_file, os.path.join(self.conf["Temp.dist_dir"],
                                         plist_dest))

  # WARNING: change with care since the PackageMaker files are fragile!
  def BuildInstallerPkg(self, package_dir, output_dir):
    """Builds a package (.pkg) using PackageMaker."""
    build_files_dir = os.path.join(self.build_files_dir, "macosx", "client")

    pmdoc_dir = os.path.join(build_files_dir, "grr.pmdoc")

    self.GenerateFile(os.path.join(pmdoc_dir, "index.xml"))
    self.GenerateFile(os.path.join(pmdoc_dir, "01grr.xml"))
    self.GenerateFile(os.path.join(pmdoc_dir, "02com.xml"))

    self.GenerateFile(os.path.join(build_files_dir, "preinstall.sh"))
    self.GenerateFile(os.path.join(build_files_dir, "postinstall.sh"))

    filename = os.path.join(pmdoc_dir,
                            "01%(ClientBuildDarwin.plist_binary_directory)s.xml"
                            % self.conf)
    if not os.path.exists(filename):
      shutil.copy(os.path.join(pmdoc_dir, "01grr.xml"), filename)

    filename = os.path.join(
        pmdoc_dir, "01%(ClientBuildDarwin.plist_binary_directory)s-contents.xml"
        % self.conf)
    if not os.path.exists(filename):
      shutil.copy(os.path.join(pmdoc_dir, "01grr-contents.xml"), filename)

    filename = os.path.join(
        pmdoc_dir, "02%(ClientBuildDarwin.plist_label_prefix)s.xml" % self.conf)
    if not os.path.exists(filename):
      shutil.copy(os.path.join(pmdoc_dir, "02com.xml"), filename)

    filename = os.path.join(
        pmdoc_dir, "02%(ClientBuildDarwin.plist_label_prefix)s-contents.xml"
        % self.conf)
    if not os.path.exists(filename):
      shutil.copy(os.path.join(pmdoc_dir, "02com-contents.xml"), filename)

    print "Fixing file ownership and permissions"
    command_prefix = "sudo chown -R root:wheel"

    # Change the owner and group of the launctl plist
    command = "%s %s" % (command_prefix, os.path.join(
        self.conf["Temp.dist_dir"], "%(ClientBuildDarwin.plist_filename)s"
        % self.conf))
    print "Running: %s" %(command)
    subprocess.call(command, shell=True)

    # Change the owner, group and permissions of the binaries
    command = "%s %s" % (command_prefix, output_dir)
    print "Running: %s" %(command)
    subprocess.call(command, shell=True)

    command_prefix = "sudo chmod -R 755"

    command = "%s %s" % (command_prefix, output_dir)
    print "Running: %s" %(command)
    subprocess.call(command, shell=True)

    print "Creating: %(ClientBuildDarwin.packagemaker_name)s.pkg" % self.conf
    # Need shell=True here
    subprocess.call(
        "%s --doc %s --out %s" % (self.packagemaker, pmdoc_dir, package_dir),
        shell=True)

  def BuildInstallerDmg(self, disk_image_path, package_dir):
    """Builds a disk image (.dmg) using hdiutil."""
    print "Creating: %(ClientBuildDarwin.packagemaker_name)s.dmg" % (self.conf)
    # Need shell=True here
    subprocess.call(
        "hdiutil create %s -srcfolder %s -fs HFS+" % (
            disk_image_path, package_dir), shell=True)
