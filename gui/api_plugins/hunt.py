#!/usr/bin/env python
"""API renderers for accessing hunts."""

import operator

from grr.gui import api_object_renderers
from grr.gui import api_renderers

from grr.lib import aff4
from grr.lib import hunts
from grr.lib import rdfvalue


HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class ApiHuntsListRenderer(api_renderers.ApiRenderer):

  method = "GET"
  route = "/api/hunts"

  def Render(self, request):
    offset = int(request.get("offset", 0))
    count = int(request.get("count", 10000))

    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=request.token)

    children = list(fd.ListChildren())
    children.sort(key=operator.attrgetter("age"), reverse=True)
    children = children[offset:offset + count]

    hunt_list = []
    for hunt in fd.OpenChildren(children=children):
      if not isinstance(hunt, hunts.GRRHunt) or not hunt.state:
        continue

      hunt.create_time = hunt.GetRunner().context.create_time
      hunt_list.append(hunt)

    hunt_list.sort(key=lambda x: x.create_time, reverse=True)

    encoded_hunt_list = []
    for hunt in hunt_list:
      encoded_hunt = api_object_renderers.RenderObject(
          hunt, {"no_lists": True})
      encoded_hunt["create_time"] = api_object_renderers.RenderObject(
          hunt.create_time)
      encoded_hunt["description"] = hunt.state.context.args.description
      encoded_hunt_list.append(encoded_hunt)

    return encoded_hunt_list


class ApiHuntSummaryRenderer(api_renderers.ApiRenderer):
  """Renders hunt's summary."""

  method = "GET"
  route = "/api/hunts/<hunt_id>"

  def Render(self, request):
    hunt = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(request.route_args["hunt_id"]),
        aff4_type="GRRHunt",
        token=request.token)
    return api_object_renderers.RenderObject(hunt, {})


class ApiHuntLogRenderer(api_renderers.ApiRenderer):
  """Renders hunt's log."""

  method = "GET"
  route = "/api/hunts/<hunt_id>/log"

  def Render(self, request):
    logs_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(request.route_args["hunt_id"]).Add("log"),
        aff4_type="RDFValueCollection", mode="r", token=request.token)
    return api_object_renderers.RenderObject(logs_collection, {})


class ApiHuntErrorsRenderer(api_renderers.ApiRenderer):
  """Renders hunt's errors."""

  method = "GET"
  route = "/api/hunts/<hunt_id>/errors"

  def Render(self, request):
    errors_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(request.route_args["hunt_id"]).Add("errors"),
        aff4_type="RDFValueCollection", mode="r", token=request.token)
    return api_object_renderers.RenderObject(errors_collection, {})
