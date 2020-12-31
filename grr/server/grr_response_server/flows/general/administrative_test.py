#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for administrative flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import subprocess
import sys
from unittest import mock

from absl import app
import psutil

from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import tests_pb2
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow_base
from grr_response_server import maintenance_utils
from grr_response_server import server_stubs
from grr_response_server import signed_binary_utils
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import discovery
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ClientActionRunnerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.ClientActionRunnerArgs


class ClientActionRunner(flow_base.FlowBase):
  """Just call the specified client action directly."""
  args_type = ClientActionRunnerArgs

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes[self.args.action],
        next_state="End")


class KeepAliveFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Tests for the KeepAlive flow."""

  def testKeepAliveRunsSuccessfully(self):
    client_id = self.SetupClient(0)
    client_mock = action_mocks.ActionMock(admin.Echo)
    flow_test_lib.TestFlowHelper(
        compatibility.GetName(administrative.KeepAlive),
        duration=rdfvalue.Duration.From(1, rdfvalue.SECONDS),
        client_id=client_id,
        client_mock=client_mock,
        token=self.token)


class TestAdministrativeFlows(flow_test_lib.FlowTestsBaseclass,
                              hunt_test_lib.StandardHuntTestMixin):
  """Tests the administrative flows."""

  def setUp(self):
    super(TestAdministrativeFlows, self).setUp()

    config_overrider = test_lib.ConfigOverrider({
        # Make sure that Client.tempdir_roots are unique. Otherwise parallel
        # test execution may lead to races.
        "Client.tempdir_roots": [self.temp_dir],
        "Monitoring.alert_email": "grr-monitoring@localhost",
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

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

    client = data_store.REL_DB.ReadClientSnapshot(client_id)
    config_dat = {item.key: item.value for item in client.grr_configuration}
    # The grr_configuration only contains strings.
    # TODO: We use eval here, because in Python 2 these server URLs
    # are a stringified list and have leading 'u' characters (to denote unicode
    # literals). To overcome this difference in Python versions, we use `eval`
    # to evaluate these lists. Once support for Python 2 is dropped, this can be
    # again made an equality check for raw string contents.
    self.assertEqual(
        eval(config_dat["Client.server_urls"]),  # pylint: disable=eval-used
        ["http://www.example.com/"])
    self.assertEqual(config_dat["Client.poll_min"], "1.0")

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

    self.assertIn(client_id, email_message["title"])
    rel_flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(rel_flow_obj.flow_state, rel_flow_obj.FlowState.CRASHED)

    # Make sure client object is updated with the last crash.
    crash = data_store.REL_DB.ReadClientCrashInfo(client_id)
    self.CheckCrash(crash, client.flow_id, client_id)

  def _CheckNannyEmail(self, client_id, nanny_message, email_dict):
    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"])

    # Make sure the message is included in the email message.
    self.assertIn(nanny_message, email_dict["message"])

    self.assertIn(client_id, email_dict["title"])
    crash = data_store.REL_DB.ReadClientCrashInfo(client_id)

    self.assertEqual(crash.client_id, client_id)
    self.assertEqual(crash.client_info.client_name, "GRR Monitor")
    self.assertEqual(crash.crash_type, "Nanny Message")
    self.assertEqual(crash.crash_message, nanny_message)

  def _CheckAlertEmail(self, client_id, message, email_dict):
    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"])

    self.assertIn(client_id, email_dict["title"])

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
        code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/test")

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
        code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/test")

    flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock,
        client_id=client_id,
        hack_name="test",
        py_args=dict(value=5678),
        token=self.token)

    self.assertEqual(sys.test_code_ran_here, 5678)

  def testExecutePythonHackWithResult(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    code = """
