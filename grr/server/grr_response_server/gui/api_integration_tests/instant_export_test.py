#!/usr/bin/env python
"""Tests for instant export-realted API calls."""

import csv
import io
import textwrap
import zipfile

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server.export_converters import process as ec_process
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import action_mocks
from grr.test_lib import export_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ApiInstantExportTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests instant-export parts of GRR Python API client library."""

  @test_plugins.WithInstantOutputPluginProto(
      csv_instant_plugin.CSVInstantOutputPluginProto
  )
  @export_test_lib.WithExportConverterProto(
      ec_process.ProcessToExportedProcessConverterProto
  )
  def testGetExportedResultsArchiveForListProcessesFlowProto(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=1333718907167083,
        RSS_size=42,
    )

    client_id = self.SetupClient(0)
    flow_id = flow_test_lib.StartAndRunFlow(
        processes.ListProcesses,
        client_id=client_id,
        client_mock=action_mocks.ListProcessesMock([process]),
        creator=self.test_username,
    )

    result_flow = self.api.Client(client_id=client_id).Flow(flow_id)
    exported_archive = result_flow.GetExportedResultsArchive(
        csv_instant_plugin.CSVInstantOutputPluginProto.plugin_name
    )

    out_fd = io.BytesIO()
    exported_archive.WriteToStream(out_fd)
    out_fd.seek(0)

    zip_fd = zipfile.ZipFile(out_fd, "r")

    prefix = f"results_{client_id}_flows_{flow_id}"
    manifest_path = f"{prefix}/MANIFEST"
    exported_process_path = f"{prefix}/ExportedProcess/from_Process.csv"

    self.assertCountEqual(
        zip_fd.namelist(),
        [
            manifest_path,
            exported_process_path,
        ],
    )

    with zip_fd.open(manifest_path) as fd:
      content = fd.read().decode("utf-8")
      self.assertEqual(
          content,
          textwrap.dedent("""\
          export_stats:
            Process:
              ExportedProcess: 1
          """),
      )

    with zip_fd.open(exported_process_path) as fd:
      content = fd.read().decode("utf-8")
      reader = csv.reader(io.StringIO(content))
      rows = list(reader)

      self.assertLen(rows, 2)
      header = rows[0]
      values = rows[1]

      expected_header = [
          "metadata.client_urn",
          "metadata.client_id",
          "metadata.hostname",
          "metadata.os",
          "metadata.client_age",
          "metadata.os_release",
          "metadata.os_version",
          "metadata.usernames",
          "metadata.mac_address",
          "metadata.timestamp",
          "metadata.deprecated_session_id",
          "metadata.labels",
          "metadata.system_labels",
          "metadata.user_labels",
          "metadata.source_urn",
          "metadata.annotations",
          "metadata.hardware_info.serial_number",
          "metadata.hardware_info.system_manufacturer",
          "metadata.hardware_info.system_product_name",
          "metadata.hardware_info.system_uuid",
          "metadata.hardware_info.system_sku_number",
          "metadata.hardware_info.system_family",
          "metadata.hardware_info.bios_vendor",
          "metadata.hardware_info.bios_version",
          "metadata.hardware_info.bios_release_date",
          "metadata.hardware_info.bios_rom_size",
          "metadata.hardware_info.bios_revision",
          "metadata.hardware_info.system_assettag",
          "metadata.kernel_version",
          "metadata.cloud_instance_type",
          "metadata.cloud_instance_id",
          "pid",
          "ppid",
          "name",
          "exe",
          "cmdline",
          "ctime",
          "real_uid",
          "effective_uid",
          "saved_uid",
          "real_gid",
          "effective_gid",
          "saved_gid",
          "username",
          "terminal",
          "status",
          "nice",
          "cwd",
          "num_threads",
          "user_cpu_time",
          "system_cpu_time",
          "rss_size",
          "vms_size",
          "memory_percent",
      ]
      self.assertEqual(header, expected_header)

      # Check and erase values that are not deterministic.
      self.assertNotEmpty(values[header.index("metadata.timestamp")])
      values[header.index("metadata.timestamp")] = ""

      expected_values = [
          f"aff4:/{client_id}",  # metadata.client_urn
          client_id,  # metadata.client_id
          "Host-0.example.com",  # metadata.hostname
          "Linux",  # metadata.os
          "0",  # metadata.client_age
          "",  # metadata.os_release
          "buster/sid",  # metadata.os_version
          "user1,user2",  # metadata.usernames
          "aabbccddee00\nbbccddeeff00",  # metadata.mac_address
          "",  # metadata.timestamp
          "",  # metadata.deprecated_session_id
          "",  # metadata.labels
          "",  # metadata.system_labels
          "",  # metadata.user_labels
          f"aff4:/{client_id}/flows/{flow_id}",  # metadata.source_urn
          "",  # metadata.annotations
          "",  # metadata.hardware_info.serial_number
          "System-Manufacturer-0",  # metadata.hardware_info.system_manufacturer
          "",  # metadata.hardware_info.system_product_name
          "",  # metadata.hardware_info.system_uuid
          "",  # metadata.hardware_info.system_sku_number
          "",  # metadata.hardware_info.system_family
          "",  # metadata.hardware_info.bios_vendor
          "Bios-Version-0",  # metadata.hardware_info.bios_version
          "",  # metadata.hardware_info.bios_release_date
          "",  # metadata.hardware_info.bios_rom_size
          "",  # metadata.hardware_info.bios_revision
          "",  # metadata.hardware_info.system_assettag
          "4.0.0",  # metadata.kernel_version
          "0",  # metadata.cloud_instance_type
          "",  # metadata.cloud_instance_id
          "2",  # pid
          "1",  # ppid
          "",  # name
          "c:\\windows\\cmd.exe",  # exe
          "cmd.exe",  # cmdline
          "1333718907167083",  # ctime
          "0",  # real_uid
          "0",  # effective_uid
          "0",  # saved_uid
          "0",  # real_gid
          "0",  # effective_gid
          "0",  # saved_gid
          "",  # username
          "",  # terminal
          "",  # status
          "0",  # nice
          "",  # cwd
          "0",  # num_threads
          "0.0",  # user_cpu_time
          "0.0",  # system_cpu_time
          "42",  # rss_size
          "0",  # vms_size
          "0.0",  # memory_percent
      ]
      self.assertEqual(values, expected_values)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
