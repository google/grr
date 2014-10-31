#!/usr/bin/env python
"""Configuration parameters for client builder and server packaging."""
import os
import time

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info


# Windows Memory driver information.
config_lib.DEFINE_string("MemoryDriver.driver_service_name",
                         "Pmem",
                         "The SCCM service name for the driver.")

config_lib.DEFINE_string("MemoryDriver.driver_display_name",
                         "%(Client.name) Pmem",
                         "The SCCM display name for the driver.")

config_lib.DEFINE_list("MemoryDriver.driver_files", [],
                       "The default drivers to use.")

config_lib.DEFINE_list("MemoryDriver.aff4_paths", [],
                       "The AFF4 paths to the driver objects.")

config_lib.DEFINE_string("MemoryDriver.device_path", r"\\\\.\\pmem",
                         "The device path which the client will open after "
                         "installing this driver.")

config_lib.DEFINE_string("MemoryDriver.service_name", "pmem",
                         "The name of the service created for "
                         "the driver (Windows).")

config_lib.DEFINE_string("MemoryDriver.display_name", "%(service_name)",
                         "The display name of the service created for "
                         "the driver (Windows).")

config_lib.DEFINE_option(type_info.RDFValueType(
    rdfclass=rdfvalue.RDFURN,
    name="Config.aff4_root", default="aff4:/config/",
    description=("The path where the configs are stored in the aff4 "
                 "namespace.")))

config_lib.DEFINE_option(type_info.RDFValueType(
    rdfclass=rdfvalue.RDFURN,
    name="Config.python_hack_root",
    default="%(Config.aff4_root)/python_hacks",
    description=("The path where python hacks are stored in the aff4 "
                 "namespace.")))

# Executables must be signed and uploaded to their dedicated AFF4 namespace.
config_lib.DEFINE_option(type_info.RDFValueType(
    rdfclass=rdfvalue.RDFURN,
    name="Executables.aff4_path",
    description="The aff4 path to signed executables.",
    default="%(Config.aff4_root)/executables/%(Client.platform)"))

config_lib.DEFINE_string(
    name="Executables.installer",
    default=("%(Executables.aff4_path)/installers/"
             "%(ClientBuilder.output_basename)"
             "%(ClientBuilder.output_extension)"),
    help="The location of the generated installer in the config directory.")


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

config_lib.DEFINE_string(
    name="PyInstaller.spec",
    help="The spec file contents to use for building the client.",
    default=r"""
# By default build in one dir mode.
a = Analysis\(
    ["%(%(ClientBuilder.source)|unixpath)/grr/client/client.py"],
    hiddenimports=[],
    hookspath=None\)

# Remove some optional libraries that would be packed but serve no purpose.
for prefix in ["IPython"]:
  for collection in [a.binaries, a.datas, a.pure]:
    for item in collection[:]:
      if item[0].startswith\(prefix\):
        collection.remove\(item\)

pyz = PYZ\(
    a.pure\)
exe = EXE\(
    pyz,
    a.scripts,
    exclude_binaries=1,
    name='build/grr-client',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    version='%(PyInstaller.build_dir)/version.txt',
    icon='%(PyInstaller.build_dir)/grr.ico'\)

coll = COLLECT\(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='grr-client'
\)
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
        [
    StringStruct\('CompanyName',
    "<---------------- Client.company_name ------------------->"\),

    StringStruct\('FileDescription',
    "<---------------- Client.description ------------------->"\),

    StringStruct\('FileVersion',
    "<---------------- Client.version_string ------------------->"\),

    StringStruct\('ProductName',
    "<---------------- Client.name ------------------->"\),

    StringStruct\('OriginalFilename',
    "<---------------- ClientBuilder.package_name ------------------->"\),
        ]\),
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
    name="Client.prefix", default="",
    help="A prefix for the client name, usually dbg_ for debug builds.")

config_lib.DEFINE_string(
    name="ClientBuilder.output_basename",
    default=("%(Client.prefix)%(Client.name)_"
             "%(Client.version_string)_%(Client.arch)"),
    help="The base name of the output package.")

# Windows client specific options.
config_lib.DEFINE_bool(
    "ClientBuilder.console", default=False,
    help="Should the application be built as a console program. "
    "This aids debugging in windows.")

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

config_lib.DEFINE_string(
    name="PyInstaller.template_basename",
    default=("grr-client_%(Client.version_string)_%(Client.arch)"),
    help="The template name of the output package.")

config_lib.DEFINE_string(
    name="PyInstaller.template_filename",
    default=(
        "%(PyInstaller.template_basename)%(ClientBuilder.template_extension)"),
    help="The template file name of the output package.")

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.template_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)/templates/"
        "%(PyInstaller.template_filename)"),
    help="The full path to the executable template file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.executables_path", must_exist=False,
    default="%(ClientBuilder.source)/grr/executables",
    help="The path to the grr executables directory."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.output_filename", must_exist=False,
    default=(
        "%(ClientBuilder.output_basename)%(ClientBuilder.output_extension)"),
    help="The filename of the generated installer file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.output_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)"
        "/installers/%(ClientBuilder.output_filename)"),
    help="The full path to the generated installer file."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.generated_config_path", must_exist=False,
    default=(
        "%(ClientBuilder.executables_path)/%(Client.platform)"
        "/config/%(ClientBuilder.output_basename).yaml"),
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
    name="ClientBuilder.rpm_build_time",
    default=time.strftime("%a %b %d %Y", time.gmtime()),
    help="The build time put into the rpm package. Needs to be formatted"
    " according to the rpm specs.")

config_lib.DEFINE_string(
    name="ClientBuilder.debian_version",
    default="%(Client.version_numeric)-1",
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


config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.source", must_exist=False,
    default=os.path.normpath(__file__ + "/../../.."),
    help="The location of the source files."))

config_lib.DEFINE_option(type_info.PathTypeInfo(
    name="ClientBuilder.executables_dir",
    default="%(ClientBuilder.source)/grr/executables",
    help="The directory that contains the executables."))

config_lib.DEFINE_string(
    name="ClientBuilder.build_time",
    default=time.ctime(),
    help="Time of build to embed into binary.")

config_lib.DEFINE_string(
    "ClientBuilder.packagemaker",
    default=("/Developer/Applications/Utilities/PackageMaker.app/Contents"
             "/MacOS/PackageMaker"),
    help="Location of the PackageMaker executable.")
