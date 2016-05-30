#!/usr/bin/env python
"""Tests for API docs view."""



from grr.gui import runtests_test

from grr.lib import flags
from grr.lib import test_lib


class TestAPIDocs(test_lib.GRRSeleniumTest):
  """Tests the API docs UI."""

  def testStatsMetricRouteIsShown(self):
    self.Open("/#main=ApiDocumentation")

    # Check that header is shown.
    self.WaitUntil(self.IsTextPresent,
                   "GET /api/stats/store/<component>/metrics/<metric_name>")

    # Check that parameters are shown along with possible Enum values.
    self.WaitUntil(self.IsTextPresent, "Parameters")

    self.WaitUntil(self.IsTextPresent, "distribution_handling_mode")
    self.WaitUntil(self.IsTextPresent, "DH_COUNT")
    self.WaitUntil(self.IsTextPresent, "DH_SUM")

    self.WaitUntil(self.IsTextPresent, "aggregation_mode")
    self.WaitUntil(self.IsTextPresent, "AGG_SUM")
    self.WaitUntil(self.IsTextPresent, "AGG_MEAN")
    self.WaitUntil(self.IsTextPresent, "AGG_NONE")

    # Check that examples are shown.
    self.WaitUntil(self.IsTextPresent, "Examples")
    self.WaitUntil(self.IsTextPresent,
                   "/api/stats/store/WORKER/metrics/sample_counter?"
                   "start=42000000&end=3600000000")
    self.WaitUntil(self.IsTextPresent, 'metric_name": "sample_counter"')


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
