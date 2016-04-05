#!/usr/bin/env python
"""API Authorization Manager."""



import logging

from grr.gui import api_call_router
from grr.lib import config_lib
from grr.lib import registry
from grr.lib import stats
from grr.lib.authorization import auth_manager
from grr.lib.rdfvalues import structs
from grr.proto import api_pb2


class Error(Exception):
  """Base class for auth manager exception."""


class InvalidAPIAuthorization(Error):
  """Used when an invalid authorization is defined."""


class ApiCallRouterNotFoundError(Error):
  """Used when a router with a given name can't be found."""


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
  def router(self):
    return self.Get("router")

  @router.setter
  def router(self, value):
    self.Set("router", value)

  @property
  def key(self):
    return self.Get("router")


class APIAuthorizationManager(object):
  """Manages loading API authorizations and enforcing them."""

  def _CreateRouter(self, router_name):
    return api_call_router.ApiCallRouter.classes[router_name]()

  def Initialize(self):
    """Initializes the manager by reading the config file."""

    self.acled_routers = []
    self.auth_manager = auth_manager.AuthorizationManager()

    if config_lib.CONFIG["API.RouterACLConfigFile"]:
      logging.info("Using API router ACL config file: %s",
                   config_lib.CONFIG["API.RouterACLConfigFile"])

      reader = auth_manager.AuthorizationReader()
      with open(config_lib.CONFIG["API.RouterACLConfigFile"], mode="rb") as fh:
        reader.CreateAuthorizations(fh.read(), APIAuthorization)

        if not reader.GetAllAuthorizationObjects():
          raise InvalidAPIAuthorization("No entries added from "
                                        "RouterACLConfigFile.")

      for acl in reader.GetAllAuthorizationObjects():
        # Allow empty acls to act as DenyAll
        self.auth_manager.DenyAll(acl.router)

        for group in acl.groups:
          self.auth_manager.AuthorizeGroup(group, acl.router)

        for user in acl.users:
          self.auth_manager.AuthorizeUser(user, acl.router)

        self.acled_routers.append(acl.router)
        logging.info("Applied API ACL: %s, %s, to router: %s",
                     acl.users, acl.groups, acl.router)

    return self

  def GetRouterForUser(self, username):
    """Returns a router corresponding to a given username."""

    for acled_router in self.acled_routers:
      if self.auth_manager.CheckPermissions(username, acled_router):
        router = self._CreateRouter(acled_router)
        logging.debug("Matched router %s to user %s", router.__class__.__name__,
                      username)
        return router

    logging.debug("No router ACL rule match for user %s. Using default "
                  "router %s", username, config_lib.CONFIG["API.DefaultRouter"])
    return self._CreateRouter(config_lib.CONFIG["API.DefaultRouter"])

  def GetACLedRouters(self):
    return self.acled_routers


# Set in APIACLInit
API_AUTH_MGR = None


class APIACLInit(registry.InitHook):
  """Init hook that initializes API auth manager."""

  @staticmethod
  def InitApiAuthManager():
    global API_AUTH_MGR
    API_AUTH_MGR = APIAuthorizationManager().Initialize()

    stats.STATS.RegisterCounterMetric("grr_api_auth_success",
                                      fields=[("handler", str), ("user", str)])
    stats.STATS.RegisterCounterMetric("grr_api_auth_fail",
                                      fields=[("handler", str), ("user", str)])

    # Quickly validate the list of routers.
    for router in API_AUTH_MGR.GetACLedRouters():
      if router not in api_call_router.ApiCallRouter.classes:
        raise ApiCallRouterNotFoundError("%s not a valid router" % router)

  def RunOnce(self):
    allowed_contexts = ["AdminUI Context"]

    for ctx in allowed_contexts:
      if ctx in config_lib.CONFIG.context:
        self.InitApiAuthManager()
        return

    logging.debug("Not initializing API Authorization Manager, as it's not "
                  "supposed to be used by this component.")
