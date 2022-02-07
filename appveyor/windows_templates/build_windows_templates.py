#!/usr/bin/env python
#!/usr/bin/env python
"""Script to build windows templates."""

import argparse
import errno
import glob
import logging
import os
import shutil
import subprocess
import time

from typing import Callable

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

parser.add_argument(
    "--build_msi",
    dest="build_msi",
    default=False,
    action="store_true",
    help="Enable building of an MSI template.")

args = parser.parse_args()


_SC_STOP_WAIT_TIME_SECS = 10
_FILE_RETRY_LOOP_RETRY_TIME_SECS = 30


def _FileRetryLoop(path: str, f: Callable[[], None]) -> None:
  """If `path` exists, calls `f` in a retry loop."""
  if not os.path.exists(path):
    return
  attempts = 0
  while True:
    try:
      f()
      return
    except OSError as e:
      attempts += 1
      if (e.errno == errno.EACCES and
          attempts < _FILE_RETRY_LOOP_RETRY_TIME_SECS):
        # The currently installed GRR process may stick around for a few
        # seconds after the service is terminated (keeping the contents of
        # the installation directory locked).
        logging.info("Permission-denied error while trying to process %s.",
                     path)
        time.sleep(1)
      else:
        raise


def _RmTree(path: str) -> None:
  _FileRetryLoop(path, lambda: shutil.rmtree(path))


def _Rename(src: str, dst: str) -> None:
  _FileRetryLoop(src, lambda: os.rename(src, dst))


def _RmTreePseudoTransactional(path: str) -> None:
  """Removes `path`.

  Makes sure that either `path` is gone or that it is still present as
  it was.

  Args:
    path: The path to remove.
  """
  temp_path = f"{path}_orphaned_{int(time.time())}"
  logging.info("Trying to rename %s -> %s.", path, temp_path)

  _Rename(path, temp_path)

  try:
    logging.info("Trying to remove %s.", temp_path)
    _RmTree(temp_path)
  except:  # pylint: disable=bare-except
    logging.info("Failed to remove %s. Ignoring.", temp_path, exc_info=True)


def _VerboseCheckCall(params):
  logging.info("Running: %s", params)

  try:
    subprocess.check_call(params)
    logging.info("Finished successfully: %s", params)
  except Exception as e:
    logging.exception("Running %s raised:", params)
    raise


