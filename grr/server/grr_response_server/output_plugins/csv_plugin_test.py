#!/usr/bin/env python
"""Tests for CSV output plugin."""

import csv
import io
import os
import zipfile

from absl import app
import yaml

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server.output_plugins import csv_plugin
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import export_test_lib
from grr.test_lib import test_lib


class CSVInstantOutputPluginTest(test_plugins.InstantOutputPluginTestBase):
  """Tests instant CSV output plugin."""

  plugin_cls = csv_plugin.CSVInstantOutputPlugin

  def ProcessValuesToZip(self, values_by_cls):
    fd_path = self.ProcessValues(values_by_cls)
    file_basename, _ = os.path.splitext(os.path.basename(fd_path))
    return zipfile.ZipFile(fd_path), file_basename

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWithValuesOfSameType(self):
    responses = []
    for i in range(10):
      responses.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="/foo/bar/%d" % i, pathtype="OS"),
              st_mode=33184,  # octal = 100640 => u=rw,g=r,o= => -rw-r-----
              st_ino=1063090,
              st_dev=64512,
              st_nlink=1 + i,
              st_uid=139592,
              st_gid=5000,
              st_size=0,
              st_atime=1336469177,
              st_mtime=1336129892,
              st_ctime=1336129892))

    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: responses})
    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            "%s/MANIFEST" % prefix,
            "%s/ExportedFile/from_StatEntry.csv" % prefix
        ]))

    parsed_manifest = yaml.safe_load(zip_fd.read("%s/MANIFEST" % prefix))
    self.assertEqual(parsed_manifest,
                     {"export_stats": {
                         "StatEntry": {
                             "ExportedFile": 10
                         }
                     }})

    with zip_fd.open("%s/ExportedFile/from_StatEntry.csv" % prefix) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 10)
    for i in range(10):
      # Make sure metadata is filled in.
      self.assertEqual(parsed_output[i]["metadata.client_urn"],
                       "aff4:/%s" % self.client_id)
      self.assertEqual(parsed_output[i]["metadata.hostname"],
                       "Host-0.example.com")
      self.assertEqual(parsed_output[i]["metadata.mac_address"],
                       "aabbccddee00\nbbccddeeff00")
      self.assertEqual(parsed_output[i]["metadata.source_urn"],
                       self.results_urn)
      self.assertEqual(parsed_output[i]["metadata.hardware_info.bios_version"],
                       "Bios-Version-0")

      self.assertEqual(parsed_output[i]["urn"],
                       "aff4:/%s/fs/os/foo/bar/%d" % (self.client_id, i))
      self.assertEqual(parsed_output[i]["st_mode"], "-rw-r-----")
      self.assertEqual(parsed_output[i]["st_ino"], "1063090")
      self.assertEqual(parsed_output[i]["st_dev"], "64512")
      self.assertEqual(parsed_output[i]["st_nlink"], str(1 + i))
      self.assertEqual(parsed_output[i]["st_uid"], "139592")
      self.assertEqual(parsed_output[i]["st_gid"], "5000")
      self.assertEqual(parsed_output[i]["st_size"], "0")
      self.assertEqual(parsed_output[i]["st_atime"], "2012-05-08 09:26:17")
      self.assertEqual(parsed_output[i]["st_mtime"], "2012-05-04 11:11:32")
      self.assertEqual(parsed_output[i]["st_ctime"], "2012-05-04 11:11:32")
      self.assertEqual(parsed_output[i]["st_blksize"], "0")
      self.assertEqual(parsed_output[i]["st_rdev"], "0")
      self.assertEqual(parsed_output[i]["symlink"], "")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWithValuesOfMultipleTypes(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        rdf_client_fs.StatEntry: [
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/foo/bar", pathtype="OS"))
        ],
        rdf_client.Process: [rdf_client.Process(pid=42)]
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            "%s/MANIFEST" % prefix,
            "%s/ExportedFile/from_StatEntry.csv" % prefix,
            "%s/ExportedProcess/from_Process.csv" % prefix
        ]))

    parsed_manifest = yaml.safe_load(zip_fd.read("%s/MANIFEST" % prefix))
    self.assertEqual(
        parsed_manifest, {
            "export_stats": {
                "StatEntry": {
                    "ExportedFile": 1
                },
                "Process": {
                    "ExportedProcess": 1
                }
            }
        })

    with zip_fd.open("%s/ExportedFile/from_StatEntry.csv" % prefix) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 1)

    # Make sure metadata is filled in.
    self.assertEqual(parsed_output[0]["metadata.client_urn"],
                     "aff4:/%s" % self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"],
                     "Host-0.example.com")
    self.assertEqual(parsed_output[0]["metadata.mac_address"],
                     "aabbccddee00\nbbccddeeff00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(parsed_output[0]["urn"],
                     "aff4:/%s/fs/os/foo/bar" % self.client_id)

    filepath = "%s/ExportedProcess/from_Process.csv" % prefix
    with zip_fd.open(filepath) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, 1)

    self.assertEqual(parsed_output[0]["metadata.client_urn"],
                     "aff4:/%s" % self.client_id)
    self.assertEqual(parsed_output[0]["metadata.hostname"],
                     "Host-0.example.com")
    self.assertEqual(parsed_output[0]["metadata.mac_address"],
                     "aabbccddee00\nbbccddeeff00")
    self.assertEqual(parsed_output[0]["metadata.source_urn"], self.results_urn)
    self.assertEqual(parsed_output[0]["pid"], "42")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWritesUnicodeValuesCorrectly(self):
    zip_fd, prefix = self.ProcessValuesToZip({
        rdf_client_fs.StatEntry: [
            rdf_client_fs.StatEntry(
                pathspec=rdf_paths.PathSpec(path="/中国新闻网新闻中", pathtype="OS"))
        ]
    })
    self.assertEqual(
        set(zip_fd.namelist()),
        set([
            "%s/MANIFEST" % prefix,
            "%s/ExportedFile/from_StatEntry.csv" % prefix
        ]))

    data = zip_fd.open("%s/ExportedFile/from_StatEntry.csv" % prefix)
    data = io.TextIOWrapper(data, encoding="utf-8")
    parsed_output = list(csv.reader(data))

    self.assertLen(parsed_output, 2)
    urn_pos = parsed_output[0].index("urn")
    urn = parsed_output[1][urn_pos]
    self.assertEqual(urn, "aff4:/C.1000000000000000/fs/os/中国新闻网新闻中")

  @export_test_lib.WithAllExportConverters
  def testCSVPluginWritesBytesValuesCorrectly(self):
    pathspec = rdf_paths.PathSpec.OS(path="/żółta/gęśla/jaźń")
    values = {
        rdf_client.BufferReference: [
            rdf_client.BufferReference(data=b"\xff\x00\xff", pathspec=pathspec),
            rdf_client.BufferReference(data=b"\xfa\xfb\xfc", pathspec=pathspec),
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
    num_rows = csv_plugin.CSVInstantOutputPlugin.ROW_BATCH * 2 + 1

    responses = []
    for i in range(num_rows):
      responses.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path="/foo/bar/%d" % i, pathtype="OS")))

    zip_fd, prefix = self.ProcessValuesToZip(
        {rdf_client_fs.StatEntry: responses})

    with zip_fd.open("%s/ExportedFile/from_StatEntry.csv" % prefix) as filedesc:
      content = filedesc.read().decode("utf-8")

    parsed_output = list(csv.DictReader(io.StringIO(content)))
    self.assertLen(parsed_output, num_rows)
    for i in range(num_rows):
      self.assertEqual(parsed_output[i]["urn"],
                       "aff4:/%s/fs/os/foo/bar/%d" % (self.client_id, i))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
