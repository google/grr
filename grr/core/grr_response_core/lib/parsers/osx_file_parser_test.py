#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for grr.parsers.osx_file_parser."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os

from absl import app
import biplist

from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import osx_file_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


class TestOSXFileParsing(test_lib.GRRBaseTest):
  """Test parsing of OSX files."""

  def testOSXUsersParser(self):
    """Ensure we can extract users from a passwd file."""
    paths = ["/Users/user1", "/Users/user2", "/Users/Shared"]
    statentries = []
    for path in paths:
      statentries.append(
          rdf_client_fs.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path=path, pathtype=rdf_paths.PathSpec.PathType.OS),
              st_mode=16877))

    statentries.append(
        rdf_client_fs.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path="/Users/.localized",
                pathtype=rdf_paths.PathSpec.PathType.OS),
            st_mode=33261))

    parser = osx_file_parser.OSXUsersParser()
    out = list(parser.ParseResponses(rdf_client.KnowledgeBase(), statentries))
    self.assertCountEqual([x.username for x in out], ["user1", "user2"])
    self.assertCountEqual([x.homedir for x in out],
                          ["/Users/user1", "/Users/user2"])

  def testOSXSPHardwareDataTypeParserInvalidInput(self):
    parser = osx_file_parser.OSXSPHardwareDataTypeParser()

    response = rdf_client_action.ExecuteResponse()
    response.request.cmd = "/usr/sbin/system_profiler"
    response.request.args = ["-xml", "SPHardwareDataType"]
    response.stdout = "chrząszcz brzmi w trzcinie".encode("utf-8")
    response.stdout = b""
    response.exit_status = 0

    with self.assertRaises(parsers.ParseError) as context:
      list(parser.ParseResponse(None, response))

    exception = context.exception
    self.assertIsInstance(exception.cause, biplist.InvalidPlistException)

  def testOSXSPHardwareDataTypeParser(self):
    parser = osx_file_parser.OSXSPHardwareDataTypeParser()
    content = open(os.path.join(self.base_path, "system_profiler.xml"),
                   "rb").read()
    result = list(
        parser.Parse("/usr/sbin/system_profiler", ["SPHardwareDataType -xml"],
                     content, "", 0, None))
    self.assertEqual(result[0].serial_number, "C02JQ0F5F6L9")
    self.assertEqual(result[0].bios_version, "MBP101.00EE.B02")
    self.assertEqual(result[0].system_product_name, "MacBookPro10,1")

  def testOSXLaunchdPlistParser(self):
    parser = osx_file_parser.OSXLaunchdPlistParser()
    plists = ["com.google.code.grr.plist", "com.google.code.grr.bplist"]
    results = []
    for plist in plists:
      path = os.path.join(self.base_path, "parser_test", plist)
      plist_file = open(path, "rb")
      pathspec = rdf_paths.PathSpec.OS(path=path)
      results.extend(list(parser.ParseFile(None, pathspec, plist_file)))

    for result in results:
      self.assertEqual(result.Label, "com.google.code.grr")
      self.assertCountEqual(result.ProgramArguments, [
          "/usr/lib/grr/grr_3.0.0.5_amd64/grr",
          "--config=/usr/lib/grr/grr_3.0.0.5_amd64/grr.yaml"
      ])

  def testOSXInstallHistoryPlistParserInvalidInput(self):
    parser = osx_file_parser.OSXInstallHistoryPlistParser()

    pathspec = rdf_paths.PathSpec.OS(path=os.path.join("foo", "bar", "baz"))
    contents = io.BytesIO("zażółć gęślą jaźń".encode("utf-8"))

    with self.assertRaises(parsers.ParseError) as context:
      list(parser.ParseFile(None, pathspec, contents))

    exception = context.exception
    self.assertIsInstance(exception.cause, biplist.InvalidPlistException)

  def testOSXInstallHistoryPlistParser(self):
    parser = osx_file_parser.OSXInstallHistoryPlistParser()

    path = os.path.join(self.base_path, "parser_test", "InstallHistory.plist")
    pathspec = rdf_paths.PathSpec.OS(path=path)
    with io.open(path, "rb") as plist_file:
      results = list(parser.ParseFile(None, pathspec, plist_file))

    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_client.SoftwarePackages)
    packages = results[0].packages

    # ESET AV
    self.assertEqual(packages[0].name, "ESET NOD32 Antivirus")
    self.assertEqual(packages[0].version, "")
    self.assertEqual(
        packages[0].description,
        "com.eset.esetNod32Antivirus.ESETNOD32Antivirus.pkg,"
        "com.eset.esetNod32Antivirus.GUI_startup.pkg,"
        "com.eset.esetNod32Antivirus.pkgid.pkg,"
        "com.eset.esetNod32Antivirus.com.eset.esets_daemon.pkg,"
        "com.eset.esetNod32Antivirus.esetsbkp.pkg,"
        "com.eset.esetNod32Antivirus.esets_kac_64_106.pkg")
    # echo $(( $(date --date="2017-07-20T18:40:22Z" +"%s") * 1000000))
    self.assertEqual(packages[0].installed_on, 1500576022000000)
    self.assertEqual(packages[0].install_state,
                     rdf_client.SoftwarePackage.InstallState.INSTALLED)

    # old grr agent
    self.assertEqual(packages[1].name, "grr")
    self.assertEqual(packages[1].version, "")
    self.assertEqual(packages[1].description, "com.google.code.grr.grr_3.2.1.0")
    # echo $(( $(date --date="2018-03-13T05:39:17Z" +"%s") * 1000000))
    self.assertEqual(packages[1].installed_on, 1520919557000000)
    self.assertEqual(packages[1].install_state,
                     rdf_client.SoftwarePackage.InstallState.INSTALLED)

    # new grr agent
    self.assertEqual(packages[2].name, "grr")
    self.assertEqual(packages[2].version, "")
    self.assertEqual(packages[2].description, "com.google.code.grr.grr_3.2.3.2")
    # echo $(( $(date --date="2018-08-07T16:07:10Z" +"%s") * 1000000))
    self.assertEqual(packages[2].installed_on, 1533658030000000)
    self.assertEqual(packages[2].install_state,
                     rdf_client.SoftwarePackage.InstallState.INSTALLED)

    # Sierra
    self.assertEqual(packages[3].name, "macOS Sierra Update")
    self.assertEqual(packages[3].version, "10.12.6")
    self.assertEqual(
        packages[3].description, "com.apple.pkg.update.os.10.12.6Patch.16G29,"
        "com.apple.pkg.FirmwareUpdate,"
        "com.apple.update.fullbundleupdate.16G29,"
        "com.apple.pkg.EmbeddedOSFirmware")
    # echo $(( $(date --date="2017-07-25T04:26:10Z" +"%s") * 1000000))
    self.assertEqual(packages[3].installed_on, 1500956770000000)
    self.assertEqual(packages[3].install_state,
                     rdf_client.SoftwarePackage.InstallState.INSTALLED)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
