#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests client actions related to administrating the client."""



import os
import StringIO

import mox
import psutil

from grr.client import conf as flags
import logging

from grr.client import actions
from grr.client import comms
from grr.client import conf
from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib

FLAGS = flags.FLAGS


class ConfigActionTest(test_lib.EmptyActionTest):
  """Tests the client actions UpdateConfig and GetConfig."""

  def setUp(self):
    vfs.VFSInit()

    super(ConfigActionTest, self).setUp()
    FLAGS.config = FLAGS.test_tmpdir + "/config.ini"

  def testUpdateConfig(self):
    """Test that we can update the config."""
    # Make sure the config file is not already there
    try:
      os.unlink(FLAGS.config)
    except OSError:
      pass

    # Make sure the file is gone
    self.assertRaises(IOError, open, FLAGS.config)
    location = "http://www.example.com"
    request = rdfvalue.GRRConfig(location=location,
                                 foreman_check_frequency=3600)
    result = self.RunAction("UpdateConfig", request)

    self.assertEqual(result, [])
    self.assertEqual(conf.FLAGS.foreman_check_frequency, 3600)

    # Test the config file got written.
    data = open(conf.FLAGS.config).read()
    self.assert_("location = {0}".format(location) in data)

    # Now test that our location was actually updated.
    def FakeUrlOpen(req):
      self.fake_url = req.get_full_url()
      return StringIO.StringIO()
    comms.urllib2.urlopen = FakeUrlOpen
    client_context = comms.GRRHTTPClient()
    client_context.MakeRequest("", comms.Status())
    self.assertTrue(self.fake_url.startswith(location))

  def testUpdateConfigBlacklist(self):
    """Tests that disallowed fields are not getting updated."""
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(logging, "warning")

    logging.warning(mox.StrContains("restricted field(s)"), mox.And(
        mox.StrContains("camode"),
        mox.StrContains("debug"),
        mox.Not(mox.StrContains("location"))))

    self.mox.ReplayAll()

    location = "http://www.example.com"
    request = rdfvalue.GRRConfig(location=location,
                                 camode="test",
                                 debug=True)
    result = self.RunAction("UpdateConfig", request)

    self.mox.UnsetStubs()
    self.mox.VerifyAll()

    self.assertEqual(result, [])

  def testGetConfig(self):
    """Check GetConfig client action works."""
    # Use UpdateConfig to generate a config.
    location = "http://example.com"
    request = rdfvalue.GRRConfig(location=location,
                                 foreman_check_frequency=3600)
    self.RunAction("UpdateConfig", request)
    # Check that our GetConfig actually gets the real data.
    result = self.RunAction("GetConfig")[0]
    self.assertEqual(result.foreman_check_frequency, 3600)
    self.assertEqual(result.location, location)

  def VerifyResponse(self, response):

    self.assertEqual(response.bytes_received, 1566)
    self.assertEqual(response.bytes_sent, 2000)

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

      stats.STATS.Set("grr_client_received_bytes", 1566)
      stats.STATS.Set("grr_client_sent_bytes", 2000)

      action_cls = actions.ActionPlugin.classes.get(
          "GetClientStatsAuto", actions.ActionPlugin)
      action = action_cls(None, grr_worker=self)
      action.grr_worker = MockContext()
      action.Send = self.VerifyResponse
      action.Run(None)
    finally:
      psutil.BOOT_TIME = old_boot_time
