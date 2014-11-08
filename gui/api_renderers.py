#!/usr/bin/env python
"""This module contains RESTful API renderers."""


import json


from django import http

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

from grr.lib import access_control
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


class Error(Exception):
  """Base class for API renderers exception."""


class ApiRendererNotFoundError(Error):
  """Raised when no renderer found for a given URL."""


class ApiRenderer(object):
  """Baseclass for restful API renderers."""

  __metaclass__ = registry.MetaclassRegistry

  # HTTP method. Can be either GET, POST, PUT or DELETE.
  method = None

  # Werkzeug-style route. See http://werkzeug.pocoo.org/docs/routing/ for
  # details.
  route = None

  # This is a maximum time in seconds the renderer is allowed to run. Renderers
  # exceeding this time are killed softly (i.e. the time is not a guaranteed
  # maximum, but will be used as a guide).
  max_execution_time = 60

  def __init__(self):
    if self.method not in ["GET", "POST", "PUT", "DELETE"]:
      raise ValueError("ApiRenderer's method should be either GET, POST, PUT "
                       "or DELETE.")

    if not self.route:
      raise ValueError("ApiRenderer's route should be set.")

  def Render(self, request):
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


def BuildRoutingMap():
  """Builds Werkzeug routing map for all the API renderers."""

  rules = []

  for candidate in ApiRenderer.classes.values():
    if candidate.route:
      rules.append(routing.Rule(candidate.route, methods=[candidate.method],
                                endpoint=candidate))

  return routing.Map(rules)


ROUTING_MAP = None


def GetRendererForRequest(request):
  """Returns a renderer to handle given HTTP request."""

  global ROUTING_MAP

  if not ROUTING_MAP:
    ROUTING_MAP = BuildRoutingMap()

  matcher = ROUTING_MAP.bind("%s:%s" % (request.environ["SERVER_NAME"],

                                        request.environ["SERVER_PORT"]))
  try:
    match = matcher.match(request.path, request.method)
  except werkzeug_exceptions.NotFound:
    raise ApiRendererNotFoundError("No API renderer was found for (%s) %s" % (
        request.path,
        request.method))

  renderer_cls, route_args = match
  return (renderer_cls(), route_args)


def RenderResponse(request):
  """Handles given HTTP request with one of the available API renderers."""

  renderer, route_args = GetRendererForRequest(request)

  if renderer.method == "GET":
    if hasattr(request.GET, "dict"):
      request_data_obj = utils.DataObject(request.GET.dict())
    else:
      request_data_obj = utils.DataObject(request.GET)

  elif renderer.method == "POST":
    if hasattr(request.POST, "dict"):
      request_data_obj = utils.DataObject(request.POST.dict())
    else:
      request_data_obj = utils.DataObject(request.POST)

  for k, v in route_args.items():
    request_data_obj[k] = v

  request_data_obj.token = BuildToken(request, renderer.max_execution_time)

  rendered_data = renderer.Render(request_data_obj)
  response = http.HttpResponse(content_type="application/json")
  response.write(json.dumps(rendered_data))

  return response
