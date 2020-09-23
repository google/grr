#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""This modules contains tests for VFS API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import io
import zipfile

from absl import app
import mock

from grr_response_core.lib import factory
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths

from grr_response_server import data_store
from grr_response_server import decoders
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import vfs as vfs_plugin
from grr_response_server.rdfvalues import objects as rdf_objects

from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class VfsTestMixin(object):
  """A helper mixin providing methods to prepare files and flows for testing."""

  time_0 = rdfvalue.RDFDatetime(42)
  time_1 = time_0 + rdfvalue.Duration.From(1, rdfvalue.DAYS)
  time_2 = time_1 + rdfvalue.Duration.From(1, rdfvalue.DAYS)

  # TODO(hanuszczak): This function not only contains a lot of code duplication
  # but is also a duplication with `gui_test_lib.CreateFileVersion(s)`. This
  # should be refactored in the near future.
  def CreateFileVersions(self, client_id, file_path):
    """Add a new version for a file."""
    path_type, components = rdf_objects.ParseCategorizedPath(file_path)
    client_path = db.ClientPath(client_id, path_type, components)

    with test_lib.FakeTime(self.time_1):
      vfs_test_lib.CreateFile(client_path, "Hello World".encode("utf-8"))

    with test_lib.FakeTime(self.time_2):
      vfs_test_lib.CreateFile(client_path, "Goodbye World".encode("utf-8"))

  def CreateRecursiveListFlow(self, client_id):
    flow_args = filesystem.RecursiveListDirectoryArgs()

    return flow.StartFlow(
        client_id=client_id,
        flow_cls=filesystem.RecursiveListDirectory,
        flow_args=flow_args)

  def CreateMultiGetFileFlow(self, client_id, file_path):
    pathspec = rdf_paths.PathSpec(
        path=file_path, pathtype=rdf_paths.PathSpec.PathType.OS)
    flow_args = transfer.MultiGetFileArgs(pathspecs=[pathspec])

    return flow.StartFlow(
        client_id=client_id,
        flow_cls=transfer.MultiGetFile,
        flow_args=flow_args)


class ApiGetFileDetailsHandlerTest(api_test_lib.ApiCallHandlerTest,
                                   VfsTestMixin):
  """Test for ApiGetFileDetailsHandler."""

  def setUp(self):
    super(ApiGetFileDetailsHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileDetailsHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnNonexistentPath(self):
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/fs/os/foo/bar")
    with self.assertRaises(vfs_plugin.FileNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerReturnsNewestVersionByDefault(self):
    # Get file version without specifying a timestamp.
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)

    # Should return the newest version.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(
        result.file.age,
        self.time_2,
        delta=rdfvalue.Duration.From(1, rdfvalue.SECONDS))

  def testHandlerReturnsClosestSpecificVersion(self):
    # Get specific version.
    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_1)
    result = self.handler.Handle(args, context=self.context)

    # The age of the returned version might have a slight deviation.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(
        result.file.age,
        self.time_1,
        delta=rdfvalue.Duration.From(1, rdfvalue.SECONDS))

  def testResultIncludesDetails(self):
    """Checks if the details include certain attributes.

    Instead of using a (fragile) regression test, we enumerate important
    attributes here and make sure they are returned.
    """

    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)

    attributes_by_type = {}
    attributes_by_type["VFSFile"] = ["STAT"]
    attributes_by_type["AFF4Stream"] = ["HASH", "SIZE"]
    attributes_by_type["AFF4Object"] = ["TYPE"]

    details = result.file.details
    for type_name, attrs in attributes_by_type.items():
      type_obj = next(t for t in details.types if t.name == type_name)
      all_attrs = set([a.name for a in type_obj.attributes])
      self.assertContainsSubset(attrs, all_attrs)

  def testIsDirectoryFlag(self):
    # Set up a directory.
    dir_path = "fs/os/Random/Directory"
    path_type, components = rdf_objects.ParseCategorizedPath(dir_path)
    client_path = db.ClientPath(self.client_id, path_type, components)
    vfs_test_lib.CreateDirectory(client_path)

    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)
    self.assertFalse(result.file.is_directory)

    args = vfs_plugin.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=dir_path)
    result = self.handler.Handle(args, context=self.context)
    self.assertTrue(result.file.is_directory)


class ApiListFilesHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):
  """Test for ApiListFilesHandler."""

  def setUp(self):
    super(ApiListFilesHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiListFilesHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/etc"

  def testDoesNotRaiseIfFirstCompomentIsEmpty(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="")
    self.handler.Handle(args, context=self.context)

  def testDoesNotRaiseIfPathIsRoot(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="/")
    self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentIsNotAllowlisted(self):
    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerListsFilesAndDirectories(self):
    fixture_test_lib.ClientFixture(self.client_id)

    # Fetch all children of a directory.
    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 4)
    for item in result.items:
      # Check that all files are really in the right directory.
      self.assertIn(self.file_path, item.path)

  def testHandlerFiltersDirectoriesIfFlagIsSet(self):
    fixture_test_lib.ClientFixture(self.client_id)

    # Only fetch sub-directories.
    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        directories_only=True)
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].is_directory, True)
    self.assertIn(self.file_path, result.items[0].path)

  def testHandlerRespectsTimestamp(self):
    # file_path is "fs/os/etc", a directory.
    self.CreateFileVersions(self.client_id, self.file_path + "/file")

    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_2)
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertIsInstance(result.items[0].last_collected_size, int)
    self.assertEqual(result.items[0].last_collected_size, 13)

    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_1)
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].last_collected_size, 11)

    args = vfs_plugin.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_0)
    result = self.handler.Handle(args, context=self.context)
    self.assertEmpty(result.items)

  def testRoot(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="/")
    result = self.handler.Handle(args, context=self.context)
    self.assertSameElements([(item.name, item.path) for item in result.items],
                            [("fs", "fs"), ("temp", "temp")])

  def testFs(self):
    args = vfs_plugin.ApiListFilesArgs(client_id=self.client_id, file_path="fs")
    result = self.handler.Handle(args, context=self.context)
    self.assertSameElements([(item.name, item.path) for item in result.items],
                            [("os", "fs/os"), ("tsk", "fs/tsk"),
                             ("ntfs", "fs/ntfs")])


class ApiGetFileTextHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):
  """Test for ApiGetFileTextHandler."""

  def setUp(self):
    super(ApiGetFileTextHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileTextHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileTextArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testDifferentTimestampsYieldDifferentFileContents(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        encoding=vfs_plugin.ApiGetFileTextArgs.Encoding.UTF_8)

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)

    # Change timestamp to get a different file version.
    args.timestamp = self.time_1
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.content, "Hello World")
    self.assertEqual(result.total_size, 11)

  def testEncodingChangesResult(self):
    args = vfs_plugin.ApiGetFileTextArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        encoding=vfs_plugin.ApiGetFileTextArgs.Encoding.UTF_16)

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, context=self.context)

    self.assertNotEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)


class ApiGetFileBlobHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):

  def setUp(self):
    super(ApiGetFileBlobHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetFileBlobHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnNonExistentPath(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar")
    with self.assertRaises(vfs_plugin.FileNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])

  def testRaisesOnExistingPathWithoutContent(self):
    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar")

    with self.assertRaises(vfs_plugin.FileContentNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])
    self.assertIsNone(exception.timestamp)

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileBlobArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testNewestFileContentIsReturnedByDefault(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"Goodbye World")

  def testOffsetAndLengthRestrictResult(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.file_path, offset=2, length=3)
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"odb")

  def testReturnsOlderVersionIfTimestampIsSupplied(self):
    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_1)
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"Hello World")

  def testLargeFileIsReturnedInMultipleChunks(self):
    chars = [b"a", b"b", b"x"]

    # Overwrite CHUNK_SIZE in handler for smaller test streams.
    self.handler.CHUNK_SIZE = 5

    client_path = db.ClientPath.OS(self.client_id,
                                   ["c", "Downloads", "huge.txt"])
    vfs_test_lib.CreateFile(
        client_path,
        content=b"".join([c * self.handler.CHUNK_SIZE for c in chars]))

    args = vfs_plugin.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/c/Downloads/huge.txt")
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    for chunk, char in zip(result.GenerateContent(), chars):
      self.assertEqual(chunk, char * self.handler.CHUNK_SIZE)


class ApiGetFileVersionTimesHandlerTest(api_test_lib.ApiCallHandlerTest,
                                        VfsTestMixin):

  def setUp(self):
    super(ApiGetFileVersionTimesHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = vfs_plugin.ApiGetFileVersionTimesHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)


class ApiGetFileDownloadCommandHandlerTest(api_test_lib.ApiCallHandlerTest,
                                           VfsTestMixin):

  def setUp(self):
    super(ApiGetFileDownloadCommandHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = vfs_plugin.ApiGetFileDownloadCommandHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)


