#!/usr/bin/env python
"""Tests for hunts output plugins."""



import csv
import StringIO
import sys


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils


class EmailPluginTest(test_lib.FlowTestsBaseclass):
  """Tests email hunt output plugins."""

  def RunHunt(self, plugin_name, plugin_args):
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[rdfvalue.OutputPlugin(
            plugin_name=plugin_name,
            plugin_args=plugin_args)],
        client_rate=0, token=self.token) as hunt:
      hunt.Run()

      hunt.StartClients(hunt.session_id, self.client_ids)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Stop the hunt now.
      hunt.GetRunner().Stop()

    # Run cron flow that executes actual output plugins
    for _ in test_lib.TestFlowHelper("ProcessHuntResultsCronFlow",
                                     token=self.token):
      pass

    return hunt.urn

  def setUp(self):
    super(EmailPluginTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(40)

  def testEmailPlugin(self):
    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      self.email_messages = []

      email_alerts.SendEmail = SendEmail
      email_address = "notify@%s" % config_lib.CONFIG["Logging.domain"]

      hunt_urn = self.RunHunt("EmailPlugin", rdfvalue.EmailPluginArgs(
          email=email_address, email_limit=10))

      hunt_obj = aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES,
                                   mode="rw", token=self.token)

      self.client_ids = self.SetupClients(40)
      hunt_obj.StartClients(hunt_obj.session_id, self.client_ids)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Run cron flow that executes actual output plugins
      for _ in test_lib.TestFlowHelper("ProcessHuntResultsCronFlow",
                                       token=self.token):
        pass

      # Stop the hunt now.
      hunt_obj.GetRunner().Stop()

      hunt_obj = aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES,
                                   token=self.token)

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 40)
      self.assertEqual(finished, 40)
      self.assertEqual(errors, 20)

      collection = aff4.FACTORY.Open(hunt_urn.Add("Results"),
                                     mode="r", token=self.token)

      self.assertEqual(len(collection), 20)

      # Due to the limit there should only by 10 messages.
      self.assertEqual(len(self.email_messages), 10)

      for msg in self.email_messages:
        self.assertEqual(msg["address"], email_address)
        self.assertTrue(
            "%s got a new result" % hunt_obj.session_id.Add("Results")
            in msg["title"])
        self.assertTrue("fs/os/tmp/evil.txt" in msg["message"])

      self.assertTrue("sending of emails will be disabled now"
                      in self.email_messages[-1]["message"])


