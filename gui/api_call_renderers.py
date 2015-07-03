#!/usr/bin/env python
"""Renderers for API calls (that can be bound to HTTP API, for example)."""



import logging

import yaml

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib.rdfvalues import structs
from grr.proto import api_pb2


class Error(Exception):
  """Base class for API renderers exception."""


class ApiCallRendererNotFoundError(Error):
  """Raised when no renderer found for a given URL."""


class InvalidAPIAuthorization(Error):
  """Used when an invalid API ACL is defined."""


class ApiCallAdditionalArgs(structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCallAdditionalArgs

  def GetArgsClass(self):
    return rdfvalue.RDFValue.classes[self.type]


class ApiCallRenderer(object):
  """Baseclass for restful API renderers."""

  __metaclass__ = registry.MetaclassRegistry

  # RDFValue type used to handle API renderer arguments. This can be
  # a class object, an array of class objects or a function returning
  # either option.
  #
  # For GET renderers arguments will be passed via query parameters.
  # For POST renderers arguments will be passed via request payload.
  args_type = None

  # This is either a dictionary (key -> arguments class) of allowed additional
  # arguments types or a function returning this dictionary.
  #
  # addtional_args_types is only used when renderer's arguments RDFValue (
  # specified by args_type) has "additional_args" field of type
  # ApiCallAdditionalArgs.
  #
  # If this field is present, it will be filled with additional arguments
  # objects when the request is parsed. Keys of addtional_args_types
  # dictionary are used as prefixes when parsing the request.
  #
  # For example, if additional_args_types is
  # {"AFF4Object": ApiAFF4ObjectRendererArgs} and request has following key-
  # value pair set: "AFF4Object.limit_lists" -> 10, then
  # ApiAFF4ObjectRendererArgs(limit_lists=10) object will be created and put
  # into "additional_args" list of this renderer's arguments RDFValue.
  additional_args_types = {}

  # This is a maximum time in seconds the renderer is allowed to run. Renderers
  # exceeding this time are killed softly (i.e. the time is not a guaranteed
  # maximum, but will be used as a guide).
  max_execution_time = 60

  # privileged=True means that the renderer was designed to run in a privileged
  # context when no ACL checks are made. It means that this renderer makes
  # all the necessary ACL-related checks itself.
  #
  # NOTE: renderers with privileged=True have to be designed with extra caution
  # as they run without any ACL checks in place and can therefore cause the
  # system to be compromised.
  privileged = False

  # enabled_by_default=True means renderers are accessible by authenticated
  # users by default. Set this to False to disable a renderer and grant explicit
  # ACL'ed access in API.RendererACLFile.
  enabled_by_default = True

  def Render(self, args, token=None):
    raise NotImplementedError()


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
    if value not in ApiCallRenderer.classes:
      raise ApiCallRendererNotFoundError(
          "%s not a valid renderer" % self.renderer)
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
  __metaclass__ = registry.MetaclassRegistry

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


# Set in APIACLInit
API_AUTH_MGR = None


class APIACLInit(registry.InitHook):
  pre = ["StatsInit", "GuiPluginsInit"]

  def RunOnce(self):
    stats.STATS.RegisterCounterMetric("grr_api_auth_success",
                                      fields=[("renderer", str), ("user", str)])
    stats.STATS.RegisterCounterMetric("grr_api_auth_fail",
                                      fields=[("renderer", str), ("user", str)])

    global API_AUTH_MGR
    API_AUTH_MGR = SimpleAPIAuthorizationManager.classes[
        config_lib.CONFIG["API.AuthorizationManager"]]()


def HandleApiCall(renderer, args, token=None):
  """Handles API call to a given renderers with given args and token."""

  if not hasattr(renderer, "Render"):
    renderer = ApiCallRenderer.classes[renderer]

  if renderer.privileged:
    token = token.SetUID()

  # Raises on access denied
  API_AUTH_MGR.CheckAccess(renderer, token.username)

  return renderer.Render(args, token=token)

