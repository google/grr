#!/usr/bin/env python
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


"""Tests for grr.parsers.osx_launchd."""




from grr.client import conf

from grr.lib import test_lib
from grr.parsers import osx_launchd
from grr.test_data import osx_launchd as testdata


class OSXLaunchdJobDictTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(OSXLaunchdJobDictTest, self).setUp()
    self.jobdict = testdata.JOBS
    self.parser = osx_launchd.OSXLaunchdJobDict(self.jobdict)

  def testParseRegex(self):
    filtered = 0
    unfiltered = 0
    for job in self.jobdict:
      if self.parser.FilterItem(job):
        filtered += 1
        self.assertTrue(job['Label'].startswith('0x'), job['Label'])
      else:
        unfiltered += 1
        self.assertFalse(job['Label'].startswith('0x'), job['Label'])
        self.assertFalse('anonymous' in job['Label'], job['Label'])
        self.assertFalse('mach_init.crash_inspector' in job['Label'],
                         job['Label'])

    self.assertEqual(filtered, testdata.FILTERED_COUNT)
    self.assertEqual(unfiltered, len(testdata.JOBS) - testdata.FILTERED_COUNT)


def main(argv):
  test_lib.main(argv)


if __name__ == '__main__':
  conf.StartMain(main)
