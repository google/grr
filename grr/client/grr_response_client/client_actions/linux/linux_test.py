#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Linux only tests."""

import __builtin__
import glob
import os

from grr_response_client.client_actions.linux import linux
from grr.lib import flags
from grr.lib import utils
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


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
