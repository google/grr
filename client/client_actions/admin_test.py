#!/usr/bin/env python
"""Tests client actions related to administrating the client."""



import os
import StringIO

import psutil

from grr.client import comms
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict as rdf_protodict


class ConfigActionTest(test_lib.EmptyActionTest):
  """Tests the client actions UpdateConfiguration and GetConfiguration."""

  def setUp(self):
    super(ConfigActionTest, self).setUp()
    # These tests change the config so we preserve state.
    self.config_stubber = test_lib.PreserveConfig()
    self.config_stubber.Start()

  def tearDown(self):
    super(ConfigActionTest, self).tearDown()
    self.config_stubber.Stop()

  def testUpdateConfiguration(self):
    """Test that we can update the config."""
    # A unique name on the filesystem for the writeback.
    self.config_file = os.path.join(self.temp_dir, "ConfigActionTest.yaml")

    # In a real client, the writeback location should be set to something real,
    # but for this test we make it the same as the config file..
    config_lib.CONFIG.SetWriteBack(self.config_file)

    # Make sure the file is gone
    self.assertRaises(IOError, open, self.config_file)

    location = ["http://www.example1.com/",
                "http://www.example2.com/"]
    request = rdf_protodict.Dict()
    request["Client.server_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    result = self.RunAction("UpdateConfiguration", request)

    self.assertEqual(result, [])
    self.assertEqual(config_lib.CONFIG["Client.foreman_check_frequency"], 3600)

    # Test the config file got written.
    data = open(self.config_file).read()
    self.assertTrue("server_urls: {0}".format(",".join(location)) in data)

    self.urls = []
    # Now test that our location was actually updated.

    def FakeUrlOpen(req, timeout=10):
      _ = timeout
      self.urls.append(req.get_full_url())
      return StringIO.StringIO()

    with utils.Stubber(comms.urllib2, "urlopen", FakeUrlOpen):
      client_context = comms.GRRHTTPClient(worker=MockClientWorker)
      client_context.MakeRequest("")

    # Since the request is successful we only connect to one location.
    self.assertTrue(location[0] in self.urls[0])

  def testUpdateConfigBlacklist(self):
    """Tests that disallowed fields are not getting updated."""
    with test_lib.ConfigOverrider({
        "Client.server_urls": ["http://something.com/"],
        "Client.server_serial_number": 1}):

      location = ["http://www.example.com"]
      request = rdf_protodict.Dict()
      request["Client.server_urls"] = location
      request["Client.server_serial_number"] = 10

      self.RunAction("UpdateConfiguration", request)

      # Location can be set.
      self.assertEqual(config_lib.CONFIG["Client.server_urls"], location)

      # But the server serial number can not be updated.
      self.assertEqual(config_lib.CONFIG["Client.server_serial_number"], 1)

  def testGetConfig(self):
    """Check GetConfig client action works."""
    # Use UpdateConfig to generate a config.
    location = ["http://example.com"]
    request = rdf_protodict.Dict()
    request["Client.server_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    self.RunAction("UpdateConfiguration", request)
    # Check that our GetConfig actually gets the real data.
    self.RunAction("GetConfiguration")

    self.assertEqual(config_lib.CONFIG["Client.foreman_check_frequency"], 3600)
    self.assertEqual(config_lib.CONFIG["Client.server_urls"], location)


class MockStatsCollector(object):
  """Mock stats collector for GetClientStatsActionTest."""

  # First value in every tuple is a timestamp (as if it was returned by
  # time.time()).
  cpu_samples = [(rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
                  0.1, 0.1, 10.0),
                 (rdfvalue.RDFDatetime().FromSecondsFromEpoch(110),
                  0.1, 0.2, 15.0),
                 (rdfvalue.RDFDatetime().FromSecondsFromEpoch(120),
                  0.1, 0.3, 20.0)]
  io_samples = [(rdfvalue.RDFDatetime().FromSecondsFromEpoch(100), 100, 100),
                (rdfvalue.RDFDatetime().FromSecondsFromEpoch(110), 200, 200),
                (rdfvalue.RDFDatetime().FromSecondsFromEpoch(120), 300, 300)]


class MockClientWorker(object):
  """Mock client worker for GetClientStatsActionTest."""

  def __init__(self):
    self.stats_collector = MockStatsCollector()


class GetClientStatsActionTest(test_lib.EmptyActionTest):
  """Test GetClientStats client action."""

  def setUp(self):
    super(GetClientStatsActionTest, self).setUp()
    self.old_boot_time = psutil.boot_time
    psutil.boot_time = lambda: 100

  def tearDown(self):
    super(GetClientStatsActionTest, self).tearDown()
    psutil.boot_time = self.old_boot_time

  def testReturnsAllDataByDefault(self):
    """Checks that stats collection works."""

    stats.STATS.RegisterCounterMetric("grr_client_received_bytes")
    stats.STATS.IncrementCounter("grr_client_received_bytes", 1566)

    stats.STATS.RegisterCounterMetric("grr_client_sent_bytes")
    stats.STATS.IncrementCounter("grr_client_sent_bytes", 2000)

    results = self.RunAction("GetClientStats", grr_worker=MockClientWorker(),
                             arg=rdf_client.GetClientStatsRequest())

    response = results[0]
    self.assertEqual(response.bytes_received, 1566)
    self.assertEqual(response.bytes_sent, 2000)

    self.assertEqual(len(response.cpu_samples), 3)
    for i in range(3):
      self.assertEqual(response.cpu_samples[i].timestamp,
                       rdfvalue.RDFDatetime().FromSecondsFromEpoch(
                           100 + i * 10))
      self.assertAlmostEqual(response.cpu_samples[i].user_cpu_time, 0.1)
      self.assertAlmostEqual(response.cpu_samples[i].system_cpu_time,
                             0.1 * (i + 1))
      self.assertAlmostEqual(response.cpu_samples[i].cpu_percent, 10.0 + 5 * i)

    self.assertEqual(len(response.io_samples), 3)
    for i in range(3):
      self.assertEqual(response.io_samples[i].timestamp,
                       rdfvalue.RDFDatetime().FromSecondsFromEpoch(
                           100 + i * 10))
      self.assertEqual(response.io_samples[i].read_bytes, 100 * (i + 1))
      self.assertEqual(response.io_samples[i].write_bytes, 100 * (i + 1))

    self.assertEqual(response.boot_time, long(100 * 1e6))

  def testFiltersDataPointsByStartTime(self):
    start_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(117)
    results = self.RunAction(
        "GetClientStats", grr_worker=MockClientWorker(),
        arg=rdf_client.GetClientStatsRequest(start_time=start_time))

    response = results[0]
    self.assertEqual(len(response.cpu_samples), 1)
    self.assertEqual(response.cpu_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(120))

    self.assertEqual(len(response.io_samples), 1)
    self.assertEqual(response.io_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(120))

  def testFiltersDataPointsByEndTime(self):
    end_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(102)
    results = self.RunAction(
        "GetClientStats", grr_worker=MockClientWorker(),
        arg=rdf_client.GetClientStatsRequest(end_time=end_time))

    response = results[0]
    self.assertEqual(len(response.cpu_samples), 1)
    self.assertEqual(response.cpu_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(100))

    self.assertEqual(len(response.io_samples), 1)
    self.assertEqual(response.io_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(100))

  def testFiltersDataPointsByStartAndEndTimes(self):
    start_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(109)
    end_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(113)
    results = self.RunAction(
        "GetClientStats", grr_worker=MockClientWorker(),
        arg=rdf_client.GetClientStatsRequest(start_time=start_time,
                                             end_time=end_time))

    response = results[0]
    self.assertEqual(len(response.cpu_samples), 1)
    self.assertEqual(response.cpu_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(110))

    self.assertEqual(len(response.io_samples), 1)
    self.assertEqual(response.io_samples[0].timestamp,
                     rdfvalue.RDFDatetime().FromSecondsFromEpoch(110))


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
