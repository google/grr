#!/usr/bin/env python
"""This module serializes AFF4 objects in various ways."""


import yaml
from grr.lib import aff4


def YamlDumper(aff4object):
  """Dumps the given aff4object into a yaml representation."""
  aff4object.Flush()

  result = {}
  for attribute, values in aff4object.synced_attributes.items():
    result[attribute.predicate] = []
    for value in values:
      result[attribute.predicate].append(
          [value.__class__.__name__,
           value.SerializeToString(),
           str(value.age)])

  return yaml.dump(dict(
      aff4_class=aff4object.__class__.__name__,
      _urn=aff4object.urn.SerializeToString(),
      attributes=result,
      age_policy=aff4object.age_policy,
      ))


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
      tmp.append(rdfvalue_cls(value, age=aff4.RDFDatetime(age)))

  return result_cls(urn=representation["_urn"],
                    clone=aff4_attributes, mode="rw",
                    age=representation["age_policy"])