class ApiCreateVfsRefreshOperationHandlerTest(
    notification_test_lib.NotificationTestMixin,
    api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateVfsRefreshOperationHandler."""

  def setUp(self):
    super(ApiCreateVfsRefreshOperationHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiCreateVfsRefreshOperationHandler()
    self.client_id = self.SetupClient(0)
    # Choose some directory with pathspec in the ClientFixture.
    self.file_path = "fs/os/Users/Shared"

  def testRaisesOnNonExistentPath(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar")
    with self.assertRaises(vfs_plugin.FileNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerRefreshStartsListDirectoryFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=1)
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id,
                                                result.operation_id)
    self.assertEqual(flow_obj.flow_class_name, "ListDirectory")

  def testHandlerRefreshStartsRecursiveListDirectoryFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=5)
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id,
                                                result.operation_id)
    self.assertEqual(flow_obj.flow_class_name, "RecursiveListDirectory")

  def testNotificationIsSent(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_plugin.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        max_depth=0,
        notify_user=True)
    result = self.handler.Handle(args, context=self.context)

    flow_test_lib.RunFlow(
        self.client_id, result.operation_id, check_flow_errors=False)

    pending_notifications = self.GetUserNotifications(self.context.username)

    self.assertIn("Recursive Directory Listing complete",
                  pending_notifications[0].message)

    self.assertEqual(
        pending_notifications[0].reference.vfs_file.path_components,
        ["Users", "Shared"])


class ApiGetVfsRefreshOperationStateHandlerTest(api_test_lib.ApiCallHandlerTest,
                                                VfsTestMixin):
  """Test for GetVfsRefreshOperationStateHandler."""

  def setUp(self):
    super(ApiGetVfsRefreshOperationStateHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsRefreshOperationStateHandler()
    self.client_id = self.SetupClient(0)

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    flow_id = self.CreateRecursiveListFlow(self.client_id)

    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=flow_id)

    # Flow was started and should be running.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(result.state, "RUNNING")

    # Terminate flow.
    flow_base.TerminateFlow(self.client_id, flow_id, "Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(result.state, "FINISHED")

  def testHandlerThrowsExceptionOnArbitraryFlowId(self):
    # Create a mock flow.
    flow_id = flow.StartFlow(
        client_id=self.client_id, flow_cls=discovery.Interrogate)

    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=flow_id)

    # Our mock flow is not a RecursiveListFlow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id="12345678")

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, context=self.context)


class ApiUpdateVfsFileContentHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiUpdateVfsFileContentHandler."""

  def setUp(self):
    super(ApiUpdateVfsFileContentHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiUpdateVfsFileContentHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/bin/bash"

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerStartsFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_plugin.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=self.file_path)
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id,
                                                result.operation_id)
    self.assertEqual(flow_obj.flow_class_name, transfer.MultiGetFile.__name__)
    self.assertEqual(flow_obj.creator, self.context.username)


class ApiGetVfsFileContentUpdateStateHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin):
  """Test for ApiGetVfsFileContentUpdateStateHandler."""

  def setUp(self):
    super(ApiGetVfsFileContentUpdateStateHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsFileContentUpdateStateHandler()
    self.client_id = self.SetupClient(0)

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    flow_id = self.CreateMultiGetFileFlow(
        self.client_id, file_path="fs/os/c/bin/bash")

    args = vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=flow_id)

    # Flow was started and should be running.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(result.state, "RUNNING")

    # Terminate flow.
    flow_base.TerminateFlow(self.client_id, flow_id, "Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(result.state, "FINISHED")

  def testHandlerRaisesOnArbitraryFlowId(self):
    # Create a mock flow.
    flow_id = flow.StartFlow(
        client_id=self.client_id, flow_cls=discovery.Interrogate)

    args = vfs_plugin.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=flow_id)

    # Our mock flow is not a MultiGetFile flow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_plugin.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id="12345678")

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, context=self.context)


