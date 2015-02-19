#!/usr/bin/env python
"""Renderers for API calls (that can be bound to HTTP API, for example)."""



import json


from django import http

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

from grr.lib import access_control
from grr.lib import rdfvalue
from grr.lib import registry
from grr.proto import api_pb2


class Error(Exception):
  """Base class for API renderers exception."""


class ApiCallRendererNotFoundError(Error):
  """Raised when no renderer found for a given URL."""


class ApiCallAdditionalArgs(rdfvalue.RDFProtoStruct):
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

  def Render(self, args, token=None):
    raise NotImplementedError()


def BuildToken(request, execution_time):
  """Build an ACLToken from the request."""

  if request.method == "GET":
    reason = request.GET.get("reason", "")
  elif request.method == "POST":
    reason = request.POST.get("reason", "")

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


HTTP_ROUTING_MAP = routing.Map()


def RegisterHttpRouteHandler(method, route, renderer_cls):
  """Registers given ApiCallRenderer for given method and route."""
  HTTP_ROUTING_MAP.add(routing.Rule(
      route, methods=[method],
      endpoint=renderer_cls))


def GetRendererForHttpRequest(request):
  """Returns a renderer to handle given HTTP request."""

  matcher = HTTP_ROUTING_MAP.bind("%s:%s" % (request.environ["SERVER_NAME"],
                                             request.environ["SERVER_PORT"]))
  try:
    match = matcher.match(request.path, request.method)
  except werkzeug_exceptions.NotFound:
    raise ApiCallRendererNotFoundError("No API renderer was "
                                       "found for (%s) %s" % (
                                           request.path,
                                           request.method))

  renderer_cls, route_args = match
  return (renderer_cls(), route_args)


def FillAdditionalArgsFromRequest(request, supported_types):
  """Creates arguments objects from a given request dictionary."""

  results = {}
  for key, value in request.items():
    try:
      request_arg_type, request_attr = key.split(".", 1)
    except ValueError:
      continue

    arg_class = None
    for key, supported_type in supported_types.items():
      if key == request_arg_type:
        arg_class = supported_type

    if arg_class:
      if request_arg_type not in results:
        results[request_arg_type] = arg_class()

      results[request_arg_type].Set(request_attr, value)

  results_list = []
  for name, arg_obj in results.items():
    additional_args = ApiCallAdditionalArgs(
        name=name, type=supported_types[name].__name__)
    additional_args.args = arg_obj
    results_list.append(additional_args)

  return results_list


def RenderHttpResponse(request):
  """Handles given HTTP request with one of the available API renderers."""

  renderer, route_args = GetRendererForHttpRequest(request)

  if request.method == "GET":

    if renderer.args_type:
      unprocessed_request = request.GET
      if hasattr(unprocessed_request, "dict"):
        unprocessed_request = unprocessed_request.dict()

      args = renderer.args_type()
      for type_info in args.type_infos:
        if type_info.name in route_args:
          args.Set(type_info.name, route_args[type_info.name])
        elif type_info.name in unprocessed_request:
          args.Set(type_info.name, unprocessed_request[type_info.name])

      if renderer.additional_args_types:
        if not hasattr(args, "additional_args"):
          raise RuntimeError("Renderer %s defines additional arguments types "
                             "but its arguments object does not have "
                             "'additional_args' field." % renderer)

        if hasattr(renderer.additional_args_types, "__call__"):
          additional_args_types = renderer.additional_args_types()
        else:
          additional_args_types = renderer.additional_args_types

        args.additional_args = FillAdditionalArgsFromRequest(
            unprocessed_request, additional_args_types)

    else:
      args = None
  else:
    raise RuntimeError("Unsupported method: %s." % renderer.method)

  token = BuildToken(request, renderer.max_execution_time)
  rendered_data = renderer.Render(args, token=token)

  response = http.HttpResponse(content_type="application/json")
  response.write(")]}'\n")  # XSSI protection
  response.write(json.dumps(rendered_data))

  return response
