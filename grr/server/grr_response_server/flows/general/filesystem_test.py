#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the filesystem related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import io
import os
import platform

from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import windows_registry_parser as winreg_parser
from grr_response_core.lib.parsers import wmi_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import notification
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard as aff4_standard
# TODO(user): break the dependency cycle described in filesystem.py and
# and remove this import.
# pylint: disable=unused-import
from grr_response_server.flows.general import collectors
# pylint: enable=unused-import
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestSparseImage(flow_test_lib.FlowTestsBaseclass):
  """Tests the sparse image related flows."""

  def CreateNewSparseImage(self):
    client_id = self.SetupClient(0)

    path = os.path.join(self.base_path, "test_img.dd")

    urn = client_id.Add("fs/os").Add(path)

    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)

    with aff4.FACTORY.Create(
        urn, aff4_standard.AFF4SparseImage, mode="rw", token=self.token) as fd:

      # Give the new object a pathspec.
      fd.Set(fd.Schema.PATHSPEC, pathspec)

    return urn

  def ReadFromSparseImage(self, client_id, length, offset):

    urn = self.CreateNewSparseImage()

    self.client_mock = action_mocks.FileFinderClientMock()

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.FetchBufferForSparseImage),
        self.client_mock,
        client_id=client_id,
        token=self.token,
        file_urn=urn,
        length=length,
        offset=offset)

    # Reopen the object so we can read the freshest version of the size
    # attribute.
    return aff4.FACTORY.Open(urn, token=self.token)

  def testFetchBufferForSparseImageReadAlignedToChunks(self):
    client_id = self.SetupClient(0)
    # From a 2MiB offset, read 5MiB.
    length = 1024 * 1024 * 5
    offset = 1024 * 1024 * 2
    fd = self.ReadFromSparseImage(client_id, length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # We should have increased in size by the amount of data we requested
    # exactly, since we already aligned to chunks.
    self.assertEqual(size_after, length)

    # Open the actual file on disk without using AFF4 and hash the data we
    # expect to be reading.
    with io.open(os.path.join(self.base_path, "test_img.dd"), "rb") as test_fd:
      test_fd.seek(offset)
      disk_file_contents = test_fd.read(length)
      expected_hash = hashlib.sha256(disk_file_contents).digest()

    # Write the file contents to the datastore.
    fd.Flush()
    # Make sure the data we read is actually the data that was in the file.
    fd.Seek(offset)
    contents = fd.Read(length)

    # There should be no gaps.
    self.assertLen(contents, length)

    self.assertEqual(hashlib.sha256(contents).digest(), expected_hash)

  def testFetchBufferForSparseImageReadNotAlignedToChunks(self):
    client_id = self.SetupClient(0)

    # Read a non-whole number of chunks.
    # (This should be rounded up to 5Mib + 1 chunk)
    length = 1024 * 1024 * 5 + 42
    # Make sure we're not reading from exactly the beginning of a chunk.
    # (This should get rounded down to 2Mib)
    offset = 1024 * 1024 * 2 + 1

    fd = self.ReadFromSparseImage(client_id, length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # The chunksize the sparse image uses.
    chunksize = aff4_standard.AFF4SparseImage.chunksize

    # We should have rounded the 5Mib + 42 up to the nearest chunk,
    # and rounded down the + 1 on the offset.
    self.assertEqual(size_after, length + (chunksize - 42))

  def testFetchBufferForSparseImageCorrectChunksRead(self):
    client_id = self.SetupClient(0)

    length = 1
    offset = 1024 * 1024 * 10
    fd = self.ReadFromSparseImage(client_id, length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # We should have rounded up to 1 chunk size.
    self.assertEqual(size_after, fd.chunksize)

  def ReadTestImage(self, size_threshold):
    client_id = self.SetupClient(0)
    path = os.path.join(self.base_path, "test_img.dd")

    urn = rdfvalue.RDFURN(client_id.Add("fs/os").Add(path))

    pathspec = rdf_paths.PathSpec(
        path=path, pathtype=rdf_paths.PathSpec.PathType.OS)

    client_mock = action_mocks.FileFinderClientMock()

    # Get everything as an AFF4SparseImage
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.MakeNewAFF4SparseImage),
        client_mock,
        client_id=client_id,
        token=self.token,
        size_threshold=size_threshold,
        pathspec=pathspec)

    return aff4.FACTORY.Open(urn, token=self.token)

  def testReadNewAFF4SparseImage(self):

    # Smaller than the size of the file.
    fd = self.ReadTestImage(size_threshold=0)

    self.assertIsInstance(fd, aff4_standard.AFF4SparseImage)

    # The file should be empty.
    self.assertEmpty(fd.Read(10000))
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def testNewSparseImageFileNotBigEnough(self):

    # Bigger than the size of the file.
    fd = self.ReadTestImage(size_threshold=2**32)

    # We shouldn't be a sparse image in this case.
    self.assertNotIsInstance(fd, aff4_standard.AFF4SparseImage)
    self.assertIsInstance(fd, aff4.AFF4Image)
    self.assertNotEmpty(fd.Read(10000))
    self.assertGreater(fd.Get(fd.Schema.SIZE), 0)


class TestFilesystem(flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  flow_base_cls = flow.GRRFlow

  def setUp(self):
    super(TestFilesystem, self).setUp()
    self.client_id = self.SetupClient(0)

  def testListDirectoryOnFile(self):
    """OS ListDirectory on a file will raise."""
    client_mock = action_mocks.ListDirectoryClientMock()

    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)

    # Make sure the flow raises.
    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            compatibility.GetName(filesystem.ListDirectory),
            client_mock,
            client_id=self.client_id,
            pathspec=pb,
            token=self.token)

  def testListDirectory(self):
    """Test that the ListDirectory flow works."""
    client_mock = action_mocks.ListDirectoryClientMock()
    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    pb.Append(path="test directory", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Change the username so we get a notification about the flow termination.
    token = self.token.Copy()
    token.username = "User"

    with mock.patch.object(notification, "Notify") as mock_notify:
      flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.ListDirectory),
          client_mock,
          client_id=self.client_id,
          pathspec=pb,
          token=token)
      self.assertEqual(mock_notify.call_count, 1)
      args = list(mock_notify.mock_calls[0])[1]
      self.assertEqual(args[0], token.username)
      com = rdf_objects.UserNotification.Type.TYPE_VFS_LIST_DIRECTORY_COMPLETED
      self.assertEqual(args[1], com)
      self.assertIn(pb.path, args[2])

    if data_store.AFF4Enabled():
      # Check the output file is created
      output_path = self.client_id.Add("fs/tsk").Add(pb.first.path)

      fd = aff4.FACTORY.Open(
          output_path.Add("Test Directory"), token=self.token)
      children = list(fd.OpenChildren())
      self.assertLen(children, 1)
      child = children[0]

      # Check that the object is stored with the correct casing.
      self.assertEqual(child.urn.Basename(), "numbers.txt")

      # And the wrong object is not there
      self.assertRaises(
          IOError,
          aff4.FACTORY.Open,
          output_path.Add("test directory"),
          aff4_type=aff4_standard.VFSDirectory,
          token=self.token)
    else:
      children = self._ListTestChildPathInfos(["test_img.dd"])
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "Test Directory")

  def testListDirectoryOnNonexistentDir(self):
    """Test that the ListDirectory flow works."""
    client_mock = action_mocks.ListDirectoryClientMock()
    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    pb.Append(path="doesnotexist", pathtype=rdf_paths.PathSpec.PathType.TSK)

    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            compatibility.GetName(filesystem.ListDirectory),
            client_mock,
            client_id=self.client_id,
            pathspec=pb,
            token=self.token)

  def _ListTestChildPathInfos(self,
                              path_components,
                              path_type=rdf_objects.PathInfo.PathType.TSK):
    components = self.base_path.strip("/").split("/") + path_components
    return data_store.REL_DB.ListChildPathInfos(self.client_id.Basename(),
                                                path_type, components)

  def testUnicodeListDirectory(self):
    """Test that the ListDirectory flow works on unicode directories."""

    client_mock = action_mocks.ListDirectoryClientMock()

    pb = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    filename = "入乡随俗 海外春节别样过法"

    pb.Append(path=filename, pathtype=rdf_paths.PathSpec.PathType.TSK)

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.ListDirectory),
        client_mock,
        client_id=self.client_id,
        pathspec=pb,
        token=self.token)

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(pb.CollapsePath())

    if data_store.AFF4Enabled():
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.OpenChildren())
      self.assertLen(children, 1)
      child = children[0]
      filename = child.urn.Basename()
    else:
      components = ["test_img.dd", filename]
      children = self._ListTestChildPathInfos(components)
      self.assertLen(children, 1)
      filename = children[0].components[-1]

    self.assertEqual(filename, "入乡随俗.txt")

  def testGlob(self):
    """Test that glob works properly."""
    users = [
        rdf_client.User(username="test"),
        rdf_client.User(username="syslog")
    ]
    client_id = self.SetupClient(0, users=users)

    client_mock = action_mocks.GlobClientMock()

    # This glob selects all files which start with the username on this system.
    paths = [
        os.path.join(self.base_path, "%%Users.username%%*"),
        os.path.join(self.base_path, "VFSFixture/var/*/wtmp")
    ]

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=client_id,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token,
        sync=False,
        check_flow_errors=False)

    expected_files = [
        filename for filename in os.listdir(self.base_path)
        if filename.startswith("test") or filename.startswith("syslog")
    ]
    expected_files.append("VFSFixture")

    if data_store.AFF4Enabled():
      output_path = client_id.Add("fs/os").Add(self.base_path)

      fd = aff4.FACTORY.Open(output_path, token=self.token)
      found_files = [urn.Basename() for urn in fd.ListChildren()]

      self.assertCountEqual(expected_files, found_files)

      fd = aff4.FACTORY.Open(
          output_path.Add("VFSFixture/var/log"), token=self.token)
      self.assertCountEqual([urn.Basename() for urn in fd.ListChildren()],
                            ["wtmp"])
    else:
      children = self._ListTestChildPathInfos(
          [], path_type=rdf_objects.PathInfo.PathType.OS)
      found_files = [child.components[-1] for child in children]

      self.assertCountEqual(expected_files, found_files)

      children = self._ListTestChildPathInfos(
          ["VFSFixture", "var", "log"],
          path_type=rdf_objects.PathInfo.PathType.OS)
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "wtmp")

  def _RunGlob(self, paths):
    client_mock = action_mocks.GlobClientMock()
    session_id = flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=paths,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    return [st.pathspec.path for st in results]

  def testGlobWithStarStarRootPath(self):
    """Test ** expressions with root_path."""
    users = [
        rdf_client.User(username="test"),
        rdf_client.User(username="syslog")
    ]
    self.client_id = self.SetupClient(0, users=users)

    client_mock = action_mocks.GlobClientMock()

    # Glob for foo at a depth of 4.
    path = os.path.join("foo**4")
    root_path = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    root_path.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Run the flow.
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        root_path=root_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)

    if data_store.AFF4Enabled():
      children = []
      output_path = self.client_id.Add("fs/tsk").Add(
          self.base_path).Add("test_img.dd/glob_test/a/b")
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      for child in fd.ListChildren():
        children.append(child.Basename())
      # We should find some files.
      self.assertEqual(children, ["foo"])
    else:
      children = self._ListTestChildPathInfos(
          ["test_img.dd", "glob_test", "a", "b"])
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "foo")

  def _MakeTestDirs(self):
    fourth_level_dir = utils.JoinPath(self.temp_dir, "1/2/3/4")
    os.makedirs(fourth_level_dir)

    top_level_path = self.temp_dir
    io.open(utils.JoinPath(top_level_path, "bar"), "wb").close()
    for level in range(1, 5):
      top_level_path = utils.JoinPath(top_level_path, level)
      for filename in ("foo", "fOo", "bar"):
        file_path = utils.JoinPath(top_level_path, filename + str(level))
        io.open(file_path, "wb").close()
        self.assertTrue(os.path.exists(file_path))

  def testGlobWithStarStar(self):
    """Test that ** expressions mean recursion."""

    self._MakeTestDirs()

    # Test filename and directory with spaces
    os.makedirs(utils.JoinPath(self.temp_dir, "1/2 space"))
    path_spaces = utils.JoinPath(self.temp_dir, "1/2 space/foo something")
    io.open(path_spaces, "wb").close()
    self.assertTrue(os.path.exists(path_spaces))

    # Get the foos using default of 3 directory levels.
    paths = [os.path.join(self.temp_dir, "1/**/foo*")]

    # Handle filesystem case insensitivity
    expected_results = [
        "1/2/3/4/foo4", "/1/2/3/foo3", "1/2/foo2", "1/2 space/foo something"
    ]
    if platform.system() == "Linux":
      expected_results = [
          "1/2/3/4/fOo4", "1/2/3/4/foo4", "/1/2/3/fOo3", "/1/2/3/foo3",
          "1/2/fOo2", "1/2/foo2", "1/2 space/foo something"
      ]

    expected_results = [
        utils.JoinPath(self.temp_dir, x) for x in expected_results
    ]

    results = self._RunGlob(paths)
    self.assertCountEqual(results, expected_results)

    # Get the files 2 levels down only.
    paths = [os.path.join(self.temp_dir, "1/", "**2/foo*")]

    # Handle filesystem case insensitivity
    expected_results = ["1/2/3/foo3", "/1/2/foo2", "1/2 space/foo something"]
    if platform.system() == "Linux":
      expected_results = [
          "1/2/3/foo3", "1/2/3/fOo3", "/1/2/fOo2", "/1/2/foo2",
          "1/2 space/foo something"
      ]

    expected_results = [
        utils.JoinPath(self.temp_dir, x) for x in expected_results
    ]

    results = self._RunGlob(paths)
    self.assertCountEqual(results, expected_results)

    # Get all of the bars.
    paths = [os.path.join(self.temp_dir, "**10bar*")]
    expected_results = [
        "bar", "1/bar1", "/1/2/bar2", "/1/2/3/bar3", "/1/2/3/4/bar4"
    ]
    expected_results = [
        utils.JoinPath(self.temp_dir, x) for x in expected_results
    ]
    results = self._RunGlob(paths)
    self.assertCountEqual(results, expected_results)

  def testGlobWithTwoStars(self):
    self._MakeTestDirs()
    paths = [os.path.join(self.temp_dir, "1/", "*/*/foo*")]
    # Handle filesystem case insensitivity
    expected_results = ["1/2/3/foo3"]
    if platform.system() == "Linux":
      expected_results = ["1/2/3/foo3", "1/2/3/fOo3"]

    expected_results = [
        utils.JoinPath(self.temp_dir, x) for x in expected_results
    ]

    results = self._RunGlob(paths)
    self.assertCountEqual(results, expected_results)

  def testGlobWithMultiplePaths(self):
    self._MakeTestDirs()
    paths = [
        os.path.join(self.temp_dir, "*/*/foo*"),
        os.path.join(self.temp_dir, "notthere"),
        os.path.join(self.temp_dir, "*/notthere"),
        os.path.join(self.temp_dir, "*/foo*")
    ]

    # Handle filesystem case sensitivity
    expected_results = ["1/foo1", "/1/2/foo2"]
    if platform.system() == "Linux":
      expected_results = ["1/foo1", "1/fOo1", "/1/2/fOo2", "/1/2/foo2"]
    results = self._RunGlob(paths)
    self.assertCountEqual(
        results, [utils.JoinPath(self.temp_dir, x) for x in expected_results])

  def testGlobWithInvalidStarStar(self):
    client_mock = action_mocks.GlobClientMock()

    # This glob is invalid since it uses 2 ** expressions..
    paths = [os.path.join(self.base_path, "test_img.dd", "**", "**", "foo")]

    # Make sure the flow raises.
    with self.assertRaises(ValueError):
      flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.Glob),
          client_mock,
          client_id=self.client_id,
          paths=paths,
          pathtype=rdf_paths.PathSpec.PathType.OS,
          token=self.token)

  def testGlobWithWildcardsInsideTSKFile(self):
    client_mock = action_mocks.GlobClientMock()

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join("*", "a", "b", "*")
    root_path = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    root_path.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Run the flow.
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        root_path=root_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)

    output_path = self.client_id.Add("fs/tsk").Add(
        os.path.join(self.base_path, "test_img.dd", "glob_test", "a", "b"))

    if data_store.AFF4Enabled():
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.ListChildren())
      self.assertLen(children, 1)
      self.assertEqual(children[0].Basename(), "foo")
    else:
      children = self._ListTestChildPathInfos(
          ["test_img.dd", "glob_test", "a", "b"])
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "foo")

  def testGlobWithWildcardsInsideTSKFileCaseInsensitive(self):
    client_mock = action_mocks.GlobClientMock()

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join("*", "a", "b", "FOO*")
    root_path = rdf_paths.PathSpec(
        path=os.path.join(self.base_path, "test_IMG.dd"),
        pathtype=rdf_paths.PathSpec.PathType.OS)
    root_path.Append(path="/", pathtype=rdf_paths.PathSpec.PathType.TSK)

    # Run the flow.
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        root_path=root_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)

    output_path = self.client_id.Add("fs/tsk").Add(
        os.path.join(self.base_path, "test_img.dd", "glob_test", "a", "b"))

    if data_store.AFF4Enabled():
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.ListChildren())
      self.assertLen(children, 1)
      self.assertEqual(children[0].Basename(), "foo")
    else:
      children = self._ListTestChildPathInfos(
          ["test_img.dd", "glob_test", "a", "b"])
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "foo")

  def testGlobWildcardsAndTSK(self):
    client_mock = action_mocks.GlobClientMock()

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join(self.base_path, "test_IMG.dd", "glob_test", "a", "b",
                        "FOO*")
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)

    if data_store.AFF4Enabled():
      output_path = self.client_id.Add("fs/tsk").Add(
          os.path.join(self.base_path, "test_img.dd", "glob_test", "a", "b"))

      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.ListChildren())

      self.assertLen(children, 1)
      self.assertEqual(children[0].Basename(), "foo")
    else:
      children = self._ListTestChildPathInfos(
          ["test_img.dd", "glob_test", "a", "b"])
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "foo")

  def testGlobWildcardOnImage(self):
    client_mock = action_mocks.GlobClientMock()
    # Specifying a wildcard for the image will not open it.
    path = os.path.join(self.base_path, "*.dd", "glob_test", "a", "b", "FOO*")
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token)

    if data_store.AFF4Enabled():
      output_path = self.client_id.Add("fs/tsk").Add(
          os.path.join(self.base_path, "test_img.dd", "glob_test", "a", "b"))
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(fd.ListChildren())
      self.assertEmpty(children)
    else:
      children = self._ListTestChildPathInfos(
          ["test_img.dd", "glob_test", "a", "b"])
      self.assertEmpty(children)

  def testGlobDirectory(self):
    """Test that glob expands directories."""
    users = [
        rdf_client.User(username="test", appdata="test_data/index.dat"),
        rdf_client.User(username="test2", appdata="test_data/History"),
        rdf_client.User(username="test3", appdata="%%PATH%%"),
    ]
    self.client_id = self.SetupClient(0, users=users)

    client_mock = action_mocks.GlobClientMock()

    # This glob selects all files which start with the username on this system.
    path = os.path.join(os.path.dirname(self.base_path), "%%users.appdata%%")

    # Run the flow.
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        token=self.token)

    if data_store.AFF4Enabled():
      path = self.client_id.Add("fs/os").Add(self.base_path).Add("index.dat")

      aff4.FACTORY.Open(path, aff4_type=aff4_grr.VFSFile, token=self.token)
    else:
      children = self._ListTestChildPathInfos(
          [], path_type=rdf_objects.PathInfo.PathType.OS)
      self.assertLen(children, 1)
      self.assertEqual(children[0].components[-1], "index.dat")

  def testGlobGrouping(self):
    """Tests the glob grouping functionality."""

    pattern = "test_data/{ntfs_img.dd,*log,*.exe}"

    client_mock = action_mocks.GlobClientMock()
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.Glob),
        client_mock,
        client_id=self.client_id,
        paths=[path],
        token=self.token)

    if data_store.AFF4Enabled():
      path = self.client_id.Add("fs/os").Add(self.base_path)
      files_found = [urn.Basename() for urn in aff4.FACTORY.ListChildren(path)]
    else:
      children = self._ListTestChildPathInfos(
          [], path_type=rdf_objects.PathInfo.PathType.OS)
      files_found = [child.components[-1] for child in children]

    self.assertCountEqual(files_found, [
        "ntfs_img.dd",
        "apache_false_log",
        "apache_log",
        "syslog",
        "hello.exe",
    ])

  def testIllegalGlob(self):
    """Test that illegal globs raise."""

    paths = ["Test/%%Weird_illegal_attribute%%"]

    # Run the flow - we expect an AttributeError error to be raised from the
    # flow since Weird_illegal_attribute is not a valid client attribute.
    self.assertRaises(
        artifact_utils.KnowledgeBaseInterpolationError,
        flow_test_lib.StartFlow,
        filesystem.Glob,
        paths=paths,
        client_id=self.client_id)

  def testIllegalGlobAsync(self):
    # When running the flow asynchronously, we will not receive any errors from
    # the Start method, but the flow should still fail.
    paths = ["Test/%%Weird_illegal_attribute%%"]
    client_mock = action_mocks.GlobClientMock()

    # Run the flow.
    session_id = None

    # This should not raise here since the flow is run asynchronously.
    with test_lib.SuppressLogs():
      session_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.Glob),
          client_mock,
          client_id=self.client_id,
          check_flow_errors=False,
          paths=paths,
          pathtype=rdf_paths.PathSpec.PathType.OS,
          token=self.token,
          sync=False)

    fd = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertIn("KnowledgeBaseInterpolationError", fd.context.backtrace)
    self.assertEqual("ERROR", str(fd.context.state))

  def testGlobRoundtrips(self):
    """Tests that glob doesn't use too many client round trips."""

    for pattern, num_find, num_stat, duplicated_ok in [
        ("test_data/test_artifact.json", 0, 1, False),
        ("test_data/test_*", 1, 0, False),
        ("test_da*/test_artifact.json", 1, 1, False),
        ("test_da*/test_*", 2, 0, False),
        ("test_da*/test_{artifact,artifacts}.json", 1, 2, True),
        ("test_data/test_{artifact,artifacts}.json", 0, 2, False),
        ("test_data/{ntfs_img.dd,*.log,*.raw}", 1, 1, False),
        ("test_data/{*.log,*.raw}", 1, 0, False),
        ("test_data/a/**/helloc.txt", 1, None, False),
        ("test_data/a/**/hello{c,d}.txt", 1, None, True),
        ("test_data/a/**/hello*.txt", 4, None, False),
        ("test_data/a/**.txt", 1, None, False),
        ("test_data/a/**5*.txt", 1, None, False),
        ("test_data/a/**{.json,.txt}", 1, 0, False),
    ]:

      path = os.path.join(os.path.dirname(self.base_path), pattern)
      client_mock = action_mocks.GlobClientMock()

      # Run the flow.
      flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.Glob),
          client_mock,
          client_id=self.client_id,
          paths=[path],
          token=self.token)

      if num_find is not None:
        self.assertEqual(client_mock.action_counts.get("Find", 0), num_find)
      if num_stat is not None:
        self.assertEqual(
            client_mock.action_counts.get("GetFileStat", 0), num_stat)

      if not duplicated_ok:
        # Check for duplicate client calls. There might be duplicates that are
        # very cheap when we look for a wildcard (* or **) first and later in
        # the pattern for a group of files ({}).
        for method in "StatFile", "Find":
          stat_args = client_mock.recorded_args.get(method, [])
          stat_paths = [c.pathspec.CollapsePath() for c in stat_args]
          self.assertListEqual(sorted(stat_paths), sorted(set(stat_paths)))

  def _CheckCasing(self, path, filename):
    if data_store.AFF4Enabled():
      output_path = self.client_id.Add("fs/os").Add(
          os.path.join(self.base_path, path))
      fd = aff4.FACTORY.Open(output_path, token=self.token)
      filenames = [urn.Basename() for urn in fd.ListChildren()]
      self.assertIn(filename, filenames)
    else:
      path_infos = self._ListTestChildPathInfos(
          path.split("/"), path_type=rdf_objects.PathInfo.PathType.OS)
      filenames = [path_info.components[-1] for path_info in path_infos]
      self.assertIn(filename, filenames)

  def testGlobCaseCorrection(self):
    # This should get corrected to "a/b/c/helloc.txt"
    test_path = "a/B/c/helloC.txt"

    self._RunGlob([os.path.join(self.base_path, test_path)])

    self._CheckCasing("a", "b")
    self._CheckCasing("a/b/c", "helloc.txt")

  def testGlobCaseCorrectionUsingWildcards(self):
    # Make sure this also works with *s in the glob.

    # This should also get corrected to "a/b/c/helloc.txt"
    test_path = "a/*/C/*.txt"

    self._RunGlob([os.path.join(self.base_path, test_path)])

    self._CheckCasing("a", "b")
    self._CheckCasing("a/b", "c")

  def testDownloadDirectoryUnicode(self):
    """Test a FileFinder flow with depth=1."""
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS,
                                   vfs_test_lib.ClientVFSHandlerFixture):
      # Mock the client actions FileFinder uses.
      client_mock = action_mocks.FileFinderClientMock()

      flow_test_lib.TestFlowHelper(
          compatibility.GetName(file_finder.FileFinder),
          client_mock,
          client_id=self.client_id,
          paths=["/c/Downloads/*"],
          action=rdf_file_finder.FileFinderAction.Download(),
          token=self.token)

      # There should be 6 children:
      expected_filenames = [
          "a.txt", "b.txt", "c.txt", "d.txt", "sub1", "中国新闻网新闻中.txt"
      ]

      if data_store.AFF4Enabled():
        # Check if the base path was created
        output_path = self.client_id.Add("fs/os/c/Downloads")

        output_fd = aff4.FACTORY.Open(output_path, token=self.token)
        children = list(output_fd.OpenChildren())

        filenames = [child.urn.Basename() for child in children]

        self.assertCountEqual(filenames, expected_filenames)
      else:
        children = data_store.REL_DB.ListChildPathInfos(
            self.client_id.Basename(), rdf_objects.PathInfo.PathType.OS,
            ["c", "Downloads"])
        filenames = [child.components[-1] for child in children]
        self.assertCountEqual(filenames, expected_filenames)

  def _SetupTestDir(self, directory):
    base = utils.JoinPath(self.temp_dir, directory)
    os.makedirs(base)
    with io.open(utils.JoinPath(base, "a.txt"), "wb") as fd:
      fd.write("Hello World!\n")
    with io.open(utils.JoinPath(base, "b.txt"), "wb") as fd:
      pass
    with io.open(utils.JoinPath(base, "c.txt"), "wb") as fd:
      pass
    with io.open(utils.JoinPath(base, "d.txt"), "wb") as fd:
      pass

    sub = utils.JoinPath(base, "sub1")
    os.makedirs(sub)
    with io.open(utils.JoinPath(sub, "a.txt"), "wb") as fd:
      fd.write("Hello World!\n")
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

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(file_finder.FileFinder),
        client_mock,
        client_id=self.client_id,
        paths=[test_dir + "/*"],
        action=rdf_file_finder.FileFinderAction.Download(),
        token=self.token)

    # There should be 5 children:
    expected_filenames = ["a.txt", "b.txt", "c.txt", "d.txt", "sub1"]

    if data_store.AFF4Enabled():
      output_path = self.client_id.Add("fs/os").Add(test_dir)

      output_fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(output_fd.OpenChildren())

      filenames = [child.urn.Basename() for child in children]

      self.assertCountEqual(filenames, expected_filenames)

      fd = aff4.FACTORY.Open(output_path.Add("a.txt"))
      self.assertEqual(fd.read(), "Hello World!\n")
    else:
      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id.Basename(), rdf_objects.PathInfo.PathType.OS,
          test_dir.strip("/").split("/"))

      filenames = [child.components[-1] for child in children]
      self.assertCountEqual(filenames, expected_filenames)
      fd = file_store.OpenFile(
          db.ClientPath.FromPathInfo(self.client_id.Basename(), children[0]))
      self.assertEqual(fd.read(), "Hello World!\n")

  def testDownloadDirectorySub(self):
    """Test a FileFinder flow with depth=5."""
    # Mock the client actions FileFinder uses.
    client_mock = action_mocks.FileFinderClientMock()

    test_dir = self._SetupTestDir("testDownloadDirectorySub")

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(file_finder.FileFinder),
        client_mock,
        client_id=self.client_id,
        paths=[test_dir + "/**5"],
        action=rdf_file_finder.FileFinderAction.Download(),
        token=self.token)

    expected_filenames = ["a.txt", "b.txt", "c.txt", "d.txt", "sub1"]
    expected_filenames_sub = ["a.txt", "b.txt", "c.txt"]

    if data_store.AFF4Enabled():
      output_path = self.client_id.Add("fs/os").Add(test_dir)

      output_fd = aff4.FACTORY.Open(output_path, token=self.token)
      children = list(output_fd.OpenChildren())

      filenames = [child.urn.Basename() for child in children]

      self.assertCountEqual(filenames, expected_filenames)

      output_fd = aff4.FACTORY.Open(output_path.Add("sub1"), token=self.token)
      children = list(output_fd.OpenChildren())

      filenames = [child.urn.Basename() for child in children]

      self.assertCountEqual(filenames, expected_filenames_sub)

    else:
      components = test_dir.strip("/").split("/")
      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id.Basename(), rdf_objects.PathInfo.PathType.OS,
          components)
      filenames = [child.components[-1] for child in children]
      self.assertCountEqual(filenames, expected_filenames)

      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id.Basename(), rdf_objects.PathInfo.PathType.OS,
          components + ["sub1"])
      filenames = [child.components[-1] for child in children]
      self.assertCountEqual(filenames, expected_filenames_sub)

  def testDiskVolumeInfoOSXLinux(self):
    client_mock = action_mocks.UnixVolumeClientMock()
    session_id = flow_test_lib.TestFlowHelper(
        compatibility.GetName(filesystem.DiskVolumeInfo),
        client_mock,
        client_id=self.client_id,
        token=self.token,
        path_list=["/usr/local", "/home"])

    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    self.assertCountEqual([x.unixvolume.mount_point for x in results],
                          ["/", "/usr"])

  @parser_test_lib.WithParser("WmiDisk", wmi_parser.WMILogicalDisksParser)
  @parser_test_lib.WithParser("WinReg", winreg_parser.WinSystemRootParser)
  def testDiskVolumeInfoWindows(self):
    self.client_id = self.SetupClient(0, system="Windows")
    with vfs_test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.REGISTRY,
                                   vfs_test_lib.FakeRegistryVFSHandler):

      client_mock = action_mocks.WindowsVolumeClientMock()
      session_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.DiskVolumeInfo),
          client_mock,
          client_id=self.client_id,
          token=self.token,
          path_list=[r"D:\temp\something", r"/var/tmp"])

      results = flow_test_lib.GetFlowResults(self.client_id, session_id)

      # We asked for D and we guessed systemroot (C) for "/var/tmp", but only
      # C and Z are present, so we should just get C.
      self.assertCountEqual([x.windowsvolume.drive_letter for x in results],
                            ["C:"])

      session_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.DiskVolumeInfo),
          client_mock,
          client_id=self.client_id,
          token=self.token,
          path_list=[r"Z:\blah"])

      results = flow_test_lib.GetFlowResults(self.client_id, session_id)
      self.assertCountEqual([x.windowsvolume.drive_letter for x in results],
                            ["Z:"])

  def testGlobBackslashHandlingNoRegex(self):
    self._Touch("foo.txt")
    self._Touch("foo.txt~")
    paths = [
        utils.JoinPath(self.temp_dir, "foo.txt"),

        # The backslash in the path will be replaced by a forward-slash when
        # building a tree representing all the paths (this behavior isn't
        # particularly correct). Note that the tilde does not need to be
        # escaped.
        utils.JoinPath(self.temp_dir, r"foo.txt\~"),
    ]
    expected_paths = [utils.JoinPath(self.temp_dir, "foo.txt")]
    results = self._RunGlob(paths)
    self.assertCountEqual(expected_paths, results)

  def testGlobBackslashHandlingWithRegex(self):
    os.mkdir(utils.JoinPath(self.temp_dir, "1"))
    self._Touch("1/foo.txt")
    self._Touch("1/foo.txt~")
    paths = [
        utils.JoinPath(self.temp_dir, "*/foo.txt"),

        # The backslash in the path will be replaced by a forward-slash when
        # building a tree representing all the paths (this behavior isn't
        # particularly correct). Note that the tilde does not need to be
        # escaped.
        utils.JoinPath(self.temp_dir, r"*/foo.txt\~"),
    ]
    expected_paths = [utils.JoinPath(self.temp_dir, "1/foo.txt")]
    results = self._RunGlob(paths)
    self.assertCountEqual(expected_paths, results)

  def testGlobBackslashHandlingWithRecursion(self):
    os.makedirs(utils.JoinPath(self.temp_dir, "1/2"))
    self._Touch("1/foo.txt")
    self._Touch("1/foo.txt~")
    self._Touch("1/2/foo.txt")
    self._Touch("1/2/foo.txt~")
    paths = [
        utils.JoinPath(self.temp_dir, "**2/foo.txt"),

        # The backslash in the path will be replaced by a forward-slash when
        # building a tree representing all the paths (this behavior isn't
        # particularly correct). Note that the tilde does not need to be
        # escaped.
        utils.JoinPath(self.temp_dir, r"**2/foo.txt\~"),
    ]
    expected_paths = [
        utils.JoinPath(self.temp_dir, "1/foo.txt"),
        utils.JoinPath(self.temp_dir, "1/2/foo.txt"),
    ]
    results = self._RunGlob(paths)
    self.assertCountEqual(expected_paths, results)

  def _Touch(self, relative_path):
    io.open(utils.JoinPath(self.temp_dir, relative_path), "wb").close()

  def testListingRegistryDirectoryDoesNotYieldMtimes(self):
    with vfs_test_lib.RegistryVFSStubber():

      client_id = self.SetupClient(0)
      pb = rdf_paths.PathSpec(
          path="/HKEY_LOCAL_MACHINE/SOFTWARE/ListingTest",
          pathtype=rdf_paths.PathSpec.PathType.REGISTRY)

      client_mock = action_mocks.ListDirectoryClientMock()

      flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.ListDirectory),
          client_mock,
          client_id=client_id,
          pathspec=pb,
          token=self.token)

      if data_store.AFF4Enabled():
        output_path = client_id.Add("registry").Add(pb.first.path)
        results = list(
            aff4.FACTORY.Open(output_path, token=self.token).OpenChildren())
        self.assertLen(results, 2)
        for result in results:
          st = result.Get(result.Schema.STAT)
          self.assertIsNone(st.st_mtime)
      else:
        children = data_store.REL_DB.ListChildPathInfos(
            self.client_id.Basename(), rdf_objects.PathInfo.PathType.REGISTRY,
            ["HKEY_LOCAL_MACHINE", "SOFTWARE", "ListingTest"])
        self.assertLen(children, 2)
        for child in children:
          self.assertIsNone(child.stat_entry.st_mtime)


class RelFlowsTestFilesystem(db_test_lib.RelationalDBEnabledMixin,
                             TestFilesystem):

  flow_base_cls = flow_base.FlowBase

  # No async flow starts in the new framework anymore.
  def testIllegalGlobAsync(self):
    pass


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
