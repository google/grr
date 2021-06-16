#!/usr/bin/env python
"""Tests for clients with special approval logic."""

import os

from absl import app

from grr_api_client import errors as grr_api_errors
from grr_response_core.lib import utils
from grr_response_core.lib.util import compatibility
from grr_response_server.authorization import client_approval_auth
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_router_with_approval_checks
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui import webauth
from grr.test_lib import test_lib


class ApprovalByLabelE2ETest(api_integration_test_lib.ApiIntegrationTest):

  def TouchFile(self, client_id, path):
    gui_test_lib.CreateFileVersion(client_id=client_id, path=path)

  def setUp(self):
    super().setUp()

    self.client_nolabel_id = self.SetupClient(0)
    self.client_legal_id = self.SetupClient(1, labels=[u"legal_approval"])
    self.client_prod_id = self.SetupClient(
        2, labels=[u"legal_approval", u"prod_admin_approval"])

    cls = (api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks)
    cls.ClearCache()
    approver = test_lib.ConfigOverrider({
        "API.DefaultRouter":
            compatibility.GetName(cls),
        "ACL.approvers_config_file":
            os.path.join(self.base_path, "approvers.yaml")
    })
    approver.Start()
    self.addCleanup(approver.Stop)

    # Get a fresh approval manager object and reload with test approvers.
    approval_manager_stubber = utils.Stubber(
        client_approval_auth, "CLIENT_APPROVAL_AUTH_MGR",
        client_approval_auth.ClientApprovalAuthorizationManager())
    approval_manager_stubber.Start()
    self.addCleanup(approval_manager_stubber.Stop)

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.InitializeApiAuthManager()

  def testClientNoLabels(self):
    self.TouchFile(self.client_nolabel_id, "fs/os/foo")

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get)

    # approvers.yaml rules don't get checked because this client has no
    # labels. Regular approvals still required.
    self.RequestAndGrantClientApproval(
        self.client_nolabel_id, requestor=self.context.username)

    # Check we now have access
    self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get()

  def testClientApprovalSingleLabel(self):
    """Client requires an approval from a member of "legal_approval"."""
    self.TouchFile(self.client_legal_id, "fs/os/foo")

    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    approval_id = self.RequestAndGrantClientApproval(
        self.client_legal_id, requestor=self.context.username)
    # This approval isn't enough, we need one from legal, so it should still
    # fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_legal_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"legal1")

    # Check we now have access
    self.api.Client(self.client_legal_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabel(self):
    """Multi-label client approval test.

    This client requires one legal and two prod admin approvals. The requester
    must also be in the prod admin group.
    """
    self.TouchFile(self.client_prod_id, "fs/os/foo")

    self.context = api_call_context.ApiCallContext("prod1")
    webauth.WEBAUTH_MANAGER.SetUserName(self.context.username)

    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    approval_id = self.RequestAndGrantClientApproval(
        self.client_prod_id, requestor=self.context.username)

    # This approval from "approver" isn't enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"legal1")

    # We have "approver", "legal1": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the prod_admin_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"prod2")

    # We have "approver", "legal1", "prod2": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"prod3")

    # We have "approver", "legal1", "prod2", "prod3": we should have
    # access.
    self.api.Client(self.client_prod_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabelCheckRequester(self):
    """Requester must be listed as prod_admin_approval in approvals.yaml."""
    self.TouchFile(self.client_prod_id, "fs/os/foo")

    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant all the necessary approvals
    approval_id = self.RequestAndGrantClientApproval(
        self.client_prod_id, requestor=self.context.username)
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"legal1")
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"prod2")
    self.GrantClientApproval(
        self.client_prod_id,
        requestor=self.context.username,
        approval_id=approval_id,
        approver=u"prod3")

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
  app.run(main)
