#!/usr/bin/env python
"""API renderer for rendering API docs."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderer_base
from grr.gui import http_routing


CATEGORY = "Other"


class ApiDocsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders HTTP API docs sources."""

  category = CATEGORY

  def RenderApiCallRenderers(self, routing_rules):
    result = []
    for rule in routing_rules:
      result.append(dict(route=rule.rule,
                         renderer=rule.endpoint.__name__,
                         category=rule.endpoint.category,
                         methods=list(rule.methods - set(["HEAD"])),
                         doc=rule.endpoint.__doc__,
                         args_type=(rule.endpoint.args_type and
                                    rule.endpoint.args_type.__name__)))

    return result

  def RenderApiObjectRenderers(self, renderers):
    result = {}
    for renderer in renderers:
      if not renderer.aff4_type:
        continue

      result[renderer.aff4_type] = dict(
          name=renderer.__name__,
          doc=renderer.__doc__,
          args_type=renderer.args_type and renderer.args_type.__name__)

    return result

  def Render(self, unused_args, token=None):
    routing_rules = sorted(
        http_routing.HTTP_ROUTING_MAP.iter_rules(),
        key=lambda x: x.rule)

    object_renderers = (api_aff4_object_renderers.ApiAFF4ObjectRenderer.
                        classes.values())

    return dict(
        api_call_renderers=self.RenderApiCallRenderers(routing_rules),
        api_object_renderers=self.RenderApiObjectRenderers(object_renderers)
        )
