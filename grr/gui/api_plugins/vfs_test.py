#!/usr/bin/env python
"""This modules contains tests for VFS API handlers."""



from grr.gui import api_test_lib

from grr.gui.api_plugins import vfs as vfs_plugin
from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.general import filesystem


class VfsTestMixin(object):
  """A helper mixin providing methods to prepare files and flows for testing.
  """

  time_0 = rdfvalue.RDFDatetime(42)
  time_1 = time_0 + rdfvalue.Duration("1d")
  time_2 = time_1 + rdfvalue.Duration("1d")

  def CreateFileVersions(self, client_id, file_path):
    """Add a new version for a file."""

    with test_lib.FakeTime(self.time_1):
      token = access_control.ACLToken(username="test")
      fd = aff4.FACTORY.Create(client_id.Add(file_path),
                               "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Hello World")
      fd.Close()

    with test_lib.FakeTime(self.time_2):
      fd = aff4.FACTORY.Create(client_id.Add(file_path),
                               "AFF4MemoryStream", mode="w", token=token)
      fd.Write("Goodbye World")
      fd.Close()

  def CreateRecursiveListFlow(self, client_id, token):
    flow_args = filesystem.RecursiveListDirectoryArgs()

    return flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name="RecursiveListDirectory",
        args=flow_args,
        token=token)


class ApiGetFileDetailsHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):
  """Test for ApiGetFileDetailsHandler."""

  def setUp(self):
    super(ApiGetFileDetailsHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileDetailsHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testHandlerReturnsNewestVersionByDefault(self):
    # Get file version without specifying a timestamp.
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    # Should return the newest version.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(result.file.age, self.time_2,
                           delta=rdfvalue.Duration("1s"))

  def testHandlerReturnsClosestSpecificVersion(self):
    # Get specific version.
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path,
        timestamp=self.time_1)
    result = self.handler.Handle(args, token=self.token)

    # The age of the returned version might have a slight deviation.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(result.file.age, self.time_1,
                           delta=rdfvalue.Duration("1s"))

  def testResultIncludesDetails(self):
    """Checks if the details include certain attributes.

    Instead of using a (fragile) regression test, we enumerate important
    attributes here and make sure they are returned.
    """

    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    attributes_by_type = {}
    attributes_by_type["AFF4MemoryStream"] = ["CONTENT"]
    attributes_by_type["AFF4MemoryStreamBase"] = ["SIZE"]
    attributes_by_type["AFF4Object"] = ["LAST", "SUBJECT", "TYPE"]

    details = result.file.details
    for type_name, attrs in attributes_by_type.iteritems():
      type_obj = next(t for t in details.types if t.name == type_name)
      all_attrs = set([a.name for a in type_obj.attributes])
      self.assertTrue(set(attrs).issubset(all_attrs))


class ApiGetFileListHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):
  """Test for ApiGetFileListHandler."""

  def setUp(self):
    super(ApiGetFileListHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileListHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/etc"

  def testHandlerListsFilesAndDirectories(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Fetch all children of a directory.
    args = vfs_plugin.ApiGetFileListArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 4)
    for item in result.items:
      # Check that all files are really in the right directory.
      self.assertIn(self.file_path, item.path)

  def testHandlerFiltersDirectoriesIfFlagIsSet(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Only fetch sub-directories.
    args = vfs_plugin.ApiGetFileListArgs(
        client_id=self.client_id, file_path=self.file_path,
        directories_only=True)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].is_directory, True)
    self.assertIn(self.file_path, result.items[0].path)


class ApiGetFileListHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileListHandler"

  def setUp(self):
    super(ApiGetFileListHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    test_lib.ClientFixture(self.client_id, token=self.token, age=42)

  def Run(self):
    self.Check("GET",
               "/api/clients/%s/vfs-index/fs/tsk/c/bin" % (
                   self.client_id.Basename()))


class ApiGetFileTextHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):
  """Test for ApiGetFileTextHandler."""

  def setUp(self):
    super(ApiGetFileTextHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileTextHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testDifferentTimestampsYieldDifferentFileContents(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id, file_path=self.file_path,
        encoding=vfs_plugin.ApiGetFileTextArgs.Encoding.UTF_8)

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)

    # Change timestamp to get a different file version.
    args.timestamp = self.time_1
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(result.content, "Hello World")
    self.assertEqual(result.total_size, 11)

  def testEncodingChangesResult(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id, file_path=self.file_path,
        encoding=vfs_plugin.ApiGetFileTextArgs.Encoding.UTF_16)

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, token=self.token)

    self.assertNotEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)


class ApiGetFileTextHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileTextHandler"

  def setUp(self):
    super(ApiGetFileTextHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def Run(self):
    base_url = "/api/clients/%s/vfs-text/%s" % (self.client_id.Basename(),
                                                self.file_path)
    self.Check("GET", base_url)
    self.Check("GET", base_url + "?offset=3&length=2")
    self.Check("GET", base_url + "?timestamp=" +
               str(self.time_1.AsMicroSecondsFromEpoch()))


class ApiGetFileBlobHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileBlobHandler"

  def setUp(self):
    super(ApiGetFileBlobHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def Run(self):
    base_url = "/api/clients/%s/vfs-blob/%s" % (self.client_id.Basename(),
                                                self.file_path)
    self.Check("GET", base_url)
    self.Check("GET", base_url + "?offset=3&length=2")
    self.Check("GET", base_url + "?timestamp=" +
               str(self.time_1.AsMicroSecondsFromEpoch()))


class ApiGetFileVersionTimesHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileVersionTimesHandler"

  def setUp(self):
    super(ApiGetFileVersionTimesHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def Run(self):
    self.Check("GET", "/api/clients/%s/vfs-version-times/%s" % (
        self.client_id.Basename(), self.file_path))


class ApiListKnownEncodingsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiListKnownEncodingsHandler"

  def Run(self):
    self.Check("GET", "/api/reflection/file-encodings")


class ApiGetFileDownloadCommandHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileDownloadCommandHandler"

  def Run(self):
    self.client_id = self.SetupClients(1)[0].Basename()
    self.file_path = "fs/os/etc"
    self.Check("GET",
               "/api/clients/%s/vfs-download-command/%s" % (self.client_id,
                                                            self.file_path))


class ApiCreateVfsRefreshOperationHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiCreateVfsRefreshOperationHandler."""

  def setUp(self):
    super(ApiCreateVfsRefreshOperationHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiCreateVfsRefreshOperationHandler()
    self.client_id = self.SetupClients(1)[0]
    # Choose some directory with pathspec in the ClientFixture.
    self.file_path = "fs/os/Users/Shared"

  def testHandlerStartsFlow(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=0)
    result = self.handler.Handle(args, token=self.token)

    # Check returned operation_id to references a RecursiveListDirectory flow.
    flow_obj = aff4.FACTORY.Open(result.operation_id, token=self.token)
    self.assertEqual(flow_obj.Get(flow_obj.Schema.TYPE),
                     "RecursiveListDirectory")

  def testNotificationIsSent(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=0,
        notify_user=True)
    result = self.handler.Handle(args, token=self.token)

    # Finish flow and check if there are any new notifications.
    flow_urn = rdfvalue.RDFURN(result.operation_id)
    client_mock = action_mocks.ActionMock()
    for _ in test_lib.TestFlowHelper(
        flow_urn, client_mock, client_id=self.client_id,
        token=self.token, check_flow_errors=False):
      pass

    # Get pending notifications and check the newest one.
    user_record = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type="GRRUser", mode="r", token=self.token)

    pending_notifications = user_record.Get(
        user_record.Schema.PENDING_NOTIFICATIONS)

    self.assertIn("Recursive Directory Listing complete",
                  pending_notifications[0].message)
    self.assertEqual(pending_notifications[0].source, str(flow_urn))


class ApiCreateVfsRefreshOperationHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiCreateVfsRefreshOperationHandler."""

  handler = "ApiCreateVfsRefreshOperationHandler"

  def setUp(self):
    super(ApiCreateVfsRefreshOperationHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    # Choose some directory with pathspec in the ClientFixture.
    self.file_path = "fs/os/Users/Shared"

  def Run(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    def ReplaceFlowId():
      flows_dir_fd = aff4.FACTORY.Open(self.client_id.Add("flows"),
                                       token=self.token)
      flow_urn = list(flows_dir_fd.ListChildren())[0]
      return {flow_urn.Basename(): "W:ABCDEF"}

    url = "/api/clients/%s/vfs-refresh-operations" % self.client_id.Basename()
    with test_lib.FakeTime(42):
      self.Check("POST", url,
                 {"file_path": self.file_path,
                  "max_depth": 1},
                 replace=ReplaceFlowId)


class GetVfsRefreshOperationStateHandlerTest(test_lib.GRRBaseTest,
                                             VfsTestMixin):
  """Test for GetVfsRefreshOperationStateHandler."""

  def setUp(self):
    super(GetVfsRefreshOperationStateHandlerTest, self).setUp()
    self.handler = vfs_plugin.GetVfsRefreshOperationStateHandler()
    self.client_id = self.SetupClients(1)[0]

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    self.flow_urn = self.CreateRecursiveListFlow(
        self.client_id, self.token)

    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        operation_id=str(self.flow_urn))

    # Flow was started and should be running.
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(result.state, "RUNNING")

    # Terminate flow.
    with aff4.FACTORY.Open(self.flow_urn, aff4_type="GRRFlow", mode="rw",
                           token=self.token) as flow_obj:
      flow_obj.GetRunner().Error("Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(result.state, "FINISHED")

  def testHandlerThrowsExceptionOnArbitraryFlowId(self):
    # Create a mock flow.
    self.flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                           flow_name="Interrogate",
                                           token=self.token)

    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        operation_id=str(self.flow_urn))

    # Our mock flow is not a RecursiveListFlow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, token=self.token)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        operation_id="F:12345678")

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, token=self.token)


class GetVfsRefreshOperationStateHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):
  """Regression test for GetVfsRefreshOperationStateHandler."""

  handler = "GetVfsRefreshOperationStateHandler"

  def setUp(self):
    super(GetVfsRefreshOperationStateHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    # Create a running mock refresh operation.
    self.running_flow_urn = self.CreateRecursiveListFlow(
        self.client_id, self.token)

    # Create a mock refresh operation and complete it.
    self.finished_flow_urn = self.CreateRecursiveListFlow(
        self.client_id, self.token)
    with aff4.FACTORY.Open(self.finished_flow_urn, aff4_type="GRRFlow",
                           mode="rw", token=self.token) as flow_obj:
      flow_obj.GetRunner().Error("Fake error")

    # Create an arbitrary flow to check on 404s.
    self.non_refresh_flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id, flow_name="Interrogate", token=self.token)

    # Unkonwn flow ids should also cause 404s.
    self.unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" % (
                   self.client_id.Basename(), str(self.running_flow_urn)),
               replace={self.running_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" % (
                   self.client_id.Basename(), str(self.finished_flow_urn)),
               replace={self.finished_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" % (
                   self.client_id.Basename(), str(self.non_refresh_flow_urn)),
               replace={self.non_refresh_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" % (
                   self.client_id.Basename(), self.unknown_flow_id),
               replace={self.unknown_flow_id: "W:ABCDEF"})


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
