#!/usr/bin/env python
"""This modules contains tests for VFS API handlers."""

import binascii
import io
import os
import zipfile

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import vfs_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import vfs as vfs_plugin
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class VfsTestMixin:
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
        flow_args=flow_args,
    )

  def CreateMultiGetFileFlow(self, client_id, file_path):
    pathspec = rdf_paths.PathSpec(
        path=file_path, pathtype=rdf_paths.PathSpec.PathType.OS
    )
    flow_args = transfer.MultiGetFileArgs(pathspecs=[pathspec])

    return flow.StartFlow(
        client_id=client_id, flow_cls=transfer.MultiGetFile, flow_args=flow_args
    )


class ApiGetFileDetailsHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):
  """Test for ApiGetFileDetailsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetFileDetailsHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetFileDetailsArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnNonexistentPath(self):
    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path="/fs/os/foo/bar"
    )
    with self.assertRaises(vfs_plugin.FileNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerReturnsNewestVersionByDefault(self):
    # Get file version without specifying a timestamp.
    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path
    )
    result = self.handler.Handle(args, context=self.context)

    # Should return the newest version.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(result.file.age),
        self.time_2,
        delta=rdfvalue.Duration.From(1, rdfvalue.SECONDS),
    )

  def testHandlerReturnsClosestSpecificVersion(self):
    # Get specific version.
    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=int(self.time_1),
    )
    result = self.handler.Handle(args, context=self.context)

    # The age of the returned version might have a slight deviation.
    self.assertEqual(result.file.path, self.file_path)
    self.assertAlmostEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(result.file.age),
        self.time_1,
        delta=rdfvalue.Duration.From(1, rdfvalue.SECONDS),
    )

  def testResultIncludesDetails(self):
    """Checks if the details include certain attributes.

    Instead of using a (fragile) regression test, we enumerate important
    attributes here and make sure they are returned.
    """

    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path
    )
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

    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=self.file_path
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertFalse(result.file.is_directory)

    args = vfs_pb2.ApiGetFileDetailsArgs(
        client_id=self.client_id, file_path=dir_path
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertTrue(result.file.is_directory)


class ApiListFilesHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):
  """Test for ApiListFilesHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiListFilesHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/etc"

  def testDoesNotRaiseIfFirstComponentIsEmpty(self):
    args = vfs_pb2.ApiListFilesArgs(client_id=self.client_id, file_path="")
    self.handler.Handle(args, context=self.context)

  def testDoesNotRaiseIfPathIsRoot(self):
    args = vfs_pb2.ApiListFilesArgs(client_id=self.client_id, file_path="/")
    self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentIsNotAllowlisted(self):
    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerListsFilesAndDirectories(self):
    fixture_test_lib.ClientFixture(self.client_id)

    # Fetch all children of a directory.
    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id, file_path=self.file_path
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 4)
    for item in result.items:
      # Check that all files are really in the right directory.
      self.assertIn(self.file_path, item.path)

  def testHandlerFiltersDirectoriesIfFlagIsSet(self):
    fixture_test_lib.ClientFixture(self.client_id)

    # Only fetch sub-directories.
    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        directories_only=True,
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].is_directory, True)
    self.assertIn(self.file_path, result.items[0].path)

  def testHandlerRespectsTimestamp(self):
    # file_path is "fs/os/etc", a directory.
    self.CreateFileVersions(self.client_id, self.file_path + "/file")

    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=int(self.time_2),
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertIsInstance(result.items[0].last_collected_size, int)
    self.assertEqual(result.items[0].last_collected_size, 13)

    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=int(self.time_1),
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.items, 1)
    self.assertEqual(result.items[0].last_collected_size, 11)

    args = vfs_pb2.ApiListFilesArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=int(self.time_0),
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertEmpty(result.items)

  def testRoot(self):
    args = vfs_pb2.ApiListFilesArgs(client_id=self.client_id, file_path="/")
    result = self.handler.Handle(args, context=self.context)
    self.assertSameElements(
        [(item.name, item.path) for item in result.items],
        [("fs", "fs"), ("temp", "temp")],
    )

  def testFs(self):
    args = vfs_pb2.ApiListFilesArgs(client_id=self.client_id, file_path="fs")
    result = self.handler.Handle(args, context=self.context)
    self.assertSameElements(
        [(item.name, item.path) for item in result.items],
        [("os", "fs/os"), ("tsk", "fs/tsk"), ("ntfs", "fs/ntfs")],
    )


class ApiBrowseFilesystemHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):
  """Test for ApiBrowseFilesystemHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiBrowseFilesystemHandler()
    self.client_id = self.SetupClient(0)

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)):
      vfs_test_lib.CreateFile(
          db.ClientPath.NTFS(self.client_id, ["mixeddir", "ntfs-then-os"]),
          b"NTFS",
      )
      vfs_test_lib.CreateFile(
          db.ClientPath.OS(self.client_id, ["mixeddir", "os-then-ntfs"]), b"OS"
      )
      vfs_test_lib.CreateFile(
          db.ClientPath.TSK(self.client_id, ["mixeddir", "tsk-only"]), b"TSK"
      )

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)):
      vfs_test_lib.CreateFile(
          db.ClientPath.OS(self.client_id, ["mixeddir", "ntfs-then-os"]), b"OS"
      )
      vfs_test_lib.CreateFile(
          db.ClientPath.NTFS(self.client_id, ["mixeddir", "os-then-ntfs"]),
          b"NTFS",
      )
      vfs_test_lib.CreateFile(
          db.ClientPath.OS(self.client_id, ["mixeddir", "os-only"]), b"OS"
      )

  def testQueriesRootPathForEmptyPath(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(client_id=self.client_id, path="")
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.root_entry.file.name, "")
    self.assertEqual(result.root_entry.file.path, "fs/os/")
    self.assertEqual(result.root_entry.file.is_directory, True)
    self.assertLen(result.root_entry.children, 1)
    self.assertEqual(result.root_entry.children[0].file.name, "mixeddir")
    self.assertEqual(result.root_entry.children[0].file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.children[0].file.is_directory, True)

  def testQueriesRootPathForSingleSlashPath(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(client_id=self.client_id, path="/")
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.root_entry.file.name, "")
    self.assertEqual(result.root_entry.file.path, "fs/os/")
    self.assertEqual(result.root_entry.file.is_directory, True)
    self.assertLen(result.root_entry.children, 1)
    self.assertEqual(result.root_entry.children[0].file.name, "mixeddir")
    self.assertEqual(result.root_entry.children[0].file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.children[0].file.is_directory, True)

  def testHandlerListsFilesAndDirectories(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id, path="/mixeddir"
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.root_entry.file.name, "mixeddir")
    self.assertEqual(result.root_entry.file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.file.is_directory, True)

    self.assertLen(result.root_entry.children, 4)
    self.assertEqual(result.root_entry.children[0].file.name, "ntfs-then-os")
    self.assertEqual(result.root_entry.children[1].file.name, "os-only")
    self.assertEqual(result.root_entry.children[2].file.name, "os-then-ntfs")
    self.assertEqual(result.root_entry.children[3].file.name, "tsk-only")

  def testHandlerCanListDirectoryTree(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id, path="/mixeddir", include_directory_tree=True
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(result.root_entry.file.is_directory)
    self.assertEqual(result.root_entry.file.name, "")
    self.assertEqual(result.root_entry.file.path, "fs/os/")
    self.assertEqual(result.root_entry.file.is_directory, True)

    self.assertLen(result.root_entry.children, 1)
    self.assertEqual(result.root_entry.children[0].file.name, "mixeddir")
    self.assertEqual(result.root_entry.children[0].file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.children[0].file.is_directory, True)

    self.assertLen(result.root_entry.children[0].children, 4)
    self.assertEqual(
        result.root_entry.children[0].children[0].file.name, "ntfs-then-os"
    )
    self.assertEqual(
        result.root_entry.children[0].children[1].file.name, "os-only"
    )
    self.assertEqual(
        result.root_entry.children[0].children[2].file.name, "os-then-ntfs"
    )
    self.assertEqual(
        result.root_entry.children[0].children[3].file.name, "tsk-only"
    )

  def testHandlerCanListDirectoryTreeWhenPointingToFile(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id,
        path="/mixeddir/os-only",
        include_directory_tree=True,
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(result.root_entry.file.is_directory)
    self.assertEqual(result.root_entry.file.name, "")
    self.assertEqual(result.root_entry.file.path, "fs/os/")
    self.assertEqual(result.root_entry.file.is_directory, True)

    self.assertLen(result.root_entry.children, 1)
    self.assertEqual(result.root_entry.children[0].file.name, "mixeddir")
    self.assertEqual(result.root_entry.children[0].file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.children[0].file.is_directory, True)

    self.assertLen(result.root_entry.children[0].children, 4)
    self.assertEqual(
        result.root_entry.children[0].children[0].file.name, "ntfs-then-os"
    )
    self.assertEqual(
        result.root_entry.children[0].children[1].file.name, "os-only"
    )
    self.assertEqual(
        result.root_entry.children[0].children[2].file.name, "os-then-ntfs"
    )
    self.assertEqual(
        result.root_entry.children[0].children[3].file.name, "tsk-only"
    )

  def testHandlerMergesFilesOfDifferentPathSpecs(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id, path="/mixeddir"
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.root_entry.file.name, "mixeddir")
    self.assertEqual(result.root_entry.file.path, "fs/os/mixeddir")
    self.assertEqual(result.root_entry.file.is_directory, True)

    self.assertLen(result.root_entry.children, 4)
    self.assertEqual(result.root_entry.children[0].file.name, "ntfs-then-os")
    self.assertEqual(
        result.root_entry.children[0].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.OS,
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[0].file.last_collected_size,
        len("OS"),
    )
    self.assertEqual(result.root_entry.children[1].file.name, "os-only")
    self.assertEqual(
        result.root_entry.children[1].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.OS,
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[1].file.last_collected_size,
        len("OS"),
    )

    self.assertEqual(result.root_entry.children[2].file.name, "os-then-ntfs")
    self.assertEqual(
        result.root_entry.children[2].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.NTFS,
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[2].file.last_collected_size,
        len("NTFS"),
    )

    self.assertEqual(result.root_entry.children[3].file.name, "tsk-only")
    self.assertEqual(
        result.root_entry.children[3].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.TSK,
    )
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[3].file.last_collected_size,
        len("TSK"),
    )

  def testHandlerRespectsTimestamp(self):
    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id,
        path="/mixeddir",
        timestamp=int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)),
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertEmpty(result.root_entry.children)

    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id,
        path="/mixeddir",
        timestamp=int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)),
    )
    result = self.handler.Handle(args, context=self.context)
    self.assertLen(result.root_entry.children, 3)
    self.assertEqual(result.root_entry.children[0].file.name, "ntfs-then-os")
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[0].file.last_collected_size, len("NTFS")
    )
    self.assertEqual(
        result.root_entry.children[0].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.NTFS,
    )

    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id,
        path="/mixeddir",
        timestamp=int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2)),
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.root_entry.children, 4)
    self.assertEqual(result.root_entry.children[0].file.name, "ntfs-then-os")
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[0].file.last_collected_size, len("OS")
    )
    self.assertEqual(
        result.root_entry.children[0].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.OS,
    )

    args = vfs_pb2.ApiBrowseFilesystemArgs(
        client_id=self.client_id,
        path="/mixeddir",
        timestamp=int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10)),
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertLen(result.root_entry.children, 4)
    self.assertEqual(result.root_entry.children[0].file.name, "ntfs-then-os")
    self.assertEqual(  # pylint: disable=g-generic-assert
        result.root_entry.children[0].file.last_collected_size, len("OS")
    )
    self.assertEqual(
        result.root_entry.children[0].file.stat.pathspec.pathtype,
        jobs_pb2.PathSpec.PathType.OS,
    )


class ApiGetFileTextHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):
  """Test for ApiGetFileTextHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetFileTextHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetFileTextArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetFileTextArgs(client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetFileTextArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testDifferentTimestampsYieldDifferentFileContents(self):
    args = vfs_pb2.ApiGetFileTextArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        encoding=vfs_pb2.ApiGetFileTextArgs.Encoding.UTF_8,
    )

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)

    # Change timestamp to get a different file version.
    args.timestamp = self.time_1.AsMicrosecondsSinceEpoch()
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.content, "Hello World")
    self.assertEqual(result.total_size, 11)

  def testEncodingChangesResult(self):
    args = vfs_pb2.ApiGetFileTextArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        encoding=vfs_pb2.ApiGetFileTextArgs.Encoding.UTF_16,
    )

    # Retrieving latest version by not setting a timestamp.
    result = self.handler.Handle(args, context=self.context)

    self.assertNotEqual(result.content, "Goodbye World")
    self.assertEqual(result.total_size, 13)


