#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for CSV output plugin."""

import csv
import StringIO

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.output_plugins import csv_plugin
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


class CSVOutputPluginTest(test_lib.FlowTestsBaseclass):
  """Tests CSV hunt output plugin."""

  def setUp(self):
    super(CSVOutputPluginTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.results_urn = self.client_id.Add("Results")
    self.base_urn = rdfvalue.RDFURN("aff4:/foo/bar")

  def ProcessResponses(self,
                       plugin_args=None,
                       responses=None,
                       process_responses_separately=False):
    plugin = csv_plugin.CSVOutputPlugin(source_urn=self.results_urn,
                                        output_base_urn=self.base_urn,
                                        args=plugin_args,
                                        token=self.token)
    plugin.Initialize()

    messages = []
    for response in responses:
      messages.append(rdf_flows.GrrMessage(source=self.client_id,
                                           payload=response))

    if process_responses_separately:
      for message in messages:
        plugin.ProcessResponses([message])
    else:
      plugin.ProcessResponses(messages)

    plugin.Flush()

    return plugin.OpenOutputStreams()

  def testCSVPluginWithValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(rdf_client.StatEntry(
          aff4path=self.client_id.Add("/fs/os/foo/bar").Add(str(i)),
          pathspec=rdf_paths.PathSpec(path="/foo/bar"),
          st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
          st_ino=1063090,
          st_dev=64512L,
          st_nlink=1 + i,
          st_uid=139592,
          st_gid=5000,
          st_size=0,
          st_atime=1336469177,
          st_mtime=1336129892,
          st_ctime=1336129892))

    streams = self.ProcessResponses(
        plugin_args=csv_plugin.CSVOutputPluginArgs(),
        responses=responses)
    self.assertEqual(streams.keys(), ["ExportedFile.csv"])
    self.assertEqual(streams["ExportedFile.csv"].urn,
                     rdfvalue.RDFURN("aff4:/foo/bar/ExportedFile.csv"))

    contents = StringIO.StringIO(streams["ExportedFile.csv"].Read(16384))
    parsed_output = list(csv.DictReader(contents))
    self.assertEqual(len(parsed_output), 10)
    for i in range(10):
      self.assertEqual(parsed_output[i]["metadata.client_urn"], self.client_id)
      self.assertEqual(parsed_output[i]["metadata.hostname"], "Host-0")
      self.assertEqual(parsed_output[i]["metadata.mac_address"],
                       "aabbccddee00\nbbccddeeff00")
      self.assertEqual(parsed_output[i]["metadata.source_urn"],
                       self.results_urn)

      self.assertEqual(parsed_output[i]["urn"],
                       self.client_id.Add("/fs/os/foo/bar").Add(str(i)))
      self.assertEqual(parsed_output[i]["st_mode"], "-rw-r-----")
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
    streams = self.ProcessResponses(
        plugin_args=csv_plugin.CSVOutputPluginArgs(),
        responses=[
            rdf_client.StatEntry(aff4path=self.client_id.Add("/fs/os/foo/bar"),
                                 pathspec=rdf_paths.PathSpec(path="/foo/bar")),
            rdf_client.Process(pid=42)
        ],
        process_responses_separately=True)

    self.assertEqual(
        sorted(streams.keys()),
        sorted(["ExportedFile.csv", "ExportedProcess.csv"]))
    self.assertEqual(streams["ExportedFile.csv"].urn,
                     rdfvalue.RDFURN("aff4:/foo/bar/ExportedFile.csv"))
    self.assertEqual(streams["ExportedProcess.csv"].urn,
                     rdfvalue.RDFURN("aff4:/foo/bar/ExportedProcess.csv"))

    contents = StringIO.StringIO(streams["ExportedFile.csv"].Read(16384))
    parsed_output = list(csv.DictReader(contents))

    self.assertEqual(len(parsed_output), 1)

    self.assertEqual(parsed_output[0]["metadata.client_urn"], self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"], "Host-0")
    self.assertEqual(parsed_output[0]["metadata.mac_address"],
                     "aabbccddee00\nbbccddeeff00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(parsed_output[0]["urn"],
                     self.client_id.Add("/fs/os/foo/bar"))

    contents = StringIO.StringIO(streams["ExportedProcess.csv"].Read(16384))
    parsed_output = list(csv.DictReader(contents))
    self.assertEqual(len(parsed_output), 1)

    self.assertEqual(parsed_output[0]["metadata.client_urn"], self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"], "Host-0")
    self.assertEqual(parsed_output[0]["metadata.mac_address"],
                     "aabbccddee00\nbbccddeeff00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(parsed_output[0]["pid"], "42")

  def testCSVPluginWritesUnicodeValuesCorrectly(self):
    streams = self.ProcessResponses(
        plugin_args=csv_plugin.CSVOutputPluginArgs(),
        responses=[
            rdf_client.StatEntry(aff4path=self.client_id.Add("/fs/os/中国新闻网新闻中"),
                                 pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中"))
        ],
        process_responses_separately=True)

    contents = StringIO.StringIO(streams["ExportedFile.csv"].Read(16384))
    parsed_output = list(csv.DictReader(contents))

    self.assertEqual(len(parsed_output), 1)
    self.assertEqual(parsed_output[0]["urn"],
                     self.client_id.Add("/fs/os/中国新闻网新闻中"))


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
