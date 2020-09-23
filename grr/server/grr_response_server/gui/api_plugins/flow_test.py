#!/usr/bin/env python
# Lint as: python3
"""This module contains tests for flows-related API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import random
import tarfile
from typing import Iterable
import zipfile

from absl import app
from absl.testing import absltest
import mock
import yaml

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import abstract as abstract_parser
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import temp
from grr_response_server import access_control
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows import file
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.gui.api_plugins import flow as flow_plugin
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib


class ApiFlowIdTest(rdf_test_base.RDFValueTestMixin,
                    hunt_test_lib.StandardHuntTestMixin, test_lib.GRRBaseTest):
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
        client_id=client_id, flow_cls=processes.ListProcesses)
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(flow_obj)

    self.assertEqual(flow_api_obj.client_id,
                     client_plugin.ApiClientId(client_id))

  def testFlowWithoutFlowProgressTypeDoesNotReportProgress(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_test_lib.DummyFlow)
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(flow_obj)
    self.assertIsNone(flow_api_obj.progress)

    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(
        flow_obj, with_progress=True)
    self.assertIsNone(flow_api_obj.progress)

  def testWithFlowProgressTypeReportsProgressCorrectly(self):
    client_id = self.SetupClient(0)
    flow_id = flow.StartFlow(
        client_id=client_id, flow_cls=flow_test_lib.DummyFlowWithProgress)
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)

    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(flow_obj)
    self.assertIsNotNone(flow_api_obj.progress)
    # An empty proto is created by default.
    self.assertFalse(flow_api_obj.progress.HasField("status"))

    flow_api_obj = flow_plugin.ApiFlow().InitFromFlowObject(
        flow_obj, with_progress=True)
    self.assertIsNotNone(flow_api_obj.progress)
    self.assertEqual(flow_api_obj.progress.status, "Progress.")


class ApiCreateFlowHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Test for ApiCreateFlowHandler."""

  def setUp(self):
    super(ApiCreateFlowHandlerTest, self).setUp()
    self.client_id = self.SetupClient(0)
    self.handler = flow_plugin.ApiCreateFlowHandler()

  def testRunnerArgsBaseSessionIdDoesNotAffectCreatedFlow(self):
    """When multiple clients match, check we run on the latest one."""
    flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
        base_session_id="aff4:/foo")
    args = flow_plugin.ApiCreateFlowArgs(
        client_id=self.client_id,
        flow=flow_plugin.ApiFlow(
            name=processes.ListProcesses.__name__,
            runner_args=flow_runner_args))

    result = self.handler.Handle(args, context=self.context)
    self.assertNotStartsWith(str(result.urn), "aff4:/foo")