class ApiGetFileBlobHandlerTest(api_test_lib.ApiCallHandlerTest, VfsTestMixin):

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetFileBlobHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/Downloads/a.txt"
    self.CreateFileVersions(self.client_id, self.file_path)

  def testRaisesOnNonExistentPath(self):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar"
    )
    with self.assertRaises(vfs_plugin.FileNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])

  def testRaisesOnExistingPathWithoutContent(self):
    path_info = objects_pb2.PathInfo(
        path_type=objects_pb2.PathInfo.PathType.OS, components=["foo", "bar"]
    )
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar"
    )

    with self.assertRaises(vfs_plugin.FileContentNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])
    self.assertIsNone(exception.timestamp)

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetFileBlobArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetFileBlobArgs(client_id=self.client_id, file_path="/")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testNewestFileContentIsReturnedByDefault(self):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.file_path
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"Goodbye World")

  def testOffsetAndLengthRestrictResult(self):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path=self.file_path, offset=2, length=3
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"odb")

  def testReturnsOlderVersionIfTimestampIsSupplied(self):
    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        timestamp=self.time_1.AsMicrosecondsSinceEpoch(),
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    self.assertEqual(next(result.GenerateContent()), b"Hello World")

  def testLargeFileIsReturnedInMultipleChunks(self):
    chars = [b"a", b"b", b"x"]

    # Overwrite CHUNK_SIZE in handler for smaller test streams.
    self.handler.CHUNK_SIZE = 5

    client_path = db.ClientPath.OS(
        self.client_id, ["c", "Downloads", "huge.txt"]
    )
    vfs_test_lib.CreateFile(
        client_path,
        content=b"".join([c * self.handler.CHUNK_SIZE for c in chars]),
    )

    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=self.client_id, file_path="fs/os/c/Downloads/huge.txt"
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    for chunk, char in zip(result.GenerateContent(), chars):
      self.assertEqual(chunk, char * self.handler.CHUNK_SIZE)


class ApiGetFileVersionTimesHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.handler = vfs_plugin.ApiGetFileVersionTimesHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path=""
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetFileVersionTimesArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args)


class ApiGetFileDownloadCommandHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.handler = vfs_plugin.ApiGetFileDownloadCommandHandler()

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path=""
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetFileDownloadCommandArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)


class ApiCreateVfsRefreshOperationHandlerTest(
    notification_test_lib.NotificationTestMixin,
    api_test_lib.ApiCallHandlerTest,
    VfsTestMixin,
):
  """Test for ApiCreateVfsRefreshOperationHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiCreateVfsRefreshOperationHandler()
    self.client_id = self.SetupClient(0)
    # Choose some directory with pathspec in the ClientFixture.
    self.file_path = "fs/os/Users/Shared"

  def testRaisesOnNonExistentPath(self):
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="fs/os/foo/bar"
    )
    with self.assertRaises(vfs_plugin.FileNotFoundError) as context:
      self.handler.Handle(args, context=self.context)

    exception = context.exception
    self.assertEqual(exception.client_id, self.client_id)
    self.assertEqual(exception.path_type, rdf_objects.PathInfo.PathType.OS)
    self.assertCountEqual(exception.components, ["foo", "bar"])

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=""
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerRefreshStartsListDirectoryFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=1
    )
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(
        self.client_id, result.operation_id
    )
    self.assertEqual(flow_obj.flow_class_name, "ListDirectory")

  def testHandlerRefreshStartsRecursiveListDirectoryFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=self.file_path, max_depth=5
    )
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(
        self.client_id, result.operation_id
    )
    self.assertEqual(flow_obj.flow_class_name, "RecursiveListDirectory")

  def testNotificationIsSent(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id,
        file_path=self.file_path,
        max_depth=0,
        notify_user=True,
    )
    result = self.handler.Handle(args, context=self.context)

    flow_test_lib.RunFlow(
        self.client_id, result.operation_id, check_flow_errors=False
    )

    pending_notifications = self.GetUserNotifications(self.context.username)

    self.assertIn(
        "Recursive Directory Listing complete", pending_notifications[0].message
    )

    self.assertEqual(
        list(pending_notifications[0].reference.vfs_file.path_components),
        ["Users", "Shared"],
    )

  def testPathTranslation_TSK(self):
    self._testPathTranslation(
        "/fs/tsk/c/foo",
        jobs_pb2.PathSpec(
            path="/c/foo", pathtype=jobs_pb2.PathSpec.PathType.TSK
        ),
    )

  def testPathTranslation_NTFS(self):
    self._testPathTranslation(
        "/fs/ntfs/c/foo",
        jobs_pb2.PathSpec(
            path="/c/foo", pathtype=jobs_pb2.PathSpec.PathType.NTFS
        ),
    )

  def testPathTranslation_OS(self):
    self._testPathTranslation(
        "/fs/os/c/foo",
        jobs_pb2.PathSpec(
            path="/c/foo", pathtype=jobs_pb2.PathSpec.PathType.OS
        ),
    )

  def testPathTranslation_REGISTRY(self):
    self._testPathTranslation(
        "/registry/c/foo",
        jobs_pb2.PathSpec(
            path="/c/foo", pathtype=jobs_pb2.PathSpec.PathType.REGISTRY
        ),
    )

  def testPathTranslation_TMPFILE(self):
    self._testPathTranslation(
        "/temp/c/foo",
        jobs_pb2.PathSpec(
            path="/c/foo", pathtype=jobs_pb2.PathSpec.PathType.TMPFILE
        ),
    )

  def _testPathTranslation(
      self, directory: str, expected_pathspec: jobs_pb2.PathSpec
  ) -> None:
    self.CreateFileVersions(
        self.client_id, os.path.join(directory, "some_file.txt")
    )
    args = vfs_pb2.ApiCreateVfsRefreshOperationArgs(
        client_id=self.client_id, file_path=directory
    )
    result = self.handler.Handle(args, context=self.context)
    flow_obj = data_store.REL_DB.ReadFlowObject(
        self.client_id, result.operation_id
    )

    args = flows_pb2.RecursiveListDirectoryArgs()
    flow_obj.args.Unpack(args)
    self.assertEqual(args.pathspec, expected_pathspec)


class ApiGetVfsRefreshOperationStateHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):
  """Test for GetVfsRefreshOperationStateHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetVfsRefreshOperationStateHandler()
    self.client_id = self.SetupClient(0)

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    flow_id = self.CreateRecursiveListFlow(self.client_id)

    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=flow_id
    )

    # Flow was started and should be running.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(
        result.state, vfs_pb2.ApiGetVfsRefreshOperationStateResult.State.RUNNING
    )

    # Terminate flow.
    flow_base.TerminateFlow(self.client_id, flow_id, "Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(
        result.state,
        vfs_pb2.ApiGetVfsRefreshOperationStateResult.State.FINISHED,
    )

  def testHandlerThrowsExceptionOnArbitraryFlowId(self):
    # Create a mock flow.
    flow_id = flow.StartFlow(
        client_id=self.client_id, flow_cls=discovery.Interrogate
    )

    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id=flow_id
    )

    # Our mock flow is not a RecursiveListFlow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id="12345678"
    )

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsRefreshOperationNotFoundError):
      self.handler.Handle(args, context=self.context)


class ApiUpdateVfsFileContentHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiUpdateVfsFileContentHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiUpdateVfsFileContentHandler()
    self.client_id = self.SetupClient(0)
    self.file_path = "fs/os/c/bin/bash"

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=""
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testHandlerStartsFlow(self):
    fixture_test_lib.ClientFixture(self.client_id)

    args = vfs_pb2.ApiUpdateVfsFileContentArgs(
        client_id=self.client_id, file_path=self.file_path
    )
    result = self.handler.Handle(args, context=self.context)

    flow_obj = data_store.REL_DB.ReadFlowObject(
        self.client_id, result.operation_id
    )
    self.assertEqual(flow_obj.flow_class_name, transfer.MultiGetFile.__name__)
    self.assertEqual(flow_obj.creator, self.context.username)


class ApiGetVfsFileContentUpdateStateHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):
  """Test for ApiGetVfsFileContentUpdateStateHandler."""

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetVfsFileContentUpdateStateHandler()
    self.client_id = self.SetupClient(0)

  def testHandlerReturnsCorrectStateForFlow(self):
    # Create a mock refresh operation.
    flow_id = self.CreateMultiGetFileFlow(
        self.client_id, file_path="fs/os/c/bin/bash"
    )

    args = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=flow_id
    )

    # Flow was started and should be running.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(
        result.state,
        vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State.RUNNING,
    )

    # Terminate flow.
    flow_base.TerminateFlow(self.client_id, flow_id, "Fake error")

    # Recheck status and see if it changed.
    result = self.handler.Handle(args, context=self.context)
    self.assertEqual(
        result.state,
        vfs_pb2.ApiGetVfsFileContentUpdateStateResult.State.FINISHED,
    )

  def testHandlerRaisesOnArbitraryFlowId(self):
    # Create a mock flow.
    flow_id = flow.StartFlow(
        client_id=self.client_id, flow_cls=discovery.Interrogate
    )

    args = vfs_pb2.ApiGetVfsFileContentUpdateStateArgs(
        client_id=self.client_id, operation_id=flow_id
    )

    # Our mock flow is not a MultiGetFile flow, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, context=self.context)

  def testHandlerThrowsExceptionOnUnknownFlowId(self):
    # Create args with an operation id not referencing any flow.
    args = vfs_pb2.ApiGetVfsRefreshOperationStateArgs(
        client_id=self.client_id, operation_id="12345678"
    )

    # Our mock flow can't be read, so an error should be raised.
    with self.assertRaises(vfs_plugin.VfsFileContentUpdateNotFoundError):
      self.handler.Handle(args, context=self.context)


