#!/usr/bin/env python
"""API handler for rendering descriptors of GRR data structures."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import reflection_pb2
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_value_renderers


def _GetAllRDFTypes():
  all_types = rdfvalue.RDFValue.classes.copy()

  # We shouldn't render base RDFValue class.
  all_types.pop(rdfvalue.RDFValue.__name__, None)
  all_types.pop(rdfvalue.RDFPrimitive.__name__, None)

  # Remove primitive `bool` (that shouldn't be there).
  all_types.pop("bool", None)

  return all_types


class ApiGetRDFValueDescriptorArgs(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiGetRDFValueDescriptorArgs


class ApiGetRDFValueDescriptorHandler(api_call_handler_base.ApiCallHandler):
  """Renders descriptor of a given RDFValue type."""

  args_type = ApiGetRDFValueDescriptorArgs
  result_type = api_value_renderers.ApiRDFValueDescriptor

  def Handle(self, args, context=None):
    _ = context

    rdfvalue_class = _GetAllRDFTypes()[args.type]
    return api_value_renderers.BuildTypeDescriptor(rdfvalue_class)


class ApiListRDFValueDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiListRDFValueDescriptorsResult
  rdf_deps = [
      api_value_renderers.ApiRDFValueDescriptor,
  ]


class ApiListRDFValuesDescriptorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders descriptors of all available RDFValues."""

  result_type = ApiListRDFValueDescriptorsResult

  def Handle(self, unused_args, context=None):
    result = ApiListRDFValueDescriptorsResult()

    all_types = _GetAllRDFTypes()
    for cls_name in sorted(all_types):
      cls = all_types[cls_name]
      result.items.append(api_value_renderers.BuildTypeDescriptor(cls))

    return result


class ApiMethod(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiMethod
  rdf_deps = [
      api_value_renderers.ApiRDFValueDescriptor,
  ]


class ApiListApiMethodsResult(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiListApiMethodsResult
  rdf_deps = [
      ApiMethod,
  ]


class ApiListApiMethodsHandler(api_call_handler_base.ApiCallHandler):
  """Renders HTTP API docs sources."""

  result_type = ApiListApiMethodsResult

  def __init__(self, router):
    self.router = router

  def Handle(self, unused_args, context=None):
    router_methods = self.router.__class__.GetAnnotatedMethods()

    result = ApiListApiMethodsResult()
    for router_method in router_methods.values():
      api_method = ApiMethod(
          name=router_method.name,
          category=router_method.category,
          doc=router_method.doc,
          http_route=router_method.http_methods[-1][1],
          http_methods=[router_method.http_methods[-1][0]],
      )

      if router_method.args_type:
        api_method.args_type_descriptor = (
            api_value_renderers.BuildTypeDescriptor(router_method.args_type)
        )

      if router_method.result_type:
        if router_method.result_type == router_method.BINARY_STREAM_RESULT_TYPE:
          api_method.result_kind = api_method.ResultKind.BINARY_STREAM
        else:
          api_method.result_kind = api_method.ResultKind.VALUE
          api_method.result_type_descriptor = (
              api_value_renderers.BuildTypeDescriptor(router_method.result_type)
          )
      else:
        api_method.result_kind = api_method.ResultKind.NONE

      result.items.append(api_method)

    return result
