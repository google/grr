#!/usr/bin/env python
"""Tests for grr.server.authorization.client_approval_auth."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import access_control
from grr_response_server.authorization import client_approval_auth
from grr.test_lib import test_lib


class ClientApprovalAuthorizationTest(rdf_test_base.RDFValueTestMixin,
                                      test_lib.GRRBaseTest):
  rdfvalue_class = client_approval_auth.ClientApprovalAuthorization

  def setUp(self):
    super(ClientApprovalAuthorizationTest, self).setUp()
    self.urn = rdf_client.ClientURN("C.0000000000000000")

  def GenerateSample(self, number=0):
    return client_approval_auth.ClientApprovalAuthorization(
        label="label%d" % number, users=["test", "test2"])

  def testApprovalValidation(self):
    # String instead of list of users
    with self.assertRaises(
        client_approval_auth.ErrorInvalidClientApprovalAuthorization):
      client_approval_auth.ClientApprovalAuthorization(
          label="label", users="test")

    # Missing label
    acl = client_approval_auth.ClientApprovalAuthorization(users=["test"])
    with self.assertRaises(
        client_approval_auth.ErrorInvalidClientApprovalAuthorization):
      print(acl.label)

    # Bad label
    with self.assertRaises(
        client_approval_auth.ErrorInvalidClientApprovalAuthorization):
      acl.label = None


class ClientApprovalAuthorizationManager(test_lib.GRRBaseTest):

  def setUp(self):
    super(ClientApprovalAuthorizationManager, self).setUp()
    self.mgr = client_approval_auth.ClientApprovalAuthorizationManager()
    self.urn = rdf_client.ClientURN("C.0000000000000000")

  def _CreateAuthSingleLabel(self):
    self.mgr.LoadApprovals(yaml_data="""label: "label1"
users:
  - one
  - two
""")

  def _CreateAuthCheckRequester(self):
    self.mgr.LoadApprovals(yaml_data="""label: "label1"
requester_must_be_authorized: True
users:
  - one
  - two
""")

  def _CreateAuthMultiApproval(self):
    self.mgr.LoadApprovals(yaml_data="""label: "label1"
requester_must_be_authorized: True
num_approvers_required: 2
users:
  - one
  - two
  - three
  - four
""")

  def testRaisesOnNoApprovals(self):
    self._CreateAuthSingleLabel()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "requester_user",
                                      [], "label1")

  def testRaisesOnSelfApproval(self):
    self._CreateAuthSingleLabel()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "requester_user",
                                      ["requester_user"], "label1")

  def testRaisesOnAuthorizedSelfApproval(self):
    self._CreateAuthSingleLabel()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "one", ["one"],
                                      "label1")

  def testRaisesOnApprovalFromUnauthorized(self):
    self._CreateAuthSingleLabel()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "requester_user",
                                      ["approver1"], "label1")

  def testPassesWithApprovalFromApprovedUser(self):
    self._CreateAuthSingleLabel()
    self.mgr.CheckApproversForLabel(self.token, self.urn, "requester_user",
                                    ["approver1", "two"], "label1")

  def testRaisesWhenRequesterNotAuthorized(self):
    self._CreateAuthCheckRequester()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "requester_user",
                                      ["one"], "label1")

  def testRaisesOnSelfApprovalByAuthorizedRequester(self):
    self._CreateAuthCheckRequester()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "one", ["one"],
                                      "label1")

  def testPassesWhenApproverAndRequesterAuthorized(self):
    self._CreateAuthCheckRequester()
    self.mgr.CheckApproversForLabel(self.token, self.urn, "one", ["one", "two"],
                                    "label1")

  def testRaisesWhenOnlyOneAuthorizedApprover(self):
    self._CreateAuthMultiApproval()
    with self.assertRaises(access_control.UnauthorizedAccess):
      self.mgr.CheckApproversForLabel(self.token, self.urn, "one",
                                      ["one", "two"], "label1")

  def testPassesWithTwoAuthorizedApprovers(self):
    self._CreateAuthMultiApproval()
    self.mgr.CheckApproversForLabel(self.token, self.urn, "one",
                                    ["two", "four"], "label1")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
