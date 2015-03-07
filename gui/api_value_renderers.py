#!/usr/bin/env python
"""Renderers that render RDFValues into JSON compatible data structures."""



import base64
import numbers


from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import structs


class ApiValueRenderer(object):
  """Baseclass for API renderers that render RDFValues."""

  __metaclass__ = registry.MetaclassRegistry

  value_class = object

  _type_list_cache = {}
  _renderers_cache = {}

  @classmethod
  def GetRendererForValue(cls, value, with_types=False, with_metadata=False,
                          limit_lists=-1):
    """Returns renderer corresponding to a given value and rendering args."""

    cache_key = "%s_%s_%s_%d" % (value.__class__.__name__,
                                 with_types,
                                 with_metadata,
                                 limit_lists)
    try:
      renderer_cls = cls._renderers_cache[cache_key]
    except KeyError:
      candidates = []
      for candidate in ApiValueRenderer.classes.values():
        if candidate.value_class:
          candidate_class = candidate.value_class
        else:
          continue

        if isinstance(value, candidate_class):
          candidates.append((candidate, candidate_class))

      if not candidates:
        raise RuntimeError("No renderer found for value %s." %
                           value.__class__.__name__)

      candidates = sorted(candidates,
                          key=lambda candidate: len(candidate[1].mro()))
      renderer_cls = candidates[-1][0]
      cls._renderers_cache[cache_key] = renderer_cls

    return renderer_cls(with_types=with_types,
                        with_metadata=with_metadata,
                        limit_lists=limit_lists)

  def __init__(self, with_types=False, with_metadata=False,
               limit_lists=-1):
    super(ApiValueRenderer, self).__init__()

    self.with_types = with_types
    self.with_metadata = with_metadata
    self.limit_lists = limit_lists

  def _PassThrough(self, value):
    renderer = ApiValueRenderer.GetRendererForValue(
        value, with_types=self.with_types, with_metadata=self.with_metadata,
        limit_lists=self.limit_lists)
    return renderer.RenderValue(value)

  def _GetTypeList(self, value):
    try:
      return ApiValueRenderer._type_list_cache[value.__class__.__name__]
    except KeyError:
      type_list = [klass.__name__ for klass in value.__class__.__mro__]
      ApiValueRenderer._type_list_cache[value.__class__.__name__] = type_list
      return type_list

  def _IncludeTypeInfoIfNeeded(self, result, original_value):
    # If type information is needed, converted value is placed in the
    # resulting dictionary under the 'value' key.
    if self.with_types:
      if hasattr(original_value, "age"):
        age = original_value.age.AsSecondsFromEpoch()
      else:
        age = 0

      return dict(type=original_value.__class__.__name__,
                  mro=self._GetTypeList(original_value),
                  value=result,
                  age=age)
    else:
      return result

  def RenderValue(self, value):
    return self._IncludeTypeInfoIfNeeded(utils.SmartUnicode(value), value)


class ApiNumberRenderer(ApiValueRenderer):
  """Renderer for numbers."""

  value_class = numbers.Number

  def RenderValue(self, value):
    # Numbers are returned as-is.
    return self._IncludeTypeInfoIfNeeded(value, value)


class ApiStringRenderer(ApiValueRenderer):
  """Renderer for strings."""

  value_class = basestring

  def RenderValue(self, value):
    return self._IncludeTypeInfoIfNeeded(utils.SmartUnicode(value), value)


class ApiBytesRenderer(ApiValueRenderer):
  """Renderer for RDFBytes."""

  value_class = bytes

  def RenderValue(self, value):
    result = base64.b64encode(value)
    return self._IncludeTypeInfoIfNeeded(result, value)


class ApiEnumRenderer(ApiValueRenderer):
  """Renderer for deprecated (old-style) enums."""

  value_class = structs.Enum

  def RenderValue(self, value):
    return self._IncludeTypeInfoIfNeeded(value.name, value)


class ApiEnumNamedValueRenderer(ApiValueRenderer):
  """Renderer for new-style enums."""

  value_class = structs.EnumNamedValue

  def RenderValue(self, value):
    return self._IncludeTypeInfoIfNeeded(value.name, value)


