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
  """Authorization for users/groups to use an API renderer."""
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
  def renderer(self):
    return self.Get("renderer")

  @renderer.setter
  def renderer(self, value):
    self.Set("renderer", value)


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
      if api_auth.renderer in self.acl_dict:
        raise InvalidAPIAuthorization(
            "Duplicate ACLs for %s" % api_auth.renderer)
      self.acl_dict[api_auth.renderer] = api_auth

  def GetACLs(self):
    return self.acl_dict.values()

  def GetACLedRenderers(self):
    return self.acl_dict.keys()

  def LoadACLsFromFile(self):
    file_path = config_lib.CONFIG["API.RendererACLFile"]
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

  def CheckAccess(self, renderer_name, username):
    """Check access against ACL file, if defined.

    Args:
      renderer_name: string, base name of renderer class
      username: username string

    Raises:
      access_control.UnauthorizedAccess: if the renderer is listed in the ACL
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

      user_set = self.auth_dict.setdefault(acl.renderer, set())
      user_set.update(acl.users)

  def ACLedRenderers(self):
    """List of renderers which are mentioned in the ACL file."""
    return self.auth_import.GetACLedRenderers()

  def _CheckPermission(self, username, renderer_name):
    """Apply ACLs for specific renderers if they exist."""
    if renderer_name in self.auth_dict:
      return username in self.auth_dict[renderer_name]
    return True

  def CheckAccess(self, renderer, username):
    """Check access against ACL file, if defined.

    Args:
      renderer: renderer class object
      username: username string

    Raises:
      access_control.UnauthorizedAccess: If the renderer is listed in the ACL
      file, but the user isn't authorized. Or if enabled_by_default=False and no
      ACL applies.
    """
    renderer_name = renderer.__class__.__name__
    if renderer_name in self.ACLedRenderers():
      if not self._CheckPermission(username, renderer_name):
        stats.STATS.IncrementCounter("grr_api_auth_fail",
                                     fields=[renderer_name, username])
        raise access_control.UnauthorizedAccess(
            "User %s not authorized for renderer %s." % (
                username, renderer_name))
    elif not renderer.enabled_by_default:
      raise access_control.UnauthorizedAccess(
          "%s has enabled_by_default=False and no explicit ACL set. Add ACL"
          " to ACL list (see API.RendererACLFile config option) to use "
          "this API" % renderer)

    logging.debug("Authorizing %s for API %s", username, renderer_name)
    stats.STATS.IncrementCounter("grr_api_auth_success",
                                 fields=[renderer_name, username])
