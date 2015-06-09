#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.parsers import config_file


class LinuxMountsTests(checks_test_lib.HostCheckTest):

  results = None
  check_loaded = False

  def setUp(self, *args, **kwargs):
    super(LinuxMountsTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.LoadCheck("mounts.yaml")
    self.check_loaded = True

  def testNoIssuesNoAnomalies(self):
    fstab = """
      proc       /proc              proc  defaults                    0  0
      /dev/sda1  /                  ext4  defaults,errors=remount-ro  0  1
      /dev/sda2  none               swap  sw                          0  0
    """
    data = {"/etc/fstab": fstab}
    parser = config_file.MtabParser()
    host_data = self.GetParsedFile("LinuxFstab", data, parser)

    check_id = "CIS-MOUNT-OPTION-NO-DEV"
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(check_id, results)

    check_id = "CIS-MOUNT-OPTION-NO-USER-SUID"
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(check_id, results)

  def testDeviceAllowed(self):
    fstab = """
      /dev/sda1  /                  ext4  defaults,errors=remount-ro  0  1
      /dev/sda2  /media             ext4  defaults                    0  1
      /dev/sda3  /tmp/media         ext3  noexec,ro                   0  1
    """
    data = {"/etc/fstab": fstab}
    parser = config_file.MtabParser()
    host_data = self.GetParsedFile("LinuxFstab", data, parser)

    check_id = "CIS-MOUNT-OPTION-NO-DEV"
    results = self.RunChecks(host_data)

    exp = "Found: Non-system mountpoints allow devices"
    # Mount options have variable ordering, so do a substring match.
    found = ["/media: /dev/sda2 mounted",
             "/tmp/media: /dev/sda3 mounted"]
    self.assertCheckDetectedAnom(check_id, results, exp, found)

  def testNoUserSUIDAllowed(self):
    fstab = """
      /dev/sda1  /                  ext4  defaults,errors=remount-ro  0  1
      /dev/sda2  /media             ext2  user                        0  1
      /dev/sda3  /tmp/media         xfs   nosuid,user                 0  1
    """
    data = {"/etc/fstab": fstab}
    parser = config_file.MtabParser()
    host_data = self.GetParsedFile("LinuxFstab", data, parser)

    check_id = "CIS-MOUNT-OPTION-NO-USER-SUID"
    results = self.RunChecks(host_data)

    exp = "Found: User mountable media allows suid"
    found = ["/media: /dev/sda2 mounted with user:True"]
    self.assertCheckDetectedAnom(check_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