class ApiDictRenderer(ApiValueRenderer):
  """Renderer for dicts."""

  value_class = dict

  def RenderValue(self, value):
    result = {}
    for k, v in value.items():
      result[k] = self._PassThrough(v)

    return result


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
        if self.with_types:
          result.append(dict(age=0,
                             mro=["FetchMoreLink"],
                             type="FetchMoreLink",
                             url="to/be/implemented"))
        else:
          result.append("<more items available>")

    return result


class ApiRepeatedFieldHelperRenderer(ApiListRenderer):
  """Renderer for repeated fields helpers."""

  value_class = structs.RepeatedFieldHelper


class ApiRDFValueArrayRenderer(ApiListRenderer):
  """Renderer for RDFValueArray."""

  value_class = rdfvalue.RDFValueArray


class ApiRDFBoolRenderer(ApiValueRenderer):
  """Renderer for RDFBool."""

  value_class = rdfvalue.RDFBool

  def RenderValue(self, value):
    return self._IncludeTypeInfoIfNeeded(value != 0, value)


class ApiRDFBytesRenderer(ApiValueRenderer):
  """Renderer for RDFBytes."""

  value_class = rdfvalue.RDFBytes

  def RenderValue(self, value):
    result = base64.b64encode(value.SerializeToString())
    return self._IncludeTypeInfoIfNeeded(result, value)


class ApiRDFStringRenderer(ApiValueRenderer):
  """Renderer for RDFString."""

  value_class = rdfvalue.RDFString

  def RenderValue(self, value):
    result = utils.SmartUnicode(value)
    return self._IncludeTypeInfoIfNeeded(result, value)


class ApiRDFIntegerRenderer(ApiValueRenderer):
  """Renderer for RDFInteger."""

  value_class = rdfvalue.RDFInteger

  def RenderValue(self, value):
    result = int(value)
    return self._IncludeTypeInfoIfNeeded(result, value)


class ApiFlowStateRenderer(ApiValueRenderer):
  """Renderer for FlowState."""

  value_class = rdfvalue.FlowState

  def RenderValue(self, value):
    return self._PassThrough(value.data)


class ApiDataBlobRenderer(ApiValueRenderer):
  """Renderer for DataBlob."""

  value_class = rdfvalue.DataBlob

  def RenderValue(self, value):
    return self._PassThrough(value.GetValue())


class ApiEmbeddedRDFValueRenderer(ApiValueRenderer):
  """Renderer for EmbeddedRDFValue."""

  value_class = rdfvalue.EmbeddedRDFValue

  def RenderValue(self, value):
    return self._PassThrough(value.payload)


class ApiRDFProtoStructRenderer(ApiValueRenderer):
  """Renderer for RDFProtoStructs."""

  value_class = rdfvalue.RDFProtoStruct

  processors = []

  descriptors_cache = {}

  def RenderValue(self, value):
    result = value.AsDict()
    for k, v in value.AsDict().items():
      result[k] = self._PassThrough(v)

    for processor in self.processors:
      result = processor(self, result, value)

    result = self._IncludeTypeInfoIfNeeded(result, value)

    if self.with_metadata:
      try:
        descriptors, order = self.descriptors_cache[value.__class__.__name__]
      except KeyError:
        descriptors = {}
        order = []
        for descriptor, _ in value.ListFields():
          order.append(descriptor.name)
          descriptors[descriptor.name] = {
              "friendly_name": descriptor.friendly_name,
              "description": descriptor.description
          }

        self.descriptors_cache[value.__class__.__name__] = (descriptors,
                                                            order)

      result["metadata"] = descriptors
      result["fields_order"] = order

    return result


class ApiGrrMessageRenderer(ApiRDFProtoStructRenderer):
  """Renderer for GrrMessage objects."""

  value_class = rdfvalue.GrrMessage

  def RenderPayload(self, result, value):
    """Renders GrrMessage payload and renames args_rdf_name field."""
    if "args_rdf_name" in result:
      result["payload_type"] = result["args_rdf_name"]    
      del result["args_rdf_name"]

    if "args" in result:
      result["payload"] = self._PassThrough(value.payload)
      del result["args"]
    
    return result

  processors = [RenderPayload]


def RenderValue(value, with_types=False, with_metadata=False,
                limit_lists=-1):
  if value is None:
    return None

  renderer = ApiValueRenderer.GetRendererForValue(value,
                                                  with_types=with_types,
                                                  with_metadata=with_metadata,
                                                  limit_lists=limit_lists)
  return renderer.RenderValue(value)
