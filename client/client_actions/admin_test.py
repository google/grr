#!/usr/bin/env python
"""Tests client actions related to administrating the client."""



import os
import StringIO

import psutil

from grr.client import actions
from grr.client import comms
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib


class ConfigActionTest(test_lib.EmptyActionTest):
  """Tests the client actions UpdateConfiguration and GetConfiguration."""

  def testUpdateConfiguration(self):
    """Test that we can update the config."""
    # A unique name on the filesystem for the writeback.
    self.config_file = os.path.join(self.temp_dir, "ConfigActionTest.yaml")

    # In a real client, the writeback location should be set to something real,
    # but for this test we make it the same as the config file..
    config_lib.CONFIG.SetWriteBack(self.config_file)

    # Make sure the file is gone
    self.assertRaises(IOError, open, self.config_file)

    location = ["http://www.example1.com/", "http://www.example2.com/"]
    request = rdfvalue.Dict()
    request["Client.control_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    result = self.RunAction("UpdateConfiguration", request)

    self.assertEqual(result, [])
    self.assertEqual(config_lib.CONFIG["Client.foreman_check_frequency"], 3600)

    # Test the config file got written.
    data = open(self.config_file).read()
    self.assertTrue("control_urls: {0}".format(",".join(location)) in data)

    self.urls = []
    # Now test that our location was actually updated.
    def FakeUrlOpen(req, timeout=10):
      _ = timeout
      self.urls.append(req.get_full_url())
      return StringIO.StringIO()

    comms.urllib2.urlopen = FakeUrlOpen
    client_context = comms.GRRHTTPClient()
    client_context.MakeRequest("", comms.Status())

    self.assertTrue(location[0] in self.urls[0])
    self.assertTrue(location[1] in self.urls[1])

  def testUpdateConfigBlacklist(self):
    """Tests that disallowed fields are not getting updated."""

    config_lib.CONFIG.Set("Client.control_urls", ["http://something.com/"])
    config_lib.CONFIG.Set("Client.server_serial_number", 1)

    location = ["http://www.example.com"]
    request = rdfvalue.Dict()
    request["Client.control_urls"] = location
    request["Client.server_serial_number"] = 10

    self.RunAction("UpdateConfiguration", request)

    # Location can be set.
    self.assertEqual(config_lib.CONFIG["Client.control_urls"], location)

    # But the server serial number can not be updated.
    self.assertEqual(config_lib.CONFIG["Client.server_serial_number"], 1)

  def testGetConfig(self):
    """Check GetConfig client action works."""
    # Use UpdateConfig to generate a config.
    location = ["http://example.com"]
    request = rdfvalue.Dict()
    request["Client.control_urls"] = location
    request["Client.foreman_check_frequency"] = 3600

    self.RunAction("UpdateConfiguration", request)
    # Check that our GetConfig actually gets the real data.
    self.RunAction("GetConfiguration")

    self.assertEqual(config_lib.CONFIG["Client.foreman_check_frequency"], 3600)
    self.assertEqual(config_lib.CONFIG["Client.control_urls"], location)

  def VerifyResponse(self, response, bytes_received, bytes_sent):

    self.assertEqual(response.bytes_received, bytes_received)
    self.assertEqual(response.bytes_sent, bytes_sent)

    self.assertEqual(len(response.cpu_samples), 2)
    self.assertAlmostEqual(response.cpu_samples[1].user_cpu_time, 0.1)
    self.assertAlmostEqual(response.cpu_samples[1].system_cpu_time, 0.2)
    self.assertAlmostEqual(response.cpu_samples[1].cpu_percent, 15.0)

    self.assertEqual(len(response.io_samples), 2)
    self.assertEqual(response.io_samples[0].read_bytes, 100)
    self.assertEqual(response.io_samples[1].read_bytes, 200)
    self.assertEqual(response.io_samples[1].write_bytes, 200)

    self.assertEqual(response.boot_time, long(100 * 1e6))

  def testGetClientStatsAuto(self):
    """Checks that stats collection works."""

    class MockCollector(object):
      cpu_samples = [(100, 0.1, 0.1, 10.0), (110, 0.1, 0.2, 15.0)]
      io_samples = [(100, 100, 100), (110, 200, 200)]

    class MockContext(object):

      def __init__(self):
        self.stats_collector = MockCollector()

    old_boot_time = psutil.BOOT_TIME
    psutil.BOOT_TIME = 100
    try:

      stats.STATS.IncrementCounter("grr_client_received_bytes", 1566)
      received_bytes = stats.STATS.GetMetricValue("grr_client_received_bytes")

      stats.STATS.IncrementCounter("grr_client_sent_bytes", 2000)
      sent_bytes = stats.STATS.GetMetricValue("grr_client_sent_bytes")

      action_cls = actions.ActionPlugin.classes.get(
          "GetClientStatsAuto", actions.ActionPlugin)
      action = action_cls(grr_worker=MockContext())
      action.Send = lambda r: self.VerifyResponse(r, received_bytes, sent_bytes)
      action.Run(None)
    finally:
      psutil.BOOT_TIME = old_boot_time
