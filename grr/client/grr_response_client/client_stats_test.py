#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import itertools
from unittest import mock

from absl import app
from absl.testing import absltest
import psutil

from grr_response_client import client_stats
from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr.test_lib import test_lib


class ClientStatsCollectorTest(absltest.TestCase):

  @mock.patch.object(admin, "GetClientStatsAuto")
  def testRealSamples(self, mock_get_client_stats_auto):
    del mock_get_client_stats_auto  # Unused.

    worker = mock.MagicMock()
    collector = client_stats.ClientStatsCollector(worker)

    future = rdfvalue.RDFDatetime.FromHumanReadable("2033-09-01")
    with test_lib.FakeTimeline(thread=collector, now=future) as timeline:
      timeline.Run(duration=rdfvalue.Duration.From(25, rdfvalue.SECONDS))

    cpu_samples = collector.CpuSamplesBetween(
        start_time=future,
        end_time=future + rdfvalue.Duration.From(25, rdfvalue.SECONDS))
    io_samples = collector.IOSamplesBetween(
        start_time=future,
        end_time=future + rdfvalue.Duration.From(25, rdfvalue.SECONDS))

    self.assertLen(cpu_samples, 3)
    self.assertLen(io_samples, 3)

  @mock.patch.object(admin, "GetClientStatsAuto")
  def testFakeSamples(self, mock_get_client_stats_auto):
    del mock_get_client_stats_auto  # Unused.

    with MockCpuTimes(), MockIoCounters(), MockCpuPercent():
      collector = client_stats.ClientStatsCollector(mock.MagicMock())

      millennium = rdfvalue.RDFDatetime.FromHumanReadable("2000-01-01")
      with test_lib.FakeTimeline(thread=collector, now=millennium) as timeline:
        timeline.Run(duration=rdfvalue.Duration.From(25, rdfvalue.SECONDS))

      cpu_samples = collector.CpuSamplesBetween(
          start_time=millennium,
          end_time=millennium + rdfvalue.Duration.From(25, rdfvalue.SECONDS))
      io_samples = collector.IOSamplesBetween(
          start_time=millennium,
          end_time=millennium + rdfvalue.Duration.From(25, rdfvalue.SECONDS))

    self.assertLen(cpu_samples, 3)
    self.assertLen(io_samples, 3)
    for i in range(3):
      expected_timestamp = millennium + rdfvalue.Duration.From(
          10, rdfvalue.SECONDS) * i

      cpu_sample = cpu_samples[i]
      self.assertEqual(cpu_sample.timestamp, expected_timestamp)
      self.assertEqual(cpu_sample.user_cpu_time, FAKE_CPU_TIMES[i].user)
      self.assertEqual(cpu_sample.system_cpu_time, FAKE_CPU_TIMES[i].system)
      self.assertEqual(cpu_sample.cpu_percent, FAKE_CPU_PERCENT[i])

      io_sample = io_samples[i]
      self.assertEqual(io_sample.timestamp, expected_timestamp)
      self.assertEqual(io_sample.read_bytes, FAKE_IO_COUNTERS[i].read_bytes)
      self.assertEqual(io_sample.write_bytes, FAKE_IO_COUNTERS[i].write_bytes)

  @mock.patch.object(admin, "GetClientStatsAuto")
  def testSampleFiltering(self, mock_get_client_stats_auto):
    del mock_get_client_stats_auto  # Unused.

    collector = client_stats.ClientStatsCollector(mock.MagicMock())

    past = rdfvalue.RDFDatetime.FromHumanReadable("1980-01-01")
    with test_lib.FakeTimeline(thread=collector, now=past) as timeline:
      timeline.Run(duration=rdfvalue.Duration.From(30, rdfvalue.MINUTES))

    cpu_samples = collector.CpuSamplesBetween(
        start_time=past + rdfvalue.Duration.From(10, rdfvalue.MINUTES) +
        rdfvalue.Duration.From(1, rdfvalue.SECONDS),
        end_time=past + rdfvalue.Duration.From(20, rdfvalue.MINUTES))

    self.assertLen(cpu_samples, 60)
    for sample in cpu_samples:
      self.assertLess(past + rdfvalue.Duration.From(10, rdfvalue.MINUTES),
                      sample.timestamp)
      self.assertGreaterEqual(
          past + rdfvalue.Duration.From(20, rdfvalue.MINUTES), sample.timestamp)

    io_samples = collector.IOSamplesBetween(
        start_time=past + rdfvalue.Duration.From(1, rdfvalue.MINUTES) +
        rdfvalue.Duration.From(1, rdfvalue.SECONDS),
        end_time=past + rdfvalue.Duration.From(2, rdfvalue.MINUTES))

    self.assertLen(io_samples, 6)
    for sample in io_samples:
      self.assertLess(past + rdfvalue.Duration.From(1, rdfvalue.MINUTES),
                      sample.timestamp)
      self.assertGreaterEqual(
          past + rdfvalue.Duration.From(2, rdfvalue.MINUTES), sample.timestamp)

  @mock.patch.object(admin, "GetClientStatsAuto")
  def testOldSampleCleanup(self, mock_get_client_stats_auto):
    del mock_get_client_stats_auto  # Unused.

    collector = client_stats.ClientStatsCollector(mock.MagicMock())

    epoch = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
    with test_lib.FakeTimeline(thread=collector, now=epoch) as timeline:
      timeline.Run(duration=rdfvalue.Duration.From(3, rdfvalue.HOURS))

    cpu_samples = collector.CpuSamplesBetween(
        start_time=epoch,
        end_time=epoch + rdfvalue.Duration.From(1, rdfvalue.HOURS))
    self.assertEmpty(cpu_samples)

    io_samples = collector.IOSamplesBetween(
        start_time=epoch + rdfvalue.Duration.From(30, rdfvalue.MINUTES),
        end_time=epoch + rdfvalue.Duration.From(1, rdfvalue.HOURS) +
        rdfvalue.Duration.From(50, rdfvalue.MINUTES))
    self.assertEmpty(io_samples)

  @mock.patch.object(config, "CONFIG")
  @mock.patch.object(admin.GetClientStatsAuto, "Send")
  def testSampleSending(self, mock_send, mock_config):
    del mock_config  # Unused.

    with MockCpuTimes(), MockIoCounters(), MockCpuPercent():
      worker = mock.MagicMock()
      collector = client_stats.ClientStatsCollector(worker)
      worker.stats_collector = collector
      worker.IsActive = lambda: False

      today = rdfvalue.RDFDatetime.FromHumanReadable("2018-03-14")
      with test_lib.FakeTimeline(thread=collector, now=today) as timeline:
        timeline.Run(duration=rdfvalue.Duration.From(10, rdfvalue.SECONDS))

        self.assertTrue(mock_send.called)
        response = mock_send.call_args[0][0]

        self.assertTrue(response.HasField("cpu_samples"))
        self.assertTrue(response.HasField("io_samples"))

        self.assertLen(response.cpu_samples, 1)
        self.assertLen(response.io_samples, 1)

        self.assertEqual(response.cpu_samples[0].timestamp, today)
        self.assertEqual(response.cpu_samples[0].user_cpu_time,
                         FAKE_CPU_TIMES[0].user)
        self.assertEqual(response.cpu_samples[0].system_cpu_time,
                         FAKE_CPU_TIMES[0].system)
        self.assertEqual(response.cpu_samples[0].cpu_percent,
                         FAKE_CPU_PERCENT[0])

        self.assertEqual(response.cpu_samples[0].timestamp, today)
        self.assertEqual(response.io_samples[0].read_bytes,
                         FAKE_IO_COUNTERS[0].read_bytes)
        self.assertEqual(response.io_samples[0].write_bytes,
                         FAKE_IO_COUNTERS[0].write_bytes)

  @mock.patch.object(config, "CONFIG")
  @mock.patch.object(admin.GetClientStatsAuto, "Send")
  def testMinSendInterval(self, mock_send, mock_config):
    del mock_config  # Unused.

    worker = mock.MagicMock()
    collector = client_stats.ClientStatsCollector(worker)
    worker.stats_collector = collector
    worker.IsActive = lambda: False

    with test_lib.FakeTimeline(thread=collector) as timeline:
      timeline.Run(duration=rdfvalue.Duration.From(15, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)

      collector.RequestSend()

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(10, rdfvalue.SECONDS))
      self.assertFalse(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(20, rdfvalue.SECONDS))
      self.assertFalse(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(40, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(30, rdfvalue.SECONDS))
      self.assertFalse(mock_send.called)

  @mock.patch.object(config, "CONFIG")
  @mock.patch.object(admin.GetClientStatsAuto, "Send")
  def testMaxSendInterval(self, mock_send, mock_config):
    del mock_config  # Unused.

    worker = mock.MagicMock()
    collector = client_stats.ClientStatsCollector(worker)
    worker.stats_collector = collector
    worker.IsActive = lambda: False

    with test_lib.FakeTimeline(thread=collector) as timeline:
      timeline.Run(duration=rdfvalue.Duration.From(15, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(20, rdfvalue.SECONDS))
      self.assertFalse(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(30, rdfvalue.MINUTES))
      self.assertFalse(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(30, rdfvalue.MINUTES))
      self.assertTrue(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(20, rdfvalue.MINUTES))
      self.assertFalse(mock_send.called)

      collector.RequestSend()

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(5, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)

  @mock.patch.object(config, "CONFIG")
  @mock.patch.object(admin.GetClientStatsAuto, "Send")
  def testSendWhenWorkerIsActive(self, mock_send, mock_config):
    del mock_config  # Unused.

    worker = mock.MagicMock()
    collector = client_stats.ClientStatsCollector(worker)
    worker.stats_collector = collector

    with test_lib.FakeTimeline(thread=collector) as timeline:
      worker.IsActive = lambda: True

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(5, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(2, rdfvalue.MINUTES))
      self.assertTrue(mock_send.called)

      worker.IsActive = lambda: False

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(30, rdfvalue.MINUTES))
      self.assertFalse(mock_send.called)

      worker.IsActive = lambda: True

      mock_send.reset_mock()
      timeline.Run(duration=rdfvalue.Duration.From(5, rdfvalue.SECONDS))
      self.assertTrue(mock_send.called)


def MockCpuTimes():
  cycled_fake_cpu_times = itertools.cycle(FAKE_CPU_TIMES)
  return mock.patch.object(
      psutil.Process, "cpu_times", side_effect=cycled_fake_cpu_times)


def MockIoCounters():
  cycled_fake_io_counters = itertools.cycle(FAKE_IO_COUNTERS)
  return mock.patch.object(
      psutil.Process, "io_counters", side_effect=cycled_fake_io_counters)


def MockCpuPercent():
  cycled_fake_cpu_percent = itertools.cycle(FAKE_CPU_PERCENT)
  return mock.patch.object(
      psutil.Process, "cpu_percent", side_effect=cycled_fake_cpu_percent)


PCPUTime = collections.namedtuple("pcputime", ("user", "system"))
PIO = collections.namedtuple(
    "pio", ("read_bytes", "write_bytes", "read_count", "write_count"))

FAKE_CPU_TIMES = [
    PCPUTime(user=0.1, system=0.5),
    PCPUTime(user=0.2, system=0.75),
    PCPUTime(user=0.3, system=1.5),
]

FAKE_IO_COUNTERS = [
    PIO(read_bytes=42, write_bytes=11, read_count=11, write_count=5),
    PIO(read_bytes=1024, write_bytes=512, read_count=133, write_count=74),
    PIO(read_bytes=4096, write_bytes=768, read_count=421, write_count=95),
]

FAKE_CPU_PERCENT = [1.0, 2.0, 4.0]


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
