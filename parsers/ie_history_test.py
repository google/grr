#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""Tests for grr.parsers.ie_history."""



import datetime
import os
import StringIO

from grr.client import conf
from grr.client import conf as flags
from grr.lib import test_lib
from grr.parsers import ie_history

FLAGS = flags.FLAGS


# pylint: disable=C6409


class IEHistoryTest(test_lib.GRRBaseTest):
  """Test parsing of chrome history files."""

  def testBasicParsing(self):
    """Test we can parse a standard file."""
    hist_file = os.path.join(self.base_path, "index.dat")
    c = ie_history.IEParser(open(hist_file))
    entries = [x for x in c.Parse()]
    self.assertEquals(entries[1]["url"],
                      "Visited: testing@http://www.trafficfusionx.com/"
                      "download/tfscrn2/funnycats.exe")
    dt1 = datetime.datetime.utcfromtimestamp(entries[1]["ctime"] / 1e6)
    self.assertEquals(str(dt1), "2011-06-23 18:01:45.238000")
    dt2 = datetime.datetime.utcfromtimestamp(entries[-1]["ctime"] / 1e6)
    self.assertEquals(str(dt2), "2010-05-14 18:29:41.531000")
    self.assertEquals(entries[-1]["url"],
                      "Visited: testing@http://get.adobe.com/flashplayer/thankyou/activex/?installer=Flash_Player_10_for_Windows_Internet_Explorer&i=McAfee_Security_Scan_Plus&d=Google_Toolbar_6.3")
    self.assertEquals(len(entries), 18)

  def testErrors(self):
    """Test empty files don't raise errors."""
    c = ie_history.IEParser(StringIO.StringIO())
    entries = [x for x in c.Parse()]
    self.assertEquals(len(entries), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  conf.StartMain(main)