class VfsTimelineTestMixin:
  """A helper mixin providing methods to prepare timelines for testing."""

  def SetupTestTimeline(self):
    client_id = self.SetupClient(0)
    fixture_test_lib.ClientFixture(client_id)

    # Choose some directory with pathspec in the ClientFixture.
    self.category_path = "fs/os"
    self.folder_path = self.category_path + "/Users/中国新闻网新闻中/Shared"
    self.file_path = self.folder_path + "/a.txt"

    for i in range(0, 5):
      with test_lib.FakeTime(i):
        stat_entry = jobs_pb2.StatEntry()
        stat_entry.st_mtime = (
            rdfvalue.RDFDatetimeSeconds.Now().AsSecondsSinceEpoch()
        )
        stat_entry.pathspec.path = self.file_path[len(self.category_path) :]
        stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

        sha256 = (
            "0e8dc93e150021bb4752029ebbff51394aa36f069cf19901578e4f06017acdb5"
        )
        hash_entry = jobs_pb2.Hash(sha256=binascii.unhexlify(sha256))

        self.SetupFileMetadata(
            client_id,
            self.file_path,
            stat_entry=stat_entry,
            hash_entry=hash_entry,
        )

    return client_id

  def SetupFileMetadata(
      self,
      client_id: str,
      vfs_path: str,
      stat_entry: jobs_pb2.StatEntry,
      hash_entry: jobs_pb2.Hash,
  ) -> None:
    if stat_entry:
      rdf_stat_entry = mig_client_fs.ToRDFStatEntry(stat_entry)
      path_info = rdf_objects.PathInfo.FromStatEntry(rdf_stat_entry)
    else:
      path_info = rdf_objects.PathInfo.OS(components=vfs_path.split("/"))
    path_info = mig_objects.ToProtoPathInfo(path_info)
    path_info.hash_entry.CopyFrom(hash_entry)
    data_store.REL_DB.WritePathInfos(client_id, [path_info])


class ApiGetVfsTimelineAsCsvHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTimelineTestMixin
):

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineAsCsvHandler()
    self.client_id = self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=""
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testTimelineIsReturnedInChunks(self):
    # Change chunk size to see if the handler behaves correctly.
    self.handler.CHUNK_SIZE = 1

    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path=self.folder_path
    )
    result = self.handler.Handle(args, context=self.context)

    # Check rows returned correctly.
    self.assertTrue(hasattr(result, "GenerateContent"))
    for i in reversed(range(0, 5)):
      with test_lib.FakeTime(i):
        next_chunk = next(result.GenerateContent()).strip()
        timestamp = rdfvalue.RDFDatetime.Now()

        if i == 4:  # The first row includes the column headings.
          expected_csv = "Timestamp,Datetime,Message,Timestamp_desc\n"
        else:
          expected_csv = ""
        expected_csv += "%d,%s,%s,MODIFICATION"
        expected_csv %= (
            timestamp.AsMicrosecondsSinceEpoch(),
            timestamp,
            self.file_path,
        )

        self.assertEqual(next_chunk, expected_csv.encode("utf-8"))

  def testEmptyTimelineIsReturnedOnNonexistentPath(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id, file_path="fs/os/non-existent/file/path"
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertTrue(hasattr(result, "GenerateContent"))
    with self.assertRaises(StopIteration):
      next(result.GenerateContent())

  def testTimelineInBodyFormatCorrectlyReturned(self):
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=self.client_id,
        file_path=self.folder_path,
        format=vfs_pb2.ApiGetVfsTimelineAsCsvArgs.Format.BODY,
    )
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    expected_csv = "|%s|0|?---------|0|0|0|0|4|0|0\n" % self.file_path
    self.assertEqual(content, expected_csv.encode("utf-8"))

  def testTimelineInBodyFormatWithHashCorrectlyReturned(self):
    client_id = self.SetupClient(1)
    stat_entry = jobs_pb2.StatEntry(st_size=1337)
    stat_entry.pathspec.path = "foo/bar"
    stat_entry.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    hash_entry = jobs_pb2.Hash(md5=b"quux", sha256=b"norf")
    self.SetupFileMetadata(
        client_id, "fs/os/foo/bar", stat_entry=stat_entry, hash_entry=hash_entry
    )

    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=client_id,
        file_path="fs/os/foo",
        format=vfs_pb2.ApiGetVfsTimelineAsCsvArgs.Format.BODY,
    )
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    expected_csv = "71757578|fs/os/foo/bar|0|?---------|0|0|1337|0|0|0|0\n"
    self.assertEqual(content, expected_csv.encode("utf-8"))

  def testTimelineEntriesWithHashOnlyAreIgnoredOnBodyExport(self):
    client_id = self.SetupClient(1)
    hash_entry = jobs_pb2.Hash(sha256=b"quux")
    self.SetupFileMetadata(
        client_id, "fs/os/foo/bar", stat_entry=None, hash_entry=hash_entry
    )
    args = vfs_pb2.ApiGetVfsTimelineAsCsvArgs(
        client_id=client_id,
        file_path="fs/os/foo",
        format=vfs_pb2.ApiGetVfsTimelineAsCsvArgs.Format.BODY,
    )
    result = self.handler.Handle(args, context=self.context)

    content = b"".join(result.GenerateContent())
    self.assertEqual(content, b"")


class ApiGetVfsTimelineHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTimelineTestMixin
):

  def setUp(self):
    super().setUp()
    self.handler = vfs_plugin.ApiGetVfsTimelineHandler()
    self.client_id = self.SetupTestTimeline()

  def testRaisesOnEmptyPath(self):
    args = vfs_pb2.ApiGetVfsTimelineArgs(client_id=self.client_id, file_path="")
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesOnRootPath(self):
    args = vfs_pb2.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path="/"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  def testRaisesIfFirstComponentNotInAllowlist(self):
    args = vfs_pb2.ApiGetVfsTimelineArgs(
        client_id=self.client_id, file_path="/analysis"
    )
    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)


