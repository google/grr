#!/usr/bin/env python
"""Script to build windows templates."""

import argparse
import glob
import os
import shutil
import subprocess

parser = argparse.ArgumentParser(description="Build windows templates.")

parser.add_argument(
    "--build_dir", default=r"C:\grrbuild", help="GRR build directory.")

parser.add_argument(
    "--grr_src",
    default=r"C:\grrbuild\grr",
    help="Location of the grr src code. If it doesn't exist "
    " at this path we'll try to check it out from github.")

parser.add_argument(
    "--output_dir",
    default=r"C:\grrbuild\output",
    help="Destination directory for the templates.")

parser.add_argument(
    "--cloud_storage_sdist_bucket",
    default=None,
    help="If defined, copy sdists from this bucket rather than"
    " building them.")

parser.add_argument(
    "--cloud_storage_output_bucket",
    default=None,
    help="If defined, build products will be copied to this "
    "cloud storage bucket.")

parser.add_argument(
    "--gsutil",
    default=(r"C:\Program Files (x86)\Google\Cloud "
             r"SDK\google-cloud-sdk\bin\gsutil.cmd"),
    help="gsutil binary. The default is the SDK install location since that's "
    "likely the one the user has authorized their creds for")

parser.add_argument(
    "--test_repack_install",
    action="store_true",
    default=False,
    help="Test repacking by calling repack on the template after building,"
    "then try and install the result. For use by integration tests. If you use "
    "this option you must run as admin.")

parser.add_argument(
    "--wheel_dir",
    default=None,
    help="A directory that will be passed to pip as the wheel-dir parameter.")

parser.add_argument(
    "--build_32",
    dest="build_32",
    default=True,
    action="store_true",
    help="Enable building the 32 bit version.")
parser.add_argument("--no_build_32", dest="build_32", action="store_false")

parser.add_argument(
    "--python32_dir",
    default=r"C:\Python27",
    help="Path to the 32 bit Python installation.")

parser.add_argument(
    "--python64_dir",
    default=r"C:\Python27-x64",
    help="Path to the 64 bit Python installation.")

parser.add_argument(
    "--protoc",
    default=r"C:\grr_deps\protoc\bin\protoc.exe",
    help="Path to the protoc.exe binary.")

parser.add_argument(
    "--expect_service_running",
    dest="expect_service_running",
    action="store_true",
    help="Triggers whether after installation the GRR service should be "
    "running or not. Used for testing the installation.")
parser.add_argument(
    "--noexpect_service_running",
    dest="expect_service_running",
    action="store_false")
parser.set_defaults(expect_service_running=True)

parser.add_argument(
    "--config",
    default="",
    help="Path to the config file to be used when building templates.")

args = parser.parse_args()


