#!/usr/bin/env python
# Lint as: python3
"""HTTP API logic that ties API call handlers with HTTP routes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import http.client
import itertools
import logging
import time
import traceback
from typing import Text

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

from google.protobuf import json_format
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import serialization
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util.compat import json
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_value_renderers
from grr_response_server.gui import http_response


API_METHOD_LATENCY = metrics.Event(
    "api_method_latency",
    fields=[("method_name", str), ("protocol", str), ("status", str)])
API_ACCESS_PROBE_LATENCY = metrics.Event(
    "api_access_probe_latency",
    fields=[("method_name", str), ("protocol", str), ("status", str)])


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


class InvalidRequestArgumentsInRouteError(Error):
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
    for _, metadata in router_cls.GetAnnotatedMethods().items():
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
        coerced_obj = serialization.FromHumanReadable(type_info.type, value)
    else:
      coerced_obj = serialization.FromHumanReadable(type_info.type, value)
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
          try:
            if type_info.name in route_args:
              self._SetField(args, type_info, route_args[type_info.name])
            elif type_info.name in unprocessed_request:
              self._SetField(args, type_info,
                             unprocessed_request[type_info.name])
          except Exception as e:  # pylint: disable=broad-except
            raise InvalidRequestArgumentsInRouteError(e)

      else:
        args = None
    elif request.method in ["POST", "DELETE", "PATCH"]:
      try:
        if request.content_type and request.content_type.startswith(
            "multipart/form-data;"):
          payload = json.Parse(request.form["_params_"].decode("utf-8"))
          args = method_metadata.args_type()
          args.FromDict(payload)

          for name, fd in request.files.items():
            args.Set(name, fd.read())
        elif format_mode == JsonMode.PROTO3_JSON_MODE:
          # NOTE: Arguments rdfvalue has to be a protobuf-based RDFValue.
          args_proto = method_metadata.args_type().protobuf()
          json_format.Parse(request.get_data(as_text=True) or "{}", args_proto)
          args = method_metadata.args_type.FromSerializedBytes(
              args_proto.SerializeToString())
        else:
          json_data = request.get_data(as_text=True) or "{}"
          payload = json.Parse(json_data)
          args = method_metadata.args_type()
          if payload:
            args.FromDict(payload)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Error while parsing POST request %s (%s): %s",
                          request.path, request.method, e)
        raise PostRequestParsingError(e)

      for type_info in args.type_infos:
        if type_info.name in route_args:
          try:
            self._SetField(args, type_info, route_args[type_info.name])
          except Exception as e:  # pylint: disable=broad-except
            raise InvalidRequestArgumentsInRouteError(e)
    else:
      raise UnsupportedHttpMethod("Unsupported method: %s." % request.method)

    return args

  def MatchRouter(self, request):
    """Returns a router for a given HTTP request."""
    router = api_auth_manager.API_AUTH_MGR.GetRouterForUser(request.user)
    routing_map = self._GetRoutingMap(router)

    matcher = routing_map.bind(
        "%s:%s" %
        (request.environ["SERVER_NAME"], request.environ["SERVER_PORT"]))
    try:
      match = matcher.match(request.path, request.method)
    except werkzeug_exceptions.NotFound:
      raise ApiCallRouterNotFoundError("No API router was found for (%s) %s" %
                                       (request.path, request.method))

    router_method_metadata, route_args_dict = match
    return (router, router_method_metadata,
            self._GetArgsFromRequest(request, router_method_metadata,
                                     route_args_dict))


class JSONEncoderWithRDFPrimitivesSupport(json.Encoder):
  """Custom JSON encoder that encodes handlers output.

  Custom encoder is required to facilitate usage of primitive values -
  booleans, integers and strings - in handlers responses.

  If handler references an RDFString or RDFInteger when building a
  response, it will lead to JSON encoding failure when response encoded,
  unless this custom encoder is used. Another way to solve this issue would be
  to explicitly call api_value_renderers.RenderValue on every value returned
  from the renderer, but it will make the code look overly verbose and dirty.
  """

  def default(self, obj):
    if isinstance(obj, rdfvalue.RDFInteger):
      return int(obj)

    if isinstance(obj, rdfvalue.RDFString):
      # TODO: Since we want to this to be a JSON-compatible type,
      # we cannot call `str` as that would result in `future.newstr` in Python 2
      # which is not easily serializable. This can be replaced with `str` call
      # once support for Python 2 is dropped.
      return Text(obj)

    return super(JSONEncoderWithRDFPrimitivesSupport, self).default(obj)


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

  def _BuildContext(self, request):
    """Build the API call context from the request."""

    # We assume that request.user contains the username that we can trust.
    # No matter what authentication method is used, the WebAuthManager is
    # responsible for authenticating the userand setting request.user to
    # a correct value (see gui/webauth.py).
    #
    # The context that's built here will be later used to find an API router,
    # get the ApiCallHandler from the router, and then to call the handler's
    # Handle() method. API router will be responsible for all the ACL checks.
    return api_call_context.ApiCallContext(request.user)

  def _FormatResultAsJson(self, result, format_mode=None):
    if result is None:
      return dict(status="OK")

    if format_mode == JsonMode.PROTO3_JSON_MODE:
      json_data = json_format.MessageToJson(
          result.AsPrimitiveProto(), float_precision=8)
      if compatibility.PY2:
        json_data = json_data.decode("utf-8")
      return json.Parse(json_data)
    elif format_mode == JsonMode.GRR_ROOT_TYPES_STRIPPED_JSON_MODE:
      result_dict = {}
      for field, value in result.ListSetFields():
        if isinstance(field,
                      (rdf_structs.ProtoDynamicEmbedded,
                       rdf_structs.ProtoEmbedded, rdf_structs.ProtoList)):
          result_dict[field.name] = api_value_renderers.RenderValue(value)
        else:
          result_dict[field.name] = api_value_renderers.RenderValue(
              value)["value"]
      return result_dict
    elif format_mode == JsonMode.GRR_TYPE_STRIPPED_JSON_MODE:
      rendered_data = api_value_renderers.RenderValue(result)
      return api_value_renderers.StripTypeInfo(rendered_data)
    elif format_mode == JsonMode.GRR_JSON_MODE:
      return api_value_renderers.RenderValue(result)
    else:
      raise ValueError("Invalid format_mode: %s" % format_mode)

  @staticmethod
  def CallApiHandler(handler, args, context=None):
    """Handles API call to a given handler with given args and context."""

    result = handler.Handle(args, context=context)

    expected_type = handler.result_type
    if expected_type is None:
      expected_type = None.__class__

    if result.__class__ != expected_type:
      raise UnexpectedResultTypeError(
          "Expected %s, but got %s." %
          (expected_type.__name__, result.__class__.__name__))

    return result

  def __init__(self, router_matcher=None):
    self._router_matcher = router_matcher or RouterMatcher()

  def _BuildResponse(self,
                     status,
                     rendered_data,
                     method_name=None,
                     headers=None,
                     content_length=None,
                     context=None,
                     no_audit_log=False):
    """Builds HttpResponse object from rendered data and HTTP status."""

    # To avoid IE content sniffing problems, escape the tags. Otherwise somebody
    # may send a link with malicious payload that will be opened in IE (which
    # does content sniffing and doesn't respect Content-Disposition header) and
    # IE will treat the document as html and executre arbitrary JS that was
    # passed with the payload.
    str_data = json.Dump(
        rendered_data, encoder=JSONEncoderWithRDFPrimitivesSupport)
    # XSSI protection and tags escaping
    rendered_str = ")]}'\n" + str_data.replace("<", r"\u003c").replace(
        ">", r"\u003e")

    response = http_response.HttpResponse(
        rendered_str,
        status=status,
        content_type="application/json; charset=utf-8",
        context=context)
    response.headers[
        "Content-Disposition"] = "attachment; filename=response.json"
    response.headers["X-Content-Type-Options"] = "nosniff"

    if method_name:
      response.headers["X-API-Method"] = method_name
    if no_audit_log:
      response.headers["X-No-Log"] = "True"
    if context:
      response.headers["X-API-User"] = context.username

    for key, value in (headers or {}).items():
      response.headers[key] = value

    if content_length is not None:
      response.content_length = content_length

    return response

  def _BuildStreamingResponse(self,
                              binary_stream,
                              method_name=None,
                              context=None):
    """Builds HttpResponse object for streaming."""
    precondition.AssertType(method_name, Text)

    # For the challenges of implemeting correct streaming response logic:
    # https://rhodesmill.org/brandon/2013/chunked-wsgi/

    # We get a first chunk of the output stream. This way the likelihood
    # of catching an exception that may happen during response generation
    # is much higher.
    content = binary_stream.GenerateContent()
    try:
      peek = next(content)
      stream = itertools.chain([peek], content)
    except StopIteration:
      stream = []

    response = http_response.HttpResponse(
        response=stream,
        content_type="binary/octet-stream",
        direct_passthrough=True,
        context=context)
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

    if not access_control.IsValidUsername(request.user):
      return self._BuildResponse(
          http.client.FORBIDDEN,
          dict(message="Invalid username: %s" % request.user))

    try:
      router, method_metadata, args = self._router_matcher.MatchRouter(request)
    except access_control.UnauthorizedAccess as e:
      error_message = str(e)
      logging.exception("Access denied to %s (%s): %s", request.path,
                        request.method, e)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": error_message.replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject": e.subject
      }
      return self._BuildResponse(
          http.client.FORBIDDEN,
          dict(
              message="Access denied by ACL: %s" % error_message,
              subject=e.subject),
          headers=additional_headers)

    except ApiCallRouterNotFoundError as e:
      error_message = str(e)
      return self._BuildResponse(http.client.NOT_FOUND,
                                 dict(message=error_message))
    except werkzeug_exceptions.MethodNotAllowed as e:
      error_message = str(e)
      return self._BuildResponse(http.client.METHOD_NOT_ALLOWED,
                                 dict(message=error_message))
    except (InvalidRequestArgumentsInRouteError, PostRequestParsingError) as e:
      error_message = str(e)
      return self._BuildResponse(http.client.UNPROCESSABLE_ENTITY,
                                 dict(message=error_message))
    except Error as e:
      logging.exception("Can't match URL to router/method: %s", e)

      return self._BuildResponse(
          http.client.INTERNAL_SERVER_ERROR,
          dict(message=str(e), traceBack=traceback.format_exc()))

    request.method_metadata = method_metadata
    request.parsed_args = args

    context = self._BuildContext(request)

    data_store.REL_DB.WriteGRRUser(request.user, email=request.email)

    handler = None
    try:
      # ACL checks are done here by the router. If this method succeeds (i.e.
      # does not raise), then handlers run without further ACL checks (they're
      # free to do some in their own implementations, though).
      handler = getattr(router, method_metadata.name)(args, context=context)

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
          binary_stream = handler.Handle(args, context=context)
          return self._BuildResponse(
              200, {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              content_length=binary_stream.content_length,
              context=context)
        else:
          return self._BuildResponse(
              200, {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              context=context)

      if (method_metadata.result_type ==
          method_metadata.BINARY_STREAM_RESULT_TYPE):
        binary_stream = handler.Handle(args, context=context)
        return self._BuildStreamingResponse(
            binary_stream, method_name=method_metadata.name, context=context)
      else:
        format_mode = GetRequestFormatMode(request, method_metadata)
        result = self.CallApiHandler(handler, args, context=context)
        rendered_data = self._FormatResultAsJson(
            result, format_mode=format_mode)

        return self._BuildResponse(
            200,
            rendered_data,
            method_name=method_metadata.name,
            no_audit_log=method_metadata.no_audit_log_required,
            context=context)
    except access_control.UnauthorizedAccess as e:
      error_message = str(e)
      logging.warning("Access denied for %s (HTTP %s %s): %s",
                      method_metadata.name, request.method, request.path,
                      error_message)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": error_message.replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject": e.subject
      }
      return self._BuildResponse(
          http.client.FORBIDDEN,
          dict(
              message="Access denied by ACL: %s" % error_message,
              subject=e.subject),
          headers=additional_headers,
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context)
    except api_call_handler_base.ResourceNotFoundError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.NOT_FOUND,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context)
    # ValueError is commonly raised by GRR code in arguments checks.
    except ValueError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.UNPROCESSABLE_ENTITY,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context)
    except NotImplementedError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.NOT_IMPLEMENTED,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context)
    except Exception as e:  # pylint: disable=broad-except
      error_message = str(e)
      logging.exception("Error while processing %s (%s) with %s: %s",
                        request.path, request.method,
                        handler.__class__.__name__, e)
      return self._BuildResponse(
          http.client.INTERNAL_SERVER_ERROR,
          dict(message=error_message, traceBack=traceback.format_exc()),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context)


def RenderHttpResponse(request):
  """Renders HTTP response to a given HTTP request."""

  start_time = time.time()
  response = HTTP_REQUEST_HANDLER.HandleRequest(request)
  total_time = time.time() - start_time

  method_name = response.headers.get("X-API-Method", "unknown")
  if response.status_code == http.client.OK:
    status = "SUCCESS"
  elif response.status_code == http.client.FORBIDDEN:
    status = "FORBIDDEN"
  elif response.status_code == http.client.NOT_FOUND:
    status = "NOT_FOUND"
  elif response.status_code == http.client.UNPROCESSABLE_ENTITY:
    status = "INVALID_ARGUMENT"
  elif response.status_code == http.client.NOT_IMPLEMENTED:
    status = "NOT_IMPLEMENTED"
  else:
    status = "SERVER_ERROR"

  fields = (method_name, "http", status)
  if request.method == "HEAD":
    API_ACCESS_PROBE_LATENCY.RecordEvent(total_time, fields=fields)
  else:
    API_METHOD_LATENCY.RecordEvent(total_time, fields=fields)

  return response


HTTP_REQUEST_HANDLER = None


@utils.RunOnce
def InitializeHttpRequestHandlerOnce():
  """Register HTTP API handlers."""

  global HTTP_REQUEST_HANDLER
  HTTP_REQUEST_HANDLER = HttpRequestHandler()
