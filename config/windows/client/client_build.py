#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This tool builds the windows client."""



import argparse
import ConfigParser
import glob
import os
import shutil
import StringIO
import subprocess
import sys
import time
import zipfile

from distutils import sysconfig

parser = argparse.ArgumentParser(description="Build client binaries.")

parser.add_argument("--pyinstaller_path",
                    default=os.path.join(sysconfig.PREFIX, "pyinstaller",
                                         "pyinstaller.py"),
                    help="Path to pyinstaller main script.")

parser.add_argument(
    "--vs_path",
    default=r"C:\Program Files (x86)\Microsoft Visual Studio 10.0",
    help="Path to the visual studio installation.")

parser.add_argument("--source",
                    default=os.path.join(os.getcwd(), "grr"),
                    help="The path to the grr sources.")

parser.add_argument("--build_time", default=time.ctime(),
                    help="Time of build to embed into binary")


parser.add_argument("--build_dir", default=os.getcwd(),
                    help="The directory we build in.")

parser.add_argument("-c", "--configuration", default=None,
                    help="The configuration file to parse.")

args = parser.parse_args()


# Workout the bitness.
if "32 bit" in sys.version:
  args.arch = "i386"
  args.vc_arch = "x86"
  args.bits = "32"
  args.vs_release = "Win32"
elif "64 bit" in sys.version:
  args.arch = "amd64"
  args.vc_arch = "x64"
  args.bits = "64"
  args.vs_release = "x64"
else:
  raise RuntimeError("Cant figure out the bitness.")


class GRRConfigManager(ConfigParser.SafeConfigParser):
  """A template interpolator with data from the config file."""

  def __init__(self, filename):
    ConfigParser.SafeConfigParser.__init__(self)
    self.read(filename)
    self.add_section("")
    for k, v in args.__dict__.items():
      self.set("", k, v)

  def __getitem__(self, item):
    if "." in item:
      section, param = item.split(".", 1)
    else:
      section, param = "", item

    try:
      param, filter_func = param.split("|", 1)

      return getattr(self, filter_func)(self.get(section, param))
    except ValueError:
      return self.get(section, param)

  def __setitem__(self, item, value):
    self.set("", item, value)

  def join(self, data):  # pylint: disable=g-bad-name
    return "".join(data.splitlines())


class GRRBuilder(object):
  """A Builder for the GRR Client."""

  def __init__(self):
    self.conf_path = os.path.join(args.source, "config", "windows", "client")
    self.conf_file = args.configuration or os.path.join(args.source, "config",
                                                        "client_build.conf")
    self.installers = os.path.join(args.source, "executables", "windows",
                                   "templates", "unzipsfx")
    self.conf = GRRConfigManager(self.conf_file)

    # The output directory.
    self.output_path = os.path.join(
        args.build_dir, "dist",
        "%(Nanny.Name)s_%(GRR.version)s_%(.arch)s" % self.conf)

    self.installer_path = os.path.join(
        args.build_dir, "dist",
        "%(Nanny.Name)s_%(GRR.version)s_%(.arch)s.exe" % self.conf)

    # Make sure the output directory is removed.
    # shutil.rmtree(self.output_path, ignore_errors=True)

  def BuildVSProject(self, path, configuration="Release"):
    """Builds the visual studio project specified in path.

    Args:
      path: The path that contains the VS project.
      configuration: The desired configuration to build.

    Returns:
      The path to the output directory.

    Raises:
      RuntimeError: if arch is not known.
    """
    if args.arch == "i386":
      env_script = os.path.join(args.vs_path, "VC", "bin", "vcvars32.bat")
    elif args.arch == "amd64":
      env_script = os.path.join(args.vs_path, "VC", "bin", "amd64",
                                "vcvars64.bat")
    else:
      raise RuntimeError("Arch not supported")

    # Update the following files from the configuration:
    self.UpdateFile(os.path.join(self.conf["source"], "client", "nanny",
                                 "windows_nanny.h"))

    subprocess.call("cmd /c \"%s\" && cd %s && msbuild /p:Configuration=%s" % (
        env_script, path, configuration))

    # Collect the binaries to the output directory
    self.CopyGlob(os.path.join(
        path, self.conf["vs_release"], configuration, "*.exe"), os.path.join(
            self.output_path, self.conf["Nanny.Service_Name"]))

    return os.path.join(path, configuration)

  def CopyGlob(self, source, dest_path):
    for filename in glob.glob(source):
      print "Copying %s to %s" % (filename, dest_path)
      shutil.copy(filename, dest_path)

  def UpdateFile(self, path):
    """Updates the file from a template based on the config."""
    data = open(path + ".in", "rb").read()
    print "Updating file %s" % path
    with open(path, "wb") as fd:
      fd.write(data % self.conf)

  def BuildPyinstallerEgg(self):
    """Build the pyinstalled client directory."""
    # Figure out where distorm is so pyinstaller can find it.
    librarypaths = ["."]
    try:
      import distorm3  # pylint: disable=g-import-not-at-top
      librarypaths.append(os.path.dirname(distorm3.__file__))
    except ImportError:
      pass

    self.conf["librarypaths"] = repr(librarypaths)
    spec_path = os.path.join(self.conf_path, "grr.spec")
    self.UpdateFile(spec_path)
    self.UpdateFile(os.path.join(self.conf_path, "version.txt"))
    self.UpdateFile(os.path.join(
        self.conf["source"], "client", "client_config.py"))

    subprocess.call("%s %s %s" % (sys.executable, args.pyinstaller_path,
                                  spec_path))

  def BuildInstaller(self):
    """Build the deployable self installer."""
    # Create the installer VBS.
    vbs_file = os.path.join(self.conf_path, "installer.vbs")
    self.UpdateFile(vbs_file)

    # Copy the produced zip file into memory.
    data = StringIO.StringIO(open(self.output_path + ".zip", "rb").read())

    z = zipfile.ZipFile(data, mode="a")

    # This comment is used by the self extractor to start the VBS script.
    z.comment = "$AUTORUN$>wscript installer.vbs"
    z.write(vbs_file, "installer.vbs")
    z.close()

    installer = os.path.join(self.installers,
                             "unzipsfx-%(.bits)s.exe" % self.conf)

    with open(self.output_path + ".exe", "wb") as fd:
      # First write the installer stub.
      fd.write(open(installer, "rb").read())

      # Then append the payload zip file.
      fd.write(data.getvalue())

  def BuildGRRClient(self):
    """Build the windows client."""

    # Make the pyinstaller egg.
    self.BuildPyinstallerEgg()

    # The service executable.
    self.BuildVSProject(os.path.join(args.source, "client", "nanny"))

    # Copy the C runtime dlls:
    self.CopyGlob(os.path.join(
        self.conf[".vs_path"], "VC", "redist", self.conf[".vc_arch"],
        "Microsoft.VC*CRT/*"), self.output_path)

    # Copy the config over.
    shutil.copy(self.conf_file, self.output_path)

    # Make a zip file of everything.
    shutil.make_archive(self.output_path, "zip",
                        base_dir=".",
                        root_dir=self.output_path,
                        verbose=True)

    self.BuildInstaller()


if __name__ == "__main__":
  GRRBuilder().BuildGRRClient()
