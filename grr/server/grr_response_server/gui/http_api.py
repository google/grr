#!/usr/bin/env python
"""HTTP API logic that ties API call handlers with HTTP routes."""

import http.client
import itertools
import json
import logging
import re
import time
import traceback
from typing import Iterable, Optional, Union
from urllib import parse

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

from google.protobuf import descriptor as proto_descriptor
from google.protobuf import json_format
from google.protobuf import message
from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import http_request
from grr_response_server.gui import http_response

_FIELDS = (
    ("method_name", str),
    ("protocol", str),
    ("status", str),
    ("origin", str),
)
API_METHOD_LATENCY = metrics.Event("api_method_latency", fields=_FIELDS)
API_ACCESS_PROBE_LATENCY = metrics.Event(
    "api_access_probe_latency", fields=_FIELDS
)


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


class RouterMatcher:
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
        routing_map.add(
            # https://werkzeug.palletsprojects.com/en/stable/routing/#werkzeug.routing.Rule
            # If GET is present in the list of methods and HEAD is not, HEAD
            # is added automatically.
            routing.Rule(
                path,
                methods=[http_method],
                endpoint=metadata,
            )
        )

    return routing_map

  def _GetRoutingMap(self, router):
    """Returns a routing map for a given router instance."""

    try:
      routing_map = self._routing_maps_cache.Get(router.__class__)
    except KeyError:
      routing_map = self._BuildHttpRoutingMap(router.__class__)
      self._routing_maps_cache.Put(router.__class__, routing_map)

    return routing_map

  def _FillProtoWithRouteArgs(
      self,
      args_proto: message.Message,
      route_args: dict[str, str],
  ) -> None:
    """Fills out the proto with the query param values."""
    for field in route_args:
      if field in args_proto.DESCRIPTOR.fields_by_name:
        try:
          _SetFieldProto(
              args_proto,
              args_proto.DESCRIPTOR.fields_by_name[field],
              route_args[field],
          )
        except ValueError as e:
          raise InvalidRequestArgumentsInRouteError() from e

  def _GetArgsFromRequest(
      self,
      request: http_request.HttpRequest,
      method_metadata: api_call_router.RouterMethodMetadata,
      route_args: dict[str, str],
  ) -> Optional[message.Message]:
    """Builds args struct out of HTTP request."""

    if request.method in ["GET", "HEAD"]:
      if not method_metadata.proto_args_type:
        return None

      # Capture fields on the URL request params.
      nested_request = UnflattenDict(request.args)

      # Fill out the proto with the query param values.
      args_proto = method_metadata.proto_args_type()
      try:
        RecursivelyBuildProtoFromStringDict(nested_request, args_proto)
      except ValueError as e:
        raise InvalidRequestArgumentsInRouteError() from e

      # Also override fields that are captured in the route.
      self._FillProtoWithRouteArgs(args_proto, route_args)

      return args_proto

    elif request.method in ["POST", "DELETE", "PATCH"]:
      if not method_metadata.proto_args_type:
        return None

      args_proto = method_metadata.proto_args_type()
      try:
        json_format.Parse(request.get_data(as_text=True) or "{}", args_proto)
      except json_format.ParseError as e:
        logging.exception(
            "Error while parsing %s request %s (%s): %s",
            request.method,
            request.path,
            request.method,
            e,
        )
        raise PostRequestParsingError() from e

      # Also override fields that are captured in the route.
      self._FillProtoWithRouteArgs(args_proto, route_args)
      return args_proto

    else:
      raise UnsupportedHttpMethod("Unsupported method: %s." % request.method)

  def MatchRouter(self, request: http_request.HttpRequest) -> tuple[
      api_call_router.ApiCallRouter,
      api_call_router.RouterMethodMetadata,
      Optional[message.Message],
  ]:
    """Returns a router for a given HTTP request."""
    router = api_auth_manager.API_AUTH_MGR.GetRouterForUser(request.user)
    routing_map = self._GetRoutingMap(router)

    matcher = routing_map.bind(
        "%s:%s"
        % (request.environ["SERVER_NAME"], request.environ["SERVER_PORT"])
    )
    try:
      match = matcher.match(request.path, request.method)
    except werkzeug_exceptions.NotFound as e:
      raise ApiCallRouterNotFoundError(
          "No API router was found for (%s) %s" % (request.path, request.method)
      ) from e

    router_method_metadata, route_args_dict = match
    proto_args = self._GetArgsFromRequest(
        request, router_method_metadata, route_args_dict
    )
    return (
        router,
        router_method_metadata,
        proto_args,
    )


