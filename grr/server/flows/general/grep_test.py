#!/usr/bin/env python
"""Tests for grr.server.flows.general.grep."""


import os

from grr.client.client_actions import searching
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import standard as rdf_standard
from grr.server import aff4
from grr.server import client_fixture
from grr.server import flow
from grr.server.aff4_objects import aff4_grr
from grr.server.flows.general import grep
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class GrepTests(flow_test_lib.FlowTestsBaseclass):
  pass


class TestSearchFileContentWithFixture(GrepTests):

  def FlushVFSCache(self):
    vfs_test_lib.ClientVFSHandlerFixture.cache = {}

  def CreateFile(self, filename, data):

    # Delete the fixture cache so this will be included.
    self.FlushVFSCache()

    client_fixture.VFS.append((filename, (aff4_grr.VFSFile, {
        "aff4:stat": ("\n"
                                "st_mode: 33261\n"
                                "st_ino: 1026267\n"
                                "st_dev: 51713\n"
                                "st_nlink: 1\n"
                                "st_uid: 0\n"
                                "st_gid: 0\n"
                                "st_size: 60064\n"
                                "st_atime: 1308964274\n"
                                "st_mtime: 1285093975\n"
                                "st_ctime: 1299502221\n"
                                "st_blocks: 128\n"
                                "st_blksize: 4096\n"
                                "st_rdev: 0\n"
                                "pathspec {\n"
                                "  pathtype: OS\n"
                                "  path: '%s'\n"
                                "}\n"
                                "resident: '%s'\n" % (filename, data)),
        "aff4:size":
            len(data)
    })))

  def DeleteFile(self, filename):

    # Delete the fixture cache so this will be included.
    self.FlushVFSCache()

    client_fixture.VFS = [
        path for path in client_fixture.VFS if path[0] != filename
    ]

  def setUp(self):
    super(TestSearchFileContentWithFixture, self).setUp()

    self.client_mock = action_mocks.GrepClientMock()
    self.vfs_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.ClientVFSHandlerFixture)
    self.vfs_overrider.Start()

  def tearDown(self):
    super(TestSearchFileContentWithFixture, self).tearDown()
    self.vfs_overrider.Stop()

  def testNormalGrep(self):
    grepspec = rdf_client.BareGrepSpec(
        mode=rdf_client.GrepSpec.Mode.FIRST_HIT, literal="hello")

    for s in flow_test_lib.TestFlowHelper(
        grep.SearchFileContent.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=["/proc/10/cmdline"],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        token=self.token,
        grep=grepspec):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    self.assertEqual(len(fd), 1)
    self.assertEqual(fd[0].offset, 3)
    self.assertEqual(fd[0], "ls\x00hello world\'\x00-l")
    self.assertEqual(fd[0].length, 18)

  def testMultipleHits(self):
    filename = "/fs/os/c/Downloads/grepfile.txt"
    data = "random content here. I am a HIT!!" * 100

    self.CreateFile(filename, data)

    grepspec = rdf_client.BareGrepSpec(
        mode=rdf_client.GrepSpec.Mode.ALL_HITS, literal="HIT")

    for s in flow_test_lib.TestFlowHelper(
        grep.SearchFileContent.__name__,
        self.client_mock,
        client_id=self.client_id,
        paths=["/c/Downloads/grepfile.txt"],
        pathtype=rdf_paths.PathSpec.PathType.OS,
        grep=grepspec,
        token=self.token):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    self.assertEqual(len(fd), 100)
    self.assertEqual(fd[15].offset, 523)
    self.assertEqual(fd[38], "e. I am a HIT!!random c")
    self.assertEqual(fd[99], "e. I am a HIT!!")

    self.DeleteFile(filename)

  def testPatternAtBufsize(self):
    old_size = searching.Grep.BUFF_SIZE
    try:
      searching.Grep.BUFF_SIZE = 10000

      filename = "/fs/os/c/Downloads/grepfile.txt"
      data = "X" * (searching.Grep.BUFF_SIZE - len("HIT")) + "HIT" + "X" * 1000
      self.CreateFile(filename, data)

      grepspec = rdf_client.BareGrepSpec(
          mode=rdf_client.GrepSpec.Mode.FIRST_HIT, literal="HIT")

      for s in flow_test_lib.TestFlowHelper(
          grep.SearchFileContent.__name__,
          self.client_mock,
          client_id=self.client_id,
          paths=["/c/Downloads/grepfile.txt"],
          pathtype=rdf_paths.PathSpec.PathType.OS,
          token=self.token,
          grep=grepspec):
        session_id = s

      fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)
      self.assertEqual(len(fd), 1)
      self.assertEqual(fd[0].offset, searching.Grep.BUFF_SIZE - len("HIT"))
      self.assertEqual(fd[0].length, 23)

      self.DeleteFile(filename)
    finally:
      searching.Grep.BUFF_SIZE = old_size


class TestSearchFileContent(GrepTests):

  def testSearchFileContents(self):
    pattern = "searching/*.log"

    client_mock = action_mocks.GrepClientMock()
    path = os.path.join(self.base_path, pattern)

    args = grep.SearchFileContentArgs(
        paths=[path], pathtype=rdf_paths.PathSpec.PathType.OS)

    args.grep.literal = rdf_standard.LiteralExpression(
        "session opened for user dearjohn")
    args.grep.mode = rdf_client.GrepSpec.Mode.ALL_HITS

    # Run the flow.
    for s in flow_test_lib.TestFlowHelper(
        grep.SearchFileContent.__name__,
        client_mock,
        client_id=self.client_id,
        args=args,
        token=self.token):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    # Make sure that there is a hit.
    self.assertEqual(len(fd), 1)
    first = fd[0]

    self.assertEqual(first.offset, 350)
    self.assertEqual(first.data,
                     "session): session opened for user dearjohn by (uid=0")

  def testSearchFileContentsNoGrep(self):
    """Search files without a grep specification."""
    pattern = "searching/*.log"

    client_mock = action_mocks.GrepClientMock()
    path = os.path.join(self.base_path, pattern)

    # Do not provide a Grep expression - should match all files.
    args = grep.SearchFileContentArgs(paths=[path])

    # Run the flow.
    for s in flow_test_lib.TestFlowHelper(
        grep.SearchFileContent.__name__,
        client_mock,
        client_id=self.client_id,
        args=args,
        token=self.token):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    self.assertEqual(len(fd), 3)

  def testSearchFileContentDownload(self):

    pattern = "searching/*.log"

    client_mock = action_mocks.GrepClientMock()
    path = os.path.join(self.base_path, pattern)

    # Do not provide a Grep expression - should match all files.
    args = grep.SearchFileContentArgs(paths=[path], also_download=True)

    # Run the flow.
    for s in flow_test_lib.TestFlowHelper(
        grep.SearchFileContent.__name__,
        client_mock,
        client_id=self.client_id,
        args=args,
        token=self.token):
      session_id = s

    fd = flow.GRRFlow.ResultCollectionForFID(session_id, token=self.token)

    self.assertEqual(len(fd), 3)

    for log in aff4.FACTORY.Open(
        rdfvalue.RDFURN(self.client_id).Add("/fs/os/").Add(
            self.base_path).Add("searching"),
        token=self.token).OpenChildren():
      self.assertTrue(isinstance(log, aff4_grr.VFSBlobImage))
      # Make sure there is some data.
      self.assertGreater(len(log), 0)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
