#!/usr/bin/env python
"""API renderer for rendering API docs."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderers
from grr.gui import api_value_renderers
from grr.lib import registry


class ApiDocsRenderer(api_call_renderers.ApiCallRenderer):
  """Renders HTTP API docs sources."""

  def RenderArgs(self, args_type):
    if args_type is None:
      return []

    result = []
    for field_number in sorted(args_type.type_infos_by_field_number.keys()):
      descriptor = args_type.type_infos_by_field_number[field_number]
      if descriptor.name == "additional_args":
        continue

      if descriptor.proto_type_name == "bool":
        result.append(dict(name=descriptor.name,
                           type="bool",
                           doc=descriptor.description + "\nPossibe values: " +
                           "1 or 0.",
                           default=descriptor.default and "1" or "0"))
      elif hasattr(descriptor, "enum"):
        possible_values = "\n Possible values: " + ", ".join(
            descriptor.reverse_enum.values())
        result.append(dict(name=descriptor.name,
                           type="Enum",
                           doc=descriptor.description + possible_values,
                           default=descriptor.reverse_enum[descriptor.default]))
      else:
        rendered_default = api_value_renderers.RenderValue(
            descriptor.default, with_types=True, with_metadata=True)
        if descriptor.type:
          type_name = descriptor.type.__name__
        else:
          type_name = descriptor.proto_type
          result.append(dict(name=descriptor.name,
                             type=type_name,
                             doc=descriptor.description,
                             default=rendered_default))

    return result

  def RenderApiCallRenderers(self):
    rules = sorted(api_call_renderers.HTTP_ROUTING_MAP.iter_rules(),
                   key=lambda x: x.rule)

    result = {}
    for rule in rules:
      result[rule.rule] = dict(route=rule.rule,
                               methods=list(rule.methods),
                               doc=rule.endpoint.__doc__,
                               args=self.RenderArgs(rule.endpoint.args_type))

    return result

  def RenderApiObjectRenderers(self):
    renderers = api_aff4_object_renderers.ApiAFF4ObjectRenderer.classes.values()

    result = {}
    for renderer in renderers:
      if not renderer.aff4_type:
        continue

      result[renderer.aff4_type] = dict(
          doc=renderer.__doc__,
          args=self.RenderArgs(renderer.args_type))

    return result

  def Render(self, unused_args, token=None):
    return dict(api_call_renderers=self.RenderApiCallRenderers(),
                api_object_renderers=self.RenderApiObjectRenderers())


class ApiDocsInitHook(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/docs", ApiDocsRenderer)
