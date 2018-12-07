#!/usr/bin/env python
"""This file contains utility functions used in ApiCallHandler classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import re
import sys


from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import api_utils_pb2


class ApiDataObjectKeyValuePair(rdf_structs.RDFProtoStruct):
  """Defines a proto for returning key value pairs of data objects."""

  protobuf = api_utils_pb2.ApiDataObjectKeyValuePair

  def InitFromKeyValue(self, key, value):
    self.key = key

    # Convert primitive types to rdf values so they can be serialized.
    if isinstance(value, float) and not value.is_integer():
      # TODO(user): Do not convert float values here and mark them invalid
      # later. ATM, we do not have means to properly represent floats. Change
      # this part once we have a RDFFloat implementation.
      pass
    elif rdfvalue.RDFInteger.IsNumeric(value):
      value = rdfvalue.RDFInteger(value)
    elif isinstance(value, unicode):
      value = rdfvalue.RDFString(value)
    elif isinstance(value, bytes):
      value = rdfvalue.RDFBytes(value)
    elif isinstance(value, bool):
      value = rdfvalue.RDFBool(value)

    if isinstance(value, rdfvalue.RDFValue):
      self.type = value.__class__.__name__
      self.value = value
    else:
      self.invalid = True

    return self

  def GetArgsClass(self):
    try:
      return rdfvalue.RDFValue.GetPlugin(self.type)
    except KeyError:
      raise ValueError("No class found for type %s." % self.type)


class ApiDataObject(rdf_structs.RDFProtoStruct):
  """Defines a proto for returning Data Objects over the API."""

  protobuf = api_utils_pb2.ApiDataObject
  rdf_deps = [
      ApiDataObjectKeyValuePair,
  ]

  def InitFromDataObject(self, data_object):
    for key, value in sorted(iteritems(data_object)):
      item = ApiDataObjectKeyValuePair().InitFromKeyValue(key, value)
      self.items.append(item)

    return self


def FilterList(l, offset, count=0, filter_value=None):
  """Filters a list, getting count elements, starting at offset."""

  if offset < 0:
    raise ValueError("Offset needs to be greater than or equal to zero")

  if count < 0:
    raise ValueError("Count needs to be greater than or equal to zero")

  count = count or sys.maxsize
  if not filter_value:
    return l[offset:offset + count]

  index = 0
  items = []
  for item in l:
    serialized_item = item.SerializeToString()
    if re.search(re.escape(filter_value), serialized_item, re.I):
      if index >= offset:
        items.append(item)
      index += 1

      if len(items) >= count:
        break

  return items


def FilterCollection(aff4_collection, offset, count=0, filter_value=None):
  """Filters an aff4 collection, getting count elements, starting at offset."""

  if offset < 0:
    raise ValueError("Offset needs to be greater than or equal to zero")

  if count < 0:
    raise ValueError("Count needs to be greater than or equal to zero")

  count = count or sys.maxsize
  if filter_value:
    index = 0
    items = []
    for item in aff4_collection.GenerateItems():
      serialized_item = item.SerializeToString()
      if re.search(re.escape(filter_value), serialized_item, re.I):
        if index >= offset:
          items.append(item)
        index += 1

        if len(items) >= count:
          break
  else:
    items = list(itertools.islice(aff4_collection.GenerateItems(offset), count))

  return items
