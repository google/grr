#!/usr/bin/env python
"""Tests for grr.parsers.osx_launchd."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.parsers import osx_launchd
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import flow_test_lib
from grr.test_lib import osx_launchd_testdata
from grr.test_lib import test_lib


class OSXLaunchdJobDictTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(OSXLaunchdJobDictTest, self).setUp()
    self.jobdict = osx_launchd_testdata.JOBS
    self.parser = osx_launchd.OSXLaunchdJobDict(self.jobdict)

  def testParseRegex(self):
    filtered = 0
    unfiltered = 0
    for job in self.jobdict:
      if self.parser.FilterItem(job):
        filtered += 1
        self.assertStartsWith(job["Label"], "0x")
      else:
        unfiltered += 1
        self.assertNotStartsWith(job["Label"], "0x")
        self.assertNotIn("anonymous", job["Label"])
        self.assertNotIn("mach_init.crash_inspector", job["Label"])

    num_filtered = osx_launchd_testdata.FILTERED_COUNT
    self.assertEqual(filtered, num_filtered)
    self.assertEqual(unfiltered, len(self.jobdict) - num_filtered)


class DarwinPersistenceMechanismsParserTest(flow_test_lib.FlowTestsBaseclass):

  def testParse(self):
    parser = osx_launchd.DarwinPersistenceMechanismsParser()
    serv_info = rdf_client.OSXServiceInformation(
        label="blah", args=["/blah/test", "-v"])
    results = list(
        parser.Parse(serv_info, None, rdf_paths.PathSpec.PathType.OS))
    self.assertEqual(results[0].pathspec.path, "/blah/test")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
