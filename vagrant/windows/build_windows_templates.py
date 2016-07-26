#!/usr/bin/env python
"""Script to build windows templates."""

import argparse
import glob
import os
import shutil
import subprocess

parser = argparse.ArgumentParser(description="Build windows templates.")

parser.add_argument(
    "--grr_src",
    default=r"C:\grrbuild\grr",
    help="Location of the grr src code. If it doesn't exist "
    " at this path we'll try to check it out from github.")

parser.add_argument(
    "--output_dir",
    default=r"C:\grrbuild\output",
    help="Location of the grr src code. If it doesn't exist "
    " at this path we'll check it out from github.")

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

args = parser.parse_args()


class WindowsTemplateBuilder(object):
  """Build windows templates and components."""

  # Python paths chosen to match appveyor:
  # http://www.appveyor.com/docs/installed-software#python
  PYTHON_DIR_64 = r"C:\Python27-x64"
  PYTHON_DIR_32 = r"C:\Python27"
  PYTHON_BIN64 = os.path.join(PYTHON_DIR_64, "python.exe")
  VIRTUALENV_BIN64 = os.path.join(PYTHON_DIR_64, r"Scripts\virtualenv.exe")
  VIRTUALENV_BIN32 = os.path.join(PYTHON_DIR_32, r"Scripts\virtualenv.exe")
  BUILDDIR = r"C:\grrbuild"
  VIRTUALENV64 = os.path.join(BUILDDIR, r"PYTHON_64")
  VIRTUALENV32 = os.path.join(BUILDDIR, r"PYTHON_32")
  VIRTUALENV_ACTIVATE64 = os.path.join(VIRTUALENV64, r"Scripts\activate")
  VIRTUALENV_ACTIVATE32 = os.path.join(VIRTUALENV32, r"Scripts\activate")
  GRR_CLIENT_BUILD64 = os.path.join(VIRTUALENV64,
                                    r"Scripts\grr_client_build.exe")
  GRR_CLIENT_BUILD32 = os.path.join(VIRTUALENV32,
                                    r"Scripts\grr_client_build.exe")
  PIP64 = os.path.join(VIRTUALENV64, r"Scripts\pip.exe")
  PIP32 = os.path.join(VIRTUALENV32, r"Scripts\pip.exe")

  PROTOC = r"C:\grr_deps\protoc\protoc.exe"
  GIT = r"C:\Program Files\Git\bin\git.exe"

  INSTALL_PATH = r"C:\Windows\System32\GRR"
  SERVICE_NAME = "GRR Monitor"

  def Clean(self):
    """Clean the build environment."""
    # os.unlink doesn't work effectively, use the shell to delete.
    subprocess.call("rd /s /q %s" % self.BUILDDIR, shell=True)
    subprocess.call("rd /s /q %s" % args.output_dir, shell=True)

    os.makedirs(self.BUILDDIR)
    os.makedirs(args.output_dir)

    # Create virtualenvs and make sure virtualenv itself is installed inside
    # them (otherwise component build fails).
    subprocess.check_call([self.VIRTUALENV_BIN64, self.VIRTUALENV64])
    subprocess.check_call([self.VIRTUALENV_BIN32, self.VIRTUALENV32])
    subprocess.check_call([self.PIP64, "install", "--upgrade", "virtualenv"])
    subprocess.check_call([self.PIP32, "install", "--upgrade", "virtualenv"])

    os.environ["PROTOC"] = self.PROTOC

  def GitCheckoutGRR(self):
    os.chdir(self.BUILDDIR)
    subprocess.check_call(
        [self.GIT, "clone", "https://github.com/google/grr.git"])

  def MakeCoreSdist(self):
    os.chdir(args.grr_src)
    subprocess.check_call([self.PYTHON_BIN64, "setup.py", "sdist",
                           "--dist-dir=%s" % self.BUILDDIR, "--no-make-docs",
                           "--no-make-ui-files", "--no-sync-artifacts"])
    return glob.glob(os.path.join(self.BUILDDIR,
                                  "grr-response-core-*.zip")).pop()

  def MakeClientSdist(self):
    os.chdir(os.path.join(args.grr_src, "grr/config/grr-response-client/"))
    subprocess.check_call([self.PYTHON_BIN64, "setup.py", "sdist",
                           "--dist-dir=%s" % self.BUILDDIR])
    return glob.glob(os.path.join(self.BUILDDIR,
                                  "grr-response-client-*.zip")).pop()

  def CopySdistsFromCloudStorage(self):
    """Use gsutil to copy sdists from cloud storage."""
    subprocess.check_call([args.gsutil, "cp",
                           "gs://%s/grr-response-core-*.zip" %
                           args.cloud_storage_sdist_bucket, self.BUILDDIR])
    core = glob.glob(os.path.join(self.BUILDDIR,
                                  "grr-response-core-*.zip")).pop()

    subprocess.check_call([args.gsutil, "cp",
                           "gs://%s/grr-response-client-*.zip" %
                           args.cloud_storage_sdist_bucket, self.BUILDDIR])
    client = glob.glob(os.path.join(self.BUILDDIR,
                                    "grr-response-client-*.zip")).pop()
    return core, client

  def InstallGRR(self, path):
    subprocess.check_call([self.PIP64, "install", "--upgrade", path])
    subprocess.check_call([self.PIP32, "install", "--upgrade", path])

  def BuildTemplates(self):
    """Build client templates.

    We dont need to run special compilers so just enter the virtualenv and
    build. Python will already find its own MSVC for python compilers.
    """
    subprocess.check_call([self.GRR_CLIENT_BUILD64, "--verbose", "build",
                           "--output", args.output_dir])
    subprocess.check_call([self.GRR_CLIENT_BUILD32, "--verbose", "build",
                           "--output", args.output_dir])

  def BuildComponents(self):
    subprocess.check_call([self.GRR_CLIENT_BUILD64, "--verbose",
                           "build_components", "--output", args.output_dir])
    subprocess.check_call([self.GRR_CLIENT_BUILD32, "--verbose",
                           "build_components", "--output", args.output_dir])

  def _RepackTemplates(self):
    """Repack templates with a dummy config."""
    dummy_config = os.path.join(
        args.grr_src, "grr/config/grr-response-test/test_data/dummyconfig.yaml")
    template_i386 = glob.glob(os.path.join(args.output_dir, "*_i386*.zip")).pop(
    )
    template_amd64 = glob.glob(os.path.join(args.output_dir,
                                            "*_amd64*.zip")).pop()

    # We put the installers in the output dir so they get stored as build
    # artifacts and we can test the 32bit build manually.
    subprocess.check_call([self.GRR_CLIENT_BUILD64, "--verbose",
                           "--secondary_configs", dummy_config, "repack",
                           "--template", template_amd64, "--output_dir",
                           args.output_dir])
    subprocess.check_call([self.GRR_CLIENT_BUILD64, "--verbose", "--context",
                           "DebugClientBuild Context", "--secondary_configs",
                           dummy_config, "repack", "--template", template_amd64,
                           "--output_dir", args.output_dir])
    subprocess.check_call([self.GRR_CLIENT_BUILD32, "--verbose",
                           "--secondary_configs", dummy_config, "repack",
                           "--template", template_i386, "--output_dir",
                           args.output_dir])
    subprocess.check_call([self.GRR_CLIENT_BUILD32, "--verbose", "--context",
                           "DebugClientBuild Context", "--secondary_configs",
                           dummy_config, "repack", "--template", template_i386,
                           "--output_dir", args.output_dir])

  def _CleanupInstall(self):
    """Cleanup from any previous installer enough for _CheckInstallSuccess."""
    shutil.rmtree(self.INSTALL_PATH)
    if os.path.exists(self.INSTALL_PATH):
      raise RuntimeError("Install path still exists: %s" % self.INSTALL_PATH)

    # Deliberately don't check return code, since service may not be installed.
    subprocess.call(["sc", "stop", self.SERVICE_NAME])
    output = subprocess.check_output(["sc", "query", self.SERVICE_NAME])
    if "RUNNING" in output:
      raise RuntimeError("Service still running: %s" % output)

  def _CheckInstallSuccess(self):
    """Check if installer installed correctly."""
    if not os.path.exists(self.INSTALL_PATH):
      raise RuntimeError("Install failed, no files at: %s" % self.INSTALL_PATH)

    output = subprocess.check_output(["sc", "query", self.SERVICE_NAME])
    if "RUNNING" not in output:
      raise RuntimeError(
          "GRR service not running after install, sc query output: %s" % output)

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
    subprocess.check_call([args.gsutil, "-m", "cp"] + paths + [
        "gs://%s/" % args.cloud_storage_output_bucket
    ])

  def Build(self):
    """Build templates and components."""
    self.Clean()
    if args.cloud_storage_sdist_bucket:
      core_sdist, client_sdist = self.CopySdistsFromCloudStorage()
    else:
      if not os.path.exists(args.grr_src):
        self.GitCheckoutGRR()
      core_sdist = self.MakeCoreSdist()
      client_sdist = self.MakeClientSdist()
    self.InstallGRR(core_sdist)
    self.InstallGRR(client_sdist)
    self.BuildTemplates()
    self.BuildComponents()
    if args.test_repack_install:
      self._RepackTemplates()
      self._InstallInstallers()
    if args.cloud_storage_output_bucket:
      self.CopyResultsToCloudStorage()


def main():
  WindowsTemplateBuilder().Build()


if __name__ == "__main__":
  main()