class ApiGetVfsFilesArchiveHandlerTest(
    api_test_lib.ApiCallHandlerTest, VfsTestMixin
):
  """Tests for ApiGetVfsFileArchiveHandler."""

  def setUp(self):
    super().setUp()

    self.handler = vfs_plugin.ApiGetVfsFilesArchiveHandler()
    self.client_id = self.SetupClient(0)

    self.CreateFileVersions(self.client_id, "fs/os/c/Downloads/a.txt")
    self.CreateFileVersions(self.client_id, "fs/os/c/b.txt")

  def testGeneratesZipArchiveWhenPathIsNotPassed(self):
    archive_path1 = "vfs_C_1000000000000000/fs/os/c/Downloads/a.txt"
    archive_path2 = "vfs_C_1000000000000000/fs/os/c/b.txt"

    result = self.handler.Handle(
        vfs_pb2.ApiGetVfsFilesArchiveArgs(client_id=self.client_id),
        context=self.context,
    )

    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    self.assertEqual(
        set(zip_fd.namelist()), set([archive_path1, archive_path2])
    )

    for path in [archive_path1, archive_path2]:
      contents = zip_fd.read(path)
      self.assertEqual(contents, b"Goodbye World")

  def testFiltersArchivedFilesByPath(self):
    archive_path = (
        "vfs_C_1000000000000000_fs_os_c_Downloads/fs/os/c/Downloads/a.txt"
    )

    result = self.handler.Handle(
        vfs_pb2.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, file_path="fs/os/c/Downloads"
        ),
        context=self.context,
    )

    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    self.assertEqual(zip_fd.namelist(), [archive_path])

    contents = zip_fd.read(archive_path)
    self.assertEqual(contents, b"Goodbye World")

  def testNonExistentPathRaises(self):
    result = self.handler.Handle(
        vfs_pb2.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id, file_path="fs/os/blah/blah"
        ),
        context=self.context,
    )

    with self.assertRaises(db.UnknownPathError):
      out_fd = io.BytesIO()
      for chunk in result.GenerateContent():
        out_fd.write(chunk)

  def testInvalidPathTriggersException(self):
    with self.assertRaises(ValueError):
      self.handler.Handle(
          vfs_pb2.ApiGetVfsFilesArchiveArgs(
              client_id=self.client_id, file_path="invalid-prefix/path"
          ),
          context=self.context,
      )

  def testHandlerRespectsTimestamp(self):
    archive_path1 = "vfs_C_1000000000000000/fs/os/c/Downloads/a.txt"
    archive_path2 = "vfs_C_1000000000000000/fs/os/c/b.txt"

    result = self.handler.Handle(
        vfs_pb2.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id,
            timestamp=self.time_2.AsMicrosecondsSinceEpoch(),
        ),
        context=self.context,
    )
    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)
    zip_fd = zipfile.ZipFile(out_fd, "r")

    self.assertCountEqual(zip_fd.namelist(), [archive_path1, archive_path2])
    self.assertEqual(zip_fd.read(archive_path1), b"Goodbye World")
    self.assertEqual(zip_fd.read(archive_path2), b"Goodbye World")

    result = self.handler.Handle(
        vfs_pb2.ApiGetVfsFilesArchiveArgs(
            client_id=self.client_id,
            timestamp=self.time_1.AsMicrosecondsSinceEpoch(),
        ),
        context=self.context,
    )
    out_fd = io.BytesIO()
    for chunk in result.GenerateContent():
      out_fd.write(chunk)
    zip_fd = zipfile.ZipFile(out_fd, "r")

    self.assertCountEqual(zip_fd.namelist(), [archive_path1, archive_path2])
    self.assertEqual(zip_fd.read(archive_path1), b"Hello World")
    self.assertEqual(zip_fd.read(archive_path2), b"Hello World")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
