#!/usr/bin/env python
"""Queue definitions.

This module defines the queues where a worker may look for work.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from builtins import map  # pylint: disable=redefined-builtin

from grr_response_core.lib import rdfvalue

# Queues that a standard worker should work from, highest priority first.
#
# "W" and "CA" are deprecated, but included until we are sure that they are
# empty.
WORKER_LIST = list(map(rdfvalue.RDFURN, ["CA", "W", "E", "F", "H", "S"]))

# The normal queue for enrollment messages.
ENROLLMENT = rdfvalue.RDFURN("E")

# The normal queue for flows. Must be kept synchronized with the default value
# of FlowRunnerArgs.queue.
FLOWS = rdfvalue.RDFURN("F")

# The normal queue for hunts. Must be kept synchronized with the default value
# of HuntRunnerArgs.queue.
HUNTS = rdfvalue.RDFURN("H")

# The normal queue for statistics processing.
STATS = rdfvalue.RDFURN("S")
