#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the registry flows."""

from grr.client import vfs
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.general import transfer


class TestRegistryFlows(test_lib.FlowTestsBaseclass):
  """Test the Run Key and MRU registry flows."""

  def testRegistryMRU(self):
    """Test that the MRU discovery flow. Flow is a work in Progress."""
    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture

    # Mock out the Find client action.
    client_mock = test_lib.ActionMock("Find")

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = fd.Schema.USER()
    users.Append(rdfvalue.User(
        username="testing", domain="testing-PC",
        homedir=r"C:\Users\testing", sid="S-1-5-21-2911950750-476812067-"
        "1487428992-1001"))
    fd.Set(users)
    fd.Close()

    # Run the flow in the emulated way.
    for _ in test_lib.TestFlowHelper("GetMRU", client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    # Check that the key was read.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add(
        "registry/HKEY_USERS/S-1-5-21-2911950750-476812067-1487428992-1001/"
        "Software/Microsoft/Windows/CurrentVersion/Explorer/"
        "ComDlg32/OpenSavePidlMRU/dd/0"), token=self.token)

    self.assertEqual(fd.__class__.__name__, "VFSFile")
    s = fd.Get(fd.Schema.STAT)
    # TODO(user): Make this test better when the MRU flow is complete.
    self.assertTrue(s.registry_data)

  def testCollectRunKeyBinaries(self):
    """Read Run key from the client_fixtures to test parsing and storage."""
    test_lib.ClientFixture(self.client_id, token=self.token)

    client = aff4.FACTORY.Open(self.client_id, token=self.token, mode="rw")
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(client.Schema.OS_VERSION("6.2"))
    client.Flush()

    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = test_lib.ClientRegistryVFSFixture
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.OS] = test_lib.ClientFullVFSFixture

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "HashBuffer", "HashFile", "ListDirectory")

    # Get KB initialized
    for _ in test_lib.TestFlowHelper(
        "KnowledgeBaseInitializationFlow", client_mock,
        client_id=self.client_id, token=self.token):
      pass

    with test_lib.Instrument(
        transfer.MultiGetFile, "Start") as getfile_instrument:
      # Run the flow in the emulated way.
      for _ in test_lib.TestFlowHelper(
          "CollectRunKeyBinaries", client_mock, client_id=self.client_id,
          token=self.token):
        pass

      # Check MultiGetFile got called for our runkey file
      download_requested = False
      for pathspec in getfile_instrument.args[0][0].args.pathspecs:
        if pathspec.path == u"C:\\Windows\\TEMP\\A.exe":
          download_requested = True
      self.assertTrue(download_requested)

