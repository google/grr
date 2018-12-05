#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for grr.parsers.firefox3_history."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import firefox3_history
from grr.test_lib import test_lib


class Firefox3HistoryTest(test_lib.GRRBaseTest):
  """Test parsing of Firefox 3 history files."""

  # places.sqlite contains a single history entry:
  # 2011-07-01 11:16:21.371935, FIREFOX3_VISIT,
  # http://news.google.com/, Google News

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "places.sqlite")
    history = firefox3_history.Firefox3History(open(history_file, "rb"))
    # Parse returns (timestamp, dtype, url, title)
    entries = [x for x in history.Parse()]

    self.assertLen(entries, 1)

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except (TypeError, ValueError):
      dt1 = entries[0][0]

    self.assertEqual(str(dt1), "2011-07-01 11:16:21.371935")
    self.assertEqual(entries[0][2], "http://news.google.com/")
    self.assertEqual(entries[0][3], "Google News")

  def testNewHistoryFile(self):
    """Tests reading of history files written by recent versions of Firefox."""
    history_file = os.path.join(self.base_path, "new_places.sqlite")
    history = firefox3_history.Firefox3History(open(history_file, "rb"))
    entries = [x for x in history.Parse()]

    self.assertLen(entries, 3)
    self.assertEqual(entries[1][3],
                     "Slashdot: News for nerds, stuff that matters")
    self.assertEqual(entries[2][0], 1342526323608384)
    self.assertEqual(entries[2][1], "FIREFOX3_VISIT")
    self.assertEqual(
        entries[2][2],
        "https://blog.duosecurity.com/2012/07/exploit-mitigations"
        "-in-android-jelly-bean-4-1/")

    # Check that our results are properly time ordered
    time_results = [x[0] for x in entries]
    self.assertEqual(time_results, sorted(time_results))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
