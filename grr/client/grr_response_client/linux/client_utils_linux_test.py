#!/usr/bin/env python
"""Tests for client_utils_linux.py."""

import os
import tempfile
import time

from grr_response_client import client_utils_linux
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


class ClientUtilsLinuxTest(test_lib.GRRBaseTest):
  """Test the linux client utils."""

  def testLinuxGetRawDevice(self):
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
      raw_pathspec, path = client_utils_linux.GetRawDevice(filename)

      self.assertEqual(expected_device, raw_pathspec.path)
      self.assertEqual(device_type, raw_pathspec.pathtype)
      self.assertEqual(expected_path, path)
      client_utils_linux.GetMountpoints = old_getmountpoints

  def testLinuxNanny(self):
    """Tests the linux nanny."""
    self.exit_called = False

    def MockExit(value):
      self.exit_called = value
      # Kill the nanny thread.
      raise RuntimeError("Nannythread exiting.")

    with utils.Stubber(os, "_exit", MockExit):
      nanny_controller = client_utils_linux.NannyController()
      nanny_controller.StartNanny(unresponsive_kill_period=0.5)
      try:
        for _ in range(10):
          # Unfortunately we really need to sleep because we cant mock out
          # time.time.
          time.sleep(0.1)
          nanny_controller.Heartbeat()

        self.assertEqual(self.exit_called, False)

        # Main thread sleeps for long enough for the nanny to fire.
        time.sleep(1)
        self.assertEqual(self.exit_called, -1)
      finally:
        nanny_controller.StopNanny()

  def testLinuxNannyLog(self):
    """Tests the linux nanny transaction log."""
    with tempfile.NamedTemporaryFile() as fd:
      nanny_controller = client_utils_linux.NannyController()
      nanny_controller.StartNanny(nanny_logfile=fd.name)
      try:
        grr_message = rdf_flows.GrrMessage(session_id="W:test")

        nanny_controller.WriteTransactionLog(grr_message)
        self.assertRDFValuesEqual(grr_message,
                                  nanny_controller.GetTransactionLog())
        nanny_controller.CleanTransactionLog()

        self.assertIsNone(nanny_controller.GetTransactionLog())

      finally:
        nanny_controller.StopNanny()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
