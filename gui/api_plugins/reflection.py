#!/usr/bin/env python
"""API renderer for rendering descriptors of GRR data structures."""

import logging

from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import type_info

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiRDFValueReflectionRendererArgs(rdf_structs.RDFProtoStruct):
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

      if field_type == rdf_structs.EnumNamedValue:
        allowed_values = []
        for enum_label in sorted(field_desc.enum, key=field_desc.enum.get):
          enum_value = field_desc.enum[enum_label]
          allowed_values.append(dict(name=enum_label,
                                     value=int(enum_value),
                                     doc=enum_value.description))
        field["allowed_values"] = allowed_values

      field_default = None
      if (field_desc.default is not None
          and not aff4.issubclass(field_type, rdf_structs.RDFStruct)
          and hasattr(field_desc, "GetDefault")):
        field_default = field_desc.GetDefault()
        field["default"] = api_value_renderers.RenderValue(
            field_default, with_types=True)

      if field_desc.description:
        field["doc"] = field_desc.description

      if field_desc.friendly_name:
        field["friendly_name"] = field_desc.friendly_name

      if field_desc.labels:
        field["labels"] = [rdf_structs.SemanticDescriptor.Labels.reverse_enum[x]
                           for x in field_desc.labels]

      fields.append(field)

    struct_default = None
    try:
      struct_default = cls()
    except Exception as e:   # pylint: disable=broad-except
      # TODO(user): Some RDFStruct classes can't be constructed using
      # default constructor (without arguments). Fix the code so that
      # we can either construct all the RDFStruct classes with default
      # constructors or know exactly which classes can't be constructed
      # with default constructors.
      logging.exception("Can't create default for struct %s: %s",
                        field_type.__name__, e)

    result = dict(name=cls.__name__,
                  doc=cls.__doc__ or "",
                  fields=fields,
                  kind="struct")

    if struct_default is not None:
      result["default"] = api_value_renderers.RenderValue(struct_default,
                                                          with_types=True)

    if getattr(cls, "union_field", None):
      result["union_field"] = cls.union_field

    return result

  def RenderPrimitiveRDFValue(self, cls):
    result = dict(name=cls.__name__,
                  doc=cls.__doc__ or "",
                  kind="primitive")
    try:
      default_value = api_value_renderers.RenderValue(cls(), with_types=True)
      result["default"] = default_value
    except Exception as e:   # pylint: disable=broad-except
      logging.exception("Can't create default for primitive %s: %s",
                        cls.__name__, e)

    return result

  def RenderType(self, cls):
    if aff4.issubclass(cls, rdf_structs.RDFStruct):
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
