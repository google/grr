#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Test the filesystem related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import platform

from absl import app
from future.builtins import range
from future.builtins import str
import mock

from grr_response_core.lib import utils
from grr_response_core.lib.parsers import windows_registry_parser as winreg_parser
from grr_response_core.lib.parsers import wmi_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import temp
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import notification
from grr_response_server.databases import db
# TODO(user): break the dependency cycle described in filesystem.py and
# and remove this import.
# pylint: disable=unused-import
from grr_response_server.flows.general import collectors
# pylint: enable=unused-import
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestFilesystem(flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

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
    return data_store.REL_DB.ListChildPathInfos(self.client_id, path_type,
                                                components)

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
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS)

      flow_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.RecursiveListDirectory),
          client_mock,
          client_id=self.client_id,
          pathspec=pathspec,
          max_depth=2,
          token=self.token)

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
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS)

      flow_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.RecursiveListDirectory),
          client_mock,
          client_id=self.client_id,
          pathspec=pathspec,
          max_depth=1,
          token=self.token)

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
          path=temp_dirpath, pathtype=rdf_paths.PathSpec.PathType.OS)

      flow_id = flow_test_lib.TestFlowHelper(
          compatibility.GetName(filesystem.RecursiveListDirectory),
          client_mock,
          client_id=self.client_id,
          pathspec=pathspec,
          max_depth=3,
          token=self.token)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 3)

    dirs = [_.pathspec.Basename() for _ in results]
    self.assertCountEqual(dirs, ["dir1", "dir2", "dir3"])

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
        check_flow_errors=False)

    expected_files = [
        filename for filename in os.listdir(self.base_path)
        if filename.startswith("test") or filename.startswith("syslog")
    ]
    expected_files.append("VFSFixture")

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
      top_level_path = utils.JoinPath(top_level_path, str(level))
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

    with self.assertRaises(db.UnknownPathError):
      self._ListTestChildPathInfos(["test_img.dd", "glob_test", "a", "b"])

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

    children = self._ListTestChildPathInfos(
        [], path_type=rdf_objects.PathInfo.PathType.OS)
    files_found = [child.components[-1] for child in children]

    self.assertCountEqual(files_found, [
        "ntfs_img.dd",
        "apache_false_log",
        "apache_log",
        "syslog",
        "win_hello.exe",
    ])

  def testIllegalGlob(self):
    """Test that illegal globs raise."""

    paths = ["Test/%%Weird_illegal_attribute%%"]

    # Run the flow - we expect an AttributeError error to be raised from the
    # flow since Weird_illegal_attribute is not a valid client attribute.
    flow_id = flow_test_lib.StartFlow(
        filesystem.Glob, paths=paths, client_id=self.client_id)
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(
        flow_obj.error_message,
        "Some attributes are not part of the knowledgebase: "
        "weird_illegal_attribute")
    self.assertIn("KbInterpolationUnknownAttributesError", flow_obj.backtrace)

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

      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id, rdf_objects.PathInfo.PathType.OS, ["c", "Downloads"])
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

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(file_finder.FileFinder),
        client_mock,
        client_id=self.client_id,
        paths=[test_dir + "/*"],
        action=rdf_file_finder.FileFinderAction.Download(),
        token=self.token)

    # There should be 5 children:
    expected_filenames = ["a.txt", "b.txt", "c.txt", "d.txt", "sub1"]

    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id, rdf_objects.PathInfo.PathType.OS,
        test_dir.strip("/").split("/"))

    filenames = [child.components[-1] for child in children]
    self.assertCountEqual(filenames, expected_filenames)
    fd = file_store.OpenFile(
        db.ClientPath.FromPathInfo(self.client_id, children[0]))
    self.assertEqual(fd.read(), b"Hello World!\n")

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

    components = test_dir.strip("/").split("/")
    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id, rdf_objects.PathInfo.PathType.OS, components)
    filenames = [child.components[-1] for child in children]
    self.assertCountEqual(filenames, expected_filenames)

    children = data_store.REL_DB.ListChildPathInfos(
        self.client_id, rdf_objects.PathInfo.PathType.OS, components + ["sub1"])
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

      children = data_store.REL_DB.ListChildPathInfos(
          self.client_id, rdf_objects.PathInfo.PathType.REGISTRY,
          ["HKEY_LOCAL_MACHINE", "SOFTWARE", "ListingTest"])
      self.assertLen(children, 2)
      for child in children:
        self.assertIsNone(child.stat_entry.st_mtime)

  def testNotificationWhenListingRegistry(self):
    # Change the username so notifications get written.
    token = self.token.Copy()
    token.username = "notification_test"
    acl_test_lib.CreateUser(token.username)

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
          token=token)

    notifications = data_store.REL_DB.ReadUserNotifications(token.username)
    self.assertLen(notifications, 1)
    n = notifications[0]
    self.assertEqual(n.reference.vfs_file.path_type,
                     rdf_objects.PathInfo.PathType.REGISTRY)
    self.assertEqual(n.reference.vfs_file.path_components,
                     ["HKEY_LOCAL_MACHINE", "SOFTWARE", "ListingTest"])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
