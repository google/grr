#!/usr/bin/env python
"""Unit test for the linux file parser."""

import io

from absl import app

from grr_response_core.lib import parsers
from grr_response_core.lib.parsers import linux_file_parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr.test_lib import test_lib


class LinuxFileParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux files."""

  def testPasswdParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdParser()
    dat = b"""
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user2:/bin/bash
"""
    out = list(parser.ParseFile(None, None, io.BytesIO(dat)))
    self.assertLen(out, 2)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertIsInstance(out[1], rdf_client.User)
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")
    dat = b"""
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user
"""
    parser = linux_file_parser.PasswdParser()
    with self.assertRaises(parsers.ParseError):
      list(parser.ParseFile(None, None, io.BytesIO(dat)))


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
