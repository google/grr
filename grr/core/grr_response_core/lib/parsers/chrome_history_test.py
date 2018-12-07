#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for grr.parsers.chrome_history."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import chrome_history
from grr.test_lib import test_lib


class ChromeHistoryTest(test_lib.GRRBaseTest):
  """Test parsing of chrome history files."""

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "parser_test", "History2")
    history = chrome_history.ChromeParser(open(history_file, "rb"))
    entries = [x for x in history.Parse()]

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except (TypeError, ValueError):
      dt1 = entries[0][0]

    try:
      dt2 = datetime.datetime(1970, 1, 1)
      dt2 += datetime.timedelta(microseconds=entries[-1][0])
    except (TypeError, ValueError):
      dt2 = entries[-1][0]

    # Check that our results are properly time ordered
    time_results = [x[0] for x in entries]
    self.assertEqual(time_results, sorted(time_results))

    self.assertEqual(str(dt1), "2013-05-03 15:11:26.556635")
    self.assertStartsWith(entries[0][2],
                          "https://www.google.ch/search?q=why+you+shouldn")

    self.assertEqual(str(dt2), "2013-05-03 15:11:39.763984")
    self.assertStartsWith(entries[-1][2], "http://www.test.ch/")

    self.assertLen(entries, 4)

  def testTimeOrderingDownload(self):
    """Test we can correctly time order downloads and visits."""
    history_file = os.path.join(self.base_path, "parser_test", "History3")
    history = chrome_history.ChromeParser(open(history_file, "rb"))
    entries = [x for x in history.Parse()]

    # Check that our results are properly time ordered
    time_results = [x[0] for x in entries]
    self.assertEqual(time_results, sorted(time_results))
    self.assertLen(entries, 23)

  def testBasicParsingOldFormat(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "parser_test", "History")
    history = chrome_history.ChromeParser(open(history_file, "rb"))
    entries = [x for x in history.Parse()]

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except (TypeError, ValueError):
      dt1 = entries[0][0]

    try:
      dt2 = datetime.datetime(1970, 1, 1)
      dt2 += datetime.timedelta(microseconds=entries[-1][0])
    except (TypeError, ValueError):
      dt2 = entries[-1][0]

    # Check that our results are properly time ordered
    time_results = [x[0] for x in entries]
    self.assertEqual(time_results, sorted(time_results))

    self.assertEqual(str(dt1), "2011-04-07 12:03:11")
    self.assertEqual(entries[0][2], "http://start.ubuntu.com/10.04/Google/")

    self.assertEqual(str(dt2), "2011-05-23 08:37:27.061516")
    self.assertStartsWith(
        entries[-1][2], "https://chrome.google.com/webs"
        "tore/detail/mfjkgbjaikamkkojmak"
        "jclmkianficch")

    self.assertLen(entries, 71)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
