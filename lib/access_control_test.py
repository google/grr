#!/usr/bin/env python

# Copyright 2012 Google Inc.
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

"""Tests for the access control mechanisms."""


from grr.client import conf
from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils

FLAGS = flags.FLAGS


class AccessControlTest(test_lib.GRRBaseTest):
  """Tests the access control mechanisms."""

  __metaclass__ = registry.MetaclassRegistry

  install_mock_acl = False

  def CreateApproval(self, client_id, token):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(token.reason)

    super_token = data_store.ACLToken()
    super_token.supervisor = True

    approval_request = aff4.FACTORY.Create(approval_urn, "Approval", mode="rw",
                                           token=super_token)
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver1"))
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver2"))
    approval_request.Close()

  def RevokeApproval(self, client_id, token, remove_from_cache=True):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(token.reason)

    super_token = data_store.ACLToken()
    super_token.supervisor = True

    approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                         token=super_token)
    approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
    approval_request.Close()

    if remove_from_cache:
      data_store.DB.security_manager.acl_cache.ExpireObject(
          utils.SmartUnicode(approval_urn))

  def testSimpleAccess(self):
    """Tests that simple access does not need any token."""

    client_id = "C.%016X" % 0
    client_urn = aff4.ROOT_URN.Add(client_id)

    for urn, mode in [("aff4:/foreman", "rw"),
                      ("aff4:/flows", "rw"),
                      ("aff4:/ACL", "r"),
                      ("aff4:/config/drivers", "r"),
                      ("aff4:/", "rw"),
                      (client_urn, "r")]:
      fd = aff4.FACTORY.Open(urn, mode=mode)
      fd.Close()

    # Those should raise.
    for urn, mode in [("aff4:/ACL", "rw"),
                      (client_urn, "rw")]:
      fd = aff4.FACTORY.Open(urn, mode=mode)
      self.assertRaises(data_store.UnauthorizedAccess, fd.Close)

    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open,
                      client_urn.Add("/fs"), None, mode)

  def testSuperVisorToken(self):
    """Tests that the supervisor token overrides the approvals."""

    client_id = "C.%016X" % 0
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c")
    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    super_token = data_store.ACLToken()
    super_token.supervisor = True
    aff4.FACTORY.Open(urn, mode="rw", token=super_token)

  def testApproval(self):
    """Tests that we can create an approval object to access clients."""

    client_id = "C.%016X" % 0
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs")
    token = data_store.ACLToken("test", "For testing")

    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      None, "rw", token=token)

    self.CreateApproval(client_id, token)

    fd = aff4.FACTORY.Open(urn, None, "rw", token=token)
    fd.Close()

    self.RevokeApproval(client_id, token)

    self.assertRaises(data_store.UnauthorizedAccess,
                      aff4.FACTORY.Open, urn, None, "rw", token=token)

  def testUserAccess(self):
    """Tests access to user objects."""
    token = data_store.ACLToken("test", "For testing")
    urn = aff4.ROOT_URN.Add("users")
    # We cannot open any user account.
    self.assertRaises(data_store.UnauthorizedAccess,
                      aff4.FACTORY.Open, urn.Add("some_user"), None, "rw",
                      False, token)
    # But we can open our own.
    aff4.FACTORY.Open(urn.Add("test"), mode="rw", token=token)

  def testFlowAccess(self):
    """Tests access to flows."""
    token = data_store.ACLToken("test", "For testing")
    client_id = "C." + "A" * 16

    self.assertRaises(data_store.UnauthorizedAccess, flow.FACTORY.StartFlow,
                      client_id, "SendingFlow", message_count=1, token=token)

    self.CreateApproval(client_id, token)
    sid = flow.FACTORY.StartFlow(client_id, "SendingFlow", message_count=1,
                                 token=token)

    self.RevokeApproval(client_id, token)

    self.assertRaises(data_store.UnauthorizedAccess,
                      flow.FACTORY.FetchFlow, sid, token=token)

    self.CreateApproval(client_id, token)

    flow.FACTORY.FetchFlow(sid, token=token)

  def testCaches(self):
    """Makes sure that results are cached in the security manager."""

    token = data_store.ACLToken("test", "For testing")
    client_id = "C." + "B" * 16

    self.CreateApproval(client_id, token)
    sid = flow.FACTORY.StartFlow(client_id, "SendingFlow", message_count=1,
                                 token=token)

    # Fill all the caches.
    flow.FACTORY.FetchFlow(sid, lock=False, token=token)

    flow_factory = flow.FACTORY
    aff4_factory = aff4.FACTORY

    # Disable flow to client_id resolution.
    flow.FACTORY = None
    # Disable reading of approval objects.
    aff4.FACTORY = None

    # If this doesn't raise now, all answers were cached.
    flow_factory.FetchFlow(sid, lock=False, token=token)

    flow.FACTORY = flow_factory
    aff4.FACTORY = aff4_factory


class AccessControlTestLoader(test_lib.GRRTestLoader):
  base_class = AccessControlTest


def main(argv):
  FLAGS.security_manager = "AccessControlManager"
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AccessControlTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
