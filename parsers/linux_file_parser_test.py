#!/usr/bin/env python
"""Unit test for the linux file parser."""

import StringIO


from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import linux_file_parser


class LinuxCmdParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux command output."""

  def testPasswdParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdParser()
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user2:/bin/bash
"""
    out = list(parser.Parse(None, StringIO.StringIO(dat), None))
    self.assertEquals(len(out), 2)
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertTrue(out[0].username, "user1")
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user
"""
    parser = linux_file_parser.PasswdParser()
    self.assertRaises(parsers.ParseError,
                      list, parser.Parse(None, StringIO.StringIO(dat), None))


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
