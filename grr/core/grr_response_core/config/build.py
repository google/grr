#!/usr/bin/env python
"""Configuration parameters for client builder and server packaging."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import time

from grr_response_core.lib import config_lib
from grr_response_core.lib import type_info

config_lib.DEFINE_string(
    name="ClientBuilder.output_extension",
    default=None,
    help="The file extension for the client (OS dependent).")

config_lib.DEFINE_string(
    name="ClientBuilder.package_dir", default=None, help="OSX package name.")

config_lib.DEFINE_string(
    "ClientBuilder.private_config_validator_class",
    default=None,
    help="Set this to a class name that sanity checks your client "
    "config at repacking time.")

config_lib.DEFINE_bool(
    "Client.fleetspeak_enabled", False,
    "Whether the client uses Fleetspeak to communicate "
    "with the server.")

config_lib.DEFINE_bool(
    "ClientBuilder.fleetspeak_enabled", False,
    "Whether the client will use Fleetspeak to communicate "
    "with the server.")

config_lib.DEFINE_string(
    "Client.fleetspeak_service_name", "FleetspeakService",
    "Name of the Fleetspeak Windows service. Used to restart the Fleetspeak "
    "service during GRR client installation.")

config_lib.DEFINE_string(
    "ClientBuilder.client_path",
    default="grr_response_client.client",
    help="Full module path for GRR client's main file.")

config_lib.DEFINE_string(
    "ClientBuilder.fleetspeak_service_dir", "/etc/fleetspeak/services",
    "Directory where Fleetspeak expects service configs to be. Only applies "
    "if ClientBuilder.fleetspeak_enabled is true.")

config_lib.DEFINE_string(
    "ClientBuilder.fleetspeak_plist_path", None,
    "Path where the Fleetspeak client installs its plist file. Only applies "
    "if ClientBuilder.fleetspeak_enabled is true.")

config_lib.DEFINE_string(
    "ClientBuilder.fleetspeak_config_path",
    "%(install_data/fleetspeak/%(Client.platform)/"
    "grr_service_config.txt.in@grr-response-core|resource)",
    "Path to GRR's Fleetspeak service configuration.")


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
config_lib.DEFINE_string(
    name="PyInstaller.spec",
    help="The spec file contents to use for building the client.",
    default=r"""
import capstone
import glob
import os
import platform
import sys

# By default build in one dir mode.
client_path = r"%(%(%(ClientBuilder.client_path)|module_path)|fixpathsep)"

CHIPSEC_IMPORTS = []
if platform.system\(\).lower\(\) == 'linux':
  # Note: the order here is important. Chipsec's linux.helper module expects
  # chipsec.helper.oshelper to be partially loaded by the time it gets imported,
  # otherwise a circular dependency is triggered: chipsec.helper.oshelper
  # tries to import chipsec.helper.linux.helper which itself imports
  # chipsec.helper.oshelper \(see
  # https://github.com/chipsec/chipsec/blob/5102229c6aca6ac0323b6cf8cf4c4fbcce9259a9/chipsec/helper/oshelper.py#L93
  # and
  # https://github.com/chipsec/chipsec/blob/0ad817d479bf51c0a883bb02bbb39464a5fb00a8/chipsec/helper/linux/helper.py#L54\).
  # The only reason Chipsec's code works is because classes imported by
  # chipsec.helper.linux.helper are defined before
  # "import chipsec.helper.helpers" statement, which makes chipsec's helper
  # code seem pretty fragile and somewhat horrible.
  CHIPSEC_IMPORTS = ["chipsec.helper.oshelper", "chipsec.helper.linux.helper"]

a = Analysis\(
    [client_path],
    hiddenimports=CHIPSEC_IMPORTS,
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
    name=os.path.join\("build", "grr-client"\),
    debug=False,
    strip=False,
    upx=False,
    console=True,
    version=os.path.join\(r"%(PyInstaller.build_dir)", "version.txt"\),
    icon=os.path.join\(r"%(PyInstaller.build_dir)", "grr.ico"\)\)

