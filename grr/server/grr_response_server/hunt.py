#!/usr/bin/env python
"""REL_DB implementation of hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.util import random


# TODO(user): look into using 48-bit or 64-bit ids to avoid clashes.
def RandomHuntId():
  """Returns a random hunt id encoded as a hex string."""
  return "%08X" % random.PositiveUInt32()
