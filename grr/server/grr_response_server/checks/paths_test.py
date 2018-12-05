#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for path misconfiguration checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class PathsCheckTests(checks_test_lib.HostCheckTest):
  """Test the rsyslog checks."""

  check_loaded = False
  parser = None

  def setUp(self, *args, **kwargs):
    super(PathsCheckTests, self).setUp(*args, **kwargs)
    if not self.check_loaded:
      self.check_loaded = self.LoadCheck("paths.yaml")
    if not self.parser:
      self.parser = linux_file_parser.PathParser()

  def testDetectCwdOk(self):
    chk_id = "CIS-PATH-UNSAFE-VALUE"
    paths = {
        "/root/.bashrc": "PATH=/foo/bar:$PATH",
        "/etc/csh.login": "set path=(/foo/bar)",
        "/home/user1": "export PYTHONPATH="
    }
    host_data = self.GenFileData("AllShellConfigs", paths, self.parser)
    results = self.RunChecks(host_data)
    self.assertCheckUndetected(chk_id, results)

  def testDetectIssues(self):
    paths = {
        "/root/.bashrc": "PATH=$PATH::other",
        "/etc/csh.login": "set path=(/foo/bar . /baz)",
        "/home/user1": "export PYTHONPATH=."
    }
    modes = {
        "/root/.bashrc": {
            "st_uid": 1,
            "st_gid": 0,
            "st_mode": 0o100666
        },
        "/etc/csh.login": {
            "st_uid": 0,
            "st_gid": 1,
            "st_mode": 0o100644
        },
        "/home/user1": {
            "st_uid": 1,
            "st_gid": 1,
            "st_mode": 0o100664
        }
    }
    host_data = self.GenFileData("AllShellConfigs", paths, self.parser, modes)
    host_data.update(
        self.GenFileData(
            "GlobalShellConfigs",
            paths,
            self.parser,
            modes,
            include=["/etc/csh.login"]))
    host_data.update(
        self.GenFileData(
            "RootUserShellConfigs",
            paths,
            self.parser,
            modes,
            include=["/root.bashrc"]))
    results = self.RunChecks(host_data)

    chk_id = "CIS-PATH-UNSAFE-VALUE"
    exp = "Found: Paths include unsafe values."
    found = [
        "/root/.bashrc sets PATH to $PATH,.,other",
        "/etc/csh.login sets PATH to /foo/bar,.,/baz",
        "/home/user1 sets PYTHONPATH to ."
    ]
    self.assertCheckDetectedAnom(chk_id, results, exp, found)

    chk_id = "CIS-DOTFILE-FILE-PERMISSIONS"
    exp = "Found: Dotfile permissions allow modification by others."
    found = [
        "/root/.bashrc user: 1, group: 0, mode: -rw-rw-rw-",
        "/home/user1 user: 1, group: 1, mode: -rw-rw-r--"
    ]
    self.assertCheckDetectedAnom(chk_id, results, exp, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
