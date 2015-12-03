#!/usr/bin/env python
"""An API auth manager."""

import logging

import yaml

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import registry
from grr.lib import stats
from grr.lib.rdfvalues import structs
from grr.proto import api_pb2


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAPIAuthorization(Error):
  """Used when an invalid API ACL is defined."""


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


class APIAuthorizationImporter(object):
  """Load API Authorizations from YAML."""

  def __init__(self):
    self.acl_dict = {}

  def CreateACLs(self, yaml_data):
    try:
      raw_list = list(yaml.safe_load_all(yaml_data))
    except (ValueError, yaml.YAMLError) as e:
      raise InvalidAPIAuthorization("Invalid YAML: %s" % e)

    logging.debug("Adding %s acls", len(raw_list))
    for acl in raw_list:
      api_auth = APIAuthorization(**acl)
      if api_auth.handler in self.acl_dict:
        raise InvalidAPIAuthorization(
            "Duplicate ACLs for %s" % api_auth.handler)
      self.acl_dict[api_auth.handler] = api_auth

  def GetACLs(self):
    return self.acl_dict.values()

  def GetACLedHandlers(self):
    return self.acl_dict.keys()

  def LoadACLsFromFile(self):
    file_path = config_lib.CONFIG["API.HandlerACLFile"]
    if file_path:
      logging.info("Loading acls from %s", file_path)
      # Deliberately raise if this doesn't exist, we don't want silently ignored
      # ACLs.
      with open(file_path, mode="rb") as fh:
        self.CreateACLs(fh.read(1000000))


class APIAuthorizationManager(object):
  """Abstract API authorization manager class."""

  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

  def CheckAccess(self, handler_name, username):
    """Check access against ACL file, if defined.

    Args:
      handler_name: string, base name of handler class
      username: username string

    Raises:
      access_control.UnauthorizedAccess: if the handler is listed in the ACL
        file, but the user isn't authorized.
    """
    raise NotImplementedError("This requires subclassing.")


class SimpleAPIAuthorizationManager(APIAuthorizationManager):
  """Checks API usage against authorized users.

  This is a very simple implementation that we expect production installations
  to override. This manager can only authorize individual users because GRR has
  no concept of groups. The API authorization format supports groups, your class
  just needs to have a way to check membership in those groups that should query
  the canonical source for group membership in your environment (AD, LDAP etc.).
  """

  def __init__(self):
    self.auth_import = APIAuthorizationImporter()
    self.auth_import.LoadACLsFromFile()
    self.auth_dict = {}

    for acl in self.auth_import.GetACLs():
      if acl.groups:
        raise NotImplementedError(
            "GRR doesn't have in-built groups. Override this class with one "
            "that can resolve group membership in your environment.")

      user_set = self.auth_dict.setdefault(acl.handler, set())
      user_set.update(acl.users)

  def ACLedHandlers(self):
    """List of handlers which are mentioned in the ACL file."""
    return self.auth_import.GetACLedHandlers()

  def _CheckPermission(self, username, handler_name):
    """Apply ACLs for specific handlers if they exist."""
    if handler_name in self.auth_dict:
      return username in self.auth_dict[handler_name]
    return True

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
    if handler_name in self.ACLedHandlers():
      if not self._CheckPermission(username, handler_name):
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
