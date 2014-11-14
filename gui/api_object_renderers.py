#!/usr/bin/env python
"""This module contains RESTful API renderers for AFF4 objects and RDFValues."""


import itertools
import numbers
import re


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import structs


class ApiObjectRenderer(object):
  """Baseclass for restful API objects rendering classes."""

  __metaclass__ = registry.MetaclassRegistry

  # API renderers can render RDFValues and AFF4Objects. Each renderer has
  # to be bound either to a single AFF4 type or to a rdfvalue type.
  aff4_type = None
  rdfvalue_type = None

  def __init__(self):
    if self.aff4_type and self.rdfvalue_type:
      raise ValueError("Can't have both aff4_type and rdfvalue_type set.")

    if not self.aff4_type and not self.rdfvalue_type:
      raise ValueError("Have to set either aff4_type or rdfvalue_type.")

  _type_list_cache = {}

  def GetTypeList(self, value):
    try:
      return ApiObjectRenderer._type_list_cache[value.__class__.__name__]
    except KeyError:
      type_list = [klass.__name__ for klass in value.__class__.__mro__]
      ApiObjectRenderer._type_list_cache[value.__class__.__name__] = type_list
      return type_list

  def _ToPrimitive(self, value, request):
    """Function used to convert values to JSON-friendly data structure.

    Args:
      value: An value to convert. May be either a plain Python value,
             an RDFValue or an Enum.
      request: Request parameters dictionary.

    Returns:
      JSON-friendly data: a string, a number, a dict or an array.
    """
    limit_lists = int(request.get("limit_lists", 0))
    no_lists = request.get("no_lists", False)

    # We use RenderObject (main function of this module) to render
    # all AFF4 and RDF values.
    if isinstance(value, rdfvalue.RDFValue):
      return RenderObject(value, request)
    # Repeated fields get converted to lists with each value
    # being recursively converted with _ToPrimitive().
    if isinstance(value, structs.RepeatedFieldHelper):
      if no_lists:
        return []

      return list(self._ToPrimitive(v, request) for v in value)
    # Plain dictionaries are converted to dictionaries with each value
    # being recursively converted with _ToPrimitive().
    elif isinstance(value, dict):
      result = {}
      for k, v in value.items():
        if isinstance(v, structs.RepeatedFieldHelper):
          if no_lists:
            continue

          if limit_lists and len(v) > 10:
            result[k] = self._ToPrimitive(v[:limit_lists], request)
            result[k + "_fetch_more_url"] = "to_be_implemented"
          else:
            result[k] = self._ToPrimitive(v, request)
        else:
          result[k] = self._ToPrimitive(v, request)

      return result
    # Enums are converted to strings representing the name of the value.
    elif isinstance(value, structs.Enum):
      return value.name
    # Make sure string values are properly encoded, otherwise we may have
    # problems with JSON-encoding them.
    elif isinstance(value, basestring):
      return utils.SmartUnicode(value)
    # Numbers are returned as-is.
    elif isinstance(value, numbers.Number):
      return value
    # Everything else is returned in as string.
    else:
      return utils.SmartUnicode(value)

  def RenderObject(self, obj, request):
    """Renders given object as plain JSON-friendly data structure."""
    raise NotImplementedError()


class RDFValueApiObjectRenderer(ApiObjectRenderer):
  """Renderer for a generic rdfvalue."""

  rdfvalue_type = "RDFValue"

  def RenderObject(self, value, request):
    with_type_info = request.get("with_type_info", False)

    result = value.SerializeToDataStore()
    if isinstance(result, basestring):
      result = utils.SmartUnicode(result)

    if with_type_info:
      result = dict(type=value.__class__.__name__,
                    mro=self.GetTypeList(value),
                    value=result,
                    age=value.age.AsSecondsFromEpoch())

    return result


class RDFValueArrayApiObjectRenderer(RDFValueApiObjectRenderer):
  """Renderer for RDFValueArray."""

  rdfvalue_type = "RDFValueArray"

  def RenderObject(self, value, request):
    return list(self._ToPrimitive(v, request) for v in value)


class FlowStateApiObjectRenderer(RDFValueApiObjectRenderer):
  """Renderer for FlowState."""

  rdfvalue_type = "FlowState"

  def RenderObject(self, value, request):
    return self._ToPrimitive(value.data, request)


class DataBlobApiObjectRenderer(RDFValueApiObjectRenderer):
  """Renderer for DataBlob."""

  rdfvalue_type = "DataBlob"

  def RenderObject(self, value, request):
    return self._ToPrimitive(value.GetValue(), request)


class EmbeddedRDFValueApiObjectRenderer(RDFValueApiObjectRenderer):
  """Renderer for EmbeddedRDFValue."""

  rdfvalue_type = "EmbeddedRDFValue"

  def RenderObject(self, value, request):
    return self._ToPrimitive(value.payload, request)


class RDFProtoStructApiObjectRenderer(ApiObjectRenderer):
  """Renderer for RDFProtoStructs."""

  rdfvalue_type = "RDFProtoStruct"
  translator = {}

  descriptors_cache = {}

  def RenderObject(self, value, request):
    with_type_info = request.get("with_type_info", False)
    with_descriptors = request.get("with_descriptors", False)

    result = self._ToPrimitive(value.AsDict(), request)
    for key in result.keys():
      if key in self.translator:
        result[key] = self.translator[key](self, value, request)

    # If type information is needed, converted value is placed in the
    # resulting dictionary under the 'value' key.
    if with_type_info:
      result = dict(type=value.__class__.__name__,
                    mro=self.GetTypeList(value),
                    value=result,
                    age=value.age.AsSecondsFromEpoch())

      if with_descriptors:
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

        result["descriptors"] = descriptors
        result["fields_order"] = order

    return result


