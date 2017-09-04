#!/usr/bin/env python
"""The base class for config validators.

This has to be in a separate file to avoid import loops.
"""
from grr.lib import registry


class PrivateConfigValidator(object):
  """Use this class to sanity check private config options at repack time."""
  __metaclass__ = registry.MetaclassRegistry
  __abstract = True  # pylint: disable=g-bad-name

  def ValidateEndConfig(self, conf, context, errors_fatal=True):
    raise NotImplementedError()
