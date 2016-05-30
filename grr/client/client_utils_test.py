#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test client utility functions."""


import exceptions
import imp
import os
import sys
import tempfile
import time
import mox

from grr.client import client_utils_common
from grr.client import client_utils_linux
from grr.client import client_utils_osx
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


def GetVolumePathName(_):
  return "C:\\"


def GetVolumeNameForVolumeMountPoint(_):
  return "\\\\?\\Volume{11111}\\"


class ClientUtilsTest(test_lib.GRRBaseTest):
  """Test the client utils."""

  def testLinGetRawDevice(self):
    """Test the parser for linux mounts."""
    proc_mounts = """rootfs / rootfs rw 0 0
none /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
none /proc proc rw,nosuid,nodev,noexec,relatime 0 0
none /dev devtmpfs rw,relatime,size=4056920k,nr_inodes=1014230,mode=755 0 0
none /dev/pts devpts rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
/dev/mapper/root / ext4 rw,relatime,errors=remount-ro,barrier=1,data=ordered 0 0
none /sys/fs/fuse/connections fusectl rw,relatime 0 0
none /sys/kernel/debug debugfs rw,relatime 0 0
none /sys/kernel/security securityfs rw,relatime 0 0
none /dev/shm tmpfs rw,nosuid,nodev,relatime 0 0
none /var/run tmpfs rw,nosuid,relatime 0 0
none /var/lock tmpfs rw,nosuid,nodev,noexec,relatime 0 0
none /lib/init/rw tmpfs rw,nosuid,relatime,mode=755 0 0
/dev/sda1 /boot ext2 rw,relatime,errors=continue 0 0
/dev/mapper/usr /usr/local/ ext4 rw,relatime,barrier=1,data=writeback 0 0
binfmt_misc /proc/sys/fs/binfmt_misc binfmt_misc rw,nosuid,relatime 0 0
server.nfs:/vol/home /home/user nfs rw,nosuid,relatime 0 0
"""
    mountpoints = client_utils_linux.GetMountpoints(proc_mounts)

    def GetMountpointsMock():
      return mountpoints

    old_getmountpoints = client_utils_linux.GetMountpoints
    client_utils_linux.GetMountpoints = GetMountpointsMock

    for filename, expected_device, expected_path, device_type in [
        ("/etc/passwd", "/dev/mapper/root", "/etc/passwd",
         rdf_paths.PathSpec.PathType.OS),
        ("/usr/local/bin/ls", "/dev/mapper/usr", "/bin/ls",
         rdf_paths.PathSpec.PathType.OS), ("/proc/net/sys", "none", "/net/sys",
                                           rdf_paths.PathSpec.PathType.UNSET),
        ("/home/user/test.txt", "server.nfs:/vol/home", "/test.txt",
         rdf_paths.PathSpec.PathType.UNSET)
    ]:
      raw_pathspec, path = client_utils_linux.LinGetRawDevice(filename)

      self.assertEqual(expected_device, raw_pathspec.path)
      self.assertEqual(device_type, raw_pathspec.pathtype)
      self.assertEqual(expected_path, path)
      client_utils_linux.GetMountpoints = old_getmountpoints

  def testWinSplitPathspec(self):
    """Test windows split pathspec functionality."""

    self.SetupWinEnvironment()

    # We need to import after SetupWinEnvironment or this will fail
    # pylint: disable=g-import-not-at-top
    from grr.client import client_utils_windows
    # pylint: enable=g-import-not-at-top

    testdata = [(r"C:\Windows", "\\\\?\\Volume{11111}", "/Windows"),
                (r"C:\\Windows\\", "\\\\?\\Volume{11111}", "/Windows"),
                (r"C:\\", "\\\\?\\Volume{11111}", "/")]

    for filename, expected_device, expected_path in testdata:
      raw_pathspec, path = client_utils_windows.WinGetRawDevice(filename)

      # Pathspec paths are always absolute and therefore must have a leading /.
      self.assertEqual(expected_device, raw_pathspec.path)
      self.assertEqual(expected_path, path)

  def SetupWinEnvironment(self):
    """Mock windows includes."""

    winreg = imp.new_module("_winreg")
    winreg.error = exceptions.Exception
    sys.modules["_winreg"] = winreg

    ntsecuritycon = imp.new_module("ntsecuritycon")
    sys.modules["ntsecuritycon"] = ntsecuritycon

    pywintypes = imp.new_module("pywintypes")
    pywintypes.error = Exception
    sys.modules["pywintypes"] = pywintypes

    winfile = imp.new_module("win32file")
    winfile.GetVolumeNameForVolumeMountPoint = GetVolumeNameForVolumeMountPoint
    winfile.GetVolumePathName = GetVolumePathName
    sys.modules["win32file"] = winfile

    win32security = imp.new_module("win32security")
    sys.modules["win32security"] = win32security

    win32api = imp.new_module("win32api")
    sys.modules["win32api"] = win32api

    win32service = imp.new_module("win32service")
    sys.modules["win32service"] = win32service
    win32serviceutil = imp.new_module("win32serviceutil")
    sys.modules["win32serviceutil"] = win32serviceutil
    winerror = imp.new_module("winerror")
    sys.modules["winerror"] = winerror

  def testExecutionWhiteList(self):
    """Test if unknown commands are filtered correctly."""

    # ls is not allowed
    (stdout, stderr, status, _) = client_utils_common.Execute("ls", ["."])
    self.assertEqual(status, -1)
    self.assertEqual(stdout, "")
    self.assertEqual(stderr, "Execution disallowed by whitelist.")

    # "echo 1" is
    (stdout, stderr, status, _) = client_utils_common.Execute("/bin/echo",
                                                              ["1"])
    self.assertEqual(status, 0)
    self.assertEqual(stdout, "1\n")
    self.assertEqual(stderr, "")

    # but not "echo 11"
    (stdout, stderr, status, _) = client_utils_common.Execute("/bin/echo",
                                                              ["11"])
    self.assertEqual(status, -1)
    self.assertEqual(stdout, "")
    self.assertEqual(stderr, "Execution disallowed by whitelist.")

  def AppendTo(self, list_obj, element):
    list_obj.append(element)

  def testExecutionTimeLimit(self):
    """Test if the time limit works."""

    (_, _, _, time_used) = client_utils_common.Execute("/bin/sleep", ["10"], 1)

    # This should take just a bit longer than one second.
    self.assertTrue(time_used < 2.0)

  def testLinuxNanny(self):
    """Tests the linux nanny."""
    # Starting nannies is disabled in tests. For this one we need it.
    self.nanny_stubber.Stop()
    self.exit_called = False

    def MockExit(value):
      self.exit_called = value
      # Kill the nanny thread.
      raise RuntimeError("Nannythread exiting.")

    with utils.Stubber(os, "_exit", MockExit):
      nanny_controller = client_utils_linux.NannyController()
      nanny_controller.StartNanny(unresponsive_kill_period=0.5)

      for _ in range(10):
        # Unfortunately we really need to sleep because we cant mock out
        # time.time.
        time.sleep(0.1)
        nanny_controller.Heartbeat()

      self.assertEqual(self.exit_called, False)

      # Main thread sleeps for long enough for the nanny to fire.
      time.sleep(1)
      self.assertEqual(self.exit_called, -1)

      nanny_controller.StopNanny()

  def testLinuxNannyLog(self):
    """Tests the linux nanny transaction log."""
    with tempfile.NamedTemporaryFile() as fd:
      nanny_controller = client_utils_linux.NannyController()
      nanny_controller.StartNanny(nanny_logfile=fd.name)
      grr_message = rdf_flows.GrrMessage(session_id="W:test")

      nanny_controller.WriteTransactionLog(grr_message)
      self.assertRDFValuesEqual(grr_message,
                                nanny_controller.GetTransactionLog())
      nanny_controller.CleanTransactionLog()

      self.assertIsNone(nanny_controller.GetTransactionLog())

      nanny_controller.StopNanny()


class OSXVersionTests(test_lib.GRRBaseTest):

  def setUp(self):
    super(OSXVersionTests, self).setUp()
    self.mox = mox.Mox()
    self.mac_ver = ("10.8.1", ("", "", ""), "x86_64")

    self.mox.StubOutWithMock(client_utils_osx.platform, "mac_ver")
    client_utils_osx.platform.mac_ver().AndReturn(self.mac_ver)

  def testVersionAsIntArray(self):
    self.mox.ReplayAll()
    osversion = client_utils_osx.OSXVersion()
    self.assertEqual(osversion.VersionAsMajorMinor(), [10, 8])
    self.mox.VerifyAll()

  def testVersionString(self):
    self.mox.ReplayAll()
    osversion = client_utils_osx.OSXVersion()
    self.assertEqual(osversion.VersionString(), "10.8.1")
    self.mox.VerifyAll()

  def tearDown(self):
    self.mox.UnsetStubs()
    super(OSXVersionTests, self).tearDown()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
