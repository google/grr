#!/usr/bin/env python
"""Hint processing."""
import collections
import string

from grr.lib import objectfilter
from grr.lib import rdfvalue
from grr.lib import utils


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
  for attr in ("fix", "format", "problem", "summary"):
    if not child.get(attr):
      child[attr] = parent.get(attr, "")
  return child


class RdfFormatter(string.Formatter):
  """A string formatter implementation that handles rdf data."""

  expander = objectfilter.AttributeValueExpander().Expand

  def KVExpander(self, obj, attr):
    """KeyValue entries return the values of the DataBlob structures."""

    attr_val = getattr(obj, attr).GetValue()
    if attr_val and isinstance(attr_val, basestring):
      return [attr_val]
    return attr_val

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
        if isinstance(rdf, rdfvalue.KeyValue):
          rslts = [utils.SmartStr(r) for r in self.KVExpander(rdf, field_name)]
        else:
          rslts = [utils.SmartStr(r) for r in self.expander(rdf, field_name)]
        # format the object and append to the result
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
      result = utils.SmartStr(rdf_data)
    return result
