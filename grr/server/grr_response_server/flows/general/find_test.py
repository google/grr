#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the Find flow."""
from grr_response_client.client_actions import searching
from grr.lib import flags
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import find
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class TestFindFlow(flow_test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def setUp(self):
    super(TestFindFlow, self).setUp()
    self.vfs_overrider = vfs_test_lib.VFSOverrider(
        rdf_paths.PathSpec.PathType.OS, vfs_test_lib.ClientVFSHandlerFixture)
    self.vfs_overrider.Start()
    self.client_id = self.SetupClient(0)

  def tearDown(self):
    super(TestFindFlow, self).tearDown()
    self.vfs_overrider.Stop()

  def testInvalidFindSpec(self):
    """Test that its impossible to produce an invalid findspec."""
    # The regular expression is not valid.
    self.assertRaises(
        type_info.TypeValueError, rdf_client.FindSpec, path_regex="[")

  def testFindFiles(self):
    """Test that the Find flow works with files."""
    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client.FindSpec(
        path_regex="bash",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Should match ["bash" and "rbash"].
    matches = set([x.AFF4Path(self.client_id).Basename() for x in fd])
    self.assertEqual(sorted(matches), ["bash", "rbash"])

    self.assertEqual(len(fd), 4)
    for child in fd:
      path = utils.SmartStr(child.AFF4Path(self.client_id))
      self.assertTrue(path.endswith("bash"))
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindFilesWithGlob(self):
    """Test that the Find flow works with glob."""
    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client.FindSpec(
        path_glob="bash*",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Make sure that bash is a file.
    matches = set([x.AFF4Path(self.client_id).Basename() for x in fd])
    self.assertEqual(sorted(matches), ["bash"])

    self.assertEqual(len(fd), 2)
    for child in fd:
      path = utils.SmartStr(child.AFF4Path(self.client_id))
      self.assertTrue(path.endswith("bash"))
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindDirectories(self):
    """Test that the Find flow works with directories."""

    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client.FindSpec(
        path_regex="bin",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Make sure that bin is a directory
    self.assertEqual(len(fd), 2)
    for child in fd:
      path = utils.SmartStr(child.AFF4Path(self.client_id))
      self.assertTrue("bin" in path)
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindWithMaxFiles(self):
    """Test that the Find flow works when specifying proto directly."""

    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client.FindSpec(
        path_regex=".*",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec,
        iteration_count=3,
        max_results=7)

    # Check the output file is created
    collection = flow.GRRFlow.ResultCollectionForFID(session_id)

    # Make sure we got the right number of results.
    self.assertEqual(len(collection), 7)

  def testCollectionOverwriting(self):
    """Test we overwrite the collection every time the flow is executed."""

    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client.FindSpec()
    findspec.path_regex = "bin"
    findspec.pathspec.path = "/"
    findspec.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)

    self.assertEqual(len(fd), 2)

    # Now find a new result, should overwrite the collection
    findspec.path_regex = "dd"
    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec,
        max_results=1)

    # Check the results collection.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    self.assertEqual(len(fd), 1)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
