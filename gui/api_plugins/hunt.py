#!/usr/bin/env python
"""API renderers for accessing hunts."""

import operator

from grr.gui import api_object_renderers
from grr.gui import api_renderers

from grr.lib import aff4
from grr.lib import hunts
from grr.lib import rdfvalue


HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class GRRHuntApiObjectRenderer(
    api_object_renderers.AFF4ObjectApiObjectRenderer):
  """Renderer for GRRHunt objects."""

  aff4_type = "GRRHunt"

  def RenderObject(self, hunt, request):
    with_full_summary = request.get("with_full_summary", False)

    rendered_object = super(GRRHuntApiObjectRenderer, self).RenderObject(
        hunt, request)

    runner = hunt.GetRunner()
    context = runner.context

    untyped_summary_part = dict(
        state=hunt.Get(hunt.Schema.STATE),
        hunt_name=context.args.hunt_name,
        create_time=context.create_time,
        expires=context.expires,
        client_limit=context.args.client_limit,
        client_rate=context.args.client_rate,
        creator=context.creator,
        description=context.args.description)
    typed_summary_part = {}

    if with_full_summary:
      all_clients_count, completed_clients_count, _ = hunt.GetClientsCounts()

      untyped_summary_part.update(dict(
          stats=context.usage_stats,
          all_clients_count=all_clients_count,
          completed_clients_count=completed_clients_count,
          outstanding_clients_count=(
              all_clients_count - completed_clients_count)))

      typed_summary_part = dict(
          regex_rules=list(runner.args.regex_rules),
          integer_rules=list(runner.args.integer_rules),
          args=hunt.state.args)

    for k, v in untyped_summary_part.items():
      untyped_summary_part[k] = api_object_renderers.RenderObject(v)

    for k, v in typed_summary_part.items():
      typed_summary_part[k] = api_object_renderers.RenderObject(
          v, dict(with_type_info=True, with_descriptors=True,
                  limit_lists=10))

    rendered_object["summary"] = dict(untyped_summary_part.items() +
                                      typed_summary_part.items())

    return rendered_object


class ApiHuntsListRenderer(api_renderers.ApiRenderer):
  """Renders list of available hunts."""

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

      hunt_list.append(hunt)

    hunt_list.sort(key=lambda hunt: hunt.GetRunner().context.create_time,
                   reverse=True)

    encoded_hunt_list = []
    for hunt in hunt_list:
      encoded_hunt = api_object_renderers.RenderObject(
          hunt, {"no_lists": True})
      encoded_hunt_list.append(encoded_hunt)

    return encoded_hunt_list


class ApiHuntSummaryRenderer(api_renderers.ApiRenderer):
  """Renders hunt's summary."""

  method = "GET"
  route = "/api/hunts/<hunt_id>"

  def Render(self, request):
    hunt = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(request["hunt_id"]),
        aff4_type="GRRHunt",
        token=request.token)
    return api_object_renderers.RenderObject(
        hunt, {"limit_lists": True, "with_full_summary": True})


class ApiHuntLogRenderer(api_renderers.ApiRenderer):
  """Renders hunt's log."""

  method = "GET"
  route = "/api/hunts/<hunt_id>/log"

  def Render(self, request):
    logs_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(request["hunt_id"]).Add("log"),
        aff4_type="RDFValueCollection", mode="r", token=request.token)
    return api_object_renderers.RenderObject(
        logs_collection, {})


class ApiHuntErrorsRenderer(api_renderers.ApiRenderer):
  """Renders hunt's errors."""

  method = "GET"
  route = "/api/hunts/<hunt_id>/errors"

  def Render(self, request):
    errors_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(request["hunt_id"]).Add("errors"),
        aff4_type="RDFValueCollection", mode="r", token=request.token)
    return api_object_renderers.RenderObject(errors_collection, {})
