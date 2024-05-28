#!/usr/bin/env python
"""This module contains tests for flows-related API handlers."""

import io
import os
import random
import tarfile
from unittest import mock
import zipfile

from absl import app
from absl.testing import absltest
import yaml

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_core.lib.util import temp
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_proto.api import flow_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows import file
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.gui.api_plugins import mig_flow
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
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
        client_id=client_id, flow_cls=processes.ListProcesses
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)

    self.assertEqual(
        flow_api_obj.client_id, client_plugin.ApiClientId(client_id).ToString()
    )

  def testFlowWithoutFlowProgressTypeReportsDefaultFlowProgress(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_test_lib.DummyFlow
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
        client_id=client_id, flow_cls=flow_test_lib.DummyFlow
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.InitApiFlowFromFlowObject(flow_obj)
    flow_api_obj = mig_flow.ToRDFApiFlow(flow_api_obj)
    self.assertIsNotNone(flow_api_obj.result_metadata)
    self.assertEmpty(flow_api_obj.result_metadata.num_results_per_type_tag)

  def testWithFlowProgressTypeReportsProgressCorrectly(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_test_lib.DummyFlowWithProgress
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

  def testUnknownFlowNameReturnsBestEffortApiFlow(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_test_lib.DummyFlow
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
    self.flow_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        action_mock,
        client_id=self.client_id,
        creator=self.test_username,
        paths=[os.path.join(self.base_path, "test.plist")],
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
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

      flow_id = flow_test_lib.TestFlowHelper(
          file.CollectFilesByKnownPath.__name__,
          client_mock,
          client_id=self.client_id,
          paths=[temp_filepath],
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

      flow_id = flow_test_lib.TestFlowHelper(
          file.CollectMultipleFiles.__name__,
          client_mock,
          client_id=self.client_id,
          path_expressions=[temp_filepath],
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


class ApiGetExportedFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiGetExportedFlowResultsHandler."""

  def setUp(self):
    super().setUp()

    self.handler = flow_plugin.ApiGetExportedFlowResultsHandler()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")

  def testWorksCorrectlyWithTestOutputPluginOnFlowWithSingleResult(self):
    with test_lib.FakeTime(42):
      sid = flow_test_lib.TestFlowHelper(
          flow_test_lib.DummyFlowWithSingleReply.__name__,
          client_id=self.client_id,
          creator=self.test_username,
      )

    result = self.handler.Handle(
        flow_plugin.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=sid,
            plugin_name=test_plugins.TestInstantOutputPlugin.plugin_name,
        ),
        context=self.context,
    )

    chunks = list(result.GenerateContent())

    self.assertListEqual(
        chunks,
        [
            "Start: aff4:/%s/flows/%s" % (self.client_id, sid),
            "Values of type: RDFString",
            "First pass: oh (source=aff4:/%s)" % self.client_id,
            "Second pass: oh (source=aff4:/%s)" % self.client_id,
            "Finish: aff4:/%s/flows/%s" % (self.client_id, sid),
        ],
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
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id
        )
    )
    self.assertEqual(result.total_count, 2)
    self.assertLen(result.items, 2)
    self.assertEqual(result.items[0].tag, "tag:foo")
    self.assertEqual(result.items[1].tag, "tag:bar")

  def testCorrectlyFiltersByTag(self):
    foo_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:foo"
        )
    )
    self.assertEqual(foo_result.total_count, 1)
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    bar_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:bar"
        )
    )
    self.assertEqual(bar_result.total_count, 1)
    self.assertLen(bar_result.items, 1)
    self.assertEqual(bar_result.items[0].tag, "tag:bar")

  def testCorrectlyFiltersByType(self):
    foo_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_type=rdfvalue.RDFString.__name__,
        )
    )
    self.assertEqual(foo_result.total_count, 1)
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    bar_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
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
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, filter="foo"
        )
    )
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    # Filtering by a stringified number is going to fail, as we match against
    # payload protobufs in their serialized protobuf form, meaning that integers
    # are going to be serialized as varints and not as unicode strings.
    bar_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, filter="42"
        )
    )
    self.assertEmpty(bar_result.items)

  def testReturnsNothingWhenFilteringByNonExistingTag(self):
    result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_tag="non-existing",
        )
    )
    self.assertEqual(result.total_count, 0)
    self.assertEmpty(result.items)


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
    snapshot.knowledge_base.users.add(homedir="/home/foo")
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
