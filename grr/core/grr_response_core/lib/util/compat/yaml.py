#!/usr/bin/env python
"""A module with compatibility wrappers for YAML processing."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import io

from future.builtins import str
from future.utils import iteritems
from typing import Any
from typing import IO
from typing import Iterable
from typing import Sequence
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


def ParseMany(text):
  """Parses many YAML documents into a list of Python objects.

  Args:
    text: A YAML source with multiple documents embedded.

  Returns:
    A list of Python data structures corresponding to the YAML documents.
  """
  precondition.AssertType(text, Text)

  if compatibility.PY2:
    text = text.encode("utf-8")

  return list(yaml.safe_load_all(text))


def ReadFromFile(filedesc):
  """Reads a Python object from given file descriptor.

  Args:
    filedesc: A descriptor of the file to read the YAML contents from.

  Returns:
    A Python data structure corresponding to the YAML in the given file.
  """
  content = filedesc.read()
  return Parse(content)


def ReadManyFromFile(filedesc):
  """Reads many YAML documents from given file into a list of Python objects.

  Args:
    filedesc: A descriptor of the file to read the YAML contents from.

  Returns:
    A list of Python data structures corresponding to the YAML documents.
  """
  content = filedesc.read()
  return ParseMany(content)


def ReadFromPath(filepath):
  """Reads a Python object stored in a specified YAML file.

  Args:
    filepath: A filepath to the YAML file.

  Returns:
    A Python data structure corresponding to the YAML in the given file.
  """
  with io.open(filepath, mode="r", encoding="utf-8") as filedesc:
    return ReadFromFile(filedesc)


def ReadManyFromPath(filepath):
  """Reads a Python object stored in a specified YAML file.

  Args:
    filepath: A filepath to the YAML file.

  Returns:
    A Python data structure corresponding to the YAML in the given file.
  """
  with io.open(filepath, mode="r", encoding="utf-8") as filedesc:
    return ReadManyFromFile(filedesc)


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


def DumpMany(objs):
  """Stringifies a sequence of Python objects to a multi-document YAML.

  Args:
    objs: An iterable of Python objects to convert to YAML.

  Returns:
    A multi-document YAML representation of the given objects.
  """
  precondition.AssertIterableType(objs, object)

  text = yaml.safe_dump_all(objs, default_flow_style=False, allow_unicode=True)

  if compatibility.PY2:
    text = text.decode("utf-8")

  return text


def WriteToFile(obj, filedesc):
  """Serializes and writes given Python object to a YAML file.

  Args:
    obj: A Python object to serialize.
    filedesc: A file descriptor into which the object is to be written.
  """
  filedesc.write(Dump(obj))


def WriteManyToFile(objs, filedesc):
  """Serializes and writes Python objects to a multi-document YAML file.

  Args:
    objs: An iterable of Python objects to serialize.
    filedesc: A file descriptor into which the objects are to be written.
  """
  filedesc.write(DumpMany(objs))


def WriteToPath(obj, filepath):
  """Serializes and writes given Python object to the specified YAML file.

  Args:
    obj: A Python object to serialize.
    filepath: A path to the file into which the object is to be written.
  """
  with io.open(filepath, mode="w", encoding="utf-8") as filedesc:
    WriteToFile(obj, filedesc)


def WriteManyToPath(objs, filepath):
  """Serializes and writes given Python objects to a multi-document YAML file.

  Args:
    objs: An iterable of Python objects to serialize.
    filepath: A path to the file into which the object is to be written.
  """
  with io.open(filepath, mode="w", encoding="utf-8") as filedesc:
    WriteManyToFile(objs, filedesc)


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
