#!/usr/bin/env python
"""Test the filesystem related flows."""

import io
import os
import stat
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_responses
from grr_response_server import notification
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
# TODO(user): break the dependency cycle described in filesystem.py and
# and remove this import.
# pylint: disable=unused-import
from grr_response_server.flows.general import collectors
# pylint: enable=unused-import
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import mig_filesystem
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib
from grr_response_proto.rrg import fs_pb2 as rrg_fs_pb2
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_file_metadata_pb2 as rrg_get_file_metadata_pb2


class TestFilesystem(flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testListDirectoryOnFile(self):
    """OS ListDirectory on a file will raise."""
    client_mock = action_mocks.ListDirectoryClientMock()

    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS,
    )

    # Make sure the flow raises.
    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.StartAndRunFlow(
            filesystem.ListDirectory,
            client_mock,
            client_id=self.client_id,
            flow_args=filesystem.ListDirectoryArgs(
                pathspec=pb,
            ),
            creator=self.test_username,
        )

  def testListDirectory(self):
    """Test that the ListDirectory flow works."""
    client_mock = action_mocks.ListDirectoryClientMock()
    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS,
    )
    pb.Append(path="test directory", pathtype=rdf_paths.PathSpec.PathType.TSK)

    with mock.patch.object(notification, "Notify") as mock_notify:
      # Change the username so we get a notification about the flow termination.
      flow_test_lib.StartAndRunFlow(
          filesystem.ListDirectory,
          client_mock,
          client_id=self.client_id,
          flow_args=filesystem.ListDirectoryArgs(
              pathspec=pb,
          ),
          creator="User",
      )
      self.assertEqual(mock_notify.call_count, 1)
      args = list(mock_notify.mock_calls[0])[1]
      self.assertEqual(args[0], "User")
      com = rdf_objects.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED
      self.assertEqual(args[1], com)
      self.assertIn(pb.path, args[2])

    children = self._ListTestChildPathInfos(["test_img.dd"])
    self.assertLen(children, 1)
    self.assertEqual(children[0].components[-1], "Test Directory")

  def testListDirectoryOnNonexistentDir(self):
    """Test that the ListDirectory flow works."""
    client_mock = action_mocks.ListDirectoryClientMock()
    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS,
    )
    pb.Append(path="doesnotexist", pathtype=rdf_paths.PathSpec.PathType.TSK)

    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.StartAndRunFlow(
            filesystem.ListDirectory,
            client_mock,
            client_id=self.client_id,
            flow_args=filesystem.ListDirectoryArgs(
                pathspec=pb,
            ),
            creator=self.test_username,
        )

  def _ListTestChildPathInfos(
      self,
      path_components,
      path_type=rdf_objects.PathInfo.PathType.TSK,
  ):
    components = self.base_path.strip("/").split("/") + path_components
    return data_store.REL_DB.ListChildPathInfos(
        self.client_id, path_type, components
    )

  def testUnicodeListDirectory(self):
    """Test that the ListDirectory flow works on unicode directories."""

    client_mock = action_mocks.ListDirectoryClientMock()

    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS,
    )
    filename = "入乡随俗 海外春节别样过法"

    pb.Append(path=filename, pathtype=rdf_paths.PathSpec.PathType.TSK)

    flow_test_lib.StartAndRunFlow(
        filesystem.ListDirectory,
        client_mock,
        client_id=self.client_id,
        flow_args=filesystem.ListDirectoryArgs(
            pathspec=pb,
        ),
        creator=self.test_username,
    )

    # Check the output file is created
    components = ["test_img.dd", filename]
    children = self._ListTestChildPathInfos(components)
    self.assertLen(children, 1)
    filename = children[0].components[-1]

    self.assertEqual(filename, "入乡随俗.txt")

  def testRecursiveListDirectory(self):
    """Test that RecursiveListDirectory lists files only up to max depth."""
    client_mock = action_mocks.ListDirectoryClientMock()

    dir_components = ["dir1", "dir2", "dir3", "dir4"]

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      pathspec = rdf_paths.PathSpec(
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      flow_id = flow_test_lib.StartAndRunFlow(
          filesystem.RecursiveListDirectory,
          client_mock,
          client_id=self.client_id,
          flow_args=filesystem.RecursiveListDirectoryArgs(
              pathspec=pathspec,
              max_depth=2,
          ),
          creator=self.test_username,
      )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 2)

    dirs = [_.pathspec.Basename() for _ in results]
    self.assertCountEqual(dirs, ["dir1", "dir2"])

  def testRecursiveListDirectoryTrivial(self):
    """Test that RecursiveListDirectory lists files only up to max depth."""
    client_mock = action_mocks.ListDirectoryClientMock()

    dir_components = ["dir1", "dir2"]

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      pathspec = rdf_paths.PathSpec(
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      flow_id = flow_test_lib.StartAndRunFlow(
          filesystem.RecursiveListDirectory,
          client_mock,
          client_id=self.client_id,
          flow_args=filesystem.RecursiveListDirectoryArgs(
              pathspec=pathspec,
              max_depth=1,
          ),
          creator=self.test_username,
      )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].pathspec.Basename(), "dir1")

  def testRecursiveListDirectoryDeep(self):
    """Test that RecursiveListDirectory lists files only up to max depth."""
    client_mock = action_mocks.ListDirectoryClientMock()

    dir_components = ["dir1", "dir2", "dir3", "dir4", "dir5"]

    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dirpath:
      os.makedirs(os.path.join(temp_dirpath, *dir_components))

      pathspec = rdf_paths.PathSpec(
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS
      )

      flow_id = flow_test_lib.StartAndRunFlow(
          filesystem.RecursiveListDirectory,
          client_mock,
          client_id=self.client_id,
          flow_args=filesystem.RecursiveListDirectoryArgs(
              pathspec=pathspec,
              max_depth=3,
          ),
          creator=self.test_username,
      )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 3)

    dirs = [_.pathspec.Basename() for _ in results]
    self.assertCountEqual(dirs, ["dir1", "dir2", "dir3"])

  def testDownloadDirectoryUnicode(self):
    """Test a FileFinder flow with depth=1."""
    with vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.ClientVFSHandlerFixture
    ):
      # Mock the client actions FileFinder uses.
      client_mock = action_mocks.FileFinderClientMock()

      flow_test_lib.StartAndRunFlow(
          file_finder.FileFinder,
          client_mock,
          client_id=self.client_id,
          flow_args=rdf_file_finder.FileFinderArgs(
              paths=["/c/Downloads/*"],
              action=rdf_file_finder.FileFinderAction.Download(),
          ),
          creator=self.test_username,
      )

      # There should be 6 children:
      expected_filenames = [
          "a.txt",
          "b.txt",
          "c.txt",
          "d.txt",
          "sub1",
          "中国新闻网新闻中.txt",
      ]

      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id, rdf_objects.PathInfo.PathType.OS, ["c", "Downloads"]
      )
      filenames = [child.components[-1] for child in children]
      self.assertCountEqual(filenames, expected_filenames)

  def _SetupTestDir(self, directory):
    base = utils.JoinPath(self.temp_dir, directory)
    os.makedirs(base)
    with io.open(utils.JoinPath(base, "a.txt"), "wb") as fd:
      fd.write(b"Hello World!\n")
    with io.open(utils.JoinPath(base, "b.txt"), "wb") as fd:
      pass
    with io.open(utils.JoinPath(base, "c.txt"), "wb") as fd:
      pass
    with io.open(utils.JoinPath(base, "d.txt"), "wb") as fd:
      pass

    sub = utils.JoinPath(base, "sub1")
    os.makedirs(sub)
    with io.open(utils.JoinPath(sub, "a.txt"), "wb") as fd:
      fd.write(b"Hello World!\n")
    with io.open(utils.JoinPath(sub, "b.txt"), "wb") as fd:
      pass
    with io.open(utils.JoinPath(sub, "c.txt"), "wb") as fd:
      pass

    return base

  def testDownloadDirectory(self):
    """Test a FileFinder flow with depth=1."""
    # Mock the client actions FileFinder uses.
    client_mock = action_mocks.FileFinderClientMock()

    test_dir = self._SetupTestDir("testDownloadDirectory")

    flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[test_dir + "/*"],
            action=rdf_file_finder.FileFinderAction.Download(),
        ),
        creator=self.test_username,
    )

    # There should be 5 children:
    expected_filenames = ["a.txt", "b.txt", "c.txt", "d.txt", "sub1"]

    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id,
        rdf_objects.PathInfo.PathType.OS,
        test_dir.strip("/").split("/"),
    )

    filenames = [child.components[-1] for child in children]
    self.assertCountEqual(filenames, expected_filenames)
    fd = file_store.OpenFile(
        db.ClientPath.FromPathInfo(self.client_id, children[0])
    )
    self.assertEqual(fd.read(), b"Hello World!\n")

  def testDownloadDirectorySub(self):
    """Test a FileFinder flow with depth=5."""
    # Mock the client actions FileFinder uses.
    client_mock = action_mocks.FileFinderClientMock()

    test_dir = self._SetupTestDir("testDownloadDirectorySub")

    flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        client_mock,
        client_id=self.client_id,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[test_dir + "/**5"],
            action=rdf_file_finder.FileFinderAction.Download(),
        ),
        creator=self.test_username,
    )

    expected_filenames = ["a.txt", "b.txt", "c.txt", "d.txt", "sub1"]
    expected_filenames_sub = ["a.txt", "b.txt", "c.txt"]

    components = test_dir.strip("/").split("/")
    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id, rdf_objects.PathInfo.PathType.OS, components
    )
    filenames = [child.components[-1] for child in children]
    self.assertCountEqual(filenames, expected_filenames)

    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id, rdf_objects.PathInfo.PathType.OS, components + ["sub1"]
    )
    filenames = [child.components[-1] for child in children]
    self.assertCountEqual(filenames, expected_filenames_sub)

  def testListingRegistryDirectoryDoesNotYieldMtimes(self):
    with vfs_test_lib.RegistryVFSStubber():

      client_id = self.SetupClient(0)
      pb = rdf_paths.PathSpec(
          path="/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest",
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
      )

      client_mock = action_mocks.ListDirectoryClientMock()

      flow_test_lib.StartAndRunFlow(
          filesystem.ListDirectory,
          client_mock,
          client_id=client_id,
          flow_args=filesystem.ListDirectoryArgs(
              pathspec=pb,
          ),
          creator=self.test_username,
      )

      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id,
          rdf_objects.PathInfo.PathType.REGISTRY,
          ["HKEY_LOCAL_MACHINE", "SOFTWARE", "ListingTest"],
      )
      self.assertLen(children, 2)
      for child in children:
        self.assertFalse(child.stat_entry.st_mtime)

  def testNotificationWhenListingRegistry(self):
    # Change the username so notifications get written.
    username = "notification_test"
    acl_test_lib.CreateUser(username)

    with vfs_test_lib.RegistryVFSStubber():
      client_id = self.SetupClient(0)
      pb = rdf_paths.PathSpec(
          path="/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest",
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
      )

      client_mock = action_mocks.ListDirectoryClientMock()

      flow_test_lib.StartAndRunFlow(
          filesystem.ListDirectory,
          client_mock,
          client_id=client_id,
          flow_args=filesystem.ListDirectoryArgs(
              pathspec=pb,
          ),
          creator=username,
      )

    notifications = data_store.REL_DB.ReadUserNotifications(username)
    self.assertLen(notifications, 1)
    n = mig_objects.ToRDFUserNotification(notifications[0])
    self.assertEqual(
        n.reference.vfs_file.path_type, rdf_objects.PathInfo.PathType.REGISTRY
    )
    self.assertEqual(
        n.reference.vfs_file.path_components,
        ["HKEY_LOCAL_MACHINE", "SOFTWARE", "ListingTest"],
    )


class ListDirectoryTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testHandleRRGGetFileMetadata(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )
    flow_id = db_test_utils.InitializeFlow(rel_db, client_id)

    args = filesystem.ListDirectoryArgs()
    args.pathspec.path = "/foo/bar/baz"

    result = rrg_get_file_metadata_pb2.Result()
    result.path.raw_bytes = "/foo/bar/baz".encode("utf-8")
    result.metadata.type = rrg_fs_pb2.FileMetadata.Type.DIR
    result.metadata.size = 1337
    result.metadata.access_time.seconds = 1001
    result.metadata.modification_time.seconds = 1002
    result.metadata.creation_time.seconds = 1003

    result_response = rdf_flow_objects.FlowResponse()
    result_response.any_payload = rdf_structs.AnyValue.PackProto2(result)

    status_response = rdf_flow_objects.FlowStatus()
    status_response.status = rdf_flow_objects.FlowStatus.Status.OK

    responses = flow_responses.Responses.FromResponsesProto2Any([
        result_response,
        status_response,
    ])

    rdf_flow = rdf_flow_objects.Flow()
    rdf_flow.client_id = client_id
    rdf_flow.flow_id = flow_id
    rdf_flow.flow_class_name = filesystem.ListDirectory.__name__
    rdf_flow.args = args

    flow = filesystem.ListDirectory(rdf_flow)
    flow.Start()
    flow.HandleRRGGetFileMetadata(responses)

    self.assertEqual(flow.store.stat_entry.pathspec.path, "/foo/bar/baz")
    self.assertEqual(flow.store.stat_entry.st_mode, stat.S_IFDIR)
    self.assertEqual(flow.store.stat_entry.st_size, 1337)
    self.assertEqual(flow.store.stat_entry.st_atime, 1001)
    self.assertEqual(flow.store.stat_entry.st_mtime, 1002)
    self.assertEqual(flow.store.stat_entry.st_btime, 1003)
    self.assertEqual(flow.store.urn, f"aff4:/{client_id}/fs/os/foo/bar/baz")

  @db_test_lib.WithDatabase
  def testRRG_Empty(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertEmpty(flow_results)

  @db_test_lib.WithDatabase
  def testRRG_Dir(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/bar": b"",
            "/foo/baz": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertIn("/foo/bar", results_by_path)
    self.assertIn("/foo/baz", results_by_path)

    self.assertTrue(stat.S_ISREG(results_by_path["/foo/bar"].st_mode))
    self.assertTrue(stat.S_ISDIR(results_by_path["/foo/baz"].st_mode))

    path_infos = rel_db.ListChildPathInfos(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("foo",),
    )
    self.assertLen(path_infos, 2)

    path_infos_by_components = {}
    for path_info in path_infos:
      path_infos_by_components[tuple(path_info.components)] = path_info

    self.assertIn(("foo", "bar"), path_infos_by_components)
    self.assertIn(("foo", "baz"), path_infos_by_components)

  @db_test_lib.WithDatabase
  def testRRG_Dir_Windows(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "X:\\Foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "X:\\Foo\\Bar": b"",
            "X:\\Foo\\Baz": {},
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertIn("X:/Foo/Bar", results_by_path)
    self.assertIn("X:/Foo/Baz", results_by_path)

    self.assertTrue(stat.S_ISREG(results_by_path["X:/Foo/Bar"].st_mode))
    self.assertTrue(stat.S_ISDIR(results_by_path["X:/Foo/Baz"].st_mode))

    path_infos = rel_db.ListChildPathInfos(
        client_id=client_id,
        path_type=objects_pb2.PathInfo.PathType.OS,
        components=("X:", "Foo"),
    )
    self.assertLen(path_infos, 2)

    path_infos_by_components = {}
    for path_info in path_infos:
      path_infos_by_components[tuple(path_info.components)] = path_info

    self.assertIn(("X:", "Foo", "Bar"), path_infos_by_components)
    self.assertIn(("X:", "Foo", "Baz"), path_infos_by_components)

  @db_test_lib.WithDatabase
  def testRRG_File(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertStartsWith(flow_obj.error_message, "Unexpected file type")

  @db_test_lib.WithDatabase
  def testRRG_Symlink_Absolute(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": "/quux",
            "/quux/bar": b"",
            "/quux/baz": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertIn("/quux/bar", results_by_path)
    self.assertIn("/quux/baz", results_by_path)

    self.assertTrue(stat.S_ISREG(results_by_path["/quux/bar"].st_mode))
    self.assertTrue(stat.S_ISREG(results_by_path["/quux/baz"].st_mode))

  @db_test_lib.WithDatabase
  def testRRG_Symlink_Relative(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo/norf"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo/norf": "../quux",
            "/quux/bar": b"",
            "/quux/baz": b"",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 2)

    results_by_path = {}
    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertIn("/quux/bar", results_by_path)
    self.assertIn("/quux/baz", results_by_path)

    self.assertTrue(stat.S_ISREG(results_by_path["/quux/bar"].st_mode))
    self.assertTrue(stat.S_ISREG(results_by_path["/quux/baz"].st_mode))

  @db_test_lib.WithDatabase
  def testRRG_Symlink_DepthLimit(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.LINUX,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.path = "/foo"
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakePosixFileHandlers({
            "/foo": "/foo",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertStartsWith(flow_obj.error_message, "Symlink depth reached")

  @db_test_lib.WithDatabase
  def testHandleRRG_Windows_LeadingSlash(self, rel_db: db.Database):
    client_id = db_test_utils.InitializeRRGClient(
        rel_db,
        os_type=rrg_os_pb2.WINDOWS,
    )

    args = flows_pb2.ListDirectoryArgs()
    args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.pathspec.path = "/C:/Users"

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=filesystem.ListDirectory,
        flow_args=mig_filesystem.ToRDFListDirectoryArgs(args),
        handlers=rrg_test_lib.FakeWindowsFileHandlers({
            "C:\\Users\\Foo Bar\\desktop.ini": b"Lorem ipsum.",
            "C:\\Users\\Quux\\desktop.ini": b"Lorem ipsum.",
        }),
    )

    flow_obj = rel_db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

    flow_results = rel_db.ReadFlowResults(client_id, flow_id, offset=0, count=8)
    self.assertLen(flow_results, 2)

    results_by_path: dict[str, jobs_pb2.StatEntry] = {}

    for flow_result in flow_results:
      result = jobs_pb2.StatEntry()
      self.assertTrue(flow_result.payload.Unpack(result))

      results_by_path[result.pathspec.path] = result

    self.assertIn("C:/Users/Foo Bar", results_by_path)
    self.assertIn("C:/Users/Quux", results_by_path)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