class GrrMessageApiObjectRenderer(RDFProtoStructApiObjectRenderer):
  """Renderer for GrrMessage objects."""

  rdfvalue_type = "GrrMessage"

  def RenderPayload(self, value, request):
    return self._ToPrimitive(value.payload, request)

  translator = dict(args=RenderPayload)


class AFF4ObjectApiObjectRenderer(ApiObjectRenderer):
  """Renderer for a generic AFF4 object."""

  aff4_type = "AFF4Object"

  def RenderObject(self, aff4_object, request):
    """Render given aff4 object into JSON-serializable data structure."""
    with_type_info = request.get("with_type_info", False)
    with_descriptors = request.get("with_descriptors", False)

    attributes = {}
    for attribute, values in aff4_object.synced_attributes.items():
      attributes[attribute.predicate] = []
      for value in values:
        # This value is really a LazyDecoder() instance. We need to get at the
        # real data here.
        value = value.ToRDFValue()

        if aff4_object.age_policy != aff4.NEWEST_TIME:
          attributes[attribute.predicate].append(self._ToPrimitive(value,
                                                                   request))
        else:
          attributes[attribute.predicate] = self._ToPrimitive(value, request)

    result = dict(aff4_class=aff4_object.__class__.__name__,
                  urn=utils.SmartUnicode(aff4_object.urn),
                  attributes=attributes,
                  age_policy=aff4_object.age_policy)

    if with_type_info and with_descriptors:
      descriptors = {}
      for attribute, _ in aff4_object.synced_attributes.items():
        descriptors[attribute.predicate] = {
            "description": attribute.description
            }

      result["descriptors"] = descriptors

    return result


class RDFValueCollectionApiObjectRenderer(AFF4ObjectApiObjectRenderer):
  """Renderer for RDFValueCollections."""

  aff4_type = "RDFValueCollection"

  def RenderObject(self, aff4_object, request):
    offset = int(request.get("offset", 0))
    count = int(request.get("count", 10000))
    with_total_count = request.get("with_total_count", False)
    filter_value = request.get("filter", "")

    if filter_value:
      index = 0
      items = []
      for item in aff4_object.GenerateItems():
        serialized_item = item.SerializeToString()
        if re.search(re.escape(filter_value), serialized_item, re.I):
          if index >= offset:
            items.append(item)
          index += 1

          if len(items) >= count:
            break
    else:
      items = itertools.islice(aff4_object.GenerateItems(),
                               offset, offset + count)

    rendered_object = super(RDFValueCollectionApiObjectRenderer,
                            self).RenderObject(aff4_object, request)
    rendered_object["offset"] = offset
    rendered_object["items"] = [self._ToPrimitive(item, request)
                                for item in items]

    if with_total_count:
      if hasattr(aff4_object, "CalculateLength"):
        total_count = aff4_object.CalculateLength()
      else:
        total_count = len(aff4_object)
      rendered_object["total_count"] = total_count

    return rendered_object


class VFSGRRClientApiObjectRenderer(AFF4ObjectApiObjectRenderer):
  """Renderer for VFSGRRClient objects."""

  aff4_type = "VFSGRRClient"

  def RenderObject(self, aff4_object, request):

    rendered_object = super(VFSGRRClientApiObjectRenderer, self).RenderObject(
        aff4_object, request)
    rendered_object["summary"] = self._ToPrimitive(aff4_object.GetSummary(),
                                                   request)
    return rendered_object


RENDERERS_CACHE = {}


def RenderObject(obj, request=None):
  """Handler for the /api/aff4 requests."""

  if request is None:
    request = {}

  if isinstance(obj, aff4.AFF4Object):
    is_aff4 = True
    key = "aff4." + obj.__class__.__name__
  elif isinstance(obj, rdfvalue.RDFValue):
    is_aff4 = False
    key = "rdfvalue." + obj.__class__.__name__
  else:
    raise ValueError("Can't render object that's neither AFF4Object nor "
                     "RDFValue: %s." % utils.SmartStr(obj))

  try:
    renderer_cls = RENDERERS_CACHE[key]
  except KeyError:
    candidates = []
    for candidate in ApiObjectRenderer.classes.values():
      if is_aff4 and candidate.aff4_type:
        candidate_class = aff4.AFF4Object.classes[candidate.aff4_type]
      elif candidate.rdfvalue_type:
        candidate_class = rdfvalue.RDFValue.classes[candidate.rdfvalue_type]
      else:
        continue

      if aff4.issubclass(obj.__class__, candidate_class):
        candidates.append((candidate, candidate_class))

    if not candidates:
      raise RuntimeError("No renderer found for object %s." %
                         obj.__class__.__name__)

    candidates = sorted(candidates,
                        key=lambda candidate: len(candidate[1].mro()))
    renderer_cls = candidates[-1][0]
    RENDERERS_CACHE[key] = renderer_cls

  api_renderer = renderer_cls()
  rendered_data = api_renderer.RenderObject(obj, request)

  return rendered_data
