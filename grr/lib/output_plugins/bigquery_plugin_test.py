#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for BigQuery output plugin."""


import gzip
import json
import os

import mock

from grr.lib import aff4
from grr.lib import bigquery
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.output_plugins import bigquery_plugin
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths


class BigQueryOutputPluginTest(test_lib.FlowTestsBaseclass):
  """Tests BigQuery hunt output plugin."""

  def setUp(self):
    super(BigQueryOutputPluginTest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.results_urn = self.client_id.Add("Results")
    self.base_urn = rdfvalue.RDFURN("aff4:/foo/bar")

  def ProcessResponses(self,
                       plugin_args=None,
                       responses=None,
                       process_responses_separately=False):
    plugin = bigquery_plugin.BigQueryOutputPlugin(source_urn=self.results_urn,
                                                  output_base_urn=self.base_urn,
                                                  args=plugin_args,
                                                  token=self.token)

    plugin.Initialize()

    messages = []
    for response in responses:
      messages.append(rdf_flows.GrrMessage(source=self.client_id,
                                           payload=response))

    with test_lib.FakeTime(1445995873):
      with mock.patch.object(bigquery, "GetBigQueryClient") as mock_bigquery:
        if process_responses_separately:
          for message in messages:
            plugin.ProcessResponses([message])
        else:
          plugin.ProcessResponses(messages)

        plugin.Flush()

    return [x[0] for x in mock_bigquery.return_value.InsertData.call_args_list]

  def CompareSchemaToKnownGood(self, schema):
    expected_schema_data = json.load(open(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "bigquery", "ExportedFile.schema")))

    # It's easier to just compare the two dicts but even a change to the proto
    # description requires you to fix the json so we just compare field names
    # and types.
    schema_fields = [(x["name"], x["type"]) for x in schema]
    schema_metadata_fields = [(x[
        "name"], x["type"]) for x in schema[0]["fields"]]
    expected_fields = [(x["name"], x["type"]) for x in expected_schema_data]
    expected_metadata_fields = [(x[
        "name"], x["type"]) for x in expected_schema_data[0]["fields"]]
    self.assertEqual(schema_fields, expected_fields)
    self.assertEqual(schema_metadata_fields, expected_metadata_fields)

  def testBigQueryPluginWithValuesOfSameType(self):
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

    output = self.ProcessResponses(
        plugin_args=bigquery_plugin.BigQueryOutputPluginArgs(),
        responses=responses)

    self.assertEqual(len(output), 1)
    _, stream, schema, job_id = output[0]

    self.assertEqual(job_id,
                     "C-1000000000000000_Results_ExportedFile_1445995873")

    self.CompareSchemaToKnownGood(schema)

    actual_fd = gzip.GzipFile(
        None, "r", bigquery_plugin.BigQueryOutputPlugin.GZIP_COMPRESSION_LEVEL,
        stream)

    # Compare to our stored data.
    expected_fd = open(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "bigquery", "ExportedFile.json"))

    # Bigquery expects a newline separarted list of JSON dicts, but this isn't
    # valid JSON so we can't just load the whole thing and compare.
    counter = 0
    for actual, expected in zip(actual_fd, expected_fd):
      self.assertEqual(json.loads(actual), json.loads(expected))
      counter += 1

    self.assertEqual(counter, 10)

  def _parseOutput(self, name, stream):
    content_fd = gzip.GzipFile(None, "r", 9, stream)
    counter = 0

    for item in content_fd:
      counter += 1
      row = json.loads(item)

      if name == "ExportedFile":
        self.assertEqual(row["metadata"]["client_urn"], self.client_id)
        self.assertEqual(row["metadata"]["hostname"], "Host-0")
        self.assertEqual(row["metadata"]["mac_address"],
                         "aabbccddee00\nbbccddeeff00")
        self.assertEqual(row["metadata"]["source_urn"], self.results_urn)
        self.assertEqual(row["urn"], self.client_id.Add("/fs/os/中国新闻网新闻中"))
      else:
        self.assertEqual(row["metadata"]["client_urn"], self.client_id)
        self.assertEqual(row["metadata"]["hostname"], "Host-0")
        self.assertEqual(row["metadata"]["mac_address"],
                         "aabbccddee00\nbbccddeeff00")
        self.assertEqual(row["metadata"]["source_urn"], self.results_urn)
        self.assertEqual(row["pid"], "42")

    self.assertEqual(counter, 1)

  def testBigQueryPluginWithValuesOfMultipleTypes(self):
    output = self.ProcessResponses(
        plugin_args=bigquery_plugin.BigQueryOutputPluginArgs(),
        responses=[
            rdf_client.StatEntry(aff4path=self.client_id.Add("/fs/os/中国新闻网新闻中"),
                                 pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中")),
            rdf_client.Process(pid=42)
        ],
        process_responses_separately=True)

    # Should have two separate output streams for the two types
    self.assertEqual(len(output), 2)

    for name, stream, _, job_id in output:
      self.assertTrue(job_id in [
          "C-1000000000000000_Results_ExportedFile_1445995873",
          "C-1000000000000000_Results_ExportedProcess_1445995873"
      ])
      self._parseOutput(name, stream)

  def testBigQueryPluginWithEarlyFlush(self):
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

    # Force an early flush. This max file size value has been chosen to force a
    # flush at least once, but not for all 10 records.
    with test_lib.ConfigOverrider({"BigQuery.max_file_post_size": 700}):
      output = self.ProcessResponses(
          plugin_args=bigquery_plugin.BigQueryOutputPluginArgs(),
          responses=responses)

    self.assertEqual(len(output), 2)
    # Check that the output is still consistent
    actual_fds = []

    for _, stream, _, _ in output:
      actual_fds.append(gzip.GzipFile(None, "r", 9, stream))

    # Compare to our stored data.
    expected_fd = open(os.path.join(config_lib.CONFIG[
        "Test.data_dir"], "bigquery", "ExportedFile.json"))

    # Check that the same entries we expect are spread across the two files.
    counter = 0
    for actual_fd in actual_fds:
      for actual, expected in zip(actual_fd, expected_fd):
        self.assertEqual(json.loads(actual), json.loads(expected))
        counter += 1

    self.assertEqual(counter, 10)

  def testBigQueryPluginFallbackToAFF4(self):
    plugin_args = bigquery_plugin.BigQueryOutputPluginArgs()
    responses = [
        rdf_client.StatEntry(aff4path=self.client_id.Add("/fs/os/中国新闻网新闻中"),
                             pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中")),
        rdf_client.Process(pid=42), rdf_client.Process(pid=43),
        rdf_client.SoftwarePackage(name="test.deb")
    ]

    plugin = bigquery_plugin.BigQueryOutputPlugin(source_urn=self.results_urn,
                                                  output_base_urn=self.base_urn,
                                                  args=plugin_args,
                                                  token=self.token)

    plugin.Initialize()

    messages = []
    for response in responses:
      messages.append(rdf_flows.GrrMessage(source=self.client_id,
                                           payload=response))

    with test_lib.FakeTime(1445995873):
      with mock.patch.object(bigquery, "GetBigQueryClient") as mock_bigquery:
        mock_bigquery.return_value.configure_mock(**{
            "InsertData.side_effect": bigquery.BigQueryJobUploadError()
        })
        with test_lib.ConfigOverrider({"BigQuery.max_upload_failures": 2}):
          for message in messages:
            plugin.ProcessResponses([message])
          plugin.Flush()

          # We have 3 output types but a limit of 2 upload failures, so we
          # shouldn't try the third one.
          self.assertEqual(mock_bigquery.return_value.InsertData.call_count, 2)

    # We should have written a data file and a schema file for each type.
    for output_name in ["ExportedFile", "ExportedProcess",
                        "AutoExportedSoftwarePackage"]:
      schema_fd = aff4.FACTORY.Open(
          self.base_urn.Add("C-1000000000000000_Results_%s_1445995873.schema" %
                            output_name),
          token=self.token)
      data_fd = aff4.FACTORY.Open(
          self.base_urn.Add("C-1000000000000000_Results_%s_1445995873.data" %
                            output_name),
          token=self.token)
      actual_fd = gzip.GzipFile(None, "r", 9, data_fd)

      if output_name == "ExportedFile":
        self.CompareSchemaToKnownGood(json.load(schema_fd))
        self.assertEqual(
            json.load(actual_fd)["urn"], self.client_id.Add("/fs/os/中国新闻网新闻中"))
      elif output_name == "ExportedProcess":
        self.assertEqual(json.load(schema_fd)[1]["name"], "pid")
        expected_pids = ["42", "43"]
        for i, line in enumerate(actual_fd):
          self.assertEqual(json.loads(line)["pid"], expected_pids[i])
      else:
        self.assertEqual(json.load(schema_fd)[1]["name"], "name")
        self.assertEqual(json.load(actual_fd)["name"], "test.deb")

    # Process the same messages to make sure we're re-using the filehandles.
    with test_lib.FakeTime(1445995878):
      with mock.patch.object(bigquery, "GetBigQueryClient") as mock_bigquery:
        mock_bigquery.return_value.configure_mock(**{
            "InsertData.side_effect": bigquery.BigQueryJobUploadError()
        })
        with test_lib.ConfigOverrider({"BigQuery.max_upload_failures": 2}):
          for message in messages:
            plugin.ProcessResponses([message])
          plugin.Flush()

          # We shouldn't call insertdata at all because we have passed max
          # failures already
          self.assertEqual(mock_bigquery.return_value.InsertData.call_count, 0)

    expected_line_counts = {"ExportedFile": 2,
                            "ExportedProcess": 4,
                            "AutoExportedSoftwarePackage": 2}
    for output_name in ["ExportedFile", "ExportedProcess",
                        "AutoExportedSoftwarePackage"]:
      data_fd = aff4.FACTORY.Open(
          self.base_urn.Add("C-1000000000000000_Results_%s_1445995873.data" %
                            output_name),
          token=self.token)
      actual_fd = gzip.GzipFile(None, "r", 9, data_fd)
      self.assertEqual(
          sum(1 for line in actual_fd), expected_line_counts[output_name])


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
