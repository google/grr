#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""OSX tests."""



import os

import mock
import mox

from grr.lib import flags
from grr.lib import osx_launchd as testdata
from grr.lib import test_lib


class OSXClientTests(test_lib.OSSpecificClientTests):
  """OSX client action tests."""

  def setUp(self):
    super(OSXClientTests, self).setUp()
    modules = {
        # Necessary to stop the import of client.osx.installers registering the
        # actions.ActionPlugin.classes
        "grr.client.osx": mock.MagicMock(),
        "grr.client.osx.objc": mock.MagicMock(),
        # Necessary to stop the import of client_actions.standard re-populating
        # actions.ActionPlugin.classes
        ("grr.client.client_actions"
         ".standard"): mock.MagicMock(),
    }

    self.module_patcher = mock.patch.dict("sys.modules", modules)
    self.module_patcher.start()

    # pylint: disable=g-import-not-at-top
    from grr.client.client_actions.osx import osx
    # pylint: enable=g-import-not-at-top
    self.osx = osx

  def tearDown(self):
    self.module_patcher.stop()
    super(OSXClientTests, self).tearDown()


class OSXFilesystemTests(OSXClientTests):
  """Test reading osx file system."""

  def testFileSystemEnumeration64Bit(self):
    """Ensure we can enumerate file systems successfully."""
    path = os.path.join(self.base_path, "osx_fsdata")
    results = self.osx.client_utils_osx.ParseFileSystemsStruct(
        self.osx.client_utils_osx.StatFS64Struct, 7, open(path).read())
    self.assertEqual(len(results), 7)
    self.assertEqual(results[0].f_fstypename, "hfs")
    self.assertEqual(results[0].f_mntonname, "/")
    self.assertEqual(results[0].f_mntfromname, "/dev/disk0s2")
    self.assertEqual(results[2].f_fstypename, "autofs")
    self.assertEqual(results[2].f_mntonname, "/auto")
    self.assertEqual(results[2].f_mntfromname, "map auto.auto")


class OSXEnumerateRunningServicesTest(OSXClientTests):

  def setUp(self):
    super(OSXEnumerateRunningServicesTest, self).setUp()
    self.mox = mox.Mox()
    self.action = self.osx.OSXEnumerateRunningServices(None)
    self.mock_version = self.mox.CreateMock(
        self.osx.client_utils_osx.OSXVersion)

    self.mox.StubOutWithMock(self.action, "GetRunningLaunchDaemons")
    self.mox.StubOutWithMock(self.action, "SendReply")
    self.mox.StubOutWithMock(self.osx, "client_utils_osx")

  def ValidResponseProto(self, proto):
    self.assertTrue(proto.label)
    return True

  def ValidResponseProtoSingle(self, proto):
    td = testdata.JOB[0]
    self.assertEqual(proto.label, td["Label"])
    self.assertEqual(proto.lastexitstatus, td["LastExitStatus"].value)
    self.assertEqual(proto.sessiontype, td["LimitLoadToSessionType"])
    self.assertEqual(len(proto.machservice), len(td["MachServices"]))
    self.assertEqual(proto.ondemand, td["OnDemand"].value)
    self.assertEqual(len(proto.args), len(td["ProgramArguments"]))
    self.assertEqual(proto.timeout, td["TimeOut"].value)
    return True

  def testOSXEnumerateRunningServicesAll(self):
    self.osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsMajorMinor().AndReturn([10, 7])

    self.action.GetRunningLaunchDaemons().AndReturn(testdata.JOBS)
    num_results = len(testdata.JOBS) - testdata.FILTERED_COUNT
    for _ in range(0, num_results):
      self.action.SendReply(mox.Func(self.ValidResponseProto))

    self.mox.ReplayAll()
    self.action.Run(None)
    self.mox.VerifyAll()

  def testOSXEnumerateRunningServicesSingle(self):
    self.osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsMajorMinor().AndReturn([10, 7, 1])

    self.action.GetRunningLaunchDaemons().AndReturn(testdata.JOB)
    self.action.SendReply(mox.Func(self.ValidResponseProtoSingle))

    self.mox.ReplayAll()
    self.action.Run(None)
    self.mox.VerifyAll()

  def testOSXEnumerateRunningServicesVersionError(self):
    self.osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsMajorMinor().AndReturn([10, 5, 1])
    self.mock_version.VersionString().AndReturn("10.5.1")

    self.mox.ReplayAll()
    self.assertRaises(self.osx.UnsupportedOSVersionError, self.action.Run, None)
    self.mox.VerifyAll()

  def tearDown(self):
    self.mox.UnsetStubs()
    super(OSXEnumerateRunningServicesTest, self).tearDown()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
