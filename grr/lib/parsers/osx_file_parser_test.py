#!/usr/bin/env python
"""Tests for grr.parsers.osx_file_parser."""

import os


from grr.lib import flags
from grr.lib.parsers import osx_file_parser
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


class TestOSXFileParsing(test_lib.GRRBaseTest):
  """Test parsing of OSX files."""

  def testOSXUsersParser(self):
    """Ensure we can extract users from a passwd file."""
    paths = ["/Users/user1", "/Users/user2", "/Users/Shared"]
    statentries = []
    for path in paths:
      statentries.append(
          rdf_client.StatEntry(
              pathspec=rdf_paths.PathSpec(
                  path=path, pathtype=rdf_paths.PathSpec.PathType.OS),
              st_mode=16877))

    statentries.append(
        rdf_client.StatEntry(
            pathspec=rdf_paths.PathSpec(
                path="/Users/.localized",
                pathtype=rdf_paths.PathSpec.PathType.OS),
            st_mode=33261))

    parser = osx_file_parser.OSXUsersParser()
    out = list(parser.Parse(statentries, None, None))
    self.assertItemsEqual([x.username for x in out], ["user1", "user2"])
    self.assertItemsEqual([x.homedir
                           for x in out], ["/Users/user1", "/Users/user2"])

  def testOSXSPHardwareDataTypeParser(self):
    parser = osx_file_parser.OSXSPHardwareDataTypeParser()
    content = open(os.path.join(self.base_path, "system_profiler.xml"),
                   "rb").read()
    result = list(
        parser.Parse("/usr/sbin/system_profiler", ["SPHardwareDataType -xml"],
                     content, "", 0, 5, None))
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
      stat = rdf_client.StatEntry(
          pathspec=rdf_paths.PathSpec(
              path=path, pathtype=rdf_paths.PathSpec.PathType.OS),
          st_mode=16877)
      results.extend(list(parser.Parse(stat, plist_file, None)))

    for result in results:
      self.assertEqual(result.Label, "com.google.code.grr")
      self.assertItemsEqual(result.ProgramArguments, [
          "/usr/lib/grr/grr_3.0.0.5_amd64/grr",
          "--config=/usr/lib/grr/grr_3.0.0.5_amd64/grr.yaml"
      ])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
