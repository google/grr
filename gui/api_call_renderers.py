#!/usr/bin/env python
"""Renderers for API calls (that can be bound to HTTP API, for example)."""



import logging


from grr.gui import api_auth_manager
from grr.gui import api_call_renderer_base
# pylint:disable=unused-import
# Import all api_plugins so they are available when we set up acls.
from grr.gui import api_plugins
# Import any local auth_managers.
from grr.gui import local_auth_managers
# pylint: enable=unused-import
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


class ApiCallAdditionalArgs(structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCallAdditionalArgs

  def GetArgsClass(self):
    return rdfvalue.RDFValue.classes[self.type]


# Set in APIACLInit
API_AUTH_MGR = None


class APIACLInit(registry.InitHook):
  pre = ["StatsInit"]

  def RunOnce(self):
    stats.STATS.RegisterCounterMetric("grr_api_auth_success",
                                      fields=[("renderer", str), ("user", str)])
    stats.STATS.RegisterCounterMetric("grr_api_auth_fail",
                                      fields=[("renderer", str), ("user", str)])

    global API_AUTH_MGR
    auth_mgr_cls = config_lib.CONFIG["API.AuthorizationManager"]
    logging.debug("Using API auth manager: %s", auth_mgr_cls)
    API_AUTH_MGR = api_auth_manager.SimpleAPIAuthorizationManager.classes[
        auth_mgr_cls]()

    # Quickly validate the list of renderers.
    for renderer in API_AUTH_MGR.ACLedRenderers():
      if renderer not in api_call_renderer_base.ApiCallRenderer.classes:
        raise ApiCallRendererNotFoundError(
            "%s not a valid renderer" % renderer)


def HandleApiCall(renderer, args, token=None):
  """Handles API call to a given renderers with given args and token."""

  if not hasattr(renderer, "Render"):
    renderer = api_call_renderer_base.ApiCallRenderer.classes[renderer]()

  # Privileged renderers bypass the approvals model to do things like check flow
  # status across multiple clients or add labels to clients. They provide
  # limited functionality and are responsible for their own checking.
  if renderer.privileged:
    token = token.SetUID()

  # Raises on access denied
  API_AUTH_MGR.CheckAccess(renderer, token.username)

  return renderer.Render(args, token=token)