LIBCAPSTONE = None
for name in ["capstone", "libcapstone"]:
  for ext in [".so", ".dylib", ".dll"]:
    for path in [
      os.path.join\(capstone.__path__[0], name + ext\),
      os.path.join\(os.path.dirname\(capstone.__path__[0]\), name + ext\)
    ]:
      if os.path.exists\(path\):
        LIBCAPSTONE = path

if not LIBCAPSTONE:
  raise RuntimeError\("Can't find libcasptone"\)

CHIPSEC_LIBS = []
if platform.system\(\).lower\(\) == 'linux':
  import chipsec
  CHIPSEC_LIBS = glob.glob\(
    os.path.join\(chipsec.__path__[0], "helper", "linux", "*.so"\)\)
  if not CHIPSEC_LIBS:
    raise RuntimeError\("Can't find any chipsec linux libs."\)

RESOURCES_PREFIX = os.path.join\(sys.prefix, "resources"\)

coll = COLLECT\(
    exe,
    # Forcing PyInstaller to see libcapstone built by rekall-capstone
    # and chipsec.
    a.binaries + [\(os.path.basename\(LIBCAPSTONE\), LIBCAPSTONE, "BINARY"\)] +
      [\(os.path.basename\(x\), x, "BINARY"\) for x in CHIPSEC_LIBS],
    a.zipfiles,
    # Forcing PyInstaller to copy Pmem drivers from Rekall resources.
    a.datas + [\(os.path.join\("resources", "MacPmem.kext.tgz"\),
                 os.path.join\(RESOURCES_PREFIX, "MacPmem.kext.tgz"\),
                 "DATA"\),
               \(os.path.join\("resources", "WinPmem", "winpmem_x64.sys"\),
                 os.path.join\(RESOURCES_PREFIX, "WinPmem", "winpmem_x64.sys"\),
                 "DATA"\),
               \(os.path.join\("resources", "WinPmem", "winpmem_x86.sys"\),
                 os.path.join\(RESOURCES_PREFIX, "WinPmem", "winpmem_x86.sys"\),
                 "DATA"\)],
    strip=False,
    upx=False,
    name="grr-client"
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
    filevers=\(%(Source.version_major), %(Source.version_minor),
               %(Source.version_revision), %(Source.version_release)\),
    prodvers=\(%(Source.version_major), %(Source.version_minor),
               %(Source.version_revision), %(Source.version_release)\),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=\(0, 0\)
    \),
  kids=[
  VarFileInfo\([VarStruct\('Translation', [1033, 1200]\)]\)
  ]
