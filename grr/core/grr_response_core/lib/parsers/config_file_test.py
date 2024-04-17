#!/usr/bin/env python
"""Unit test for config files."""

from absl import app

from grr_response_core.lib.parsers import config_file
from grr.test_lib import test_lib

CFG = b"""
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


class FieldParserTests(test_lib.GRRBaseTest):
  """Test the field parser."""

  def testParser(self):
    test_data = r"""
    each of these words:should;be \
        fields # but not these ones \n, or \ these.
    this  should be     another entry "with this quoted text as one field"
    'an entry'with" only two" fields ;; and not this comment.
    """
    expected = [
        ["each", "of", "these", "words", "should", "be", "fields"],
        [
            "this",
            "should",
            "be",
            "another",
            "entry",
            "with this quoted text as one field",
        ],
        ["an entrywith only two", "fields"],
    ]
    cfg = config_file.FieldParser(
        sep=["[ \t\f\v]+", ":", ";"], comments=["#", ";;"]
    )
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])

  def testNoFinalTerminator(self):
    test_data = "you forgot a newline"
    expected = [["you", "forgot", "a", "newline"]]
    cfg = config_file.FieldParser()
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])

  def testWhitespaceDoesntNukeNewline(self):
    test_data = "trailing spaces     \nno trailing spaces\n"
    expected = [["trailing", "spaces"], ["no", "trailing", "spaces"]]
    results = config_file.FieldParser().ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])
    expected = [["trailing", "spaces", "no", "trailing", "spaces"]]
    results = config_file.FieldParser(sep=r"\s+").ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertCountEqual(expect, results[i])


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
    expected = [
        {"key1": ["a", "list", "of", "fields"]},
        {"key 2": ["another", "entry"]},
        {"a keywith no value field": []},
    ]
    cfg = config_file.KeyValueParser(kv_sep=["=", ":"], comments=["#", ";;"])
    results = cfg.ParseEntries(test_data)
    for i, expect in enumerate(expected):
      self.assertDictEqual(expect, results[i])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
