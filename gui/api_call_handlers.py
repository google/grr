#!/usr/bin/env python
"""Handlers for API calls (that can be bound to HTTP API, for example)."""



import logging


from grr.gui import api_auth_manager
from grr.gui import api_call_handler_base
# pylint:disable=unused-import
# Import all api_plugins so they are available when we set up acls.
from grr.gui import api_plugins
# pylint: enable=unused-import
from grr.gui import api_value_renderers
# pylint:disable=unused-import
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
  """Base class for API handlers exception."""


class ApiCallHandlerNotFoundError(Error):
  """Raised when no handler found for a given URL."""


class UnexpectedResultTypeError(Error):
  """Raised when handler returns type different from its result_type."""


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
                                      fields=[("handler", str), ("user", str)])
    stats.STATS.RegisterCounterMetric("grr_api_auth_fail",
                                      fields=[("handler", str), ("user", str)])

    global API_AUTH_MGR
    auth_mgr_cls = config_lib.CONFIG["API.AuthorizationManager"]
    logging.debug("Using API auth manager: %s", auth_mgr_cls)
    API_AUTH_MGR = api_auth_manager.SimpleAPIAuthorizationManager.classes[
        auth_mgr_cls]()

    # Quickly validate the list of handlers.
    for handler in API_AUTH_MGR.ACLedHandlers():
      if handler not in api_call_handler_base.ApiCallHandler.classes:
        raise ApiCallHandlerNotFoundError(
            "%s not a valid handler" % handler)


def HandleApiCall(handler, args, token=None):
  """Handles API call to a given handlers with given args and token."""

  if not hasattr(handler, "Render") and not hasattr(handler, "Handle"):
    handler = api_call_handler_base.ApiCallHandler.classes[handler]()

  # Privileged handlers bypass the approvals model to do things like check flow
  # status across multiple clients or add labels to clients. They provide
  # limited functionality and are responsible for their own checking.
  if handler.privileged:
    token = token.SetUID()

  # Raises on access denied
  API_AUTH_MGR.CheckAccess(handler, token.username)

  try:
    result = handler.Handle(args, token=token)
  except NotImplementedError:
    # Fall back to legacy Render() method if Handle() is not implemented.
    return handler.Render(args, token=token)

  expected_type = handler.result_type
  if expected_type is None:
    expected_type = None.__class__

  if result.__class__.__name__ != expected_type.__name__:
    raise UnexpectedResultTypeError("Expected %s, but got %s." % (
        expected_type.__name__, result.__class__.__name__))

  if result is None:
    return dict(status="OK")
  else:
    if handler.strip_json_root_fields_types:
      result_dict = {}
      for field, value in result.ListSetFields():
        if isinstance(field, (structs.ProtoDynamicEmbedded,
                              structs.ProtoEmbedded,
                              structs.ProtoList)):
          result_dict[field.name] = api_value_renderers.RenderValue(value)
        else:
          result_dict[field.name] = api_value_renderers.RenderValue(
              value)["value"]
    else:
      result_dict = api_value_renderers.RenderValue(result)

    return result_dict