class WindowsTemplateBuilder(object):
  """Build windows templates."""

  def SetupVars(self):
    """Set up some vars for the directories we use."""
    # Python paths chosen to match appveyor:
    # http://www.appveyor.com/docs/installed-software#python

    self.python_dir_64 = args.python64_dir
    self.python_dir_32 = args.python32_dir

    self.virtualenv_bin64 = os.path.join(self.python_dir_64,
                                         r"Scripts\virtualenv.exe")
    self.virtualenv_bin32 = os.path.join(self.python_dir_32,
                                         r"Scripts\virtualenv.exe")

    self.virtualenv64 = os.path.join(args.build_dir, r"python_64")
    self.virtualenv32 = os.path.join(args.build_dir, r"python_32")

    self.grr_client_build64 = os.path.join(self.virtualenv64,
                                           r"Scripts\grr_client_build.exe")
    self.grr_client_build32 = os.path.join(self.virtualenv32,
                                           r"Scripts\grr_client_build.exe")
    self.pip64 = os.path.join(self.virtualenv64, r"Scripts\pip.exe")
    self.pip32 = os.path.join(self.virtualenv32, r"Scripts\pip.exe")

    self.virtualenv_python64 = os.path.join(self.virtualenv64,
                                            r"Scripts\python.exe")
    self.virtualenv_python32 = os.path.join(self.virtualenv32,
                                            r"Scripts\python.exe")

    self.git = r"C:\Program Files\Git\bin\git.exe"

    self.install_path = r"C:\Windows\System32\GRR"
    self.service_name = "GRR Monitor"

    self.expect_service_running = args.expect_service_running

  def Clean(self):
    """Clean the build environment."""
    # os.unlink doesn't work effectively, use the shell to delete.
    if os.path.exists(args.build_dir):
      subprocess.call("rd /s /q %s" % args.build_dir, shell=True)
    if os.path.exists(args.output_dir):
      subprocess.call("rd /s /q %s" % args.output_dir, shell=True)

    os.makedirs(args.build_dir)
    os.makedirs(args.output_dir)

    # Create virtualenvs.
    subprocess.check_call([self.virtualenv_bin64, self.virtualenv64])
    if args.build_32:
      subprocess.check_call([self.virtualenv_bin32, self.virtualenv32])

    # Currently this should do nothing as we will already have a modern pip
    # installed, but we leave this here so if we get broken by pip again it's
    # just a simple case of searching for pip>=8.1.1 and adding an upper limit
    # cap in all those places.

    cmd = ["-m", "pip", "install"]
    if args.wheel_dir:
      cmd += ["--no-index", r"--find-links=file:///%s" % args.wheel_dir]

    subprocess.check_call(
        [self.virtualenv_python64] + cmd + ["--upgrade", "pip>=8.1.1"])
    if args.build_32:
      subprocess.check_call(
          [self.virtualenv_python32] + cmd + ["--upgrade", "pip>=8.1.1"])
    os.environ["PROTOC"] = args.protoc

  def GitCheckoutGRR(self):
    os.chdir(args.build_dir)
    subprocess.check_call(
        [self.git, "clone", "https://github.com/google/grr.git"])

  def MakeProtoSdist(self):
    os.chdir(os.path.join(args.grr_src, "grr/proto"))
    subprocess.check_call([
        self.virtualenv_python64, "setup.py", "sdist", "--formats=zip",
        "--dist-dir=%s" % args.build_dir
    ])
    return glob.glob(os.path.join(args.build_dir,
                                  "grr-response-proto-*.zip")).pop()

  def MakeCoreSdist(self):
    os.chdir(args.grr_src)
    subprocess.check_call([
        self.virtualenv_python64, "setup.py", "sdist", "--formats=zip",
        "--dist-dir=%s" % args.build_dir, "--no-make-ui-files",
        "--no-sync-artifacts"
    ])
    return glob.glob(os.path.join(args.build_dir,
                                  "grr-response-core-*.zip")).pop()

  def MakeClientSdist(self):
    os.chdir(os.path.join(args.grr_src, "grr/client/"))
    subprocess.check_call([
        self.virtualenv_python64, "setup.py", "sdist", "--formats=zip",
        "--dist-dir=%s" % args.build_dir
    ])
    return glob.glob(os.path.join(args.build_dir,
                                  "grr-response-client-*.zip")).pop()

  def CopySdistsFromCloudStorage(self):
    """Use gsutil to copy sdists from cloud storage."""
    subprocess.check_call([
        args.gsutil, "cp",
        "gs://%s/grr-response-proto-*.zip" % args.cloud_storage_sdist_bucket,
        args.build_dir
    ])
    proto = glob.glob(os.path.join(args.build_dir,
                                   "grr-response-proto-*.zip")).pop()

    subprocess.check_call([
        args.gsutil, "cp",
        "gs://%s/grr-response-core-*.zip" % args.cloud_storage_sdist_bucket,
        args.build_dir
    ])
    core = glob.glob(os.path.join(args.build_dir,
                                  "grr-response-core-*.zip")).pop()

    subprocess.check_call([
        args.gsutil, "cp",
        "gs://%s/grr-response-client-*.zip" % args.cloud_storage_sdist_bucket,
        args.build_dir
    ])
    client = glob.glob(
        os.path.join(args.build_dir, "grr-response-client-*.zip")).pop()
    return proto, core, client

  def InstallGRR(self, path):
    """Installs GRR."""

    cmd64 = [self.pip64, "install"]
    cmd32 = [self.pip32, "install"]

    if args.wheel_dir:
      cmd64 += ["--no-index", r"--find-links=file:///%s" % args.wheel_dir]
      cmd32 += ["--no-index", r"--find-links=file:///%s" % args.wheel_dir]

    cmd64.append(path)
    cmd32.append(path)

    subprocess.check_call(cmd64)
    if args.build_32:
      subprocess.check_call(cmd32)

  def BuildTemplates(self):
    """Builds the client templates.

    We dont need to run special compilers so just enter the virtualenv and
    build. Python will already find its own MSVC for python compilers.
    """
    if args.config:
      build_args = [
          "--verbose", "--config", args.config, "build", "--output",
          args.output_dir
      ]
    else:
      build_args = ["--verbose", "build", "--output", args.output_dir]
    subprocess.check_call([self.grr_client_build64] + build_args)
    if args.build_32:
      subprocess.check_call([self.grr_client_build32] + build_args)

  def _RepackTemplates(self):
    """Repack templates with a dummy config."""
    dummy_config = os.path.join(
        args.grr_src, "grr/test/grr_response_test/test_data/dummyconfig.yaml")
    if args.build_32:
      template_i386 = glob.glob(os.path.join(args.output_dir,
                                             "*_i386*.zip")).pop()
    template_amd64 = glob.glob(os.path.join(args.output_dir,
                                            "*_amd64*.zip")).pop()

    # We put the installers in the output dir so they get stored as build
    # artifacts and we can test the 32bit build manually.
    subprocess.check_call([
        self.grr_client_build64, "--verbose", "--secondary_configs",
        dummy_config, "repack", "--template", template_amd64, "--output_dir",
        args.output_dir
    ])
    subprocess.check_call([
        self.grr_client_build64, "--verbose", "--context",
        "DebugClientBuild Context", "--secondary_configs", dummy_config,
        "repack", "--template", template_amd64, "--output_dir", args.output_dir
    ])
    if args.build_32:
      subprocess.check_call([
          self.grr_client_build32, "--verbose", "--secondary_configs",
          dummy_config, "repack", "--template", template_i386, "--output_dir",
          args.output_dir
      ])
      subprocess.check_call([
          self.grr_client_build32, "--verbose", "--context",
          "DebugClientBuild Context", "--secondary_configs", dummy_config,
          "repack", "--template", template_i386, "--output_dir", args.output_dir
      ])

  def _CleanupInstall(self):
    """Cleanup from any previous installer enough for _CheckInstallSuccess."""
    if os.path.exists(self.install_path):
      shutil.rmtree(self.install_path)
      if os.path.exists(self.install_path):
        raise RuntimeError("Install path still exists: %s" % self.install_path)

    # Deliberately don't check return code, since service may not be installed.
    subprocess.call(["sc", "stop", self.service_name])

  def _CheckInstallSuccess(self):
    """Checks if the installer installed correctly."""
    if not os.path.exists(self.install_path):
      raise RuntimeError("Install failed, no files at: %s" % self.install_path)

    try:
      output = subprocess.check_output(["sc", "query", self.service_name])
      service_running = "RUNNING" in output
    except subprocess.CalledProcessError as e:
      if e.returncode == 1060:
        # 1060 means: The specified service does not exist as an installed
        # service.
        service_running = False
      else:
        raise

    if self.expect_service_running:
      if not service_running:
        raise RuntimeError(
            "GRR service not running after install, sc query output: %s" %
            output)
    else:
      if service_running:
        raise RuntimeError(
            "GRR service running after install with expect_service_running == "
            "False, sc query output: %s" % output)

  def _InstallInstallers(self):
    """Install the installer built by RepackTemplates."""
    # 32 bit binary will refuse to install on a 64bit system so we only install
    # the 64 bit version
    installer_amd64 = glob.glob(
        os.path.join(args.output_dir, "dbg_*_amd64.exe")).pop()
    self._CleanupInstall()
    # The exit code is always 0, test to see if install was actually successful.
    subprocess.check_call([installer_amd64])
    self._CheckInstallSuccess()

  def CopyResultsToCloudStorage(self):
    paths = glob.glob("%s\\*" % args.output_dir)
    subprocess.check_call([args.gsutil, "-m", "cp"] + paths +
                          ["gs://%s/" % args.cloud_storage_output_bucket])

  def Build(self):
    """Build templates."""
    self.SetupVars()
    self.Clean()
    if args.cloud_storage_sdist_bucket:
      proto_sdist, core_sdist, client_sdist = self.CopySdistsFromCloudStorage()
    else:
      if not os.path.exists(args.grr_src):
        self.GitCheckoutGRR()
      proto_sdist = self.MakeProtoSdist()
      core_sdist = self.MakeCoreSdist()
      client_sdist = self.MakeClientSdist()

    self.InstallGRR(proto_sdist)
    self.InstallGRR(core_sdist)
    self.InstallGRR(client_sdist)
    self.BuildTemplates()
    if args.test_repack_install:
      self._RepackTemplates()
      self._InstallInstallers()
    if args.cloud_storage_output_bucket:
      self.CopyResultsToCloudStorage()


def main():
  WindowsTemplateBuilder().Build()


if __name__ == "__main__":
  main()
