#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Unit test for config files."""
import StringIO


from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.parsers import config_file


CFG = """
# A comment.
Protocol 2  # Another comment.
Ciphers aes128-ctr,aes256-ctr,aes128-cbc,aes256-cbc
ServerKeyBits 768
Port 22
Port 2222,10222

# Make life easy for root. It's hard running a server.
Match User root
  PermitRootLogin yes

# Oh yeah, this is an excellent way to protect that root account.
Match Address 192.168.3.12
  PermitRootLogin no
  Protocol 1  # Not a valid match group entry.
"""


class SshdConfigTest(test_lib.GRRBaseTest):
  """Test parsing of an sshd configuration."""

  def GetConfig(self):
    """Read in the test configuration file."""
    parser = config_file.SshdConfigParser()
    results = list(parser.Parse(None, StringIO.StringIO(CFG), None))
    self.assertEqual(1, len(results))
    return results[0]

  def testParseConfig(self):
    """Ensure we can extract sshd settings."""
    result = self.GetConfig()
    self.assertTrue(isinstance(result, rdfvalue.SshdConfig))
    self.assertItemsEqual([2], result.config.protocol)
    expect = ["aes128-ctr", "aes256-ctr", "aes128-cbc", "aes256-cbc"]
    self.assertItemsEqual(expect, result.config.ciphers)

  def testFindNumericValues(self):
    """Keywords with numeric settings are converted to integers."""
    result = self.GetConfig()
    self.assertEqual(768, result.config.serverkeybits)
    self.assertItemsEqual([22, 2222, 10222], result.config.port)

  def testParseMatchGroups(self):
    """Match groups are added to separate sections."""
    result = self.GetConfig()
    # Multiple Match groups found.
    self.assertEqual(2, len(result.matches))
    # Config options set per Match group.
    block_1, block_2 = result.matches
    self.assertEqual("user root", block_1.criterion)
    self.assertEqual("address 192.168.3.12", block_2.criterion)
    self.assertEqual(True, block_1.config.permitrootlogin)
    self.assertEqual(False, block_2.config.permitrootlogin)
    self.assertFalse(block_1.config.protocol)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
