#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests for BigQuery output plugin."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import json
import os


from builtins import range  # pylint: disable=redefined-builtin
from builtins import zip  # pylint: disable=redefined-builtin
import mock

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import bigquery
from grr_response_server.output_plugins import bigquery_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class BigQueryOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests BigQuery hunt output plugin."""

  def setUp(self):
    super(BigQueryOutputPluginTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.results_urn = self.client_id.Add("Results")

  def ProcessResponses(self,
                       plugin_args=None,
                       responses=None,
                       process_responses_separately=False):
    plugin_cls = bigquery_plugin.BigQueryOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=self.results_urn, args=plugin_args, token=self.token)

    messages = []
    for response in responses:
      messages.append(
          rdf_flows.GrrMessage(source=self.client_id, payload=response))

    with test_lib.FakeTime(1445995873):
      with mock.patch.object(bigquery, "GetBigQueryClient") as mock_bigquery:
        if process_responses_separately:
          for message in messages:
            plugin.ProcessResponses(plugin_state, [message])
        else:
          plugin.ProcessResponses(plugin_state, messages)

        plugin.Flush(plugin_state)
        plugin.UpdateState(plugin_state)

    return [x[0] for x in mock_bigquery.return_value.InsertData.call_args_list]

  def CompareSchemaToKnownGood(self, schema):
    expected_schema_data = json.load(
        open(
            os.path.join(config.CONFIG["Test.data_dir"], "bigquery",
                         "ExportedFile.schema"), "rb"))

    # It's easier to just compare the two dicts but even a change to the proto
    # description requires you to fix the json so we just compare field names
    # and types.
    schema_fields = [(x["name"], x["type"]) for x in schema]
    schema_metadata_fields = [
        (x["name"], x["type"]) for x in schema[0]["fields"]
    ]
    expected_fields = [(x["name"], x["type"]) for x in expected_schema_data]
    expected_metadata_fields = [
        (x["name"], x["type"]) for x in expected_schema_data[0]["fields"]
    ]
    self.assertEqual(schema_fields, expected_fields)
    self.assertEqual(schema_metadata_fields, expected_metadata_fields)

  def testBigQueryPluginWithValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="/foo/bar/%d" % i, pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
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

    self.assertLen(output, 1)
    _, stream, schema, job_id = output[0]

    self.assertEqual(job_id,
                     "C-1000000000000000_Results_ExportedFile_1445995873")

    self.CompareSchemaToKnownGood(schema)

    actual_fd = gzip.GzipFile(
        None, "r", bigquery_plugin.BigQueryOutputPlugin.GZIP_COMPRESSION_LEVEL,
        stream)

    # Compare to our stored data.
    expected_fd = open(
        os.path.join(config.CONFIG["Test.data_dir"], "bigquery",
                     "ExportedFile.json"), "rb")

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
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中", pathtype="OS")),
            rdf_client.Process(pid=42)
        ],
        process_responses_separately=True)

    # Should have two separate output streams for the two types
    self.assertLen(output, 2)

    for name, stream, _, job_id in output:
      self.assertIn(job_id, [
          "C-1000000000000000_Results_ExportedFile_1445995873",
          "C-1000000000000000_Results_ExportedProcess_1445995873"
      ])
      self._parseOutput(name, stream)

  def testBigQueryPluginWithEarlyFlush(self):
    responses = []
    for i in range(10):
      responses.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="/foo/bar/%d" % i, pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1336469177,
              st_mtime=1336129892,
              st_ctime=1336129892))

    sizes = [37, 687, 722, 755, 788, 821, 684, 719, 752, 785]

    def GetSize(unused_path):
      return sizes.pop(0)

    # Force an early flush. Gzip is non deterministic since our
    # metadata is a dict with unpredictable order so we make up the file sizes
    # such that there is one flush during processing.
    with test_lib.ConfigOverrider({"BigQuery.max_file_post_size": 800}):
      with utils.Stubber(os.path, "getsize", GetSize):
        output = self.ProcessResponses(
            plugin_args=bigquery_plugin.BigQueryOutputPluginArgs(),
            responses=responses)

    self.assertLen(output, 2)
    # Check that the output is still consistent
    actual_fds = []

    for _, stream, _, _ in output:
      actual_fds.append(gzip.GzipFile(None, "r", 9, stream))

    # Compare to our stored data.
    # TODO(user): there needs to be a better way to generate these files on
    # change than breaking into the debugger.
    expected_fd = open(
        os.path.join(config.CONFIG["Test.data_dir"], "bigquery",
                     "ExportedFile.json"), "rb")

    # Check that the same entries we expect are spread across the two files.
    counter = 0
    for actual_fd in actual_fds:
      for actual, expected in zip(actual_fd, expected_fd):
        self.assertEqual(json.loads(actual), json.loads(expected))
        counter += 1

    self.assertEqual(counter, 10)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
