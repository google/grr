#!/usr/bin/env python
"""API handler for rendering descriptors of GRR data structures."""

from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


def _GetAllTypes():
  # We have to provide info for python primitive types as well, as sometimes
  # they may be used within FlowState objects.
  all_types = rdfvalue.RDFValue.classes.copy()
  # We shouldn't render base RDFValue class.
  all_types.pop("RDFValue", None)

  for cls in [bool, int, float, long, str, unicode, list, tuple]:
    all_types[cls.__name__] = cls

  return all_types


class ApiGetRDFValueDescriptorArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetRDFValueDescriptorArgs


class ApiGetRDFValueDescriptorHandler(api_call_handler_base.ApiCallHandler):
  """Renders descriptor of a given RDFValue type."""

  args_type = ApiGetRDFValueDescriptorArgs
  result_type = api_value_renderers.ApiRDFValueDescriptor

  def Handle(self, args, token=None):
    _ = token

    rdfvalue_class = _GetAllTypes()[args.type]
    return api_value_renderers.BuildTypeDescriptor(rdfvalue_class)


class ApiListRDFValueDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListRDFValueDescriptorsResult


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

    return result


class ApiAff4AttributeDescriptor(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiAff4AttributeDescriptor


class ApiListAff4AttributeDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListAff4AttributeDescriptorsResult


class ApiListAff4AttributeDescriptorsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders available aff4 attributes."""

  result_type = ApiListAff4AttributeDescriptorsResult

  def Handle(self, unused_args, token=None):
    _ = token

    result = ApiListAff4AttributeDescriptorsResult()
    for name in sorted(aff4.Attribute.NAMES.keys()):
      result.items.append(ApiAff4AttributeDescriptor(name=name))

    return result
