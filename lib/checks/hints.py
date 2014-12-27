#!/usr/bin/env python
"""Hint processing."""
import collections
import string

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


class FormatWrapper(object):
  """Wrapper that ensures RDF values can be queried by string format."""

  def __init__(self, item):
    self.proxy = item

  def __getattr__(self, item):
    return self.get(item)

  def __getitem__(self, item):
    return getattr(self.proxy, item)


class Hinter(object):
  """Applies template filters to host data."""

  def __init__(self, template=None):
    self.template = template

  def Render(self, rdf_data):
    if self.template:
      formatable = FormatWrapper(rdf_data)
      result = string.Formatter().vformat(self.template, [], formatable)
    else:
      result = utils.SmartStr(rdf_data)
    return result
