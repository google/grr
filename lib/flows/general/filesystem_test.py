#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the filesystem related flows."""

import hashlib
import os

from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import standard
from grr.lib.flows.general import filesystem


class TestFilesystem(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def testListDirectoryOnFile(self):
    """OS ListDirectory on a file will raise."""
    client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    # Make sure the flow raises.
    self.assertRaises(RuntimeError, list, test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token))

  def testListDirectory(self):
    """Test that the ListDirectory flow works."""
    client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    # Deliberately specify incorrect casing for the image name.
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)
    pb.Append(path="test directory",
              pathtype=rdfvalue.PathSpec.PathType.TSK)

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(pb.first.path)

    fd = aff4.FACTORY.Open(output_path.Add("Test Directory"), token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]

    # Check that the object is stored with the correct casing.
    self.assertEqual(child.urn.Basename(), "numbers.txt")

    # And the wrong object is not there
    self.assertRaises(IOError, aff4.FACTORY.Open,
                      output_path.Add("test directory"),
                      aff4_type="VFSDirectory", token=self.token)

  def testUnicodeListDirectory(self):
    """Test that the ListDirectory flow works on unicode directories."""

    client_mock = action_mocks.ActionMock("ListDirectory", "StatFile")

    # Deliberately specify incorrect casing
    pb = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)

    pb.Append(path=u"入乡随俗 海外春节别样过法",
              pathtype=rdfvalue.PathSpec.PathType.TSK)

    for _ in test_lib.TestFlowHelper(
        "ListDirectory", client_mock, client_id=self.client_id,
        pathspec=pb, token=self.token):
      pass

    # Check the output file is created
    output_path = self.client_id.Add("fs/tsk").Add(pb.CollapsePath())

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.OpenChildren())
    self.assertEqual(len(children), 1)
    child = children[0]
    self.assertEqual(
        os.path.basename(utils.SmartUnicode(child.urn)), u"入乡随俗.txt")

  def testGlob(self):
    """Test that glob works properly."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = client.Schema.USER()
    users.Append(username="test")
    users.Append(username="syslog")
    client.Set(users)
    client.Close()

    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob selects all files which start with the username on this system.
    paths = [os.path.join(self.base_path, "%%Users.username%%*"),
             os.path.join(self.base_path, "wtmp")]

    # Set iterator really low to force iteration.
    with utils.Stubber(filesystem.Glob, "FILE_MAX_PER_DIR", 2):
      for _ in test_lib.TestFlowHelper(
          "Glob", client_mock, client_id=self.client_id,
          paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
          token=self.token, sync=False, check_flow_errors=False):
        pass

    output_path = self.client_id.Add("fs/os").Add(
        self.base_path.replace("\\", "/"))

    children = []
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    for child in fd.ListChildren():
      children.append(child.Basename())

    # We should find some files.
    self.assertEqual(sorted(children),
                     sorted(["syslog", "syslog_compress.gz",
                             "syslog_false.gz", "test_artifacts.json",
                             "test_artifact.json", "test_img.dd", "test.plist",
                             "tests", "tests_long", "wtmp"]))

  def _MockSendReply(self, reply=None):
    self.flow_replies.append(reply.pathspec.path)

  def _RunGlob(self, paths):
    self.flow_replies = []
    client_mock = action_mocks.ActionMock("Find", "StatFile")
    with utils.Stubber(flow.GRRFlow, "SendReply", self._MockSendReply):
      for _ in test_lib.TestFlowHelper(
          "Glob", client_mock, client_id=self.client_id,
          paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
          token=self.token):
        pass

  def testGlobWithStarStarRootPath(self):
    """Test ** expressions with root_path."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = client.Schema.USER()
    users.Append(username="test")
    users.Append(username="syslog")
    client.Set(users)
    client.Close()

    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # Glob for foo at a depth of 4.
    path = os.path.join("foo**4")
    root_path = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)
    root_path.Append(path="/",
                     pathtype=rdfvalue.PathSpec.PathType.TSK)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], root_path=root_path,
        pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(
        self.base_path.replace("\\", "/")).Add("test_img.dd/glob_test/a/b")

    children = []
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    for child in fd.ListChildren():
      children.append(child.Basename())

    # We should find some files.
    self.assertEqual(children, ["foo"])

  def _MakeTestDirs(self):
    fourth_level_dir = utils.JoinPath(self.temp_dir, "1/2/3/4")
    os.makedirs(fourth_level_dir)

    top_level_path = self.temp_dir
    open(utils.JoinPath(top_level_path, "bar"), "w").close()
    for level in range(1, 5):
      top_level_path = utils.JoinPath(top_level_path, level)
      for filename in ("foo", "fOo", "bar"):
        file_path = utils.JoinPath(top_level_path, filename + str(level))
        open(file_path, "w").close()
        self.assertTrue(os.path.exists(file_path))

  def testGlobWithStarStar(self):
    """Test that ** expressions mean recursion."""

    self._MakeTestDirs()

    # Test filename and directory with spaces
    os.makedirs(utils.JoinPath(self.temp_dir, "1/2 space"))
    path_spaces = utils.JoinPath(self.temp_dir, "1/2 space/foo something")
    open(path_spaces, "w").close()
    self.assertTrue(os.path.exists(path_spaces))

    # Get the foos using default of 3 directory levels.
    paths = [
        os.path.join(self.temp_dir, "1/**/foo*")]
    results = ["1/2/3/4/fOo4", "1/2/3/4/foo4", "/1/2/3/fOo3", "/1/2/3/foo3",
               "1/2/fOo2", "1/2/foo2", "1/2 space/foo something"]
    self._RunGlob(paths)
    self.assertItemsEqual(self.flow_replies,
                          [utils.JoinPath(self.temp_dir, x) for x in results])

    # Get the files 2 levels down only.
    paths = [os.path.join(self.temp_dir, "1/", "**2/foo*")]
    results = ["1/2/3/foo3", "1/2/3/fOo3", "/1/2/fOo2", "/1/2/foo2",
               "1/2 space/foo something"]
    self._RunGlob(paths)
    self.assertItemsEqual(self.flow_replies,
                          [utils.JoinPath(self.temp_dir, x) for x in results])

    # Get all of the bars.
    paths = [os.path.join(self.temp_dir, "**10bar*")]
    results = ["bar", "1/bar1", "/1/2/bar2", "/1/2/3/bar3", "/1/2/3/4/bar4"]
    self._RunGlob(paths)
    self.assertItemsEqual(self.flow_replies,
                          [utils.JoinPath(self.temp_dir, x) for x in results])

  def testGlobWithTwoStars(self):
    self._MakeTestDirs()
    paths = [os.path.join(self.temp_dir, "1/", "*/*/foo*")]
    results = ["1/2/3/foo3", "1/2/3/fOo3"]
    self._RunGlob(paths)
    self.assertItemsEqual(self.flow_replies,
                          [utils.JoinPath(self.temp_dir, x) for x in results])

  def testGlobWithMultiplePaths(self):
    self._MakeTestDirs()
    paths = [os.path.join(self.temp_dir, "*/*/foo*"),
             os.path.join(self.temp_dir, "notthere"),
             os.path.join(self.temp_dir, "*/notthere"),
             os.path.join(self.temp_dir, "*/foo*")]
    results = ["1/foo1", "1/fOo1", "/1/2/fOo2", "/1/2/foo2"]
    self._RunGlob(paths)
    self.assertItemsEqual(self.flow_replies,
                          [utils.JoinPath(self.temp_dir, x) for x in results])

  def testGlobWithInvalidStarStar(self):
    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob is invalid since it uses 2 ** expressions..
    paths = [os.path.join(self.base_path, "test_img.dd", "**", "**", "foo")]

    # Make sure the flow raises.
    self.assertRaises(ValueError, list, test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token))

  def testGlobWithWildcardsInsideTSKFile(self):
    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join("*", "a", "b", "*")
    root_path = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_img.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)
    root_path.Append(path="/",
                     pathtype=rdfvalue.PathSpec.PathType.TSK)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], root_path=root_path,
        pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path, "test_img.dd", "glob_test", "a", "b"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].Basename(), "foo")

  def testGlobWithWildcardsInsideTSKFileCaseInsensitive(self):
    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join("*", "a", "b", "FOO*")
    root_path = rdfvalue.PathSpec(
        path=os.path.join(self.base_path, "test_IMG.dd"),
        pathtype=rdfvalue.PathSpec.PathType.OS)
    root_path.Append(path="/",
                     pathtype=rdfvalue.PathSpec.PathType.TSK)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], root_path=root_path,
        pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path, "test_img.dd", "glob_test", "a", "b"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].Basename(), "foo")

  def testGlobWildcardsAndTSK(self):
    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob should find this file in test data: glob_test/a/b/foo.
    path = os.path.join(self.base_path,
                        "test_IMG.dd", "glob_test", "a", "b", "FOO*")
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    output_path = self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path, "test_img.dd", "glob_test", "a", "b"))

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].Basename(), "foo")

    aff4.FACTORY.Delete(self.client_id.Add("fs/tsk").Add(os.path.join(
        self.base_path)), token=self.token)

    # Specifying a wildcard for the image will not open it.
    path = os.path.join(self.base_path,
                        "*.dd", "glob_test", "a", "b", "FOO*")
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], pathtype=rdfvalue.PathSpec.PathType.OS,
        token=self.token):
      pass

    fd = aff4.FACTORY.Open(output_path, token=self.token)
    children = list(fd.ListChildren())

    self.assertEqual(len(children), 0)

  def testGlobDirectory(self):
    """Test that glob expands directories."""

    # Add some usernames we can interpolate later.
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    user_attribute = client.Schema.USER()

    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "test_data/index.dat"
    user_attribute.Append(user_record)

    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "test_data/History"
    user_attribute.Append(user_record)

    # This is a record which means something to the interpolation system. We
    # should not process this especially.
    user_record = rdfvalue.User()
    user_record.special_folders.app_data = "%%PATH%%"
    user_attribute.Append(user_record)

    client.Set(user_attribute)

    client.Close()

    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # This glob selects all files which start with the username on this system.
    path = os.path.join(os.path.dirname(self.base_path),
                        "%%Users.special_folders.app_data%%")

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

    path = self.client_id.Add("fs/os").Add(self.base_path).Add("index.dat")

    aff4.FACTORY.Open(path, aff4_type="VFSFile", token=self.token)

    path = self.client_id.Add("fs/os").Add(self.base_path).Add("index.dat")

    aff4.FACTORY.Open(path, aff4_type="VFSFile", token=self.token)

  def testGlobGrouping(self):
    """Test that glob expands directories."""

    pattern = "test_data/{ntfs_img.dd,*.log,*.raw}"

    client_mock = action_mocks.ActionMock("Find", "StatFile")
    path = os.path.join(os.path.dirname(self.base_path), pattern)

    # Run the flow.
    for _ in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id,
        paths=[path], token=self.token):
      pass

  def testIllegalGlob(self):
    """Test that illegal globs raise."""

    paths = ["Test/%%Weird_illegal_attribute%%"]

    # Run the flow - we expect an AttributeError error to be raised from the
    # flow since Weird_illegal_attribute is not a valid client attribute.
    self.assertRaises(AttributeError, flow.GRRFlow.StartFlow,
                      flow_name="Glob", paths=paths,
                      client_id=self.client_id, token=self.token)

  def testIllegalGlobAsync(self):
    # When running the flow asynchronously, we will not receive any errors from
    # the Start method, but the flow should still fail.
    paths = ["Test/%%Weird_illegal_attribute%%"]
    client_mock = action_mocks.ActionMock("Find", "StatFile")

    # Run the flow.
    session_id = None

    # This should not raise here since the flow is run asynchronously.
    for session_id in test_lib.TestFlowHelper(
        "Glob", client_mock, client_id=self.client_id, check_flow_errors=False,
        paths=paths, pathtype=rdfvalue.PathSpec.PathType.OS, token=self.token,
        sync=False):
      pass

    fd = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertTrue("AttributeError" in fd.state.context.backtrace)
    self.assertEqual("ERROR", str(fd.state.context.state))

  def testGlobRoundtrips(self):
    """Tests that glob doesn't use too many client round trips."""

    for pattern, num_find, num_stat, duplicated_ok in [
        ("test_data/test_artifact.json", 0, 1, False),
        ("test_data/test_*", 1, 0, False),
        ("test_*/test_artifact.json", 1, 1, False),
        ("test_*/test_*", 2, 0, False),
        ("test_*/test_{artifact,artifacts}.json", 1, 2, True),
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
      client_mock = action_mocks.RecordingActionMock("Find", "StatFile")

      # Run the flow.
      for _ in test_lib.TestFlowHelper(
          "Glob", client_mock, client_id=self.client_id,
          paths=[path], token=self.token):
        pass

      if num_find is not None:
        self.assertEqual(client_mock.action_counts.get("Find", 0), num_find)
      if num_stat is not None:
        self.assertEqual(client_mock.action_counts.get("StatFile", 0), num_stat)

      if not duplicated_ok:
        # Check for duplicate client calls. There might be duplicates that are
        # very cheap when we look for a wildcard (* or **) first and later in
        # the pattern for a group of files ({}).
        for method in "StatFile", "Find":
          stat_args = client_mock.recorded_args.get(method, [])
          stat_paths = [c.pathspec.CollapsePath() for c in stat_args]
          self.assertListEqual(sorted(stat_paths), sorted(set(stat_paths)))

  def _CheckCasing(self, path, filename):
    output_path = self.client_id.Add("fs/os").Add(os.path.join(
        self.base_path, path))
    fd = aff4.FACTORY.Open(output_path, token=self.token)
    filenames = [urn.Basename() for urn in fd.ListChildren()]
    self.assertTrue(filename in filenames)

  def testGlobCaseCorrection(self):
    # This should get corrected to "a/b/c/helloc.txt"
    test_path = "a/B/c/helloC.txt"

    self._RunGlob([os.path.join(self.base_path, test_path)])

    self._CheckCasing("a", "b")
    self._CheckCasing("a/b/c", "helloc.txt")

    aff4.FACTORY.Delete(self.client_id.Add("fs/os").Add(self.base_path),
                        token=self.token)

    # Make sure this also works with *s in the glob.

    # This should also get corrected to "a/b/c/helloc.txt"
    test_path = "a/*/C/*.txt"

    self._RunGlob([os.path.join(self.base_path, test_path)])

    self._CheckCasing("a", "b")
    self._CheckCasing("a/b", "c")

  def testDownloadDirectory(self):
    """Test a FileFinder flow with depth=1."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions FileFinder uses.
    client_mock = action_mocks.ActionMock("FingerprintFile", "HashBuffer",
                                          "StatFile", "Find", "TransferBuffer")

    for _ in test_lib.TestFlowHelper(
        "FileFinder", client_mock, client_id=self.client_id,
        paths=["/c/Downloads/*"],
        action=rdfvalue.FileFinderAction(
            action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD),
        token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 6 children:
    expected_children = u"a.txt b.txt c.txt d.txt sub1 中国新闻网新闻中.txt"

    self.assertEqual(len(children), 6)

    self.assertEqual(expected_children.split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: a.txt
    for child in children:
      if child.urn.Basename() == "a.txt":
        break

    # Check the AFF4 type of the child, it should have changed
    # from VFSFile to VFSBlobImage
    self.assertEqual(child.__class__.__name__, "VFSBlobImage")

  def testDownloadDirectorySub(self):
    """Test a FileFinder flow with depth=5."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions FileFinder uses.
    client_mock = action_mocks.ActionMock("FingerprintFile", "HashBuffer",
                                          "StatFile", "Find", "TransferBuffer")

    for _ in test_lib.TestFlowHelper(
        "FileFinder", client_mock, client_id=self.client_id,
        paths=["/c/Downloads/**5"],
        action=rdfvalue.FileFinderAction(
            action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD),
        token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 6 children:
    expected_children = u"a.txt b.txt c.txt d.txt sub1 中国新闻网新闻中.txt"

    self.assertEqual(len(children), 6)

    self.assertEqual(expected_children.split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: sub1
    for child in children:
      if child.urn.Basename() == "sub1":
        break

    children = list(child.OpenChildren())

    # There should be 4 children: a.txt, b.txt, c.txt, d.txt
    expected_children = "a.txt b.txt c.txt d.txt"

    self.assertEqual(len(children), 4)

    self.assertEqual(expected_children.split(),
                     sorted([child.urn.Basename() for child in children]))

  def CreateNewSparseImage(self):
    path = os.path.join(self.base_path, "test_img.dd")

    urn = self.client_id.Add("fs/os").Add(path)

    pathspec = rdfvalue.PathSpec(
        path=path, pathtype=rdfvalue.PathSpec.PathType.OS)

    with aff4.FACTORY.Create(
        urn, "AFF4SparseImage", mode="rw", token=self.token) as fd:

      # Give the new object a pathspec.
      fd.Set(fd.Schema.PATHSPEC, pathspec)

      return fd

  def ReadFromSparseImage(self, length, offset):

    fd = self.CreateNewSparseImage()
    urn = fd.urn

    self.client_mock = action_mocks.ActionMock("FingerprintFile", "HashBuffer",
                                               "StatFile", "Find",
                                               "TransferBuffer", "ReadBuffer")
    for _ in test_lib.TestFlowHelper(
        "FetchBufferForSparseImage", self.client_mock, client_id=self.client_id,
        token=self.token, file_urn=urn, length=length,
        offset=offset):
      pass

    # Reopen the object so we can read the freshest version of the size
    # attribute.
    fd = aff4.FACTORY.Open(urn, token=self.token)

    return fd

  def testFetchBufferForSparseImageReadAlignedToChunks(self):
    # From a 2MiB offset, read 5MiB.
    length = 1024 * 1024 * 5
    offset = 1024 * 1024 * 2
    fd = self.ReadFromSparseImage(length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # We should have increased in size by the amount of data we requested
    # exactly, since we already aligned to chunks.
    self.assertEqual(int(size_after), length)

    # Open the actual file on disk without using AFF4 and hash the data we
    # expect to be reading.
    with open(os.path.join(self.base_path, "test_img.dd"), "rb") as test_file:
      test_file.seek(offset)
      disk_file_contents = test_file.read(length)
      expected_hash = hashlib.sha256(disk_file_contents).digest()

    # Write the file contents to the datastore.
    fd.Flush()
    # Make sure the data we read is actually the data that was in the file.
    fd.Seek(offset)
    contents = fd.Read(length)

    # There should be no gaps.
    self.assertEqual(len(contents), length)

    self.assertEqual(hashlib.sha256(contents).digest(), expected_hash)

  def testFetchBufferForSparseImageReadNotAlignedToChunks(self):

    # Read a non-whole number of chunks.
    # (This should be rounded up to 5Mib + 1 chunk)
    length = 1024 * 1024 * 5 + 42
    # Make sure we're not reading from exactly the beginning of a chunk.
    # (This should get rounded down to 2Mib)
    offset = 1024 * 1024 * 2 + 1

    fd = self.ReadFromSparseImage(length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # The chunksize the sparse image uses.
    chunksize = aff4.AFF4SparseImage.chunksize

    # We should have rounded the 5Mib + 42 up to the nearest chunk,
    # and rounded down the + 1 on the offset.
    self.assertEqual(int(size_after), length + (chunksize - 42))

  def testFetchBufferForSparseImageCorrectChunksRead(self):
    length = 1
    offset = 1024 * 1024 * 10
    fd = self.ReadFromSparseImage(length=length, offset=offset)
    size_after = fd.Get(fd.Schema.SIZE)

    # We should have rounded up to 1 chunk size.
    self.assertEqual(int(size_after), fd.chunksize)

  def ReadTestImage(self, size_threshold):
    path = os.path.join(self.base_path, "test_img.dd")

    urn = rdfvalue.RDFURN(self.client_id.Add("fs/os").Add(path))

    pathspec = rdfvalue.PathSpec(
        path=path, pathtype=rdfvalue.PathSpec.PathType.OS)

    client_mock = action_mocks.ActionMock("FingerprintFile", "HashBuffer",
                                          "StatFile", "Find", "TransferBuffer",
                                          "ReadBuffer")

    # Get everything as an AFF4SparseImage
    for _ in test_lib.TestFlowHelper(
        "MakeNewAFF4SparseImage", client_mock, client_id=self.client_id,
        token=self.token, size_threshold=size_threshold, pathspec=pathspec):
      pass

    fd = aff4.FACTORY.Open(urn, token=self.token)
    return fd

  def testReadNewAFF4SparseImage(self):

    # Smaller than the size of the file.
    fd = self.ReadTestImage(size_threshold=0)

    self.assertTrue(isinstance(fd, standard.AFF4SparseImage))

    # The file should be empty.
    self.assertEqual(fd.Read(10000), "")
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

  def testNewSparseImageFileNotBigEnough(self):

    # Bigger than the size of the file.
    fd = self.ReadTestImage(size_threshold=2 ** 32)
    # We shouldn't be a sparse image in this case.
    self.assertFalse(isinstance(fd, aff4.AFF4SparseImage))
    self.assertTrue(isinstance(fd, aff4.AFF4Image))

    self.assertNotEqual(fd.Read(10000), "")
    self.assertNotEqual(fd.Get(fd.Schema.SIZE), 0)

  def testDiskVolumeInfoOSXLinux(self):
    client_mock = action_mocks.UnixVolumeClientMock("StatFile", "ListDirectory")
    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for _ in test_lib.TestFlowHelper(
          "DiskVolumeInfo", client_mock, client_id=self.client_id,
          token=self.token, path_list=["/usr/local", "/home"]):
        pass

      results = []
      for _, reply in send_reply.args:
        if isinstance(reply, rdfvalue.Volume):
          results.append(reply)

      self.assertItemsEqual([x.unix.mount_point for x in results],
                            ["/", "/usr"])
      self.assertEqual(len(results), 2)

  def testDiskVolumeInfoWindows(self):
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Flush()
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.FakeRegistryVFSHandler

    client_mock = action_mocks.WindowsVolumeClientMock("StatFile",
                                                       "ListDirectory")

    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for _ in test_lib.TestFlowHelper(
          "DiskVolumeInfo", client_mock, client_id=self.client_id,
          token=self.token, path_list=[r"D:\temp\something", r"/var/tmp"]):
        pass

      results = []
      for cls, reply in send_reply.args:
        if isinstance(cls, filesystem.DiskVolumeInfo) and isinstance(
            reply, rdfvalue.Volume):
          results.append(reply)

      # We asked for D and we guessed systemroot (C) for "/var/tmp", but only C
      # and Z are present, so we should just get C.
      self.assertItemsEqual([x.windows.drive_letter for x in results],
                            ["C:"])
      self.assertEqual(len(results), 1)

    with test_lib.Instrument(flow.GRRFlow, "SendReply") as send_reply:
      for _ in test_lib.TestFlowHelper(
          "DiskVolumeInfo", client_mock, client_id=self.client_id,
          token=self.token, path_list=[r"Z:\blah"]):
        pass

      results = []
      for cls, reply in send_reply.args:
        if isinstance(cls, filesystem.DiskVolumeInfo) and isinstance(
            reply, rdfvalue.Volume):
          results.append(reply)

      self.assertItemsEqual([x.windows.drive_letter for x in results],
                            ["Z:"])
      self.assertEqual(len(results), 1)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
