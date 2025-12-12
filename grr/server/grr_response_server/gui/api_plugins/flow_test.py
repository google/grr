#!/usr/bin/env python
"""This module contains tests for flows-related API handlers."""

import csv
import io
import os
import random
import tarfile
from typing import Callable, Iterable, Iterator
from unittest import mock
import zipfile

from absl import app
from absl.testing import absltest
import yaml

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import tests_pb2
from grr_response_proto.api import flow_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import instant_output_plugin
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.export_converters import log_message
from grr_response_server.flows import file
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.gui.api_plugins import mig_flow
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiFlowIdTest(
    rdf_test_base.RDFValueTestMixin,
    hunt_test_lib.StandardHuntTestMixin,
    test_lib.GRRBaseTest,
):
  """Test for ApiFlowId."""

  rdfvalue_class = flow_plugin.ApiFlowId

  def GenerateSample(self, number=0):
    return flow_plugin.ApiFlowId("F:" + "123" * (number + 1))

  def testRaisesWhenInitializedFromInvalidValues(self):
    with self.assertRaises(ValueError):
      flow_plugin.ApiFlowId("bla%h")


class ApiFlowTest(test_lib.GRRBaseTest):
  """Test for ApiFlow."""

  def testInitializesClientIdForClientBasedFlows(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=processes.ListProcesses,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)

    self.assertEqual(
        flow_api_obj.client_id, client_plugin.ApiClientId(client_id).ToString()
    )

  def testFlowWithoutFlowProgressTypeReportsDefaultFlowProgress(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_test_lib.DummyFlow,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)
    flow_api_obj = mig_flow.ToRDFApiFlow(flow_api_obj)
    self.assertIsNotNone(flow_api_obj.progress)
    self.assertIsInstance(
        flow_api_obj.progress, rdf_flow_objects.DefaultFlowProgress
    )

  def testFlowWithoutResultsCorrectlyReportsEmptyResultMetadata(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_test_lib.DummyFlow,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)
    flow_api_obj = mig_flow.ToRDFApiFlow(flow_api_obj)
    self.assertIsNotNone(flow_api_obj.result_metadata)
    self.assertEmpty(flow_api_obj.result_metadata.num_results_per_type_tag)

  def testWithFlowProgressTypeReportsProgressCorrectly(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_test_lib.DummyFlowWithProgress,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)
    flow_api_obj = mig_flow.ToRDFApiFlow(flow_api_obj)
    self.assertIsNotNone(flow_api_obj.progress)
    # An empty proto is created by default.
    self.assertFalse(flow_api_obj.progress.HasField("status"))

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(
        flow_obj, with_progress=True
    )
    flow_api_obj = mig_flow.ToRDFApiFlow(flow_api_obj)
    self.assertIsNotNone(flow_api_obj.progress)
    self.assertEqual(flow_api_obj.progress.status, "Progress.")

  def testInitApiFlowFromFlowObjectwithStore(self):
    client_id = self.SetupClient(0)
    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id="ABCDE",
    )
    store = tests_pb2.DummyFlowStore(msg="ʕノ•ᴥ•ʔノ ︵ ┻━┻")
    flow_obj.store.Pack(store)

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)

    self.assertTrue(flow_api_obj.HasField("store"))
    flow_api_obj.store.Unpack(store)
    self.assertEqual(store.msg, "ʕノ•ᴥ•ʔノ ︵ ┻━┻")

  def testUnknownFlowNameReturnsBestEffortApiFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id,
        flow_cls=flow_test_lib.DummyFlow,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_obj.flow_class_name = "UnknownFlow"

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(
        flow_obj, with_progress=True
    )
    self.assertEqual(flow_api_obj.name, "UnknownFlow")
    self.assertFalse(flow_api_obj.HasField("progress"))


class ApiGetFlowFilesArchiveHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiGetFlowFilesArchiveHandler."""

  def setUp(self):
    super().setUp()

    self.handler = flow_plugin.ApiGetFlowFilesArchiveHandler()

    self.client_id = self.SetupClient(0)

    action_mock = action_mocks.FileFinderClientMock()
    self.flow_id = flow_test_lib.StartAndRunFlow(
        file_finder.FileFinder,
        action_mock,
        client_id=self.client_id,
        creator=self.test_username,
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[os.path.join(self.base_path, "test.plist")],
            action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        ),
    )

    if isinstance(self.flow_id, rdfvalue.SessionID):
      self.flow_id = self.flow_id.Basename()

  def _GetZipManifest(self, result):
    out_fd = io.BytesIO()

    for chunk in result.GenerateContent():
      out_fd.write(chunk)

    zip_fd = zipfile.ZipFile(out_fd, "r")
    for name in zip_fd.namelist():
      if name.endswith("MANIFEST"):
        return yaml.safe_load(zip_fd.read(name))

    raise RuntimeError("MANIFEST not found")

  def _GetTarGzManifest(self, result):
    with utils.TempDirectory() as temp_dir:
      tar_path = os.path.join(temp_dir, "archive.tar.gz")
      with open(tar_path, "wb") as fd:
        for chunk in result.GenerateContent():
          fd.write(chunk)

      with tarfile.open(tar_path) as tar_fd:
        tar_fd.extractall(path=temp_dir)

      for parent, _, files in os.walk(temp_dir):
        if "MANIFEST" in files:
          with open(os.path.join(parent, "MANIFEST"), "rb") as fd:
            return yaml.safe_load(fd.read())

    raise RuntimeError("MANIFEST not found")

  def testGeneratesZipArchive(self):
    result = self.handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=self.flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testGeneratesZipArchiveForCollectFilesByKnownPath(self):
    client_mock = action_mocks.FileFinderClientMockWithTimestamps()
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dir:
      temp_filepath = os.path.join(temp_dir, "foo.txt")
      with open(temp_filepath, mode="w") as temp_file:
        temp_file.write("Lorem ipsum.")

      flow_id = flow_test_lib.StartAndRunFlow(
          file.CollectFilesByKnownPath,
          client_mock,
          client_id=self.client_id,
          flow_args=rdf_file_finder.CollectFilesByKnownPathArgs(
              paths=[temp_filepath],
          ),
          creator=self.test_username,
      )

    result = self.handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testGeneratesZipArchiveForCollectMultipleFiles(self):
    client_mock = action_mocks.CollectMultipleFilesClientMock()
    with temp.AutoTempDirPath(remove_non_empty=True) as temp_dir:
      temp_filepath = os.path.join(temp_dir, "foo.txt")
      with open(temp_filepath, mode="w") as temp_file:
        temp_file.write("Lorem ipsum.")

      flow_id = flow_test_lib.StartAndRunFlow(
          file.CollectMultipleFiles,
          client_mock,
          client_id=self.client_id,
          flow_args=rdf_file_finder.CollectMultipleFilesArgs(
              path_expressions=[temp_filepath],
          ),
          creator=self.test_username,
      )

    result = self.handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsInclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        exclude_path_globs=[],
        include_only_path_globs=[rdf_paths.GlobExpression("/**/foo.bar")],
    )
    result = handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=self.flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)],
    )

  def testArchivesFileMatchingPathGlobsInclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        exclude_path_globs=[],
        include_only_path_globs=[rdf_paths.GlobExpression("/**/*/test.plist")],
    )
    result = handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=self.flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsExclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        include_only_path_globs=[rdf_paths.GlobExpression("/**/*/test.plist")],
        exclude_path_globs=[rdf_paths.GlobExpression("**/*.plist")],
    )
    result = handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id, flow_id=self.flow_id, archive_format="ZIP"
        ),
        context=self.context,
    )
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)],
    )

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        flow_pb2.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="TAR_GZ",
        ),
        context=self.context,
    )

    manifest = self._GetTarGzManifest(result)
    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testGeneratesZipArchiveForFlowWithCustomMappings(self):
    path = abstract_db.ClientPath.OS(
        self.client_id, self.base_path.lstrip("/").split("/") + ["test.plist"]
    )
    mappings = [
        flow_base.ClientPathArchiveMapping(path, "foo/file"),
    ]
    with mock.patch.object(
        file_finder.FileFinder, "GetFilesArchiveMappings", return_value=mappings
    ):
      result = self.handler.Handle(
          flow_pb2.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id,
              flow_id=self.flow_id,
              archive_format="ZIP",
          ),
          context=self.context,
      )

    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["client_id"], self.client_id)
    self.assertEqual(manifest["flow_id"], self.flow_id)
    self.assertEqual(manifest["processed_files"], {path.vfs_path: "foo/file"})
    self.assertEmpty(manifest["missing_files"])

  def testGeneratesTarGzArchiveForFlowWithCustomMappings(self):
    path = abstract_db.ClientPath.OS(
        self.client_id, self.base_path.lstrip("/").split("/") + ["test.plist"]
    )
    mappings = [
        flow_base.ClientPathArchiveMapping(path, "foo/file"),
    ]
    with mock.patch.object(
        file_finder.FileFinder, "GetFilesArchiveMappings", return_value=mappings
    ):
      result = self.handler.Handle(
          flow_pb2.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id,
              flow_id=self.flow_id,
              archive_format="TAR_GZ",
          ),
          context=self.context,
      )

    manifest = self._GetTarGzManifest(result)
    self.assertEqual(manifest["client_id"], self.client_id)
    self.assertEqual(manifest["flow_id"], self.flow_id)
    self.assertEqual(manifest["processed_files"], {path.vfs_path: "foo/file"})
    self.assertEmpty(manifest["missing_files"])


class TestInstantOutputPluginProto(
    instant_output_plugin.InstantOutputPluginProto,
):
  """Test plugin."""

  plugin_name = "test"
  friendly_name = "test plugin"
  description = "test plugin description"

  def Start(self):
    yield f"Start: {self.source_urn}"

  def ProcessValuesOfType(
      self,
      type_url: str,
      type_url_results_generator_fn: Callable[
          [], Iterable[flows_pb2.FlowResult]
      ],
  ) -> Iterator[bytes]:
    yield f"Values of type: {type_url}"
    for flow_result in type_url_results_generator_fn():
      yield (
          "First pass:"
          f" {flow_result.payload} (client_id={flow_result.client_id})"
      )
    for flow_result in type_url_results_generator_fn():
      yield (
          "Second pass:"
          f" {flow_result.payload} (client_id={flow_result.client_id})"
      )

  def Finish(self):
    yield f"Finish: {self.source_urn}"


class ApiGetExportedFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiGetExportedFlowResultsHandler."""

  def setUp(self):
    super().setUp()

    self.handler = flow_plugin.ApiGetExportedFlowResultsHandler()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")

  @test_plugins.WithInstantOutputPluginProto(TestInstantOutputPluginProto)
  def testWorksCorrectlyWithProtoPlugin(
      self,
  ):
    input_str = "golden"

    flow_id = flow_test_lib.StartAndRunFlow(
        flow_test_lib.EchoLogFlowProto,
        flow_args=rdf_client.LogMessage(data=input_str),
        client_id=self.client_id,
        creator=self.test_username,
    )

    result = self.handler.Handle(
        flow_pb2.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=flow_id,
            plugin_name=TestInstantOutputPluginProto.plugin_name,
        ),
        context=self.context,
    )

    chunks = list(result.GenerateContent())

    # The flow is expected to return an echo of the input log message
    flow_result = jobs_pb2.LogMessage(data=f"echo('{input_str}')")
    # The InstantOutputPluginProto should received the FlowResult with a
    # payload packed into Any proto and print that.
    packed_flow_result = any_pb2.Any()
    packed_flow_result.Pack(flow_result)

    self.assertListEqual(
        chunks,
        [
            f"Start: aff4:/{self.client_id}/flows/{flow_id}",
            (
                "Values of type:"
                f" type.googleapis.com/{jobs_pb2.LogMessage.DESCRIPTOR.full_name}"
            ),
            f"First pass: {packed_flow_result} (client_id={self.client_id})",
            f"Second pass: {packed_flow_result} (client_id={self.client_id})",
            f"Finish: aff4:/{self.client_id}/flows/{flow_id}",
        ],
    )

  def testComplainsAboutMissingPlugin(
      self,
  ):
    with self.assertRaises(flow_plugin.InstantOutputPluginNotFoundError):
      self.handler.Handle(
          flow_pb2.ApiGetExportedFlowResultsArgs(
              client_id=self.client_id,
              flow_id="shouldn't be relevant",
              plugin_name="non-existing",
          ),
          context=self.context,
      )

  @test_plugins.WithInstantOutputPluginProto(
      csv_instant_plugin.CSVInstantOutputPluginProto
  )
  @export_test_lib.WithExportConverterProto(
      log_message.LogMessageToExportedStringConverter
  )
  def testIntegrationWithCSVAndExportConverter(
      self,
  ):
    flow_id = flow_test_lib.StartAndRunFlow(
        flow_test_lib.EchoLogFlowProto,
        flow_args=rdf_client.LogMessage(data="soda pop"),
        client_id=self.client_id,
        creator=self.test_username,
    )

    result = self.handler.Handle(
        flow_pb2.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=flow_id,
            plugin_name=csv_instant_plugin.CSVInstantOutputPluginProto.plugin_name,
        ),
        context=self.context,
    )

    chunks = list(result.GenerateContent())

    fd_path = os.path.join(self.temp_dir, "csv_result.zip")
    with open(fd_path, "wb") as fd:
      for chunk in chunks:
        fd.write(chunk)
    zip_fd = zipfile.ZipFile(fd_path)
    filename_prefix = f"results_{self.client_id}_flows_{flow_id}"

    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            f"{filename_prefix}/MANIFEST",
            f"{filename_prefix}/ExportedString/from_LogMessage.csv",
        ]),
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{filename_prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest, {"export_stats": {"LogMessage": {"ExportedString": 1}}}
    )

    with zip_fd.open(
        f"{filename_prefix}/ExportedString/from_LogMessage.csv"
    ) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))

    self.assertLen(parsed_output, 1)
    self.assertEqual(
        parsed_output[0]["data"],
        "echo('soda pop')",
    )


