#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for API client and flows-related API calls."""

import io
import threading
import time
from typing import Iterable
import zipfile

from absl import app

from grr_api_client import errors as grr_api_errors
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.parsers import abstract as parser
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_proto.api import flow_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import parser_test_lib
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib


class ApiClientLibFlowTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests flows-related part of GRR Python API client library."""

  def testSearchWithNoClients(self):
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testSearchClientsWith2Clients(self):
    client_ids = sorted(self.SetupClients(2))

    clients = sorted(
        self.api.SearchClients(query="."), key=lambda c: c.client_id)
    self.assertLen(clients, 2)

    for i in range(2):
      self.assertEqual(clients[i].client_id, client_ids[i])
      self.assertEqual(clients[i].data.urn, "aff4:/%s" % client_ids[i])

  def testListFlowsFromClientRef(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)

    flows = list(self.api.Client(client_id=client_id).ListFlows())

    self.assertLen(flows, 1)
    self.assertEqual(flows[0].client_id, client_id)
    self.assertEqual(flows[0].flow_id, flow_id)
    self.assertEqual(flows[0].data.flow_id, flow_id)

  def testListFlowsFromClientObject(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)

    client = self.api.Client(client_id=client_id).Get()
    flows = list(client.ListFlows())

    self.assertLen(flows, 1)
    self.assertEqual(flows[0].client_id, client_id)
    self.assertEqual(flows[0].flow_id, flow_id)
    self.assertEqual(flows[0].data.flow_id, flow_id)

  def testCreateFlowWithUnicodeArguments(self):
    unicode_str = "🐊 🐢 🦎 🐍"

    client_id = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex=unicode_str, fetch_binaries=True)

    client_ref = self.api.Client(client_id=client_id)
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    got_flow = client_ref.Flow(flow_id=result_flow.flow_id).Get()
    self.assertEqual(got_flow.args.filename_regex, unicode_str)

  def testCreateFlowFromClientRef(self):
    client_id = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertEmpty(flows)

    client_ref = self.api.Client(client_id=client_id)
    client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].args, args)

  def testCreateFlowFromClientObject(self):
    client_id = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertEmpty(flows)

    client = self.api.Client(client_id=client_id).Get()
    client.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].args, args)

  def testRunInterrogateFlow(self):
    client_id = self.SetupClient(0)
    client_ref = self.api.Client(client_id=client_id)
    result_flow = client_ref.Interrogate()

    self.assertEqual(result_flow.data.client_id, client_id)
    self.assertEqual(result_flow.data.name, "Interrogate")

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].flow_class_name, "Interrogate")

  def testListResultsForListProcessesFlow(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        RSS_size=42)

    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.TestFlowHelper(
        compatibility.GetName(processes.ListProcesses),
        client_id=client_id,
        client_mock=action_mocks.ListProcessesMock([process]),
        creator=self.test_username)

    result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
    results = list(result_flow.ListResults())

    self.assertLen(results, 1)
    self.assertEqual(process.AsPrimitiveProto(), results[0].payload)

  def testListParsedFlowResults(self):
    client_id = self.SetupClient(0)
    flow_id = "4815162342ABCDEF"

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = flow_id
    flow.flow_class_name = collectors.ArtifactCollectorFlow.__name__
    flow.args = rdf_artifacts.ArtifactCollectorFlowArgs(apply_parsers=False)
    flow.persistent_data = {"knowledge_base": rdf_client.KnowledgeBase()}
    data_store.REL_DB.WriteFlowObject(flow)

    result = rdf_flow_objects.FlowResult()
    result.client_id = client_id
    result.flow_id = flow_id
    result.tag = "artifact:Echo"

    response = rdf_client_action.ExecuteResponse()
    response.stderr = "Lorem ipsum.".encode("utf-8")

    result.payload = response
    data_store.REL_DB.WriteFlowResults([result])

    response = rdf_client_action.ExecuteResponse()
    response.stderr = "Dolor sit amet.".encode("utf-8")

    result.payload = response
    data_store.REL_DB.WriteFlowResults([result])

    class StderrToStdoutParser(
        parser.SingleResponseParser[rdf_client_action.ExecuteResponse]):

      supported_artifacts = ["Echo"]

      def ParseResponse(
          self,
          knowledge_base: rdf_client.KnowledgeBase,
          response: rdf_client_action.ExecuteResponse,
      ) -> Iterable[rdf_client_action.ExecuteResponse]:
        del knowledge_base  # Unused.

        if not isinstance(response, rdf_client_action.ExecuteResponse):
          raise TypeError(f"Unexpected response type: {type(response)}")

        parsed_response = rdf_client_action.ExecuteResponse()
        parsed_response.stdout = response.stderr

        return [parsed_response]

    with parser_test_lib._ParserContext("StderrToStdout", StderrToStdoutParser):
      results = self.api.Client(client_id).Flow(flow_id).ListParsedResults()

    stdouts = [result.payload.stdout.decode("utf-8") for result in results]
    self.assertLen(stdouts, 2)
    self.assertEqual(stdouts[0], "Lorem ipsum.")
    self.assertEqual(stdouts[1], "Dolor sit amet.")

  def testListFlowApplicableParsers(self):
    client_id = self.SetupClient(0)
    flow_id = "4815162342ABCDEF"

    flow = rdf_flow_objects.Flow()
    flow.client_id = client_id
    flow.flow_id = flow_id
    flow.flow_class_name = collectors.ArtifactCollectorFlow.__name__
    flow.args = rdf_artifacts.ArtifactCollectorFlowArgs(apply_parsers=False)
    data_store.REL_DB.WriteFlowObject(flow)

    result = rdf_flow_objects.FlowResult()
    result.client_id = client_id
    result.flow_id = flow_id
    result.tag = "artifact:Fake"
    result.payload = rdf_client_action.ExecuteResponse(stderr=b"foobar")
    data_store.REL_DB.WriteFlowResults([result])

    class FakeParser(parser.SingleResponseParser[None]):

      supported_artifacts = ["Fake"]

      def ParseResponse(
          self,
          knowledge_base: rdf_client.KnowledgeBase,
          response: rdfvalue.RDFValue,
      ) -> Iterable[None]:
        raise NotImplementedError()

    with parser_test_lib._ParserContext("Fake", FakeParser):
      results = self.api.Client(client_id).Flow(flow_id).ListApplicableParsers()

    self.assertLen(results.parsers, 1)

    result = results.parsers[0]
    self.assertEqual(result.name, "Fake")
    self.assertEqual(result.type, flow_pb2.ApiParserDescriptor.SINGLE_RESPONSE)

  def testWaitUntilDoneReturnsWhenFlowCompletes(self):
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)
    result_flow = self.api.Client(client_id=client_id).Flow(flow_id).Get()
    self.assertEqual(result_flow.data.state, result_flow.data.RUNNING)

    def ProcessFlow():
      time.sleep(1)
      client_mock = action_mocks.ListProcessesMock([])
      flow_test_lib.FinishAllFlowsOnClient(client_id, client_mock=client_mock)

    t = threading.Thread(target=ProcessFlow)
    t.start()
    try:
      f = result_flow.WaitUntilDone()
      self.assertEqual(f.data.state, f.data.TERMINATED)
    finally:
      t.join()

  def testWaitUntilDoneRaisesWhenFlowFails(self):
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)
    result_flow = self.api.Client(client_id=client_id).Flow(flow_id).Get()

    def ProcessFlow():
      time.sleep(1)
      flow_base.TerminateFlow(client_id, flow_id, "")

    t = threading.Thread(target=ProcessFlow)
    t.start()
    try:
      with self.assertRaises(grr_api_errors.FlowFailedError):
        result_flow.WaitUntilDone()
    finally:
      t.join()

  def testWaitUntilDoneRasiesWhenItTimesOut(self):
    client_id = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)
    result_flow = self.api.Client(client_id=client_id).Flow(flow_id).Get()

    with self.assertRaises(grr_api_errors.PollTimeoutError):
      result_flow.WaitUntilDone(timeout=1)

  def _SetupFlowWithStatEntryResults(self):
    client_id = self.SetupClient(0)
    # Start a flow. The exact type of the flow doesn't matter:
    # we'll add results manually.
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)

    data_store.REL_DB.WriteFlowResults([
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(
                    path="/foo/bar1",
                    pathtype=rdf_paths.PathSpec.PathType.OS))),
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(
                    path="/foo/bar2",
                    pathtype=rdf_paths.PathSpec.PathType.OS))),
    ])

    return client_id, flow_id

  def testGetFilesArchiveGeneratesCorrectArchive(self):
    client_id, flow_id = self._SetupFlowWithStatEntryResults()

    blob_size = 1024 * 1024 * 4
    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(blob_size, "ab")
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.OS(client_id, ["foo", "bar1"]), blob_refs, blob_data)

    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(blob_size, "cd")
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.OS(client_id, ["foo", "bar2"]), blob_refs, blob_data)

    zip_stream = io.BytesIO()
    self.api.Client(client_id).Flow(flow_id).GetFilesArchive().WriteToStream(
        zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    prefix = "%s_flow_ListProcesses_%s" % (client_id, flow_id)
    namelist = zip_fd.namelist()
    self.assertCountEqual(namelist, [
        "%s/MANIFEST" % prefix,
        "%s/%s/client_info.yaml" % (prefix, client_id),
        "%s/%s/fs/os/foo/bar1" % (prefix, client_id),
        "%s/%s/fs/os/foo/bar2" % (prefix, client_id),
    ])

    for info in zip_fd.infolist():
      self.assertGreater(info.compress_size, 0)

  def testGetFilesArchiveFailsWhenFirstFileBlobIsMissing(self):
    client_id, flow_id = self._SetupFlowWithStatEntryResults()

    _, blob_refs = vfs_test_lib.GenerateBlobRefs(10, "0")
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.OS(client_id, ["foo", "bar1"]), blob_refs, [])

    zip_stream = io.BytesIO()
    with self.assertRaisesRegex(grr_api_errors.UnknownError,
                                "Could not find one of referenced blobs"):
      self.api.Client(client_id).Flow(flow_id).GetFilesArchive().WriteToStream(
          zip_stream)

  def testGetFilesArchiveDropsStreamingResponsesWhenSecondFileBlobIsMissing(
      self):
    client_id, flow_id = self._SetupFlowWithStatEntryResults()

    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(1024 * 1024 * 4, "abc")
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        db.ClientPath.OS(client_id, ["foo", "bar1"]), blob_refs, blob_data[0:2])

    zip_stream = io.BytesIO()
    timestamp = rdfvalue.RDFDatetime.Now()
    self.api.Client(client_id).Flow(flow_id).GetFilesArchive().WriteToStream(
        zip_stream)

    with self.assertRaises(zipfile.BadZipfile):
      zipfile.ZipFile(zip_stream)

    # Check that notification was pushed indicating the failure to the user.
    pending_notifications = list(self.api.GrrUser().ListPendingNotifications(
        timestamp=timestamp.AsMicrosecondsSinceEpoch()))
    self.assertLen(pending_notifications, 1)
    self.assertEqual(
        pending_notifications[0].data.notification_type,
        int(rdf_objects.UserNotification.Type
            .TYPE_FILE_ARCHIVE_GENERATION_FAILED))
    self.assertEqual(pending_notifications[0].data.reference.type,
                     pending_notifications[0].data.reference.FLOW)
    self.assertEqual(pending_notifications[0].data.reference.flow.client_id,
                     client_id)
    self.assertEqual(pending_notifications[0].data.reference.flow.flow_id,
                     flow_id)

  def testClientReprContainsClientId(self):
    client_id = self.SetupClient(0)
    client_ref = self.api.Client(client_id=client_id)
    self.assertIn(client_id, repr(client_ref))
    self.assertIn(client_id, repr(client_ref.Get()))

  def testFlowReprContainsMetadata(self):
    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_id)

    flow_ref = self.api.Client(client_id=client_id).Flow(flow_id)
    self.assertIn(client_id, repr(flow_ref))
    self.assertIn(flow_id, repr(flow_ref))

    flow = flow_ref.Get()
    self.assertIn(client_id, repr(flow))
    self.assertIn(flow_id, repr(flow))
    self.assertIn("ListProcesses", repr(flow))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
