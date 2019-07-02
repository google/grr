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
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import compatibility
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_e2e_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiClientLibFlowTest(db_test_lib.RelationalDBEnabledMixin,
                           api_e2e_test_lib.ApiE2ETest):
  """Tests flows-related part of GRR Python API client library."""

  def testSearchWithNoClients(self):
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testSearchClientsWith2Clients(self):
    client_urns = sorted(self.SetupClients(2))

    clients = sorted(
        self.api.SearchClients(query="."), key=lambda c: c.client_id)
    self.assertLen(clients, 2)

    for i in range(2):
      self.assertEqual(clients[i].client_id, client_urns[i].Basename())
      self.assertEqual(clients[i].data.urn, client_urns[i])

  def testListFlowsFromClientRef(self):
    client_urn = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_urn)

    flows = list(self.api.Client(client_id=client_urn.Basename()).ListFlows())

    self.assertLen(flows, 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_id)
    self.assertEqual(flows[0].data.flow_id, flow_id)

  def testListFlowsFromClientObject(self):
    client_urn = self.SetupClient(0)
    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_urn)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    flows = list(client.ListFlows())

    self.assertLen(flows, 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_id)
    self.assertEqual(flows[0].data.flow_id, flow_id)

  def testCreateFlowWithUnicodeArguments(self):
    unicode_str = "🐊 🐢 🦎 🐍"

    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex=unicode_str, fetch_binaries=True)

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    got_flow = client_ref.Flow(flow_id=result_flow.flow_id).Get()
    self.assertEqual(got_flow.args.filename_regex, unicode_str)

  def testCreateFlowFromClientRef(self):
    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    if data_store.RelationalDBEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_urn.Basename())
      self.assertEmpty(flows)
    else:
      children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
      self.assertEmpty(list(children))

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    if data_store.RelationalDBEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_urn.Basename())
      self.assertLen(flows, 1)
      self.assertEqual(flows[0].args, args)
    else:
      children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
      self.assertLen(list(children), 1)
      result_flow_obj = aff4.FACTORY.Open(
          result_flow.data.urn, token=self.token)
      self.assertEqual(result_flow_obj.args, args)

  def testCreateFlowFromClientObject(self):
    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    if data_store.RelationalDBEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_urn.Basename())
      self.assertEmpty(flows)
    else:
      children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
      self.assertEmpty(list(children))

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    result_flow = client.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    if data_store.RelationalDBEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(client_urn.Basename())
      self.assertLen(flows, 1)
      self.assertEqual(flows[0].args, args)
    else:
      children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
      self.assertLen(list(children), 1)
      result_flow_obj = aff4.FACTORY.Open(
          result_flow.data.urn, token=self.token)
      self.assertEqual(result_flow_obj.args, args)

  def testListResultsForListProcessesFlow(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        RSS_size=42)

    client_urn = self.SetupClient(0)
    flow_urn = flow_test_lib.TestFlowHelper(
        compatibility.GetName(processes.ListProcesses),
        client_id=client_urn,
        client_mock=action_mocks.ListProcessesMock([process]),
        token=self.token)
    if isinstance(flow_urn, rdfvalue.RDFURN):
      flow_id = flow_urn.Basename()
    else:
      flow_id = flow_urn

    result_flow = self.api.Client(client_id=client_urn.Basename()).Flow(flow_id)
    results = list(result_flow.ListResults())

    self.assertLen(results, 1)
    self.assertEqual(process.AsPrimitiveProto(), results[0].payload)

  def testWaitUntilDoneReturnsWhenFlowCompletes(self):
    client_urn = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_urn)
    result_flow = self.api.Client(
        client_id=client_urn.Basename()).Flow(flow_id).Get()
    self.assertEqual(result_flow.data.state, result_flow.data.RUNNING)

    def ProcessFlow():
      time.sleep(1)
      client_mock = action_mocks.ListProcessesMock([])
      flow_test_lib.FinishAllFlowsOnClient(client_urn, client_mock=client_mock)

    t = threading.Thread(target=ProcessFlow)
    t.start()
    try:
      f = result_flow.WaitUntilDone()
      self.assertEqual(f.data.state, f.data.TERMINATED)
    finally:
      t.join()

  def testWaitUntilDoneRaisesWhenFlowFails(self):
    client_urn = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_urn)
    result_flow = self.api.Client(
        client_id=client_urn.Basename()).Flow(flow_id).Get()

    def ProcessFlow():
      time.sleep(1)
      if data_store.RelationalDBEnabled():
        flow_base.TerminateFlow(client_urn.Basename(), flow_id, "")
      else:
        with aff4.FACTORY.Open(
            client_urn.Add("flows").Add(flow_id), mode="rw",
            token=self.token) as fd:
          fd.GetRunner().Error("")

    t = threading.Thread(target=ProcessFlow)
    t.start()
    try:
      with self.assertRaises(grr_api_errors.FlowFailedError):
        result_flow.WaitUntilDone()
    finally:
      t.join()

  def testWaitUntilDoneRasiesWhenItTimesOut(self):
    client_urn = self.SetupClient(0)

    flow_id = flow_test_lib.StartFlow(
        processes.ListProcesses, client_id=client_urn)
    result_flow = self.api.Client(
        client_id=client_urn.Basename()).Flow(flow_id).Get()

    with self.assertRaises(grr_api_errors.PollTimeoutError):
      with utils.Stubber(grr_api_utils, "DEFAULT_POLL_TIMEOUT", 1):
        result_flow.WaitUntilDone()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
