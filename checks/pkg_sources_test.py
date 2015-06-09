#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for package source checks."""

import StringIO


from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.parsers import config_file


class PkgSourceCheckTests(checks_test_lib.HostCheckTest):

  def _GenResults(self):
    self.LoadCheck("pkg_sources.yaml")
    sources = {
        "/etc/apt/sources.list": r"""
            # APT sources.list providing the default Ubuntu packages
            #
            deb https://httpredir.debian.org/debian jessie-updates main
            deb https://security.debian.org/ wheezy/updates main
            # comment 2
            """,
        "/etc/apt/sources.list.d/test.list": r"""
            deb file:/tmp/debs/ distro main
            deb [arch=amd64,blah=blah] [meh=meh] https://securitytestasdf.debian.org/ wheezy/updates main contrib non-free
            deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main
            """,
        "/etc/apt/sources.list.d/test2.list": r"""
            deb http://dl.google.com/linux/chrome/deb/ stable main
            """,
        "/etc/apt/sources.list.d/test3.list": r"""
            deb https://security.debian.org/ wheezy/updates main contrib non-free
            """,
        "/etc/apt/sources.list.d/file-test.list": r"""
            deb file:/mnt/debian/debs/ distro main
            """,
        "/etc/apt/sources.list.d/rfc822.list": r"""
            Type: deb deb-src
            URI: http://security.example.com
              https://dl.google.com
            Suite: testing
            Section: main contrib
            """}
    rdfs = []
    parser = config_file.APTPackageSourceParser()
    stats = []
    for path, lines in sources.items():
      p = rdf_paths.PathSpec(path=path)
      stat = rdf_client.StatEntry(pathspec=p)
      stats.append(stat)
      file_obj = StringIO.StringIO(lines)
      rdfs.extend(list(parser.Parse(stat, file_obj, None)))
    host_data = self.SetKnowledgeBase()
    host_data["APTSources"] = self.SetArtifactData(
        anomaly=[a for a in rdfs if isinstance(a, rdf_anomaly.Anomaly)],
        parsed=[r for r in rdfs if not isinstance(r, rdf_anomaly.Anomaly)],
        raw=stats)
    return self.RunChecks(host_data)

  def testDetectUnsupportedTransport(self):
    chk_id = "CIS-APT-SOURCE-UNSUPPORTED-TRANSPORT"
    exp = "Found: APT sources use unsupported transport."
    found = ["/etc/apt/sources.list.d/test.list: transport: file,https,https",
             "/etc/apt/sources.list.d/test2.list: transport: http",
             "/etc/apt/sources.list.d/file-test.list: transport: file",
             "/etc/apt/sources.list.d/rfc822.list: transport: http,https"]
    results = self._GenResults()
    self.assertCheckDetectedAnom(chk_id, results, exp, found)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)

