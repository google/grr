#!/usr/bin/env python
"""The base class for config validators.

This has to be in a separate file to avoid import loops.
"""

from future.utils import with_metaclass

from grr.core.grr_response_core.lib import registry


class PrivateConfigValidator(
    with_metaclass(registry.MetaclassRegistry, object)):
  """Use this class to sanity check private config options at repack time."""
  __abstract = True  # pylint: disable=g-bad-name

  def ValidateEndConfig(self, conf, context, errors_fatal=True):
    raise NotImplementedError()
