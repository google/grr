#!/usr/bin/env python
"""Hint processing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import string


from future.utils import iteritems
from future.utils import string_types

from grr_response_core.lib import objectfilter
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A hint was defined badly."""


def Overlay(child, parent):
  """Adds hint attributes to a child hint if they are not defined."""
  for arg in child, parent:
    if not isinstance(arg, collections.Mapping):
      raise DefinitionError("Trying to merge badly defined hints. Child: %s, "
                            "Parent: %s" % (type(child), type(parent)))
  for attr in ["fix", "format", "problem", "summary"]:
    if not child.get(attr):
      child[attr] = parent.get(attr, "").strip()
  return child


class RdfFormatter(string.Formatter):
  """A string formatter implementation that handles rdf data."""

  expander = objectfilter.AttributeValueExpander().Expand

  def FanOut(self, obj, parent=None):
    """Expand values from various attribute types.

    Strings are returned as is.
    Dictionaries are returned with a key string, and an expanded set of values.
    Other iterables are expanded until they flatten out.
    Other items are returned in string format.

    Args:
      obj: The object to expand out.
      parent: The parent object: Used to short-circuit infinite recursion.

    Returns:
      a list of expanded values as strings.
    """
    # Catch cases where RDFs are iterable but return themselves.
    if parent and obj == parent:
      results = [utils.SmartUnicode(obj).strip()]
    elif isinstance(obj, (string_types, rdf_structs.EnumNamedValue)):
      results = [utils.SmartUnicode(obj).strip()]
    elif isinstance(obj, rdf_protodict.DataBlob):
      results = self.FanOut(obj.GetValue())
    elif isinstance(obj, (collections.Mapping, rdf_protodict.Dict)):
      results = []
      # rdf_protodict.Dict only has items, not iteritems.
      for k, v in iteritems(obj):
        expanded_v = [utils.SmartUnicode(r) for r in self.FanOut(v)]
        results.append("%s:%s" % (utils.SmartUnicode(k), ",".join(expanded_v)))
    elif isinstance(obj, (collections.Iterable,
                          rdf_structs.RepeatedFieldHelper)):
      results = []
      for rslt in [self.FanOut(o, obj) for o in obj]:
        results.extend(rslt)
    else:
      results = [utils.SmartUnicode(obj).strip()]
    return results

  def Format(self, format_string, rdf):
    """Apply string formatting templates to rdf data.

    Uses some heuristics to coerce rdf values into a form compatible with string
    formatter rules. Repeated items are condensed into a single comma separated
    list. Unlike regular string.Formatter operations, we use objectfilter
    expansion to fully acquire the target attribute in one pass, rather than
    recursing down each element of the attribute tree.

    Args:
      format_string: A format string specification.
      rdf: The rdf value to be formatted.

    Returns:
      A string of formatted data.
    """
    result = []
    for literal_text, field_name, _, _ in self.parse(format_string):
      # output the literal text
      if literal_text:
        result.append(literal_text)
      # if there's a field, output it
      if field_name is not None:
        rslts = []
        objs = self.expander(rdf, field_name)
        for o in objs:
          rslts.extend(self.FanOut(o))
        # format the objects and append to the result
        result.append(",".join(rslts))
    return "".join(result)


class Hinter(object):
  """Applies template filters to host data."""

  formatter = RdfFormatter().Format

  def __init__(self, template=None):
    self.template = template

  def Render(self, rdf_data):
    if self.template:
      result = self.formatter(self.template, rdf_data)
    else:
      result = utils.SmartUnicode(rdf_data)
    return result.strip()
