#!/usr/bin/env python
"""MySQL implementation of DB methods for handling client-report data."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Dict, Optional, Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import time_utils
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs


# TODO(user): Implement methods for this mixin.
class MySQLDBClientReportsMixin(object):
  """Mixin providing an F1 implementation of client-reports DB logic."""

  def WriteClientGraphSeries(self,
                             graph_series,
                             client_label,
                             timestamp = None):
    """See db.Database."""
    raise NotImplementedError()

  def ReadAllClientGraphSeries(
      self,
      client_label,
      report_type,
      time_range = None
  ):
    """See db.Database."""
    raise NotImplementedError()

  def ReadMostRecentClientGraphSeries(self, client_label,
                                      report_type
                                     ):
    """See db.Database."""
    raise NotImplementedError()


# pytype: enable=attribute-error