\)
""")

config_lib.DEFINE_string("PyInstaller.icon_path",
                         "%(install_data/grr.ico@grr-response-core|resource)",
                         "A path to the icon to use for building the client.")

config_lib.DEFINE_string(
    "PyInstaller.build_dir",
    default="%(ClientBuilder.build_root_dir)/%(ClientBuilder.build_dest)",
    help="The path to the build directory.")

config_lib.DEFINE_string(
    "PyInstaller.dpkg_root",
    default="%(ClientBuilder.build_root_dir)/dist",
    help="Pyinstaller dpkg root.")

config_lib.DEFINE_string(
    "PyInstaller.workpath_dir",
    default="%(ClientBuilder.build_root_dir)/workpath",
    help="Pyinstaller working directory.")

config_lib.DEFINE_string(
    name="Client.prefix",
    default="",
    help="A prefix for the client name, usually dbg_ for debug builds.")

config_lib.DEFINE_string(
    name="ClientBuilder.output_basename",
    default=("%(Client.prefix)%(Client.name)_"
             "%(Source.version_string)_%(Client.arch)"),
    help="The base name of the output package.")

# Windows client specific options.
config_lib.DEFINE_bool(
    "ClientBuilder.console",
    default=False,
    help="Should the application be built as a console program. "
    "This aids debugging in windows.")

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.nanny_source_dir",
        must_exist=True,
        default=("%(grr_response_client|"
                 "module_path)/nanny/"),
        description="Path to the windows nanny VS solution file."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.nanny_prebuilt_binaries",
        must_exist=False,
        default="%(ClientBuilder.executables_dir)/%(Client.platform)/",
        description="Path to the pre-build GRRNanny executables (This will be "
        "used if there are no VS compilers available)."))

config_lib.DEFINE_choice(
    name="ClientBuilder.build_type",
    default="Release",
    choices=["Release", "Debug"],
    help="Type of build (Debug, Release)")

config_lib.DEFINE_string(
    name="ClientBuilder.template_extension",
    default=".zip",
    help="The extension to appear on templates.")

config_lib.DEFINE_string(
    name="PyInstaller.template_basename",
    default=("%(Client.name)_%(Source.version_string)_%(Client.arch)"),
    help="The template name of the output package.")

config_lib.DEFINE_string(
    name="PyInstaller.template_filename",
    default=(
        "%(PyInstaller.template_basename)%(ClientBuilder.template_extension)"),
    help="The template file name of the output package.")

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.template_dir",
        must_exist=False,
        default=("%(grr-response-templates@grr-response-templates|resource)/"
                 "templates"),
        description="The directory holding executable template files."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.template_path",
        must_exist=False,
        default=(
            "%(ClientBuilder.template_dir)/%(PyInstaller.template_filename)"),
        description="The full path to the executable template files for "
        "building."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.executables_dir",
        must_exist=False,
        default="%(executables@grr-response-core|resource)",
        description="The path to the grr executables directory."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.unzipsfx_stub_dir",
        must_exist=False,
        default=("%(ClientBuilder.executables_dir)/%(Client.platform)"
                 "/templates/unzipsfx"),
        description="The directory that contains the zip self extracting "
        "stub."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientBuilder.unzipsfx_stub",
        must_exist=False,
        default=(
            "%(ClientBuilder.unzipsfx_stub_dir)/unzipsfx-%(Client.arch).exe"),
        description="The full path to the zip self extracting stub."))

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
    default="%(Logging.path)/%(Client.name)_log.txt",
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
    default="%(Template.version_numeric)-1",
    help="The version of the debian package.")

config_lib.DEFINE_string(
    name="ClientBuilder.debian_package_base",
    default=("%(ClientBuilder.package_name)_"
             "%(ClientBuilder.debian_version)_%(Template.arch)"),
    help="The filename of the debian package without extension.")

config_lib.DEFINE_string(
    name="ClientBuilder.package_name",
    default="%(Client.name)",
    help="The debian package name.")

config_lib.DEFINE_string(
    name="ClientBuilder.build_time",
    default=time.ctime(),
    help="Time of build to embed into binary.")

config_lib.DEFINE_string(
    "ClientBuilder.vs_arch",
    default=None,
    help="Visual studio architecture string.")

config_lib.DEFINE_string(
    "ClientBuilder.vs_env_script",
    default=None,
    help="Path to visual studio environment variables bat file.")

config_lib.DEFINE_string(
    "ClientBuilder.vs_dir",
    default=None,
    help="Path to visual studio installation dir.")

config_lib.DEFINE_string(
    "ClientBuilder.build_root_dir",
    default=None,
    help="Root directory for client builds.")

config_lib.DEFINE_string(
    "ClientBuilder.build_dest",
    default="%(Client.name)-build",
    help="Output directory for client building.")

config_lib.DEFINE_string(
    "ClientBuilder.install_dir",
    default="/usr/lib/%(Client.name)",
    help="Target installation directory for client builds.")

config_lib.DEFINE_string(
    "ClientBuilder.mangled_output_basename",
    default=None,
    help="OS X package maker mangled name.")

config_lib.DEFINE_string(
    "ClientBuilder.package_maker_organization",
    default=None,
    help="OS X package maker organization name.")

config_lib.DEFINE_string(
    "ClientBuilder.signing_cert_name",
    default=None,
    help="Name of a Darwin signing cert.")

config_lib.DEFINE_string(
    "ClientBuilder.signing_keychain_file",
    default=None,
    help="Path to a keychain file to be used to sign Darwin binaries.")

config_lib.DEFINE_string(
    "ClientBuilder.target_dir",
    default=None,
    help="ClientBuilder target directory.")

config_lib.DEFINE_string(
    "ClientBuilder.daemon_link",
    default=None,
    help="The installer package will create a link in the system to the "
    "installed binary.")

# These options will be used by client.client_build when running buildandrepack
# and can be used to customize what is built for each client label.
config_lib.DEFINE_multichoice(
    name="ClientBuilder.target_platforms",
    default=[],
    choices=[
        "darwin_amd64_dmg", "linux_amd64_deb", "linux_i386_deb",
        "linux_amd64_rpm", "linux_i386_rpm", "windows_amd64_exe",
        "windows_i386_exe"
    ],
    help="Platforms that will be built by client_build buildandrepack")

config_lib.DEFINE_list(
    name="ClientBuilder.BuildTargets",
    default=[],
    help="List of context names that should be built by "
    "buildandrepack")

config_lib.DEFINE_string(
    "ClientBuilder.rpm_signing_key_public_keyfile",
    default="/etc/alternatives/grr_rpm_signing_key",
    help="Public key file for post-signing verification.")

config_lib.DEFINE_string(
    "ClientBuilder.rpm_gpg_name",
    default="GRR Team",
    help="The gpg name should match your gpg key name.")

# Parameters for signing Windows binaries on Linux hosts.
config_lib.DEFINE_string(
    "ClientBuilder.windows_signing_key",
    default="/etc/alternatives/grr_windows_signing_key",
    help="Path to GRR signing key. Should symlink "
    "to actual key.")

config_lib.DEFINE_string(
    "ClientBuilder.windows_signing_cert",
    default="/etc/alternatives/grr_windows_signing_cert",
    help="Path to GRR signing cert. Should symlink "
    "to actual cert.")

config_lib.DEFINE_string(
    "ClientBuilder.windows_signing_application_name",
    default="GRR",
    help="Signing cert application name.")

# Parameters for signing Windows binaries on Windows hosts.
config_lib.DEFINE_string(
    "ClientBuilder.signtool_signing_cmd",
    default=None,
    help="Full commandline for signtool to sign files.")

config_lib.DEFINE_string(
    "ClientBuilder.signtool_verification_cmd",
    default=None,
    help="Full commandline for signtool to verify signatures.")

config_lib.DEFINE_string(
    name="ClientRepacker.output_basename",
    default=("%(Client.prefix)%(Client.name)_"
             "%(Template.version_string)_%(Template.arch)"),
    help="The base name of the output package.")

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientRepacker.output_filename",
        must_exist=False,
        default=(
            "%(ClientRepacker.output_basename)%(ClientBuilder.output_extension)"
        ),
        description="The filename of the generated installer file."))

config_lib.DEFINE_option(
    PathTypeInfo(
        name="ClientRepacker.output_path",
        must_exist=False,
        default=("%(ClientBuilder.executables_dir)"
                 "/installers/%(ClientRepacker.output_filename)"),
        description="The full path to the generated installer file."))

# These values are determined from the template at repack time.
config_lib.DEFINE_choice(
    name="Template.build_type",
    default="Release",
    choices=["Release", "Debug"],
    help="Type of build (Debug, Release)")

config_lib.DEFINE_list(
    name="Template.build_context",
    default=[],
    help="List of build contexts that should be reapplied at repack.")

config_lib.DEFINE_integer("Template.version_major", None,
                          "Major version number of client template.")

config_lib.DEFINE_integer("Template.version_minor", None,
                          "Minor version number of client template.")

config_lib.DEFINE_integer("Template.version_revision", None,
                          "Revision number of client template.")

config_lib.DEFINE_integer("Template.version_release", None,
                          "Release number of client template.")

config_lib.DEFINE_string(
    "Template.version_string", "%(version_major).%(version_minor)."
    "%(version_revision).%(version_release)",
    "Version string of the client template.")

config_lib.DEFINE_integer(
    "Template.version_numeric", "%(version_major)%(version_minor)"
    "%(version_revision)%(version_release)",
    "Version string of the template as an integer.")

config_lib.DEFINE_string("Template.arch", None,
                         "The architecture of the client template.")
