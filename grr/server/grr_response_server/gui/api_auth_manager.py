#!/usr/bin/env python
"""API Authorization Manager."""

import io
import logging

from typing import Iterable, Text, Type

import yaml

from grr_response_core import config
from grr_response_core.lib.util import precondition
from grr_response_server.authorization import auth_manager
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_registry


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAPIAuthorization(Error):
  """Used when an invalid authorization is defined."""


class ApiCallRouterNotFoundError(Error):
  """Used when a router with a given name can't be found."""


class ApiCallRouterDoesNotExpectParameters(Error):
  """Raised when params are passed to a router that doesn't expect them."""


class APIAuthorization(object):
  """Authorization for users/groups to use an API handler."""

  def __init__(self):
    self.router_cls = None
    self.users = []
    self.groups = []
    self.router_params = {}

  @staticmethod
  def ParseYAMLAuthorizationsList(yaml_data):
    """Parses YAML data into a list of APIAuthorization objects."""
    try:
      raw_list = list(yaml.safe_load_all(yaml_data))
    except (ValueError, yaml.YAMLError) as e:
      raise InvalidAPIAuthorization("Invalid YAML: %s" % e)

    result = []
    for auth_src in raw_list:
      auth = APIAuthorization()
      auth.router_cls = _GetRouterClass(auth_src["router"])
      auth.users = auth_src.get("users", [])
      auth.groups = auth_src.get("groups", [])
      auth.router_params = auth_src.get("router_params", {})

      result.append(auth)

    return result


class APIAuthorizationManager(object):
  """Manages loading API authorizations and enforcing them."""

  def _CreateRouter(self, router_cls, params=None):
    """Creates a router with a given name and params."""
    if not router_cls.params_type and params:
      raise ApiCallRouterDoesNotExpectParameters("%s is not configurable" %
                                                 router_cls)

    rdf_params = None
    if router_cls.params_type:
      rdf_params = router_cls.params_type()
      if params:
        rdf_params.FromDict(params)

    return router_cls(params=rdf_params)

  def __init__(self, acl_list: Iterable[APIAuthorization],
               default_router_cls: Type[api_call_router.ApiCallRouter]):
    """Initializes the manager by reading the config file."""
    precondition.AssertIterableType(acl_list, APIAuthorization)

    self.routers = []
    self.auth_manager = auth_manager.AuthorizationManager()

    self.default_router = self._CreateRouter(default_router_cls)

    for index, acl in enumerate(acl_list):
      router = self._CreateRouter(acl.router_cls, params=acl.router_params)
      self.routers.append(router)

      router_id = str(index)
      self.auth_manager.DenyAll(router_id)

      for group in acl.groups:
        self.auth_manager.AuthorizeGroup(group, router_id)

      for user in acl.users:
        self.auth_manager.AuthorizeUser(user, router_id)

  @staticmethod
  def FromYaml(
      source: Text, default_router_cls: Type[api_call_router.ApiCallRouter]
  ) -> "APIAuthorizationManager":
    precondition.AssertType(source, Text)

    acl_list = APIAuthorization.ParseYAMLAuthorizationsList(source)
    return APIAuthorizationManager(acl_list, default_router_cls)

  def GetRouterForUser(self, username):
    """Returns a router corresponding to a given username."""

    for index, router in enumerate(self.routers):
      router_id = str(index)

      if self.auth_manager.CheckPermissions(username, router_id):
        logging.debug("Matched router %s to user %s", router.__class__.__name__,
                      username)
        return router

    logging.debug(
        "No router ACL rule match for user %s. Using default "
        "router %s", username, self.default_router.__class__.__name__)
    return self.default_router


# Set in InitializeApiAuthManager
API_AUTH_MGR = None


def InitializeApiAuthManager(default_router_cls=None):
  """Init hook that initializes API auth manager."""
  global API_AUTH_MGR

  if not default_router_cls:
    default_router_name = config.CONFIG["API.DefaultRouter"]
    default_router_cls = _GetRouterClass(default_router_name)

  filepath = config.CONFIG["API.RouterACLConfigFile"]
  if filepath:
    logging.info("Using API router ACL file: %s", filepath)
    with io.open(filepath, "r") as filedesc:
      API_AUTH_MGR = APIAuthorizationManager.FromYaml(filedesc.read(),
                                                      default_router_cls)
  else:
    API_AUTH_MGR = APIAuthorizationManager([], default_router_cls)


def _GetRouterClass(router_name: Text) -> Type[api_call_router.ApiCallRouter]:
  try:
    return api_call_router_registry.GetRouterClass(router_name)
  except KeyError:
    message = "Router '{}' does not exist".format(router_name)
    raise ApiCallRouterNotFoundError(message)
