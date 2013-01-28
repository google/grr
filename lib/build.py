#!/usr/bin/env python
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

import glob
import os
import shutil
import StringIO
import subprocess
import sys
import zipfile


class ClientBuilder(object):
  """Abstract client builder class, used by the OS specific implementations."""

  def __init__(self, source, build_files_dir, build_dir, build_time,
               pyinstaller, config, architecture):
    """Initialize the client builder.

    Args:
      source: the path to the source directory.
      build_files_dir: the (root) directory that contains the (input) build
                       file.
      build_dir: the build (root) directory.
      build_time: string containing the build time.
      pyinstaller: the location of the pyinstaller.py script.
      config: the configuration (config_lib.ConfigManager).
      architecture: string containing the architecture to build for, e.g. i386
                    or amd64.
    """
    self.build_files_dir = build_files_dir
    self.pyinstaller = pyinstaller
    self.conf = config

    # Add temporary section to the config. This is not written to the config
    # file, but instead kept at runtime to ease interpolation with configs.
    if not config.has_section("Temp"):
      config.add_section("Temp")
    config["Temp.arch"] = architecture
    config["Temp.build_dir"] = build_dir
    config["Temp.build_time"] = build_time
    config["Temp.source"] = source

    # Set dist_dir in the config so we can use it in the templates
    config["dist_dir"] = os.path.join(build_dir, "dist")

    config["PyInstaller.Sources"] = (
        "os.path.join('%s', 'client', 'client.py')" % source)

  def CopyGlob(self, source, dest_path):
    for filename in glob.glob(source):
      print "Copying %s to %s" % (filename, dest_path)
      shutil.copy(filename, dest_path)

  def GenerateFile(self, filename):
    """Generates a file using the builder configuration and a template file.

    Args:
      filename: the name of the template file without the .in suffix.
    """
    data = open(filename + ".in", "rb").read()
    print "Generating file: %s" % filename
    with open(filename, "wb") as fd:
      fd.write(data % self.conf)

  def BuildPyInstaller(self, output_basename, build_dir):
    """Builds the client using PyInstaller.

    Args:
      output_basename: the client output directory basename.
      build_dir: the PyInstaller build directory.

    Returns:
      The name of the client directory created by PyInstaller.
    """
    # Figure out where distorm is so PyInstaller can find it.
    librarypaths = ["."]
    try:
      import distorm3  # pylint: disable=g-import-not-at-top
      librarypaths.append(os.path.dirname(distorm3.__file__))
    except ImportError:
      pass

    output_dir = os.path.join(self.conf["Temp.dist_dir"], output_basename)
    build_files_dir = os.path.join(
        self.build_files_dir, "pyinstaller", "client")
    icon_file = os.path.join(build_files_dir, "grr.ico")
    spec_file = os.path.join(build_files_dir, "grr.spec")
    version_file = os.path.join(build_files_dir, "version.txt")

    self.conf["PyInstaller.Pathex"] = repr(librarypaths)
    self.conf["PyInstaller.Build_Directory"] = build_dir
    self.conf["PyInstaller.Output_Directory"] = output_dir
    self.conf["PyInstaller.Version_File"] = version_file
    self.conf["PyInstaller.Icon_File"] = icon_file

    self.GenerateFile(spec_file)

    self.GenerateFile(
        os.path.join(self.conf["Temp.source"], "client", "client_config.py"))
    self.GenerateFile(
        os.path.join(self.conf["Temp.source"], "client", "client_keys.py"))

    # PyInstaller uses version.txt to generate the VERSION resource
    # in the Windows PE/COFF executable
    self.GenerateFile(version_file)

    # Need shell=True here otherwise /usr/bin/env python is not expanded
    subprocess.call(
        "%s %s %s" % (sys.executable, self.pyinstaller, spec_file), shell=True)

    return os.path.join(self.conf["Temp.dist_dir"], output_basename)

  def WriteConfig(self, output_dir):
    """Writes the client config file in the output directory.

    The output directory is created when necessary.

    Args:
      output_dir: the name of the directory to copy the client config to.

    Returns:
      The filename of the newly written client config.
    """
    if not os.path.isdir(output_dir):
      os.makedirs(output_dir)
    out_file = os.path.join(output_dir, "%(Nanny.Name)s.conf" % self.conf)
    self.conf.WriteClientConfigCopy(out_file)
    return out_file


