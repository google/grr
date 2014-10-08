#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Unit test for the linux file parser."""

import os
import StringIO


from grr.lib import config_lib
from grr.lib import flags
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.parsers import linux_file_parser


class LinuxFileParserTest(test_lib.GRRBaseTest):
  """Test parsing of linux files."""

  def testPasswdParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdParser()
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user2:/bin/bash
"""
    out = list(parser.Parse(None, StringIO.StringIO(dat), None))
    self.assertEqual(len(out), 2)
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")
    dat = """
user1:x:1000:1000:User1 Name,,,:/home/user1:/bin/bash
user2:x:1001:1001:User2 Name,,,:/home/user
"""
    parser = linux_file_parser.PasswdParser()
    self.assertRaises(parsers.ParseError,
                      list, parser.Parse(None, StringIO.StringIO(dat), None))

  def testPasswdBufferParser(self):
    """Ensure we can extract users from a passwd file."""
    parser = linux_file_parser.PasswdBufferParser()
    buf1 = rdfvalue.BufferReference(data="user1:x:1000:1000:User1"
                                    " Name,,,:/home/user1:/bin/bash\n")

    buf2 = rdfvalue.BufferReference(data="user2:x:1000:1000:User2"
                                    " Name,,,:/home/user2:/bin/bash\n")

    ff_result = rdfvalue.FileFinderResult(matches=[buf1, buf2])
    out = list(parser.Parse(ff_result, None))
    self.assertEqual(len(out), 2)
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertTrue(isinstance(out[1], rdfvalue.KnowledgeBaseUser))
    self.assertEqual(out[0].username, "user1")
    self.assertEqual(out[0].full_name, "User1 Name,,,")

  def testNetgroupParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupParser()
    dat = u"""group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 (-,user4,) (-,user2,)

super_group (-,user5,) (-,user6,) (-,文德文,) group1 group2
super_group2 (-,user7,) super_group
super_group3 (-,user5,) (-,user6,) group1 group2
"""
    dat_fd = StringIO.StringIO(dat)

    config_lib.CONFIG.Set("Artifacts.netgroup_user_blacklist", ["user2",
                                                                "user3"])
    out = list(parser.Parse(None, dat_fd, None))
    users = []
    for result in out:
      if isinstance(result, rdfvalue.Anomaly):
        self.assertTrue(utils.SmartUnicode(u"文德文") in result.symptom)
      else:
        users.append(result)

    self.assertItemsEqual([x.username for x in users],
                          [u"user1", u"user4", u"user5", u"user6", u"user7"])

    dat_fd.seek(0)
    config_lib.CONFIG.Set("Artifacts.netgroup_filter_regexes",
                          [r"^super_group3$"])
    out = list(parser.Parse(None, dat_fd, None))
    self.assertItemsEqual([x.username for x in out],
                          [u"user5", u"user6"])

  def testNetgroupBufferParser(self):
    """Ensure we can extract users from a netgroup file."""
    parser = linux_file_parser.NetgroupBufferParser()
    buf1 = rdfvalue.BufferReference(data="group1 (-,user1,) (-,user2,) "
                                    "(-,user3,)\n")
    buf2 = rdfvalue.BufferReference(data="super_group3 (-,user5,) (-,user6,)"
                                    " group1 group2\n")

    ff_result = rdfvalue.FileFinderResult(matches=[buf1, buf2])
    config_lib.CONFIG.Set("Artifacts.netgroup_user_blacklist", ["user2",
                                                                "user3"])
    out = list(parser.Parse(ff_result, None))
    self.assertItemsEqual([x.username for x in out],
                          [u"user1", u"user5", u"user6"])

  def testNetgroupParserBadInput(self):
    parser = linux_file_parser.NetgroupParser()
    dat = """group1 (-,user1,) (-,user2,) (-,user3,)
#group1 comment
group2 user4 (-user2,)
super_group (-,,user5,) (-user6,) group1 group2
super_group2 (-,user7,) super_group
"""
    self.assertRaises(parsers.ParseError,
                      list, parser.Parse(None, StringIO.StringIO(dat), None))

  def testWtmpParser(self):
    """Test parsing of wtmp file."""
    parser = linux_file_parser.LinuxWtmpParser()
    path = os.path.join(self.base_path, "wtmp")
    with open(path, "rb") as wtmp_fd:
      out = list(parser.Parse(None, wtmp_fd, None))

    self.assertEqual(len(out), 3)
    self.assertItemsEqual(["%s:%d" % (x.username, x.last_logon) for x in out],
                          ["user1:1296552099000000",
                           "user2:1296552102000000",
                           "user3:1296569997000000"])


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
