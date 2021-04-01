#!/usr/bin/env python
import contextlib
import os
import platform
import random
import unittest
from unittest import mock

from absl.testing import absltest
from grr_response_client.unprivileged.unix import sandbox


@unittest.skipIf(platform.system() != "Linux" and platform.system() != "Darwin",
                 "Unix only test.")
class SandboxTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._mock_setresuid = stack.enter_context(
        mock.patch.object(os, "setresuid"))
    self._mock_setresgid = stack.enter_context(
        mock.patch.object(os, "setresgid"))
    self._mock_setgroups = stack.enter_context(
        mock.patch.object(os, "setgroups"))

    # pylint: disable=g-import-not-at-top
    import grp
    import pwd
    # pylint: enable=g-import-not-at-top
    random.seed(42)
    pwd_entry = random.choice(pwd.getpwall())
    grp_entry = random.choice(grp.getgrall())

    self._uid = pwd_entry.pw_uid
    self._gid = grp_entry.gr_gid
    self._user = pwd_entry.pw_name
    self._group = grp_entry.gr_name

  def testEnterSandbox(self):
    sandbox.EnterSandbox(self._user, self._group)
    self._mock_setresuid.assert_called_with(self._uid, self._uid, self._uid)
    self._mock_setresgid.assert_called_with(self._gid, self._gid, self._gid)
    self._mock_setgroups.assert_called_with([self._gid])

  def testEnterSandbox_userOnly(self):
    sandbox.EnterSandbox(self._user, "")
    self._mock_setresuid.assert_called_with(self._uid, self._uid, self._uid)
    self._mock_setresgid.assert_not_called()
    self._mock_setgroups.assert_not_called()

  def testEnterSandbox_groupOnly(self):
    sandbox.EnterSandbox("", self._group)
    self._mock_setresuid.assert_not_called()
    self._mock_setresgid.assert_called_with(self._gid, self._gid, self._gid)
    self._mock_setgroups.assert_called_with([self._gid])

  def testEnterSandbox_nothing(self):
    sandbox.EnterSandbox("", "")
    self._mock_setresuid.assert_not_called()
    self._mock_setresgid.assert_not_called()
    self._mock_setgroups.assert_not_called()


if __name__ == "__main__":
  absltest.main()
