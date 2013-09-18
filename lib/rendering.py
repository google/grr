#!/usr/bin/env python
"""A module that provides access to the GUI rendering system."""

# pylint: disable=unused-import
from grr.gui import django_lib
# pylint: enable=unused-import


def FindRendererForObject(rdf_obj):
  """A proxy method for semantic.FindRendererForObject."""
  # pylint: disable=g-import-not-at-top, unused-variable, redefined-outer-name
  from grr.gui.plugins import semantic
  # pylint: enable=g-import-not-at-top, unused-variable, redefined-outer-name

  return semantic.FindRendererForObject(rdf_obj)
