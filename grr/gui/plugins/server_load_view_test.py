#!/usr/bin/env python
"""Test the server load view interface."""



from grr.gui import runtests_test

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib

from grr.lib.aff4_objects import stats_store


class TestServerLoadView(test_lib.GRRSeleniumTest):
  """Tests for ServerLoadView."""

  @staticmethod
  def SetupSampleMetrics(token=None):
    store = aff4.FACTORY.Create(None,
                                stats_store.StatsStore,
                                mode="w",
                                token=token)

    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_num")
    stats.STATS.RegisterCounterMetric("grr_frontendserver_handle_throttled_num")

    now = rdfvalue.RDFDatetime().Now()
    handle_data = [(3, now - rdfvalue.Duration("50m")),
                   (0, now - rdfvalue.Duration("45m")),
                   (1, now - rdfvalue.Duration("40m")),
                   (0, now - rdfvalue.Duration("35m")),
                   (0, now - rdfvalue.Duration("30m")),
                   (1, now - rdfvalue.Duration("25m")),
                   (0, now - rdfvalue.Duration("20m")),
                   (0, now - rdfvalue.Duration("15m")),
                   (0, now - rdfvalue.Duration("10m")),
                   (5, now - rdfvalue.Duration("5m")),
                   (0, now)]  # pyformat: disable

    handle_data = [(value, timestamp.AsMicroSecondsFromEpoch())
                   for value, timestamp in handle_data]
    for value, timestamp in handle_data:
      with test_lib.FakeTime(timestamp / 1e6):
        stats.STATS.IncrementCounter("grr_frontendserver_handle_num", value)
        store.WriteStats(process_id="frontend")

    throttle_data = [(0, now - rdfvalue.Duration("50m")),
                     (0, now - rdfvalue.Duration("45m")),
                     (0, now - rdfvalue.Duration("40m")),
                     (0, now - rdfvalue.Duration("35m")),
                     (0, now - rdfvalue.Duration("30m")),
                     (0, now - rdfvalue.Duration("25m")),
                     (0, now - rdfvalue.Duration("20m")),
                     (0, now - rdfvalue.Duration("15m")),
                     (0, now - rdfvalue.Duration("10m")),
                     (0, now - rdfvalue.Duration("5m")),
                     (0, now)]  # pyformat: disable

    throttle_data = [(value, timestamp.AsMicroSecondsFromEpoch())
                     for value, timestamp in throttle_data]

    for value, timestamp in throttle_data:
      with test_lib.FakeTime(timestamp / 1e6):
        stats.STATS.IncrementCounter("grr_frontendserver_handle_throttled_num",
                                     value)
        store.WriteStats(process_id="frontend")

  def testServerLoadPageContainsIndicatorsAndGraphs(self):
    self.Open("/#main=ServerLoadView")
    self.WaitUntil(self.IsTextPresent, "Frontends load")
    self.WaitUntil(self.IsTextPresent, "Frontend handled vs throttled rate")

    self.Click("css=li[heading=Worker]")
    self.WaitUntil(self.IsTextPresent, "Worker successful vs failed flows rate")

  # TODO(user): uncomment as soon as number of instances is back.
  # def testServerLoadPageShowsCorrectNumberOfInstances(self):
  #   with self.ACLChecksDisabled():
  #     self.SetupSampleMetrics(token=self.token)

  #   self.Open("/#main=ServerLoadView")
  #   self.WaitUntil(self.IsTextPresent, "Frontend (1 instances)")

  def testTimeRangeButtonsAreClickable(self):
    self.Open("/#main=ServerLoadView")
    self.WaitUntil(self.IsTextPresent, "Frontends load")

    self.Click("css=label[btn-radio=72]")
    self.WaitUntil(self.IsTextPresent, "Frontends load")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
