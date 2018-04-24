#!/usr/bin/env python
"""This module serializes AFF4 objects in various ways."""

import yaml
from grr.lib import rdfvalue
from grr.server.grr_response_server import aff4


def YamlDumper(aff4object):
  """Dumps the given aff4object into a yaml representation."""
  aff4object.Flush()

  result = {}
  for attribute, values in aff4object.synced_attributes.items():
    result[attribute.predicate] = []
    for value in values:
      # This value is really a LazyDecoder() instance. We need to get at the
      # real data here.
      value = value.ToRDFValue()

      result[attribute.predicate].append(
          [value.__class__.__name__,
           value.SerializeToString(),
           str(value.age)])

  return yaml.dump(
      dict(
          aff4_class=aff4object.__class__.__name__,
          _urn=aff4object.urn.SerializeToString(),
          attributes=result,
          age_policy=aff4object.age_policy,))


def YamlLoader(string):
  """Load an AFF4 object from a serialized YAML representation."""
  representation = yaml.load(string)
  result_cls = aff4.FACTORY.AFF4Object(representation["aff4_class"])
  aff4_attributes = {}
  for predicate, values in representation["attributes"].items():
    attribute = aff4.Attribute.PREDICATES[predicate]
    tmp = aff4_attributes[attribute] = []

    for rdfvalue_cls_name, value, age in values:
      rdfvalue_cls = aff4.FACTORY.RDFValue(rdfvalue_cls_name)
      value = rdfvalue_cls(value, age=rdfvalue.RDFDatetime(age))
      tmp.append(value)

  # Ensure the object is dirty so when we save it, it can be written to the data
  # store.
  result = result_cls(
      urn=representation["_urn"],
      clone=aff4_attributes,
      mode="rw",
      age=representation["age_policy"])

  result.new_attributes, result.synced_attributes = result.synced_attributes, {}

  result._dirty = True  # pylint: disable=protected-access

  return result