class WindowsClientBuilder(ClientBuilder):
  """Builder class for the Windows client."""

  def __init__(self, source, build_files_dir, build_dir, build_time,
               pyinstaller, config, architecture, executables_dir,
               vs_dir, installer_type="vbs"):
    """Initialize the Windows client builder.

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
      executables_dir: the directory containing prebuilt executables
                       (for unzipsfx).
      vs_dir: the location of the Visual Studio directory.
      installer_type: the installer type, either "bat" or "vbs"
    """
    super(WindowsClientBuilder, self).__init__(
        source, build_files_dir, build_dir, build_time, pyinstaller, config,
        architecture)
    self.executables_dir = executables_dir
    self.vs_dir = vs_dir
    self.installer_type = installer_type
    self.output_basename = (
        "%(ClientBuildWindows.name)s_" % self.conf +
        "%(ClientBuildWindows.version_string)s_%(Temp.arch)s" % self.conf)

  def BuildVSProject(self, vs_solution_dir, vs_solution_conf="Release"):
    """Builds the Visual Studio (VS) project specified in path.

    Args:
      vs_solution_dir: the location of the VS solution (project).
      vs_solution_conf: the name of the VS solution configuration e.g. Release.

    Returns:
      The location of the directory that contains the built files.

    Raises:
      RuntimeError: if architecture defined by the config is not supported.
    """
    if self.conf["Temp.arch"] == "i386":
      vs_arch = "Win32"
      env_script = os.path.join(self.vs_dir, "VC", "bin", "vcvars32.bat")
    elif self.conf["Temp.arch"] == "amd64":
      vs_arch = "x64"
      env_script = os.path.join(
          self.vs_dir, "VC", "bin", "amd64", "vcvars64.bat")
    else:
      raise RuntimeError("unsupported architecture: %s" %
                         self.conf["Temp.arch"])

    # if cmd cannot find env_script and it contains spaces cmd will only show
    # the part up to space.
    if not os.path.exists(env_script):
      raise RuntimeError("no such Visual Studio script: %s" % env_script)

    self.GenerateFile(os.path.join(self.conf["Temp.source"], "client", "nanny",
                                   "windows_nanny.h"))

    subprocess.call("cmd /c \"%s\" && cd %s && msbuild /p:Configuration=%s" % (
        env_script, vs_solution_dir, vs_solution_conf))

    return os.path.join(vs_solution_dir, vs_arch, vs_solution_conf)

  def BuildInstallerBatZipSfx(self, sfx_file, zip_file):
    """Builds an installer that uses install.bat and config.reg.

    Args:
      sfx_file: the name of the resulting ZIP SFX file.
      zip_file: the location of the prebuilt ZIP file.
    """
    build_files_dir = os.path.join(self.build_files_dir, "windows", "client")

    bat_file = os.path.join(build_files_dir, "install.bat")
    reg_file = os.path.join(build_files_dir, "config.reg")

    self.GenerateFile(bat_file)
    self.GenerateFile(reg_file)

    self.BuildInstallerZipSfx(
        sfx_file, zip_file, "install.bat", [bat_file, reg_file])

  def BuildInstallerVbsZipSfx(self, sfx_file, zip_file):
    """Builds an installer that uses installer.vbs.

    Args:
      sfx_file: the name of the resulting ZIP SFX file.
      zip_file: the location of the prebuilt ZIP file.
    """
    build_files_dir = os.path.join(self.build_files_dir, "windows", "client")

    vbs_file = os.path.join(build_files_dir, "installer.vbs")

    self.GenerateFile(vbs_file)

    self.BuildInstallerZipSfx(
        sfx_file, zip_file, "wscript installer.vbs", [vbs_file])

  def BuildInstallerZipSfx(self, sfx_file, zip_file, autorun_command,
                           additional_files):
    """Builds a self extracting ZIP that autoruns an installation script.

    Args:
      sfx_file: the name of the resulting ZIP SFX file.
      zip_file: the location of the prebuilt ZIP file.
      autorun_command: the autorun command to add to the ZIP SFX.
      additional_files: additional files to add to the ZIP ZFX.

    Raises:
      RuntimeError: if architecture defined by the config is not supported.
    """
    if self.conf["Temp.arch"] == "i386":
      sfx_bits = "32"
    elif self.conf["Temp.arch"] == "amd64":
      sfx_bits = "64"
    else:
      raise RuntimeError("unsupported architecture: %s" %
                         self.conf["Temp.arch"])

    unzip_sfx_exe_file = os.path.join(
        self.executables_dir, "windows", "templates", "unzipsfx",
        "unzipsfx-%s.exe" % sfx_bits)

    zip_data = StringIO.StringIO(open(zip_file, "rb").read())
    z = zipfile.ZipFile(zip_data, mode="a")

    # The zip file comment is used by the self extractor to run
    # the installation script
    z.comment = "$AUTORUN$>%s" % autorun_command

    for filename in additional_files:
      z.write(filename, os.path.basename(filename))
    z.close()

    with open(sfx_file, "wb") as fd:
      # First write the installer stub.
      fd.write(open(unzip_sfx_exe_file, "rb").read())

      # Then append the payload zip file.
      fd.write(zip_data.getvalue())

  def Build(self):
    """Builds the client."""
    output_dir = os.path.join(self.conf["Temp.dist_dir"], self.output_basename)

    self.conf["PyInstaller.Sources"] = (
        "os.path.join(HOMEPATH, 'support', '_mountzlib.py'), "
        "os.path.join(HOMEPATH, 'support', 'useUnicode.py'), "
        "os.path.join('%s', 'client', 'client.py')" % self.conf["Temp.source"])

    # TODO(user): why does Windows needs a binary name? Check if we
    # can simplify this and move this (largely) into BuildPyInstaller()
    build_dir = os.path.join(
        self.conf["Temp.build_dir"], "build", "pyi.win32", self.output_basename,
        "%(ClientBuildWindows.binary_name)s" % self.conf)

    self.BuildPyInstaller(self.output_basename, build_dir)

    # Builds the Nanny service executable.
    vs_solution_dir = os.path.join(self.conf["Temp.source"], "client", "nanny")
    nanny_build_dir = self.BuildVSProject(vs_solution_dir)

    if self.conf["Temp.arch"] == "i386":
      vc_arch = "x86"
    elif self.conf["Temp.arch"] == "amd64":
      vc_arch = "x64"
    else:
      raise RuntimeError("unsupported architecture: %s" %
                         self.conf["Temp.arch"])

    # Copy the nanny binaries and Visual Studio C runtime DLLs to the
    # output directory
    self.CopyGlob(
        os.path.join(nanny_build_dir, "*.exe"),
        os.path.join(output_dir, self.conf["ClientBuildWindows.service_name"]))

    self.CopyGlob(os.path.join(self.vs_dir, "VC", "redist", vc_arch,
                               "Microsoft.VC*CRT/*"), output_dir)

    # TODO(user): after the rewrite do we still need to keep a copy of the
    # config?
    # self.WriteConfig(output_dir)

    # Make a zip file of everything.
    self.MakeZip(output_dir, output_dir)

    zip_file = "%s.zip" % output_dir
    sfx_file = "%s.exe" % output_dir

    if self.installer_type == "bat":
      self.BuildInstallerBatZipSfx(sfx_file, zip_file)
    else:
      self.BuildInstallerVbsZipSfx(sfx_file, zip_file)

  def MakeZip(self, input_dir, output_file):
    """Creates a ZIP archive of the files in the input directory.

    Args:
      input_dir: the name of the input directory.
      output_file: the name of the output ZIP archive without extension.
    """
    shutil.make_archive(output_file, "zip",
                        base_dir=".",
                        root_dir=input_dir,
                        verbose=True)

  def RepackZipSfxClient(self, input_dir, output_dir):
    """Take an executable directory and repack found executable templates."""

    # TODO(user): after the rewrite do we still need to keep a copy of the
    # config?
    # self.WriteConfig(output_dir)

    output_file = os.path.join(output_dir, self.output_basename)
    self.MakeZip(input_dir, output_file)

    zip_file = os.path.join(output_dir, "%s.zip" % self.output_basename)
    sfx_file = os.path.join(output_dir, "%s.exe" % self.output_basename)

    if self.installer_type == "bat":
      self.BuildInstallerBatZipSfx(sfx_file, zip_file)
    else:
      self.BuildInstallerVbsZipSfx(sfx_file, zip_file)

    return sfx_file


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

  def Build(self):
    """Builds the client."""
    output_basename = "%(ClientBuildDarwin.plist_binary_directory)s" % self.conf
    output_dir = os.path.join(self.conf["Temp.dist_dir"], output_basename)

    build_dir = os.path.join(
        self.conf["Temp.build_dir"], "build", "pyi.darwin", output_basename)

    self.BuildPyInstaller(output_basename, build_dir)

    package_dir = os.path.join(self.conf["Temp.dist_dir"],
                               "%(ClientBuildDarwin.packageMaker_name)s.pkg"
                               % (self.conf))
    disk_image_path = os.path.join(self.conf["Temp.dist_dir"],
                                   "%(ClientBuildDarwin.packagemaker_name)s.dmg"
                                   % (self.conf))

    self.BuildInstallerLaunchDaemonsPlist()
    self.BuildInstallerPkg(package_dir, output_dir)
    self.BuildInstallerDmg(disk_image_path, package_dir)

    # TODO(user): create a zip file


