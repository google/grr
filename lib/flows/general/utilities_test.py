#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the utilities related flows."""

from grr.client import vfs
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestDownloadDirectory(test_lib.FlowTestsBaseclass):
  """Test the DownloadDirectory flow."""

  def testDownloadDirectory(self):
    """Test a DownloadDirectory flow with depth=1."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions DownloadDirectory uses
    client_mock = test_lib.ActionMock("HashFile",
                                      "ReadBuffer",
                                      "ListDirectory",
                                      "StatFile",
                                      "TransferBuffer")

    pathspec = rdfvalue.PathSpec(
        path="/c/Downloads", pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "DownloadDirectory", client_mock, client_id=self.client_id,
        depth=1, pathspec=pathspec, ignore_errors=False, token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 4 children: a.txt, b.txt, c.txt, d.txt
    self.assertEqual(len(children), 4)

    self.assertEqual("a.txt b.txt c.txt d.txt".split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: a.txt
    for child in children:
      if child.urn.Basename() == "a.txt":
        break

    # Check the AFF4 type of the child, it should have changed
    # from VFSFile to HashImage
    self.assertEqual(child.__class__.__name__, "HashImage")

  def testDownloadDirectorySub(self):
    """Test a DownloadDirectory flow with depth=5."""
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientVFSHandlerFixture

    # Mock the client actions DownloadDirectory uses
    client_mock = test_lib.ActionMock("HashFile",
                                      "ReadBuffer",
                                      "ListDirectory",
                                      "StatFile",
                                      "TransferBuffer")

    pathspec = rdfvalue.PathSpec(
        path="/c/Downloads", pathtype=rdfvalue.PathSpec.PathType.OS)

    for _ in test_lib.TestFlowHelper(
        "DownloadDirectory", client_mock, client_id=self.client_id,
        pathspec=pathspec, depth=5, ignore_errors=False, token=self.token):
      pass

    # Check if the base path was created
    output_path = self.client_id.Add("fs/os/c/Downloads")

    output_fd = aff4.FACTORY.Open(output_path, token=self.token)

    children = list(output_fd.OpenChildren())

    # There should be 5 children: a.txt, b.txt, c.txt, d.txt, sub1
    self.assertEqual(len(children), 5)

    self.assertEqual("a.txt b.txt c.txt d.txt sub1".split(),
                     sorted([child.urn.Basename() for child in children]))

    # Find the child named: sub1
    for child in children:
      if child.urn.Basename() == "sub1":
        break

    children = list(child.OpenChildren())

    # There should be 4 children: a.txt, b.txt, c.txt, d.txt
    self.assertEqual(len(children), 4)

    self.assertEqual("a.txt b.txt c.txt d.txt".split(),
                     sorted([child.urn.Basename() for child in children]))
