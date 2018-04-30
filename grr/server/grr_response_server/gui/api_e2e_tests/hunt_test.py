#!/usr/bin/env python
"""Tests for API client and hunts-related API calls."""

import StringIO
import zipfile


from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.server.grr_response_server.output_plugins import csv_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiClientLibHuntTest(api_e2e_test_lib.ApiE2ETest,
                           hunt_test_lib.StandardHuntTestMixin):
  """Tests flows-related part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibHuntTest, self).setUp()
    self.hunt_obj = self.CreateHunt()

  def testListHunts(self):
    hs = list(self.api.ListHunts())
    self.assertEqual(len(hs), 1)
    self.assertEqual(hs[0].hunt_id, self.hunt_obj.urn.Basename())
    self.assertEqual(hs[0].data.name, "GenericHunt")

  def testGetHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.hunt_id, self.hunt_obj.urn.Basename())
    self.assertEqual(h.data.name, "GenericHunt")

  def testModifyHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.client_limit, 100)

    h = h.Modify(client_limit=200)
    self.assertEqual(h.data.client_limit, 200)

    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.client_limit, 200)

  def testDeleteHunt(self):
    self.api.Hunt(self.hunt_obj.urn.Basename()).Delete()

    obj = aff4.FACTORY.Open(self.hunt_obj.urn, token=self.token)
    self.assertEqual(obj.__class__, aff4.AFF4Volume)

  def testStartHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.PAUSED)

    h = h.Start()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

  def testStopHunt(self):
    hunt_urn = self.StartHunt()

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = h.Stop()
    self.assertEqual(h.data.state, h.data.STOPPED)

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STOPPED)

  def testListResults(self):
    self.client_ids = self.SetupClients(5)
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt()
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    results = list(h.ListResults())

    client_ids = set(r.client.client_id for r in results)
    self.assertEqual(client_ids, set(x.Basename() for x in self.client_ids))
    for r in results:
      self.assertEqual(r.timestamp, 42000000)
      self.assertEqual(r.payload.pathspec.path, "/tmp/evil.txt")

  def testListLogsWithoutClientIds(self):
    self.hunt_obj.Log("Sample message: foo.")
    self.hunt_obj.Log("Sample message: bar.")

    logs = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListLogs())
    self.assertEqual(len(logs), 2)

    self.assertEqual(logs[0].client, None)
    self.assertEqual(logs[0].data.log_message, "Sample message: foo.")
    self.assertEqual(logs[1].client, None)
    self.assertEqual(logs[1].data.log_message, "Sample message: bar.")

  def testListLogsWithClientIds(self):
    self.client_ids = self.SetupClients(2)
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    logs = list(self.api.Hunt(hunt_urn.Basename()).ListLogs())
    client_ids = set()
    for l in logs:
      client_ids.add(l.client.client_id)
    self.assertEqual(client_ids, set(x.Basename() for x in self.client_ids))

  def testListErrors(self):
    client_urn_1 = rdf_client.ClientURN("C.0000111122223333")
    with test_lib.FakeTime(52):
      self.hunt_obj.LogClientError(client_urn_1, "Error foo.")

    client_urn_2 = rdf_client.ClientURN("C.1111222233334444")
    with test_lib.FakeTime(55):
      self.hunt_obj.LogClientError(client_urn_2, "Error bar.",
                                   "<some backtrace>")

    errors = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListErrors())
    self.assertEqual(len(errors), 2)

    self.assertEqual(errors[0].log_message, "Error foo.")
    self.assertEqual(errors[0].client.client_id, client_urn_1.Basename())
    self.assertEqual(errors[0].backtrace, "")

    self.assertEqual(errors[1].log_message, "Error bar.")
    self.assertEqual(errors[1].client.client_id, client_urn_2.Basename())
    self.assertEqual(errors[1].backtrace, "<some backtrace>")

  def testListCrashes(self):
    self.hunt_obj.Run()

    client_ids = self.SetupClients(2)
    client_mocks = dict([(client_id,
                          flow_test_lib.CrashClientMock(client_id, self.token))
                         for client_id in client_ids])
    self.AssignTasksToClients(client_ids)
    hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False,
                                                  self.token)

    crashes = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListCrashes())
    self.assertEqual(len(crashes), 2)

    self.assertEqual(
        set(x.client.client_id for x in crashes),
        set(x.Basename() for x in client_ids))
    for c in crashes:
      self.assertEqual(c.crash_message, "Client killed during transaction")

  def testListClients(self):
    self.hunt_obj.Run()
    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)
    self.RunHunt(client_ids=[client_ids[-1]], failrate=0)

    h = self.api.Hunt(self.hunt_obj.urn.Basename())
    clients = list(h.ListClients(h.CLIENT_STATUS_STARTED))
    self.assertEqual(len(clients), 5)

    clients = list(h.ListClients(h.CLIENT_STATUS_OUTSTANDING))
    self.assertEqual(len(clients), 4)

    clients = list(h.ListClients(h.CLIENT_STATUS_COMPLETED))
    self.assertEqual(len(clients), 1)
    self.assertEqual(clients[0].client_id, client_ids[-1].Basename())

  def testGetClientCompletionStats(self):
    self.hunt_obj.Run()
    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)

    client_stats = self.api.Hunt(
        self.hunt_obj.urn.Basename()).GetClientCompletionStats()
    self.assertEqual(len(client_stats.start_points), 0)
    self.assertEqual(len(client_stats.complete_points), 0)

  def testGetStats(self):
    self.client_ids = self.SetupClients(5)
    self.hunt_obj.Run()
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    stats = self.api.Hunt(self.hunt_obj.urn.Basename()).GetStats()
    self.assertEqual(len(stats.worst_performers), 5)

  def testGetFilesArchive(self):
    zip_stream = StringIO.StringIO()
    self.api.Hunt(self.hunt_obj.urn.Basename()).GetFilesArchive().WriteToStream(
        zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)

  def testExportedResults(self):
    zip_stream = StringIO.StringIO()
    self.api.Hunt(self.hunt_obj.urn.Basename()).GetExportedResults(
        csv_plugin.CSVInstantOutputPlugin.plugin_name).WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
