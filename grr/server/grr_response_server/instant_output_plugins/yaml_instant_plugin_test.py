#!/usr/bin/env python
"""Tests for YAML instant output plugin."""

import os
import zipfile

from absl import app
import yaml

from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.instant_output_plugins import yaml_instant_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class YamlInstantOutputPluginProtoTest(
    test_plugins.InstantOutputPluginTestBase
):
  """Tests the proto-based YAML instant output plugin."""

  plugin_cls = yaml_instant_plugin.YamlInstantOutputPluginProto

  def ProcessValuesToZip(self, values_by_cls):
    fd_path = self.ProcessValuesProto(values_by_cls)
    file_basename, _ = os.path.splitext(os.path.basename(fd_path))
    return zipfile.ZipFile(fd_path), file_basename

  @export_test_lib.WithAllExportConverters
  def testYamlPluginWithValuesOfSameType(self):
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
            f"{prefix}/ExportedFile/from_StatEntry.yaml",
        ]),
    )

    parsed_manifest = yaml.safe_load(zip_fd.read(f"{prefix}/MANIFEST"))
    self.assertEqual(
        parsed_manifest, {"export_stats": {"StatEntry": {"ExportedFile": 10}}}
    )

    parsed_output = yaml.safe_load(
        zip_fd.read(f"{prefix}/ExportedFile/from_StatEntry.yaml")
    )
    self.assertLen(parsed_output, 10)

    for i in range(10):
      # Make sure metadata is filled in.
      self.assertEqual(
          parsed_output[i]["metadata"]["clientUrn"], f"aff4:/{self.client_id}"
      )
      self.assertEqual(
          parsed_output[i]["metadata"]["hostname"], "Host-0.example.com"
      )
      self.assertEqual(
          parsed_output[i]["metadata"]["macAddress"],
          "aabbccddee00\nbbccddeeff00",
      )
      self.assertEqual(
          parsed_output[i]["metadata"]["sourceUrn"], self.results_urn
      )
      self.assertEqual(
          parsed_output[i]["metadata"]["hardwareInfo"]["biosVersion"],
          "Bios-Version-0",
      )

      self.assertEqual(
          parsed_output[i]["urn"],
          f"aff4:/{self.client_id}/fs/os/foo/bar/{i}",
      )
      self.assertEqual(parsed_output[i]["stMode"], "33184")
      self.assertEqual(parsed_output[i]["stIno"], "1063090")
      self.assertEqual(parsed_output[i]["stDev"], "64512")
      self.assertEqual(parsed_output[i]["stNlink"], str(1 + i))
      self.assertEqual(parsed_output[i]["stUid"], 139592)
      self.assertEqual(parsed_output[i]["stGid"], 5000)
      self.assertEqual(parsed_output[i]["stSize"], "0")
      # TODO: Add human-friendly timestamp fields to the exported
      # proto.
      self.assertEqual(parsed_output[i]["stAtime"], "1336469177")
      self.assertEqual(parsed_output[i]["stMtime"], "1336129892")
      self.assertEqual(parsed_output[i]["stCtime"], "1336129892")
      self.assertEqual(parsed_output[i]["stBlksize"], "0")
      self.assertEqual(parsed_output[i]["stRdev"], "0")
      self.assertEqual(parsed_output[i]["symlink"], "")

  @export_test_lib.WithAllExportConverters
  def testYamlPluginWithValuesOfMultipleTypes(self):
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
    self.assertEqual(
        set(zip_fd.namelist()),
        {
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile/from_StatEntry.yaml",
            f"{prefix}/ExportedProcess/from_Process.yaml",
        },
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

    parsed_output = yaml.safe_load(
        zip_fd.read(f"{prefix}/ExportedFile/from_StatEntry.yaml")
    )
    self.assertLen(parsed_output, 1)
    # Make sure metadata is filled in.
    self.assertEqual(
        parsed_output[0]["metadata"]["clientUrn"], f"aff4:/{self.client_id}"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["hostname"], "Host-0.example.com"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["macAddress"], "aabbccddee00\nbbccddeeff00"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["sourceUrn"], self.results_urn
    )
    self.assertEqual(
        parsed_output[0]["urn"], f"aff4:/{self.client_id}/fs/os/foo/bar"
    )

    parsed_output = yaml.safe_load(
        zip_fd.read(f"{prefix}/ExportedProcess/from_Process.yaml")
    )
    self.assertLen(parsed_output, 1)
    self.assertEqual(
        parsed_output[0]["metadata"]["clientUrn"], f"aff4:/{self.client_id}"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["hostname"], "Host-0.example.com"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["macAddress"], "aabbccddee00\nbbccddeeff00"
    )
    self.assertEqual(
        parsed_output[0]["metadata"]["sourceUrn"], self.results_urn
    )
    self.assertEqual(parsed_output[0]["pid"], 42)

  @export_test_lib.WithAllExportConverters
  def testYamlPluginWritesUnicodeValuesCorrectly(self):
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
        {
            f"{prefix}/MANIFEST",
            f"{prefix}/ExportedFile/from_StatEntry.yaml",
        },
    )

    parsed_output = yaml.safe_load(
        zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.yaml")
    )

    self.assertLen(parsed_output, 1)
    self.assertEqual(
        parsed_output[0]["urn"],
        "aff4:/C.1000000000000000/fs/os/中国新闻网新闻中",
    )

  @export_test_lib.WithAllExportConverters
  def testYamlPluginWritesMoreThanOneBatchOfRowsCorrectly(self):
    num_rows = self.__class__.plugin_cls.ROW_BATCH * 2 + 1

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
    parsed_output = yaml.safe_load(
        zip_fd.open(f"{prefix}/ExportedFile/from_StatEntry.yaml")
    )
    self.assertLen(parsed_output, num_rows)
    for i in range(num_rows):
      self.assertEqual(
          parsed_output[i]["urn"], f"aff4:/{self.client_id}/fs/os/foo/bar/{i}"
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
