#!/usr/bin/env python
"""HTTP API logic that ties API call handlers with HTTP routes."""



import json
import time
import traceback
import urllib2


# pylint: disable=g-bad-import-order,unused-import
from grr.gui import django_lib
# pylint: enable=g-bad-import-order,unused-import

from django import http
from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

import logging

from grr.gui import api_auth_manager
from grr.gui import api_call_handler_base
from grr.gui import api_call_router
from grr.gui import api_value_renderers
from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.rdfvalues import structs as rdf_structs


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
    for _, metadata in router_cls.GetAnnotatedMethods().items():
      for http_method, path in metadata.http_methods:
        routing_map.add(routing.Rule(path,
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

    router_method_metadata, route_args = match
    return (router, router_method_metadata, route_args)


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
    if isinstance(obj, (rdfvalue.RDFInteger, rdfvalue.RDFBool,
                        rdfvalue.RDFString)):
      return obj.SerializeToDataStore()

    return json.JSONEncoder.default(self, obj)


class HttpRequestHandler(object):
  """Handles HTTP requests."""

  @staticmethod
  def StripTypeInfo(rendered_data):
    """Strips type information from rendered data. Useful for debugging."""

    if isinstance(rendered_data, (list, tuple)):
      return [HttpRequestHandler.StripTypeInfo(d) for d in rendered_data]
    elif isinstance(rendered_data, dict):
      if "value" in rendered_data:
        return HttpRequestHandler.StripTypeInfo(rendered_data["value"])
      else:
        result = {}
        for k, v in rendered_data.items():
          result[k] = HttpRequestHandler.StripTypeInfo(v)
        return result
    else:
      return rendered_data

  @staticmethod
  def BuildToken(request, execution_time):
    """Build an ACLToken from the request."""

    # The request.GET dictionary will also be filled on HEAD and DELETE calls.
    if request.method in ["GET", "HEAD", "DELETE"]:
      reason = request.GET.get("reason", "")
    elif request.method == "POST":
      # The header X-GRR-REASON is set in api-service.js, which django converts
      # to HTTP_X_GRR_REASON.
      reason = utils.SmartUnicode(urllib2.unquote(request.META.get(
          "HTTP_X_GRR_REASON", "")))

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
        expiry=rdfvalue.RDFDatetime().Now() + execution_time)

    for field in ["REMOTE_ADDR", "HTTP_X_FORWARDED_FOR"]:
      remote_addr = request.META.get(field, "")
      if remote_addr:
        token.source_ips.append(remote_addr)
    return token

  @staticmethod
  def CallApiHandler(handler, args, token=None):
    """Handles API call to a given handler with given args and token."""

    try:
      result = handler.Handle(args, token=token)
    except NotImplementedError:
      # Fall back to legacy Render() method if Handle() is not implemented.
      return handler.Render(args, token=token)

    expected_type = handler.result_type
    if expected_type is None:
      expected_type = None.__class__

    if result.__class__ != expected_type:
      raise UnexpectedResultTypeError("Expected %s, but got %s." %
                                      (expected_type.__name__,
                                       result.__class__.__name__))

    if result is None:
      return dict(status="OK")
    else:
      if handler.strip_json_root_fields_types:
        result_dict = {}
        for field, value in result.ListSetFields():
          if isinstance(field, (rdf_structs.ProtoDynamicEmbedded,
                                rdf_structs.ProtoEmbedded,
                                rdf_structs.ProtoList)):
            result_dict[field.name] = api_value_renderers.RenderValue(value)
          else:
            result_dict[field.name] = api_value_renderers.RenderValue(value)[
                "value"]
      else:
        result_dict = api_value_renderers.RenderValue(result)

      return result_dict

  def __init__(self, router_matcher=None):
    self._router_matcher = router_matcher or RouterMatcher()

  def _BuildResponse(self,
                     status,
                     rendered_data,
                     method_name=None,
                     headers=None):
    """Builds HTTPResponse object from rendered data and HTTP status."""

    response = http.HttpResponse(status=status,
                                 content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=response.json"
    response["X-Content-Type-Options"] = "nosniff"
    if method_name:
      response["X-API-Method"] = method_name

    for key, value in (headers or {}).items():
      response[key] = value

    response.write(")]}'\n")  # XSSI protection

    # To avoid IE content sniffing problems, escape the tags. Otherwise somebody
    # may send a link with malicious payload that will be opened in IE (which
    # does content sniffing and doesn't respect Content-Disposition header) and
    # IE will treat the document as html and executre arbitrary JS that was
    # passed with the payload.
    str_data = json.dumps(rendered_data,
                          cls=JSONEncoderWithRDFPrimitivesSupport)
    response.write(str_data.replace("<", r"\u003c").replace(">", r"\u003e"))

    return response

  def _BuildStreamingResponse(self, binary_stream, method_name=None):
    """Builds HTTPResponse object for streaming."""

    response = http.StreamingHttpResponse(
        streaming_content=binary_stream.GenerateContent(),
        content_type="binary/octet-stream")
    response["Content-Disposition"] = ("attachment; filename=%s" %
                                       binary_stream.filename)
    if method_name:
      response["X-API-Method"] = method_name

    if binary_stream.content_length:
      response["Content-Length"] = binary_stream.content_length

    return response

  def _GetArgsFromRequest(self, request, method_metadata, route_args):
    """Builds args struct out of HTTP request."""

    if request.method in ["GET", "HEAD", "DELETE"]:
      if method_metadata.args_type:
        unprocessed_request = request.GET
        if hasattr(unprocessed_request, "dict"):
          unprocessed_request = unprocessed_request.dict()

        args = method_metadata.args_type()
        for type_info in args.type_infos:
          if type_info.name in route_args:
            args.Set(type_info.name, route_args[type_info.name])
          elif type_info.name in unprocessed_request:
            args.Set(type_info.name, unprocessed_request[type_info.name])

      else:
        args = None
    elif request.method == "POST":
      try:
        args = method_metadata.args_type()
        for type_info in args.type_infos:
          if type_info.name in route_args:
            args.Set(type_info.name, route_args[type_info.name])

        if request.META["CONTENT_TYPE"].startswith("multipart/form-data;"):
          payload = json.loads(request.POST["_params_"])
          args.FromDict(payload)

          for name, fd in request.FILES.items():
            args.Set(name, fd.read())
        else:
          payload = json.loads(request.body)
          if payload:
            args.FromDict(payload)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Error while parsing POST request %s (%s): %s",
                          request.path, request.method, e)
        raise PostRequestParsingError(e)
    else:
      raise UnsupportedHttpMethod("Unsupported method: %s." % request.method)

    return args

  def HandleRequest(self, request):
    """Handles given HTTP request."""
    impersonated_username = config_lib.CONFIG["AdminUI.debug_impersonate_user"]
    if impersonated_username:
      logging.info("Overriding user as %s", impersonated_username)
      request.user = config_lib.CONFIG["AdminUI.debug_impersonate_user"]

    if not aff4_users.GRRUser.IsValidUsername(request.user):
      return self._BuildResponse(403,
                                 dict(message="Invalid username: %s" %
                                      request.user))

    strip_type_info = False
    if hasattr(request, "GET") and request.GET.get("strip_type_info", ""):
      strip_type_info = True

    try:
      router, method_metadata, route_args = self._router_matcher.MatchRouter(
          request)
      args = self._GetArgsFromRequest(request, method_metadata, route_args)
    except access_control.UnauthorizedAccess as e:
      logging.exception("Access denied to %s (%s): %s", request.path,
                        request.method, e)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": utils.SmartStr(e.message),
          "X-GRR-Unauthorized-Access-Subject": utils.SmartStr(e.subject)
      }
      return self._BuildResponse(403,
                                 dict(message="Access denied by ACL: %s" %
                                      utils.SmartStr(e.message),
                                      subject=utils.SmartStr(e.subject)),
                                 headers=additional_headers)

    except ApiCallRouterNotFoundError as e:
      return self._BuildResponse(404, dict(message=e.message))
    except werkzeug_exceptions.MethodNotAllowed as e:
      return self._BuildResponse(405, dict(message=e.message))
    except Error as e:
      logging.exception("Can't match URL to router/method: %s", e)

      return self._BuildResponse(500,
                                 dict(message=str(e),
                                      traceBack=traceback.format_exc()))

    # SetUID() is called here so that ACL checks done by the router do not
    # clash with datastore ACL checks.
    # TODO(user): increase token expiry time.
    token = self.BuildToken(request, 60).SetUID()

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
          headers = None
          if binary_stream.content_length:
            headers = {"Content-Length": binary_stream.content_length}
          return self._BuildResponse(200, {"status": "OK"},
                                     method_name=method_metadata.name,
                                     headers=headers)
        else:
          return self._BuildResponse(200, {"status": "OK"},
                                     method_name=method_metadata.name)

      if (method_metadata.result_type ==
          method_metadata.BINARY_STREAM_RESULT_TYPE):
        binary_stream = handler.Handle(args, token=token)
        return self._BuildStreamingResponse(binary_stream,
                                            method_name=method_metadata.name)
      else:
        rendered_data = self.CallApiHandler(handler, args, token=token)

        if strip_type_info:
          rendered_data = self.StripTypeInfo(rendered_data)

        return self._BuildResponse(200,
                                   rendered_data,
                                   method_name=method_metadata.name)
    except access_control.UnauthorizedAccess as e:
      logging.exception("Access denied to %s (%s) with %s: %s", request.path,
                        request.method, method_metadata.name, e)

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": utils.SmartStr(e.message),
          "X-GRR-Unauthorized-Access-Subject": utils.SmartStr(e.subject)
      }
      return self._BuildResponse(403,
                                 dict(message="Access denied by ACL: %s" %
                                      e.message,
                                      subject=utils.SmartStr(e.subject)),
                                 headers=additional_headers,
                                 method_name=method_metadata.name)
    except api_call_handler_base.ResourceNotFoundError as e:
      return self._BuildResponse(404,
                                 dict(message=e.message),
                                 method_name=method_metadata.name)
    except NotImplementedError as e:
      return self._BuildResponse(501,
                                 dict(message=e.message),
                                 method_name=method_metadata.name)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error while processing %s (%s) with %s: %s",
                        request.path, request.method,
                        handler.__class__.__name__, e)

      return self._BuildResponse(500,
                                 dict(message=str(e),
                                      traceBack=traceback.format_exc()),
                                 method_name=method_metadata.name)


def RenderHttpResponse(request):
  """Renders HTTP response to a given HTTP request."""

  start_time = time.time()
  response = HTTP_REQUEST_HANDLER.HandleRequest(request)
  total_time = time.time() - start_time

  method_name = response.get("X-API-Method", "unknown")
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

  stats.STATS.RecordEvent(metric_name,
                          total_time,
                          fields=(method_name, "http", status))

  return response


HTTP_REQUEST_HANDLER = None


class HttpApiInitHook(registry.InitHook):
  """Register HTTP API handlers."""

  def RunOnce(self):
    global HTTP_REQUEST_HANDLER
    HTTP_REQUEST_HANDLER = HttpRequestHandler()

    stats.STATS.RegisterEventMetric(
        "api_method_latency",
        fields=[("method_name", str), ("protocol", str), ("status", str)])

    stats.STATS.RegisterEventMetric(
        "api_access_probe_latency",
        fields=[("method_name", str), ("protocol", str), ("status", str)])
