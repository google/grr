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
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.flows.general import filesystem
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


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
      fd = aff4.FACTORY.Create(
          client_id.Add(file_path),
          aff4.AFF4MemoryStream,
          mode="w",
          token=token)
      fd.Write("Hello World")
      fd.Close()

    with test_lib.FakeTime(self.time_2):
      fd = aff4.FACTORY.Create(
          client_id.Add(file_path),
          aff4.AFF4MemoryStream,
          mode="w",
          token=token)
      fd.Write("Goodbye World")
      fd.Close()

  def CreateRecursiveListFlow(self, client_id, token):
    flow_args = filesystem.RecursiveListDirectoryArgs()

    return flow.GRRFlow.StartFlow(client_id=client_id,
                                  flow_name="RecursiveListDirectory",
                                  args=flow_args,
                                  token=token)

  def CreateMultiGetFileFlow(self, client_id, file_path, token):
    pathspec = rdf_paths.PathSpec(path=file_path,
                                  pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_args = transfer.MultiGetFileArgs(pathspecs=[pathspec])

    return flow.GRRFlow.StartFlow(client_id=client_id,
                                  flow_name="MultiGetFile",
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

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testHandlerReturnsNewestVersionByDefault(self):
    # Get file version without specifying a timestamp.
    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    # Should return the newest version.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(result.file.age,
                           self.time_2,
                           delta=rdfvalue.Duration("1s"))

  def testHandlerReturnsClosestSpecificVersion(self):
    # Get specific version.
    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path=self.file_path,
                                            timestamp=self.time_1)
    result = self.handler.Handle(args, token=self.token)

    # The age of the returned version might have a slight deviation.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(result.file.age,
                           self.time_1,
                           delta=rdfvalue.Duration("1s"))

  def testResultIncludesDetails(self):
    """Checks if the details include certain attributes.

    Instead of using a (fragile) regression test, we enumerate important
    attributes here and make sure they are returned.
    """

    args = vfs_plugin.ApiGetFileDetailsArgs(client_id=self.client_id,
                                            file_path=self.file_path)
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


class ApiListFilesHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):
  """Test for ApiListFilesHandler."""

  def setUp(self):
    super(ApiListFilesHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiListFilesHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/etc"

  def testDoesNotRaiseIfFirstCompomentIsEmpty(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="")
    self.handler.Handle(args, token=self.token)

  def testDoesNotRaiseIfPathIsRoot(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="/")
    self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentIsNotWhitelisted(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id,
                                       file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testHandlerListsFilesAndDirectories(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Fetch all children of a directory.
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id,
                                       file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 4)
    for item in result.items:
      # Check that all files are really in the right directory.
      self.assertIn(self.file_path, item.path)

  def testHandlerFiltersDirectoriesIfFlagIsSet(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Only fetch sub-directories.
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id,
                                       file_path=self.file_path,
                                       directories_only=True)
    result = self.handler.Handle(args, token=self.token)

    self.assertEqual(len(result.items), 1)
    self.assertEqual(result.items[0].is_directory, True)
    self.assertIn(self.file_path, result.items[0].path)


class ApiListFilesHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiListFilesHandler"

  def setUp(self):
    super(ApiListFilesHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    test_lib.ClientFixture(self.client_id, token=self.token, age=42)

  def Run(self):
    self.Check("GET", "/api/clients/%s/vfs-index/fs/tsk/c/bin" %
               (self.client_id.Basename()))


class ApiGetFileTextHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):
  """Test for ApiGetFileTextHandler."""

  def setUp(self):
    super(ApiGetFileTextHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileTextHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileTextArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileTextArgs(client_id=self.client_id,
                                         file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetFileTextArgs(client_id=self.client_id,
                                         file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testDifferentTimestampsYieldDifferentFileContents(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id,
        file_path=self.file_path,
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
        client_id=self.client_id,
        file_path=self.file_path,
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
    self.Check(
        "GET",
        base_url + "?timestamp=" + str(self.time_1.AsMicroSecondsFromEpoch()))


class ApiGetFileBlobHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):

  def setUp(self):
    super(ApiGetFileBlobHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileBlobHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testNewestFileContentIsReturnedByDefault(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), "Goodbye World")

  def testOffsetAndLengthRestrictResult(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path=self.file_path,
                                         offset=2,
                                         length=3)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), "odb")

  def testReturnsOlderVersionIfTimestampIsSupplied(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path=self.file_path,
                                         timestamp=self.time_1)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), "Hello World")

  def testLargeFileIsReturnedInMultipleChunks(self):
    chars = ["a", "b", "x"]
    huge_file_path = "fs/os/c/Downloads/huge.txt"

    # Overwrite CHUNK_SIZE in handler for smaller test streams.
    self.handler.CHUNK_SIZE = 5

    # Create a file that requires several chunks to load.
    with aff4.FACTORY.Create(
        self.client_id.Add(huge_file_path),
        aff4.AFF4MemoryStream,
        mode="w",
        token=self.token) as fd:
      for char in chars:
        fd.Write(char * self.handler.CHUNK_SIZE)

    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id,
                                         file_path=huge_file_path)
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(hasattr(result, "GenerateContent"))
    for chunk, char in zip(result.GenerateContent(), chars):
      self.assertEqual(chunk, char * self.handler.CHUNK_SIZE)


class ApiGetFileVersionTimesHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):

  def setUp(self):
    super(ApiGetFileVersionTimesHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = vfs_plugin.ApiGetFileVersionTimesHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(client_id=self.client_id,
                                                 file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(client_id=self.client_id,
                                                 file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(client_id=self.client_id,
                                                 file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)


class ApiGetFileVersionTimesHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiGetFileVersionTimesHandler"

  def setUp(self):
    super(ApiGetFileVersionTimesHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def Run(self):
    self.Check("GET", "/api/clients/%s/vfs-version-times/%s" %
               (self.client_id.Basename(), self.file_path))


class ApiListKnownEncodingsHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):

  handler = "ApiListKnownEncodingsHandler"

  def Run(self):
    self.Check("GET", "/api/reflection/file-encodings")


class ApiGetFileDownloadCommandHandlerTest(test_lib.GRRBaseTest, VfsTestMixin):

  def setUp(self):
    super(ApiGetFileDownloadCommandHandlerTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.handler = vfs_plugin.ApiGetFileDownloadCommandHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(client_id=self.client_id,
                                                    file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(client_id=self.client_id,
                                                    file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(client_id=self.client_id,
                                                    file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)


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

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id,
                                                       file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id,
                                                       file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id,
                                                       file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testHandlerStartsFlow(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id,
                                                       file_path=self.file_path,
                                                       max_depth=0)
    result = self.handler.Handle(args, token=self.token)

    # Check returned operation_id to references a RecursiveListDirectory flow.
    flow_obj = aff4.FACTORY.Open(result.operation_id, token=self.token)
    self.assertEqual(
        flow_obj.Get(flow_obj.Schema.TYPE), "RecursiveListDirectory")

  def testNotificationIsSent(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(client_id=self.client_id,
                                                       file_path=self.file_path,
                                                       max_depth=0,
                                                       notify_user=True)
    result = self.handler.Handle(args, token=self.token)

    # Finish flow and check if there are any new notifications.
    flow_urn = rdfvalue.RDFURN(result.operation_id)
    client_mock = action_mocks.ActionMock()
    for _ in test_lib.TestFlowHelper(flow_urn,
                                     client_mock,
                                     client_id=self.client_id,
                                     token=self.token,
                                     check_flow_errors=False):
      pass

    # Get pending notifications and check the newest one.
    user_record = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=self.token)

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
      flows_dir_fd = aff4.FACTORY.Open(
          self.client_id.Add("flows"),
          token=self.token)
      flow_urn = list(flows_dir_fd.ListChildren())[0]
      return {flow_urn.Basename(): "W:ABCDEF"}

    url = "/api/clients/%s/vfs-refresh-operations" % self.client_id.Basename()
    with test_lib.FakeTime(42):
      self.Check("POST",
                 url, {"file_path": self.file_path,
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
    self.flow_urn = self.CreateRecursiveListFlow(self.client_id, self.token)

    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        operation_id=str(self.flow_urn))

    # Flow was started and should be running.
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(result.state, "RUNNING")

    # Terminate flow.
    with aff4.FACTORY.Open(self.flow_urn,
                           aff4_type=flow.GRRFlow,
                           mode="rw",
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
    self.running_flow_urn = self.CreateRecursiveListFlow(self.client_id,
                                                         self.token)

    # Create a mock refresh operation and complete it.
    self.finished_flow_urn = self.CreateRecursiveListFlow(self.client_id,
                                                          self.token)
    with aff4.FACTORY.Open(self.finished_flow_urn,
                           aff4_type=flow.GRRFlow,
                           mode="rw",
                           token=self.token) as flow_obj:
      flow_obj.GetRunner().Error("Fake error")

    # Create an arbitrary flow to check on 404s.
    self.non_refresh_flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                                       flow_name="Interrogate",
                                                       token=self.token)

    # Unkonwn flow ids should also cause 404s.
    self.unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" %
               (self.client_id.Basename(), str(self.running_flow_urn)),
               replace={self.running_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" %
               (self.client_id.Basename(), str(self.finished_flow_urn)),
               replace={self.finished_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" %
               (self.client_id.Basename(), str(self.non_refresh_flow_urn)),
               replace={self.non_refresh_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-refresh-operations/%s" %
               (self.client_id.Basename(), self.unknown_flow_id),
               replace={self.unknown_flow_id: "W:ABCDEF"})


class ApiUpdateVfsFileContentHandlerTest(test_lib.GRRBaseTest):
  """Test for ApiUpdateVfsFileContentHandler."""

  def setUp(self):
    super(ApiUpdateVfsFileContentHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiUpdateVfsFileContentHandler()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/bin/bash"

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(client_id=self.client_id,
                                                  file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(client_id=self.client_id,
                                                  file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(client_id=self.client_id,
                                                  file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testHandlerStartsFlow(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    args = vfs_plugin.ApiUpdateVfsFileContentArgs(client_id=self.client_id,
                                                  file_path=self.file_path)
    result = self.handler.Handle(args, token=self.token)

    # Check returned operation_id to references a MultiGetFile flow.
    flow_obj = aff4.FACTORY.Open(result.operation_id, token=self.token)
    self.assertEqual(flow_obj.Get(flow_obj.Schema.TYPE), "MultiGetFile")


class ApiUpdateVfsFileContentHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):
  """Regression test for ApiUpdateVfsFileContentHandler."""

  handler = "ApiUpdateVfsFileContentHandler"

  def setUp(self):
    super(ApiUpdateVfsFileContentHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.file_path = "fs/os/c/bin/bash"

  def Run(self):
    test_lib.ClientFixture(self.client_id, token=self.token)

    def ReplaceFlowId():
      flows_dir_fd = aff4.FACTORY.Open(
          self.client_id.Add("flows"),
          token=self.token)
      flow_urn = list(flows_dir_fd.ListChildren())[0]
      return {flow_urn.Basename(): "W:ABCDEF"}

    url = "/api/clients/%s/vfs-update" % self.client_id.Basename()
    with test_lib.FakeTime(42):
      self.Check("POST",
                 url, {"file_path": self.file_path},
                 replace=ReplaceFlowId)


class ApiGetVfsFileContentUpdateStateHandlerTest(test_lib.GRRBaseTest,
                                                 VfsTestMixin):
  """Test for ApiGetVfsFileContentUpdateStateHandler."""

  def setUp(self):
    super(ApiGetVfsFileContentUpdateStateHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsFileContentUpdateStateHandler()
    self.client_id = self.SetupClients(1)[0]

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    self.flow_urn = self.CreateMultiGetFileFlow(self.client_id,
                                                file_path="fs/os/c/bin/bash",
                                                token=self.token)

    args = vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
        operation_id=str(self.flow_urn))

    # Flow was started and should be running.
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(result.state, "RUNNING")

    # Terminate flow.
    with aff4.FACTORY.Open(self.flow_urn,
                           aff4_type=flow.GRRFlow,
                           mode="rw",
                           token=self.token) as flow_obj:
      flow_obj.GetRunner().Error("Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, token=self.token)
    self.assertEqual(result.state, "FINISHED")

  def testHandlerRaisesOnArbitraryFlowId(self):
    # Create a mock flow.
    self.flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                           flow_name="Interrogate",
                                           token=self.token)

    args = vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
        operation_id=str(self.flow_urn))

    # Our mock flow is not a MultiGetFile flow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, token=self.token)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        operation_id="F:12345678")

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, token=self.token)


class GetVfsFileContentUpdateStateHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTestMixin):
  """Regression test for GetVfsFileContentUpdateStateHandler."""

  handler = "GetVfsFileContentUpdateStateHandler"

  def setUp(self):
    super(GetVfsFileContentUpdateStateHandlerRegressionTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]

  def Run(self):
    # Create a running mock refresh operation.
    self.running_flow_urn = self.CreateMultiGetFileFlow(
        self.client_id,
        file_path="fs/os/c/bin/bash",
        token=self.token)

    # Create a mock refresh operation and complete it.
    self.finished_flow_urn = self.CreateMultiGetFileFlow(
        self.client_id,
        file_path="fs/os/c/bin/bash",
        token=self.token)
    with aff4.FACTORY.Open(self.finished_flow_urn,
                           aff4_type=flow.GRRFlow,
                           mode="rw",
                           token=self.token) as flow_obj:
      flow_obj.GetRunner().Error("Fake error")

    # Create an arbitrary flow to check on 404s.
    self.non_update_flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                                      flow_name="Interrogate",
                                                      token=self.token)

    # Unkonwn flow ids should also cause 404s.
    self.unknown_flow_id = "F:12345678"

    # Check both operations.
    self.Check("GET",
               "/api/clients/%s/vfs-update/%s" % (self.client_id.Basename(),
                                                  str(self.running_flow_urn)),
               replace={self.running_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-update/%s" % (self.client_id.Basename(),
                                                  str(self.finished_flow_urn)),
               replace={self.finished_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-update/%s" %
               (self.client_id.Basename(), str(self.non_update_flow_urn)),
               replace={self.non_update_flow_urn.Basename(): "W:ABCDEF"})
    self.Check("GET",
               "/api/clients/%s/vfs-update/%s" % (self.client_id.Basename(),
                                                  self.unknown_flow_id),
               replace={self.unknown_flow_id: "W:ABCDEF"})


class VfsTimelineTestMixin(object):
  """A helper mixin providing methods to prepare timelines for testing.
  """

  def SetupTestTimeline(self):
    self.client_id = self.SetupClients(1)[0]
    test_lib.ClientFixture(self.client_id, token=self.token)

    # Choose some directory with pathspec in the ClientFixture.
    self.folder_path = "fs/os/Users/Shared"
    self.file_path = self.folder_path + "/a.txt"

    file_urn = self.client_id.Add(self.file_path)
    for i in range(0, 5):
      with test_lib.FakeTime(i):
        with aff4.FACTORY.Create(file_urn,
                                 aff4_grr.VFSAnalysisFile,
                                 mode="w",
                                 token=self.token) as fd:
          stats = rdf_client.StatEntry(
              st_mtime=rdfvalue.RDFDatetimeSeconds().Now())
          fd.Set(fd.Schema.STAT, stats)


class ApiGetVfsTimelineAsCsvHandlerTest(test_lib.GRRBaseTest,
                                        VfsTimelineTestMixin):

  def setUp(self):
    super(ApiGetVfsTimelineAsCsvHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineAsCsvHandler()
    self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id,
                                                 file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id,
                                                 file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id,
                                                 file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testTimelineIsReturnedInChunks(self):
    # Change chunk size to see if the handler behaves correctly.
    self.handler.CHUNK_SIZE = 1

    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(client_id=self.client_id,
                                                 file_path=self.folder_path)
    result = self.handler.Handle(args, token=self.token)

    # Check rows returned correctly.
    self.assertTrue(hasattr(result, "GenerateContent"))
    for i in reversed(range(0, 5)):
      with test_lib.FakeTime(i):
        next_chunk = next(result.GenerateContent()).strip()
        timestamp = rdfvalue.RDFDatetime().Now()
        if i == 4:  # The first row includes the column headings.
          self.assertEqual(next_chunk,
                           "Timestamp,Datetime,Message,Timestamp_desc\r\n"
                           "%d,%s,%s,MODIFICATION" %
                           (timestamp.AsMicroSecondsFromEpoch(), str(timestamp),
                            self.file_path))
        else:
          self.assertEqual(next_chunk, "%d,%s,%s,MODIFICATION" %
                           (timestamp.AsMicroSecondsFromEpoch(), str(timestamp),
                            self.file_path))

  def testEmptyTimelineIsReturnedOnNonexistantPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id,
        file_path="fs/non-existant/file/path")
    result = self.handler.Handle(args, token=self.token)

    self.assertTrue(hasattr(result, "GenerateContent"))
    with self.assertRaises(StopIteration):
      next(result.GenerateContent())


class ApiGetVfsTimelineHandlerTest(test_lib.GRRBaseTest, VfsTimelineTestMixin):

  def setUp(self):
    super(ApiGetVfsTimelineHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineHandler()
    self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(client_id=self.client_id,
                                            file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(client_id=self.client_id,
                                            file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)

  def testRaisesIfFirstComponentNotInWhitelist(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(client_id=self.client_id,
                                            file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, token=self.token)


class ApiGetVfsTimelineHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest, VfsTimelineTestMixin):
  """Regression test for ApiGetVfsTimelineHandler."""

  handler = "ApiGetVfsTimelineHandler"

  def setUp(self):
    super(ApiGetVfsTimelineHandlerRegressionTest, self).setUp()
    self.SetupTestTimeline()

  def Run(self):
    self.Check("GET",
               "/api/clients/%s/vfs-timeline/%s" % (self.client_id.Basename(),
                                                    self.folder_path))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
