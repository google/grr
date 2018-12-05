#!/usr/bin/env python
"""HTTP API logic that ties API call handlers with HTTP routes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import json
import logging
import time
import traceback


from future.moves.urllib import parse as urlparse
from future.utils import iteritems
from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing
from werkzeug import wrappers as werkzeug_wrappers

from google.protobuf import json_format

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_value_renderers


class Error(Exception):
  pass


class PostRequestParsingError(Error):
  pass


class UnsupportedHttpMethod(Error):
  pass


class AdditionalArgsProcessingError(Error):
  pass


class UnexpectedResultTypeError(Error):
  pass


class ApiCallRouterNotFoundError(Error):
  pass


class RouterMatcher(object):
  """Matches requests to routers (and caches them)."""

  def __init__(self):
    self._routing_maps_cache = utils.FastStore()

  def _BuildHttpRoutingMap(self, router_cls):
    """Builds a werkzeug routing map out of a given router class."""

    if not issubclass(router_cls, api_call_router.ApiCallRouter):
      raise ValueError("Router has to be an instance of ApiCallRouter.")

    routing_map = routing.Map()
    # Note: we traverse methods of the base class (ApiCallRouter) to avoid
    # potential problems caused by child router classes using the @Http
    # annotation (thus adding additional unforeseen HTTP paths/methods). We
    # don't want the HTTP API to depend on a particular router implementation.
    for _, metadata in iteritems(router_cls.GetAnnotatedMethods()):
      for http_method, path, unused_options in metadata.http_methods:
        routing_map.add(
            routing.Rule(path, methods=[http_method], endpoint=metadata))
        # This adds support for the next version of the API that uses
        # standartized JSON protobuf serialization.
        routing_map.add(
            routing.Rule(
                path.replace("/api/", "/api/v2/"),
                methods=[http_method],
                endpoint=metadata))

    return routing_map

  def _GetRoutingMap(self, router):
    """Returns a routing map for a given router instance."""

    try:
      routing_map = self._routing_maps_cache.Get(router.__class__)
    except KeyError:
      routing_map = self._BuildHttpRoutingMap(router.__class__)
      self._routing_maps_cache.Put(router.__class__, routing_map)

    return routing_map

  def _SetField(self, args, type_info, value):
    """Sets fields on the arg rdfvalue object."""
    if hasattr(type_info, "enum"):
      try:
        coerced_obj = type_info.enum[value.upper()]
      except KeyError:
        # A bool is an enum but serializes to "1" / "0" which are both not in
        # enum or reverse_enum.
        coerced_obj = type_info.type.FromHumanReadable(value)
    else:
      coerced_obj = type_info.type.FromHumanReadable(value)
    args.Set(type_info.name, coerced_obj)

  def _GetArgsFromRequest(self, request, method_metadata, route_args):
    """Builds args struct out of HTTP request."""
    format_mode = GetRequestFormatMode(request, method_metadata)

    if request.method in ["GET", "HEAD"]:
      if method_metadata.args_type:
        unprocessed_request = request.args
        if hasattr(unprocessed_request, "dict"):
          unprocessed_request = unprocessed_request.dict()

        args = method_metadata.args_type()
        for type_info in args.type_infos:
          if type_info.name in route_args:
            self._SetField(args, type_info, route_args[type_info.name])
          elif type_info.name in unprocessed_request:
            self._SetField(args, type_info, unprocessed_request[type_info.name])

      else:
        args = None
    elif request.method in ["POST", "DELETE", "PATCH"]:
      try:
        args = method_metadata.args_type()
        for type_info in args.type_infos:
          if type_info.name in route_args:
            self._SetField(args, type_info, route_args[type_info.name])

        if request.content_type and request.content_type.startswith(
            "multipart/form-data;"):
          payload = json.loads(request.form["_params_"])
          args.FromDict(payload)

          for name, fd in iteritems(request.files):
            args.Set(name, fd.read())
        elif format_mode == JsonMode.PROTO3_JSON_MODE:
          # NOTE: Arguments rdfvalue has to be a protobuf-based RDFValue.
          args_proto = args.protobuf()
          json_format.Parse(request.get_data(as_text=True) or "{}", args_proto)
          args.ParseFromString(args_proto.SerializeToString())
        else:
          payload = json.loads(request.get_data(as_text=True) or "{}")
          if payload:
            args.FromDict(payload)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Error while parsing POST request %s (%s): %s",
                          request.path, request.method, e)
        raise PostRequestParsingError(e)
    else:
      raise UnsupportedHttpMethod("Unsupported method: %s." % request.method)

    return args

  def MatchRouter(self, request):
    """Returns a router for a given HTTP request."""
    router = api_auth_manager.API_AUTH_MGR.GetRouterForUser(request.user)
    routing_map = self._GetRoutingMap(router)

    matcher = routing_map.bind("%s:%s" % (request.environ["SERVER_NAME"],
                                          request.environ["SERVER_PORT"]))
    try:
      match = matcher.match(request.path, request.method)
    except werkzeug_exceptions.NotFound:
      raise ApiCallRouterNotFoundError("No API router was found for (%s) %s" %
                                       (request.path, request.method))

    router_method_metadata, route_args_dict = match
    return (router, router_method_metadata,
            self._GetArgsFromRequest(request, router_method_metadata,
                                     route_args_dict))


class JSONEncoderWithRDFPrimitivesSupport(json.JSONEncoder):
  """Custom JSON encoder that encodes handlers output.

  Custom encoder is required to facilitate usage of primitive values -
  booleans, integers and strings - in handlers responses.

  If handler references an RDFString, RDFInteger or and RDFBOol when building a
  response, it will lead to JSON encoding failure when response encoded,
  unless this custom encoder is used. Another way to solve this issue would be
  to explicitly call api_value_renderers.RenderValue on every value returned
  from the renderer, but it will make the code look overly verbose and dirty.
  """

  def default(self, obj):
    if isinstance(obj,
                  (rdfvalue.RDFInteger, rdfvalue.RDFBool, rdfvalue.RDFString)):
      return obj.SerializeToDataStore()

    return json.JSONEncoder.default(self, obj)


class JsonMode(object):
  """Enum class for various JSON encoding modes."""
  PROTO3_JSON_MODE = 0
  GRR_JSON_MODE = 1
  GRR_ROOT_TYPES_STRIPPED_JSON_MODE = 2
  GRR_TYPE_STRIPPED_JSON_MODE = 3


def GetRequestFormatMode(request, method_metadata):
  """Returns JSON format mode corresponding to a given request and method."""
  if request.path.startswith("/api/v2/"):
    return JsonMode.PROTO3_JSON_MODE

  if request.args.get("strip_type_info", ""):
    return JsonMode.GRR_TYPE_STRIPPED_JSON_MODE

  for http_method, unused_url, options in method_metadata.http_methods:
    if (http_method == request.method and
        options.get("strip_root_types", False)):
      return JsonMode.GRR_ROOT_TYPES_STRIPPED_JSON_MODE

  return JsonMode.GRR_JSON_MODE


class HttpRequestHandler(object):
  """Handles HTTP requests."""

  @staticmethod
  def BuildToken(request, execution_time):
    """Build an ACLToken from the request."""

    # The request.args dictionary will also be filled on HEAD calls.
    if request.method in ["GET", "HEAD"]:
      reason = request.args.get("reason", "")
    elif request.method in ["POST", "DELETE", "PATCH"]:
      # The header X-GRR-Reason is set in api-service.js.
      reason = utils.SmartUnicode(
          urlparse.unquote(request.headers.get("X-Grr-Reason", "")))

    # We assume that request.user contains the username that we can trust.
    # No matter what authentication method is used, the WebAuthManager is
    # responsible for authenticating the userand setting request.user to
    # a correct value (see gui/webauth.py).
    #
    # The token that's built here will be later used to find an API router,
    # get the ApiCallHandler from the router, and then to call the handler's
    # Handle() method. API router will be responsible for all the ACL checks.
    token = access_control.ACLToken(
        username=request.user,
        reason=reason,
        process="GRRAdminUI",
        expiry=rdfvalue.RDFDatetime.Now() + execution_time)

    for field in ["Remote_Addr", "X-Forwarded-For"]:
      remote_addr = request.headers.get(field, "")
      if remote_addr:
        token.source_ips.append(remote_addr)
    return token

  def _FormatResultAsJson(self, result, format_mode=None):
    if result is None:
      return dict(status="OK")

    if format_mode == JsonMode.PROTO3_JSON_MODE:
      return json.loads(json_format.MessageToJson(result.AsPrimitiveProto()))
    elif format_mode == JsonMode.GRR_ROOT_TYPES_STRIPPED_JSON_MODE:
      result_dict = {}
      for field, value in result.ListSetFields():
        if isinstance(field,
                      (rdf_structs.ProtoDynamicEmbedded,
                       rdf_structs.ProtoEmbedded, rdf_structs.ProtoList)):
          result_dict[field.name] = api_value_renderers.RenderValue(value)
        else:
          result_dict[field.name] = api_value_renderers.RenderValue(value)[
              "value"]
      return result_dict
    elif format_mode == JsonMode.GRR_TYPE_STRIPPED_JSON_MODE:
      rendered_data = api_value_renderers.RenderValue(result)
      return api_value_renderers.StripTypeInfo(rendered_data)
    elif format_mode == JsonMode.GRR_JSON_MODE:
      return api_value_renderers.RenderValue(result)
    else:
      raise ValueError("Invalid format_mode: %s" % format_mode)

  @staticmethod
  def CallApiHandler(handler, args, token=None):
    """Handles API call to a given handler with given args and token."""

    result = handler.Handle(args, token=token)

    expected_type = handler.result_type
    if expected_type is None:
      expected_type = None.__class__

    if result.__class__ != expected_type:
      raise UnexpectedResultTypeError(
          "Expected %s, but got %s." % (expected_type.__name__,
                                        result.__class__.__name__))

    return result

  def __init__(self, router_matcher=None):
    self._router_matcher = router_matcher or RouterMatcher()

  def _BuildResponse(self,
                     status,
                     rendered_data,
                     method_name=None,
                     headers=None,
                     content_length=None,
                     token=None,
                     no_audit_log=False):
    """Builds HTTPResponse object from rendered data and HTTP status."""

    # To avoid IE content sniffing problems, escape the tags. Otherwise somebody
    # may send a link with malicious payload that will be opened in IE (which
    # does content sniffing and doesn't respect Content-Disposition header) and
    # IE will treat the document as html and executre arbitrary JS that was
    # passed with the payload.
    str_data = json.dumps(
        rendered_data, cls=JSONEncoderWithRDFPrimitivesSupport)
    # XSSI protection and tags escaping
    rendered_data = ")]}'\n" + str_data.replace("<", r"\u003c").replace(
        ">", r"\u003e")

    response = werkzeug_wrappers.Response(
        rendered_data,
        status=status,
        content_type="application/json; charset=utf-8")
    response.headers[
        "Content-Disposition"] = "attachment; filename=response.json"
    response.headers["X-Content-Type-Options"] = "nosniff"

    if token and token.reason:
      response.headers["X-GRR-Reason"] = utils.SmartStr(token.reason)
    if method_name:
      response.headers["X-API-Method"] = method_name
    if no_audit_log:
      response.headers["X-No-Log"] = "True"

    for key, value in iteritems(headers or {}):
      response.headers[key] = value

    if content_length is not None:
      response.content_length = content_length

    return response

  def _BuildStreamingResponse(self, binary_stream, method_name=None):
    """Builds HTTPResponse object for streaming."""
    precondition.AssertType(method_name, unicode)

    # We get a first chunk of the output stream. This way the likelihood
    # of catching an exception that may happen during response generation
    # is much higher.
    content = binary_stream.GenerateContent()
    try:
      peek = content.next()
      stream = itertools.chain([peek], content)
    except StopIteration:
      stream = []

    response = werkzeug_wrappers.Response(
        response=stream,
        content_type="binary/octet-stream",
        direct_passthrough=True)
    response.headers["Content-Disposition"] = ((
        "attachment; filename=%s" % binary_stream.filename).encode("utf-8"))
    if method_name:
      response.headers["X-API-Method"] = method_name.encode("utf-8")

    if binary_stream.content_length:
      response.content_length = binary_stream.content_length

    return response

  def HandleRequest(self, request):
    """Handles given HTTP request."""
    impersonated_username = config.CONFIG["AdminUI.debug_impersonate_user"]
    if impersonated_username:
      logging.info("Overriding user as %s", impersonated_username)
      request.user = config.CONFIG["AdminUI.debug_impersonate_user"]

    if not aff4_users.GRRUser.IsValidUsername(request.user):
      return self._BuildResponse(
          403, dict(message="Invalid username: %s" % request.user))

    try:
      router, method_metadata, args = self._router_matcher.MatchRouter(request)
    except access_control.UnauthorizedAccess as e:
      logging.exception("Access denied to %s (%s): %s", request.path,
                        request.method, e)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason":
              utils.SmartStr(e.message).replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject":
              utils.SmartStr(e.subject)
      }
      return self._BuildResponse(
          403,
          dict(
              message="Access denied by ACL: %s" % utils.SmartStr(e.message),
              subject=utils.SmartStr(e.subject)),
          headers=additional_headers)

    except ApiCallRouterNotFoundError as e:
      return self._BuildResponse(404, dict(message=e.message))
    except werkzeug_exceptions.MethodNotAllowed as e:
      return self._BuildResponse(405, dict(message=e.message))
    except Error as e:
      logging.exception("Can't match URL to router/method: %s", e)

      return self._BuildResponse(
          500, dict(message=str(e), traceBack=traceback.format_exc()))

    request.method_metadata = method_metadata
    request.parsed_args = args

    # SetUID() is called here so that ACL checks done by the router do not
    # clash with datastore ACL checks.
    # TODO(user): increase token expiry time.
    token = self.BuildToken(request, 60).SetUID()

    # AFF4 edge case: if a user is issuing a request, before they are created
    # using CreateGRRUser (e.g. in E2E tests or with single sign-on),
    # AFF4's ReadGRRUsers will NEVER contain the user, because the creation
    # done in the following lines does not add the user to the /users/
    # collection. Furthermore, subsequent CreateGrrUserHandler calls fail,
    # because the user technically already exists.

    # We send a blind-write request to ensure that the user object is created
    # for a user specified by the username.
    user_urn = rdfvalue.RDFURN("aff4:/users/").Add(request.user)
    # We can't use conventional AFF4 interface, since aff4.FACTORY.Create will
    # create a new version of the object for every call.
    with data_store.DB.GetMutationPool() as pool:
      pool.MultiSet(
          user_urn, {
              aff4_users.GRRUser.SchemaCls.TYPE: [aff4_users.GRRUser.__name__],
              aff4_users.GRRUser.SchemaCls.LAST: [
                  rdfvalue.RDFDatetime.Now().SerializeToDataStore()
              ]
          },
          replace=True)

    if data_store.RelationalDBWriteEnabled():
      data_store.REL_DB.WriteGRRUser(request.user)

    handler = None
    try:
      # ACL checks are done here by the router. If this method succeeds (i.e.
      # does not raise), then handlers run without further ACL checks (they're
      # free to do some in their own implementations, though).
      handler = getattr(router, method_metadata.name)(args, token=token)

      if handler.args_type != method_metadata.args_type:
        raise RuntimeError("Handler args type doesn't match "
                           "method args type: %s vs %s" %
                           (handler.args_type, method_metadata.args_type))

      binary_result_type = (
          api_call_router.RouterMethodMetadata.BINARY_STREAM_RESULT_TYPE)

      if (handler.result_type != method_metadata.result_type and
          not (handler.result_type is None and
               method_metadata.result_type == binary_result_type)):
        raise RuntimeError("Handler result type doesn't match "
                           "method result type: %s vs %s" %
                           (handler.result_type, method_metadata.result_type))

      # HEAD method is only used for checking the ACLs for particular API
      # methods.
      if request.method == "HEAD":
        # If the request would return a stream, we add the Content-Length
        # header to the response.
        if (method_metadata.result_type ==
            method_metadata.BINARY_STREAM_RESULT_TYPE):
          binary_stream = handler.Handle(args, token=token)
          return self._BuildResponse(
              200, {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              content_length=binary_stream.content_length,
              token=token)
        else:
          return self._BuildResponse(
              200, {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              token=token)

      if (method_metadata.result_type ==
          method_metadata.BINARY_STREAM_RESULT_TYPE):
        binary_stream = handler.Handle(args, token=token)
        return self._BuildStreamingResponse(
            binary_stream, method_name=method_metadata.name)
      else:
        format_mode = GetRequestFormatMode(request, method_metadata)
        result = self.CallApiHandler(handler, args, token=token)
        rendered_data = self._FormatResultAsJson(
            result, format_mode=format_mode)

        return self._BuildResponse(
            200,
            rendered_data,
            method_name=method_metadata.name,
            no_audit_log=method_metadata.no_audit_log_required,
            token=token)
    except access_control.UnauthorizedAccess as e:
      logging.exception("Access denied to %s (%s) with %s: %s", request.path,
                        request.method, method_metadata.name, e)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason":
              utils.SmartStr(e.message).replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject":
              utils.SmartStr(e.subject)
      }
      return self._BuildResponse(
          403,
          dict(
              message="Access denied by ACL: %s" % e.message,
              subject=utils.SmartStr(e.subject)),
          headers=additional_headers,
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          token=token)
    except api_call_handler_base.ResourceNotFoundError as e:
      return self._BuildResponse(
          404,
          dict(message=e.message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          token=token)
    except NotImplementedError as e:
      return self._BuildResponse(
          501,
          dict(message=e.message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          token=token)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error while processing %s (%s) with %s: %s",
                        request.path, request.method,
                        handler.__class__.__name__, e)
      return self._BuildResponse(
          500,
          dict(message=str(e), traceBack=traceback.format_exc()),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          token=token)


def RenderHttpResponse(request):
  """Renders HTTP response to a given HTTP request."""

  start_time = time.time()
  response = HTTP_REQUEST_HANDLER.HandleRequest(request)
  total_time = time.time() - start_time

  method_name = response.headers.get("X-API-Method", "unknown")
  if response.status_code == 200:
    status = "SUCCESS"
  elif response.status_code == 403:
    status = "FORBIDDEN"
  elif response.status_code == 404:
    status = "NOT_FOUND"
  elif response.status_code == 501:
    status = "NOT_IMPLEMENTED"
  else:
    status = "SERVER_ERROR"

  if request.method == "HEAD":
    metric_name = "api_access_probe_latency"
  else:
    metric_name = "api_method_latency"

  stats_collector_instance.Get().RecordEvent(
      metric_name, total_time, fields=(method_name, "http", status))

  return response


HTTP_REQUEST_HANDLER = None


class HttpApiInitHook(registry.InitHook):
  """Register HTTP API handlers."""

  def RunOnce(self):
    global HTTP_REQUEST_HANDLER
    HTTP_REQUEST_HANDLER = HttpRequestHandler()
