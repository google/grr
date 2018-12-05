#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for stat checks."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class StatOnlyTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    super(StatOnlyTests, cls).setUpClass()

    cls.LoadCheck("stat.yaml")

  def testRootPATHCheck(self):
    """Ensure root $PATH check detects files that non-root users can edit."""

    data = [
        self.CreateStat("/usr/local/bin/hit-123", 50, 0, 0o0100640),
        self.CreateStat("/usr/local/bin/no-hit-123", 0, 6000, 0o0100440),
        self.CreateStat("/usr/local/bin/no-hit-234", 0, 0, 0o0100640),
        self.CreateStat("/usr/local/bin/hit-345", 70, 0, 0o0100660),
        self.CreateStat("/bin/hit-symlink-567", 70, 0, 0o0120777),
        self.CreateStat("/bin/no-hit-symlink-456", 0, 0, 0o0120777)
    ]

    results = self.GenResults(["RootEnvPath"], [data])

    check_id = "CIS-ROOT-PATH-HAS-FILES-WRITABLE-BY-NON-ROOT"
    sym = ("Found: Files in default $PATH of root can be modified "
           "by non-privileged users.")
    found = [
        "/usr/local/bin/hit-123 user: 50, group: 0, mode: -rw-r-----",
        "/usr/local/bin/hit-345 user: 70, group: 0, mode: -rw-rw----",
        "/bin/hit-symlink-567 user: 70, group: 0, mode: lrwxrwxrwx"
    ]
    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testRootPATHDirCheck(self):
    """Ensure root $PATH directory entries are editable only by root."""

    data = [
        # Bad cases:
        # Non-root group ownership & permissions.
        self.CreateStat("/usr/local/bin", 0, 60, 0o0040775),
        # File & Non-root owner.
        self.CreateStat("/bin", 70, 0, 0o0100660),
        # A non-root symlink.
        self.CreateStat("/usr/local/sbin", 1, 0, 0o0120777),
        # File not owned by root but has no write permissions.
        self.CreateStat("/sbin", 1, 0, 0o0100400),
        # Fully root owned dir, but world writable.
        self.CreateStat("/usr", 0, 0, 0o0040666),

        # Safe cases:
        self.CreateStat("/usr/local", 0, 0, 0o0040755),  # Root owned directory.
        self.CreateStat("/usr/bin", 0, 0, 0o0120777),  # Root owned symlink.
        self.CreateStat("/usr/sbin", 0, 0, 0o0100775)
    ]  # Root owned file.

    results = self.GenResults(["RootEnvPathDirs"], [data])

    check_id = "CIS-ROOT-PATH-HAS-FOLDERS-WRITABLE-BY-NON-ROOT"
    sym = ("Found: Folders that comprise the default $PATH of root can be "
           "modified by non-privileged users.")
    found = [
        "/usr/local/bin user: 0, group: 60, mode: drwxrwxr-x",
        "/bin user: 70, group: 0, mode: -rw-rw----",
        "/usr/local/sbin user: 1, group: 0, mode: lrwxrwxrwx",
        "/sbin user: 1, group: 0, mode: -r--------",
        "/usr user: 0, group: 0, mode: drw-rw-rw-"
    ]
    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testUserHomeDirCheck(self):
    """Ensure user home dir check detect folders modifiable by non-owners."""

    data = [
        self.CreateStat("/root", 0, 0, 0o0040750),
        self.CreateStat("/home/non-matching-user1", 1000, 600, 0o0040700),
        self.CreateStat("/home/user2", 200, 60, 0o0040770),
        self.CreateStat("/home/user3", 300, 70, 0o0040777),
        self.CreateStat("/home/user4", 400, 70, 0o0040760),
        self.CreateStat("/home/non-matching-user2", 500, 80, 0o0040755),
        self.CreateStat("/home/non-matching-user3", 2000, 800, 0o0040750),
        self.CreateStat("/home/non-matching-user4", 6000, 600, 0o0040751),
        self.CreateStat("/home/user8", 700, 70, 0o0040752)
    ]

    results = self.GenResults(["UserHomeDirs"], [data])

    check_id = "CIS-HOME-DIRS-WRITABLE-BY-NON-OWNERS"
    sym = ("Found: User home directory can be written to by "
           "group or others.")
    found = [
        "/home/user2 user: 200, group: 60, mode: drwxrwx---",
        "/home/user3 user: 300, group: 70, mode: drwxrwxrwx",
        "/home/user4 user: 400, group: 70, mode: drwxrw----",
        "/home/user8 user: 700, group: 70, mode: drwxr-x-w-",
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testUserDotFilesCheck(self):
    """Ensure user dot files check detects files that are world writable."""

    data = [
        self.CreateStat("/root/.bash_history", 0, 0, 0o0100755),
        self.CreateStat("/root/.bash_logout", 0, 0, 0o0100775),
        self.CreateStat("/root/.bashrc", 0, 0, 0o0100772),  # match
        self.CreateStat("/root/.gitconfig", 0, 0, 0o0100773),  # match
        self.CreateStat("/home/user/.mozilla", 100, 70, 0o0100755),
        self.CreateStat("/home/user/.vim", 100, 70, 0o0040777),  # match
        self.CreateStat("/home/user/.netrc", 100, 70, 0o0100664)
    ]

    results = self.GenResults(["UserDotFiles"], [data])

    check_id = "CIS-USER-DOT-FILES-DIRS-WORLD-WRITABLE"
    sym = ("Found: Dot files or folders in user home directory are world "
           "writable.")
    found = [
        "/root/.bashrc user: 0, group: 0, mode: -rwxrwx-w-",
        "/root/.gitconfig user: 0, group: 0, mode: -rwxrwx-wx",
        "/home/user/.vim user: 100, group: 70, mode: drwxrwxrwx",
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)

    check_id = "CIS-DOT-NETRC-FILE-EXISTS"
    sym = "Found: The .netrc file exists in a user's home directory."
    found = ["/home/user/.netrc user: 100, group: 70, mode: -rw-rw-r--"]

    self.assertCheckDetectedAnom(check_id, results, sym, found)

  def testLogFilesCheck(self):
    """Ensure log files check detects files modifiable by non-root."""

    data = [
        self.CreateStat("/var/log/syslog", 0, 0, 0o0100666),
        self.CreateStat("/var/log/auth.log.1", 0, 4, 0o0100774),
        self.CreateStat("/var/log/debug.1.gz", 10, 0, 0o0100774),
        self.CreateStat("/var/log/mail.log", 0, 2, 0o0100770),
        self.CreateStat("/var/log/user.log.1.gz", 0, 4, 0o0100642),
        self.CreateStat("/var/log/puppet/mail.log", 30, 70, 0o0100777),
        self.CreateStat("/var/log/dpkg.log", 200, 70, 0o0100664)
    ]

    results = self.GenResults(["LinuxLogFiles"], [data])

    check_id = "CIS-LOG-FILES-PERMISSIONS-WRONG-OWNER"
    sym = "Found: Vital system log files have wrong owner."
    found = [
        "/var/log/debug.1.gz user: 10, group: 0, mode: -rwxrwxr--",
        "/var/log/dpkg.log user: 200, group: 70, mode: -rw-rw-r--"
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)

    check_id = "CIS-LOG-FILES-PERMISSIONS-WRONG-GROUP"
    sym = "Found: Vital system log files have wrong group."
    found = [
        "/var/log/mail.log user: 0, group: 2, mode: -rwxrwx---",
        "/var/log/dpkg.log user: 200, group: 70, mode: -rw-rw-r--"
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)

    check_id = "CIS-LOG-FILES-PERMISSIONS-WORLD-WRITABLE"
    sym = "Found: Log files are world writable."
    found = [
        "/var/log/syslog user: 0, group: 0, mode: -rw-rw-rw-",
        "/var/log/puppet/mail.log user: 30, group: 70, mode: -rwxrwxrwx",
        "/var/log/user.log.1.gz user: 0, group: 4, mode: -rw-r---w-"
    ]

    self.assertCheckDetectedAnom(check_id, results, sym, found)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
