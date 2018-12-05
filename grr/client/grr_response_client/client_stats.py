#!/usr/bin/env python
"""CPU/IO stats collector."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time

import psutil

from grr_response_client.client_actions import admin
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.stats import stats_collector_instance


class ClientStatsCollector(threading.Thread):
  """This thread keeps track of client stats."""

  SLEEP_DURATION = rdfvalue.Duration("10s")  # A delay between main loop ticks.
  KEEP_DURATION = rdfvalue.Duration("1h")  # How long we preserve samples.

  MIN_SEND_INTERVAL = rdfvalue.Duration("60s")
  MAX_SEND_INTERVAL = rdfvalue.Duration("50m")

  # TODO(hanuszczak): This is a hack used to make `grr/server/front_end_test.py`
  # work. While not terrible, including any kind of hacks to production code
  # just to make the tests work does not seem like a great idea. It should be
  # investigated whether we can get rid of it and make the tests work in some
  # other way.
  exit = False  # Setting this value to `True` terminates the thread.

  def __init__(self, worker):
    """Initializes the stat collector.

    Args:
      worker: A `GRRClientWorker` instance that spawned this stat collector.
    """
    super(ClientStatsCollector, self).__init__()
    self.daemon = True

    self._worker = worker

    self._process = psutil.Process()
    self._cpu_samples = []
    self._io_samples = []

    self._last_send_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
    self._should_send = False

    stats_collector = stats_collector_instance.Get()
    stats_collector.SetGaugeCallback("grr_client_cpu_usage",
                                     self._PrintCpuSamples)
    stats_collector.SetGaugeCallback("grr_client_io_usage", self._PrintIOSample)

  def RequestSend(self):
    """Requests to send the collected data.

    This method does not send the data immediately and does not block. Instead,
    it will upload samples in near future provided that sufficient amount of
    time has elapsed since the last upload.
    """
    self._should_send = True

  def CpuSamplesBetween(self, start_time, end_time):
    """Computes CPU samples collected between specified time range.

    Args:
      start_time: A lower bound for the timestamp of returned samples.
      end_time: An upper bound for the timestamp of returned samples.

    Returns:
      A list of `CpuSample` instances.
    """
    return _SamplesBetween(self._cpu_samples, start_time, end_time)

  def IOSamplesBetween(self, start_time, end_time):
    """Computes IO samples collected between specified time range.

    Args:
      start_time: A lower bound for the timestamp of returned samples.
      end_time: An upper bound for the timestamp of returned samples.

    Returns:
      A list of `IOSample` instances.
    """
    return _SamplesBetween(self._io_samples, start_time, end_time)

  def run(self):
    while not self.exit:
      self._Collect()
      self._Send()
      time.sleep(self.SLEEP_DURATION.seconds)

  def _Send(self):
    if not self._ShouldSend():
      return

    # TODO(hanuszczak): We shouldn't manually create action instances. Instead,
    # we should refactor action code to some other function and make the action
    # class use that function. Then here we should use that function as well.
    #
    # Also, it looks like there is a very weird dependency triangle: the worker
    # creates stat collector (which requires a worker), then the stats action
    # requires a worker and uses stat collector internally. But this action is
    # spawned by the stat collector. What...?
    action = admin.GetClientStatsAuto(grr_worker=self._worker)
    request = rdf_client_action.GetClientStatsRequest(
        start_time=self._last_send_time)
    action.Run(request)

    self._should_send = False
    self._last_send_time = rdfvalue.RDFDatetime.Now()

  def _ShouldSend(self):
    delta = rdfvalue.RDFDatetime.Now() - self._last_send_time
    if delta < self.MIN_SEND_INTERVAL:
      return False
    if delta > self.MAX_SEND_INTERVAL:
      return True
    return self._should_send or self._worker.IsActive()

  def _Collect(self):
    self._CollectCpuUsage()
    self._CollectIOUsage()

  def _CollectCpuUsage(self):
    cpu_times = self._process.cpu_times()
    cpu_percent = self._process.cpu_percent()

    sample = rdf_client_stats.CpuSample(
        timestamp=rdfvalue.RDFDatetime.Now(),
        user_cpu_time=cpu_times.user,
        system_cpu_time=cpu_times.system,
        cpu_percent=cpu_percent)

    self._cpu_samples.append(sample)
    self._cpu_samples = self.CpuSamplesBetween(
        start_time=rdfvalue.RDFDatetime.Now() - self.KEEP_DURATION,
        end_time=rdfvalue.RDFDatetime.Now())

  def _CollectIOUsage(self):
    # Not supported on MacOS.
    try:
      io_counters = self._process.io_counters()
    except (AttributeError, NotImplementedError, psutil.Error):
      return

    sample = rdf_client_stats.IOSample(
        timestamp=rdfvalue.RDFDatetime.Now(),
        read_bytes=io_counters.read_bytes,
        write_bytes=io_counters.write_bytes,
        read_count=io_counters.read_count,
        write_count=io_counters.write_count)

    self._io_samples.append(sample)
    self._io_samples = self.IOSamplesBetween(
        start_time=rdfvalue.RDFDatetime.Now() - self.KEEP_DURATION,
        end_time=rdfvalue.RDFDatetime.Now())

  def _PrintCpuSamples(self):
    """Returns a string with last 20 cpu load samples."""
    samples = [str(sample.percent) for sample in self._cpu_samples[-20:]]
    return ", ".join(samples)

  def _PrintIOSample(self):
    try:
      return str(self._process.io_counters())
    except (NotImplementedError, AttributeError):
      return "Not available on this platform."


def _SamplesBetween(samples, start_time, end_time):
  return [s for s in samples if start_time <= s.timestamp <= end_time]
