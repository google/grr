#!/usr/bin/env python
"""Tests for API client and flows-related API calls."""

import threading
import time


from grr_api_client import errors as grr_api_errors
from grr_api_client import utils as grr_api_utils
from grr.lib import flags
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import processes
from grr.server.grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiClientLibFlowTest(api_e2e_test_lib.ApiE2ETest):
  """Tests flows-related part of GRR Python API client library."""

  def testSearchWithNoClients(self):
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testSearchClientsWith2Clients(self):
    client_urns = sorted(self.SetupClients(2))

    clients = sorted(
        self.api.SearchClients(query="."), key=lambda c: c.client_id)
    self.assertEqual(len(clients), 2)

    for i in range(2):
      self.assertEqual(clients[i].client_id, client_urns[i].Basename())
      self.assertEqual(clients[i].data.urn, client_urns[i])

  def testListFlowsFromClientRef(self):
    client_urn = self.SetupClient(0)
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)

    flows = list(self.api.Client(client_id=client_urn.Basename()).ListFlows())

    self.assertEqual(len(flows), 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_urn.Basename())
    self.assertEqual(flows[0].data.urn, flow_urn)

  def testListFlowsFromClientObject(self):
    client_urn = self.SetupClient(0)
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    flows = list(client.ListFlows())

    self.assertEqual(len(flows), 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_urn.Basename())
    self.assertEqual(flows[0].data.urn, flow_urn)

  def testCreateFlowFromClientRef(self):
    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data.urn, token=self.token)
    self.assertEqual(result_flow_obj.args, args)

  def testCreateFlowFromClientObject(self):
    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    result_flow = client.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data.urn, token=self.token)
    self.assertEqual(result_flow_obj.args, args)

  def testListResultsForListProcessesFlow(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        RSS_size=42)

    client_urn = self.SetupClient(0)
    client_mock = action_mocks.ListProcessesMock([process])

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    flow_test_lib.TestFlowHelper(
        flow_urn, client_mock, client_id=client_urn, token=self.token)

    result_flow = self.api.Client(client_id=client_urn.Basename()).Flow(
        flow_urn.Basename())
    results = list(result_flow.ListResults())

    self.assertEqual(len(results), 1)
    self.assertEqual(process.AsPrimitiveProto(), results[0].payload)

  def testWaitUntilDoneReturnsWhenFlowCompletes(self):
    client_urn = self.SetupClient(0)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    result_flow = self.api.Client(client_id=client_urn.Basename()).Flow(
        flow_urn.Basename()).Get()
    self.assertEqual(result_flow.data.state, result_flow.data.RUNNING)

    def ProcessFlow():
      time.sleep(1)
      client_mock = action_mocks.ListProcessesMock([])
      flow_test_lib.TestFlowHelper(
          flow_urn, client_mock, client_id=client_urn, token=self.token)

    threading.Thread(target=ProcessFlow).start()
    f = result_flow.WaitUntilDone()
    self.assertEqual(f.data.state, f.data.TERMINATED)

  def testWaitUntilDoneRaisesWhenFlowFails(self):
    client_urn = self.SetupClient(0)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    result_flow = self.api.Client(client_id=client_urn.Basename()).Flow(
        flow_urn.Basename()).Get()

    def ProcessFlow():
      time.sleep(1)
      with aff4.FACTORY.Open(flow_urn, mode="rw", token=self.token) as fd:
        fd.GetRunner().Error("")

    threading.Thread(target=ProcessFlow).start()
    with self.assertRaises(grr_api_errors.FlowFailedError):
      result_flow.WaitUntilDone()

  def testWaitUntilDoneRasiesWhenItTimesOut(self):
    client_urn = self.SetupClient(0)

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    result_flow = self.api.Client(client_id=client_urn.Basename()).Flow(
        flow_urn.Basename()).Get()

    with self.assertRaises(grr_api_errors.PollTimeoutError):
      with utils.Stubber(grr_api_utils, "DEFAULT_POLL_TIMEOUT", 1):
        result_flow.WaitUntilDone()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
