#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for stat checks."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib


class StatOnlyTests(checks_test_lib.HostCheckTest):

  @classmethod
  def setUpClass(cls):
    cls.LoadCheck("stat.yaml")

  def testRootPATHCheck(self):
    """Ensure root $PATH check detects files that non-root users can edit."""

    data = [self.CreateStat("/usr/local/bin/hit-123", 50, 0, 0o0100640),
            self.CreateStat("/usr/local/bin/hit-234", 0, 60, 0o0040777),
            self.CreateStat("/usr/local/bin/no-hit-123", 0, 6000, 0o0100440),
            self.CreateStat("/usr/local/bin/no-hit-234", 0, 0, 0o0100640),
            self.CreateStat("/usr/local/bin/hit-345", 70, 0, 0o0100660)]

    results = self.GenResults(["RootEnvPath"], [data])

    check_id = "CIS-ROOT-PATH-HAS-FILES-FOLDERS-WRITABLE-BY-NON-ROOT"
    exp = ("Found: Files or folders in default $PATH of root can be modified "
           "by non-privileged users.\n")
    found = ["/usr/local/bin/hit-123 user: 50, group: 0, mode: -rw-r-----\n",
             "/usr/local/bin/hit-234 user: 0, group: 60, mode: drwxrwxrwx\n",
             "/usr/local/bin/hit-345 user: 70, group: 0, mode: -rw-rw----\n",]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

  def testUserHomeDirCheck(self):
    """Ensure user home dir check detect folders modifiable by non-owners."""

    data = [self.CreateStat("/root", 0, 0, 0o0040750),
            self.CreateStat("/home/non-matching-user1", 1000, 600, 0o0040700),
            self.CreateStat("/home/user2", 200, 60, 0o0040770),
            self.CreateStat("/home/user3", 300, 70, 0o0040777),
            self.CreateStat("/home/user4", 400, 70, 0o0040760),
            self.CreateStat("/home/non-matching-user2", 500, 80, 0o0040755),
            self.CreateStat("/home/non-matching-user3", 2000, 800, 0o0040750),
            self.CreateStat("/home/non-matching-user4", 6000, 600, 0o0040751),
            self.CreateStat("/home/user8", 700, 70, 0o0040752)]

    results = self.GenResults(["UserHomeDirs"], [data])

    check_id = "CIS-HOME-DIRS-WRITABLE-BY-NON-OWNERS"
    exp = ("Found: User home dirctory can be written to by "
           "group or others.\n")
    found = ["/home/user2 user: 200, group: 60, mode: drwxrwx---\n",
             "/home/user3 user: 300, group: 70, mode: drwxrwxrwx\n",
             "/home/user4 user: 400, group: 70, mode: drwxrw----\n",
             "/home/user8 user: 700, group: 70, mode: drwxr-x-w-\n",]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

  def testUserDotFilesCheck(self):
    """Ensure user dot files check detects files that are world writable."""

    data = [self.CreateStat("/root/.bash_history", 0, 0, 0o0100755),
            self.CreateStat("/root/.bash_logout", 0, 0, 0o0100775),
            self.CreateStat("/root/.bashrc", 0, 0, 0o0100772),  # match
            self.CreateStat("/root/.gitconfig", 0, 0, 0o0100773),  # match
            self.CreateStat("/home/user/.mozilla", 100, 70, 0o0100755),
            self.CreateStat("/home/user/.vim", 100, 70, 0o0040777),  # match
            self.CreateStat("/home/user/.netrc", 100, 70, 0o0100664)]

    results = self.GenResults(["UserDotFiles"], [data])

    check_id = "CIS-USER-DOT-FILES-DIRS-WORLD-WRITABLE"
    exp = ("Found: Dot files or folders in user home dirctory are world "
           "writable.\n")
    found = ["/root/.bashrc user: 0, group: 0, mode: -rwxrwx-w-\n",
             "/root/.gitconfig user: 0, group: 0, mode: -rwxrwx-wx\n",
             "/home/user/.vim user: 100, group: 70, mode: drwxrwxrwx\n",]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

    check_id = "CIS-DOT-NETRC-FILE-EXISTS"
    exp = "Found: The .netrc file exists in a user's home directory.\n"
    found = ["/home/user/.netrc user: 100, group: 70, mode: -rw-rw-r--\n"]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

  def testLogFilesCheck(self):
    """Ensure log files check detects files modifiable by non-root."""

    data = [self.CreateStat("/var/log/syslog", 0, 0, 0o0100666),
            self.CreateStat("/var/log/auth.log.1", 0, 4, 0o0100774),
            self.CreateStat("/var/log/debug.1.gz", 10, 0, 0o0100774),
            self.CreateStat("/var/log/mail.log", 0, 2, 0o0100770),
            self.CreateStat("/var/log/user.log.1.gz", 0, 4, 0o0100642),
            self.CreateStat("/var/log/puppet/mail.log", 30, 70, 0o0100777),
            self.CreateStat("/var/log/dpkg.log", 200, 70, 0o0100664)]

    results = self.GenResults(["LinuxLogFiles"], [data])

    check_id = "CIS-LOG-FILES-PERMISSIONS-WRONG-OWNER"
    exp = "Found: Vital system log files have wrong owner."
    found = ["/var/log/debug.1.gz user: 10, group: 0, mode: -rwxrwxr--\n",
             "/var/log/dpkg.log user: 200, group: 70, mode: -rw-rw-r--\n"]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

    check_id = "CIS-LOG-FILES-PERMISSIONS-WRONG-GROUP"
    exp = "Found: Vital system log files have wrong group."
    found = ["/var/log/mail.log user: 0, group: 2, mode: -rwxrwx---\n",
             "/var/log/dpkg.log user: 200, group: 70, mode: -rw-rw-r--\n"]

    self.assertCheckDetectedAnom(check_id, results, exp, found)

    check_id = "CIS-LOG-FILES-PERMISSIONS-WORLD-WRITABLE"
    exp = "Found: Log files are world writable."
    found = ["/var/log/syslog user: 0, group: 0, mode: -rw-rw-rw-\n",
             "/var/log/puppet/mail.log user: 30, group: 70, mode: -rwxrwxrwx\n",
             "/var/log/user.log.1.gz user: 0, group: 4, mode: -rw-r---w-\n"]

    self.assertCheckDetectedAnom(check_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

