#!/usr/bin/env python
"""Tests for administrative flows."""



import os
import subprocess
import sys
import time


import psutil

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import maintenance_utils
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
# pylint: disable=unused-import
from grr.lib.flows.general import administrative
# For AuditEventListener, needed to handle published audit events.
from grr.lib.flows.general import audit as _
from grr.lib.flows.general import discovery
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict


class AdministrativeFlowTests(test_lib.FlowTestsBaseclass):
  pass


class TestAdministrativeFlows(AdministrativeFlowTests):
  """Tests the administrative flows."""

  def setUp(self):
    super(TestAdministrativeFlows, self).setUp()

    test_tmp = os.environ.get("TEST_TMPDIR")
    if test_tmp:
      self.tempdir_overrider = test_lib.ConfigOverrider({})
      self.tempdir_overrider.Start()

  def tearDown(self):
    super(TestAdministrativeFlows, self).tearDown()
    try:
      self.tempdir_overrider.Stop()
    except AttributeError:
      pass

  def testUpdateConfig(self):
    """Ensure we can retrieve and update the config."""

    # Only mock the pieces we care about.
    client_mock = action_mocks.ActionMock("GetConfiguration",
                                          "UpdateConfiguration")

    loc = "http://www.example.com"
    new_config = rdf_protodict.Dict(
        {"Client.server_urls": [loc],
         "Client.foreman_check_frequency": 3600,
         "Client.poll_min": 1})

    # Setting config options is disallowed in tests so we need to temporarily
    # revert this.
    with utils.Stubber(config_lib.CONFIG, "Set",
                       config_lib.CONFIG.Set.old_target):
      # Write the config.
      for _ in test_lib.TestFlowHelper("UpdateConfiguration", client_mock,
                                       client_id=self.client_id,
                                       token=self.token,
                                       config=new_config):
        pass

    # Now retrieve it again to see if it got written.
    for _ in test_lib.TestFlowHelper("Interrogate", client_mock,
                                     token=self.token,
                                     client_id=self.client_id):
      pass

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    config_dat = fd.Get(fd.Schema.GRR_CONFIGURATION)
    self.assertEqual(config_dat["Client.server_urls"], [loc])
    self.assertEqual(config_dat["Client.poll_min"], 1)

  def CheckCrash(self, crash, expected_session_id):
    """Checks that ClientCrash object's fields are correctly filled in."""
    self.assertTrue(crash is not None)
    self.assertEqual(crash.client_id, self.client_id)
    self.assertEqual(crash.session_id, expected_session_id)
    self.assertEqual(crash.client_info.client_name, "GRR Monitor")
    self.assertEqual(
        crash.crash_type,
        "aff4:/flows/" + queues.FLOWS.Basename() + ":CrashHandler")
    self.assertEqual(crash.crash_message,
                     "Client killed during transaction")

  def testAlertEmailIsSentWhenClientKilled(self):
    """Test that client killed messages are handled correctly."""
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = test_lib.CrashClientMock(self.client_id, self.token)
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneClientRequest", client, client_id=self.client_id,
          token=self.token, check_flow_errors=False):
        pass

    self.assertEqual(len(self.email_messages), 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(email_message.get("address", ""),
                     config_lib.CONFIG["Monitoring.alert_email"])
    self.assertTrue(str(self.client_id) in email_message["title"])

    # Make sure the flow state is included in the email message.
    for s in ["Flow name", "FlowWithOneClientRequest", "current_state"]:
      self.assertTrue(s in email_message["message"])

    flow_obj = aff4.FACTORY.Open(client.flow_id, age=aff4.ALL_TIMES,
                                 token=self.token)
    self.assertEqual(flow_obj.state.context.state, rdf_flows.Flow.State.ERROR)

    # Make sure client object is updated with the last crash.
    client_obj = aff4.FACTORY.Open(self.client_id, token=self.token)
    crash = client_obj.Get(client_obj.Schema.LAST_CRASH)
    self.CheckCrash(crash, flow_obj.session_id)

    # Make sure crashes RDFValueCollections are created and written
    # into proper locations. First check the per-client crashes collection.
    client_crashes = sorted(
        list(aff4.FACTORY.Open(self.client_id.Add("crashes"),
                               aff4_type="PackedVersionedCollection",
                               token=self.token)),
        key=lambda x: x.timestamp)

    self.assertTrue(len(client_crashes) >= 1)
    crash = list(client_crashes)[0]
    self.CheckCrash(crash, flow_obj.session_id)

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
                          aff4_type="PackedVersionedCollection",
                          token=self.token),
        key=lambda x: x.timestamp)
    self.assertEqual(len(global_crashes), len(client_crashes))
    for a, b in zip(global_crashes, client_crashes):
      self.assertEqual(a, b)

  def testAlertEmailIsSentWhenClientKilledDuringHunt(self):
    """Test that client killed messages are handled correctly for hunts."""
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(
            flow_name="FlowWithOneClientRequest"),
        client_rate=0, crash_alert_email="crashes@example.com",
        token=self.token) as hunt:
      hunt.Run()
      hunt.StartClients(hunt.session_id, self.client_id)

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = test_lib.CrashClientMock(self.client_id, self.token)
      test_lib.TestHuntHelper(
          client, [self.client_id],
          token=self.token, check_flow_errors=False)

    self.assertEqual(len(self.email_messages), 2)
    self.assertListEqual([self.email_messages[0]["address"],
                          self.email_messages[1]["address"]],
                         ["crashes@example.com",
                          config_lib.CONFIG["Monitoring.alert_email"]])

  def testNannyMessage(self):
    nanny_message = "Oh no!"
    self.email_message = {}

    def SendEmail(address, sender, title, message, **_):
      self.email_message.update(dict(address=address, sender=sender,
                                     title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      msg = rdf_flows.GrrMessage(
          session_id=rdfvalue.SessionID(flow_name="NannyMessage"),
          payload=rdf_protodict.DataBlob(string=nanny_message),
          source=self.client_id,
          auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

      # This is normally done by the FrontEnd when a CLIENT_KILLED message is
      # received.
      flow.Events.PublishEvent("NannyMessage", msg, token=self.token)

      # Now emulate a worker to process the event.
      worker = test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

      # We expect the email to be sent.
      self.assertEqual(self.email_message.get("address"),
                       config_lib.CONFIG["Monitoring.alert_email"])
      self.assertTrue(str(self.client_id) in self.email_message["title"])

      # Make sure the message is included in the email message.
      self.assertTrue(nanny_message in self.email_message["message"])

      # Make sure crashes RDFValueCollections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = list(aff4.FACTORY.Open(
          self.client_id.Add("crashes"),
          aff4_type="PackedVersionedCollection",
          token=self.token))

      self.assertEqual(len(client_crashes), 1)
      crash = client_crashes[0]
      self.assertEqual(crash.client_id, self.client_id)
      self.assertEqual(crash.client_info.client_name, "GRR Monitor")
      self.assertEqual(crash.crash_type, "aff4:/flows/" +
                       queues.FLOWS.Basename() + ":NannyMessage")
      self.assertEqual(crash.crash_message, nanny_message)

      # Check global crash collection. Check that crash written there is
      # equal to per-client crash.
      global_crashes = list(aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("crashes"),
          aff4_type="PackedVersionedCollection",
          token=self.token))
      self.assertEqual(len(global_crashes), 1)
      self.assertEqual(global_crashes[0], crash)

  def testStartupHandler(self):
    # Clean the client records.
    aff4.FACTORY.Delete(self.client_id, token=self.token)

    client_mock = action_mocks.ActionMock("SendStartupInfo")
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
    self.assertAlmostEqual(psutil.boot_time(), boot_time.AsSecondsFromEpoch())

    # Run it again - this should not update any record.
    for _ in test_lib.TestFlowHelper(
        "ClientActionRunner", client_mock, client_id=self.client_id,
        action="SendStartupInfo", token=self.token):
      pass

    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.assertEqual(boot_time.age, fd.Get(fd.Schema.LAST_BOOT_TIME).age)
    self.assertEqual(client_info.age, fd.Get(fd.Schema.CLIENT_INFO).age)

    # Simulate a reboot in 10 minutes.
    current_boot_time = psutil.boot_time()
    psutil.boot_time = lambda: current_boot_time + 600

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
    with test_lib.ConfigOverrider({
        "Client.build_time": time.ctime()}):

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
    client_mock = action_mocks.ActionMock("ExecutePython")
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
    client_mock = action_mocks.ActionMock("ExecutePython")
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
    client_mock = action_mocks.ActionMock("ExecuteBinaryCommand")

    code = "I am a binary file"
    upload_path = config_lib.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, token=self.token)

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create("aff4:/users/%s" % self.token.username,
                               mode="rw", aff4_type="GRRUser", token=self.token)
    user.SetLabels("admin", owner="GRR")
    user.Close()

    with utils.Stubber(subprocess, "Popen", test_lib.Popen):
      for _ in test_lib.TestFlowHelper(
          "LaunchBinary", client_mock, client_id=self.client_id,
          binary=upload_path, command_line="--value 356", token=self.token):
        pass

      # Check that the executable file contains the code string.
      self.assertEqual(test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(test_lib.Popen.running_args[1], "--value")
      self.assertEqual(test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertTrue(test_lib.Popen.running_args[0].startswith(
          config_lib.CONFIG["Client.tempdir_roots"][0]))

  def testExecuteLargeBinaries(self):
    client_mock = action_mocks.ActionMock("ExecuteBinaryCommand")

    code = "I am a large binary file" * 100
    upload_path = config_lib.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, limit=100, token=self.token)

    # Ensure the aff4 collection has many items.
    fd = aff4.FACTORY.Open(upload_path, token=self.token)

    # Total size is 2400.
    self.assertEqual(len(fd), 2400)

    # There should be 24 parts to this binary.
    self.assertEqual(len(fd.collection), 24)

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create("aff4:/users/%s" % self.token.username,
                               mode="rw", aff4_type="GRRUser", token=self.token)
    user.SetLabels("admin", owner="GRR")
    user.Close()

    with utils.Stubber(subprocess, "Popen", test_lib.Popen):
      for _ in test_lib.TestFlowHelper(
          "LaunchBinary", client_mock, client_id=self.client_id,
          binary=upload_path, command_line="--value 356", token=self.token):
        pass

      # Check that the executable file contains the code string.
      self.assertEqual(test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(test_lib.Popen.running_args[1], "--value")
      self.assertEqual(test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertTrue(test_lib.Popen.running_args[0].startswith(
          config_lib.CONFIG["Client.tempdir_roots"][0]))

  def testGetClientStats(self):

    class ClientMock(object):

      def GetClientStats(self, _):
        """Fake get client stats method."""
        response = rdf_client.ClientStats()
        for i in range(12):
          sample = rdf_client.CpuSample(
              timestamp=int(i * 10 * 1e6),
              user_cpu_time=10 + i,
              system_cpu_time=20 + i,
              cpu_percent=10 + i)
          response.cpu_samples.Append(sample)

          sample = rdf_client.IOSample(
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
                           sum(range(10, 16)) / 6.0)
    self.assertAlmostEqual(sample.cpu_samples[1].cpu_percent,
                           sum(range(16, 22)) / 6.0)

    self.assertAlmostEqual(sample.cpu_samples[0].user_cpu_time, 15.0)
    self.assertAlmostEqual(sample.cpu_samples[1].system_cpu_time, 31.0)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
