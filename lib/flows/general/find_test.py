#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the Find flow."""
from grr.client import vfs
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib import utils


class TestFindFlow(test_lib.FlowTestsBaseclass):
  """Test the interrogate flow."""

  def setUp(self):
    super(TestFindFlow, self).setUp()
    # Install the mock
    vfs_type = rdfvalue.PathSpec.PathType.OS
    vfs.VFS_HANDLERS[vfs_type] = test_lib.ClientVFSHandlerFixture

  def testInvalidFindSpec(self):
    """Test that its impossible to produce an invalid findspec."""
    # The regular expression is not valid.
    self.assertRaises(type_info.TypeValueError, rdfvalue.FindSpec,
                      path_regex="[")

  def testFindFiles(self):
    """Test that the Find flow works with files."""
    client_mock = action_mocks.ActionMock("Find")
    output_path = "analysis/FindFlowTest1"

    # Prepare a findspec.
    findspec = rdfvalue.FindSpec(
        path_regex="bash",
        pathspec=rdfvalue.PathSpec(
            path="/", pathtype=rdfvalue.PathSpec.PathType.OS))

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        token=self.token, output=output_path, findspec=findspec):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Should match ["bash" and "rbash"].
    matches = set([x.aff4path.Basename() for x in fd])
    self.assertEqual(sorted(matches), ["bash", "rbash"])

    self.assertEqual(len(fd), 4)
    for child in fd:
      path = utils.SmartStr(child.aff4path)
      self.assertTrue(path.endswith("bash"))
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindFilesWithGlob(self):
    """Test that the Find flow works with glob."""
    client_mock = action_mocks.ActionMock("Find")
    output_path = "analysis/FindFlowTest1"

    # Prepare a findspec.
    findspec = rdfvalue.FindSpec(
        path_glob="bash*",
        pathspec=rdfvalue.PathSpec(
            path="/", pathtype=rdfvalue.PathSpec.PathType.OS))

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        token=self.token, output=output_path, findspec=findspec):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Make sure that bash is a file.
    matches = set([x.aff4path.Basename() for x in fd])
    self.assertEqual(sorted(matches), ["bash"])

    self.assertEqual(len(fd), 2)
    for child in fd:
      path = utils.SmartStr(child.aff4path)
      self.assertTrue(path.endswith("bash"))
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindDirectories(self):
    """Test that the Find flow works with directories."""

    client_mock = action_mocks.ActionMock("Find")
    output_path = "analysis/FindFlowTest2"

    # Prepare a findspec.
    findspec = rdfvalue.FindSpec(
        path_regex="bin",
        pathspec=rdfvalue.PathSpec(path="/",
                                   pathtype=rdfvalue.PathSpec.PathType.OS))

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id,
        token=self.token, output=output_path, findspec=findspec):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Make sure that bin is a directory
    self.assertEqual(len(fd), 2)
    for child in fd:
      path = utils.SmartStr(child.aff4path)
      self.assertTrue("bin" in path)
      self.assertEqual(child.__class__.__name__, "StatEntry")

  def testFindWithMaxFiles(self):
    """Test that the Find flow works when specifying proto directly."""

    client_mock = action_mocks.ActionMock("Find")
    output_path = "analysis/FindFlowTest4"

    # Prepare a findspec.
    findspec = rdfvalue.FindSpec(
        path_regex=".*",
        pathspec=rdfvalue.PathSpec(path="/",
                                   pathtype=rdfvalue.PathSpec.PathType.OS))

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=findspec, iteration_count=3, output=output_path,
        max_results=7):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add(output_path), token=self.token)

    # Make sure we got the right number of results.
    self.assertEqual(len(fd), 7)

  def testCollectionOverwriting(self):
    """Test we overwrite the collection every time the flow is executed."""

    client_mock = action_mocks.ActionMock("Find")
    output_path = "analysis/FindFlowTest5"

    # Prepare a findspec.
    findspec = rdfvalue.FindSpec()
    findspec.path_regex = "bin"
    findspec.pathspec.path = "/"
    findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS

    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=findspec, output=output_path):
      pass

    # Check the output file with the right number of results.
    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)

    self.assertEqual(len(fd), 2)

    # Now find a new result, should overwrite the collection
    findspec.path_regex = "dd"
    for _ in test_lib.TestFlowHelper(
        "FindFiles", client_mock, client_id=self.client_id, token=self.token,
        findspec=findspec, output=output_path, max_results=1):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add(output_path),
                           token=self.token)
    self.assertEqual(len(fd), 1)
