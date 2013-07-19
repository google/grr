#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.

"""OSX tests.

These tests will on OS X with run_tests.py, but not with run_tests.py on Linux
due to conditional imports.
"""



import glob
import os

import mox

# Populate the action registry
# pylint: disable=unused-import
from grr.client import client_actions
# pylint: enable=unused-import
from grr.client import client_utils_osx
from grr.client import vfs
from grr.client.client_actions.osx import osx
from grr.lib import aff4
from grr.lib import flags
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.test_data import osx_launchd as testdata


class OsxClientTests(test_lib.EmptyActionTest):
  """Test reading osx file system."""

  def testFileSystemEnumeration64Bit(self):
    """Ensure we can enumerate file systems successfully."""
    path = os.path.join(self.base_path, "osx_fsdata")
    results = client_utils_osx.ParseFileSystemsStruct(
        client_utils_osx.StatFS64Struct, 7,
        open(path).read())
    self.assertEquals(len(results), 7)
    self.assertEquals(results[0].f_fstypename, "hfs")
    self.assertEquals(results[0].f_mntonname, "/")
    self.assertEquals(results[0].f_mntfromname, "/dev/disk0s2")
    self.assertEquals(results[2].f_fstypename, "autofs")
    self.assertEquals(results[2].f_mntonname, "/auto")
    self.assertEquals(results[2].f_mntfromname, "map auto.auto")


class OSXDriverTests(test_lib.EmptyActionTest):
  """Test reading osx file system."""

  def setUp(self):
    super(OSXDriverTests, self).setUp()
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(osx.client_utils_osx, "InstallDriver")

    path = os.path.join(maintenance_utils.config_lib.CONFIG["Test.srcdir"],
                        "grr/binaries/OSXPMem*.tar.gz")
    self.drivers = glob.glob(path)

  def tearDown(self):
    self.mox.UnsetStubs()
    super(OSXDriverTests, self).tearDown()

  def testFindKext(self):
    action = osx.InstallDriver("")
    kext_path = os.path.join(self.temp_dir, "testing/something/blah.kext")
    os.makedirs(kext_path)
    self.assertEqual(action._FindKext(self.temp_dir), kext_path)
    os.makedirs(os.path.join(self.temp_dir, "testing/no/kext/here"))
    self.assertRaises(RuntimeError, action._FindKext,
                      os.path.join(self.temp_dir, "testing/no"))

  def testInstallDriver(self):
    for driver_path in self.drivers:
      print "Attempting to load %s" % driver_path

      # Make sure there is a signed driver for our client.
      vfs_path = maintenance_utils.UploadSignedDriverBlob(
          open(driver_path).read(), platform="Darwin", file_name="pmem",
          token=self.token)
      fd = aff4.FACTORY.Create(vfs_path, "GRRMemoryDriver",
                               mode="r", token=self.token)
      self.blob = fd.Get(fd.Schema.BINARY)

      request = rdfvalue.DriverInstallTemplate(driver=self.blob,
                                               write_path=None,
                                               force_reload=0)
      osx.client_utils_osx.InstallDriver(
          mox.Func(lambda x: x.endswith(".kext")))
      self.mox.ReplayAll()
      self.RunAction("InstallDriver", request)
      self.mox.VerifyAll()


class OSXEnumerateRunningServices(test_lib.EmptyActionTest):

  def setUp(self):
    super(OSXEnumerateRunningServices, self).setUp()
    self.mox = mox.Mox()
    self.action = osx.EnumerateRunningServices(None)
    self.mock_version = self.mox.CreateMock(osx.client_utils_osx.OSXVersion)

    self.mox.StubOutWithMock(self.action, "GetRunningLaunchDaemons")
    self.mox.StubOutWithMock(self.action, "SendReply")
    self.mox.StubOutWithMock(osx, "client_utils_osx")

  def ValidResponseProto(self, proto):
    self.assertTrue(proto.label)
    return True

  def ValidResponseProtoSingle(self, proto):
    td = testdata.JOB[0]
    self.assertEqual(proto.label, td["Label"])
    self.assertEqual(proto.osx_launchd.lastexitstatus,
                     td["LastExitStatus"].value)
    self.assertEqual(proto.osx_launchd.sessiontype,
                     td["LimitLoadToSessionType"])
    self.assertEqual(len(proto.osx_launchd.machservice),
                     len(td["MachServices"]))
    self.assertEqual(proto.osx_launchd.ondemand, td["OnDemand"].value)
    self.assertEqual(len(proto.args.split(" ")),
                     len(td["ProgramArguments"]))
    self.assertEqual(proto.osx_launchd.timeout, td["TimeOut"].value)
    return True

  def testEnumerateRunningServicesAll(self):
    osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsFloat().AndReturn(10.7)

    self.action.GetRunningLaunchDaemons().AndReturn(testdata.JOBS)
    num_results = len(testdata.JOBS) - testdata.FILTERED_COUNT
    for _ in range(0, num_results):
      self.action.SendReply(mox.Func(self.ValidResponseProto))

    self.mox.ReplayAll()
    self.action.Run(None)
    self.mox.VerifyAll()

  def testEnumerateRunningServicesSingle(self):
    osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsFloat().AndReturn(10.7)

    self.action.GetRunningLaunchDaemons().AndReturn(testdata.JOB)
    self.action.SendReply(mox.Func(self.ValidResponseProtoSingle))

    self.mox.ReplayAll()
    self.action.Run(None)
    self.mox.VerifyAll()

  def testEnumerateRunningServicesVersionError(self):
    osx.client_utils_osx.OSXVersion().AndReturn(self.mock_version)
    self.mock_version.VersionAsFloat().AndReturn(10.5)

    self.mox.ReplayAll()
    self.assertRaises(osx.UnsupportedOSVersionError, self.action.Run, None)
    self.mox.VerifyAll()

  def tearDown(self):
    self.mox.UnsetStubs()
    super(OSXEnumerateRunningServices, self).tearDown()


def main(argv):
  # Initialize the VFS system
  vfs.VFSInit()
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
