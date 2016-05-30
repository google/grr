#!/usr/bin/env python
"""API handler for rendering API docs."""

from grr.gui import api_call_handler_base

CATEGORY = "Other"


class ApiGetDocsHandler(api_call_handler_base.ApiCallHandler):
  """Renders HTTP API docs sources."""

  category = CATEGORY

  def RenderApiCallHandlers(self):
    # NOTE: there's practically nothing we can do: ApiCallRouterWithoutChecks
    # references docs handler and docs handler has to references
    # ApiCallRouterWithoutChecks.
    #
    # pylint: disable=g-import-not-at-top
    from grr.gui import api_call_router_without_checks
    # pylint: enable=g-import-not-at-top

    router_cls = api_call_router_without_checks.ApiCallRouterWithoutChecks
    router = router_cls()
    router_methods = router_cls.GetAnnotatedMethods()

    result = []
    for router_method in router_methods.values():
      handler = getattr(router, router_method.name)(None)

      result.append(dict(
          route=router_method.http_methods[-1][1],
          handler=handler.__class__.__name__, category=router_method.category,
          methods=[router_method.http_methods[-1][0]], doc=handler.__doc__,
          args_type=(router_method.args_type and
                     router_method.args_type.__name__)))

    return result

  def RenderApiObjectRenderers(self, renderers):
    result = {}
    for renderer in renderers:
      if not renderer.aff4_type:
        continue

      result[renderer.aff4_type] = dict(name=renderer.__name__,
                                        doc=renderer.__doc__,
                                        args_type=renderer.args_type and
                                        renderer.args_type.__name__)

    return result

  def Render(self, unused_args, token=None):
    return dict(api_call_handlers=self.RenderApiCallHandlers())
