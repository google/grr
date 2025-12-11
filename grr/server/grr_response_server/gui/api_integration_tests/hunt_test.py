#!/usr/bin/env python
"""Tests for API client and hunts-related API calls."""

import csv
import io
import stat
import zipfile

from absl import app

from grr_response_core.lib.rdfvalues import timeline as rdf_timeline
from grr_response_core.lib.util import chunked
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import timeline_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import processes as flows_processes
from grr_response_server.flows.general import timeline
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiClientLibHuntTest(
    hunt_test_lib.StandardHuntTestMixin,
    api_integration_test_lib.ApiIntegrationTest,
):
  """Tests flows-related part of GRR Python API client library."""

  def testListHunts(self):
    hunt_id = self.StartHunt()

    hs = list(self.api.ListHunts())
    self.assertLen(hs, 1)
    self.assertEqual(hs[0].hunt_id, hunt_id)
    self.assertEqual(hs[0].data.client_limit, 100)

  def testGetHunt(self):
    hunt_id = self.StartHunt()

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.hunt_id, hunt_id)
    self.assertEqual(h.data.name, "GenericHunt")

  def testModifyHunt(self):
    hunt_id = self.StartHunt(paused=True)

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.client_limit, 100)

    h = h.Modify(client_limit=200)
    self.assertEqual(h.data.client_limit, 200)

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.client_limit, 200)

  def testDeleteHunt(self):
    hunt_id = self.StartHunt(paused=True)

    self.api.Hunt(hunt_id).Delete()

    with self.assertRaises(db.UnknownHuntError):
      data_store.REL_DB.ReadHuntObject(hunt_id)

  def testStartHunt(self):
    hunt_id = self.StartHunt(paused=True)

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.state, h.data.PAUSED)

    h = h.Start()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

  def testStopHunt(self):
    hunt_id = self.StartHunt()

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = h.Stop()
    self.assertEqual(h.data.state, h.data.STOPPED)

    h = self.api.Hunt(hunt_id).Get()
    self.assertEqual(h.data.state, h.data.STOPPED)

  # TODO: Stop relying on default hunt constants.
  def testListResults(self):
    self.client_ids = self.SetupClients(5)
    with test_lib.FakeTime(42):
      hunt_id = self.StartHunt()
      self.RunHunt(failrate=-1)

    h = self.api.Hunt(hunt_id).Get()
    results = list(h.ListResults())

    client_ids = set(r.client.client_id for r in results)
    self.assertEqual(client_ids, set(self.client_ids))
    for r in results:
      self.assertEqual(r.timestamp, 42000000)
      self.assertEqual(r.payload.stat_entry.pathspec.path, "/tmp/evil.txt")

  def testListLogsWithoutClientIds(self):
    hunt_id = self.StartHunt()

    client_ids = self.SetupClients(2)
    self.AssignTasksToClients(client_ids)

    data_store.REL_DB.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_ids[0],
            flow_id=hunt_id,
            hunt_id=hunt_id,
            message="Sample message: foo.",
        )
    )
    data_store.REL_DB.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_ids[1],
            flow_id=hunt_id,
            hunt_id=hunt_id,
            message="Sample message: bar.",
        )
    )

    logs = list(self.api.Hunt(hunt_id).ListLogs())
    self.assertLen(logs, 2)

    self.assertEqual(logs[0].data.log_message, "Sample message: foo.")
    self.assertEqual(logs[1].data.log_message, "Sample message: bar.")

  def testListLogsWithClientIds(self):
    self.client_ids = self.SetupClients(2)
    hunt_id = self.StartHunt()
    self.RunHunt(failrate=-1)

    logs = list(self.api.Hunt(hunt_id).ListLogs())
    client_ids = set()
    for l in logs:
      client_ids.add(l.client.client_id)
    self.assertEqual(client_ids, set(self.client_ids))

  def testListErrors(self):
    hunt_id = self.StartHunt()
    client_ids = self.SetupClients(2)

    with test_lib.FakeTime(52):
      flow_id = flow_test_lib.StartFlow(
          flows_processes.ListProcesses,
          client_id=client_ids[0],
          parent=flow.FlowParent.FromHuntID(hunt_id),
      )
      flow_obj = data_store.REL_DB.ReadFlowObject(client_ids[0], flow_id)
      flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
      flow_obj.error_message = "Error foo."
      data_store.REL_DB.UpdateFlow(client_ids[0], flow_id, flow_obj=flow_obj)

    with test_lib.FakeTime(55):
      flow_id = flow_test_lib.StartFlow(
          flows_processes.ListProcesses,
          client_id=client_ids[1],
          parent=flow.FlowParent.FromHuntID(hunt_id),
      )
      flow_obj = data_store.REL_DB.ReadFlowObject(client_ids[1], flow_id)
      flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
      flow_obj.error_message = "Error bar."
      flow_obj.backtrace = "<some backtrace>"
      data_store.REL_DB.UpdateFlow(client_ids[1], flow_id, flow_obj=flow_obj)

    errors = list(self.api.Hunt(hunt_id).ListErrors())
    self.assertLen(errors, 2)

    self.assertEqual(errors[0].log_message, "Error foo.")
    self.assertEqual(errors[0].client.client_id, client_ids[0])
    self.assertEqual(errors[0].backtrace, "")

    self.assertEqual(errors[1].log_message, "Error bar.")
    self.assertEqual(errors[1].client.client_id, client_ids[1])
    self.assertEqual(errors[1].backtrace, "<some backtrace>")

  def testListCrashes(self):
    hunt_id = self.StartHunt()

    client_ids = self.SetupClients(2)
    client_mocks = dict([
        (client_id, flow_test_lib.CrashClientMock(client_id))
        for client_id in client_ids
    ])
    self.AssignTasksToClients(client_ids)
    hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks)

    crashes = list(self.api.Hunt(hunt_id).ListCrashes())
    self.assertLen(crashes, 2)

    self.assertCountEqual([x.client.client_id for x in crashes], client_ids)
    for c in crashes:
      self.assertEqual(c.crash_message, "Client killed during transaction")

  def testListClients(self):
    hunt_id = self.StartHunt()

    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids[:-1])
    self.RunHunt(client_ids=[client_ids[-1]], failrate=0)

    h = self.api.Hunt(hunt_id)
    clients = list(h.ListClients(h.CLIENT_STATUS_STARTED))
    self.assertLen(clients, 5)

    clients = list(h.ListClients(h.CLIENT_STATUS_OUTSTANDING))
    self.assertLen(clients, 4)

    clients = list(h.ListClients(h.CLIENT_STATUS_COMPLETED))
    self.assertLen(clients, 1)
    self.assertEqual(clients[0].client_id, client_ids[-1])

  def testGetClientCompletionStats(self):
    hunt_id = self.StartHunt(paused=True)

    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)

    client_stats = self.api.Hunt(hunt_id).GetClientCompletionStats()
    self.assertEmpty(client_stats.start_points)
    self.assertEmpty(client_stats.complete_points)

  def testGetStats(self):
    hunt_id = self.StartHunt()

    self.client_ids = self.SetupClients(5)
    self.RunHunt(failrate=-1)

    stats = self.api.Hunt(hunt_id).GetStats()
    self.assertLen(stats.worst_performers, 5)

  def testGetFilesArchive(self):
    hunt_id = self.StartHunt()

    zip_stream = io.BytesIO()
    self.api.Hunt(hunt_id).GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)

  @test_plugins.WithInstantOutputPluginProto(
      csv_instant_plugin.CSVInstantOutputPluginProto
  )
  def testExportedResults(self):
    hunt_id = self.StartHunt()

    zip_stream = io.BytesIO()
    self.api.Hunt(hunt_id).GetExportedResults(
        csv_instant_plugin.CSVInstantOutputPluginProto.plugin_name
    ).WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)

  def testGetCollectedTimelinesBody(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    fqdn = "foo.bar.quux"

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.fqdn = fqdn
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    hunt_id = "B1C2E3D4"

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.flow_name = timeline.TimelineFlow.__name__
    hunt_obj.hunt_state = hunts_pb2.Hunt.HuntState.PAUSED
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    flow_obj = flows_pb2.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = hunt_id
    flow_obj.flow_class_name = timeline.TimelineFlow.__name__
    flow_obj.parent_hunt_id = hunt_id
    data_store.REL_DB.WriteFlowObject(flow_obj)

    entry_1 = timeline_pb2.TimelineEntry()
    entry_1.path = "/bar/baz/quux".encode("utf-8")
    entry_1.ino = 5926273453
    entry_1.size = 13373
    entry_1.atime_ns = 111 * 10**9
    entry_1.mtime_ns = 222 * 10**9
    entry_1.ctime_ns = 333 * 10**9
    entry_1.mode = 0o664

    entry_2 = timeline_pb2.TimelineEntry()
    entry_2.path = "/bar/baz/quuz".encode("utf-8")
    entry_2.ino = 6037384564
    entry_2.size = 13374
    entry_2.atime_ns = 777 * 10**9
    entry_2.mtime_ns = 888 * 10**9
    entry_2.ctime_ns = 999 * 10**9
    entry_2.mode = 0o777

    entries = [entry_1, entry_2]
    blobs = list(rdf_timeline.SerializeTimelineEntryStream(entries))
    blob_ids = data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)

    result = timeline_pb2.TimelineResult()
    result.entry_batch_blob_ids.extend(list(map(bytes, blob_ids)))

    flow_result = flows_pb2.FlowResult()
    flow_result.client_id = client_id
    flow_result.flow_id = hunt_id
    flow_result.hunt_id = hunt_id
    flow_result.payload.Pack(result)

    data_store.REL_DB.WriteFlowResults([flow_result])

    buffer = io.BytesIO()
    self.api.Hunt(hunt_id).GetCollectedTimelines(
        api_timeline_pb2.ApiGetCollectedTimelineArgs.Format.BODY
    ).WriteToStream(buffer)

    with zipfile.ZipFile(buffer, mode="r") as archive:
      with archive.open(f"{client_id}_{fqdn}.body", mode="r") as file:
        content_file = file.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(content_file), delimiter="|"))
        self.assertLen(rows, 2)

        self.assertEqual(rows[0][1], "/bar/baz/quux")
        self.assertEqual(rows[0][2], "5926273453")
        self.assertEqual(rows[0][3], stat.filemode(0o664))
        self.assertEqual(rows[0][6], "13373")
        self.assertEqual(rows[0][7], "111")
        self.assertEqual(rows[0][8], "222")
        self.assertEqual(rows[0][9], "333")

        self.assertEqual(rows[1][1], "/bar/baz/quuz")
        self.assertEqual(rows[1][2], "6037384564")
        self.assertEqual(rows[1][3], stat.filemode(0o777))
        self.assertEqual(rows[1][6], "13374")
        self.assertEqual(rows[1][7], "777")
        self.assertEqual(rows[1][8], "888")
        self.assertEqual(rows[1][9], "999")

  def testGetCollectedTimelinesGzchunked(self):
    client_id = db_test_utils.InitializeClient(data_store.REL_DB)
    fqdn = "foo.bar.baz"

    snapshot = objects_pb2.ClientSnapshot()
    snapshot.client_id = client_id
    snapshot.knowledge_base.fqdn = fqdn
    data_store.REL_DB.WriteClientSnapshot(snapshot)

    hunt_id = "A0B1D2C3"

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.hunt_id = hunt_id
    hunt_obj.args.standard.flow_name = timeline.TimelineFlow.__name__
    hunt_obj.hunt_state = hunts_pb2.Hunt.HuntState.PAUSED
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    flow_obj = flows_pb2.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = hunt_id
    flow_obj.flow_class_name = timeline.TimelineFlow.__name__
    flow_obj.parent_hunt_id = hunt_id
    data_store.REL_DB.WriteFlowObject(flow_obj)

    entry_1 = timeline_pb2.TimelineEntry()
    entry_1.path = "/foo/bar".encode("utf-8")
    entry_1.ino = 7890178901
    entry_1.size = 4815162342
    entry_1.atime_ns = 123 * 10**9
    entry_1.mtime_ns = 234 * 10**9
    entry_1.ctime_ns = 567 * 10**9
    entry_1.mode = 0o654

    entry_2 = timeline_pb2.TimelineEntry()
    entry_2.path = "/foo/baz".encode("utf-8")
    entry_2.ino = 8765487654
    entry_2.size = 1337
    entry_2.atime_ns = 987 * 10**9
    entry_2.mtime_ns = 876 * 10**9
    entry_2.ctime_ns = 765 * 10**9
    entry_2.mode = 0o757

    entries = [entry_1, entry_2]
    blobs = list(rdf_timeline.SerializeTimelineEntryStream(entries))
    blob_ids = data_store.BLOBS.WriteBlobsWithUnknownHashes(blobs)

    result = timeline_pb2.TimelineResult()
    result.entry_batch_blob_ids.extend(list(map(bytes, blob_ids)))

    flow_result = flows_pb2.FlowResult()
    flow_result.client_id = client_id
    flow_result.flow_id = hunt_id
    flow_result.payload.Pack(result)

    data_store.REL_DB.WriteFlowResults([flow_result])

    buffer = io.BytesIO()

    fmt = api_timeline_pb2.ApiGetCollectedTimelineArgs.Format.RAW_GZCHUNKED
    self.api.Hunt(hunt_id).GetCollectedTimelines(fmt).WriteToStream(buffer)

    with zipfile.ZipFile(buffer, mode="r") as archive:
      with archive.open(f"{client_id}_{fqdn}.gzchunked", mode="r") as file:
        chunks = chunked.ReadAll(file)
        entries = list(rdf_timeline.DeserializeTimelineEntryStream(chunks))
        self.assertEqual(entries, [entry_1, entry_2])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
