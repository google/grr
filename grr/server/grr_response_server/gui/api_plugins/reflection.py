#!/usr/bin/env python
"""API handler for rendering descriptors of GRR data structures."""

from grr_response_proto.api import reflection_pb2
from grr_response_server.gui import api_call_handler_base


# TODO: Add tests for this handler.
class ApiListApiMethodsHandler(api_call_handler_base.ApiCallHandler):
  """Renders HTTP API docs sources."""

  proto_result_type = reflection_pb2.ApiListApiMethodsResult

  def __init__(self, router):
    self.router = router

  def Handle(self, unused_args, context=None):
    router_methods = self.router.__class__.GetAnnotatedMethods()

    result = reflection_pb2.ApiListApiMethodsResult()
    for router_method in router_methods.values():
      api_method = reflection_pb2.ApiMethod(
          name=router_method.name,
          category=router_method.category,
          doc=router_method.doc,
          http_route=router_method.http_methods[-1][1],
          http_methods=[router_method.http_methods[-1][0]],
      )

      if router_method.args_type_url:
        api_method.args_type_url = router_method.args_type_url
      if router_method.result_type_url:
        api_method.result_type_url = router_method.result_type_url
      result.items.append(api_method)

    return result
