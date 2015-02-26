#!/usr/bin/env python
"""API renderers for accessing hunts."""

import operator

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import registry

from grr.proto import api_pb2


HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class ApiGRRHuntRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiGRRHuntRendererArgs


class ApiGRRHuntRenderer(
    api_aff4_object_renderers.ApiAFF4ObjectRendererBase):
  """Renderer for GRRHunt objects."""

  aff4_type = "GRRHunt"
  args_type = ApiGRRHuntRendererArgs

  def RenderObject(self, hunt, args):
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

    if args.with_full_summary:
      all_clients_count, completed_clients_count, _ = hunt.GetClientsCounts()

      untyped_summary_part.update(dict(
          stats=context.usage_stats,
          all_clients_count=all_clients_count,
          completed_clients_count=completed_clients_count,
          outstanding_clients_count=(
              all_clients_count - completed_clients_count)))

      typed_summary_part = dict(
          regex_rules=runner.args.regex_rules or [],
          integer_rules=runner.args.integer_rules or [],
          args=hunt.state.args)

    for k, v in untyped_summary_part.items():
      untyped_summary_part[k] = api_value_renderers.RenderValue(
          v, limit_lists=10)

    for k, v in typed_summary_part.items():
      typed_summary_part[k] = api_value_renderers.RenderValue(
          v, with_types=True, with_metadata=True, limit_lists=10)

    rendered_object = {
        "summary": dict(untyped_summary_part.items() +
                        typed_summary_part.items())
        }
    return rendered_object


class ApiHuntsListRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntsListRendererArgs


class ApiHuntsListRenderer(api_call_renderers.ApiCallRenderer):
  """Renders list of available hunts."""

  args_type = ApiHuntsListRendererArgs

  def _RenderHuntList(self, hunt_list):
    hunts_list = sorted(hunt_list, reverse=True,
                        key=lambda hunt: hunt.GetRunner().context.create_time)

    encoded_hunt_list = []
    for hunt in hunts_list:
      encoded_hunt = api_aff4_object_renderers.RenderAFF4Object(
          hunt, [rdfvalue.ApiAFF4ObjectRendererArgs(limit_lists=0)])
      encoded_hunt_list.append(encoded_hunt)

    return encoded_hunt_list

  def Render(self, args, token=None):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=token)

    children = list(fd.ListChildren())
    children.sort(key=operator.attrgetter("age"), reverse=True)
    if args.count:
      children = children[args.offset:args.offset + args.count]
    else:
      children = children[args.offset:]

    hunt_list = []
    for hunt in fd.OpenChildren(children=children):
      if not isinstance(hunt, hunts.GRRHunt) or not hunt.state:
        continue

      hunt_list.append(hunt)

    return dict(total_count=len(children),
                offset=args.offset,
                count=len(hunt_list),
                items=self._RenderHuntList(hunt_list))


class ApiHuntSummaryRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntSummaryRendererArgs


class ApiHuntSummaryRenderer(api_call_renderers.ApiCallRenderer):
  """Renders hunt's summary."""

  args_type = ApiHuntSummaryRendererArgs

  def Render(self, args, token=None):
    hunt = aff4.FACTORY.Open(HUNTS_ROOT_PATH.Add(args.hunt_id),
                             aff4_type="GRRHunt", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        hunt, [ApiGRRHuntRendererArgs(with_full_summary=True),
               rdfvalue.ApiAFF4ObjectRendererArgs(limit_lists=10)])


class ApiHuntLogRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntLogRendererArgs


class ApiHuntLogRenderer(api_call_renderers.ApiCallRenderer):
  """Renders hunt's log."""

  args_type = ApiHuntLogRendererArgs

  def Render(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open logs collection.
    logs_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Logs"),
        aff4_type="RDFValueCollection", mode="r", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        logs_collection,
        [rdfvalue.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, with_total_count=True,
            items_type_info="WITH_TYPES_AND_METADATA")])


class ApiHuntErrorsRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntErrorsRendererArgs


class ApiHuntErrorsRenderer(api_call_renderers.ApiCallRenderer):
  """Renders hunt's errors."""

  args_type = ApiHuntErrorsRendererArgs

  def Render(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open errors collection.
    errors_collection = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ErrorClients"),
        aff4_type="RDFValueCollection", mode="r", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        errors_collection,
        [rdfvalue.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, with_total_count=True,
            items_type_info="WITH_TYPES_AND_METADATA")])


class ApiHuntsInitHook(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/hunts", ApiHuntsListRenderer)
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/hunts/<hunt_id>", ApiHuntSummaryRenderer)
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/hunts/<hunt_id>/errors", ApiHuntErrorsRenderer)
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/hunts/<hunt_id>/log", ApiHuntLogRenderer)
