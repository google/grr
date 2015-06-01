#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for speedway state checks."""
import StringIO


from grr.lib import flags
from grr.lib import parsers
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class SpeedwayTests(checks_test_lib.HostCheckTest):

  results = None
  checks_loaded = False

  def setUp(self, *args, **kwargs):
    super(SpeedwayTests, self).setUp(*args, **kwargs)
    if not self.checks_loaded:
      self.LoadCheck("speedway.yaml")
      self.checks_loaded = True

  def _GenResults(self, artifact, data):
    host_data = self.SetKnowledgeBase()
    stats = []
    files = []
    for path, lines in data.items():
      p = rdf_paths.PathSpec(path=path)
      stats.append(rdf_client.StatEntry(pathspec=p))
      files.append(StringIO.StringIO(lines))
    parser = parsers.FileParser()
    rdfs = parser.ParseMultiple(stats, files, host_data["KnowledgeBase"])
    if rdfs is None:
      rdfs = []
    else:
      rdfs = list(rdfs)
    host_data[artifact] = rdfs
    return self.RunChecks(host_data)

  def testSpeedwayAtBoot(self):
    exp = "Missing attribute: Speedway not configured to start at boot time."
    found = ["Expected state was not found"]
    bad = {}
    good = {"/etc/rc2.d/S88speedway": """Arbitary Text."""}

    self.assertCheckDetectedAnom("SOX-SPDWAY-STARTUP",
                                 self._GenResults("SpeedwayStartup", bad),
                                 exp, found)
    self.assertCheckUndetected("SOX-SPDWAY-STARTUP",
                               self._GenResults("SpeedwayStartup", good))

  def testSpeedwaySlackRoleInstalled(self):
    exp = "Missing attribute: Speedway slack role is not installed."
    found = ["Expected state was not found"]
    bad = {}
    good = {"/var/lib/slack/stage/roles/speedway.valentine": """Junk."""}

    self.assertCheckDetectedAnom("SOX-SPDWAY-INSTALL",
                                 self._GenResults("SpeedwayInstalled", bad),
                                 exp, found)
    self.assertCheckUndetected("SOX-SPDWAY-INSTALL",
                               self._GenResults("SpeedwayInstalled", good))


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
