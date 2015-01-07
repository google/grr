#!/usr/bin/env python
"""Tests for grr.parsers.osx_file_parser."""

import os


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import osx_file_parser


class TestOSXFileParsing(test_lib.GRRBaseTest):
  """Test parsing of OSX files."""

  def testOSXUsersParser(self):
    """Ensure we can extract users from a passwd file."""
    paths = ["/Users/user1", "/Users/user2", "/Users/Shared"]
    statentries = []
    client = "C.1000000000000000"
    for path in paths:
      statentries.append(rdfvalue.StatEntry(
          aff4path=rdfvalue.ClientURN(client).Add("fs/os").Add(path),
          pathspec=rdfvalue.PathSpec(path=path,
                                     pathtype=rdfvalue.PathSpec.PathType.OS),
          st_mode=16877))

    statentries.append(rdfvalue.StatEntry(
        aff4path=rdfvalue.ClientURN(client).Add(
            "fs/os").Add("/Users/.localized"),
        pathspec=rdfvalue.PathSpec(path="/Users/.localized",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        st_mode=33261))

    parser = osx_file_parser.OSXUsersParser()
    out = list(parser.Parse(statentries, None, None))
    self.assertItemsEqual([x.username for x in out], ["user1", "user2"])
    self.assertItemsEqual([x.homedir for x in out],
                          ["/Users/user1", "/Users/user2"])

  def testOSXSPHardwareDataTypeParser(self):
    parser = osx_file_parser.OSXSPHardwareDataTypeParser()
    content = open(os.path.join(self.base_path, "system_profiler.xml")).read()
    result = list(parser.Parse("/usr/sbin/system_profiler",
                               ["SPHardwareDataType -xml"],
                               content, "", 0, 5, None))
    self.assertEqual(result[0].serial_number, "C02JQ0F5F6L9")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
