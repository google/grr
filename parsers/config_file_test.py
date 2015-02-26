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


class FieldParserTests(test_lib.GRRBaseTest):
  """Test the field parser."""

  def testParser(self):
    test_data = r"""
    each of these words:should;be \
        fields # but not these ones \n, or \ these.
    this  should be     another entry "with this quoted text as one field"
    'an entry'with" only two" fields ;; and not this comment.
    """
    expected = [["each", "of", "these", "words", "should", "be", "fields"],
                ["this", "should", "be", "another", "entry",
                 "with this quoted text as one field"],
                ["an entrywith only two", "fields"]]
    cfg = config_file.FieldParser(sep=[r"\s+", ":", ";"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertItemsEqual(expect, results[i])


class KeyValueParserTests(test_lib.GRRBaseTest):
  """Test the field parser."""

  def testParser(self):
    test_data = r"""
    key1 = a list of \
      fields # but not \n this, or \ this.

    # Nothing here.
    key 2:another entry
    = # Bad line
    'a key'with" no" value field ;; and not this comment.
    """
    expected = [{"key1": ["a", "list", "of", "fields"]},
                {"key 2": ["another", "entry"]},
                {"a keywith no value field": []}]
    cfg = config_file.KeyValueParser(kv_sep=["=", ":"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertDictEqual(expect, results[i])


class NfsExportParserTests(test_lib.GRRBaseTest):
  """Test the NFS exports parser."""

  def testParseNfsExportFile(self):
    test_data = r"""
    /path/to/foo -rw,sync host1(ro) host2
    /path/to/bar *.example.org(all_squash,ro) \
        192.168.1.0/24 (rw) # Mistake here - space makes this default.
    """
    exports = StringIO.StringIO(test_data)
    config = config_file.NfsExportsParser()
    results = list(config.Parse(None, exports, None))
    self.assertEqual("/path/to/foo", results[0].share)
    self.assertItemsEqual(["rw", "sync"], results[0].defaults)
    self.assertEqual("host1", results[0].clients[0].host)
    self.assertItemsEqual(["ro"], results[0].clients[0].options)
    self.assertEqual("host2", results[0].clients[1].host)
    self.assertItemsEqual([], results[0].clients[1].options)
    self.assertEqual("/path/to/bar", results[1].share)
    self.assertItemsEqual(["rw"], results[1].defaults)
    self.assertEqual("*.example.org", results[1].clients[0].host)
    self.assertItemsEqual(["all_squash", "ro"], results[1].clients[0].options)
    self.assertEqual("192.168.1.0/24", results[1].clients[1].host)
    self.assertItemsEqual([], results[1].clients[1].options)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
