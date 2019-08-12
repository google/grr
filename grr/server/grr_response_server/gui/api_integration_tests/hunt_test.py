#!/usr/bin/env python
"""Tests for API client and hunts-related API calls."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import zipfile

from absl import app

from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.flows.general import processes as flows_processes
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.output_plugins import csv_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
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
      self.assertEqual(r.payload.pathspec.path, "/tmp/evil.txt")

  def testListLogsWithoutClientIds(self):
    hunt_id = self.StartHunt()

    client_ids = self.SetupClients(2)
    self.AssignTasksToClients(client_ids)

    data_store.REL_DB.WriteFlowLogEntries([
        rdf_flow_objects.FlowLogEntry(
            client_id=client_ids[0],
            flow_id=hunt_id,
            hunt_id=hunt_id,
            message="Sample message: foo."),
        rdf_flow_objects.FlowLogEntry(
            client_id=client_ids[1],
            flow_id=hunt_id,
            hunt_id=hunt_id,
            message="Sample message: bar.")
    ])

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
          parent_hunt_id=hunt_id)
      flow_obj = data_store.REL_DB.ReadFlowObject(client_ids[0], flow_id)
      flow_obj.flow_state = flow_obj.FlowState.ERROR
      flow_obj.error_message = "Error foo."
      data_store.REL_DB.UpdateFlow(client_ids[0], flow_id, flow_obj=flow_obj)

    with test_lib.FakeTime(55):
      flow_id = flow_test_lib.StartFlow(
          flows_processes.ListProcesses,
          client_id=client_ids[1],
          parent_hunt_id=hunt_id)
      flow_obj = data_store.REL_DB.ReadFlowObject(client_ids[1], flow_id)
      flow_obj.flow_state = flow_obj.FlowState.ERROR
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
    client_mocks = dict([(client_id,
                          flow_test_lib.CrashClientMock(client_id, self.token))
                         for client_id in client_ids])
    self.AssignTasksToClients(client_ids)
    hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, self.token)

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

  def testExportedResults(self):
    hunt_id = self.StartHunt()

    zip_stream = io.BytesIO()
    self.api.Hunt(hunt_id).GetExportedResults(
        csv_plugin.CSVInstantOutputPlugin.plugin_name).WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
