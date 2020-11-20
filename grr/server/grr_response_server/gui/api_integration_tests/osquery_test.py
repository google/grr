# Lint as: python3
"""Integration tests for the Osquery flow, its API client and API endpoints."""
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.flows.general import osquery as osquery_flow
from grr.test_lib import osquery_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import action_mocks
from grr_response_client.client_actions import osquery as osquery_action
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_api_client import utils

import json


class OsqueryResultsExportTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests exporting of Osquery results using functionality in the API client"""

  def _RunOsqueryExportResults(self, stdout: str) -> utils.BinaryChunkIterator:
    client_id = self.SetupClient(0)

    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      flow_id = flow_test_lib.TestFlowHelper(
        osquery_flow.OsqueryFlow.__name__,
        action_mocks.ActionMock(osquery_action.Osquery),
        client_id=client_id,
        token=self.token,
        query="doesn't matter")
      result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
      result_flow.WaitUntilDone()

    format_csv = api_osquery_pb2.ApiGetOsqueryResultsArgs.Format.CSV
    return result_flow.GetOsqueryResults(format_csv)

  def testExportSomeResults(self):

    stdout = """
    [
      { "foo": "quux", "bar": "norf", "baz": "thud" },
      { "foo": "blargh", "bar": "plugh", "baz": "ztesch" }
    ]
    """
    expected_text = "foo,bar,baz\r\nquux,norf,thud\r\nblargh,plugh,ztesch\r\n"
    expected_bytes = expected_text.encode("utf-8")

    results_iterator = self._RunOsqueryExportResults(stdout)

    csv_bytes = next(results_iterator)
    self.assertEqual(expected_bytes, csv_bytes)

  def testExportNoRows(self):
    stdout = """
    [

    ]
    """

    results_iterator = self._RunOsqueryExportResults(stdout)
    csv_bytes = next(results_iterator)

    expected_text = "\r\n"
    expected_bytes = expected_text.encode("utf-8")
    self.assertEqual(expected_bytes, csv_bytes)

  def testExportUnicodeCharacters(self):
    stdout = """
    [
      { "🇬 🇷 🇷": "🔝🔝🔝"}
    ]
    """

    results_iterator = self._RunOsqueryExportResults(stdout)
    csv_bytes = next(results_iterator)

    expected_text = "🇬 🇷 🇷\r\n🔝🔝🔝\r\n"
    expected_bytes = expected_text.encode("utf-8")
    self.assertEqual(expected_bytes, csv_bytes)

  def testExportMultipleChunks(self):
    row_count = 100
    split_pieces = 10

    cell_value = 'fixed'
    table = [{'column1': cell_value}] * row_count
    table_json = json.dumps(table)

    table_bytes = row_count * len(cell_value.encode('utf-8'))
    chunk_bytes = table_bytes // split_pieces

    with test_lib.ConfigOverrider({"Osquery.max_chunk_size": chunk_bytes}):
      results_iterator = self._RunOsqueryExportResults(table_json)
    csv_bytes = next(results_iterator)

    expected_rows = "\r\n".join([cell_value] * row_count)
    expected_bytes = ('column1\r\n' + expected_rows + "\r\n").encode("utf-8")
    self.assertEqual(expected_bytes, csv_bytes)
