#!/usr/bin/env python
"""Tests for administrative flows."""

import os
import subprocess
import sys
import time


import psutil

from grr import config
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import email_alerts
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import maintenance_utils
from grr.server.grr_response_server import server_stubs
from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import stats as aff4_stats
from grr.server.grr_response_server.aff4_objects import users
from grr.server.grr_response_server.flows.general import administrative
# pylint: disable=unused-import
# For AuditEventListener, needed to handle published audit events.
from grr.server.grr_response_server.flows.general import audit as _
# pylint: enable=unused-import
from grr.server.grr_response_server.flows.general import discovery
from grr.server.grr_response_server.hunts import implementation as hunts_implementation
from grr.server.grr_response_server.hunts import standard as hunts_standard
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class ClientActionRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ClientActionRunnerArgs


class ClientActionRunner(flow.GRRFlow):
  """Just call the specified client action directly.
  """
  args_type = ClientActionRunnerArgs
  action_args = {}

  @flow.StateHandler()
  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes[self.args.action],
        next_state="End",
        **self.action_args)


class AdministrativeFlowTests(flow_test_lib.FlowTestsBaseclass):
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

    # Write a client without a proper system so we don't need to
    # provide the os specific artifacts in the interrogate flow below.
    client_id = self.SetupClient(0, system="")

    # Only mock the pieces we care about.
    client_mock = action_mocks.ActionMock(admin.GetConfiguration,
                                          admin.UpdateConfiguration)

    loc = "http://www.example.com"
    new_config = rdf_protodict.Dict({
        "Client.server_urls": [loc],
        "Client.foreman_check_frequency": 3600,
        "Client.poll_min": 1
    })

    # Setting config options is disallowed in tests so we need to temporarily
    # revert this.
    with utils.Stubber(config.CONFIG, "Set", config.CONFIG.Set.old_target):
      # Write the config.
      flow_test_lib.TestFlowHelper(
          administrative.UpdateConfiguration.__name__,
          client_mock,
          client_id=client_id,
          token=self.token,
          config=new_config)

    # Now retrieve it again to see if it got written.
    flow_test_lib.TestFlowHelper(
        discovery.Interrogate.__name__,
        client_mock,
        token=self.token,
        client_id=client_id)

    fd = aff4.FACTORY.Open(client_id, token=self.token)
    config_dat = fd.Get(fd.Schema.GRR_CONFIGURATION)
    self.assertEqual(config_dat["Client.server_urls"], [loc])
    self.assertEqual(config_dat["Client.poll_min"], 1)

  def CheckCrash(self, crash, expected_session_id, client_id):
    """Checks that ClientCrash object's fields are correctly filled in."""
    self.assertTrue(crash is not None)
    self.assertEqual(crash.client_id, client_id)
    self.assertEqual(crash.session_id, expected_session_id)
    self.assertEqual(crash.client_info.client_name, "GRR Monitor")
    self.assertEqual(crash.crash_type, "Client Crash")
    self.assertEqual(crash.crash_message, "Client killed during transaction")

  def testAlertEmailIsSentWhenClientKilled(self):
    """Test that client killed messages are handled correctly."""
    client_id = self.SetupClient(0)
    self.SetupTestClientObject(0)

    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = flow_test_lib.CrashClientMock(client_id, self.token)
      flow_test_lib.TestFlowHelper(
          flow_test_lib.FlowWithOneClientRequest.__name__,
          client,
          client_id=client_id,
          token=self.token,
          check_flow_errors=False)

    self.assertEqual(len(self.email_messages), 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(
        email_message.get("address", ""),
        config.CONFIG["Monitoring.alert_email"])
    self.assertTrue(str(client_id) in email_message["title"])

    # Make sure the flow state is included in the email message.
    for s in [
        "flow_name", flow_test_lib.FlowWithOneClientRequest.__name__,
        "current_state"
    ]:
      self.assertTrue(s in email_message["message"])

    flow_obj = aff4.FACTORY.Open(
        client.flow_id, age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(flow_obj.context.state, rdf_flows.FlowContext.State.ERROR)

    # Make sure client object is updated with the last crash.

    # AFF4.
    client_obj = aff4.FACTORY.Open(client_id, token=self.token)
    crash = client_obj.Get(client_obj.Schema.LAST_CRASH)
    self.CheckCrash(crash, flow_obj.session_id, client_id)

    # Relational db.
    crash = data_store.REL_DB.ReadClientCrashInfo(client_id.Basename())
    self.CheckCrash(crash, flow_obj.session_id, client_id)

    # Make sure crashes collections are created and written
    # into proper locations. First check the per-client crashes collection.
    client_crashes = sorted(
        list(aff4_grr.VFSGRRClient.CrashCollectionForCID(client_id)),
        key=lambda x: x.timestamp)

    self.assertTrue(len(client_crashes) >= 1)
    crash = list(client_crashes)[0]
    self.CheckCrash(crash, flow_obj.session_id, client_id)

    # Check per-flow crash collection. Check that crash written there is
    # equal to per-client crash.
    flow_crashes = sorted(
        list(flow_obj.GetValuesForAttribute(flow_obj.Schema.CLIENT_CRASH)),
        key=lambda x: x.timestamp)
    self.assertEqual(len(flow_crashes), len(client_crashes))
    for a, b in zip(flow_crashes, client_crashes):
      self.assertEqual(a, b)

  def testAlertEmailIsSentWhenClientKilledDuringHunt(self):
    """Test that client killed messages are handled correctly for hunts."""
    client_id = test_lib.TEST_CLIENT_ID
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    with hunts_implementation.GRRHunt.StartHunt(
        hunt_name=hunts_standard.GenericHunt.__name__,
        flow_runner_args=rdf_flows.FlowRunnerArgs(
            flow_name=flow_test_lib.FlowWithOneClientRequest.__name__),
        client_rate=0,
        crash_alert_email="crashes@example.com",
        token=self.token) as hunt:
      hunt.Run()
      hunt.StartClients(hunt.session_id, client_id)

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = flow_test_lib.CrashClientMock(client_id, self.token)
      hunt_test_lib.TestHuntHelper(
          client, [client_id], token=self.token, check_flow_errors=False)

    self.assertEqual(len(self.email_messages), 2)
    self.assertListEqual(
        [self.email_messages[0]["address"], self.email_messages[1]["address"]],
        ["crashes@example.com", config.CONFIG["Monitoring.alert_email"]])

  def testNannyMessage(self):
    client_id = self.SetupClient(0)
    nanny_message = "Oh no!"
    self.email_message = {}

    def SendEmail(address, sender, title, message, **_):
      self.email_message.update(
          dict(address=address, sender=sender, title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      self.SendResponse(
          session_id=rdfvalue.SessionID(flow_name="NannyMessage"),
          data=nanny_message,
          client_id=client_id,
          well_known=True)

      # Now emulate a worker to process the event.
      worker = worker_test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

      # We expect the email to be sent.
      self.assertEqual(
          self.email_message.get("address"),
          config.CONFIG["Monitoring.alert_email"])
      self.assertTrue(str(client_id) in self.email_message["title"])

      # Make sure the message is included in the email message.
      self.assertTrue(nanny_message in self.email_message["message"])

      # Make sure crashes collections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = list(
          aff4_grr.VFSGRRClient.CrashCollectionForCID(client_id))

      self.assertEqual(len(client_crashes), 1)
      crash = client_crashes[0]
      self.assertEqual(crash.client_id, client_id)
      self.assertEqual(crash.client_info.client_name, "GRR Monitor")
      self.assertEqual(crash.crash_type, "Nanny Message")
      self.assertEqual(crash.crash_message, nanny_message)

  def _RunSendStartupInfo(self, client_id):
    client_mock = action_mocks.ActionMock(admin.SendStartupInfo)
    flow_test_lib.TestFlowHelper(
        ClientActionRunner.__name__,
        client_mock,
        client_id=client_id,
        action="SendStartupInfo",
        token=self.token)

  def testStartupHandlerRelational(self):
    client_id = test_lib.TEST_CLIENT_ID

    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      rel_client_id = client_id.Basename()
      data_store.REL_DB.WriteClientMetadata(
          rel_client_id, fleetspeak_enabled=False)

      self._RunSendStartupInfo(client_id)

      si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
      self.assertIsNotNone(si)
      self.assertEqual(si.client_info.client_name, config.CONFIG["Client.name"])
      self.assertEqual(si.client_info.client_description,
                       config.CONFIG["Client.description"])

      # Run it again - this should not update any record.
      self._RunSendStartupInfo(client_id)

      new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
      self.assertEqual(new_si, si)

      # Simulate a reboot.
      current_boot_time = psutil.boot_time()
      with utils.Stubber(psutil, "boot_time", lambda: current_boot_time + 600):

        # Run it again - this should now update the boot time.
        self._RunSendStartupInfo(client_id)

        new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
        self.assertIsNotNone(new_si)
        self.assertNotEqual(new_si.boot_time, si.boot_time)

        # Now set a new client build time.
        with test_lib.ConfigOverrider({"Client.build_time": time.ctime()}):

          # Run it again - this should now update the client info.
          self._RunSendStartupInfo(client_id)

          new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
          self.assertIsNotNone(new_si)
          self.assertNotEqual(new_si.client_info, si.client_info)

  def testStartupHandler(self):
    client_id = test_lib.TEST_CLIENT_ID
    rel_client_id = client_id.Basename()
    data_store.REL_DB.WriteClientMetadata(
        rel_client_id, fleetspeak_enabled=True)

    self._RunSendStartupInfo(client_id)

    # AFF4 client.

    # Check the client's boot time and info.
    fd = aff4.FACTORY.Open(client_id, token=self.token)
    client_info = fd.Get(fd.Schema.CLIENT_INFO)
    boot_time = fd.Get(fd.Schema.LAST_BOOT_TIME)

    self.assertEqual(client_info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(client_info.client_description,
                     config.CONFIG["Client.description"])

    # Check that the boot time is accurate.
    self.assertAlmostEqual(psutil.boot_time(), boot_time.AsSecondsSinceEpoch())

    # objects.ClientSnapshot.

    si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
    self.assertIsNotNone(si)
    self.assertEqual(si.client_info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(si.client_info.client_description,
                     config.CONFIG["Client.description"])

    # Run it again - this should not update any record.
    self._RunSendStartupInfo(client_id)

    # AFF4 client.
    fd = aff4.FACTORY.Open(client_id, token=self.token)
    self.assertEqual(boot_time.age, fd.Get(fd.Schema.LAST_BOOT_TIME).age)
    self.assertEqual(client_info.age, fd.Get(fd.Schema.CLIENT_INFO).age)

    # objects.ClientSnapshot.

    new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
    self.assertEqual(new_si, si)

    # Simulate a reboot.
    current_boot_time = psutil.boot_time()
    with utils.Stubber(psutil, "boot_time", lambda: current_boot_time + 600):

      # Run it again - this should now update the boot time.
      self._RunSendStartupInfo(client_id)

      # AFF4 client.

      # Ensure only this attribute is updated.
      fd = aff4.FACTORY.Open(client_id, token=self.token)
      self.assertNotEqual(
          int(boot_time.age), int(fd.Get(fd.Schema.LAST_BOOT_TIME).age))
      self.assertEqual(
          int(client_info.age), int(fd.Get(fd.Schema.CLIENT_INFO).age))

      # objects.ClientSnapshot.
      new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
      self.assertIsNotNone(new_si)
      self.assertNotEqual(new_si.boot_time, si.boot_time)

      # Now set a new client build time.
      with test_lib.ConfigOverrider({"Client.build_time": time.ctime()}):

        # Run it again - this should now update the client info.
        self._RunSendStartupInfo(client_id)

        # AFF4 client.

        # Ensure the client info attribute is updated.
        fd = aff4.FACTORY.Open(client_id, token=self.token)
        self.assertNotEqual(
            int(client_info.age), int(fd.Get(fd.Schema.CLIENT_INFO).age))

        # objects.ClientSnapshot.
        new_si = data_store.REL_DB.ReadClientStartupInfo(rel_client_id)
        self.assertIsNotNone(new_si)
        self.assertNotEqual(new_si.client_info, si.client_info)

  def testExecutePythonHack(self):
    client_mock = action_mocks.ActionMock(standard.ExecutePython)
    # This is the code we test. If this runs on the client mock we can check for
    # this attribute.
    sys.test_code_ran_here = False

    code = """
import sys
sys.test_code_ran_here = True
"""
    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path="aff4:/config/python_hacks/test", token=self.token)

    flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock,
        client_id=test_lib.TEST_CLIENT_ID,
        hack_name="test",
        token=self.token)

    self.assertTrue(sys.test_code_ran_here)

  def testExecutePythonHackWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecutePython)
    sys.test_code_ran_here = 1234
    code = """
import sys
sys.test_code_ran_here = py_args['value']
"""
    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path="aff4:/config/python_hacks/test", token=self.token)

    flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock,
        client_id=test_lib.TEST_CLIENT_ID,
        hack_name="test",
        py_args=dict(value=5678),
        token=self.token)

    self.assertEqual(sys.test_code_ran_here, 5678)

  def testExecuteBinariesWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = "I am a binary file"
    upload_path = config.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, token=self.token)

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create(
        "aff4:/users/%s" % self.token.username,
        mode="rw",
        aff4_type=users.GRRUser,
        token=self.token)
    user.SetLabel("admin", owner="GRRTest")
    user.Close()

    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.TestFlowHelper(
          administrative.LaunchBinary.__name__,
          client_mock,
          client_id=test_lib.TEST_CLIENT_ID,
          binary=upload_path,
          command_line="--value 356",
          token=self.token)

      # Check that the executable file contains the code string.
      self.assertEqual(client_test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, client_test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(client_test_lib.Popen.running_args[1], "--value")
      self.assertEqual(client_test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertTrue(client_test_lib.Popen.running_args[0].startswith(
          config.CONFIG["Client.tempdir_roots"][0]))

  def testExecuteLargeBinaries(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = "I am a large binary file" * 100
    upload_path = config.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, limit=100, token=self.token)

    # Ensure the aff4 collection has many items.
    fd = aff4.FACTORY.Open(upload_path, token=self.token)

    # Total size is 2400.
    self.assertEqual(len(fd), 2400)

    # There should be 24 parts to this binary.
    self.assertEqual(len(fd.collection), 24)

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create(
        "aff4:/users/%s" % self.token.username,
        mode="rw",
        aff4_type=users.GRRUser,
        token=self.token)
    user.SetLabel("admin", owner="GRRTest")
    user.Close()

    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.TestFlowHelper(
          administrative.LaunchBinary.__name__,
          client_mock,
          client_id=test_lib.TEST_CLIENT_ID,
          binary=upload_path,
          command_line="--value 356",
          token=self.token)

      # Check that the executable file contains the code string.
      self.assertEqual(client_test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, client_test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(client_test_lib.Popen.running_args[1], "--value")
      self.assertEqual(client_test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertTrue(client_test_lib.Popen.running_args[0].startswith(
          config.CONFIG["Client.tempdir_roots"][0]))

  def testGetClientStats(self):
    client_id = test_lib.TEST_CLIENT_ID

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

    flow_test_lib.TestFlowHelper(
        administrative.GetClientStats.__name__,
        ClientMock(),
        token=self.token,
        client_id=client_id)

    urn = client_id.Add("stats")
    stats_fd = aff4.FACTORY.Create(
        urn, aff4_stats.ClientStats, token=self.token, mode="rw")
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

  def testOnlineNotificationEmail(self):
    """Tests that the mail is sent in the OnlineNotification flow."""
    client_id = self.SetupClient(0)
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client_mock = action_mocks.ActionMock(admin.Echo)
      flow_test_lib.TestFlowHelper(
          administrative.OnlineNotification.__name__,
          client_mock,
          args=administrative.OnlineNotificationArgs(email="test@localhost"),
          token=self.token,
          client_id=client_id)

    self.assertEqual(len(self.email_messages), 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(email_message.get("address", ""), "test@localhost")
    self.assertEqual(email_message["title"],
                     "GRR Client on Host-0 became available.")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
