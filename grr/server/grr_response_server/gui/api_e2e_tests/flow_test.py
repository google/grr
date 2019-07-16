#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for API client and flows-related API calls."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time

from absl import app
from future.builtins import range

from grr_api_client import errors as grr_api_errors
from grr_api_client import utils as grr_api_utils
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiClientLibFlowTest(api_e2e_test_lib.ApiE2ETest):
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
        token=self.token)

    result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
    results = list(result_flow.ListResults())

    self.assertLen(results, 1)
    self.assertEqual(process.AsPrimitiveProto(), results[0].payload)

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
      with utils.Stubber(grr_api_utils, "DEFAULT_POLL_TIMEOUT", 1):
        result_flow.WaitUntilDone()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
