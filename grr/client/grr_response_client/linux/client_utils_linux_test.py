#!/usr/bin/env python
"""Tests for client_utils_linux.py."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import platform
import tempfile
import unittest

from absl import app
from absl.testing import absltest
from future.builtins import range
import mock

from grr_response_client import client_utils_linux
from grr_response_client import client_utils_osx_linux
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr.test_lib import filesystem_test_lib
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
         rdf_paths.PathSpec.PathType.OS),
        ("/proc/net/sys", "none", "/net/sys",
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

    def MockExit(unused_value):
      raise RuntimeError("Exit was called.")

    now = rdfvalue.RDFDatetime.Now()

    with utils.Stubber(os, "_exit", MockExit):
      nanny = client_utils_osx_linux.NannyThread(unresponsive_kill_period=5)
      with test_lib.FakeTime(now):
        nanny.Heartbeat()

      for i in range(10):
        with test_lib.FakeTime(now + i * rdfvalue.Duration("1s")):
          nanny._CheckHeartbeatDeadline(nanny.last_heart_beat_time +
                                        nanny.unresponsive_kill_period)
          nanny.Heartbeat()

      with test_lib.FakeTime(now + (10 + 5) * rdfvalue.Duration("1s")):
        with self.assertRaises(RuntimeError):
          nanny._CheckHeartbeatDeadline(nanny.last_heart_beat_time +
                                        nanny.unresponsive_kill_period)

  def testLinuxTransactionLog(self):
    """Tests the linux transaction log."""
    with tempfile.NamedTemporaryFile() as fd:
      log = client_utils_linux.TransactionLog(logfile=fd.name)
      grr_message = rdf_flows.GrrMessage(session_id="W:test")

      log.Write(grr_message)
      self.assertEqual(grr_message, log.Get())
      log.Clear()

      self.assertIsNone(log.Get())


@unittest.skipIf(platform.system() != "Linux", "only Linux is supported")
class GetExtAttrsText(absltest.TestCase):

  def testEmpty(self):
    with temp.AutoTempFilePath() as temp_filepath:
      attrs = list(client_utils_linux.GetExtAttrs(temp_filepath))

      self.assertEmpty(attrs)

  def testMany(self):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.foo", value=b"bar")
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.quux", value=b"norf")

      attrs = list(client_utils_linux.GetExtAttrs(temp_filepath))

      self.assertLen(attrs, 2)
      self.assertEqual(attrs[0].name, b"user.foo")
      self.assertEqual(attrs[0].value, b"bar")
      self.assertEqual(attrs[1].name, b"user.quux")
      self.assertEqual(attrs[1].value, b"norf")

  def testIncorrectFilePath(self):
    attrs = list(client_utils_linux.GetExtAttrs("/foo/bar/baz/quux"))

    self.assertEmpty(attrs)

  @mock.patch("xattr.listxattr", return_value=[b"user.foo", b"user.bar"])
  def testAttrChangeAfterListing(self, listxattr):
    with temp.AutoTempFilePath() as temp_filepath:
      filesystem_test_lib.SetExtAttr(
          temp_filepath, name=b"user.bar", value=b"baz")

      attrs = list(client_utils_linux.GetExtAttrs(temp_filepath))

      self.assertTrue(listxattr.called)
      self.assertLen(attrs, 1)
      self.assertEqual(attrs[0].name, b"user.bar")
      self.assertEqual(attrs[0].value, b"baz")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
