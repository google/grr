#!/usr/bin/env python
"""Tests for API docs view."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags

from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class TestAPIDocs(gui_test_lib.GRRSeleniumTest):
  """Tests the API docs UI."""

  def testStatsMetricRouteIsShown(self):
    self.Open("/#main=ApiDocumentation")

    self.WaitUntil(
        self.AllTextsPresent,
        [
            # Check that header is shown.
            "GET /api/stats/store/<component>/metrics/<metric_name>",

            # Check that parameters are shown along with possible Enum values.
            "Parameters",
            "distribution_handling_mode",
            "DH_COUNT",
            "DH_SUM",
            "aggregation_mode",
            "AGG_SUM",
            "AGG_MEAN",
            "AGG_NONE",

            # Check that examples are shown.
            "Examples",
            "/api/stats/store/worker/metrics/sample_counter?"
            "end=3600000000&start=42000000",
            '"metric_name": "sample_counter"'
        ])


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
