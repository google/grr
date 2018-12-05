#!/usr/bin/env python
"""Tests for grr.parsers.osx_quarantine."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import os

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import osx_quarantine
from grr.test_lib import test_lib


class OSXQuarantineTest(test_lib.GRRBaseTest):
  """Test parsing of osx quarantine files."""

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    infile = os.path.join(self.base_path, "parser_test",
                          "com.apple.LaunchServices.QuarantineEvents")
    parser = osx_quarantine.OSXQuarantineEvents(open(infile))
    entries = [x for x in parser.Parse()]

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

    self.assertEqual(str(dt1), "2011-05-09 13:13:20.897449")
    self.assertEqual(entries[0][2], "http://test.com?output=rss")

    self.assertEqual(str(dt2), "2011-05-11 10:40:18")
    url = "https://hilariouscatsdownload.com/badfile?dat=funny_cats.exe"
    self.assertEqual(entries[-1][2], url)

    self.assertLen(entries, 2)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