def _ContentDispositionHeader(filename: str):
  """Content-Disposition as specified by RFC 6266."""
  try:
    filename.encode("ascii")
    is_ascii = True
  except UnicodeEncodeError:
    is_ascii = False
  # https://datatracker.ietf.org/doc/html/rfc9110#name-quoted-strings
  quotable_characters = r"^[\t \x21-\x7e]*$"
  if is_ascii and re.match(quotable_characters, filename):
    f = filename.replace("\\", "\\\\").replace('"', r"\"")
    return (
        f'attachment;  filename="{f}";'
        f" filename*=utf-8''{parse.quote(filename)}"
    )
  else:
    return f"attachment; filename*=utf-8''{parse.quote(filename)}"


class HttpRequestHandler:
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

  def _FormatResultAsJson(self, result):
    if result is None:
      return dict(status="OK")

    json_data = json_format.MessageToJson(result)
    return json.loads(json_data)

  def CallApiHandler(
      self,
      handler: api_call_handler_base.ApiCallHandler,
      args: Optional[message.Message] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> Optional[message.Message]:
    """Handles API call to a given handler with given args and context.

    Only handles non-streaming requests.

    Args:
      handler: An instance of an API call handler.
      args: A proto message containing arguments for the handler call.
      context: An instance of ApiCallContext.

    Returns:
      A proto message with the result of the handler call.

    Raises:
      UnexpectedResultTypeError: If the handler returns a result of an
        unexpected type.
    """

    result = handler.Handle(args, context=context)

    if handler.proto_result_type and not result:
      raise UnexpectedResultTypeError(
          "Handler (%s) expected to return a proto message, but didn't:"
          " %s vs %s"
          % (
              handler.__class__.__name__,
              handler.proto_result_type,
              result.__class__.__name__,
          )
      )

    if not result:
      return None

    if not isinstance(result, message.Message):
      raise UnexpectedResultTypeError(
          "Handler (%s) expected a proto message result, but got: %s"
          % (handler.__class__.__name__, type(result))
      )

    if not isinstance(result, handler.proto_result_type):
      raise UnexpectedResultTypeError(
          "Handler (%s) expected %s, but got %s."
          % (
              handler.__class__.__name__,
              handler.proto_result_type,
              result.__class__.__name__,
          )
      )

    return result

  def __init__(self, router_matcher=None):
    self._router_matcher = router_matcher or RouterMatcher()

  def _BuildResponse(
      self,
      status,
      rendered_data,
      method_name=None,
      headers=None,
      content_length=None,
      context=None,
      no_audit_log=False,
  ):
    """Builds HttpResponse object from rendered data and HTTP status."""

    # To avoid IE content sniffing problems, escape the tags. Otherwise somebody
    # may send a link with malicious payload that will be opened in IE (which
    # does content sniffing and doesn't respect Content-Disposition header) and
    # IE will treat the document as html and execute arbitrary JS that was
    # passed with the payload.
    str_data = json.dumps(rendered_data)
    # XSSI protection and tags escaping
    rendered_str = ")]}'\n" + str_data.replace("<", r"\u003c").replace(
        ">", r"\u003e"
    )

    response = http_response.HttpResponse(
        rendered_str,
        status=status,
        content_type="application/json; charset=utf-8",
        context=context,
    )
    response.headers["Content-Disposition"] = (
        "attachment; filename=response.json"
    )
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

  def _BuildStreamingResponse(
      self, binary_stream, method_name=None, context=None
  ):
    """Builds HttpResponse object for streaming."""
    precondition.AssertType(method_name, str)

    # For the challenges of implementing correct streaming response logic:
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
        context=context,
    )
    response.headers["Content-Disposition"] = _ContentDispositionHeader(
        binary_stream.filename
    )

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
          dict(message="Invalid username: %s" % request.user),
      )

    try:
      router, method_metadata, proto_args = self._router_matcher.MatchRouter(
          request
      )
    except access_control.UnauthorizedAccess as e:
      error_message = str(e)
      logging.exception(
          "Access denied to %s (%s): %s", request.path, request.method, e
      )

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": error_message.replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject": e.subject,
      }
      return self._BuildResponse(
          http.client.FORBIDDEN,
          dict(
              message="Access denied by ACL: %s" % error_message,
              subject=e.subject,
          ),
          headers=additional_headers,
      )

    except ApiCallRouterNotFoundError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.NOT_FOUND, dict(message=error_message)
      )
    except werkzeug_exceptions.MethodNotAllowed as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.METHOD_NOT_ALLOWED, dict(message=error_message)
      )
    except (InvalidRequestArgumentsInRouteError, PostRequestParsingError) as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.UNPROCESSABLE_ENTITY, dict(message=error_message)
      )
    except Error as e:
      logging.exception("Can't match URL to router/method: %s", e)

      return self._BuildResponse(
          http.client.INTERNAL_SERVER_ERROR,
          dict(message=str(e), traceBack=traceback.format_exc()),
      )

    request.parsed_args = proto_args

    context = self._BuildContext(request)

    data_store.REL_DB.WriteGRRUser(request.user, email=request.email)

    handler = None

    # The **convention** is that router methods take the same argument type as
    # the handler they return. Some routers use the params to check whether
    # access is allowed.
    if method_metadata.proto_args_type:
      router_args = proto_args
    else:
      router_args = None

    try:
      # ACL checks are done here by the router. If this method succeeds (i.e.
      # does not raise), then handlers run without further ACL checks (they're
      # free to do some in their own implementations, though).
      handler = getattr(router, method_metadata.name)(
          router_args, context=context
      )

      if handler.proto_args_type != method_metadata.proto_args_type:
        raise RuntimeError(
            f"Handler {handler.__class__.__name__}.proto_args_type doesn't"
            f" match expected method args type: {handler.proto_args_type} vs"
            f" {method_metadata.proto_args_type}"
        )

      if not method_metadata.is_streaming:
        if handler.proto_result_type != method_metadata.proto_result_type:
          raise RuntimeError(
              f"Handler {handler.__class__.__name__}.proto_result_type doesn't"
              " match expected method result type:"
              f" {handler.proto_result_type} vs"
              f" {method_metadata.proto_result_type}"
          )

      # HEAD method is only used for checking the ACLs for particular API
      # methods.
      if request.method == "HEAD":
        # If the request would return a stream, we add the Content-Length
        # header to the response.
        if method_metadata.is_streaming:
          binary_stream = handler.Handle(proto_args, context=context)
          if not isinstance(
              binary_stream, api_call_handler_base.ApiBinaryStream
          ):
            raise RuntimeError(
                "Invalid result type returned from the API handler. Expected"
                " ApiBinaryStream, got %s"
                % binary_stream.__class__.__name__
            )
          return self._BuildResponse(
              200,
              {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              content_length=binary_stream.content_length,
              context=context,
          )
        else:
          return self._BuildResponse(
              200,
              {"status": "OK"},
              method_name=method_metadata.name,
              no_audit_log=method_metadata.no_audit_log_required,
              context=context,
          )

      if method_metadata.is_streaming:
        binary_stream = handler.Handle(proto_args, context=context)
        if not isinstance(binary_stream, api_call_handler_base.ApiBinaryStream):
          raise RuntimeError(
              "Invalid result type returned from the API handler. Expected"
              " ApiBinaryStream, got %s"
              % binary_stream.__class__.__name__
          )
        return self._BuildStreamingResponse(
            binary_stream, method_name=method_metadata.name, context=context
        )
      else:
        result = self.CallApiHandler(handler, proto_args, context=context)
        rendered_data = self._FormatResultAsJson(result)

        return self._BuildResponse(
            200,
            rendered_data,
            method_name=method_metadata.name,
            no_audit_log=method_metadata.no_audit_log_required,
            context=context,
        )
    # ResourceExhaustedError inherits from UnauthorizedAccess, so it
    # should be above UnauthorizedAccess in the code.
    except api_call_handler_base.ResourceExhaustedError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.TOO_MANY_REQUESTS,
          {"message": f"Quota exceeded: {error_message}"},
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )
    except access_control.UnauthorizedAccess as e:
      error_message = str(e)
      logging.warning(
          "Access denied for %s (HTTP %s %s): %s",
          method_metadata.name,
          request.method,
          request.path,
          error_message,
      )

      additional_headers = {
          "X-GRR-Unauthorized-Access-Reason": error_message.replace("\n", ""),
          "X-GRR-Unauthorized-Access-Subject": e.subject,
      }
      return self._BuildResponse(
          http.client.FORBIDDEN,
          dict(
              message="Access denied by ACL: %s" % error_message,
              subject=e.subject,
          ),
          headers=additional_headers,
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )
    except api_call_handler_base.ResourceNotFoundError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.NOT_FOUND,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )
    # ValueError is commonly raised by GRR code in arguments checks.
    except ValueError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.UNPROCESSABLE_ENTITY,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )
    except NotImplementedError as e:
      error_message = str(e)
      return self._BuildResponse(
          http.client.NOT_IMPLEMENTED,
          dict(message=error_message),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )
    except Exception as e:  # pylint: disable=broad-except
      error_message = str(e)
      logging.exception(
          "Error while processing %s (%s) with %s: %s",
          request.path,
          request.method,
          handler.__class__.__name__,
          e,
      )
      return self._BuildResponse(
          http.client.INTERNAL_SERVER_ERROR,
          dict(message=error_message, traceBack=traceback.format_exc()),
          method_name=method_metadata.name,
          no_audit_log=method_metadata.no_audit_log_required,
          context=context,
      )


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
  elif response.status_code == http.client.TOO_MANY_REQUESTS:
    status = "RESOURCE_EXHAUSTED"
  elif response.status_code == http.client.NOT_FOUND:
    status = "NOT_FOUND"
  elif response.status_code == http.client.UNPROCESSABLE_ENTITY:
    status = "INVALID_ARGUMENT"
  elif response.status_code == http.client.NOT_IMPLEMENTED:
    status = "NOT_IMPLEMENTED"
  else:
    status = "SERVER_ERROR"

  fields = (method_name, "http", status, _GetRequestOrigin(request))
  if request.method == "HEAD":
    API_ACCESS_PROBE_LATENCY.RecordEvent(total_time, fields=fields)
  else:
    API_METHOD_LATENCY.RecordEvent(total_time, fields=fields)

  return response


