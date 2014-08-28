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
from grr.lib import flow
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import tests_pb2


class ClientActionRunnerArgs(rdfvalue.RDFProtoStruct):
  protobuf = tests_pb2.ClientActionRunnerArgs


class ClientActionRunner(flow.GRRFlow):
  """Just call the specified client action directly.
  """
  args_type = ClientActionRunnerArgs
  action_args = {}

  @flow.StateHandler(next_state="End")
  def Start(self):
    self.CallClient(self.args.action, next_state="End", **self.action_args)


class TestAdministrativeFlows(test_lib.FlowTestsBaseclass):
  """Tests the administrative flows."""

  def setUp(self):
    super(TestAdministrativeFlows, self).setUp()

    test_tmp = os.environ.get("TEST_TMPDIR")
    if test_tmp:
      config_lib.CONFIG.Set("Client.tempdir", test_tmp)

  def testUpdateConfig(self):
    """Ensure we can retrieve and update the config."""

    # Only mock the pieces we care about.
    client_mock = action_mocks.ActionMock("GetConfiguration",
                                          "UpdateConfiguration")

    loc = "http://www.example.com"
    new_config = rdfvalue.Dict(
        {"Client.control_urls": [loc],
         "Client.foreman_check_frequency": 3600,
         "Client.poll_min": 1})

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
    self.assertEqual(config_dat["Client.control_urls"], [loc])
    self.assertEqual(config_dat["Client.poll_min"], 1)

  def CheckCrash(self, crash, expected_session_id):
    """Checks that ClientCrash object's fields are correctly filled in."""
    self.assertTrue(crash is not None)
    self.assertEqual(crash.client_id, self.client_id)
    self.assertEqual(crash.session_id, expected_session_id)
    self.assertEqual(crash.client_info.client_name, "GRR Monitor")
    self.assertEqual(crash.crash_type, "aff4:/flows/W:CrashHandler")
    self.assertEqual(crash.crash_message,
                     "Client killed during transaction")

  def testClientKilled(self):
    """Test that client killed messages are handled correctly."""
    self.email_message = {}

    def SendEmail(address, sender, title, message, **_):
      self.email_message.update(dict(address=address, sender=sender,
                                     title=title, message=message))

    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      client = test_lib.CrashClientMock(self.client_id, self.token)
      for _ in test_lib.TestFlowHelper(
          "FlowWithOneClientRequest", client, client_id=self.client_id,
          token=self.token, check_flow_errors=False):
        pass

      # We expect the email to be sent.
      self.assertEqual(self.email_message.get("address", ""),
                       config_lib.CONFIG["Monitoring.alert_email"])
      self.assertTrue(str(self.client_id) in self.email_message["title"])

      # Make sure the flow state is included in the email message.
      for s in ["Flow name", "FlowWithOneClientRequest", "current_state"]:
        self.assertTrue(s in self.email_message["message"])

      flow_obj = aff4.FACTORY.Open(client.flow_id, age=aff4.ALL_TIMES,
                                   token=self.token)
      self.assertEqual(flow_obj.state.context.state, rdfvalue.Flow.State.ERROR)

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

  def testNannyMessage(self):
    nanny_message = "Oh no!"
    self.email_message = {}

    def SendEmail(address, sender, title, message, **_):
      self.email_message.update(dict(address=address, sender=sender,
                                     title=title, message=message))

    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      msg = rdfvalue.GrrMessage(
          session_id=rdfvalue.SessionID("aff4:/flows/W:NannyMessage"),
          args=rdfvalue.DataBlob(string=nanny_message).SerializeToString(),
          source=self.client_id,
          auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

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
      self.assertEqual(crash.crash_type, "aff4:/flows/W:NannyMessage")
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

    class Popen(object):
      """A mock object for subprocess.Popen."""

      def __init__(self, run, stdout, stderr, stdin):
        Popen.running_args = run
        Popen.stdout = stdout
        Popen.stderr = stderr
        Popen.stdin = stdin
        Popen.returncode = 0

        # Store the content of the executable file.
        Popen.binary = open(run[0]).read()

      def communicate(self):  # pylint: disable=g-bad-name
        return "stdout here", "stderr here"

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create("aff4:/users/%s" % self.token.username,
                               mode="rw", aff4_type="GRRUser", token=self.token)
    user.SetLabels("admin", owner="GRR")
    user.Close()

    with utils.Stubber(subprocess, "Popen", Popen):
      for _ in test_lib.TestFlowHelper(
          "LaunchBinary", client_mock, client_id=self.client_id,
          binary=upload_path, command_line="--value 356", token=self.token):
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

  def testExecuteLargeBinaries(self):
    client_mock = action_mocks.ActionMock("ExecuteBinaryCommand")

    code = "I am a large binary file" * 100
    upload_path = config_lib.CONFIG["Executables.aff4_path"].Add("test.exe")

    maintenance_utils.UploadSignedConfigBlob(
        code, aff4_path=upload_path, limit=100, token=self.token)

    # Ensure the aff4 collection has many items.
    fd = aff4.FACTORY.Open(upload_path, token=self.token)

    # There should be 24 parts to this binary.
    self.assertEqual(len(fd.collection), 24)

    # Total size is 2400.
    self.assertEqual(len(fd), 2400)

    class Popen(object):
      """A mock object for subprocess.Popen."""

      def __init__(self, run, stdout, stderr, stdin):
        Popen.running_args = run
        Popen.stdout = stdout
        Popen.stderr = stderr
        Popen.stdin = stdin
        Popen.returncode = 0

        # Store the content of the executable file.
        Popen.binary = open(run[0]).read()

      def communicate(self):  # pylint: disable=g-bad-name
        return "stdout here", "stderr here"

    # This flow has an acl, the user needs to be admin.
    user = aff4.FACTORY.Create("aff4:/users/%s" % self.token.username,
                               mode="rw", aff4_type="GRRUser", token=self.token)
    user.SetLabels("admin", owner="GRR")
    user.Close()

    with utils.Stubber(subprocess, "Popen", Popen):
      for _ in test_lib.TestFlowHelper(
          "LaunchBinary", client_mock, client_id=self.client_id,
          binary=upload_path, command_line="--value 356", token=self.token):
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
        """Fake get client stats method."""
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


class TestApplyLabelsToClientsFlow(test_lib.FlowTestsBaseclass):
  """Tests for ApplyLabelsToClientsFlow."""

  def GetClientLabels(self, client_id):
    fd = aff4.FACTORY.Open(client_id, aff4_type="VFSGRRClient",
                           token=self.token)
    return list(fd.Get(fd.Schema.LABELS,
                       rdfvalue.AFF4ObjectLabelsList()).labels)

  def testAppliesSingleLabelToSingleClient(self):
    client_id = self.SetupClients(1)[0]

    self.assertFalse(self.GetClientLabels(client_id))

    with test_lib.FakeTime(42):
      flow.GRRFlow.StartFlow(flow_name="ApplyLabelsToClientsFlow",
                             clients=[client_id],
                             labels=["foo"],
                             token=self.token)

    self.assertListEqual(
        self.GetClientLabels(client_id),
        [rdfvalue.AFF4ObjectLabel(
            name="foo", owner="test",
            timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))])

  def testAppliesSingleLabelToMultipleClients(self):
    client_ids = self.SetupClients(3)

    for client_id in client_ids:
      self.assertFalse(self.GetClientLabels(client_id))

    with test_lib.FakeTime(42):
      flow.GRRFlow.StartFlow(flow_name="ApplyLabelsToClientsFlow",
                             clients=client_ids,
                             labels=["foo"],
                             token=self.token)

    for client_id in client_ids:
      self.assertListEqual(
          self.GetClientLabels(client_id),
          [rdfvalue.AFF4ObjectLabel(
              name="foo", owner="test",
              timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))])

  def testAppliesMultipleLabelsToSingleClient(self):
    client_id = self.SetupClients(1)[0]

    self.assertFalse(self.GetClientLabels(client_id))

    with test_lib.FakeTime(42):
      flow.GRRFlow.StartFlow(flow_name="ApplyLabelsToClientsFlow",
                             clients=[client_id],
                             labels=["drei", "ein", "zwei"],
                             token=self.token)

    self.assertListEqual(
        sorted(self.GetClientLabels(client_id),
               key=lambda label: label.name),
        [rdfvalue.AFF4ObjectLabel(
            name="drei", owner="test",
            timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42)),
         rdfvalue.AFF4ObjectLabel(
             name="ein", owner="test",
             timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42)),
         rdfvalue.AFF4ObjectLabel(
             name="zwei", owner="test",
             timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))])

  def testAppliesMultipleLabelsToMultipleClients(self):
    client_ids = self.SetupClients(3)

    for client_id in client_ids:
      self.assertFalse(self.GetClientLabels(client_id))

    with test_lib.FakeTime(42):
      flow.GRRFlow.StartFlow(flow_name="ApplyLabelsToClientsFlow",
                             clients=client_ids,
                             labels=["drei", "ein", "zwei"],
                             token=self.token)

    for client_id in client_ids:
      self.assertListEqual(
          sorted(self.GetClientLabels(client_id),
                 key=lambda label: label.name),
          [rdfvalue.AFF4ObjectLabel(
              name="drei", owner="test",
              timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42)),
           rdfvalue.AFF4ObjectLabel(
               name="ein", owner="test",
               timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42)),
           rdfvalue.AFF4ObjectLabel(
               name="zwei", owner="test",
               timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42))])

  def testAuditEntryIsCreatedForEveryClient(self):
    client_ids = self.SetupClients(3)

    flow.GRRFlow.StartFlow(flow_name="ApplyLabelsToClientsFlow",
                           clients=client_ids,
                           labels=["drei", "ein", "zwei"],
                           token=self.token)
    mock_worker = test_lib.MockWorker(token=self.token)
    mock_worker.Simulate()

    fd = aff4.FACTORY.Open("aff4:/audit/log", token=self.token)

    for client_id in client_ids:
      found_event = None
      for event in fd:
        if (event.action == rdfvalue.AuditEvent.Action.CLIENT_ADD_LABEL and
            event.client == rdfvalue.ClientURN(client_id)):
          found_event = event
          break

      self.assertFalse(found_event is None)

      self.assertEqual(found_event.flow_name, "ApplyLabelsToClientsFlow")
      self.assertEqual(found_event.user, self.token.username)
      self.assertEqual(found_event.description, "test.drei,test.ein,test.zwei")
