#!/usr/bin/env python
"""Tests for instant export-realted API calls."""

import io
import zipfile

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import compatibility
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.output_plugins import csv_plugin
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiInstantExportTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests instant-export parts of GRR Python API client library."""

  def testGetExportedResultsArchiveForListProcessesFlow(self):
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
        creator=self.test_username)

    result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
    exported_archive = result_flow.GetExportedResultsArchive(
        csv_plugin.CSVInstantOutputPlugin.plugin_name)

    out_fd = io.BytesIO()
    exported_archive.WriteToStream(out_fd)
    out_fd.seek(0)

    zip_fd = zipfile.ZipFile(out_fd, "r")

    self.assertNotEmpty([n for n in zip_fd.namelist() if "MANIFEST" not in n])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
