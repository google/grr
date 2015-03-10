#!/usr/bin/env python
"""API renderer for rendering descriptors of GRR data structures."""

from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info

from grr.proto import api_pb2


class ApiRDFValueReflectionRendererArgs(rdfvalue.RDFProtoStruct):
  protobuf = api_pb2.ApiRDFValueReflectionRendererArgs


class ApiRDFValueReflectionRenderer(api_call_renderers.ApiCallRenderer):
  """Renders descriptor of a given RDFValue type."""

  args_type = ApiRDFValueReflectionRendererArgs

  def RenderRDFStruct(self, cls):
    fields = []
    for field_desc in cls.type_infos:
      repeated = isinstance(field_desc, type_info.ProtoList)
      if hasattr(field_desc, "delegate"):
        field_desc = field_desc.delegate

      field = {
          "name": field_desc.name,
          "index": field_desc.field_number,
          "repeated": repeated,
          "dynamic": isinstance(field_desc, type_info.ProtoDynamicEmbedded)
      }

      field_type = field_desc.type
      if field_type is not None:
        field["type"] = field_type.__name__

      if field_type == rdfvalue.EnumNamedValue:
        allowed_values = []
        for enum_label in sorted(field_desc.enum):
          enum_value = field_desc.enum[enum_label]
          allowed_values.append(dict(name=enum_label,
                                     value=int(enum_value),
                                     doc=enum_value.description))
        field["allowed_values"] = allowed_values

      if field_desc.default is not None:
        if field_type:
          field_default = field_type(field_desc.default)
        else:
          field_default = field_desc.default

        field["default"] = api_value_renderers.RenderValue(
            field_default, with_types=True)

      if field_desc.description:
        field["doc"] = field_desc.description

      if field_desc.friendly_name:
        field["friendly_name"] = field_desc.friendly_name

      if field_desc.labels:
        field["labels"] = [rdfvalue.SemanticDescriptor.Labels.reverse_enum[x]
                           for x in field_desc.labels]

      fields.append(field)

    return dict(name=cls.__name__,
                doc=cls.__doc__ or "",
                fields=fields,
                kind="struct")

  def RenderPrimitiveRDFValue(self, cls):
    return  dict(name=cls.__name__,
                 doc=cls.__doc__ or "",
                 kind="primitive")

  def RenderType(self, cls):
    if aff4.issubclass(cls, rdfvalue.RDFStruct):
      return self.RenderRDFStruct(cls)
    else:
      return self.RenderPrimitiveRDFValue(cls)

  def Render(self, args, token=None):
    _ = token

    if self.args_type:
      rdfvalue_class = rdfvalue.RDFValue.classes[args.type]
      return self.RenderType(rdfvalue_class)
    else:
      results = {}
      for cls in rdfvalue.RDFValue.classes.values():
        if aff4.issubclass(cls, rdfvalue.RDFValue):
          results[cls.__name__] = self.RenderType(cls)

      return results


class ApiAllRDFValuesReflectionRenderer(ApiRDFValueReflectionRenderer):
  """Renders descriptors of all available RDFValues."""

  args_type = None


class ApiReflectionInitHook(registry.InitHook):

  def RunOnce(self):
    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/reflection/rdfvalue/<type>",
        ApiRDFValueReflectionRenderer)

    api_call_renderers.RegisterHttpRouteHandler(
        "GET", "/api/reflection/rdfvalue/all",
        ApiAllRDFValuesReflectionRenderer)
