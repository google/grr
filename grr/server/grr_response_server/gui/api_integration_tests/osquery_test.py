#!/usr/bin/env python
# Lint as: python3
"""Integration tests for the Osquery flow, its api client and api endpoints."""
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import osquery_test_lib

from grr_response_proto import osquery_pb2
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2


class OsqueryIntegrationTest(api_integration_test_lib.ApiIntegrationTest):
  def testFlowRuns(self):
    client_id = self.SetupClient(0)
    client_ref = self.api.Client(client_id=client_id)

    flow_args = self.api.types.CreateFlowArgs("OsqueryFlow")

    with osquery_test_lib.FakeOsqueryiOutput(stdout="dummy output", stderr=""):
      flow = client_ref.CreateFlow("OsqueryFlow", flow_args)
      flow_with_data = flow.Get()

    import pdb; pdb.set_trace()
