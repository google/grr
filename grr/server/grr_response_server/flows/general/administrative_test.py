#!/usr/bin/env python
"""Tests for administrative flows."""

import datetime
import os
import subprocess
import sys
import tempfile
from unittest import mock

from absl import app
import psutil

from grr_response_client import actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import tests_pb2
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import maintenance_utils
from grr_response_server import signed_binary_utils
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import discovery
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_objects
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
        action_registry.ACTION_STUB_BY_ID[self.args.action], next_state="End"
    )


class UpdateClientErrorAction(actions.ActionPlugin):
  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]

  def Run(self, args: rdf_client_action.ExecuteBinaryRequest):
    if not args.more_data:
      self.SendReply(
          rdf_client_action.ExecuteBinaryResponse(
              exit_status=1, stdout=b"\xff\xff\xff\xff", stderr=b"foobar"
          )
      )


class UpdateClientNoCrashAction(actions.ActionPlugin):
  in_rdfvalue = rdf_client_action.ExecuteBinaryRequest
  out_rdfvalues = [rdf_client_action.ExecuteBinaryResponse]

  def Run(self, args: rdf_client_action.ExecuteBinaryRequest):
    if not args.more_data:
      self.SendReply(
          rdf_client_action.ExecuteBinaryResponse(
              exit_status=0, stdout=b"foobar", stderr=b"\xff\xff\xff\xff"
          )
      )


