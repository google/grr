#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the registry flows."""

from grr.client import vfs
from grr.lib import aff4
from grr.lib import test_lib
from grr.proto import jobs_pb2


class ClientRegistryVFSFixture(test_lib.ClientVFSHandlerFixture):
  """Special client VFS mock that will emulate the registry."""
  prefix = "/registry"
  supported_pathtype = jobs_pb2.Path.REGISTRY


class TestRegistry(test_lib.FlowTestsBaseclass):
  """Test the registry flows."""

  def testResgistryMRU(self):
    """Test that the MRU discovery flow."""
    # Install the mock
    vfs.VFS_HANDLERS[jobs_pb2.Path.REGISTRY] = ClientRegistryVFSFixture

    # Mock out the Find client action.
    client_mock = test_lib.ActionMock("Find")

    # Add some user accounts to this client.
    fd = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    users = fd.Schema.USER()
    users.Append(jobs_pb2.UserAccount(
        username="testing", domain="testing-PC",
        homedir="C:\Users\testing", sid="S-1-5-21-2911950750-476812067-"
        "1487428992-1001"))
    fd.Set(users)
    fd.Close()

    # Run the flow in the emulated way.
    for _ in test_lib.TestFlowHelper(
        "FindMRU", client_mock, client_id=self.client_id,
        token=self.token):
      pass

    # Check that the key was read.
    fd = aff4.FACTORY.Open(aff4.RDFURN(self.client_id).Add(
        "registry/HKEY_USERS/S-1-5-21-2911950750-476812067-1487428992-1001/"
        "Software/Microsoft/Windows/CurrentVersion/Explorer/"
        "ComDlg32/OpenSavePidlMRU/dd/0"), token=self.token)

    self.assertEqual(fd.__class__.__name__, "VFSFile")
    s = fd.Get(fd.Schema.STAT)
    self.assert_(s.data.registry_data)
