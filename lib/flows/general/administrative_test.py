#!/usr/bin/env python
"""Tests for administrative flows."""



import subprocess
import sys
import time


import psutil

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info


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


class ClientActionRunner(flow.GRRFlow):
  """Just call the specified client action directly.
  """

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="action",
          description="Action to run."
          )
      )

  args = {}

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallClient(self.state.action, next_state="End", **self.args)


class TestAdministrativeFlows(test_lib.FlowTestsBaseclass):

  def testClientKilled(self):
    """Test that client killed messages are handled correctly."""
    try:
      old_send_email = email_alerts.SendEmail

      self.email_message = {}

      def SendEmail(address, sender, title, message, **_):
        self.email_message.update(dict(address=address, sender=sender,
                                       title=title, message=message))

      email_alerts.SendEmail = SendEmail
      config_lib.CONFIG.Set("Monitoring.alert_email", "admin@nowhere.com")

      client = test_lib.CrashClientMock(self.client_id, self.token)
      for _ in test_lib.TestFlowHelper(
          "ListDirectory", client, client_id=self.client_id,
          pathspec=rdfvalue.PathSpec(path="/"), token=self.token,
          check_flow_errors=False):
        pass

      # We expect the email to be sent.
      self.assertEqual(self.email_message.get("address", ""),
                       config_lib.CONFIG["Monitoring.alert_email"])
      self.assertTrue(str(self.client_id) in self.email_message["title"])

      # Make sure the flow state is included in the email message.
      for s in ["flow_name", "ListDirectory", "current_state", "Start"]:
        self.assertTrue(s in self.email_message["message"])

      flow_obj = aff4.FACTORY.Open(client.flow_id, age=aff4.ALL_TIMES,
                                   token=self.token)
      self.assertEqual(flow_obj.state.context.state, rdfvalue.Flow.State.ERROR)

      # Make sure crashes RDFValueCollections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = sorted(
          list(aff4.FACTORY.Open(self.client_id.Add("crashes"),
                                 aff4_type="RDFValueCollection",
                                 token=self.token)),
          key=lambda x: x.timestamp)

      self.assertTrue(len(client_crashes) >= 1)
      crash = list(client_crashes)[0]
      self.assertEqual(crash.client_id, self.client_id)
      self.assertEqual(crash.session_id, flow_obj.session_id)
      self.assertEqual(crash.client_info.client_name, "GRR Monitor")
      self.assertEqual(crash.crash_type, "aff4:/flows/W:CrashHandler")
      self.assertEqual(crash.crash_message, "Client killed during transaction")

      # Check per-flow crash collection. Check that crash written there is
      # equal to per-client crash.
      flow_crashes = sorted(
          list(flow_obj.GetValuesForAttribute(flow_obj.Schema.CLIENT_CRASH)),
          key=lambda x: x.timestamp)
      self.assertEqual(len(flow_crashes), len(client_crashes))
      for a, b in zip(flow_crashes, client_crashes):
        self.assertEqual(a, b)

      # Check global crash collection. Check that crash written there is
      # equal to per-client crash.
      global_crashes = sorted(
          aff4.FACTORY.Open(aff4.ROOT_URN.Add("crashes"),
                            aff4_type="RDFValueCollection",
                            token=self.token),
          key=lambda x: x.timestamp)
      self.assertEqual(len(global_crashes), len(client_crashes))
      for a, b in zip(global_crashes, client_crashes):
        self.assertEqual(a, b)

    finally:
      email_alerts.SendEmail = old_send_email

  def testNannyMessage(self):
    nanny_message = "Oh no!"
    try:
      old_send_email = email_alerts.SendEmail

      self.email_message = {}

      def SendEmail(address, sender, title, message, **_):
        self.email_message.update(dict(address=address, sender=sender,
                                       title=title, message=message))

      email_alerts.SendEmail = SendEmail
      config_lib.CONFIG.Set("Monitoring.alert_email", "admin@nowhere.com")

      msg = rdfvalue.GrrMessage(
          session_id=rdfvalue.SessionID("aff4:/flows/W:NannyMessage"),
          args=rdfvalue.DataBlob(string=nanny_message).SerializeToString(),
          source=self.client_id,
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

      # This is normally done by the FrontEnd when a CLIENT_KILLED message is
      # received.
      flow.PublishEvent("NannyMessage", msg, token=self.token)

      # Now emulate a worker to process the event.
      worker = test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

      # We expect the email to be sent.
      self.assertEqual(self.email_message.get("address", ""),
                       config_lib.CONFIG["Monitoring.alert_email"])
      self.assertTrue(str(self.client_id) in self.email_message["title"])

      # Make sure the message is included in the email message.
      self.assertTrue(nanny_message in self.email_message["message"])

      # Make sure crashes RDFValueCollections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = aff4.FACTORY.Open(self.client_id.Add("crashes"),
                                         aff4_type="RDFValueCollection",
                                         token=self.token)
      self.assertEqual(len(client_crashes), 1)
      crash = list(client_crashes)[0]
      self.assertEqual(crash.client_id, self.client_id)
      self.assertEqual(crash.client_info.client_name, "GRR Monitor")
      self.assertEqual(crash.crash_type, "aff4:/flows/W:NannyMessage")
      self.assertEqual(crash.crash_message, nanny_message)

      # Check global crash collection. Check that crash written there is
      # equal to per-client crash.
      global_crashes = aff4.FACTORY.Open(aff4.ROOT_URN.Add("crashes"),
                                         aff4_type="RDFValueCollection",
                                         token=self.token)
      self.assertEqual(len(global_crashes), 1)
      self.assertEqual(list(global_crashes)[0], crash)

    finally:
      email_alerts.SendEmail = old_send_email

  def testStartupHandler(self):
    # Clean the client records.
    aff4.FACTORY.Delete(self.client_id, token=self.token)

    client_mock = test_lib.ActionMock("SendStartupInfo")
    for _ in test_lib.TestFlowHelper(
        "ClientActionRunner", client_mock, client_id=self.client_id,
        action="SendStartupInfo", token=self.token):
      pass

    # Check the client's boot time and info.
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    client_info = fd.Get(fd.Schema.CLIENT_INFO)
    boot_time = fd.Get(fd.Schema.LAST_BOOT_TIME)

    self.assertEqual(client_info.client_name,
                     config_lib.CONFIG["Client.name"])
    self.assertEqual(client_info.client_description,
                     config_lib.CONFIG["Client.description"])

    # Check that the boot time is accurate.
    self.assertAlmostEqual(psutil.BOOT_TIME, boot_time.AsSecondsFromEpoch())

    # Run it again - this should not update any record.
    for _ in test_lib.TestFlowHelper(
        "ClientActionRunner", client_mock, client_id=self.client_id,
        action="SendStartupInfo", token=self.token):
      pass

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertEqual(boot_time.age, fd.Get(fd.Schema.LAST_BOOT_TIME).age)
    self.assertEqual(client_info.age, fd.Get(fd.Schema.CLIENT_INFO).age)

    # Simulate a reboot in 10 minutes.
    psutil.BOOT_TIME += 600

    # Run it again - this should now update the boot time.
    for _ in test_lib.TestFlowHelper(
        "ClientActionRunner", client_mock, client_id=self.client_id,
        action="SendStartupInfo", token=self.token):
      pass

    # Ensure only this attribute is updated.
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertNotEqual(int(boot_time.age),
                        int(fd.Get(fd.Schema.LAST_BOOT_TIME).age))

    self.assertEqual(int(client_info.age),
                     int(fd.Get(fd.Schema.CLIENT_INFO).age))

    # Now set a new client build time.
    config_lib.CONFIG.Set("Client.build_time", time.ctime())

    # Run it again - this should now update the client info.
    for _ in test_lib.TestFlowHelper(
        "ClientActionRunner", client_mock, client_id=self.client_id,
        action="SendStartupInfo", token=self.token):
      pass

    # Ensure the client info attribute is updated.
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertNotEqual(int(client_info.age),
                        int(fd.Get(fd.Schema.CLIENT_INFO).age))

  def testExecutePythonHack(self):
    client_mock = test_lib.ActionMock("ExecutePython")
    # This is the code we test. If this runs on the client mock we can check for
    # this attribute.
    sys.test_code_ran_here = False

    code = """
import sys
sys.test_code_ran_here = True
"""
    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path="aff4:/config/python_hacks/test", token=self.token)

    for _ in test_lib.TestFlowHelper(
        "ExecutePythonHack", client_mock, client_id=self.client_id,
        hack_name="test", token=self.token):
      pass

    self.assertTrue(sys.test_code_ran_here)

  def testExecutePythonHackWithArgs(self):
    client_mock = test_lib.ActionMock("ExecutePython")
    sys.test_code_ran_here = 1234
    code = """
import sys
sys.test_code_ran_here = py_args['value']
"""
    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path="aff4:/config/python_hacks/test", token=self.token)

    for _ in test_lib.TestFlowHelper(
        "ExecutePythonHack", client_mock, client_id=self.client_id,
        hack_name="test", py_args=dict(value=5678), token=self.token):
      pass

    self.assertEqual(sys.test_code_ran_here, 5678)

  def testExecuteBinariesWithArgs(self):
    client_mock = test_lib.ActionMock("ExecuteBinaryCommand")

    code = "I am a binary file"
    upload_path = config_lib.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, token=self.token)

    class Popen(object):
      """A mock object for subprocess.Popen."""

      def __init__(self, run, stdout, stderr):
        Popen.running_args = run
        Popen.stdout = stdout
        Popen.stderr = stderr
        Popen.returncode = 0

        # Store the content of the executable file.
        Popen.binary = open(run[0]).read()

      def communicate(self):  # pylint: disable=g-bad-name
        return "stdout here", "stderr here"

    with test_lib.Stubber(subprocess, "Popen", Popen):
      for _ in test_lib.TestFlowHelper(
          "LaunchBinary", client_mock, client_id=self.client_id,
          binary=upload_path, args=["--value", "356"], token=self.token):
        pass

      # Check that the executable file contains the code string.
      self.assertEqual(Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(Popen.running_args[1], "--value")
      self.assertEqual(Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertTrue(Popen.running_args[0].startswith(
          config_lib.CONFIG["Client.tempdir"]))

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

    urn = self.client_id.Add("stats")
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
