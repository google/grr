#!/usr/bin/env python
"""Tests for CSV output plugin."""

import csv
import io
import os
import zipfile

from absl import app
import yaml

from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.instant_output_plugins import csv_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class CSVInstantOutputPluginProtoTest(test_plugins.InstantOutputPluginTestBase):
  """Tests instant CSV output plugin."""

  plugin_cls = csv_instant_plugin.CSVInstantOutputPluginProto

  def ProcessValuesToZip(self, values_by_cls):
    fd_path = self.ProcessValuesProto(values_by_cls)
    file_basename, _ = os.path.splitext(os.path.basename(fd_path))
    return zipfile.ZipFile(fd_path), file_basename

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWithValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  path=f"/foo/bar/{i}",
                  pathtype=jobs_pb2.PathSpec.PathType.OS,
              ),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1336469177,
              st_mtime=1336129892,
              st_ctime=1336129892,
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip({jobs_pb2.StatEntry: responses})
    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile/from_StatEntry.csv",
        ]),
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest, {"export_stats": {"StatEntry": {"ExportedFile": 10}}}
    )

    with zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.csv") as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 10)
    for i in range(10):
      # Make sure metadata is filled in.
      self.assertEqual(
          parsed_output[i]["metadata.client_urn"], f"aff4:/{self.client_id}"
      )
      self.assertEqual(
          parsed_output[i]["metadata.hostname"], "Host-0.example.com"
      )
      self.assertEqual(
          parsed_output[i]["metadata.mac_address"], "aabbccddee00\nbbccddeeff00"
      )
      self.assertEqual(
          parsed_output[i]["metadata.source_urn"], self.results_urn
      )
      self.assertEqual(
          parsed_output[i]["metadata.hardware_info.bios_version"],
          "Bios-Version-0",
      )

      self.assertEqual(
          parsed_output[i]["urn"],
          f"aff4:/{self.client_id}/fs/os/foo/bar/{i}",
      )
      self.assertEqual(parsed_output[i]["st_mode"], "33184")
      self.assertEqual(parsed_output[i]["st_ino"], "1063090")
      self.assertEqual(parsed_output[i]["st_dev"], "64512")
      self.assertEqual(parsed_output[i]["st_nlink"], str(1 + i))
      self.assertEqual(parsed_output[i]["st_uid"], "139592")
      self.assertEqual(parsed_output[i]["st_gid"], "5000")
      self.assertEqual(parsed_output[i]["st_size"], "0")
      # TODO: Add human-friendly timestamp fields to the exported
      # proto.
      self.assertEqual(parsed_output[i]["st_atime"], "1336469177")
      self.assertEqual(parsed_output[i]["st_mtime"], "1336129892")
      self.assertEqual(parsed_output[i]["st_ctime"], "1336129892")
      self.assertEqual(parsed_output[i]["st_blksize"], "0")
      self.assertEqual(parsed_output[i]["st_rdev"], "0")
      self.assertEqual(parsed_output[i]["symlink"], "")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWithValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        jobs_pb2.StatEntry: [
            jobs_pb2.StatEntry(
                pathspec=jobs_pb2.PathSpec(
                    path="/foo/bar",
                    pathtype=jobs_pb2.PathSpec.PathType.OS,
                )
            )
        ],
        sysinfo_pb2.Process: [sysinfo_pb2.Process(pid=42)],
    })
    self.assertCountEqual(
        set(zip_fd.namelist()),
        set([
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile/from_StatEntry.csv",
            f"{prefix}/ExportedProcess/from_Process.csv",
        ]),
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest,
        {
            "export_stats": {
                "StatEntry": {"ExportedFile": 1},
                "Process": {"ExportedProcess": 1},
            }
        },
    )

    with zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.csv") as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 1)

    # Make sure metadata is filled in.
    self.assertEqual(
        parsed_output[0]["metadata.client_urn"], f"aff4:/{self.client_id}"
    )
    self.assertEqual(
        parsed_output[0]["metadata.hostname"], "Host-0.example.com"
    )
    self.assertEqual(
        parsed_output[0]["metadata.mac_address"], "aabbccddee00\nbbccddeeff00"
    )
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(
        parsed_output[0]["urn"], f"aff4:/{self.client_id}/fs/os/foo/bar"
    )

    filepath = f"{prefix}/ExportedProcess/from_Process.csv"
    with zip_fd.open(filepath) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 1)

    self.assertEqual(
        parsed_output[0]["metadata.client_urn"], f"aff4:/{self.client_id}"
    )
    self.assertEqual(
        parsed_output[0]["metadata.hostname"], "Host-0.example.com"
    )
    self.assertEqual(
        parsed_output[0]["metadata.mac_address"], "aabbccddee00\nbbccddeeff00"
    )
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(parsed_output[0]["pid"], "42")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWritesUnicodeValuesCorrectly(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        jobs_pb2.StatEntry: [
            jobs_pb2.StatEntry(
                pathspec=jobs_pb2.PathSpec(
                    path="/中国新闻网新闻中",
                    pathtype=jobs_pb2.PathSpec.PathType.OS,
                )
            )
        ]
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile/from_StatEntry.csv",
        ]),
    )

    data = zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.csv")
    data = io.TextIOWrapper(data, encoding="utf-8")
    parsed_output = list(csv.reader(data))

    self.assertLen(parsed_output, 2)
    urn_pos = parsed_output[0].index("urn")
    urn = parsed_output[1][urn_pos]
    self.assertEqual(urn, "aff4:/C.1000000000000000/fs/os/中国新闻网新闻中")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWritesBytesValuesCorrectly(self):
    pathspec = jobs_pb2.PathSpec(
        path="/żółta/gęśla/jaźń",
        pathtype=jobs_pb2.PathSpec.PathType.OS,
    )
    values = {
        jobs_pb2.BufferReference: [
            jobs_pb2.BufferReference(data=b"\xff\x00\xff", pathspec=pathspec),
            jobs_pb2.BufferReference(data=b"\xfa\xfb\xfc", pathspec=pathspec),
        ],
    }

    zip_fd, prefix = self.ProcessValuesToZip(values)

    manifest_path = "{}/MANIFEST".format(prefix)
    data_path = "{}/ExportedMatch/from_BufferReference.csv".format(prefix)

    self.assertCountEqual(zip_fd.namelist(), [manifest_path, data_path])

    with zip_fd.open(data_path) as data:
      data = io.TextIOWrapper(data, encoding="utf-8")
      results = list(csv.reader(data))

    self.assertLen(results, 3)

    data_idx = results[0].index("data")
    self.assertEqual(results[1][data_idx], "\\xff\\x00\\xff")
    self.assertEqual(results[2][data_idx], "\\xfa\\xfb\\xfc")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWritesMoreThanOneBatchOfRowsCorrectly(self):
    num_rows = csv_instant_plugin.CSVInstantOutputPluginProto.ROW_BATCH * 2 + 1

    responses = []
    for i in range(num_rows):
      responses.append(
          jobs_pb2.StatEntry(
              pathspec=jobs_pb2.PathSpec(
                  path=f"/foo/bar/{i}",
                  pathtype=jobs_pb2.PathSpec.PathType.OS,
              )
          )
      )

    zip_fd, prefix = self.ProcessValuesToZip({jobs_pb2.StatEntry: responses})

    with zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.csv") as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, num_rows)
    for i in range(num_rows):
      self.assertEqual(
          parsed_output[i]["urn"],
          f"aff4:/{self.client_id}/fs/os/foo/bar/{i}",
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
