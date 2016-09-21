#!/usr/bin/env python
"""API handler for rendering API docs."""

from grr.gui import api_call_handler_base

CATEGORY = "Other"


class ApiGetDocsHandler(api_call_handler_base.ApiCallHandler):
  """Renders HTTP API docs sources."""

  category = CATEGORY

  def __init__(self, router):
    self.router = router

  def RenderApiCallHandlers(self):
    router_methods = self.router.__class__.GetAnnotatedMethods()

    result = []
    for router_method in router_methods.values():
      handler = getattr(self.router, router_method.name)(None)

      result.append(
          dict(
              route=router_method.http_methods[-1][1], handler=handler.
              __class__.__name__, category=router_method.category,
              methods=[router_method.http_methods[-1][0]], doc=handler.__doc__,
              args_type=(router_method.args_type and
                         router_method.args_type.__name__)))

    return result

  def Render(self, unused_args, token=None):
    return dict(api_call_handlers=self.RenderApiCallHandlers())
