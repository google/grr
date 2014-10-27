#!/usr/bin/env python
"""Hint processing."""
import collections

from django.template import Context
from django.template import Template
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


class Hinter(object):

  def __init__(self, template=None):
    self.template = None
    if template:
      self.template = Template(template)

  def Render(self, rdf_data):
    if self.template:
      c = Context(rdf_data.AsDict())
      result = self.template.render(c)
    else:
      result = utils.SmartStr(rdf_data)
    return result

