#!/usr/bin/env python
"""Client label approvals authorization manager."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import string_types

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import acls_pb2

from grr_response_server import access_control
from grr_response_server.authorization import auth_manager


class Error(Exception):
  """Base class for user manager exception."""


class ErrorInvalidClientApprovalAuthorization(Error):
  """Used when an invalid ClientApprovalAuthorization is defined."""


class ErrorInvalidApprovers(Error):
  """Raised when approvers.yaml is invalid."""


class ErrorInvalidApprovalSpec(Error):
  """Raised when approval spec in approvers.yaml is invalid."""


class ClientApprovalAuthorization(rdf_structs.RDFProtoStruct):
  """Authorization to approve clients with a particular label."""
  protobuf = acls_pb2.ClientApprovalAuthorization

  @property
  def label(self):
    label = self.Get("label")
    if not label:
      raise ErrorInvalidClientApprovalAuthorization(
          "label string cannot be empty")
    return label

  @label.setter
  def label(self, value):
    if not isinstance(value, string_types) or not value:
      raise ErrorInvalidClientApprovalAuthorization(
          "label must be a non-empty string")
    self.Set("label", value)

  @property
  def users(self):
    return self.Get("users")

  @users.setter
  def users(self, value):
    if not isinstance(value, list):
      raise ErrorInvalidClientApprovalAuthorization("users must be a list")
    self.Set("users", value)

  @property
  def groups(self):
    return self.Get("groups")

  @groups.setter
  def groups(self, value):
    if not isinstance(value, list):
      raise ErrorInvalidClientApprovalAuthorization("groups must be a list")
    self.Set("groups", value)

  @property
  def key(self):
    return self.Get("label")


class ClientApprovalAuthorizationManager(auth_manager.AuthorizationManager):
  """Manage client label approvers from approvers.yaml."""

  def Initialize(self):
    self.LoadApprovals()

  def IsActive(self):
    """Does this manager have any rules loaded?"""
    return bool(self.reader.auth_objects)

  def LoadApprovals(self, yaml_data=None):
    self.reader = auth_manager.AuthorizationReader()

    # Clear out any previous approvals
    if yaml_data:
      self.reader.CreateAuthorizations(yaml_data, ClientApprovalAuthorization)
    else:
      with open(config.CONFIG["ACL.approvers_config_file"], mode="rb") as fh:
        self.reader.CreateAuthorizations(fh.read(), ClientApprovalAuthorization)

    for approval_spec in self.reader.GetAllAuthorizationObjects():
      for group in approval_spec.groups:
        self.AuthorizeGroup(group, approval_spec.label)

      for user in approval_spec.users:
        self.AuthorizeUser(user, approval_spec.label)

  def CheckApproversForLabel(self, token, client_urn, requester, approvers,
                             label):
    """Checks if requester and approvers have approval privileges for labels.

    Checks against list of approvers for each label defined in approvers.yaml to
    determine if the list of approvers is sufficient.

    Args:
      token: user token
      client_urn: ClientURN object of the client
      requester: username string of person requesting approval.
      approvers: list of username strings that have approved this client.
      label: label strings to check approval privs for.
    Returns:
      True if access is allowed, raises otherwise.
    """
    auth = self.reader.GetAuthorizationForSubject(label)
    if not auth:
      # This label isn't listed in approvers.yaml
      return True

    if auth.requester_must_be_authorized:
      if not self.CheckPermissions(requester, label):
        raise access_control.UnauthorizedAccess(
            "User %s not in %s or groups:%s for %s" % (requester, auth.users,
                                                       auth.groups, label),
            subject=client_urn,
            requested_access=token.requested_access)

    approved_count = 0
    for approver in approvers:
      if self.CheckPermissions(approver, label) and approver != requester:
        approved_count += 1

    if approved_count < auth.num_approvers_required:
      raise access_control.UnauthorizedAccess(
          "Found %s approvers for %s, needed %s" %
          (approved_count, label, auth.num_approvers_required),
          subject=client_urn,
          requested_access=token.requested_access)
    return True


CLIENT_APPROVAL_AUTH_MGR = None


class ClientApprovalAuthorizationInit(registry.InitHook):

  def RunOnce(self):
    global CLIENT_APPROVAL_AUTH_MGR
    CLIENT_APPROVAL_AUTH_MGR = ClientApprovalAuthorizationManager()