class TestAdministrativeFlows(
    flow_test_lib.FlowTestsBaseclass, hunt_test_lib.StandardHuntTestMixin
):
  """Tests the administrative flows."""

  def setUp(self):
    super().setUp()

    config_overrider = test_lib.ConfigOverrider({
        # Make sure that Client.tempdir_roots are unique. Otherwise parallel
        # test execution may lead to races.
        "Client.tempdir_roots": [self.temp_dir],
        "Monitoring.alert_email": "grr-monitoring@localhost",
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

  def testDeleteGRRTempFiles(self):
    client_id = self.SetupClient(0)

    class FakeDeleteGRRTempFiles(actions.ActionPlugin):
      in_rdfvalue = rdf_paths.PathSpec
      out_rdfvalues = [rdf_client.LogMessage]

      def Run(self, args):
        self.SendReply(rdf_client.LogMessage(data="Deleted 10 files"))

    flow_id = flow_test_lib.StartAndRunFlow(
        administrative.DeleteGRRTempFiles,
        action_mocks.ActionMock.With({
            "DeleteGRRTempFiles": FakeDeleteGRRTempFiles,
        }),
        flow_args=administrative.DeleteGRRTempFilesArgs(
            pathspec=rdf_paths.PathSpec(path="tmp/foo/bar")
        ),
        creator=self.test_username,
        client_id=client_id,
    )
    logs = data_store.REL_DB.ReadFlowLogEntries(
        client_id, flow_id, offset=0, count=1024
    )
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].message, "Deleted 10 files")

  def CheckCrash(self, crash, expected_session_id, client_id):
    """Checks that ClientCrash object's fields are correctly filled in."""
    self.assertIsNotNone(crash)
    self.assertEqual(crash.client_id, rdf_client.ClientURN(client_id))
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
          dict(address=address, sender=sender, title=title, message=message)
      )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client = flow_test_lib.CrashClientMock(client_id)
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.FlowWithOneClientRequest,
          client,
          client_id=client_id,
          creator=self.test_username,
          check_flow_errors=False,
      )

    self.assertLen(self.email_messages, 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(
        email_message.get("address", ""),
        config.CONFIG["Monitoring.alert_email"],
    )

    # Make sure the flow state is included in the email message.
    self.assertIn("Host-0.example.com", email_message["message"])
    self.assertIn(
        "http://localhost:8000/v2/clients/C.1000000000000000",
        email_message["message"],
    )

    self.assertIn(client_id, email_message["title"])
    rel_flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(rel_flow_obj.flow_state, flows_pb2.Flow.FlowState.CRASHED)

    # Make sure client object is updated with the last crash.
    crash = data_store.REL_DB.ReadClientCrashInfo(client_id)
    self.CheckCrash(crash, client.flow_id, client_id)

  def _CheckAlertEmail(self, client_id, message, email_dict):
    # We expect the email to be sent.
    self.assertEqual(
        email_dict.get("address"), config.CONFIG["Monitoring.alert_email"]
    )

    self.assertIn(client_id, email_dict["title"])

    # Make sure the message is included in the email message.
    self.assertIn(message, email_dict["message"])

  def _RunSendStartupInfo(self, client_id):
    client_mock = action_mocks.ActionMock(admin.SendStartupInfo)
    flow_test_lib.StartAndRunFlow(
        ClientActionRunner,
        client_mock,
        client_id=client_id,
        flow_args=ClientActionRunnerArgs(
            action="SendStartupInfo",
        ),
        creator=self.test_username,
    )

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
        code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/test"
    )

    flow_test_lib.StartAndRunFlow(
        administrative.ExecutePythonHack,
        client_mock,
        client_id=client_id,
        flow_args=administrative.ExecutePythonHackArgs(
            hack_name="test",
        ),
        creator=self.test_username,
    )

    self.assertTrue(sys.test_code_ran_here)

  def testExecutePythonHackWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecutePython)
    sys.test_code_ran_here = 1234
    code = "import sys\nsys.test_code_ran_here = py_args['value']\n"

    client_id = self.SetupClient(0)

    maintenance_utils.UploadSignedConfigBlob(
        code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/test"
    )

    flow_test_lib.StartAndRunFlow(
        administrative.ExecutePythonHack,
        client_mock,
        client_id=client_id,
        flow_args=administrative.ExecutePythonHackArgs(
            hack_name="test",
            py_args=dict(value=5678),
        ),
        creator=self.test_username,
    )

    self.assertEqual(sys.test_code_ran_here, 5678)

  def testExecutePythonHackWithResult(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    code = """
magic_return_str = str(py_args["foobar"])
    """

    maintenance_utils.UploadSignedConfigBlob(
        content=code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/quux"
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        administrative.ExecutePythonHack,
        client_mock=action_mocks.ActionMock(standard.ExecutePython),
        client_id=client_id,
        flow_args=administrative.ExecutePythonHackArgs(
            hack_name="quux",
            py_args={"foobar": 42},
        ),
        creator=self.test_username,
    )

    flow_test_lib.FinishAllFlowsOnClient(client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], administrative.ExecutePythonHackResult)
    self.assertEqual(results[0].result_string, "42")

  def testExecutePythonHackWithFormatString(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    code = """
magic_return_str = "foo(%s)"
    """

    maintenance_utils.UploadSignedConfigBlob(
        content=code.encode("utf-8"), aff4_path="aff4:/config/python_hacks/quux"
    )

    flow_id = flow_test_lib.StartAndRunFlow(
        administrative.ExecutePythonHack,
        client_mock=action_mocks.ActionMock(standard.ExecutePython),
        client_id=client_id,
        flow_args=administrative.ExecutePythonHackArgs(
            hack_name="quux",
        ),
        creator=self.test_username,
    )

    flow_test_lib.FinishAllFlowsOnClient(client_id=client_id)

    results = flow_test_lib.GetFlowResults(client_id=client_id, flow_id=flow_id)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], administrative.ExecutePythonHackResult)
    self.assertEqual(results[0].result_string, "foo(%s)")

  def testExecuteBinariesWithArgs(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = b"I am a binary file"
    upload_path = (
        signed_binary_utils.GetAFF4ExecutablesRoot()
        .Add(config.CONFIG["Client.platform"])
        .Add("test.exe")
    )

    maintenance_utils.UploadSignedConfigBlob(code, aff4_path=upload_path)

    binary_urn = rdfvalue.RDFURN(upload_path)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn
    )

    # There should be only a single part to this binary.
    self.assertLen(list(blob_iterator), 1)

    # This flow has an acl, the user needs to be admin.
    acl_test_lib.CreateAdminUser(self.test_username)

    with mock.patch.object(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.StartAndRunFlow(
          administrative.LaunchBinary,
          client_mock,
          client_id=self.SetupClient(0),
          flow_args=administrative.LaunchBinaryArgs(
              binary=upload_path,
              command_line="--value 356",
          ),
          creator=self.test_username,
      )

      # Check that the executable file contains the code string.
      self.assertEqual(client_test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, client_test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(client_test_lib.Popen.running_args[1], "--value")
      self.assertEqual(client_test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertStartsWith(
          client_test_lib.Popen.running_args[0],
          config.CONFIG["Client.tempdir_roots"][0],
      )

  def testExecuteLargeBinaries(self):
    client_mock = action_mocks.ActionMock(standard.ExecuteBinaryCommand)

    code = b"I am a large binary file" * 100
    upload_path = (
        signed_binary_utils.GetAFF4ExecutablesRoot()
        .Add(config.CONFIG["Client.platform"])
        .Add("test.exe")
    )

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, limit=100
    )

    binary_urn = rdfvalue.RDFURN(upload_path)
    binary_size = signed_binary_utils.FetchSizeOfSignedBinary(binary_urn)
    blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        binary_urn
    )

    # Total size is 2400.
    self.assertEqual(binary_size, 2400)

    # There should be 24 parts to this binary.
    self.assertLen(list(blob_iterator), 24)

    # This flow has an acl, the user needs to be admin.
    acl_test_lib.CreateAdminUser(self.test_username)

    with mock.patch.object(subprocess, "Popen", client_test_lib.Popen):
      flow_test_lib.StartAndRunFlow(
          administrative.LaunchBinary,
          client_mock,
          client_id=self.SetupClient(0),
          flow_args=administrative.LaunchBinaryArgs(
              binary=upload_path,
              command_line="--value 356",
          ),
          creator=self.test_username,
      )

      # Check that the executable file contains the code string.
      self.assertEqual(client_test_lib.Popen.binary, code)

      # At this point, the actual binary should have been cleaned up by the
      # client action so it should not exist.
      self.assertRaises(IOError, open, client_test_lib.Popen.running_args[0])

      # Check the binary was run with the correct command line.
      self.assertEqual(client_test_lib.Popen.running_args[1], "--value")
      self.assertEqual(client_test_lib.Popen.running_args[2], "356")

      # Check the command was in the tmp file.
      self.assertStartsWith(
          client_test_lib.Popen.running_args[0],
          config.CONFIG["Client.tempdir_roots"][0],
      )

  def testExecuteBinaryWeirdOutput(self):
    binary_path = signed_binary_utils.GetAFF4ExecutablesRoot().Add("foo.exe")
    maintenance_utils.UploadSignedConfigBlob(
        b"foobarbaz", aff4_path=binary_path
    )

    client_id = self.SetupClient(0)

    def Run(self, args):
      del args  # Unused.

      stdout = "żółć %s gęślą {} jaźń # ⛷".encode("utf-8")
      stderr = b"\x00\xff\x00\xff\x00"

      response = rdf_client_action.ExecuteBinaryResponse(
          stdout=stdout, stderr=stderr, exit_status=0, time_used=0
      )
      self.SendReply(response)

    with mock.patch.object(standard.ExecuteBinaryCommand, "Run", new=Run):
      # Should not fail.
      flow_test_lib.StartAndRunFlow(
          administrative.LaunchBinary,
          action_mocks.ActionMock(standard.ExecuteBinaryCommand),
          client_id=client_id,
          creator=self.test_username,
          flow_args=administrative.LaunchBinaryArgs(
              binary=binary_path,
              command_line="--bar --baz",
          ),
      )

  def testUpdateClient(self):
    client_mock = action_mocks.ActionMock.With(
        {"UpdateAgent": UpdateClientNoCrashAction}
    )
    fake_installer = b"FakeGRRDebInstaller" * 20
    upload_path = (
        signed_binary_utils.GetAFF4ExecutablesRoot()
        .Add(config.CONFIG["Client.platform"])
        .Add("test.deb")
    )
    maintenance_utils.UploadSignedConfigBlob(
        fake_installer, aff4_path=upload_path, limit=100
    )

    blob_list, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        upload_path
    )
    self.assertLen(list(blob_list), 4)

    acl_test_lib.CreateAdminUser(self.test_username)

    client_id = self.SetupClient(0, system="")
    flow_id = flow_test_lib.StartAndRunFlow(
        administrative.UpdateClient,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=administrative.UpdateClientArgs(
            binary_path=os.path.join(
                config.CONFIG["Client.platform"], "test.deb"
            ),
        ),
    )
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(0, results[0].exit_status)
    self.assertEqual(results[0].stdout, b"foobar")

  def testUpdateClientFailure(self):
    client_mock = action_mocks.ActionMock.With(
        {"UpdateAgent": UpdateClientErrorAction}
    )
    fake_installer = b"FakeGRRDebInstaller" * 20
    upload_path = (
        signed_binary_utils.GetAFF4ExecutablesRoot()
        .Add(config.CONFIG["Client.platform"])
        .Add("test.deb")
    )
    maintenance_utils.UploadSignedConfigBlob(
        fake_installer, aff4_path=upload_path, limit=100
    )

    blob_list, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
        upload_path
    )
    self.assertLen(list(blob_list), 4)

    acl_test_lib.CreateAdminUser(self.test_username)

    client_id = self.SetupClient(0, system="")
    flow_id = flow_test_lib.StartAndRunFlow(
        administrative.UpdateClient,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
        flow_args=administrative.UpdateClientArgs(
            binary_path=os.path.join(
                config.CONFIG["Client.platform"], "test.deb"
            ),
        ),
        check_flow_errors=False,
    )

    rel_flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    self.assertEqual(rel_flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    results = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertEmpty(results)
    self.assertContainsInOrder(
        ["stdout: b'\\xff\\xff\\xff\\xff'", "stderr: b'foobar'"],
        rel_flow_obj.error_message,
    )

  def testOnlineNotificationEmail(self):
    """Tests that the mail is sent in the OnlineNotification flow."""
    client_id = self.SetupClient(0)
    self.email_messages = []

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message)
      )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      client_mock = action_mocks.ActionMock(admin.Echo)
      flow_test_lib.StartAndRunFlow(
          administrative.OnlineNotification,
          client_mock,
          flow_args=administrative.OnlineNotificationArgs(
              email="test@localhost"
          ),
          creator=self.test_username,
          client_id=client_id,
      )

    self.assertLen(self.email_messages, 1)
    email_message = self.email_messages[0]

    # We expect the email to be sent.
    self.assertEqual(email_message.get("address", ""), "test@localhost")
    self.assertEqual(
        email_message["title"],
        "GRR Client on Host-0.example.com became available.",
    )
    self.assertIn(
        "This notification was created by %s" % self.test_username,
        email_message.get("message", ""),
    )

  def testStartupHandler(self):
    client_id = self.SetupClient(0)

    self._RunSendStartupInfo(client_id)

    si = data_store.REL_DB.ReadClientStartupInfo(client_id)
    self.assertIsNotNone(si)
    self.assertEqual(si.client_info.client_name, config.CONFIG["Client.name"])
    self.assertEqual(
        si.client_info.client_description, config.CONFIG["Client.description"]
    )

    # Run it again - this should not update any record.
    self._RunSendStartupInfo(client_id)

    new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
    self.assertEqual(new_si, si)

    # Simulate a reboot.
    current_boot_time = psutil.boot_time()
    with mock.patch.object(
        psutil, "boot_time", lambda: current_boot_time + 600
    ):

      # Run it again - this should now update the boot time.
      self._RunSendStartupInfo(client_id)

      new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
      self.assertIsNotNone(new_si)
      self.assertNotEqual(new_si.boot_time, si.boot_time)

      # Now set a new client build time.
      build_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
      with test_lib.ConfigOverrider({"Client.build_time": build_time}):

        # Run it again - this should now update the client info.
        self._RunSendStartupInfo(client_id)

        new_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
        self.assertIsNotNone(new_si)
        self.assertNotEqual(new_si.client_info, si.client_info)

  def testStartupTriggersInterrogateForNewClient(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)

    startup = jobs_pb2.StartupInfo()
    startup.client_info.client_version = 4321

    request = objects_pb2.MessageHandlerRequest()
    request.client_id = client_id
    request.request.name = jobs_pb2.StartupInfo.__name__
    request.request.data = startup.SerializeToString()

    handler = administrative.ClientStartupHandler()
    handler.ProcessMessages([mig_objects.ToRDFMessageHandlerRequest(request)])

    interrogate_flow_objs = [
        flow_obj
        for flow_obj in data_store.REL_DB.ReadAllFlowObjects(client_id)
        if flow_obj.flow_class_name == discovery.Interrogate.__name__
    ]

    self.assertLen(interrogate_flow_objs, 1)

  def testStartupTriggersInterrogateWhenVersionChanges(self):
    with test_lib.ConfigOverrider({"Source.version_numeric": 3000}):
      client_id = self.SetupClient(0)
      self._RunSendStartupInfo(client_id)

    si = data_store.REL_DB.ReadClientStartupInfo(client_id)
    self.assertEqual(si.client_info.client_version, 3000)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    orig_count = len([
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ])

    with mock.patch.multiple(
        discovery.Interrogate, Start=mock.DEFAULT, End=mock.DEFAULT
    ):
      with test_lib.ConfigOverrider({"Source.version_numeric": 3001}):
        self._RunSendStartupInfo(client_id)

    si = data_store.REL_DB.ReadClientStartupInfo(client_id)
    self.assertEqual(si.client_info.client_version, 3001)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    interrogates = [
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ]
    self.assertLen(interrogates, orig_count + 1)
    self.assertEqual(flows[-1].flow_class_name, discovery.Interrogate.__name__)

  def testStartupTriggersInterrogateWhenExplicitlyRequestedByClient(self):
    client_id = self.SetupClient(0)
    self._RunSendStartupInfo(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    orig_count = len([
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ])

    # It's the second StartupInfo call and the version hasn't changed.
    # The only thing that's changed: a trigger file is created - and
    # that should trigger an interrogate.
    with tempfile.NamedTemporaryFile(delete=False) as temp_fd:
      with test_lib.ConfigOverrider(
          {"Client.interrogate_trigger_path": temp_fd.name}
      ):
        with mock.patch.multiple(
            discovery.Interrogate, Start=mock.DEFAULT, End=mock.DEFAULT
        ):
          self._RunSendStartupInfo(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    interrogates = [
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ]
    self.assertLen(interrogates, orig_count + 1)
    self.assertEqual(flows[-1].flow_class_name, discovery.Interrogate.__name__)

  def testStartupDoesNotTriggerInterrogateIfVersionStaysTheSame(self):
    with test_lib.ConfigOverrider({"Source.version_numeric": 3000}):
      client_id = self.SetupClient(0)
      self._RunSendStartupInfo(client_id)

      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id, include_child_flows=False
      )
      orig_count = len([
          f
          for f in flows
          if f.flow_class_name == discovery.Interrogate.__name__
      ])

      self._RunSendStartupInfo(client_id)

      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id, include_child_flows=False
      )
      same_ver_count = len([
          f
          for f in flows
          if f.flow_class_name == discovery.Interrogate.__name__
      ])
      self.assertEqual(same_ver_count, orig_count)

  def testStartupDoesNotTriggerInterrogateIfRecentInterrogateIsRunning(self):
    with test_lib.ConfigOverrider({"Source.version_numeric": 3000}):
      client_id = self.SetupClient(0)
      self._RunSendStartupInfo(client_id)

      data_store.REL_DB.WriteFlowObject(
          mig_flow_objects.ToProtoFlow(
              rdf_flow_objects.Flow(
                  flow_id=flow.RandomFlowId(),
                  client_id=client_id,
                  flow_class_name=discovery.Interrogate.__name__,
                  flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
              )
          )
      )

      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id, include_child_flows=False
      )
      orig_count = len([
          f
          for f in flows
          if f.flow_class_name == discovery.Interrogate.__name__
      ])

      self._RunSendStartupInfo(client_id)

      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id, include_child_flows=False
      )
      same_ver_count = len([
          f
          for f in flows
          if f.flow_class_name == discovery.Interrogate.__name__
      ])
      self.assertEqual(same_ver_count, orig_count)

  def testStartupTriggersInterrogateWhenPreviousInterrogateIsDone(self):
    with test_lib.ConfigOverrider({"Source.version_numeric": 3000}):
      client_id = self.SetupClient(0)
      self._RunSendStartupInfo(client_id)

    data_store.REL_DB.WriteFlowObject(
        mig_flow_objects.ToProtoFlow(
            rdf_flow_objects.Flow(
                flow_id=flow.RandomFlowId(),
                client_id=client_id,
                flow_class_name=discovery.Interrogate.__name__,
                flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
            )
        )
    )

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    orig_count = len([
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ])

    with mock.patch.multiple(
        discovery.Interrogate, Start=mock.DEFAULT, End=mock.DEFAULT
    ):
      with test_lib.ConfigOverrider({"Source.version_numeric": 3001}):
        self._RunSendStartupInfo(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id, include_child_flows=False
    )
    interrogates = [
        f for f in flows if f.flow_class_name == discovery.Interrogate.__name__
    ]
    self.assertLen(interrogates, orig_count + 1)

  def testClientAlertHandler(self):
    client_id = self.SetupClient(0)
    client_message = "Oh no!"
    email_dict = {}

    def SendEmail(address, sender, title, message, **_):
      email_dict.update(
          dict(address=address, sender=sender, title=title, message=message)
      )

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      flow_test_lib.MockClient(client_id, None)._PushHandlerMessage(
          rdf_flows.GrrMessage(
              source=client_id,
              session_id=rdfvalue.SessionID(flow_name="ClientAlert"),
              payload=rdf_protodict.DataBlob(string=client_message),
              request_id=0,
              auth_state="AUTHENTICATED",
              response_id=123,
          )
      )

    self._CheckAlertEmail(client_id, client_message, email_dict)

  def testForemanTimeIsResetOnClientStartupInfoWrite(self):
    client_id = self.SetupClient(0)
    reset_time = data_store.REL_DB.MinTimestamp()
    later_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600)

    data_store.REL_DB.WriteClientMetadata(client_id, last_foreman=later_time)
    self._RunSendStartupInfo(client_id)

    md = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertTrue(md.HasField("last_foreman_time"))
    self.assertEqual(md.last_foreman_time, int(reset_time))

    # Run it again - this should not update any record.
    data_store.REL_DB.WriteClientMetadata(client_id, last_foreman=later_time)
    self._RunSendStartupInfo(client_id)

    md = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertTrue(md.HasField("last_foreman_time"))
    self.assertEqual(md.last_foreman_time, int(later_time))


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
