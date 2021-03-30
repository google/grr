#!/usr/bin/env python
"""Integration tests for the Osquery flow, its API client and API endpoints."""
import json

from absl import app

from grr_api_client import utils
from grr_response_proto.api import osquery_pb2 as api_osquery_pb2
from grr_response_server.flows.general import osquery as osquery_flow
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import osquery_test_lib
from grr.test_lib import test_lib


class OsqueryResultsExportTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests exporting Osquery results using functionality in the API client."""

  def _RunOsqueryExportResults(self, stdout: str) -> utils.BinaryChunkIterator:
    client_id = self.SetupClient(0)

    with osquery_test_lib.FakeOsqueryiOutput(stdout=stdout, stderr=""):
      flow_id = flow_test_lib.TestFlowHelper(
          osquery_flow.OsqueryFlow.__name__,
          action_mocks.OsqueryClientMock(),
          client_id=client_id,
          creator=self.test_username,
          query="doesn't matter")
      result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
      result_flow.WaitUntilDone()

    format_csv = api_osquery_pb2.ApiGetOsqueryResultsArgs.Format.CSV
    return result_flow.GetOsqueryResults(format_csv)

  def testExportSomeResults(self):
    stdout = """
    [
      { "foo": "quux", "bar": "norf" },
      { "foo": "blargh", "bar": "plugh" }
    ]
    """

    results_iterator = self._RunOsqueryExportResults(stdout)
    output_bytes = next(results_iterator)
    output_text = output_bytes.decode("utf-8")

    self.assertEqual("foo,bar\r\nquux,norf\r\nblargh,plugh\r\n", output_text)

  def testExportNoRows(self):
    stdout = """
    [

    ]
    """

    output_bytes = b"".join(self._RunOsqueryExportResults(stdout))
    output_text = output_bytes.decode("utf-8")

    self.assertEmpty(output_text)

  def testExportUnicodeCharacters(self):
    stdout = """
    [
      { "🇬 🇷 🇷": "🔝🔝🔝"}
    ]
    """

    results_iterator = self._RunOsqueryExportResults(stdout)
    output_bytes = next(results_iterator)
    output_text = output_bytes.decode("utf-8")

    self.assertEqual("🇬 🇷 🇷\r\n🔝🔝🔝\r\n", output_text)

  def testExportMultipleChunks(self):
    row_count = 100
    split_pieces = 10

    cell_value = "fixed"
    table = [{"column1": cell_value}] * row_count
    table_json = json.dumps(table)

    table_bytes = row_count * len(cell_value.encode("utf-8"))
    chunk_bytes = table_bytes // split_pieces

    with test_lib.ConfigOverrider({"Osquery.max_chunk_size": chunk_bytes}):
      results_iterator = self._RunOsqueryExportResults(table_json)
    output_bytes = next(results_iterator)
    output_text = output_bytes.decode("utf-8")

    expected_rows = "\r\n".join([cell_value] * row_count)
    self.assertEqual("column1\r\n" + expected_rows + "\r\n", output_text)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
