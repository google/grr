#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Linux only tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import __builtin__
import glob
import os

from grr_response_client.client_actions.linux import linux
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class LinuxOnlyTest(client_test_lib.EmptyActionTest):

  def testEnumerateUsersLinux(self):
    """Enumerate users from the wtmp file."""

    def MockedOpen(requested_path, mode="rb"):
      try:
        fixture_path = os.path.join(self.base_path, "VFSFixture",
                                    requested_path.lstrip("/"))
        return __builtin__.open.old_target(fixture_path, mode)
      except IOError:
        return __builtin__.open.old_target(requested_path, mode)

    with utils.MultiStubber((__builtin__, "open", MockedOpen),
                            (glob, "glob", lambda x: ["/var/log/wtmp"])):
      results = self.RunAction(linux.EnumerateUsers)

    found = 0
    for result in results:
      if result.username == "user1":
        found += 1
        self.assertEqual(result.last_logon, 1296552099 * 1000000)
      elif result.username == "user2":
        found += 1
        self.assertEqual(result.last_logon, 1296552102 * 1000000)
      elif result.username == "user3":
        found += 1
        self.assertEqual(result.last_logon, 1296569997 * 1000000)
      elif result.username == "utuser":
        self.assertEqual(result.last_logon, 1510318881 * 1000000)
      else:
        self.fail("Unexpected user found: %s" % result.username)

    self.assertEqual(found, 3)

  def testEnumerateFilesystemsLinux(self):
    """Enumerate filesystems."""

    def MockCheckMounts(unused_filename):
      del unused_filename  # Unused.
      device = "/dev/mapper/dhcp--100--104--9--24--vg-root"
      fs_type = "ext4"
      mnt_point = "/"
      yield device, fs_type, mnt_point

    with utils.Stubber(linux, "CheckMounts", MockCheckMounts):
      results = self.RunAction(linux.EnumerateFilesystems)

    expected = rdf_client_fs.Filesystem(
        mount_point="/",
        type="ext4",
        device="/dev/mapper/dhcp--100--104--9--24--vg-root")

    self.assertLen(results, 2)
    for result in results:
      self.assertEqual(result, expected)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
