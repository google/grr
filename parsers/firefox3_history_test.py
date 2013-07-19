#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Tests for grr.parsers.firefox3_history."""



import datetime
import os

from grr.lib import flags
from grr.lib import test_lib
from grr.parsers import firefox3_history


class Firefox3HistoryTest(test_lib.GRRBaseTest):
  """Test parsing of Firefox 3 history files."""

  # places.sqlite contains a single history entry:
  # 2011-07-01 11:16:21.371935	FIREFOX3_VISIT \
  # 	http://news.google.com/	Google News
  def testBasicParsing(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "places.sqlite")
    history = firefox3_history.Firefox3History(open(history_file))
    # Parse returns (timestamp, dtype, url, title)
    entries = [x for x in history.Parse()]

    self.assertEquals(len(entries), 1)

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except (TypeError, ValueError):
      dt1 = entries[0][0]

    self.assertEquals(str(dt1), "2011-07-01 11:16:21.371935")
    self.assertEquals(entries[0][2], "http://news.google.com/")
    self.assertEquals(entries[0][3], "Google News")

  def testNewHistoryFile(self):
    """Tests reading of history files written by recent versions of Firefox."""
    history_file = os.path.join(self.base_path, "new_places.sqlite")
    history = firefox3_history.Firefox3History(open(history_file))
    entries = [x for x in history.Parse()]

    self.assertEquals(len(entries), 3)
    self.assertEquals(entries[1][3],
                      "Slashdot: News for nerds, stuff that matters")
    self.assertEquals(entries[2][0], 1342526323608384L)
    self.assertEquals(entries[2][1], "FIREFOX3_VISIT")
    self.assertEquals(entries[2][2],
                      "https://blog.duosecurity.com/2012/07/exploit-mitigations"
                      "-in-android-jelly-bean-4-1/")


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
