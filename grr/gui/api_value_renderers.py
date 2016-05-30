#!/usr/bin/env python
"""Renderers that render RDFValues into JSON compatible data structures."""



import base64
import inspect
import numbers


import logging
from grr.client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs


class Error(Exception):
  pass


class DefaultValueRenderingError(Error):
  pass


class ApiValueRenderer(object):
  """Baseclass for API renderers that render RDFValues."""

  __metaclass__ = registry.MetaclassRegistry

  value_class = object

  _type_list_cache = {}
  _renderers_cache = {}

  @classmethod
  def GetRendererForValueOrClass(cls, value, limit_lists=-1):
    """Returns renderer corresponding to a given value and rendering args."""

    if inspect.isclass(value):
      value_cls = value
    else:
      value_cls = value.__class__

    cache_key = "%s_%d" % (value_cls.__name__, limit_lists)
    try:
      renderer_cls = cls._renderers_cache[cache_key]
    except KeyError:
      candidates = []
      for candidate in ApiValueRenderer.classes.values():
        if candidate.value_class:
          candidate_class = candidate.value_class
        else:
          continue

        if inspect.isclass(value):
          if aff4.issubclass(value_cls, candidate_class):
            candidates.append((candidate, candidate_class))
        else:
          if isinstance(value, candidate_class):
            candidates.append((candidate, candidate_class))

      if not candidates:
        raise RuntimeError("No renderer found for value %s." %
                           value.__class__.__name__)

      candidates = sorted(candidates,
                          key=lambda candidate: len(candidate[1].mro()))
      renderer_cls = candidates[-1][0]
      cls._renderers_cache[cache_key] = renderer_cls

    return renderer_cls(limit_lists=limit_lists)

  def __init__(self, limit_lists=-1):
    super(ApiValueRenderer, self).__init__()

    self.limit_lists = limit_lists

  def _PassThrough(self, value):
    renderer = ApiValueRenderer.GetRendererForValueOrClass(
        value, limit_lists=self.limit_lists)
    return renderer.RenderValue(value)

  def _IncludeTypeInfo(self, result, original_value):
    # Converted value is placed in the resulting dictionary under the 'value'
    # key.
    if hasattr(original_value, "age"):
      age = original_value.age.AsMicroSecondsFromEpoch()
    else:
      age = 0

    return dict(type=original_value.__class__.__name__, value=result, age=age)

  def RenderValue(self, value):
    """Renders given value into plain old python objects."""
    return self._IncludeTypeInfo(utils.SmartUnicode(value), value)

  def RenderDefaultValue(self, value_cls):
    """Renders default value of a given class.

    Args:
      value_cls: Default value of this class will be rendered. This class has
                 to be (or to be a subclass of) a self.value_class (i.e.
                 a class that this renderer is capable of rendering).
    Returns:
      Dictionary with a JSON-rendered value.

    Raises:
      DefaultValueRenderingError: if something goes wrong.
    """
    try:
      return RenderValue(value_cls())
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(e)
      raise DefaultValueRenderingError("Can't create default for value %s: %s" %
                                       (value_cls.__name__, e))

  def RenderMetadata(self, value_cls):
    """Renders metadata of a given value class.

    Args:
      value_cls: Metadata of this class will be rendered. This class has
                 to be (or to be a subclass of) a self.value_class (i.e.
                 a class that this renderer is capable of rendering).
    Returns:
      Dictionary with class metadata.
    """
    result = dict(name=value_cls.__name__,
                  mro=[klass.__name__ for klass in value_cls.__mro__],
                  doc=value_cls.__doc__ or "",
                  kind="primitive")

    result["default"] = self.RenderDefaultValue(value_cls)

    return result


class ApiNumberRenderer(ApiValueRenderer):
  """Renderer for numbers."""

  value_class = numbers.Number

  def RenderValue(self, value):
    # Always render ints as longs - so that there's no ambiguity in the UI
    # renderers when type depends on the value.
    if isinstance(value, int):
      value = long(value)

    return self._IncludeTypeInfo(value, value)


class ApiStringRenderer(ApiValueRenderer):
  """Renderer for strings."""

  value_class = basestring

  def RenderValue(self, value):
    return self._IncludeTypeInfo(utils.SmartUnicode(value), value)


class ApiEnumRenderer(ApiValueRenderer):
  """Renderer for deprecated (old-style) enums."""

  value_class = rdf_structs.Enum

  def RenderValue(self, value):
    return self._IncludeTypeInfo(value.name, value)


