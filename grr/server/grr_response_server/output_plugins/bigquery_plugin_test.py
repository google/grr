#!/usr/bin/env python
"""Tests for BigQuery output plugin."""

import base64
import gzip
import io
import json
import os
from unittest import mock

from absl import app

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import bigquery
from grr_response_server.output_plugins import bigquery_plugin
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class BigQueryOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests BigQuery hunt output plugin."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.source_id = rdf_client.ClientURN(
        self.client_id).Add("Results").RelativeName("aff4:/")

  def ProcessResponses(self,
                       plugin_args=None,
                       responses=None,
                       process_responses_separately=False):
    plugin_cls = bigquery_plugin.BigQueryOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=self.source_id, args=plugin_args)

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
    expected_schema_path = os.path.join(config.CONFIG["Test.data_dir"],
                                        "bigquery", "ExportedFile.schema")
    with open(expected_schema_path, mode="rt", encoding="utf-8") as file:
      expected_schema_data = json.load(file)

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

  @export_test_lib.WithAllExportConverters
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
              st_ctime=1336129892,
              st_btime=1338111338))

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
                     "ExportedFile.jsonlines"), "rb")

    # Bigquery expects a newline separarted list of JSON dicts, but this isn't
    # valid JSON so we can't just load the whole thing and compare.
    counter = 0
    for actual, expected in zip(actual_fd, expected_fd):
      actual = actual.decode("utf-8")
      expected = expected.decode("utf-8")
      self.assertEqual(json.loads(actual), json.loads(expected))
      counter += 1

    self.assertEqual(counter, 10)

  @export_test_lib.WithAllExportConverters
  def testMissingTimestampSerialization(self):
    response = rdf_client_fs.StatEntry()
    response.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
    response.pathspec.path = "/foo/bar"
    response.st_mtime = None

    args = bigquery_plugin.BigQueryOutputPluginArgs()

    output = self.ProcessResponses(plugin_args=args, responses=[response])
    self.assertLen(output, 1)

    _, filedesc, _, _ = output[0]
    with gzip.GzipFile(mode="r", fileobj=filedesc) as filedesc:
      filedesc = io.TextIOWrapper(filedesc)
      content = json.load(filedesc)

    self.assertIsNone(content["st_mtime"])

  @export_test_lib.WithAllExportConverters
  def testBinaryDataExportDisabled(self):
    response = rdf_client_fs.BlobImageChunkDescriptor()
    response.digest = b"\x00\xff\x00\xff\x00"

    args = bigquery_plugin.BigQueryOutputPluginArgs()
    args.base64_bytes_export = False

    output = self.ProcessResponses(plugin_args=args, responses=[response])

    self.assertLen(output, 1)
    _, filedesc, _, _ = output[0]

    with gzip.GzipFile(mode="r", fileobj=filedesc) as filedesc:
      filedesc = io.TextIOWrapper(filedesc)
      content = json.load(filedesc)

    self.assertNotIn("digest", content)

  @export_test_lib.WithAllExportConverters
  def testBinaryDataExportEnabled(self):
    response = rdf_client_fs.BlobImageChunkDescriptor()
    response.digest = b"\x00\xff\x00"

    args = bigquery_plugin.BigQueryOutputPluginArgs()
    args.base64_bytes_export = True

    output = self.ProcessResponses(plugin_args=args, responses=[response])

    self.assertLen(output, 1)
    _, filedesc, _, _ = output[0]

    with gzip.GzipFile(mode="r", fileobj=filedesc) as filedesc:
      filedesc = io.TextIOWrapper(filedesc)
      content = json.load(filedesc)

    self.assertIn("digest", content)
    self.assertEqual(base64.b64decode(content["digest"]), b"\x00\xff\x00")

  def _parseOutput(self, name, stream):
    content_fd = gzip.GzipFile(None, "r", 9, stream)
    counter = 0

    # The source id is converted to a URN then to a JSON string.
    source_urn = str(rdfvalue.RDFURN(self.source_id))

    for item in content_fd:
      counter += 1
      row = json.loads(item.decode("utf-8"))

      if name == "ExportedFile":
        self.assertEqual(row["metadata"]["client_urn"],
                         "aff4:/%s" % self.client_id)
        self.assertEqual(row["metadata"]["hostname"], "Host-0.example.com")
        self.assertEqual(row["metadata"]["mac_address"],
                         "aabbccddee00\nbbccddeeff00")
        self.assertEqual(row["metadata"]["source_urn"], source_urn)
        self.assertEqual(row["urn"], "aff4:/%s/fs/os/中国新闻网新闻中" % self.client_id)
      else:
        self.assertEqual(row["metadata"]["client_urn"],
                         "aff4:/%s" % self.client_id)
        self.assertEqual(row["metadata"]["hostname"], "Host-0.example.com")
        self.assertEqual(row["metadata"]["mac_address"],
                         "aabbccddee00\nbbccddeeff00")
        self.assertEqual(row["metadata"]["source_urn"], source_urn)
        self.assertEqual(row["pid"], "42")

    self.assertEqual(counter, 1)

  @export_test_lib.WithAllExportConverters
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

  @export_test_lib.WithAllExportConverters
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
              st_ctime=1336129892,
              st_btime=1338111338))

    sizes = [37, 687, 722, 755, 788, 821, 684, 719, 752, 785]

    def GetSize(unused_path):
      return sizes.pop(0)

    # Force an early flush. Gzip is non deterministic since our
    # metadata is a dict with unpredictable order so we make up the file sizes
    # such that there is one flush during processing.
    with test_lib.ConfigOverrider({"BigQuery.max_file_post_size": 800}):
      with mock.patch.object(os.path, "getsize", GetSize):
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
                     "ExportedFile.jsonlines"), "rb")

    # Check that the same entries we expect are spread across the two files.
    counter = 0
    for actual_fd in actual_fds:
      for actual, expected in zip(actual_fd, expected_fd):
        actual = actual.decode("utf-8")
        expected = expected.decode("utf-8")
        self.assertEqual(json.loads(actual), json.loads(expected))
        counter += 1

    self.assertEqual(counter, 10)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