class DummyFlowWithTwoTaggedReplies(flow_base.FlowBase):
  """Emits 2 tagged replies."""

  def Start(self):
    self.CallState(next_state="SendSomething")

  def SendSomething(self, responses=None):
    del responses  # Unused.
    self.SendReply(rdfvalue.RDFString("foo"), tag="tag:foo")
    self.SendReply(rdfvalue.RDFInteger(42), tag="tag:bar")


class ApiListFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiListFlowResultsHandler."""

  def setUp(self):
    super().setUp()

    self.handler = flow_plugin.ApiListFlowResultsHandler()

    self.client_id = self.SetupClient(0)
    self.flow_id = flow_test_lib.StartAndRunFlow(
        DummyFlowWithTwoTaggedReplies, client_id=self.client_id
    )

  def testReturnsTagsInResultsList(self):
    result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id
        )
    )
    self.assertEqual(result.total_count, 2)
    self.assertLen(result.items, 2)
    self.assertEqual(result.items[0].tag, "tag:foo")
    self.assertEqual(result.items[1].tag, "tag:bar")

  def testCorrectlyFiltersByTag(self):
    foo_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:foo"
        )
    )
    self.assertEqual(foo_result.total_count, 1)
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    bar_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:bar"
        )
    )
    self.assertEqual(bar_result.total_count, 1)
    self.assertLen(bar_result.items, 1)
    self.assertEqual(bar_result.items[0].tag, "tag:bar")

  def testCorrectlyFiltersByType(self):
    foo_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_type=rdfvalue.RDFString.__name__,
        )
    )
    self.assertEqual(foo_result.total_count, 1)
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    bar_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_type=rdfvalue.RDFInteger.__name__,
        )
    )
    self.assertEqual(bar_result.total_count, 1)
    self.assertLen(bar_result.items, 1)
    self.assertEqual(bar_result.items[0].tag, "tag:bar")

  def testCorrectlyFiltersBySubstring(self):
    foo_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, filter="foo"
        )
    )
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    # Filtering by a stringified number is going to fail, as we match against
    # payload protobufs in their serialized protobuf form, meaning that integers
    # are going to be serialized as varints and not as unicode strings.
    bar_result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, filter="42"
        )
    )
    self.assertEmpty(bar_result.items)

  def testReturnsNothingWhenFilteringByNonExistingTag(self):
    result = self.handler.Handle(
        flow_pb2.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_tag="non-existing",
        )
    )
    self.assertEqual(result.total_count, 0)
    self.assertEmpty(result.items)


class ApiListAllFlowOutputPluginLogsHandlerTest(
    api_test_lib.ApiCallHandlerTest
):
  """Tests for ApiListAllFlowOutputPluginLogsHandler."""

  def setUp(self):
    super().setUp()
    self.handler = flow_plugin.ApiListAllFlowOutputPluginLogsHandler()
    self.client_id = self.SetupClient(0)
    self.flow_id = flow_test_lib.StartFlow(
        flow_test_lib.DummyFlow, client_id=self.client_id
    )

  def testReturnsCorrectData(self):
    entry1 = flows_pb2.FlowOutputPluginLogEntry(
        client_id=self.client_id,
        flow_id=self.flow_id,
        output_plugin_id="plugin1",
        log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
        message="foo",
    )
    entry2 = flows_pb2.FlowOutputPluginLogEntry(
        client_id=self.client_id,
        flow_id=self.flow_id,
        output_plugin_id="plugin2",
        log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
        message="bar",
    )
    data_store.REL_DB.WriteMultipleFlowOutputPluginLogEntries([entry1, entry2])

    args = flow_pb2.ApiListAllFlowOutputPluginLogsArgs(
        client_id=self.client_id, flow_id=self.flow_id
    )
    result = self.handler.Handle(args, context=self.context)

    self.assertEqual(result.total_count, 2)
    self.assertLen(result.items, 2)
    self.assertEqual(result.items[0].message, "foo")
    self.assertEqual(result.items[0].output_plugin_id, "plugin1")
    self.assertEqual(
        result.items[0].log_entry_type,
        flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertEqual(result.items[1].message, "bar")
    self.assertEqual(result.items[1].output_plugin_id, "plugin2")
    self.assertEqual(
        result.items[1].log_entry_type,
        flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )


def _CreateContext(db: abstract_db.Database) -> api_call_context.ApiCallContext:
  username = "".join(random.choice("abcdef") for _ in range(8))
  db.WriteGRRUser(username)
  return api_call_context.ApiCallContext(username)


class ApiExplainGlobExpressionHandlerTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testHandlerUsesKnowledgeBase(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.users.add(username="foo", homedir="/home/foo")
    db.WriteClientSnapshot(snapshot)

    handler = flow_plugin.ApiExplainGlobExpressionHandler()
    args = flow_pb2.ApiExplainGlobExpressionArgs(
        example_count=2,
        client_id=client_id,
        glob_expression="%%users.homedir%%/foo",
    )
    results = handler.Handle(args, context=context)
    self.assertEqual(
        list(results.components),
        [
            flows_pb2.GlobComponentExplanation(
                glob_expression="%%users.homedir%%", examples=["/home/foo"]
            ),
            flows_pb2.GlobComponentExplanation(glob_expression="/foo"),
        ],
    )


class ApiCreateFlowTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testDisableRRGSupport(self, db: abstract_db.Database):
    handler = flow_plugin.ApiCreateFlowHandler()

    client_id = db_test_utils.InitializeRRGClient(db)

    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id
    args.flow.name = processes.ListProcesses.__name__
    args.flow.runner_args.disable_rrg_support = True

    result = handler.Handle(args, context=_CreateContext(db))
    self.assertTrue(result.runner_args.disable_rrg_support)

    flow_obj = db.ReadFlowObject(client_id, result.flow_id)
    self.assertTrue(flow_obj.disable_rrg_support)


class ApiScheduleFlowsTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testScheduleFlow(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    sf = handler.Handle(args, context=context)

    self.assertEqual(sf.client_id, client_id)
    self.assertEqual(sf.creator, context.username)
    self.assertNotEmpty(sf.scheduled_flow_id)
    self.assertEqual(sf.flow_name, file.CollectFilesByKnownPath.__name__)
    flow_args = flows_pb2.CollectFilesByKnownPathArgs()
    sf.flow_args.Unpack(flow_args)
    self.assertEqual(flow_args.paths, ["/foo"])
    self.assertEqual(sf.runner_args.cpu_limit, 60)

  @db_test_lib.WithDatabase
  def testListScheduledFlows(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id1 = db_test_utils.InitializeClient(db)
    client_id2 = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id1
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    sf1 = handler.Handle(args, context=context)

    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id1
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    sf2 = handler.Handle(args, context=context)

    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id2
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    handler.Handle(args, context=context)

    handler = flow_plugin.ApiListScheduledFlowsHandler()
    args = flow_pb2.ApiListScheduledFlowsArgs(
        client_id=client_id1, creator=context.username
    )
    results = handler.Handle(args, context=context)

    self.assertCountEqual(results.scheduled_flows, [sf1, sf2])

  @db_test_lib.WithDatabase
  def testUnscheduleFlowRemovesScheduledFlow(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    sf1 = handler.Handle(args, context=context)

    args = flow_pb2.ApiCreateFlowArgs()
    args.client_id = client_id
    args.flow.name = file.CollectFilesByKnownPath.__name__
    args.flow.args.Pack(flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]))
    args.flow.runner_args.CopyFrom(flows_pb2.FlowRunnerArgs(cpu_limit=60))
    sf2 = handler.Handle(args, context=context)

    handler = flow_plugin.ApiUnscheduleFlowHandler()
    args = flow_pb2.ApiUnscheduleFlowArgs(
        client_id=client_id, scheduled_flow_id=sf1.scheduled_flow_id
    )
    handler.Handle(args, context=context)

    handler = flow_plugin.ApiListScheduledFlowsHandler()
    args = flow_pb2.ApiListScheduledFlowsArgs(
        client_id=client_id, creator=context.username
    )
    results = handler.Handle(args, context=context)

    self.assertCountEqual(results.scheduled_flows, [sf2])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