def _GetRequestOrigin(request):
  """Returns the self-reported origin (e.g. "GRR-UI/2.0") of the request."""
  ua = request.headers.get("X-User-Agent", "")

  # Do not loop-through arbitrary header values into the metric data. Instead,
  # allow-list known good values.
  if ua in ("GRR-UI/1.0", "GRR-UI/2.0"):
    return ua
  else:
    # "unknown" can be returned for UIv1's file downloads, because these are
    # triggered through an iframe.
    return "unknown"


def UnflattenDict(
    flattened_dict: dict[str, str],
) -> dict[str, str]:
  """Converts a flattened dictionary to a nested structure.

  For example, the following dictionary:
    {
      "foo.bar": "42",
      "foo.baz.quux": "thud"
    }
  will be converted to:
    {
      "foo": {
        "bar": "42",
        "baz": {
          "quux": "thud"
        }
      }
    }

  Args:
    flattened_dict: A flat dictionary to convert.

  Returns:
    A nested dictionary with values preserved.
  """
  nested_dict: dict[str, str] = {}
  for key, value in flattened_dict.items():
    parts = key.split(".")
    current_level = nested_dict

    # For every part but the last, create an empty dictionary if it
    # doesn't exist yet. Otherwise add the value to the dictionary.
    for i, part in enumerate(parts):
      if i == len(parts) - 1:
        # Last part, assign the value
        current_level[part] = value
      else:
        # Not the last part, ensure it's a dictionary
        if part not in current_level:
          current_level[part] = {}
        current_level = current_level[part]
  return nested_dict


