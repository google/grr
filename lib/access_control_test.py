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

import time

from grr.client import conf
from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import registry
from grr.lib import test_lib
from grr.lib import utils

FLAGS = flags.FLAGS


class AccessControlTest(test_lib.GRRBaseTest):
  """Tests the access control mechanisms."""

  __metaclass__ = registry.MetaclassRegistry

  install_mock_acl = False

  def setUp(self):
    FLAGS.security_manager = "AccessControlManager"
    super(AccessControlTest, self).setUp()

  def CreateApproval(self, client_id, token):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    super_token = data_store.ACLToken()
    super_token.supervisor = True

    approval_request = aff4.FACTORY.Create(approval_urn, "Approval", mode="rw",
                                           token=super_token)
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver1"))
    approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver2"))
    approval_request.Close()

  def RevokeApproval(self, client_id, token, remove_from_cache=True):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

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

    for urn, mode in [("aff4:/flows", "rw"),
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
      # Force cache flush.
      fd._dirty = True
      self.assertRaises(data_store.UnauthorizedAccess, fd.Close)

    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open,
                      client_urn.Add("/fs"), None, mode)

  def testSupervisorToken(self):
    """Tests that the supervisor token overrides the approvals."""

    client_id = "C.%016X" % 0
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c")
    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    super_token = data_store.ACLToken()
    super_token.supervisor = True
    aff4.FACTORY.Open(urn, mode="rw", token=super_token)

  def testExpiredTokens(self):
    """Tests that expired tokens are rejected."""

    client_id = "C.%016X" % 0
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c")
    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn)

    old_time = time.time
    try:
      time.time = lambda: 100

      # Token expires in 5 seconds.
      super_token = data_store.ACLToken(expiry=105)
      super_token.supervisor = True

      # This should work since token is a super token.
      aff4.FACTORY.Open(urn, mode="rw", token=super_token)

      # Change the time to 200
      time.time = lambda: 200

      # Should be expired now.
      self.assertRaises(data_store.ExpiryError, aff4.FACTORY.Open, urn,
                        token=super_token, mode="rw")
    finally:
      time.time = old_time

  def testApprovalExpiry(self):
    """Tests that approvals expire after the correct time."""

    client_id = "C.%016X" % 1020
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c")
    token = data_store.ACLToken("test", "For testing")
    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      None, "rw", token)

    old_time = time.time
    try:
      time.time = lambda: 100.0
      self.CreateApproval(client_id, token)

      # This should work now.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

      # 3 weeks later.
      time.time = lambda: 100.0 + 3 * 7 * 24 * 60 * 60

      # This should still work.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

      # Getting close.
      time.time = lambda: 100.0 + 4 * 7 * 24 * 60 * 60 - 100.0

      # This should still work.
      aff4.FACTORY.Open(urn, mode="rw", token=token)

      # Over 4 weeks now.
      time.time = lambda: 100.0 + 4 * 7 * 24 * 60 * 60 + 100.0

      self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                        None, "rw", token)
    finally:
      time.time = old_time

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

    # And we can also access our labels.
    label_urn = urn.Add("test").Add("labels")
    labels = aff4.FACTORY.Open(label_urn, mode="rw", token=token)

    # But we cannot write to them.
    l = labels.Schema.LABEL()
    l.data.label.append("admin")
    labels.Set(labels.Schema.LABEL, l)
    self.assertRaises(data_store.UnauthorizedAccess, labels.Close)

  def testForemanAccess(self):
    """Test admin users can access the foreman."""
    token = data_store.ACLToken("test", "For testing")
    self.assertRaises(data_store.UnauthorizedAccess,
                      aff4.FACTORY.Open, "aff4:/foreman", token=token)

    # Make sure the user themselves can not create the labels object.
    fd = aff4.FACTORY.Create("aff4:/users/test/labels", "AFF4Object",
                             token=token)

    labels = fd.Schema.LABEL()
    labels.data.label.append("admin")
    fd.Set(labels)

    # The write will fail due to access denied!
    self.assertRaises(data_store.UnauthorizedAccess, fd.Close)

    # We need a supervisor to manipulate a user's ACL token:
    super_token = data_store.ACLToken()
    super_token.supervisor = True

    # Make the user an admin user now, this time with the supervisor token.
    fd = aff4.FACTORY.Create("aff4:/users/test/labels", "AFF4Object",
                             token=super_token)

    labels = fd.Schema.LABEL()
    labels.data.label.append("admin")
    fd.Set(labels)
    fd.Close()

    # Now we are allowed.
    aff4.FACTORY.Open("aff4:/foreman", token=token)

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

  def testBreakGlass(self):
    """Test the breakglass mechanism."""

    client_id = "C.%016X" % 0
    urn = aff4.ROOT_URN.Add(client_id).Add("/fs/os/c")

    self.assertRaises(data_store.UnauthorizedAccess, aff4.FACTORY.Open, urn,
                      token=self.token)

    # We expect to receive an email about this
    email = {}

    def SendEmail(to, from_user, subject, message, **_):
      email["to"] = to
      email["from_user"] = from_user
      email["subject"] = subject
      email["message"] = message

    old_email = email_alerts.SendEmail
    email_alerts.SendEmail = SendEmail

    try:
      flow.FACTORY.StartFlow(client_id, "BreakGlassGrantAccessFlow",
                             token=self.token, reason=self.token.reason)

      # Reset the emergency state of the token.
      self.token.is_emergency = False

      # This access is using the emergency_access granted, so we expect the
      # token to be tagged as such.
      aff4.FACTORY.Open(urn, token=self.token)

      self.assertEqual(email["to"], FLAGS.grr_emergency_email_address)
      self.assert_(self.token.username in email["message"])
      self.assertEqual(email["from_user"], self.token.username)
    finally:
      email_alerts.SendEmail = old_email

    # Make sure the token is tagged as an emergency token:
    self.assertEqual(self.token.is_emergency, True)


class AccessControlTestLoader(test_lib.GRRTestLoader):
  base_class = AccessControlTest


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=AccessControlTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
