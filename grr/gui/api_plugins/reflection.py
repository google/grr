#!/usr/bin/env python
"""API handler for rendering descriptors of GRR data structures."""

from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Other"


class ApiGetRDFValueDescriptorArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetRDFValueDescriptorArgs


class ApiGetRDFValueDescriptorHandler(api_call_handler_base.ApiCallHandler):
  """Renders descriptor of a given RDFValue type."""

  category = CATEGORY
  args_type = ApiGetRDFValueDescriptorArgs

  def Render(self, args, token=None):
    _ = token

    # We have to provide info for python primitive types as well, as sometimes
    # they may be used within FlowState objects.
    all_types = dict(rdfvalue.RDFValue.classes.items())
    # We shouldn't render base RDFValue class.
    all_types.pop("RDFValue", None)

    for cls in [bool, int, float, long, str, unicode, list, tuple]:
      all_types[cls.__name__] = cls

    if self.args_type:
      rdfvalue_class = all_types[args.type]
      return api_value_renderers.RenderTypeMetadata(rdfvalue_class)
    else:
      results = {}
      for cls in all_types.values():
        results[cls.__name__] = api_value_renderers.RenderTypeMetadata(cls)

      return results


class ApiListRDFValuesDescriptorsHandler(ApiGetRDFValueDescriptorHandler):
  """Renders descriptors of all available RDFValues."""

  args_type = None


class ApiListAff4AttributesDescriptorsHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders available aff4 attributes."""

  category = CATEGORY

  def Render(self, unused_args, token=None):
    _ = token

    attributes = {}
    for name in sorted(aff4.Attribute.NAMES.keys()):
      attributes[name] = dict(name=name)

    return dict(status="OK", attributes=attributes)