_DESCRIPTOR_TYPE_TO_NAME = {
    proto_descriptor.FieldDescriptor.TYPE_DOUBLE: "double",
    proto_descriptor.FieldDescriptor.TYPE_FLOAT: "float",
    proto_descriptor.FieldDescriptor.TYPE_INT64: "int64",
    proto_descriptor.FieldDescriptor.TYPE_UINT64: "uint64",
    proto_descriptor.FieldDescriptor.TYPE_INT32: "int32",
    proto_descriptor.FieldDescriptor.TYPE_FIXED64: "fixed64",
    proto_descriptor.FieldDescriptor.TYPE_FIXED32: "fixed32",
    proto_descriptor.FieldDescriptor.TYPE_BOOL: "bool",
    proto_descriptor.FieldDescriptor.TYPE_STRING: "string",
    proto_descriptor.FieldDescriptor.TYPE_GROUP: "group",
    proto_descriptor.FieldDescriptor.TYPE_MESSAGE: "message",
    proto_descriptor.FieldDescriptor.TYPE_BYTES: "bytes",
    proto_descriptor.FieldDescriptor.TYPE_UINT32: "uint32",
    proto_descriptor.FieldDescriptor.TYPE_ENUM: "enum",
    proto_descriptor.FieldDescriptor.TYPE_SFIXED32: "sfixed32",
    proto_descriptor.FieldDescriptor.TYPE_SFIXED64: "sfixed64",
    proto_descriptor.FieldDescriptor.TYPE_SINT32: "sint32",
    proto_descriptor.FieldDescriptor.TYPE_SINT64: "sint64",
}