class VfsTimelineTestMixin(object):
  """A helper mixin providing methods to prepare timelines for testing."""

  def SetupTestTimeline(self):
    client_id = self.SetupClient(0)
    fixture_test_lib.ClientFixture(client_id)

    # Choose some directory with pathspec in the ClientFixture.
    self.category_path = u"fs/os"
    self.folder_path = self.category_path + u"/Users/中国新闻网新闻中/Shared"
    self.file_path = self.folder_path + u"/a.txt"

    for i in range(0, 5):
      with test_lib.FakeTime(i):
        stat_entry = rdf_client_fs.StatEntry()
        stat_entry.st_mtime = rdfvalue.RDFDatetimeSeconds.Now()
        stat_entry.pathspec.path = self.file_path[len(self.category_path):]
        stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

        sha256 = (
            "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5")
        hash_entry = rdf_crypto.Hash(sha256=binascii.unhexlify(sha256))

        self.SetupFileMetadata(
            client_id,
            self.file_path,
            stat_entry=stat_entry,
            hash_entry=hash_entry)

    return client_id

  def SetupFileMetadata(self, client_id, vfs_path, stat_entry, hash_entry):
    if stat_entry:
      path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)
    else:
      path_info = rdf_objects.PathInfo.OS(components=vfs_path.split("/"))
    path_info.hash_entry = hash_entry
    data_store.REL_DB.WritePathInfos(client_id, [path_info])


class ApiGetVfsTimelineAsCsvHandlerTest(api_test_lib.ApiCallHandlerTest,
                                        VfsTimelineTestMixin):

  def setUp(self):
    super(ApiGetVfsTimelineAsCsvHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineAsCsvHandler()
    self.client_id = self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testTimelineIsReturnedInChunks(self):
    # Change chunk size to see if the handler behaves correctly.
    self.handler.CHUNK_SIZE = 1

    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=self.folder_path)
    result = self.handler.Handle(args, context=self.context)

    # Check rows returned correctly.
    self.assertTrue(hasattr(result, "GenerateContent"))
    for i in reversed(range(0, 5)):
      with test_lib.FakeTime(i):
        next_chunk = next(result.GenerateContent()).strip()
        timestamp = rdfvalue.RDFDatetime.Now()

        if i == 4:  # The first row includes the column headings.
          expected_csv = u"Timestamp,Datetime,Message,Timestamp_desc\n"
        else:
          expected_csv = u""
        expected_csv += u"%d,%s,%s,MODIFICATION"
        expected_csv %= (timestamp.AsMicrosecondsSinceEpoch(), timestamp,
                         self.file_path)

        self.assertEqual(next_chunk, expected_csv.encode("utf-8"))

  def testEmptyTimelineIsReturnedOnNonexistantPath(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="fs/os/non-existent/file/path")
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    with self.assertRaises(StopIteration):
      next(result.GenerateContent())

  def testTimelineInBodyFormatCorrectlyReturned(self):
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id,
        file_path=self.folder_path,
        format=vfs_plugin.ApiGetVfsTimelineAsCsvArgs.Format.BODY)
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    expected_csv = u"|%s|0|----------|0|0|0|0|4|0|0\n" % self.file_path
    self.assertEqual(content, expected_csv.encode("utf-8"))

  def testTimelineInBodyFormatWithHashCorrectlyReturned(self):
    client_id = self.SetupClient(1)
    stat_entry = rdf_client_fs.StatEntry(st_size=1337)
    stat_entry.pathspec.path = u"foo/bar"
    stat_entry.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    hash_entry = rdf_crypto.Hash(md5=b"quux", sha256=b"norf")
    self.SetupFileMetadata(
        client_id,
        u"fs/os/foo/bar",
        stat_entry=stat_entry,
        hash_entry=hash_entry)

    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=client_id,
        file_path=u"fs/os/foo",
        format=vfs_plugin.ApiGetVfsTimelineAsCsvArgs.Format.BODY)
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    expected_csv = u"71757578|fs/os/foo/bar|0|----------|0|0|1337|0|0|0|0\n"
    self.assertEqual(content, expected_csv.encode("utf-8"))

  def testTimelineEntriesWithHashOnlyAreIgnoredOnBodyExport(self):
    client_id = self.SetupClient(1)
    hash_entry = rdf_crypto.Hash(sha256=b"quux")
    self.SetupFileMetadata(
        client_id, u"fs/os/foo/bar", stat_entry=None, hash_entry=hash_entry)
    args = vfs_plugin.ApiGetVfsTimelineAsCsvArgs(
        client_id=client_id,
        file_path=u"fs/os/foo",
        format=vfs_plugin.ApiGetVfsTimelineAsCsvArgs.Format.BODY)
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    self.assertEqual(content, b"")


