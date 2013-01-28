#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""Tests for administrative flows."""


import sys

from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import test_lib

FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG


class TestClientConfigHandling(test_lib.FlowTestsBaseclass):
  """Test the GetConfig flow."""

  def testUpdateConfig(self):
    """Ensure we can retrieve the config."""
    pass
    # # Only mock the pieces we care about.
    # client_mock = test_lib.ActionMock("GetConfig", "UpdateConfig")
    # # Fix up the client actions to not use /etc.
    # conf.FLAGS.config = FLAGS.test_tmpdir + "/config.ini"
    # loc = "http://www.example.com"
    # grr_config = rdfvalue.GRRConfig(location=loc,
    #                                 foreman_check_frequency=3600,
    #                                 poll_min=1)
    # # Write the config.
    # for _ in test_lib.TestFlowHelper("UpdateConfig", client_mock,
    #                                  client_id=self.client_id,
    #                                  token=self.token,
    #                                  grr_config=grr_config):
    #   pass

    # # Now retrieve it again to see if it got written.
    # for _ in test_lib.TestFlowHelper("Interrogate", client_mock,
    #                                  token=self.token,
    #                                  client_id=self.client_id):
    #   pass

    # urn = aff4.ROOT_URN.Add(self.client_id)
    # fd = aff4.FACTORY.Open(urn, token=self.token)
    # config_dat = fd.Get(fd.Schema.GRR_CONFIG)
    # self.assertEqual(config_dat.data.location, loc)
    # self.assertEqual(config_dat.data.poll_min, 1)


class TestAdministrativeFlows(test_lib.FlowTestsBaseclass):

  def testClientKilled(self):
    """Test that client killed messages are handled correctly."""

    client_id = self.client_id
    token = self.token

    class ClientMock(object):

      def HandleMessage(self, message):
        status = rdfvalue.GrrStatus(
            status=rdfvalue.GrrStatus.Enum("CLIENT_KILLED"),
            error_message="Client killed during transaction")

        msg = rdfvalue.GRRMessage(
            request_id=message.request_id, response_id=1,
            session_id=message.session_id,
            type=rdfvalue.GRRMessage.Enum("STATUS"),
            args=status.SerializeToString(), source=client_id,
            auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"))

        self.flow_id = message.session_id

        # This is normally done by the FrontEnd when a CLIENT_KILLED message is
        # received.
        flow.PublishEvent("ClientCrash", msg, token=token)

        return [status]

    try:
      old_send_email = email_alerts.SendEmail

      self.email_message = {}

      def SendEmail(address, sender, title, message, **_):
        self.email_message.update(dict(address=address, sender=sender,
                                       title=title, message=message))

      email_alerts.SendEmail = SendEmail
      FLAGS.monitoring_email = "admin@nowhere.com"

      client = ClientMock()
      for _ in test_lib.TestFlowHelper(
          "ListDirectory", client, client_id=self.client_id,
          pathspec=rdfvalue.RDFPathSpec(path="/"), token=self.token,
          check_flow_errors=False):
        pass

      # We expect the email to be sent.
      self.assertEqual(self.email_message["address"], FLAGS.monitoring_email)
      self.assertTrue(self.client_id in self.email_message["title"])

      # Make sure the flow protobuf dump is included in the email message.
      for s in ["name: \"ListDirectory\"", "state:", "pickle:"]:
        self.assertTrue(s in self.email_message["message"])

      flow_pb = flow.FACTORY.FetchFlow(client.flow_id, token=self.token)
      self.assertEqual(flow_pb.state, rdfvalue.Flow.Enum("ERROR"))
      flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

    finally:
      email_alerts.SendEmail = old_send_email

  def testExecutePythonHack(self):
    client_mock = test_lib.ActionMock("ExecutePython")

    FLAGS.camode = "test"

    # This is the code we test. If this runs on the client mock we can check for
    # this attribute.
    sys.test_code_ran_here = False

    code = """
import sys
sys.test_code_ran_here = True
"""

    maintenance_utils.UploadSignedConfigBlob(
        code, file_name="", config=CONFIG, platform="Windows",
        aff4_path="aff4:/config/python_hacks/test", token=self.token)

    for _ in test_lib.TestFlowHelper(
        "ExecutePythonHack", client_mock, client_id=self.client_id,
        hack_name="test", token=self.token):
      pass

    self.assertTrue(sys.test_code_ran_here)

  def testGetClientStats(self):

    class ClientMock(object):
      def GetClientStats(self, _):
        response = rdfvalue.ClientStats()
        for i in range(12):
          sample = rdfvalue.CpuSample(
              timestamp=int(i * 10 * 1e6),
              user_cpu_time=10 + i,
              system_cpu_time=20 + i,
              cpu_percent=10 + i)
          response.cpu_samples.Append(sample)

          sample = rdfvalue.IOSample(
              timestamp=int(i * 10 * 1e6),
              read_bytes=10 + i,
              write_bytes=10 + i)
          response.io_samples.Append(sample)

        return [response]

    for _ in test_lib.TestFlowHelper("GetClientStats", ClientMock(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    urn = aff4.ROOT_URN.Add(self.client_id).Add("stats")
    stats_fd = aff4.FACTORY.Create(urn, "ClientStats", token=self.token,
                                   mode="rw")
    sample = stats_fd.Get(stats_fd.Schema.STATS)

    # Samples are taken at the following timestamps and should be split into 2
    # bins as follows (sample_interval is 60000000):

    # 00000000, 10000000, 20000000, 30000000, 40000000, 50000000  -> Bin 1
    # 60000000, 70000000, 80000000, 90000000, 100000000, 110000000  -> Bin 2

    self.assertEqual(len(sample.cpu_samples), 2)
    self.assertEqual(len(sample.io_samples), 2)

    self.assertAlmostEqual(sample.io_samples[0].read_bytes, 15.0)
    self.assertAlmostEqual(sample.io_samples[1].read_bytes, 21.0)

    self.assertAlmostEqual(sample.cpu_samples[0].cpu_percent,
                           sum(range(10, 16))/6.0)
    self.assertAlmostEqual(sample.cpu_samples[1].cpu_percent,
                           sum(range(16, 22))/6.0)

    self.assertAlmostEqual(sample.cpu_samples[0].user_cpu_time, 15.0)
    self.assertAlmostEqual(sample.cpu_samples[1].system_cpu_time, 31.0)