class CSVOutputPluginTest(test_lib.FlowTestsBaseclass):
  """Tests CSV hunt output plugins."""

  def RunHunt(self, plugin_args=None, responses=None,
              process_responses_separately=False):
    if responses is None:
      responses = []

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(pathspec=rdfvalue.PathSpec(
            path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        regex_rules=[
            rdfvalue.ForemanAttributeRegex(attribute_name="GRR client",
                                           attribute_regex="GRR"),
            ],
        client_rate=0, token=self.token) as hunt:

      hunt_urn = hunt.urn
      plugin_def = rdfvalue.OutputPlugin(
          plugin_name="CSVOutputPlugin",
          plugin_args=plugin_args)
      plugin = plugin_def.GetPluginForHunt(hunt)

    # We don't want to test the whole output plugins subsystem as it's
    # tested in its own tests. We only want to test logic specific to
    # ColumnIOHuntOutputPlugin.
    messages = []
    for response in responses:
      messages.append(rdfvalue.GrrMessage(source=self.client_id,
                                          payload=response))

    if process_responses_separately:
      for message in messages:
        plugin.ProcessResponses([message])
    else:
      plugin.ProcessResponses(messages)

    plugin.Flush()

    return (hunt_urn, plugin)

  def setUp(self):
    super(CSVOutputPluginTest, self).setUp()

    self.client_id = self.SetupClients(1)[0]

  def testCSVPluginWithValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(rdfvalue.StatEntry(
          aff4path=self.client_id.Add("/fs/os/foo/bar").Add(str(i)),
          pathspec=rdfvalue.PathSpec(path="/foo/bar"),
          st_mode=33184,
          st_ino=1063090,
          st_dev=64512L,
          st_nlink=1 + i,
          st_uid=139592,
          st_gid=5000,
          st_size=0,
          st_atime=1336469177,
          st_mtime=1336129892,
          st_ctime=1336129892))

    hunt_urn, _ = self.RunHunt(plugin_args=rdfvalue.CSVOutputPluginArgs(
        output_dir=rdfvalue.RDFURN("aff4:/tmp/csv")), responses=responses)

    plugin_output_files = list(aff4.FACTORY.Open(
        "aff4:/tmp/csv", token=self.token).ListChildren())
    self.assertListEqual(plugin_output_files,
                         [rdfvalue.RDFURN("aff4:/tmp/csv/ExportedFile.csv")])

    output_file = aff4.FACTORY.Open(
        plugin_output_files[0], aff4_type="AFF4Image", token=self.token)
    contents = output_file.Read(sys.maxint)

    parsed_output = list(csv.DictReader(StringIO.StringIO(contents)))
    self.assertEqual(len(parsed_output), 10)
    for i in range(10):
      self.assertEqual(parsed_output[i]["metadata.client_urn"], self.client_id)
      self.assertEqual(parsed_output[i]["metadata.hostname"], "Host-0")
      self.assertEqual(parsed_output[i]["metadata.mac_address"], "aabbccddee00")
      self.assertEqual(parsed_output[i]["metadata.source_urn"],
                       hunt_urn.Add("Results"))

      self.assertEqual(parsed_output[i]["urn"],
                       self.client_id.Add("/fs/os/foo/bar").Add(str(i)))
      self.assertEqual(parsed_output[i]["st_mode"], "33184")
      self.assertEqual(parsed_output[i]["st_ino"], "1063090")
      self.assertEqual(parsed_output[i]["st_dev"], "64512")
      self.assertEqual(parsed_output[i]["st_nlink"], str(1 + i))
      self.assertEqual(parsed_output[i]["st_uid"], "139592")
      self.assertEqual(parsed_output[i]["st_gid"], "5000")
      self.assertEqual(parsed_output[i]["st_size"], "0")
      self.assertEqual(parsed_output[i]["st_atime"], "2012-05-08 09:26:17")
      self.assertEqual(parsed_output[i]["st_mtime"], "2012-05-04 11:11:32")
      self.assertEqual(parsed_output[i]["st_ctime"], "2012-05-04 11:11:32")
      self.assertEqual(parsed_output[i]["st_blksize"], "0")
      self.assertEqual(parsed_output[i]["st_rdev"], "0")
      self.assertEqual(parsed_output[i]["symlink"], "")

  def testCSVPluginWithValuesOfMultipleTypes(self):
    hunt_urn, _ = self.RunHunt(
        plugin_args=rdfvalue.CSVOutputPluginArgs(
            output_dir=rdfvalue.RDFURN("aff4:/tmp/csv")),
        responses=[
            rdfvalue.StatEntry(
                aff4path=self.client_id.Add("/fs/os/foo/bar"),
                pathspec=rdfvalue.PathSpec(path="/foo/bar")),
            rdfvalue.Process(pid=42)],
        process_responses_separately=True)

    plugin_output_files = sorted(list(aff4.FACTORY.Open(
        "aff4:/tmp/csv", token=self.token).ListChildren()))
    self.assertListEqual(plugin_output_files,
                         [rdfvalue.RDFURN("aff4:/tmp/csv/ExportedFile.csv"),
                          rdfvalue.RDFURN("aff4:/tmp/csv/ExportedProcess.csv")])

    output_file = aff4.FACTORY.Open(
        plugin_output_files[0], aff4_type="AFF4Image", token=self.token)
    parsed_output = list(csv.DictReader(
        StringIO.StringIO(output_file.Read(sys.maxint))))
    self.assertEqual(len(parsed_output), 1)

    self.assertEqual(parsed_output[0]["metadata.client_urn"], self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"], "Host-0")
    self.assertEqual(parsed_output[0]["metadata.mac_address"], "aabbccddee00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"],
                     hunt_urn.Add("Results"))
    self.assertEqual(parsed_output[0]["urn"],
                     self.client_id.Add("/fs/os/foo/bar"))

    output_file = aff4.FACTORY.Open(
        plugin_output_files[1], aff4_type="AFF4Image", token=self.token)
    parsed_output = list(csv.DictReader(
        StringIO.StringIO(output_file.Read(sys.maxint))))
    self.assertEqual(len(parsed_output), 1)

    self.assertEqual(parsed_output[0]["metadata.client_urn"], self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"], "Host-0")
    self.assertEqual(parsed_output[0]["metadata.mac_address"], "aabbccddee00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"],
                     hunt_urn.Add("Results"))
    self.assertEqual(parsed_output[0]["pid"], "42")

  def testCSVPluginGeneratesTemporaryNameIfOutputDirIsNotSpecified(self):
    _, plugin = self.RunHunt(responses=[rdfvalue.Process(pid=42)])

    self.assertTrue("ExportedProcess" in plugin.state.files_by_type)
    output_file = aff4.FACTORY.Open(
        plugin.state.files_by_type["ExportedProcess"].urn,
        aff4_type="AFF4Image", token=self.token)
    parsed_output = list(csv.DictReader(
        StringIO.StringIO(output_file.Read(sys.maxint))))
    self.assertEqual(len(parsed_output), 1)


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
