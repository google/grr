#!/usr/bin/env python
#
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for grr.parsers.osx_quarantine."""



import datetime
import os

from grr.client import conf
from grr.client import conf as flags
from grr.lib import test_lib
from grr.parsers import osx_quarantine

FLAGS = flags.FLAGS


# pylint: disable=C6409


class OSXQuarantineTest(test_lib.GRRBaseTest):
  """Test parsing of osx quarantine files."""

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    infile = os.path.join(self.base_path,
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

    self.assertEquals(str(dt1), "2011-05-09 13:13:20.897449")
    self.assertEquals(entries[0][2], "http://test.com?output=rss")

    self.assertEquals(str(dt2), "2011-05-11 10:40:18")
    url = "https://hilariouscatsdownload.com/badfile?dat=funny_cats.exe"
    self.assertEquals(entries[-1][2], url)

    self.assertEquals(len(entries), 2)


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
