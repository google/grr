#!/usr/bin/env python
"""A module with compatibility wrappers for YAML processing."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections

from future.builtins import str
from future.utils import iteritems
from typing import Any
from typing import Text
import yaml

from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition


def Parse(text):
  """Parses a YAML source into a Python object.

  Args:
    text: A YAML source to parse.

  Returns:
    A Python data structure corresponding to the YAML source.
  """
  precondition.AssertType(text, Text)

  if compatibility.PY2:
    text = text.encode("utf-8")

  return yaml.safe_load(text)


def Dump(obj):
  """Stringifies a Python object into its YAML representation.

  Args:
    obj: A Python object to convert to YAML.

  Returns:
    A YAML representation of the given object.
  """
  text = yaml.safe_dump(obj, default_flow_style=False, allow_unicode=True)

  if compatibility.PY2:
    text = text.decode("utf-8")

  return text


# This makes sure that all string literals in the YAML file are parsed as an
# `unicode` object rather than `bytes` instances.
def _StrConstructor(loader, node):
  precondition.AssertType(node.value, Text)
  return loader.construct_scalar(node)


yaml.add_constructor("tag:yaml.org,2002:str", _StrConstructor)
yaml.add_constructor(
    "tag:yaml.org,2002:str", _StrConstructor, Loader=yaml.SafeLoader)
yaml.add_constructor("tag:yaml.org,2002:python/unicode", _StrConstructor)
yaml.add_constructor(
    "tag:yaml.org,2002:python/unicode", _StrConstructor, Loader=yaml.SafeLoader)


# Ensure Yaml does not emit tags for unicode objects.
# http://pyyaml.org/ticket/11
def _UnicodeRepresenter(dumper, value):
  precondition.AssertType(value, Text)
  return dumper.represent_scalar(u"tag:yaml.org,2002:str", value)


yaml.add_representer(Text, _UnicodeRepresenter)
yaml.add_representer(Text, _UnicodeRepresenter, Dumper=yaml.SafeDumper)
yaml.add_representer(str, _UnicodeRepresenter)
yaml.add_representer(str, _UnicodeRepresenter, Dumper=yaml.SafeDumper)


# Add support for dumping `collections.OrderedDict`.
def _OrderedDictRepresenter(dumper, value):
  precondition.AssertType(value, collections.OrderedDict)
  return dumper.represent_dict(list(iteritems(value)))


yaml.add_representer(collections.OrderedDict, _OrderedDictRepresenter)
yaml.add_representer(
    collections.OrderedDict, _OrderedDictRepresenter, Dumper=yaml.SafeDumper)
