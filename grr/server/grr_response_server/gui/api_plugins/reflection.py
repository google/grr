#!/usr/bin/env python
"""API handler for rendering descriptors of GRR data structures."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import reflection_pb2
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_value_renderers


def _GetAllTypes():
  # We have to provide info for python primitive types as well, as sometimes
  # they may be used within FlowState objects.
  all_types = rdfvalue.RDFValue.classes.copy()
  # We shouldn't render base RDFValue class.
  all_types.pop(rdfvalue.RDFValue.__name__, None)
  all_types.pop(rdfvalue.RDFPrimitive.__name__, None)

  for cls in [bool, int, float, str]:
    all_types[cls.__name__] = cls

  return all_types


class ApiGetRDFValueDescriptorArgs(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiGetRDFValueDescriptorArgs


class ApiGetRDFValueDescriptorHandler(api_call_handler_base.ApiCallHandler):
  """Renders descriptor of a given RDFValue type."""

  args_type = ApiGetRDFValueDescriptorArgs
  result_type = api_value_renderers.ApiRDFValueDescriptor

  def Handle(self, args, token=None):
    _ = token

    rdfvalue_class = _GetAllTypes()[args.type]
    return api_value_renderers.BuildTypeDescriptor(rdfvalue_class)


class ApiListRDFValueDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = reflection_pb2.ApiListRDFValueDescriptorsResult
  rdf_deps = [
      api_value_renderers.ApiRDFValueDescriptor,
  ]


class ApiListRDFValuesDescriptorsHandler(ApiGetRDFValueDescriptorHandler):
  """Renders descriptors of all available RDFValues."""

  args_type = None
  result_type = ApiListRDFValueDescriptorsResult

  def Handle(self, unused_args, token=None):
    result = ApiListRDFValueDescriptorsResult()

    all_types = _GetAllTypes()
    for cls_name in sorted(all_types):
      cls = all_types[cls_name]
      result.items.append(api_value_renderers.BuildTypeDescriptor(cls))

    # TODO(user): remove this special case as soon as Python 3 migration
    # is done. This is needed, since in Python 2 "bytes" is an alias
    # to "str" and doesn't exist as a standalone type.
    bytes_descriptor = api_value_renderers.ApiRDFValueDescriptor(
        name="bytes",
        parents=["bytes", "object"],
        doc="",
        kind=api_value_renderers.ApiRDFValueDescriptor.Kind.PRIMITIVE,
    )
    result.items.append(bytes_descriptor)

    # TODO(user): remove this special case as soon as Python 3 migration
    # is done. This is needed, since in Python 3 "unicode" is an alias to
    # "str" and doesn't exist as a standalone type.
    unicode_descriptor = api_value_renderers.ApiRDFValueDescriptor(
        name="unicode",
        parents=["unicode", "object"],
        doc="",
        kind=api_value_renderers.ApiRDFValueDescriptor.Kind.PRIMITIVE,
    )
    result.items.append(unicode_descriptor)

    # TODO(user): remove this special case as soon as Python 3 migration
    # is done. This is needed, since in Python 3 "long" is an alias to
    # "int" and doesn't exist as a standalone type.
    unicode_descriptor = api_value_renderers.ApiRDFValueDescriptor(
        name="long",
        parents=["long", "object"],
        doc="",
        kind=api_value_renderers.ApiRDFValueDescriptor.Kind.PRIMITIVE,
    )
    result.items.append(unicode_descriptor)

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

  TYPE_URL_PATTERN = "type.googleapis.com/%s"

  result_type = ApiListApiMethodsResult

  def __init__(self, router):
    self.router = router

  def Handle(self, unused_args, token=None):
    router_methods = self.router.__class__.GetAnnotatedMethods()

    result = ApiListApiMethodsResult()
    for router_method in itervalues(router_methods):
      api_method = ApiMethod(
          name=router_method.name,
          category=router_method.category,
          doc=router_method.doc,
          http_route=router_method.http_methods[-1][1],
          http_methods=[router_method.http_methods[-1][0]])

      if router_method.args_type:
        api_method.args_type_descriptor = (
            api_value_renderers.BuildTypeDescriptor(router_method.args_type))

      if router_method.result_type:
        if router_method.result_type == router_method.BINARY_STREAM_RESULT_TYPE:
          api_method.result_kind = api_method.ResultKind.BINARY_STREAM
        else:
          api_method.result_kind = api_method.ResultKind.VALUE
          api_method.result_type_descriptor = (
              api_value_renderers.BuildTypeDescriptor(
                  router_method.result_type))
      else:
        api_method.result_kind = api_method.ResultKind.NONE

      result.items.append(api_method)

    return result