class ApiGetVfsTimelineHandlerTest(api_test_lib.ApiCallHandlerTest,
                                   VfsTimelineTestMixin):

  def setUp(self):
    super(ApiGetVfsTimelineHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineHandler()
    self.client_id = self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_plugin.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path="/analysis")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)


class ApiGetVfsFilesArchiveHandlerTest(api_test_lib.ApiCallHandlerTest,
                                       VfsTestMixin):
  """Tests for ApiGetVfsFileArchiveHandler."""

  def setUp(self):
    super(ApiGetVfsFilesArchiveHandlerTest, self).setUp()

    self.handler = vfs_plugin.ApiGetVfsFilesArchiveHandler()
    self.client_id = self.SetupClient(0)

    self.CreateFileVersions(self.client_id, "fs/os/c/Downloads/a.txt")
    self.CreateFileVersions(self.client_id, "fs/os/c/b.txt")

  def testGeneratesZipArchiveWhenPathIsNotPassed(self):
    archive_path1 = "vfs_C_1000000000000000/fs/os/c/Downloads/a.txt"
    archive_path2 = "vfs_C_1000000000000000/fs/os/c/b.txt"

    result = self.handler.Handle(
        vfs_plugin.ApiGetVfsFilesArchiveArgs(client_id=self.client_id),
        context=self.context)

    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    self.assertEqual(
        set(zip_fd.namelist()), set([archive_path1, archive_path2]))

    for path in [archive_path1, archive_path2]:
      contents = zip_fd.read(path)
      self.assertEqual(contents, b"Goodbye World")

  def testFiltersArchivedFilesByPath(self):
    archive_path = ("vfs_C_1000000000000000_fs_os_c_Downloads/"
                    "fs/os/c/Downloads/a.txt")

    result = self.handler.Handle(
        vfs_plugin.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, file_path="fs/os/c/Downloads"),
        context=self.context)

    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    self.assertEqual(zip_fd.namelist(), [archive_path])

    contents = zip_fd.read(archive_path)
    self.assertEqual(contents, b"Goodbye World")

  def testNonExistentPathRaises(self):
    result = self.handler.Handle(
        vfs_plugin.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, file_path="fs/os/blah/blah"),
        context=self.context)

    with self.assertRaises(db.UnknownPathError):
      out_fd = io.BytesIO()
      for chunk in result.GenerateContent():
        out_fd.write(chunk)

  def testInvalidPathTriggersException(self):
    with self.assertRaises(ValueError):
      self.handler.Handle(
          vfs_plugin.ApiGetVfsFilesArchiveArgs(
              client_id=self.client_id, file_path="invalid-prefix/path"),
          context=self.context)

  def testHandlerRespectsTimestamp(self):
    archive_path1 = "vfs_C_1000000000000000/fs/os/c/Downloads/a.txt"
    archive_path2 = "vfs_C_1000000000000000/fs/os/c/b.txt"

    result = self.handler.Handle(
        vfs_plugin.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, timestamp=self.time_2),
        context=self.context)
    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)
    zip_fd = zipfile.ZipFile(out_fd, "r")

    self.assertCountEqual(zip_fd.namelist(), [archive_path1, archive_path2])
    self.assertEqual(zip_fd.read(archive_path1), b"Goodbye World")
    self.assertEqual(zip_fd.read(archive_path2), b"Goodbye World")

    result = self.handler.Handle(
        vfs_plugin.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, timestamp=self.time_1),
        context=self.context)
    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)
    zip_fd = zipfile.ZipFile(out_fd, "r")

    self.assertCountEqual(zip_fd.namelist(), [archive_path1, archive_path2])
    self.assertEqual(zip_fd.read(archive_path1), b"Hello World")
    self.assertEqual(zip_fd.read(archive_path2), b"Hello World")


class DecodersTestMixin(object):

  def setUp(self):
    super(DecodersTestMixin, self).setUp()
    self.client_id = self.SetupClient(0)

    decoders_patcher = mock.patch.object(
        decoders, "FACTORY", factory.Factory(decoders.AbstractDecoder))
    decoders_patcher.start()
    self.addCleanup(decoders_patcher.stop)

  def Touch(self, vfs_path, content=b""):
    path_type, components = rdf_objects.ParseCategorizedPath(vfs_path)
    client_path = db.ClientPath(
        client_id=self.client_id, path_type=path_type, components=components)
    vfs_test_lib.CreateFile(client_path, content=content)


