#!/usr/bin/env python
"""This module contains RESTful API renderers."""


import itertools
import re


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import structs


class ApiRenderer(object):
  """Baseclass for restful API rendering classes."""

  __metaclass__ = registry.MetaclassRegistry

  aff4_type = None

  def RenderObject(self, aff4_object, request):
    """Renders given AFF4 object as plain JSON-friendly data structure."""
    raise NotImplementedError()


class AFF4ObjectApiRenderer(ApiRenderer):
  """Renderer for a generic AFF4 object."""

  aff4_type = "AFF4Object"

  def GetTypeList(self, value):
    return [klass.__name__ for klass in value.__class__.__mro__]

  def ToPrimitive(self, value):
    """Function used to convert values to JSON-friendly data structure.

    Args:
      value: An value to convert. May be either a plain Python value,
             an RDFValue or an Enum.

    Returns:
      JSON-friendly data: a string, a number, a dict or an array.
    """

    # Repeated fields get converted to lists with each value
    # being recursively converted with ToPrimitive().
    if isinstance(value, structs.RepeatedFieldHelper):
      return list(self.ToPrimitive(v) for v in value)
    # rdfvalue.Dict gets converted to a dictionary with each value
    # being recursively converted with ToPrimitive().
    elif isinstance(value, rdfvalue.Dict):
      new_val = value.ToDict()
      return dict((k, self.ToPrimitive(v))
                  for k, v in new_val.items())
    # Plain dictionaries are converted to dictionaries with each value
    # being recursively converted with ToPrimitive().
    elif isinstance(value, dict):
      return dict((k, self.ToPrimitive(v))
                  for k, v in value.items())
    # DataBlob is converted to its value passed through ToPrimitive().
    elif isinstance(value, rdfvalue.DataBlob):
      return self.ToPrimitive(value.GetValue())
    # EmbeddedRDFValue is converted to its payload passed through
    # ToPrimitive().
    elif isinstance(value, rdfvalue.EmbeddedRDFValue):
      return self.ToPrimitive(value.payload)
    # RDFProtoStruct is converted to a dictionary with struct's fields
    # being recursively converted with ToPrimitive().
    elif isinstance(value, rdfvalue.RDFProtoStruct):
      result = self.ToPrimitive(value.AsDict())
      # If type information is needed, converted value is placed in the
      # resulting dictionary under the 'value' key.
      if self.with_type_info:
        result = dict(type=value.__class__.__name__,
                      mro=self.GetTypeList(value),
                      value=result,
                      age=value.age.AsSecondsFromEpoch())

        if self.with_descriptors:
          descriptors = {}
          for descriptor, value in value.ListFields():
            descriptors[descriptor.name] = {
                "friendly_name": descriptor.friendly_name,
                "description": descriptor.description
                }
          result["descriptors"] = descriptors

      return result
    # Enums are converted to strings representing the name of the value.
    elif isinstance(value, structs.Enum):
      return value.name
    # Make sure string values are properly encoded, otherwise we may have
    # problems with JSON-encoding them.
    elif isinstance(value, basestring):
      return utils.SmartUnicode(value)
    # Other RDFValues are converted to their datastore-friendly representation.
    elif hasattr(value, "SerializeToDataStore"):
      result = value.SerializeToDataStore()
      if isinstance(result, basestring):
        result = utils.SmartUnicode(result)

      if self.with_type_info:
        result = dict(type=value.__class__.__name__,
                      mro=self.GetTypeList(value),
                      value=result,
                      age=value.age.AsSecondsFromEpoch())

      return result
    # Everything else is returned as-is.
    else:
      return value

  def RenderObject(self, aff4_object, request):
    """Render given aff4 object into JSON-serializable data structure."""
    _ = request

    self.with_type_info = request.get("with_type_info", False)
    self.with_descriptors = request.get("with_descriptors", False)

    attributes = {}
    for attribute, values in aff4_object.synced_attributes.items():
      attributes[attribute.predicate] = []
      for value in values:
        # This value is really a LazyDecoder() instance. We need to get at the
        # real data here.
        value = value.ToRDFValue()

        if aff4_object.age_policy != aff4.NEWEST_TIME:
          attributes[attribute.predicate].append(self.ToPrimitive(value))
        else:
          attributes[attribute.predicate] = self.ToPrimitive(value)

    result = dict(aff4_class=aff4_object.__class__.__name__,
                  urn=utils.SmartUnicode(aff4_object.urn),
                  attributes=attributes,
                  age_policy=aff4_object.age_policy)

    if self.with_type_info and self.with_descriptors:
      descriptors = {}
      for attribute, _ in aff4_object.synced_attributes.items():
        descriptors[attribute.predicate] = {
            "description": attribute.description
            }

      result["descriptors"] = descriptors

    return result


class RDFValueCollectionApiRenderer(AFF4ObjectApiRenderer):
  """Renderer for RDFValueCollections."""

  aff4_type = "RDFValueCollection"

  def RenderObject(self, aff4_object, request):
    offset = int(request.get("offset", 0))
    count = int(request.get("count", 10000))

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

    rendered_object = super(RDFValueCollectionApiRenderer, self).RenderObject(
        aff4_object, request)
    rendered_object["offset"] = offset
    rendered_object["items"] = [self.ToPrimitive(item) for item in items]

    if request.get("with_total_count", False):
      if hasattr(aff4_object, "CalculateLength"):
        total_count = aff4_object.CalculateLength()
      else:
        total_count = len(aff4_object)
      rendered_object["total_count"] = total_count

    return rendered_object


class VFSGRRClientApiRenderer(AFF4ObjectApiRenderer):
  """Renderer for VFSGRRClient objects."""

  aff4_type = "VFSGRRClient"

  def RenderObject(self, aff4_object, request):

    rendered_object = super(VFSGRRClientApiRenderer, self).RenderObject(
        aff4_object, request)
    rendered_object["summary"] = self.ToPrimitive(aff4_object.GetSummary())
    return rendered_object
