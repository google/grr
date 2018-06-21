#!/usr/bin/env python
"""Tests for clients with special approval logic."""

import os


from grr_api_client import errors as grr_api_errors
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.authorization import client_approval_auth
from grr.server.grr_response_server.gui import api_auth_manager
from grr.server.grr_response_server.gui import api_call_router_with_approval_checks
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.server.grr_response_server.gui import gui_test_lib
from grr.server.grr_response_server.gui import webauth
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ApprovalByLabelE2ETest(api_e2e_test_lib.ApiE2ETest):

  def SetUpLegacy(self):
    # Set up clients and labels before we turn on the FullACM. We need to create
    # the client because to check labels the client needs to exist.
    client_nolabel, client_legal, client_prod = self.SetupClients(3)

    self.client_nolabel_id = client_nolabel.Basename()
    self.client_legal_id = client_legal.Basename()
    self.client_prod_id = client_prod.Basename()

    with aff4.FACTORY.Open(
        client_legal,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token) as client_obj:
      client_obj.AddLabel("legal_approval")

    with aff4.FACTORY.Open(
        client_prod,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token) as client_obj:
      client_obj.AddLabels(["legal_approval", "prod_admin_approval"])

  def SetUpRelationalDB(self):
    self.client_nolabel_id = self.SetupTestClientObject(0).client_id
    self.client_legal_id = self.SetupTestClientObject(
        1, labels=["legal_approval"]).client_id
    self.client_prod_id = self.SetupTestClientObject(
        2, labels=["legal_approval", "prod_admin_approval"]).client_id

  def TouchFile(self, client_id, path):
    gui_test_lib.CreateFileVersion(
        client_id=client_id, path=path, token=self.token)

  def setUp(self):
    super(ApprovalByLabelE2ETest, self).setUp()

    self.SetUpLegacy()
    if data_store.RelationalDBReadEnabled():
      self.SetUpRelationalDB()

    cls = (api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks)
    cls.ClearCache()
    self.approver = test_lib.ConfigOverrider({
        "API.DefaultRouter":
            cls.__name__,
        "ACL.approvers_config_file":
            os.path.join(self.base_path, "approvers.yaml")
    })
    self.approver.Start()

    # Get a fresh approval manager object and reload with test approvers.
    self.approval_manager_stubber = utils.Stubber(
        client_approval_auth, "CLIENT_APPROVAL_AUTH_MGR",
        client_approval_auth.ClientApprovalAuthorizationManager())
    self.approval_manager_stubber.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def tearDown(self):
    super(ApprovalByLabelE2ETest, self).tearDown()

    self.approval_manager_stubber.Stop()
    self.approver.Stop()

  def testClientNoLabels(self):
    self.TouchFile(rdf_client.ClientURN(self.client_nolabel_id), "fs/os/foo")

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get)

    # approvers.yaml rules don't get checked because this client has no
    # labels. Regular approvals still required.
    self.RequestAndGrantClientApproval(
        self.client_nolabel_id, requestor=self.token.username)

    # Check we now have access
    self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get()

  def testClientApprovalSingleLabel(self):
    """Client requires an approval from a member of "legal_approval"."""
    self.TouchFile(rdf_client.ClientURN(self.client_legal_id), "fs/os/foo")

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    approval_id = self.RequestAndGrantClientApproval(
        self.client_legal_id, requestor=self.token.username)
    # This approval isn't enough, we need one from legal, so it should still
    # fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_legal_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="legal1")

    # Check we now have access
    self.api.Client(self.client_legal_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabel(self):
    """Multi-label client approval test.

    This client requires one legal and two prod admin approvals. The requester
    must also be in the prod admin group.
    """
    self.TouchFile(rdf_client.ClientURN(self.client_prod_id), "fs/os/foo")

    self.token.username = "prod1"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    approval_id = self.RequestAndGrantClientApproval(
        self.client_prod_id, requestor=self.token.username)

    # This approval from "approver" isn't enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="legal1")

    # We have "approver", "legal1": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the prod_admin_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="prod2")

    # We have "approver", "legal1", "prod2": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3": we should have
    # access.
    self.api.Client(self.client_prod_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabelCheckRequester(self):
    """Requester must be listed as prod_admin_approval in approvals.yaml."""
    self.TouchFile(rdf_client.ClientURN(self.client_prod_id), "fs/os/foo")

    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant all the necessary approvals
    approval_id = self.RequestAndGrantClientApproval(
        self.client_prod_id, requestor=self.token.username)
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="legal1")
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="prod2")
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.token.username,
        approval_id=approval_id,
        approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3" approvals but because
    # "notprod" user isn't in prod_admin_approval and
    # requester_must_be_authorized is True it should still fail. This user can
    # never get a complete approval.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
