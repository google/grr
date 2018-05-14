#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""OSX tests."""

import os

import mock

from grr.lib import flags
from grr.test_lib import client_test_lib
from grr.test_lib import osx_launchd_testdata
from grr.test_lib import test_lib


class OSXClientTests(client_test_lib.OSSpecificClientTests):
  """OSX client action tests."""

  def setUp(self):
    super(OSXClientTests, self).setUp()
    # TODO(user): move this import to the top of the file.
    # At the moment, importing this at the top of the file causes
    # "Duplicate names for registered classes" metaclass registry
    # error.
    # pylint: disable=g-import-not-at-top
    from grr_response_client.client_actions.osx import osx
    # pylint: enable=g-import-not-at-top
    self.osx = osx


class OSXFilesystemTests(OSXClientTests):
  """Test reading osx file system."""

  def testFileSystemEnumeration64Bit(self):
    """Ensure we can enumerate file systems successfully."""
    path = os.path.join(self.base_path, "osx_fsdata")
    results = self.osx.client_utils_osx.ParseFileSystemsStruct(
        self.osx.client_utils_osx.StatFS64Struct, 7,
        open(path, "rb").read())
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

  def ValidResponseProto(self, proto):
    self.assertTrue(proto.label)
    return True

  def ValidResponseProtoSingle(self, proto):
    return True

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesAll(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 7]
    osx_version_mock.return_value = version_value_mock

    with mock.patch.object(
        self.osx.OSXEnumerateRunningServices,
        "GetRunningLaunchDaemons") as get_running_launch_daemons_mock:
      with mock.patch.object(self.osx.OSXEnumerateRunningServices,
                             "SendReply") as send_reply_mock:

        get_running_launch_daemons_mock.return_value = osx_launchd_testdata.JOBS

        action = self.osx.OSXEnumerateRunningServices(None)
        num_results = len(
            osx_launchd_testdata.JOBS) - osx_launchd_testdata.FILTERED_COUNT

        action.Run(None)

        self.assertEqual(send_reply_mock.call_count, num_results)
        for c_args in send_reply_mock.call_args_list:
          # First call argument is expected to be an OSXServiceInformation.
          # Verify that the label is set.
          self.assertTrue(c_args[0][0].label)

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesSingle(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 7, 1]
    osx_version_mock.return_value = version_value_mock

    with mock.patch.object(
        self.osx.OSXEnumerateRunningServices,
        "GetRunningLaunchDaemons") as get_running_launch_daemons_mock:
      with mock.patch.object(self.osx.OSXEnumerateRunningServices,
                             "SendReply") as send_reply_mock:

        get_running_launch_daemons_mock.return_value = osx_launchd_testdata.JOB

        action = self.osx.OSXEnumerateRunningServices(None)
        action.Run(None)

        self.assertEqual(send_reply_mock.call_count, 1)
        proto = send_reply_mock.call_args[0][0]

        td = osx_launchd_testdata.JOB[0]
        self.assertEqual(proto.label, td["Label"])
        self.assertEqual(proto.lastexitstatus, td["LastExitStatus"].value)
        self.assertEqual(proto.sessiontype, td["LimitLoadToSessionType"])
        self.assertEqual(len(proto.machservice), len(td["MachServices"]))
        self.assertEqual(proto.ondemand, td["OnDemand"].value)
        self.assertEqual(len(proto.args), len(td["ProgramArguments"]))
        self.assertEqual(proto.timeout, td["TimeOut"].value)

  @mock.patch(
      "grr_response_client.client_utils_osx."
      "OSXVersion")
  def testOSXEnumerateRunningServicesVersionError(self, osx_version_mock):
    version_value_mock = mock.Mock()
    version_value_mock.VersionAsMajorMinor.return_value = [10, 5, 1]
    version_value_mock.VersionString.return_value = "10.5.1"
    osx_version_mock.return_value = version_value_mock

    action = self.osx.OSXEnumerateRunningServices(None)
    with self.assertRaises(self.osx.UnsupportedOSVersionError):
      action.Run(None)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