class ApiEnumNamedValueRenderer(ApiValueRenderer):
  """Renderer for new-style enums."""

  value_class = rdf_structs.EnumNamedValue

  def RenderValue(self, value):
    return self._IncludeTypeInfo(value.name, value)


class ApiDictRenderer(ApiValueRenderer):
  """Renderer for dicts."""

  value_class = dict

  def RenderValue(self, value):
    result = {}
    for k, v in value.items():
      result[utils.SmartUnicode(k)] = self._PassThrough(v)

    return self._IncludeTypeInfo(result, value)


class ApiRDFDictRenderer(ApiDictRenderer):
  """Renderer for RDF Dict instances."""

  value_class = rdf_protodict.Dict


class FetchMoreLink(rdfvalue.RDFValue):
  """Stub used to display 'More data available...' link."""

  def ParseFromString(self, unused_string):
    pass

  def SerializeToString(self):
    return ""


class ApiListRenderer(ApiValueRenderer):
  """Renderer for lists."""

  value_class = list

  def RenderValue(self, value):
    if self.limit_lists == 0:
      return "<lists are omitted>"
    elif self.limit_lists == -1:
      return [self._PassThrough(v) for v in value]
    else:
      result = [self._PassThrough(v) for v in list(value)[:self.limit_lists]]
      if len(value) > self.limit_lists:
        result.append(dict(age=0,
                           type=FetchMoreLink.__name__,
                           url="to/be/implemented"))

    return result


class ApiTupleRenderer(ApiListRenderer):
  """Renderer for tuples."""

  value_class = tuple


class ApiSetRenderer(ApiListRenderer):
  """Renderer for sets."""

  value_class = set


class ApiRepeatedFieldHelperRenderer(ApiListRenderer):
  """Renderer for repeated fields helpers."""

  value_class = rdf_structs.RepeatedFieldHelper


class ApiRDFValueArrayRenderer(ApiListRenderer):
  """Renderer for RDFValueArray."""

  value_class = rdf_protodict.RDFValueArray


class ApiRDFBoolRenderer(ApiValueRenderer):
  """Renderer for RDFBool."""

  value_class = rdfvalue.RDFBool

  def RenderValue(self, value):
    return self._IncludeTypeInfo(value != 0, value)


class ApiRDFBytesRenderer(ApiValueRenderer):
  """Renderer for RDFBytes."""

  value_class = rdfvalue.RDFBytes

  def RenderValue(self, value):
    result = base64.b64encode(value.SerializeToString())
    return self._IncludeTypeInfo(result, value)


class ApiRDFZippedBytesRenderer(ApiValueRenderer):
  """Renderer for RDFZippedBytes."""

  value_class = rdfvalue.RDFZippedBytes

  def RenderValue(self, value):
    result = base64.b64encode(value.Uncompress())
    return self._IncludeTypeInfo(result, value)


class ApiZippedJSONBytesRenderer(ApiValueRenderer):
  """Renderer for ZippedJSONBytes."""

  value_class = rdf_rekall_types.ZippedJSONBytes

  def RenderValue(self, value):
    result = utils.SmartUnicode(value.Uncompress())
    return self._IncludeTypeInfo(result, value)


class ApiRDFStringRenderer(ApiValueRenderer):
  """Renderer for RDFString."""

  value_class = rdfvalue.RDFString

  def RenderValue(self, value):
    result = utils.SmartUnicode(value)
    return self._IncludeTypeInfo(result, value)


class ApiRDFIntegerRenderer(ApiValueRenderer):
  """Renderer for RDFInteger."""

  value_class = rdfvalue.RDFInteger

  def RenderValue(self, value):
    result = int(value)
    return self._IncludeTypeInfo(result, value)


class ApiFlowStateRenderer(ApiValueRenderer):
  """Renderer for FlowState."""

  value_class = rdf_flows.FlowState

  def RenderValue(self, value):
    return self._PassThrough(value.data)


class ApiDataBlobRenderer(ApiValueRenderer):
  """Renderer for DataBlob."""

  value_class = rdf_protodict.DataBlob

  def RenderValue(self, value):
    return self._PassThrough(value.GetValue())


class ApiRDFURNRenderer(ApiValueRenderer):
  """Renderer for RDFURNs."""

  value_class = rdfvalue.RDFURN

  def RenderDefaultValue(self, value_cls):
    return dict(type=value_cls.__name__, value="", age=0)


