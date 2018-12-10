#!/usr/bin/env python
"""Tests for administrative flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import subprocess
import sys
import time


from builtins import range  # pylint: disable=redefined-builtin
from builtins import zip  # pylint: disable=redefined-builtin
import psutil

from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow_base
from grr_response_server import maintenance_utils
from grr_response_server import server_stubs
from grr_response_server import signed_binary_utils
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.general import administrative
# pylint: disable=unused-import
# For AuditEventListener, needed to handle published audit events.
from grr_response_server.flows.general import audit as _
# pylint: enable=unused-import
from grr_response_server.flows.general import discovery
from grr_response_server.hunts import implementation as hunts_implementation
from grr_response_server.hunts import standard as hunts_standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class ClientActionRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ClientActionRunnerArgs


@flow_base.DualDBFlow
class ClientActionRunnerMixin(object):
  """Just call the specified client action directly."""
  args_type = ClientActionRunnerArgs

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes[self.args.action],
        next_state="End")


class TestAdministrativeFlows(flow_test_lib.FlowTestsBaseclass):
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

    loc = "http://www.example.com/"
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

    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(client_id.Basename())
      config_dat = {item.key: item.value for item in client.grr_configuration}
      # The grr_configuration only contains strings.
      self.assertEqual(config_dat["Client.server_urls"],
                       "[u'http://www.example.com/']")
      self.assertEqual(config_dat["Client.poll_min"], "1.0")
    else:
      fd = aff4.FACTORY.Open(client_id, token=self.token)
      config_dat = fd.Get(fd.Schema.GRR_CONFIGURATION)
      self.assertEqual(config_dat["Client.server_urls"], [loc])
      self.assertEqual(config_dat["Client.poll_min"], 1)

  def CheckCrash(self, crash, expected_session_id, client_id):
    """Checks that ClientCrash object's fields are correctly filled in."""
    self.assertIsNotNone(crash)
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
      flow_id = flow_test_lib.TestFlowHelper(
          flow_test_lib.FlowWithOneClientRequest.__name__,
          client,
          client_id=client_id,
          token=self.token,
          check_flow_errors=False)

    self.assertLen(self.email_messages, 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(
        email_message.get("address", ""),
        config.CONFIG["Monitoring.alert_email"])

    # Make sure the flow state is included in the email message.
    self.assertIn("Host-0.example.com", email_message["message"])
    self.assertIn("http://localhost:8000/#/clients/C.1000000000000000",
                  email_message["message"])

    if data_store.RelationalDBFlowsEnabled():
      self.assertIn(client_id.Basename(), email_message["title"])
      rel_flow_obj = data_store.REL_DB.ReadFlowObject(client_id.Basename(),
                                                      flow_id)
      self.assertEqual(rel_flow_obj.flow_state, rel_flow_obj.FlowState.ERROR)

      # Make sure client object is updated with the last crash.
      crash = data_store.REL_DB.ReadClientCrashInfo(client_id.Basename())
      self.CheckCrash(crash, client.flow_id, client_id.Basename())
    else:
      self.assertIn(client_id.Basename(), email_message["title"])
      flow_obj = aff4.FACTORY.Open(
          flow_id, age=aff4.ALL_TIMES, token=self.token)
      self.assertEqual(flow_obj.context.state,
                       rdf_flow_runner.FlowContext.State.ERROR)

      # Make sure client object is updated with the last crash.
      client_obj = aff4.FACTORY.Open(client_id, token=self.token)
      crash = client_obj.Get(client_obj.Schema.LAST_CRASH)
      self.CheckCrash(crash, client.flow_id, client_id)

      # Make sure crashes collections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = sorted(
          list(aff4_grr.VFSGRRClient.CrashCollectionForCID(client_id)),
          key=lambda x: x.timestamp)

      self.assertLen(client_crashes, 1)
      crash = list(client_crashes)[0]
      self.CheckCrash(crash, client.flow_id, client_id)

      # Check per-flow crash collection. Check that crash written there is
      # equal to per-client crash.
      flow_crashes = sorted(
          list(flow_obj.GetValuesForAttribute(flow_obj.Schema.CLIENT_CRASH)),
          key=lambda x: x.timestamp)
      self.assertLen(flow_crashes, len(client_crashes))
      for a, b in zip(flow_crashes, client_crashes):
        self.assertEqual(a, b)

  def testAlertEmailIsSentWhenClientKilledDuringHunt(self):
    """Test that client killed messages are handled correctly for hunts."""
    client_id = self.SetupClient(0)
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    with hunts_implementation.StartHunt(
        hunt_name=hunts_standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=flow_test_lib.FlowWithOneClientRequest.__name__),
        client_rate=0,
        crash_alert_email="crashes@example.com",
        token=self.token) as hunt:
      hunt.Run()
      hunt.StartClients(hunt.session_id, [client_id])

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = flow_test_lib.CrashClientMock(client_id, self.token)
      hunt_test_lib.TestHuntHelper(
          client, [client_id], token=self.token, check_flow_errors=False)

    self.assertLen(self.email_messages, 2)
    self.assertListEqual(
        [self.email_messages[0]["address"], self.email_messages[1]["address"]],
        ["crashes@example.com", config.CONFIG["Monitoring.alert_email"]])

  def testNannyMessageFlow(self):
    client_id = self.SetupClient(0)
    email_dict = {}
    with test_lib.ConfigOverrider(
        {"Database.useForReads.message_handlers": False}):
      nanny_message = "Oh no!"
      self.SendResponse(
          session_id=rdfvalue.SessionID(flow_name="NannyMessage"),
          data=nanny_message,
          client_id=client_id,
          well_known=True)

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      # Now emulate a worker to process the event.
      worker = worker_test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

    self._CheckNannyEmail(client_id, nanny_message, email_dict)

  def _CheckNannyEmail(self, client_id, nanny_message, email_dict):
    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"])

    # Make sure the message is included in the email message.
    self.assertIn(nanny_message, email_dict["message"])

    if data_store.RelationalDBReadEnabled():
      self.assertIn(client_id, email_dict["title"])
      crash = data_store.REL_DB.ReadClientCrashInfo(client_id)
    else:
      self.assertIn(client_id.Basename(), email_dict["title"])

      # Make sure crashes collections are created and written
      # into proper locations. First check the per-client crashes collection.
      client_crashes = list(
          aff4_grr.VFSGRRClient.CrashCollectionForCID(client_id))

      self.assertLen(client_crashes, 1)
      crash = client_crashes[0]

    self.assertEqual(crash.client_id, client_id)
    self.assertEqual(crash.client_info.client_name, "GRR Monitor")
    self.assertEqual(crash.crash_type, "Nanny Message")
    self.assertEqual(crash.crash_message, nanny_message)

  def testClientAlertFlow(self):
    client_id = self.SetupClient(0)
    email_dict = {}
    with test_lib.ConfigOverrider(
        {"Database.useForReads.message_handlers": False}):
      client_message = "Oh no!"
      self.SendResponse(
          session_id=rdfvalue.SessionID(flow_name="ClientAlert"),
          data=client_message,
          client_id=client_id,
          well_known=True)

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      # Now emulate a worker to process the event.
      worker = worker_test_lib.MockWorker(token=self.token)
      while worker.Next():
        pass
      worker.pool.Join()

    self._CheckAlertEmail(client_id, client_message, email_dict)

  def _CheckAlertEmail(self, client_id, message, email_dict):
    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"])

    if data_store.RelationalDBReadEnabled():
      self.assertIn(client_id, email_dict["title"])
    else:
      self.assertIn(client_id.Basename(), email_dict["title"])

    # Make sure the message is included in the email message.
    self.assertIn(message, email_dict["message"])

  def _RunSendStartupInfo(self, client_id):
    client_mock = action_mocks.ActionMock(admin.SendStartupInfo)
    # Undefined name since the flow class get autogenerated.
    flow_test_lib.TestFlowHelper(
        ClientActionRunner.__name__,  # pylint: disable=undefined-variable
        client_mock,
        client_id=client_id,
        action="SendStartupInfo",
        token=self.token)

  def testStartupFlow(self):
    with test_lib.ConfigOverrider(
        {"Database.useForReads.message_handlers": False}):
      client_id = self.SetupClient(0)
      rel_client_id = client_id.Basename()
      data_store.REL_DB.WriteClientMetadata(
          rel_client_id, fleetspeak_enabled=False)

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
      self.assertAlmostEqual(psutil.boot_time(),
                             boot_time.AsSecondsSinceEpoch())

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

    client_id = self.SetupClient(0)

    code = """
import sys
sys.test_code_ran_here = True
"""
    maintenance_utils.UploadSignedConfigBlob(
        code.encode("utf-8"),
        aff4_path="aff4:/config/python_hacks/test",
        token=self.token)

    flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock,
        client_id=client_id,
        hack_name="test",
        token=self.token)

    self.assertTrue(sys.test_code_ran_here)

  def testExecutePythonHackWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecutePython)
    sys.test_code_ran_here = 1234
    code = "import sys\nsys.test_code_ran_here = py_args['value']\n"

    client_id = self.SetupClient(0)

    maintenance_utils.UploadSignedConfigBlob(
        code.encode("utf-8"),
        aff4_path="aff4:/config/python_hacks/test",
        token=self.token)

    flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock,
        client_id=client_id,
        hack_name="test",
        py_args=dict(value=5678),
        token=self.token)

    self.assertEqual(sys.test_code_ran_here, 5678)

  def testExecuteBinariesWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = b"I am a binary file"
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, token=self.token)

    # This flow has an acl, the user needs to be admin.
    acl_test_lib.CreateAdminUser(self.token.username)

    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.TestFlowHelper(
          administrative.LaunchBinary.__name__,
          client_mock,
          client_id=self.SetupClient(0),
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
      self.assertStartsWith(client_test_lib.Popen.running_args[0],
                            config.CONFIG["Client.tempdir_roots"][0])

  def testExecuteLargeBinaries(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = b"I am a large binary file" * 100
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, limit=100, token=self.token)

    binary_urn = rdfvalue.RDFURN(upload_path)
    binary_size = signed_binary_utils.FetchSizeOfSignedBinary(
        binary_urn, token=self.token)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinary(
        binary_urn, token=self.token)

    # Total size is 2400.
    self.assertEqual(binary_size, 2400)

    # There should be 24 parts to this binary.
    self.assertLen(list(blob_iterator), 24)

    # This flow has an acl, the user needs to be admin.
    acl_test_lib.CreateAdminUser(self.token.username)

    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.TestFlowHelper(
          administrative.LaunchBinary.__name__,
          client_mock,
          client_id=self.SetupClient(0),
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
      self.assertStartsWith(client_test_lib.Popen.running_args[0],
                            config.CONFIG["Client.tempdir_roots"][0])

  def testUpdateClient(self):
    client_mock = action_mocks.UpdateAgentClientMock()
    fake_installer = b"FakeGRRDebInstaller" * 20
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.deb")
    maintenance_utils.UploadSignedConfigBlob(
        fake_installer, aff4_path=upload_path, limit=100, token=self.token)

    acl_test_lib.CreateAdminUser(self.token.username)

    flow_test_lib.TestFlowHelper(
        administrative.UpdateClient.__name__,
        client_mock,
        client_id=self.SetupClient(0, system=""),
        blob_path=upload_path,
        token=self.token)
    self.assertEqual(client_mock.GetDownloadedFileContents(), fake_installer)

  def testGetClientStats(self):
    client_id = self.SetupClient(0)

    # TODO(amoser): Fix this.
    if not data_store.AFF4Enabled():
      self.skipTest(
          "Client stats storage not yet implemented for the relational db.")

    class ClientMock(action_mocks.ActionMock):

      def GetClientStats(self, _):
        """Fake get client stats method."""
        response = rdf_client_stats.ClientStats()
        for i in range(12):
          sample = rdf_client_stats.CpuSample(
              timestamp=int(i * 10 * 1e6),
              user_cpu_time=10 + i,
              system_cpu_time=20 + i,
              cpu_percent=10 + i)
          response.cpu_samples.Append(sample)

          sample = rdf_client_stats.IOSample(
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

    self.assertLen(sample.cpu_samples, 2)
    self.assertLen(sample.io_samples, 2)

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

    self.assertLen(self.email_messages, 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(email_message.get("address", ""), "test@localhost")
    self.assertEqual(email_message["title"],
                     "GRR Client on Host-0.example.com became available.")


class TestAdministrativeFlowsRelFlows(db_test_lib.RelationalDBEnabledMixin,
                                      TestAdministrativeFlows):

  def testStartupFlow(self):
    # Replaced by handlers when running with relational flows, tested in
    # testStartupHandler.
    pass

  def testNannyMessageFlow(self):
    # Replaced by handlers when running with relational flows, tested in
    # testNannyMessageHandler.
    pass

  def testClientAlertFlow(self):
    # Replaced by handlers when running with relational flows, tested in
    # testClientAlertHandler.
    pass

  def testAlertEmailIsSentWhenClientKilledDuringHunt(self):
    # Starting new style flows from hunts is not yet implemented.
    # TODO(amoser): Fix this test once hunts are feature complete.
    pass

  def testStartupHandler(self):
    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True,
    }):
      client_id = self.SetupClient(0).Basename()

      self._RunSendStartupInfo(client_id)

      si = data_store.REL_DB.ReadClientStartupInfo(client_id)
      self.assertIsNotNone(si)
      self.assertEqual(si.client_info.client_name, config.CONFIG["Client.name"])
      self.assertEqual(si.client_info.client_description,
                       config.CONFIG["Client.description"])

      # Run it again - this should not update any record.
      self._RunSendStartupInfo(client_id)

      new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
      self.assertEqual(new_si, si)

      # Simulate a reboot.
      current_boot_time = psutil.boot_time()
      with utils.Stubber(psutil, "boot_time", lambda: current_boot_time + 600):

        # Run it again - this should now update the boot time.
        self._RunSendStartupInfo(client_id)

        new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
        self.assertIsNotNone(new_si)
        self.assertNotEqual(new_si.boot_time, si.boot_time)

        # Now set a new client build time.
        with test_lib.ConfigOverrider({"Client.build_time": time.ctime()}):

          # Run it again - this should now update the client info.
          self._RunSendStartupInfo(client_id)

          new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
          self.assertIsNotNone(new_si)
          self.assertNotEqual(new_si.client_info, si.client_info)

  def testNannyMessageHandler(self):
    client_id = self.SetupClient(0).Basename()
    nanny_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
        flow_test_lib.MockClient(client_id, None)._PushHandlerMessage(
            rdf_flows.GrrMessage(
                source=client_id,
                session_id=rdfvalue.SessionID(flow_name="NannyMessage"),
                payload=rdf_protodict.DataBlob(string=nanny_message),
                request_id=0,
                auth_state="AUTHENTICATED",
                response_id=123))

    self._CheckNannyEmail(client_id, nanny_message, email_dict)

  def testNannyMessageHandlerForUnknownClient(self):
    client_id = "C.1000000000000000"
    nanny_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
        flow_test_lib.MockClient(client_id, None)._PushHandlerMessage(
            rdf_flows.GrrMessage(
                source=client_id,
                session_id=rdfvalue.SessionID(flow_name="NannyMessage"),
                payload=rdf_protodict.DataBlob(string=nanny_message),
                request_id=0,
                auth_state="AUTHENTICATED",
                response_id=123))

    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"])

    # Make sure the message is included in the email message.
    self.assertIn(nanny_message, email_dict["message"])

    if data_store.RelationalDBReadEnabled():
      self.assertIn(client_id, email_dict["title"])
    else:
      self.assertIn(client_id.Basename(), email_dict["title"])

  def testClientAlertHandler(self):
    client_id = self.SetupClient(0).Basename()
    client_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
        flow_test_lib.MockClient(client_id, None)._PushHandlerMessage(
            rdf_flows.GrrMessage(
                source=client_id,
                session_id=rdfvalue.SessionID(flow_name="ClientAlert"),
                payload=rdf_protodict.DataBlob(string=client_message),
                request_id=0,
                auth_state="AUTHENTICATED",
                response_id=123))

    self._CheckAlertEmail(client_id, client_message, email_dict)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