def _ConvertStringToValue(
    field_descriptor: proto_descriptor.FieldDescriptor,
    value: str,
):
  """Converts a string value to the appropriate type based on the field descriptor.

  Args:
      field_descriptor: The descriptor of the field.
      value: The string value to convert.

  Returns:
      The converted value.

  Raises:
      ValueError: If the value cannot be converted to the expected type.
  """
  field_name = field_descriptor.name
  field_type = field_descriptor.type
  try:
    field_type_name = _DESCRIPTOR_TYPE_TO_NAME[field_type]
  except KeyError:
    field_type_name = f"unknown type ({field_type})"

  if field_type == proto_descriptor.FieldDescriptor.TYPE_STRING:
    return value
  elif field_type in [
      proto_descriptor.FieldDescriptor.TYPE_INT32,
      proto_descriptor.FieldDescriptor.TYPE_INT64,
      proto_descriptor.FieldDescriptor.TYPE_UINT32,
      proto_descriptor.FieldDescriptor.TYPE_UINT64,
  ]:
    return int(value)
  elif field_type in [
      proto_descriptor.FieldDescriptor.TYPE_FLOAT,
      proto_descriptor.FieldDescriptor.TYPE_DOUBLE,
  ]:
    return float(value)
  elif field_type == proto_descriptor.FieldDescriptor.TYPE_BOOL:
    if value.lower() in ("true", "1"):
      return True
    elif value.lower() in ("false", "0"):
      return False
    else:
      raise ValueError(
          f"Could not convert '{value}' to boolean for field '{field_name}'."
      )
  elif field_type == proto_descriptor.FieldDescriptor.TYPE_ENUM:
    # Try to get the enum value from the string name
    enum_value = field_descriptor.enum_type.values_by_name.get(value)
    if enum_value is None:
      # If not found by name, try to get it by number
      try:
        enum_number = int(value)
        enum_value = field_descriptor.enum_type.values_by_number.get(
            enum_number
        )
      except ValueError:
        pass  # it was not a number either
    if enum_value is None:
      raise ValueError(
          f"'{value}' is not a valid enum value for field"
          f" '{field_name}'. Available values:"
          f" {field_descriptor.enum_type.values_by_name.keys()} or numbers:"
          f" {field_descriptor.enum_type.values_by_number.keys()}"
      )
    return enum_value.number
  else:
    raise ValueError(
        f"Unsupported field type: {field_type_name} for field '{field_name}'."
    )


def _SetFieldProto(
    args_proto: message.Message,
    field_descriptor: proto_descriptor.FieldDescriptor,
    value: Union[str, Iterable[str]],
):
  """Sets fields on the arg_proto object.

  Args:
    args_proto: Proto message to set the field on.
    field_descriptor: Descriptor of the field to set.
    value: Value to set. Doesn't support all field types.
  """
  field_name = field_descriptor.name

  # pylint: disable=line-too-long
  is_repeated = field_descriptor.label == proto_descriptor.FieldDescriptor.LABEL_REPEATED
  # pylint: enable=line-too-long
  try:
    if is_repeated:
      current_field = getattr(args_proto, field_name)
      for item in value:
        current_field.append(_ConvertStringToValue(field_descriptor, item))
    else:
      converted_value = _ConvertStringToValue(field_descriptor, value)
      setattr(args_proto, field_name, converted_value)
  except ValueError as e:
    raise ValueError(
        f"Error setting field '{field_name}' with value '{value}': {e}"
    ) from e


def RecursivelyBuildProtoFromStringDict(
    str_dict: dict[str, str], proto: message.Message
) -> message.Message:
  """Recursively parses a dict into a proto."""

  for k, v in str_dict.items():
    if k not in proto.DESCRIPTOR.fields_by_name:
      # Ignore unknown fields.
      continue

    field_descriptor = proto.DESCRIPTOR.fields_by_name[k]
    if field_descriptor.message_type is not None:
      # Nested message, recursively parse the value.
      nested_empty = getattr(proto, k)
      RecursivelyBuildProtoFromStringDict(v, nested_empty)
    else:
      # Leaf field, set the value.
      _SetFieldProto(
          proto,
          field_descriptor,
          v,
      )


HTTP_REQUEST_HANDLER = None


@utils.RunOnce
def InitializeHttpRequestHandlerOnce():
  """Register HTTP API handlers."""

  global HTTP_REQUEST_HANDLER
  HTTP_REQUEST_HANDLER = HttpRequestHandler()