def RepackAllBinaries(build_files_dir, config, exe_dir):
  """Repack binaries based on the configuration.

  Args:
    build_files_dir: The (root) directory that contains the (input) build
                     file.
    config: The configuration (config_lib.ConfigManager).
    exe_dir: Directory containing the executables used in the build.

  Returns:
    A list of tuples containing (output_file, platform, architecture)
  """
  built = []
  print "\n## Repacking i386 Windows client with bat installer"
  output_dir = os.path.join(exe_dir, "windows", "installers")

  # A number of args are not required to do a repack, so we fake some of these.
  base_args = dict(source="source", build_files_dir=build_files_dir,
                   build_dir="", build_time="", pyinstaller="", config=config,
                   executables_dir=exe_dir, vs_dir="")
  template_dir = os.path.join(exe_dir, "windows", "templates")

  builder = WindowsClientBuilder(architecture="i386", installer_type="bat",
                                 **base_args)
  out = builder.RepackZipSfxClient(
      input_dir=os.path.join(template_dir, "win32"), output_dir=output_dir)
  built.append((out, "Windows", "i386"))
  print "Packed to %s" % out

  print "\n## Repacking amd64 Windows client with vbs installer"
  builder = WindowsClientBuilder(architecture="amd64", installer_type="vbs",
                                 **base_args)
  out = builder.RepackZipSfxClient(
      input_dir=os.path.join(template_dir, "win64"), output_dir=output_dir)
  built.append((out, "Windows", "amd64"))
  print "Packed to %s" % out

  # TODO(user): This is disabled until the Darwin builder supports the output
  # we need.
  #
  # print "\n## Repacking Mac OS X client"
  # print "NOTE: Currently this just generates a compatible conf file"
  # builder = DarwinClientBuilder(architecture="amd64",
  #    packagemaker=args.packagemaker)

  # output_dir = os.path.join(exe_dir, "darwin", "installers")
  # new_file = builder.WriteConfig(output_dir)
  # built.append((out, "Darwin", "amd64"))
  # print "Packed to %s" % out

  return built
