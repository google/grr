#!/usr/bin/env python
"""This modules contains regression tests for clients API handlers."""


import psutil

from grr.gui import api_regression_test_lib
from grr.gui.api_plugins import client as client_plugin

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.server import aff4
from grr.server import flow
from grr.server import queue_manager
from grr.server.aff4_objects import aff4_grr

from grr.server.aff4_objects import stats as aff4_stats
from grr.server.flows.general import processes
from grr.server.hunts import standard_test
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiSearchClientsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "SearchClients"
  handler = client_plugin.ApiSearchClientsHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

      # Delete the certificate as it's being regenerated every time the
      # client is created.
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

      self.Check(
          "SearchClients",
          args=client_plugin.ApiSearchClientsArgs(query=client_id.Basename()))


class ApiGetClientHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetClient"
  handler = client_plugin.ApiGetClientHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.Set(grr_client.Schema.MEMORY_SIZE(4294967296))
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    self.Check(
        "GetClient",
        args=client_plugin.ApiGetClientArgs(client_id=client_id.Basename()))


class ApiGetClientVersionsRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetClientVersions"
  handler = client_plugin.ApiGetClientVersionsHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.Set(grr_client.Schema.MEMORY_SIZE(4294967296))
        # Delete the certificate as it's being regenerated every time the
        # client is created.
        grr_client.DeleteAttribute(grr_client.Schema.CERT)

    with test_lib.FakeTime(45):
      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.Set(grr_client.Schema.HOSTNAME("some-other-hostname.org"))

    with test_lib.FakeTime(47):
      for mode in ["FULL", "DIFF"]:
        self.Check(
            "GetClientVersions",
            args=client_plugin.ApiGetClientVersionsArgs(
                client_id=client_id.Basename(), mode=mode))
        self.Check(
            "GetClientVersions",
            args=client_plugin.ApiGetClientVersionsArgs(
                client_id=client_id.Basename(),
                end=rdfvalue.RDFDatetime().FromSecondsFromEpoch(44),
                mode=mode))
        self.Check(
            "GetClientVersions",
            args=client_plugin.ApiGetClientVersionsArgs(
                client_id=client_id.Basename(),
                start=rdfvalue.RDFDatetime().FromSecondsFromEpoch(44),
                end=rdfvalue.RDFDatetime().FromSecondsFromEpoch(46),
                mode=mode))


class ApiGetLastClientIPAddressHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetLastClientIPAddress"
  handler = client_plugin.ApiGetLastClientIPAddressHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

      with aff4.FACTORY.Open(
          client_id, mode="rw", token=self.token) as grr_client:
        grr_client.Set(grr_client.Schema.CLIENT_IP("192.168.100.42"))

    self.Check(
        "GetLastClientIPAddress",
        args=client_plugin.ApiGetLastClientIPAddressArgs(
            client_id=client_id.Basename()))


class ApiListClientsLabelsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListClientsLabels"
  handler = client_plugin.ApiListClientsLabelsHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_ids = self.SetupClients(2)

      with aff4.FACTORY.Open(
          client_ids[0], mode="rw", token=self.token) as grr_client:
        grr_client.AddLabel("foo")

      with aff4.FACTORY.Open(
          client_ids[1], mode="rw", token=self.token) as grr_client:
        grr_client.AddLabel("bar")

    self.Check("ListClientsLabels")


class ApiListKbFieldsHandlerTest(api_regression_test_lib.ApiRegressionTest):

  api_method = "ListKbFields"
  handler = client_plugin.ApiListKbFieldsHandler

  def Run(self):
    self.Check("ListKbFields")


class ApiListClientCrashesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    standard_test.StandardHuntTestMixin):

  api_method = "ListClientCrashes"
  handler = client_plugin.ApiListClientCrashesHandler

  def Run(self):
    client_ids = self.SetupClients(1)
    client_id = client_ids[0]
    client_mock = flow_test_lib.CrashClientMock(client_id, self.token)

    with test_lib.FakeTime(42):
      with self.CreateHunt(description="the hunt") as hunt_obj:
        hunt_obj.Run()

    with test_lib.FakeTime(45):
      self.AssignTasksToClients(client_ids)
      hunt_test_lib.TestHuntHelperWithMultipleMocks({
          client_id: client_mock
      }, False, self.token)

    crashes = aff4_grr.VFSGRRClient.CrashCollectionForCID(client_id)
    crash = list(crashes)[0]
    session_id = crash.session_id.Basename()
    replace = {hunt_obj.urn.Basename(): "H:123456", session_id: "H:11223344"}

    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(
            client_id=client_id.Basename()),
        replace=replace)
    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(
            client_id=client_id.Basename(), count=1),
        replace=replace)
    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(
            client_id=client_id.Basename(), offset=1, count=1),
        replace=replace)


class ApiListClientActionRequestsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    standard_test.StandardHuntTestMixin):

  api_method = "ListClientActionRequests"
  handler = client_plugin.ApiListClientActionRequestsHandler

  def Run(self):
    client_id = self.SetupClient(0)

    replace = {}
    with test_lib.FakeTime(42):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=client_id,
          flow_name=processes.ListProcesses.__name__,
          token=self.token)
      replace[flow_urn.Basename()] = "F:123456"

      test_process = client_test_lib.MockWindowsProcess(name="test_process")
      with utils.Stubber(psutil, "Process", lambda: test_process):
        # Here we emulate a mock client with no actions (None) that
        # should produce an error.
        mock = flow_test_lib.MockClient(client_id, None, token=self.token)
        while mock.Next():
          pass

    manager = queue_manager.QueueManager(token=self.token)
    requests_responses = manager.FetchRequestsAndResponses(flow_urn)
    for request, responses in requests_responses:
      replace[str(request.request.task_id)] = "42"
      for response in responses:
        replace[str(response.task_id)] = "43"

    self.Check(
        "ListClientActionRequests",
        args=client_plugin.ApiListClientActionRequestsArgs(
            client_id=client_id.Basename()),
        replace=replace)
    self.Check(
        "ListClientActionRequests",
        args=client_plugin.ApiListClientActionRequestsArgs(
            client_id=client_id.Basename(), fetch_responses=True),
        replace=replace)


class ApiGetClientLoadStatsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetClientLoadStats"
  handler = client_plugin.ApiGetClientLoadStatsHandler

  def FillClientStats(self, client_id):
    with aff4.FACTORY.Create(
        client_id.Add("stats"),
        aff4_type=aff4_stats.ClientStats,
        token=self.token,
        mode="rw") as stats_fd:

      for i in range(6):
        with test_lib.FakeTime((i + 1) * 10):
          timestamp = int((i + 1) * 10 * 1e6)
          st = rdf_client.ClientStats()

          sample = rdf_client.CpuSample(
              timestamp=timestamp,
              user_cpu_time=10 + i,
              system_cpu_time=20 + i,
              cpu_percent=10 + i)
          st.cpu_samples.Append(sample)

          sample = rdf_client.IOSample(
              timestamp=timestamp, read_bytes=10 + i, write_bytes=10 + i * 2)
          st.io_samples.Append(sample)

          stats_fd.AddAttribute(stats_fd.Schema.STATS(st))

  def Run(self):
    client_id = self.SetupClient(0)
    self.FillClientStats(client_id)

    self.Check(
        "GetClientLoadStats",
        args=client_plugin.ApiGetClientLoadStatsArgs(
            client_id=client_id.Basename(),
            metric="CPU_PERCENT",
            start=rdfvalue.RDFDatetime().FromSecondsFromEpoch(10),
            end=rdfvalue.RDFDatetime().FromSecondsFromEpoch(21)))
    self.Check(
        "GetClientLoadStats",
        args=client_plugin.ApiGetClientLoadStatsArgs(
            client_id=client_id.Basename(),
            metric="IO_WRITE_BYTES",
            start=rdfvalue.RDFDatetime().FromSecondsFromEpoch(10),
            end=rdfvalue.RDFDatetime().FromSecondsFromEpoch(21)))


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
