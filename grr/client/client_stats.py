#!/usr/bin/env python
"""CPU/IO stats collector."""



import os
import threading
import time

import psutil

from grr.lib import rdfvalue
from grr.lib import stats


class ClientStatsCollector(threading.Thread):
  """This thread keeps track of client stats."""

  exit = False

  def __init__(self, worker, sleep_time=10):
    super(ClientStatsCollector, self).__init__()
    self.sleep_time = sleep_time
    self.daemon = True
    self.proc = psutil.Process(os.getpid())
    self.cpu_samples = []
    self.io_samples = []
    self.worker = worker
    stats.STATS.RegisterGaugeMetric("grr_client_cpu_usage", str)
    stats.STATS.SetGaugeCallback("grr_client_cpu_usage", self.PrintCpuSamples)

    stats.STATS.RegisterGaugeMetric("grr_client_io_usage", str)
    stats.STATS.SetGaugeCallback("grr_client_io_usage", self.PrintIOSample)

  def run(self):
    while not self.exit:
      time.sleep(self.sleep_time)

      self.Collect()
      # Let the worker check if it should send back the stats.
      self.worker.CheckStats()

  def Collect(self):
    """Collects the stats."""

    user, system = self.proc.cpu_times()
    percent = self.proc.cpu_percent()
    self.cpu_samples.append((rdfvalue.RDFDatetime().Now(), user, system, percent
                            ))
    # Keep stats for one hour.
    self.cpu_samples = self.cpu_samples[-3600 / self.sleep_time:]

    # Not supported on MacOS.
    try:
      _, _, read_bytes, write_bytes = self.proc.io_counters()
      self.io_samples.append((rdfvalue.RDFDatetime().Now(), read_bytes,
                              write_bytes))
      self.io_samples = self.io_samples[-3600 / self.sleep_time:]
    except (AttributeError, NotImplementedError, psutil.Error):
      pass

  def PrintCpuSamples(self):
    """Returns a string with last 20 cpu load samples."""
    samples = [str(sample[3]) for sample in self.cpu_samples[-20:]]
    return ", ".join(samples)

  def PrintIOSample(self):
    try:
      return str(self.proc.io_counters())
    except (NotImplementedError, AttributeError):
      return "Not available on this platform."