class ApiEmbeddedRDFValueRenderer(ApiValueRenderer):
  """Renderer for EmbeddedRDFValue."""

  value_class = rdf_protodict.EmbeddedRDFValue

  def RenderValue(self, value):
    return self._PassThrough(value.payload)


class ApiRDFProtoStructRenderer(ApiValueRenderer):
  """Renderer for RDFProtoStructs."""

  value_class = rdf_structs.RDFProtoStruct

  value_processors = []
  metadata_processors = []

  def RenderValue(self, value):
    result = value.AsDict()
    for k, v in result.items():
      result[k] = self._PassThrough(v)

    for processor in self.value_processors:
      result = processor(self, result, value)

    result = self._IncludeTypeInfo(result, value)

    return result

  def RenderMetadata(self, value_cls):
    fields = []
    for field_desc in value_cls.type_infos:
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

        if field_type.context_help_url:
          field["context_help_url"] = field_type.context_help_url

      if field_type == rdf_structs.EnumNamedValue:
        allowed_values = []
        for enum_label in sorted(field_desc.enum, key=field_desc.enum.get):
          enum_value = field_desc.enum[enum_label]
          labels = [rdf_structs.SemanticDescriptor.Labels.reverse_enum[x]
                    for x in enum_value.labels or []]
          allowed_values.append(dict(name=enum_label,
                                     value=int(enum_value),
                                     labels=labels,
                                     doc=enum_value.description))
        field["allowed_values"] = allowed_values

      field_default = None
      if (field_desc.default is not None and
          not aff4.issubclass(field_type, rdf_structs.RDFStruct) and
          hasattr(field_desc, "GetDefault")):
        field_default = field_desc.GetDefault()
        field["default"] = RenderValue(field_default)

      if field_desc.description:
        field["doc"] = field_desc.description

      if field_desc.friendly_name:
        field["friendly_name"] = field_desc.friendly_name

      if field_desc.labels:
        field["labels"] = [rdf_structs.SemanticDescriptor.Labels.reverse_enum[x]
                           for x in field_desc.labels]

      fields.append(field)

    for processor in self.metadata_processors:
      fields = processor(self, fields)

    result = dict(name=value_cls.__name__,
                  mro=[klass.__name__ for klass in value_cls.__mro__],
                  doc=value_cls.__doc__ or "",
                  fields=fields,
                  kind="struct")

    if getattr(value_cls, "union_field", None):
      result["union_field"] = value_cls.union_field

    struct_default = None
    try:
      struct_default = value_cls()
    except Exception as e:  # pylint: disable=broad-except
      # TODO(user): Some RDFStruct classes can't be constructed using
      # default constructor (without arguments). Fix the code so that
      # we can either construct all the RDFStruct classes with default
      # constructors or know exactly which classes can't be constructed
      # with default constructors.
      logging.debug("Can't create default for struct %s: %s",
                    field_type.__name__, e)

    if struct_default is not None:
      result["default"] = RenderValue(struct_default)

    return result


class ApiGrrMessageRenderer(ApiRDFProtoStructRenderer):
  """Renderer for GrrMessage objects."""

  value_class = rdf_flows.GrrMessage

  def RenderPayload(self, result, value):
    """Renders GrrMessage payload and renames args_rdf_name field."""
    if "args_rdf_name" in result:
      result["payload_type"] = result["args_rdf_name"]
      del result["args_rdf_name"]

    if "args" in result:
      result["payload"] = self._PassThrough(value.payload)
      del result["args"]

    return result

  def RenderPayloadMetadata(self, fields):
    """Payload-aware metadata processor."""

    for f in fields:
      if f["name"] == "args_rdf_name":
        f["name"] = "payload_type"

      if f["name"] == "args":
        f["name"] = "payload"

    return fields

  value_processors = [RenderPayload]
  metadata_processors = [RenderPayloadMetadata]


def RenderValue(value, limit_lists=-1):
  """Render given RDFValue as plain old python objects."""

  if value is None:
    return None

  renderer = ApiValueRenderer.GetRendererForValueOrClass(
      value, limit_lists=limit_lists)
  return renderer.RenderValue(value)


def RenderTypeMetadata(value_cls):
  renderer = ApiValueRenderer.GetRendererForValueOrClass(value_cls)

  return renderer.RenderMetadata(value_cls)
