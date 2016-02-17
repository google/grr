#!/usr/bin/env python
"""API Authorization Manager."""



import logging


from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import stats
from grr.lib.authorization import auth_manager
from grr.lib.rdfvalues import structs
from grr.proto import api_pb2


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAPIAuthorization(Error):
  """Used when an invalid authorization is defined."""


class APIAuthorization(structs.RDFProtoStruct):
  """Authorization for users/groups to use an API handler."""
  protobuf = api_pb2.ApiAuthorization

  @property
  def users(self):
    return self.Get("users")

  @users.setter
  def users(self, value):
    if not isinstance(value, list):
      raise InvalidAPIAuthorization("users must be a list")
    self.Set("users", value)

  @property
  def groups(self):
    return self.Get("groups")

  @groups.setter
  def groups(self, value):
    if not isinstance(value, list):
      raise InvalidAPIAuthorization("groups must be a list")
    self.Set("groups", value)

  @property
  def handler(self):
    return self.Get("handler")

  @handler.setter
  def handler(self, value):
    self.Set("handler", value)

  @property
  def key(self):
    return self.Get("handler")


class APIAuthorizationManager(auth_manager.AuthorizationManager):
  """Manages loading API authorizations and enforcing them."""

  def Initialize(self):
    self.api_groups = config_lib.CONFIG["API.access_groups"]
    self.api_access = config_lib.CONFIG["API.access_groups_label"]
    self.acled_handlers = []

    # Authorize the groups that have general access to the API
    logging.info("Authorizing groups %s for API access %s", self.api_groups,
                 self.api_access)
    for group in self.api_groups:
      self.AuthorizeGroup(group, self.api_access)

    if config_lib.CONFIG["API.HandlerACLFile"]:
      with open(config_lib.CONFIG["API.HandlerACLFile"], mode="rb") as fh:
        self.CreateAuthorizations(fh.read(), APIAuthorization)

        if not self.GetAllAuthorizationObjects():
          raise InvalidAPIAuthorization("No entries added from HandlerACLFile.")

      for acl in self.GetAllAuthorizationObjects():
        # Allow empty acls to act as DenyAll
        self.DenyAll(acl.handler)

        for group in acl.groups:
          self.AuthorizeGroup(group, acl.handler)

        for user in acl.users:
          self.AuthorizeUser(user, acl.handler)

        self.acled_handlers.append(acl.handler)

  def CheckAccess(self, handler, username):
    """Check access against ACL file, if defined.

    Args:
      handler: handler class object
      username: username string

    Raises:
      access_control.UnauthorizedAccess: If the handler is listed in the ACL
      file, but the user isn't authorized. Or if enabled_by_default=False and no
      ACL applies.
    """
    handler_name = handler.__class__.__name__

    if (self.api_groups and
        not self.CheckPermissions(username, self.api_access)):
      stats.STATS.IncrementCounter("grr_api_auth_fail",
                                   fields=[handler_name, username])
      raise access_control.UnauthorizedAccess(
          "User %s not in groups %s, authorized for %s API access." % (
              username, self.api_groups, self.api_access))

    if handler_name in self.ACLedHandlers():
      if not self.CheckPermissions(username, handler_name):
        stats.STATS.IncrementCounter("grr_api_auth_fail",
                                     fields=[handler_name, username])
        raise access_control.UnauthorizedAccess(
            "User %s not authorized for handler %s." % (
                username, handler_name))
    elif not handler.enabled_by_default:
      raise access_control.UnauthorizedAccess(
          "%s has enabled_by_default=False and no explicit ACL set. Add ACL"
          " to ACL list (see API.HandlerACLFile config option) to use "
          "this API" % handler)

    logging.debug("Authorizing %s for API %s", username, handler_name)
    stats.STATS.IncrementCounter("grr_api_auth_success",
                                 fields=[handler_name, username])

  def ACLedHandlers(self):
    return self.acled_handlers

