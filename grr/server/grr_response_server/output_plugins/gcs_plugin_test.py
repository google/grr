#!/usr/bin/env python
"""Tests for GCS output plugin."""

import json
import requests

from absl import app

from unittest import mock
from unittest.mock import MagicMock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths

from grr_response_server.output_plugins import gcs_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects

from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class GcsOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests GCS output plugin."""

  def setUp(self):
    super().setUp()

    self.client_id = self.SetupClient(0)
    self.flow_id = '12345678'
    self.source_id = (
        rdf_client.ClientURN(self.client_id)
        .Add('Results')
        .RelativeName('aff4:/')
    )


  def _CallPlugin(self, plugin_args=None, responses=None):
    plugin_cls = gcs_plugin.GcsOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=self.source_id, args=plugin_args
    )

    plugin_cls.UploadBlobFromStream = MagicMock()

    messages = []
    for response in responses:
      messages.append(
          rdf_flow_objects.FlowResult(
              client_id=self.client_id, flow_id=self.flow_id, payload=response
          )
      )

    with test_lib.FakeTime(1445995873):
        plugin.ProcessResponses(plugin_state, messages)
        plugin.Flush(plugin_state)
        plugin.UpdateState(plugin_state)

    return plugin.uploaded_files


  def testClientFileFinderResponseUploaded(self):
    rdf_payload = rdf_file_finder.FileFinderResult()
    rdf_payload.stat_entry.st_size = 1234
    rdf_payload.stat_entry.pathspec.path = ("/var/log/test.log")
    rdf_payload.stat_entry.pathspec.pathtype = "OS"
    rdf_payload.transferred_file = rdf_client_fs.BlobImageDescriptor(chunks=[])

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        uploaded_files = self._CallPlugin(
            plugin_args=gcs_plugin.GcsOutputPluginArgs(
              project_id="test-project-id",
              gcs_bucket="text-gcs-bucket"
            ),
            responses=[rdf_payload],
        )

    self.assertEqual(uploaded_files, 1)


  def testClientFileFinderResponseNoProjectId(self):
    rdf_payload = rdf_file_finder.FileFinderResult()
    rdf_payload.stat_entry.st_size = 1234
    rdf_payload.stat_entry.pathspec.path = ("/var/log/test.log")
    rdf_payload.stat_entry.pathspec.pathtype = "OS"
    rdf_payload.transferred_file = rdf_client_fs.BlobImageDescriptor(chunks=[])

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        uploaded_files = self._CallPlugin(
            plugin_args=gcs_plugin.GcsOutputPluginArgs(
              project_id="",
              gcs_bucket="text-gcs-bucket"
            ),
            responses=[rdf_payload],
        )

    self.assertEqual(uploaded_files, 0)


  def testClientFileFinderResponseNoGcsBucket(self):
    rdf_payload = rdf_file_finder.FileFinderResult()
    rdf_payload.stat_entry.st_size = 1234
    rdf_payload.stat_entry.pathspec.path = ("/var/log/test.log")
    rdf_payload.stat_entry.pathspec.pathtype = "OS"
    rdf_payload.transferred_file = rdf_client_fs.BlobImageDescriptor(chunks=[])

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        uploaded_files = self._CallPlugin(
            plugin_args=gcs_plugin.GcsOutputPluginArgs(
              project_id="test-project-id",
              gcs_bucket=""
            ),
            responses=[rdf_payload],
        )

    self.assertEqual(uploaded_files, 0)


  def testClientFileFinderResponseEmptyFile(self):
    rdf_payload = rdf_file_finder.FileFinderResult()
    rdf_payload.stat_entry.st_size = 0
    rdf_payload.stat_entry.pathspec.path = ("/var/log/test.log")
    rdf_payload.stat_entry.pathspec.pathtype = "OS"
    rdf_payload.transferred_file = rdf_client_fs.BlobImageDescriptor(chunks=[])

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        uploaded_files = self._CallPlugin(
            plugin_args=gcs_plugin.GcsOutputPluginArgs(
              project_id="test-project-id",
              gcs_bucket="text-gcs-bucket"
            ),
            responses=[rdf_payload],
        )

    self.assertEqual(uploaded_files, 0)


  def testClientFileFinderResponseNoTransferredFile(self):
    rdf_payload = rdf_file_finder.FileFinderResult()
    rdf_payload.stat_entry.st_size = 1234
    rdf_payload.stat_entry.pathspec.path = ("/var/log/test.log")
    rdf_payload.stat_entry.pathspec.pathtype = "OS"

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15)):
        uploaded_files = self._CallPlugin(
            plugin_args=gcs_plugin.GcsOutputPluginArgs(
              project_id="test-project-id",
              gcs_bucket="text-gcs-bucket"
            ),
            responses=[rdf_payload],
        )

    self.assertEqual(uploaded_files, 0)


if __name__ == '__main__':
  app.run(test_lib.main)