#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the registry flows."""

from grr.client import vfs
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class ClientRegistryVFSFixture(test_lib.ClientVFSHandlerFixture):
  """Special client VFS mock that will emulate the registry."""
  prefix = "/registry"
  supported_pathtype = rdfvalue.PathSpec.PathType.REGISTRY


class TestRegistry(test_lib.FlowTestsBaseclass):
  """Test the Run Key and MRU registry flows."""

  def testRegistryMRU(self):
    """Test that the MRU discovery flow. Flow is a work in Progress."""
    # Install the mock
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = ClientRegistryVFSFixture

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
    for _ in test_lib.TestFlowHelper("FindMRU", client_mock,
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

  def testRegistryRunKeys(self):
    """Read Run key from the client_fixtures to test parsing and storage."""
    # Install the mock.
    vfs.VFS_HANDLERS[
        rdfvalue.PathSpec.PathType.REGISTRY] = ClientRegistryVFSFixture

    # Mock out the Find client action.
    client_mock = test_lib.ActionMock("Find")

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = fd.Schema.USER()
    users.Append(rdfvalue.User(
        username="LocalService", domain="testing-PC",
        homedir=r"C:\Users\localservice", sid="S-1-5-20"))
    fd.Set(users)
    fd.Close()

    # Run the flow in the emulated way.
    for _ in test_lib.TestFlowHelper(
        "CollectRunKeys", client_mock, client_id=self.client_id,
        token=self.token):
      pass

    # Check that the key was read.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id)
                           .Add("registry/HKEY_USERS/S-1-5-20/Software/"
                                "Microsoft/Windows/CurrentVersion/Run/Sidebar"),
                           token=self.token)

    self.assertEqual(fd.__class__.__name__, "VFSFile")
    s = fd.Get(fd.Schema.STAT)
    self.assertTrue(s.registry_data)

    # Check that the key made it into the Analysis.
    fd = aff4.FACTORY.Open(rdfvalue.RDFURN(self.client_id).Add(
        "analysis/RunKeys/LocalService/Run"), token=self.token)
    self.assertEqual(fd.__class__.__name__, "RDFValueCollection")
    runkeys = list(fd)
    # And that they all have data in them.
    self.assertEqual(runkeys[0].keyname,
                     "/HKEY_USERS/S-1-5-20/Software/Microsoft/"
                     "Windows/CurrentVersion/Run/Sidebar")
    self.assertEqual(runkeys[0].lastwritten, 1247546054L)
    self.assertEqual(runkeys[0].filepath,
                     "%%ProgramFiles%%/Windows Sidebar/Sidebar.exe /autoRun")