class ApiGetFlowFilesArchiveHandlerTest(api_test_lib.ApiCallHandlerTest):
  """Tests for ApiGetFlowFilesArchiveHandler."""

  def setUp(self):
    super(ApiGetFlowFilesArchiveHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetFlowFilesArchiveHandler()

    self.client_id = self.SetupClient(0)

    action_mock = action_mocks.FileFinderClientMock()
    self.flow_id = flow_test_lib.TestFlowHelper(
        file_finder.FileFinder.__name__,
        action_mock,
        client_id=self.client_id,
        token=self.token,
        paths=[os.path.join(self.base_path, "test.plist")],
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"))

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
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="ZIP"),
        context=self.context)
    manifest = self._GetZipManifest(result)

    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsInclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        exclude_path_globs=[],
        include_only_path_globs=[rdf_paths.GlobExpression("/**/foo.bar")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="ZIP"),
        context=self.context)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)])

  def testArchivesFileMatchingPathGlobsInclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        exclude_path_globs=[],
        include_only_path_globs=[rdf_paths.GlobExpression("/**/*/test.plist")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="ZIP"),
        context=self.context)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testIgnoresFileNotMatchingPathGlobsExclusionList(self):
    handler = flow_plugin.ApiGetFlowFilesArchiveHandler(
        include_only_path_globs=[rdf_paths.GlobExpression("/**/*/test.plist")],
        exclude_path_globs=[rdf_paths.GlobExpression("**/*.plist")])
    result = handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="ZIP"),
        context=self.context)
    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["archived_files"], 0)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 1)
    self.assertEqual(
        manifest["ignored_files_list"],
        ["aff4:/%s/fs/os%s/test.plist" % (self.client_id, self.base_path)])

  def testGeneratesTarGzArchive(self):
    result = self.handler.Handle(
        flow_plugin.ApiGetFlowFilesArchiveArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            archive_format="TAR_GZ"),
        context=self.context)

    manifest = self._GetTarGzManifest(result)
    self.assertEqual(manifest["archived_files"], 1)
    self.assertEqual(manifest["failed_files"], 0)
    self.assertEqual(manifest["processed_files"], 1)
    self.assertEqual(manifest["ignored_files"], 0)

  def testGeneratesZipArchiveForFlowWithCustomMappings(self):
    path = abstract_db.ClientPath.OS(
        self.client_id,
        self.base_path.lstrip("/").split("/") + ["test.plist"])
    mappings = [
        flow_base.ClientPathArchiveMapping(path, "foo/file"),
    ]
    with mock.patch.object(
        file_finder.FileFinder,
        "GetFilesArchiveMappings",
        return_value=mappings):
      result = self.handler.Handle(
          flow_plugin.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id,
              flow_id=self.flow_id,
              archive_format="ZIP"),
          context=self.context)

    manifest = self._GetZipManifest(result)
    self.assertEqual(manifest["client_id"], self.client_id)
    self.assertEqual(manifest["flow_id"], self.flow_id)
    self.assertEqual(manifest["processed_files"], {path.vfs_path: "foo/file"})
    self.assertEmpty(manifest["missing_files"])

  def testGeneratesTarGzArchiveForFlowWithCustomMappings(self):
    path = abstract_db.ClientPath.OS(
        self.client_id,
        self.base_path.lstrip("/").split("/") + ["test.plist"])
    mappings = [
        flow_base.ClientPathArchiveMapping(path, "foo/file"),
    ]
    with mock.patch.object(
        file_finder.FileFinder,
        "GetFilesArchiveMappings",
        return_value=mappings):
      result = self.handler.Handle(
          flow_plugin.ApiGetFlowFilesArchiveArgs(
              client_id=self.client_id,
              flow_id=self.flow_id,
              archive_format="TAR_GZ"),
          context=self.context)

    manifest = self._GetTarGzManifest(result)
    self.assertEqual(manifest["client_id"], self.client_id)
    self.assertEqual(manifest["flow_id"], self.flow_id)
    self.assertEqual(manifest["processed_files"], {path.vfs_path: "foo/file"})
    self.assertEmpty(manifest["missing_files"])


class ApiGetExportedFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiGetExportedFlowResultsHandler."""

  def setUp(self):
    super(ApiGetExportedFlowResultsHandlerTest, self).setUp()

    self.handler = flow_plugin.ApiGetExportedFlowResultsHandler()
    self.client_id = self.SetupClient(0)
    self.context = api_call_context.ApiCallContext("test")

  def testWorksCorrectlyWithTestOutputPluginOnFlowWithSingleResult(self):
    with test_lib.FakeTime(42):
      sid = flow_test_lib.TestFlowHelper(
          compatibility.GetName(flow_test_lib.DummyFlowWithSingleReply),
          client_id=self.client_id,
          token=self.token)

    result = self.handler.Handle(
        flow_plugin.ApiGetExportedFlowResultsArgs(
            client_id=self.client_id,
            flow_id=sid,
            plugin_name=test_plugins.TestInstantOutputPlugin.plugin_name),
        context=self.context)

    chunks = list(result.GenerateContent())

    self.assertListEqual(chunks, [
        "Start: aff4:/%s/flows/%s" %
        (self.client_id, sid), "Values of type: RDFString",
        "First pass: oh (source=aff4:/%s)" % self.client_id,
        "Second pass: oh (source=aff4:/%s)" % self.client_id,
        "Finish: aff4:/%s/flows/%s" % (self.client_id, sid)
    ])


class DummyFlowWithTwoTaggedReplies(flow_base.FlowBase):
  """Emits 2 tagged replies."""

  def Start(self):
    self.CallState(next_state="SendSomething")

  def SendSomething(self, responses=None):
    del responses  # Unused.
    self.SendReply(rdfvalue.RDFString("foo"), tag="tag:foo")
    self.SendReply(rdfvalue.RDFString("bar"), tag="tag:bar")


class ApiListFlowResultsHandlerTest(test_lib.GRRBaseTest):
  """Tests for ApiListFlowResultsHandler."""

  def setUp(self):
    super().setUp()

    self.handler = flow_plugin.ApiListFlowResultsHandler()

    self.client_id = self.SetupClient(0)
    self.flow_id = flow_test_lib.StartAndRunFlow(
        DummyFlowWithTwoTaggedReplies, client_id=self.client_id)

  def testReturnsTagsInResultsList(self):
    result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id))
    self.assertLen(result.items, 2)
    self.assertEqual(result.items[0].tag, "tag:foo")
    self.assertEqual(result.items[1].tag, "tag:bar")

  def testCorrectlyFiltersByTag(self):
    foo_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:foo"))
    self.assertLen(foo_result.items, 1)
    self.assertEqual(foo_result.items[0].tag, "tag:foo")

    bar_result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id, flow_id=self.flow_id, with_tag="tag:bar"))
    self.assertLen(bar_result.items, 1)
    self.assertEqual(bar_result.items[0].tag, "tag:bar")

  def testReturnsNothingWhenFilteringByNonExistingTag(self):
    result = self.handler.Handle(
        flow_plugin.ApiListFlowResultsArgs(
            client_id=self.client_id,
            flow_id=self.flow_id,
            with_tag="non-existing"))
    self.assertEmpty(result.items)


class ApiListParsedFlowResultsHandlerTest(absltest.TestCase):

  ECHO1337_ARTIFACT_SOURCE = rdf_artifacts.ArtifactSource(
      type=rdf_artifacts.ArtifactSource.SourceType.COMMAND,
      attributes={
          "cmd": "/bin/echo",
          "args": ["1337"],
      })

  ECHO1337_ARTIFACT = rdf_artifacts.Artifact(
      name="FakeArtifact",
      doc="Lorem ipsum.",
      sources=[ECHO1337_ARTIFACT_SOURCE])

  class FakeExecuteCommand(action_mocks.ActionMock):

    def ExecuteCommand(
        self,
        args: rdf_client_action.ExecuteRequest,
    ) -> Iterable[rdf_client_action.ExecuteResponse]:
      if args.cmd != "/bin/echo":
        raise ValueError(f"Unsupported command: {args.cmd}")

      stdout = " ".join(args.args).encode("utf-8")
      return [rdf_client_action.ExecuteResponse(stdout=stdout)]

  def setUp(self):
    super(ApiListParsedFlowResultsHandlerTest, self).setUp()
    self.handler = flow_plugin.ApiListParsedFlowResultsHandler()

  @db_test_lib.WithDatabase
  def testValidatesFlowName(self, db: abstract_db.Database):
    context = _CreateContext(db)

    class FakeFlow(flow_base.FlowBase):

      def Start(self):
        self.CallState("End")

      def End(self, responses: flow_responses.Responses) -> None:
        del responses  # Unused.

    client_id = db_test_utils.InitializeClient(db)
    flow_id = flow_test_lib.TestFlowHelper(
        FakeFlow.__name__,
        client_id=client_id,
        token=access_control.ACLToken(username=context.username))

    flow_test_lib.FinishAllFlowsOnClient(client_id)

    args = flow_plugin.ApiListParsedFlowResultsArgs()
    args.client_id = client_id
    args.flow_id = flow_id

    with self.assertRaisesRegex(ValueError, "artifact-collector"):
      self.handler.Handle(args, context=context)

  @db_test_lib.WithDatabase
  def testValidatesParsersWereNotApplied(self, db: abstract_db.Database):
    context = _CreateContext(db)

    client_id = db_test_utils.InitializeClient(db)

    with mock.patch.object(artifact_registry, "REGISTRY",
                           artifact_registry.ArtifactRegistry()) as registry:
      registry.RegisterArtifact(self.ECHO1337_ARTIFACT)

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [self.ECHO1337_ARTIFACT.name]
      flow_args.apply_parsers = True

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          self.FakeExecuteCommand(),
          client_id=client_id,
          args=flow_args,
          token=access_control.ACLToken(username=context.username))

    flow_test_lib.FinishAllFlowsOnClient(client_id)

    args = flow_plugin.ApiListParsedFlowResultsArgs()
    args.client_id = client_id
    args.flow_id = flow_id

    with self.assertRaisesRegex(ValueError, "already parsed"):
      self.handler.Handle(args, context=context)

  @db_test_lib.WithDatabase
  def testParsesArtifactCollectionResults(self, db: abstract_db.Database):
    context = _CreateContext(db)

    with mock.patch.object(artifact_registry, "REGISTRY",
                           artifact_registry.ArtifactRegistry()) as registry:
      registry.RegisterArtifact(self.ECHO1337_ARTIFACT)

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [self.ECHO1337_ARTIFACT.name]
      flow_args.apply_parsers = False

      client_id = db_test_utils.InitializeClient(db)
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          self.FakeExecuteCommand(),
          client_id=client_id,
          args=flow_args,
          token=access_control.ACLToken(username=context.username))

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    class FakeParser(
        abstract_parser.SingleResponseParser[rdf_client_action.ExecuteResponse],
    ):

      supported_artifacts = [self.ECHO1337_ARTIFACT.name]

      def ParseResponse(
          self,
          knowledge_base: rdf_client.KnowledgeBase,
          response: rdf_client_action.ExecuteResponse,
      ) -> Iterable[rdf_client_action.ExecuteResponse]:
        precondition.AssertType(response, rdf_client_action.ExecuteResponse)

        parsed_response = rdf_client_action.ExecuteResponse()
        parsed_response.stdout = response.stdout
        parsed_response.stderr = b"4815162342"
        return [parsed_response]

    with parser_test_lib._ParserContext("Fake", FakeParser):
      args = flow_plugin.ApiListParsedFlowResultsArgs(
          client_id=client_id, flow_id=flow_id, offset=0, count=1024)

      result = self.handler.Handle(args, context=context)

    self.assertEmpty(result.errors)
    self.assertLen(result.items, 1)

    response = result.items[0].payload
    self.assertIsInstance(response, rdf_client_action.ExecuteResponse)
    self.assertEqual(response.stdout, b"1337")
    self.assertEqual(response.stderr, b"4815162342")

  @db_test_lib.WithDatabase
  def testReportsArtifactCollectionErrors(self, db: abstract_db.Database):
    context = _CreateContext(db)

    with mock.patch.object(artifact_registry, "REGISTRY",
                           artifact_registry.ArtifactRegistry()) as registry:
      registry.RegisterArtifact(self.ECHO1337_ARTIFACT)

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [self.ECHO1337_ARTIFACT.name]
      flow_args.apply_parsers = False

      client_id = db_test_utils.InitializeClient(db)
      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          self.FakeExecuteCommand(),
          client_id=client_id,
          args=flow_args,
          token=access_control.ACLToken(username=context.username))

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    class FakeParser(
        abstract_parser.SingleResponseParser[rdf_client_action.ExecuteResponse],
    ):

      supported_artifacts = [self.ECHO1337_ARTIFACT.name]

      def ParseResponse(
          self, knowledge_base: rdf_client.KnowledgeBase,
          response: rdf_client_action.ExecuteResponse
      ) -> Iterable[rdf_client_action.ExecuteResponse]:
        del knowledge_base, response  # Unused.
        raise abstract_parser.ParseError("Lorem ipsum.")

    with parser_test_lib._ParserContext("Fake", FakeParser):
      args = flow_plugin.ApiListParsedFlowResultsArgs(
          client_id=client_id, flow_id=flow_id, offset=0, count=1024)

      result = self.handler.Handle(args, context=context)

    self.assertEmpty(result.items)
    self.assertLen(result.errors, 1)
    self.assertEqual(result.errors[0], "Lorem ipsum.")

  @db_test_lib.WithDatabase
  def testUsesKnowledgebaseFromFlow(self, db: abstract_db.Database):
    context = _CreateContext(db)

    client_id = db_test_utils.InitializeClient(db)

    # This is the snapshot that is visible to the flow and should be used for
    # parsing results.
    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "redox"
    db.WriteClientSnapshot(snapshot)

    with mock.patch.object(artifact_registry, "REGISTRY",
                           artifact_registry.ArtifactRegistry()) as registry:
      registry.RegisterArtifact(self.ECHO1337_ARTIFACT)

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [self.ECHO1337_ARTIFACT.name]
      flow_args.apply_parsers = False

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          self.FakeExecuteCommand(),
          client_id=client_id,
          args=flow_args,
          token=access_control.ACLToken(username=context.username))

    class FakeParser(
        abstract_parser.SingleResponseParser[rdf_client_action.ExecuteResponse],
    ):

      supported_artifacts = [self.ECHO1337_ARTIFACT.name]

      def ParseResponse(
          self,
          knowledge_base: rdf_client.KnowledgeBase,
          response: rdf_client_action.ExecuteResponse,
      ) -> Iterable[rdf_client_action.ExecuteResponse]:
        precondition.AssertType(response, rdf_client_action.ExecuteResponse)

        parsed_response = rdf_client_action.ExecuteResponse()
        parsed_response.stdout = response.stdout
        parsed_response.stderr = knowledge_base.os.encode("utf-8")
        return [parsed_response]

    # This is a snapshot written to the database after the responses were
    # collected, so this should not be used for parsing.
    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "linux"
    db.WriteClientSnapshot(snapshot)

    with parser_test_lib._ParserContext("Fake", FakeParser):
      args = flow_plugin.ApiListParsedFlowResultsArgs(
          client_id=client_id, flow_id=flow_id, offset=0, count=1024)

      result = self.handler.Handle(args, context=context)

    self.assertEmpty(result.errors)
    self.assertLen(result.items, 1)

    response = result.items[0].payload
    self.assertIsInstance(response, rdf_client_action.ExecuteResponse)
    self.assertEqual(response.stdout, b"1337")
    self.assertEqual(response.stderr.decode("utf-8"), "redox")

  @db_test_lib.WithDatabase
  def testUsesCollectionTimeFiles(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.os = "redox"
    db.WriteClientSnapshot(snapshot)

    with temp.AutoTempFilePath() as temp_filepath:
      fake_artifact_source = rdf_artifacts.ArtifactSource(
          type=rdf_artifacts.ArtifactSource.SourceType.FILE,
          attributes={
              "paths": [temp_filepath],
          })

      fake_artifact = rdf_artifacts.Artifact(
          name="FakeArtifact",
          doc="Lorem ipsum.",
          sources=[fake_artifact_source])

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [fake_artifact.name]
      flow_args.apply_parsers = False

      with io.open(temp_filepath, mode="wb") as temp_filedesc:
        temp_filedesc.write(b"OLD")

      with mock.patch.object(artifact_registry, "REGISTRY",
                             artifact_registry.ArtifactRegistry()) as registry:
        registry.RegisterArtifact(fake_artifact)

        # First, we run the artifact collector to collect the old file and save
        # the flow id to parse the results later.
        flow_id = flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            action_mocks.FileFinderClientMock(),
            client_id=client_id,
            args=flow_args,
            token=access_control.ACLToken(username=context.username))

        flow_test_lib.FinishAllFlowsOnClient(client_id)

      with io.open(temp_filepath, mode="wb") as temp_filedesc:
        temp_filedesc.write(b"NEW")

      with mock.patch.object(artifact_registry, "REGISTRY",
                             artifact_registry.ArtifactRegistry()) as registry:
        registry.RegisterArtifact(fake_artifact)

        # Now, we run the artifact collector again to collect the new file to
        # update to this version on the server. The parsing should be performed
        # against the previous flow.
        flow_test_lib.TestFlowHelper(
            collectors.ArtifactCollectorFlow.__name__,
            action_mocks.FileFinderClientMock(),
            client_id=client_id,
            args=flow_args,
            token=access_control.ACLToken(username=context.username))

        flow_test_lib.FinishAllFlowsOnClient(client_id)

    class FakeFileParser(abstract_parser.SingleFileParser[rdfvalue.RDFBytes]):

      supported_artifacts = [fake_artifact.name]

      def ParseFile(
          self,
          knowledge_base: rdf_client.KnowledgeBase,
          pathspec: rdf_paths.PathSpec,
          filedesc: file_store.BlobStream,
      ) -> Iterable[rdfvalue.RDFBytes]:
        del knowledge_base, pathspec  # Unused.
        return [rdfvalue.RDFBytes(filedesc.Read())]

    with parser_test_lib._ParserContext("FakeFile", FakeFileParser):
      args = flow_plugin.ApiListParsedFlowResultsArgs(
          client_id=client_id, flow_id=flow_id, offset=0, count=1024)

      result = self.handler.Handle(args, context=context)

    self.assertEmpty(result.errors)
    self.assertLen(result.items, 1)

    response = result.items[0].payload
    self.assertEqual(response, b"OLD")

  @db_test_lib.WithDatabase
  def testEmptyResults(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    fake_artifact = rdf_artifacts.Artifact(
        name="FakeArtifact", doc="Lorem ipsum.", sources=[])

    with mock.patch.object(artifact_registry, "REGISTRY",
                           artifact_registry.ArtifactRegistry()) as registry:
      registry.RegisterArtifact(fake_artifact)

      flow_args = rdf_artifacts.ArtifactCollectorFlowArgs()
      flow_args.artifact_list = [fake_artifact.name]
      flow_args.apply_parsers = False

      flow_id = flow_test_lib.TestFlowHelper(
          collectors.ArtifactCollectorFlow.__name__,
          self.FakeExecuteCommand(),
          client_id=client_id,
          args=flow_args,
          token=access_control.ACLToken(username=context.username))

      flow_test_lib.FinishAllFlowsOnClient(client_id)

    args = flow_plugin.ApiListParsedFlowResultsArgs(
        client_id=client_id, flow_id=flow_id, offset=0, count=1024)

    result = self.handler.Handle(args, context=context)
    self.assertEmpty(result.errors)
    self.assertEmpty(result.items)


def _CreateContext(db: abstract_db.Database) -> api_call_context.ApiCallContext:
  username = "".join(random.choice("abcdef") for _ in range(8))
  db.WriteGRRUser(username)
  return api_call_context.ApiCallContext(username)


class ApiApiExplainGlobExpressionHandlerTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testHandlerUsesKnowledgeBase(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    snapshot = rdf_objects.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.users = [rdf_client.User(homedir="/home/foo")]
    db.WriteClientSnapshot(snapshot)

    handler = flow_plugin.ApiExplainGlobExpressionHandler()
    args = flow_plugin.ApiExplainGlobExpressionArgs(
        example_count=2,
        client_id=client_id,
        glob_expression="%%users.homedir%%/foo")
    results = handler.Handle(args, context=context)
    self.assertEqual(
        list(results.components), [
            rdf_paths.GlobComponentExplanation(
                glob_expression="%%users.homedir%%", examples=["/home/foo"]),
            rdf_paths.GlobComponentExplanation(
                glob_expression="/foo", examples=[]),
        ])


class ApiScheduleFlowsTest(absltest.TestCase):

  @db_test_lib.WithDatabase
  def testScheduleFlow(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    args = flow_plugin.ApiCreateFlowArgs(
        client_id=client_id,
        flow=flow_plugin.ApiFlow(
            name=file.CollectSingleFile.__name__,
            args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
            runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60)))

    sf = handler.Handle(args, context=context)
    self.assertEqual(sf.client_id, client_id)
    self.assertEqual(sf.creator, context.username)
    self.assertNotEmpty(sf.scheduled_flow_id)
    self.assertEqual(sf.flow_name, file.CollectSingleFile.__name__)
    self.assertEqual(sf.flow_args.path, "/foo")
    self.assertEqual(sf.runner_args.cpu_limit, 60)

  @db_test_lib.WithDatabase
  def testListScheduledFlows(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id1 = db_test_utils.InitializeClient(db)
    client_id2 = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    sf1 = handler.Handle(
        flow_plugin.ApiCreateFlowArgs(
            client_id=client_id1,
            flow=flow_plugin.ApiFlow(
                name=file.CollectSingleFile.__name__,
                args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
                runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))),
        context=context)
    sf2 = handler.Handle(
        flow_plugin.ApiCreateFlowArgs(
            client_id=client_id1,
            flow=flow_plugin.ApiFlow(
                name=file.CollectSingleFile.__name__,
                args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
                runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))),
        context=context)
    handler.Handle(
        flow_plugin.ApiCreateFlowArgs(
            client_id=client_id2,
            flow=flow_plugin.ApiFlow(
                name=file.CollectSingleFile.__name__,
                args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
                runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))),
        context=context)

    handler = flow_plugin.ApiListScheduledFlowsHandler()
    args = flow_plugin.ApiListScheduledFlowsArgs(
        client_id=client_id1, creator=context.username)
    results = handler.Handle(args, context=context)

    self.assertEqual(results.scheduled_flows, [sf1, sf2])

  @db_test_lib.WithDatabase
  def testUnscheduleFlowRemovesScheduledFlow(self, db: abstract_db.Database):
    context = _CreateContext(db)
    client_id = db_test_utils.InitializeClient(db)

    handler = flow_plugin.ApiScheduleFlowHandler()
    sf1 = handler.Handle(
        flow_plugin.ApiCreateFlowArgs(
            client_id=client_id,
            flow=flow_plugin.ApiFlow(
                name=file.CollectSingleFile.__name__,
                args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
                runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))),
        context=context)
    sf2 = handler.Handle(
        flow_plugin.ApiCreateFlowArgs(
            client_id=client_id,
            flow=flow_plugin.ApiFlow(
                name=file.CollectSingleFile.__name__,
                args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
                runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))),
        context=context)

    handler = flow_plugin.ApiUnscheduleFlowHandler()
    args = flow_plugin.ApiUnscheduleFlowArgs(
        client_id=client_id,
        scheduled_flow_id=sf1.scheduled_flow_id)
    handler.Handle(args, context=context)

    handler = flow_plugin.ApiListScheduledFlowsHandler()
    args = flow_plugin.ApiListScheduledFlowsArgs(
        client_id=client_id, creator=context.username)
    results = handler.Handle(args, context=context)

    self.assertEqual(results.scheduled_flows, [sf2])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