class WindowsTemplateBuilder(object):
  """Build windows templates."""

  def SetupVars(self):
    """Set up some vars for the directories we use."""
    # Python paths chosen to match appveyor:
    # http://www.appveyor.com/docs/installed-software#python

    self.virtualenv64 = os.path.join(args.build_dir, "python_64")
    self.grr_client_build64 = "grr_client_build"
    self.virtualenv_python64 = os.path.join(self.virtualenv64,
                                            r"Scripts\python.exe")

    self.git = r"git"

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
    subprocess.check_call(["virtualenv", self.virtualenv64])

    # Currently this should do nothing as we will already have a modern pip
    # installed, but we leave this here so if we get broken by pip again it's
    # just a simple case of searching for pip>=21.0.1 and adding an upper limit
    # cap in all those places.

    cmd = ["-m", "pip", "install"]
    if args.wheel_dir:
      cmd += ["--no-index", r"--find-links=file:///%s" % args.wheel_dir]

    subprocess.check_call(["python"] + cmd + ["--upgrade", "pip>=21.0.1"])
    subprocess.check_call(["pip", "debug", "--verbose"])

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
    os.chdir(os.path.join(args.grr_src, "grr/core"))
    subprocess.check_call([
        self.virtualenv_python64, "setup.py", "sdist", "--formats=zip",
        "--dist-dir=%s" % args.build_dir, "--no-sync-artifacts"
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

  def MakeClientBuilderSdist(self):
    os.chdir(os.path.join(args.grr_src, "grr/client_builder/"))
    subprocess.check_call([
        self.virtualenv_python64, "setup.py", "sdist", "--formats=zip",
        "--dist-dir=%s" % args.build_dir
    ])
    return glob.glob(
        os.path.join(args.build_dir,
                     "grr-response-client-builder-*.zip")).pop()

  def InstallGRR(self, path):
    """Installs GRR."""

    cmd64 = ["pip", "install"]

    if args.wheel_dir:
      cmd64 += ["--no-index", r"--find-links=file:///%s" % args.wheel_dir]

    cmd64.append(path)

    subprocess.check_call(cmd64)

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
    if args.build_msi:
      wix_tools_path = self._WixToolsPath()
      build_args += [
          "-p",
          "ClientBuilder.wix_tools_path=%{" + wix_tools_path + "}",
          "-p",
          "ClientBuilder.build_msi=true",
      ]
    _VerboseCheckCall([self.grr_client_build64] + build_args)

  def _WixToolsPath(self) -> str:
    matches = glob.glob("C:\\Program Files*\\WiX Toolset*")
    if not matches:
      raise Exception("Couldn't find WiX Toolset.")
    return matches[0]

  def _RepackTemplates(self):
    """Repack templates with a dummy config."""
    dummy_config = os.path.join(
        args.grr_src, "grr/test/grr_response_test/test_data/dummyconfig.yaml")
    template_amd64 = glob.glob(os.path.join(args.output_dir,
                                            "*_amd64*.zip")).pop()

    # We put the installers in the output dir so they get stored as build
    # artifacts.
    _VerboseCheckCall([
        self.grr_client_build64, "--verbose", "--secondary_configs",
        dummy_config, "repack", "--template", template_amd64, "--output_dir",
        args.output_dir
    ])
    _VerboseCheckCall([
        self.grr_client_build64, "--verbose", "--context",
        "DebugClientBuild Context", "--secondary_configs", dummy_config,
        "repack", "--template", template_amd64, "--output_dir", args.output_dir
    ])

  def _WaitForServiceToStop(self) -> bool:
    """Waits for the GRR monitor service to stop."""
    logging.info("Waiting for service %s to stop.", self.service_name)
    for _ in range(_SC_STOP_WAIT_TIME_SECS):
      command = ["sc", "query", self.service_name]
      output = subprocess.check_output(command, encoding="utf-8")
      logging.info("Command %s returned %s.", command, output)
      if "STOPPED" in output:
        return True
      time.sleep(1.0)
    return False

  def _CleanupInstall(self):
    """Cleanup from any previous installer enough for _CheckInstallSuccess."""
    logging.info("Stoping service %s.", self.service_name)
    _VerboseCheckCall(["sc", "stop", self.service_name])

    if args.build_msi:
      msiexec_args = [
          "msiexec",
          "/q",
          "/x",
          glob.glob(os.path.join(args.output_dir,
                                 "dbg_*_amd64.msi")).pop().replace("/", "\\"),
      ]
      _VerboseCheckCall(msiexec_args)
    else:
      self._WaitForServiceToStop()
      if os.path.exists(self.install_path):
        _RmTreePseudoTransactional(self.install_path)
        if os.path.exists(self.install_path):
          raise RuntimeError("Install path still exists: %s" %
                             self.install_path)

  def _CheckInstallSuccess(self):
    """Checks if the installer installed correctly."""
    if not os.path.exists(self.install_path):
      raise RuntimeError("Install failed, no files at: %s" % self.install_path)

    try:
      output = subprocess.check_output(["sc", "query", self.service_name],
                                       encoding="utf-8")
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
    if args.build_msi:
      installer_amd64_args = [
          "msiexec",
          "/qn",
          "/norestart",
          "/passive",
          "/i",
          glob.glob(os.path.join(args.output_dir,
                                 "dbg_*_amd64.msi")).pop().replace("/", "\\"),
      ]
    else:
      installer_amd64_args = [
          glob.glob(os.path.join(args.output_dir, "dbg_*_amd64.exe")).pop()
      ]

    # The exit code is always 0, test to see if install was actually successful.
    _VerboseCheckCall(installer_amd64_args)

    self._CheckInstallSuccess()
    self._CleanupInstall()

  def Build(self):
    """Build templates."""
    self.SetupVars()
    self.Clean()

    if not os.path.exists(args.grr_src):
      self.GitCheckoutGRR()
    proto_sdist = self.MakeProtoSdist()
    core_sdist = self.MakeCoreSdist()
    client_sdist = self.MakeClientSdist()
    client_builder_sdist = self.MakeClientBuilderSdist()

    self.InstallGRR(proto_sdist)
    self.InstallGRR(core_sdist)
    self.InstallGRR(client_sdist)
    self.InstallGRR(client_builder_sdist)
    self.BuildTemplates()
    if args.test_repack_install:
      self._RepackTemplates()
      self._InstallInstallers()


def main():
  WindowsTemplateBuilder().Build()


if __name__ == "__main__":
  main()
