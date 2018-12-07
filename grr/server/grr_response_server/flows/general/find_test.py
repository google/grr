#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for the Find flow."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from grr_response_client.client_actions import searching
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.flows.general import find
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


@db_test_lib.DualDBTest
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
    with self.assertRaises(re.error):
      rdf_client_fs.FindSpec(path_regex="[")

  def testFindFiles(self):
    """Test that the Find flow works with files."""
    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client_fs.FindSpec(
        path_regex="bash",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    # Should match ["bash" and "rbash"].
    matches = set([x.AFF4Path(self.client_id).Basename() for x in results])
    self.assertCountEqual(matches, ["bash", "rbash"])

    self.assertLen(results, 4)
    for child in results:
      path = utils.SmartStr(child.AFF4Path(self.client_id))
      self.assertEndsWith(path, "bash")
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindFilesWithGlob(self):
    """Test that the Find flow works with glob."""
    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client_fs.FindSpec(
        path_glob="bash*",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    # Make sure that bash is a file.
    matches = set([x.AFF4Path(self.client_id).Basename() for x in results])
    self.assertEqual(matches, set(["bash"]))

    self.assertLen(results, 2)
    for child in results:
      path = utils.SmartStr(child.AFF4Path(self.client_id))
      self.assertEndsWith(path, "bash")
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindDirectories(self):
    """Test that the Find flow works with directories."""

    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client_fs.FindSpec(
        path_regex="bin",
        pathspec=rdf_paths.PathSpec(
            path="/", pathtype=rdf_paths.PathSpec.PathType.OS))

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    # Make sure that bin is a directory
    self.assertLen(results, 2)
    for child in results:
      self.assertEqual(child.__class__.__name__, "StatEntry")
      self.assertIn("bin", child.pathspec.CollapsePath())

  def testCollectionOverwriting(self):
    """Test we overwrite the collection every time the flow is executed."""

    client_mock = action_mocks.ActionMock(searching.Find)

    # Prepare a findspec.
    findspec = rdf_client_fs.FindSpec()
    findspec.path_regex = "bin"
    findspec.pathspec.path = "/"
    findspec.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    self.assertLen(results, 2)

    # Now find a new result, should overwrite the collection
    findspec.path_regex = "dd"
    session_id = flow_test_lib.TestFlowHelper(
        find.FindFiles.__name__,
        client_mock,
        client_id=self.client_id,
        token=self.token,
        findspec=findspec)

    # Check the results.
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertLen(results, 1)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
