#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Tests for grr.parsers.chrome_history."""



import datetime
import os

from grr.lib import flags
from grr.lib import test_lib
from grr.parsers import chrome_history


class ChromeHistoryTest(test_lib.GRRBaseTest):
  """Test parsing of chrome history files."""

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "History2")
    history = chrome_history.ChromeParser(open(history_file))
    entries = [x for x in history.Parse()]

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except TypeError:
      dt1 = entries[0][0]
    except ValueError:
      dt1 = entries[0][0]

    try:
      dt2 = datetime.datetime(1970, 1, 1)
      dt2 += datetime.timedelta(microseconds=entries[-1][0])
    except TypeError:
      dt2 = entries[-1][0]
    except ValueError:
      dt2 = entries[-1][0]

    self.assertEquals(str(dt1), "2013-05-03 15:11:26.556635")

    self.assertTrue(entries[0][2].startswith(
        "https://www.google.ch/search?q=why+you+shouldn"))

    self.assertEquals(str(dt2), "2013-05-03 15:11:39.763984")
    self.assertTrue(entries[-1][2].startswith("http://www.test.ch/"))
    self.assertEquals(len(entries), 4)

  def testBasicParsingOldFormat(self):
    """Test we can parse a standard file."""
    history_file = os.path.join(self.base_path, "History")
    history = chrome_history.ChromeParser(open(history_file))
    entries = [x for x in history.Parse()]

    try:
      dt1 = datetime.datetime(1970, 1, 1)
      dt1 += datetime.timedelta(microseconds=entries[0][0])
    except TypeError:
      dt1 = entries[0][0]
    except ValueError:
      dt1 = entries[0][0]

    try:
      dt2 = datetime.datetime(1970, 1, 1)
      dt2 += datetime.timedelta(microseconds=entries[-1][0])
    except TypeError:
      dt2 = entries[-1][0]
    except ValueError:
      dt2 = entries[-1][0]

    self.assertEquals(str(dt1), "2011-04-07 12:03:11")
    self.assertEquals(entries[0][2], "http://start.ubuntu.com/10.04/Google/")

    self.assertEquals(str(dt2), "2011-05-23 08:36:05")
    self.assertEquals(entries[-1][2],
                      "http://www.photoscreensavers.us/Cats%20Demo.exe")

    self.assertEquals(len(entries), 71)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
