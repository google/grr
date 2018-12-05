#!/usr/bin/env python
"""MySQL implementation of DB methods for handling signed binaries."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_server.rdfvalues import objects as rdf_objects


# TODO(user): Implement methods for this mixin.
class MySQLDBSignedBinariesMixin(object):
  """Mixin providing an F1 implementation of signed binaries DB logic."""

  def WriteSignedBinaryReferences(self, binary_id,
                                  references):
    """See db.Database."""
    raise NotImplementedError()

  def ReadSignedBinaryReferences(
      self, binary_id
  ):
    """See db.Database."""
    raise NotImplementedError()

  def ReadIDsForAllSignedBinaries(self):
    """See db.Database."""
    raise NotImplementedError()

  def DeleteSignedBinaryReferences(self, binary_id):
    """See db.Database."""
    raise NotImplementedError()