magic_return_str = str(py_args["foobar"])
    """

    maintenance_utils.UploadSignedConfigBlob(
        content=code.encode("utf-8"),
        aff4_path="aff4:/config/python_hacks/quux")

    flow_id = flow_test_lib.TestFlowHelper(
        administrative.ExecutePythonHack.__name__,
        client_mock=action_mocks.ActionMock(standard.ExecutePython),
        client_id=client_id,
        hack_name="quux",
        py_args={"foobar": 42},
        token=self.token)

    flow_test_lib.FinishAllFlowsOnClient(client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], administrative.ExecutePythonHackResult)
    self.assertEqual(results[0].result_string, "42")

  def testExecuteBinariesWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = b"I am a binary file"
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(code, aff4_path=upload_path)

    binary_urn = rdfvalue.RDFURN(upload_path)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn)

    # There should be only a single part to this binary.
    self.assertLen(list(blob_iterator), 1)

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
        code, aff4_path=upload_path, limit=100)

    binary_urn = rdfvalue.RDFURN(upload_path)
    binary_size = signed_binary_utils.FetchSizeOfSignedBinary(binary_urn)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn)

    # Total size is 2400.
    self.assertEqual(binary_size, 2400)

    # There should be 24 parts to this binary.
    self.assertLen(list(blob_iterator), 24)

    # This flow has an acl, the user needs to be admin.
    acl_test_lib.CreateAdminUser(self.token.username)

    with utils.Stubber(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.TestFlowHelper(
          compatibility.GetName(administrative.LaunchBinary),
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

  def testExecuteBinaryWeirdOutput(self):
    binary_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add("foo.exe")
    maintenance_utils.UploadSignedConfigBlob(
        b"foobarbaz", aff4_path=binary_path)

    client_id = self.SetupClient(0)

    def Run(self, args):
      del args  # Unused.

      stdout = "żółć %s gęślą {} jaźń # ⛷".encode("utf-8")
      stderr = b"\x00\xff\x00\xff\x00"

      response = rdf_client_action.ExecuteBinaryResponse(
          stdout=stdout, stderr=stderr, exit_status=0, time_used=0)
      self.SendReply(response)

    with mock.patch.object(standard.ExecuteBinaryCommand, "Run", new=Run):
      # Should not fail.
      flow_test_lib.TestFlowHelper(
          administrative.LaunchBinary.__name__,
          action_mocks.ActionMock(standard.ExecuteBinaryCommand),
          binary=binary_path,
          client_id=client_id,
          command_line="--bar --baz",
          token=self.token)

  def testUpdateClient(self):
    client_mock = action_mocks.UpdateAgentClientMock()
    fake_installer = b"FakeGRRDebInstaller" * 20
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.deb")
    maintenance_utils.UploadSignedConfigBlob(
        fake_installer, aff4_path=upload_path, limit=100)

    blob_list, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        upload_path)
    self.assertLen(list(blob_list), 4)

    acl_test_lib.CreateAdminUser(self.token.username)

    flow_test_lib.TestFlowHelper(
        administrative.UpdateClient.__name__,
        client_mock,
        client_id=self.SetupClient(0, system=""),
        binary_path=os.path.join(config.CONFIG["Client.platform"], "test.deb"),
        token=self.token)
    self.assertEqual(client_mock.GetDownloadedFileContents(), fake_installer)

  def testUpdateClientSingleBlob(self):
    client_mock = action_mocks.UpdateAgentClientMock()
    fake_installer = b"FakeGRRDebInstaller" * 20
    upload_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add(
        config.CONFIG["Client.platform"]).Add("test.deb")
    maintenance_utils.UploadSignedConfigBlob(
        fake_installer, aff4_path=upload_path, limit=1000)

    blob_list, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        upload_path)
    self.assertLen(list(blob_list), 1)

    acl_test_lib.CreateAdminUser(self.token.username)

    flow_test_lib.TestFlowHelper(
        compatibility.GetName(administrative.UpdateClient),
        client_mock,
        client_id=self.SetupClient(0, system=""),
        binary_path=os.path.join(config.CONFIG["Client.platform"], "test.deb"),
        token=self.token)
    self.assertEqual(client_mock.GetDownloadedFileContents(), fake_installer)

  def testGetClientStats(self):
    client_id = self.SetupClient(0)

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

    samples = data_store.REL_DB.ReadClientStats(
        client_id=client_id,
        min_timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0),
        max_timestamp=rdfvalue.RDFDatetime.Now())
    self.assertNotEmpty(samples)
    sample = samples[0]

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
    self.assertIn("This notification was created by %s" % self.token.username,
                  email_message.get("message", ""))

  def testStartupHandler(self):
    client_id = self.SetupClient(0)

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
      build_time = compatibility.FormatTime("%a %b %d %H:%M:%S %Y")
      with test_lib.ConfigOverrider({"Client.build_time": build_time}):

        # Run it again - this should now update the client info.
        self._RunSendStartupInfo(client_id)

        new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
        self.assertIsNotNone(new_si)
        self.assertNotEqual(new_si.client_info, si.client_info)

  def testStartupHandlerNewLabels(self):
    client_id = self.SetupClient(0, labels=[])
    index = client_index.ClientIndex()

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertEmpty(labels)

    snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    self.assertEmpty(snapshot.startup_info.client_info.labels)

    search_result = index.LookupClients(["label:test_label"])
    self.assertEmpty(search_result)

    with test_lib.ConfigOverrider({"Client.labels": ["test_label"]}):
      self._RunSendStartupInfo(client_id)

    # Just sending the startup info with an updated label should also write the
    # new label to the client_labels table and update the search index so the
    # client can now also be found using the new label.

    labels = data_store.REL_DB.ReadClientLabels(client_id)
    self.assertLen(labels, 1)
    self.assertEqual(labels[0].name, "test_label")

    search_result = index.LookupClients(["label:test_label"])
    self.assertEqual(search_result, [client_id])

  def testNannyMessageHandler(self):
    client_id = self.SetupClient(0)
    nanny_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

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
    client_id = self.SetupClient(0)
    nanny_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

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

    self.assertIn(client_id, email_dict["title"])

  def testClientAlertHandler(self):
    client_id = self.SetupClient(0)
    client_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message))

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
  app.run(main)
