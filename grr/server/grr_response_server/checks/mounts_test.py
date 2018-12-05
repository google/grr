#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for service state checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import config_file
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class LinuxMountsTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    super(LinuxMountsTests, cls).setUpClass()

    cls.LoadCheck("mounts.yaml")
    cls.parser = config_file.MtabParser()

  def testNoIssuesNoAnomalies(self):
    fstab = """
      proc       /proc              proc  defaults                    0  0
      /dev/sda1  /                  ext4  defaults,errors=remount-ro  0  1
      /dev/sda4  /dev               ext4  defaults                    0  2
      /dev/sdb1  /boot              ext4  defaults                    0  0
      /dev/sda2  none               swap  sw                          0  0
    """
    data = {"/etc/fstab": fstab}
    host_data = self.GenFileData("LinuxFstab", data, self.parser)

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
    host_data = self.GenFileData("LinuxFstab", data, self.parser)

    check_id = "CIS-MOUNT-OPTION-NO-DEV"
    results = self.RunChecks(host_data)

    sym = "Found: Non-system mountpoints allow devices"
    # Mount options have variable ordering, so do a substring match.
    found = ["/media: /dev/sda2 mounted", "/tmp/media: /dev/sda3 mounted"]
    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testNoUserSUIDAllowed(self):
    fstab = """
      /dev/sda1  /                  ext4  defaults,errors=remount-ro  0  1
      /dev/sda2  /media             ext2  user                        0  1
      /dev/sda3  /tmp/media         xfs   nosuid,user                 0  1
    """
    data = {"/etc/fstab": fstab}
    host_data = self.GenFileData("LinuxFstab", data, self.parser)

    check_id = "CIS-MOUNT-OPTION-NO-USER-SUID"
    results = self.RunChecks(host_data)

    sym = "Found: User mountable media allows suid"
    found = ["/media: /dev/sda2 mounted with user:True"]
    self.assertCheckDetectedAnom(check_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