class ApiGetFileDecodersHandler(DecodersTestMixin,
                                api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiGetFileDecodersHandler, self).setUp()
    self.handler = vfs_plugin.ApiGetFileDecodersHandler()

  def testSimple(self):
    self.Touch("fs/os/foo/bar/baz")

    class FooDecoder(decoders.AbstractDecoder):

      def Check(self, filedesc):
        del filedesc  # Unused.
        return True

      def Decode(self, filedesc):
        raise NotImplementedError()

    decoders.FACTORY.Register("Foo", FooDecoder)

    args = vfs_plugin.ApiGetFileDecodersArgs()
    args.client_id = self.client_id
    args.file_path = "fs/os/foo/bar/baz"

    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(result.decoder_names, ["Foo"])

  def testMultipleDecoders(self):
    self.Touch("fs/os/foo/bar", content=b"bar")
    self.Touch("fs/os/foo/baz", content=b"baz")
    self.Touch("fs/os/foo/quux", content=b"quux")

    class BarQuuxDecoder(decoders.AbstractDecoder):

      def Check(self, filedesc):
        return filedesc.Read(1024) in [b"bar", b"quux"]

      def Decode(self, filedesc):
        raise NotImplementedError()

    class BazQuuxDecoder(decoders.AbstractDecoder):

      def Check(self, filedesc):
        return filedesc.Read(1024) in [b"baz", b"quux"]

      def Decode(self, filedesc):
        raise NotImplementedError()

    decoders.FACTORY.Register("BarQuux", BarQuuxDecoder)
    decoders.FACTORY.Register("BazQuux", BazQuuxDecoder)

    args = vfs_plugin.ApiGetFileDecodersArgs()
    args.client_id = self.client_id

    args.file_path = "fs/os/foo/bar"
    result = self.handler.Handle(args, context=self.context)
    self.assertCountEqual(result.decoder_names, ["BarQuux"])

    args.file_path = "fs/os/foo/baz"
    result = self.handler.Handle(args)
    self.assertCountEqual(result.decoder_names, ["BazQuux"])

    args.file_path = "fs/os/foo/quux"
    result = self.handler.Handle(args)
    self.assertCountEqual(result.decoder_names, ["BarQuux", "BazQuux"])


class ApiGetDecodedFileHandlerTest(DecodersTestMixin,
                                   api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super(ApiGetDecodedFileHandlerTest, self).setUp()
    self.handler = vfs_plugin.ApiGetDecodedFileHandler()

  def _Result(self, args):
    stream = self.handler.Handle(args, context=self.context)
    return b"".join(stream.GenerateContent())

  def testSimpleDecoder(self):
    self.Touch("fs/os/foo", b"foo")

    class FooDecoder(decoders.AbstractDecoder):

      def Check(self, filedesc):
        del filedesc  # Unused.
        raise NotImplementedError()

      def Decode(self, filedesc):
        del filedesc  # Unused.
        yield b"bar"

    decoders.FACTORY.Register("Foo", FooDecoder)

    args = vfs_plugin.ApiGetDecodedFileArgs()
    args.client_id = self.client_id
    args.file_path = "fs/os/foo"
    args.decoder_name = "Foo"

    self.assertEqual(self._Result(args), b"bar")

  def testMultiChunkDecoder(self):
    self.Touch("fs/os/quux", b"QUUX" * 100)
    self.Touch("fs/os/thud", b"THUD" * 100)

    class BarDecoder(decoders.AbstractDecoder):

      def Check(self, filedesc):
        del filedesc  # Unused.
        raise NotImplementedError()

      def Decode(self, filedesc):
        while True:
          chunk = filedesc.Read(4)
          if not chunk:
            return

          if chunk == b"QUUX":
            yield b"NORF"

          if chunk == b"THUD":
            yield b"BLARGH"

    decoders.FACTORY.Register("Bar", BarDecoder)

    args = vfs_plugin.ApiGetDecodedFileArgs()
    args.client_id = self.client_id
    args.decoder_name = "Bar"

    args.file_path = "fs/os/quux"
    self.assertEqual(self._Result(args), b"NORF" * 100)

    args.file_path = "fs/os/thud"
    self.assertEqual(self._Result(args), b"BLARGH" * 100)

  def testUnknownDecoder(self):
    self.Touch("fs/os/baz")

    args = vfs_plugin.ApiGetDecodedFileArgs()
    args.client_id = self.client_id
    args.file_path = "fs/os/baz"
    args.decoder_name = "Baz"

    with self.assertRaisesRegex(ValueError, "'Baz'"):
      self._Result(args)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
