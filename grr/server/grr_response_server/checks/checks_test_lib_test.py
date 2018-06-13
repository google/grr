#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks_test_lib."""

from grr.lib import flags
from grr.lib import parser
from grr.lib.rdfvalues import anomaly as rdf_anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server.checks import checks
from grr.server.grr_response_server.checks import checks_test_lib
from grr.test_lib import test_lib


class CheckHelperTests(checks_test_lib.HostCheckTest):
  """Tests for common Check Helper methods."""

  def testAssertCheckUndetected(self):
    """Tests for the asertCheckUndetected() method."""
    anomaly = {
        "finding": ["Adware 2.1.1 is installed"],
        "symptom": "Found: Malicious software.",
        "type": "ANALYSIS_ANOMALY"
    }

    # Simple no anomaly case.
    no_anomaly = {"SW-CHECK": checks.CheckResult(check_id="SW-CHECK")}
    self.assertCheckUndetected("SW-CHECK", no_anomaly)

    # The case were there is an anomaly in the results, just not the check
    # we are looking for.
    other_anomaly = {
        "SW-CHECK":
            checks.CheckResult(check_id="SW-CHECK"),
        "OTHER":
            checks.CheckResult(
                check_id="OTHER", anomaly=rdf_anomaly.Anomaly(**anomaly))
    }
    self.assertCheckUndetected("SW-CHECK", other_anomaly)

    # Check the simple failure case works.
    has_anomaly = {
        "SW-CHECK":
            checks.CheckResult(
                check_id="SW-CHECK", anomaly=rdf_anomaly.Anomaly(**anomaly))
    }
    self.assertRaises(AssertionError, self.assertCheckUndetected, "SW-CHECK",
                      has_anomaly)

  def testAssertRanChecks(self):
    """Tests for the assertRanChecks() method."""
    no_checks = {}
    some_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}

    self.assertRanChecks(["EXISTS"], some_checks)
    self.assertRaises(AssertionError, self.assertRanChecks, ["EXISTS"],
                      no_checks)
    self.assertRaises(AssertionError, self.assertRanChecks, ["FOOBAR"],
                      some_checks)

  def testAssertChecksNotRun(self):
    """Tests for the assertChecksNotRun() method."""
    no_checks = {}
    some_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}

    self.assertChecksNotRun(["FOOBAR"], no_checks)
    self.assertChecksNotRun(["FOO", "BAR"], no_checks)
    self.assertChecksNotRun(["FOOBAR"], some_checks)
    self.assertChecksNotRun(["FOO", "BAR"], some_checks)

    self.assertRaises(AssertionError, self.assertChecksNotRun, ["EXISTS"],
                      some_checks)
    self.assertRaises(AssertionError, self.assertChecksNotRun,
                      ["FOO", "EXISTS", "BAR"], some_checks)

  def testAssertCheckDetectedAnom(self):
    """Tests for the assertCheckDetectedAnom() method."""

    # Check we fail when our checkid isn't in the results.
    no_checks = {}
    self.assertRaises(
        AssertionError,
        self.assertCheckDetectedAnom,
        "UNICORN",
        no_checks,
        sym=None,
        findings=None)

    # Check we fail when our checkid is in the results but hasn't
    # produced an anomaly.
    passing_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}
    self.assertRaises(
        AssertionError,
        self.assertCheckDetectedAnom,
        "EXISTS",
        passing_checks,
        sym=None,
        findings=None)

    # On to a 'successful' cases.
    anomaly = {
        "finding": ["Finding"],
        "symptom": "Found: An issue.",
        "type": "ANALYSIS_ANOMALY"
    }
    failing_checks = {
        "EXISTS":
            checks.CheckResult(
                check_id="EXISTS", anomaly=rdf_anomaly.Anomaly(**anomaly))
    }

    # Check we pass when our check produces an anomaly and we don't care
    # about the details.
    self.assertCheckDetectedAnom(
        "EXISTS", failing_checks, sym=None, findings=None)
    # When we do care only about the 'symptom'.
    self.assertCheckDetectedAnom(
        "EXISTS", failing_checks, sym="Found: An issue.", findings=None)
    # And when we also care about the findings.
    self.assertCheckDetectedAnom(
        "EXISTS", failing_checks, sym="Found: An issue.", findings=["Finding"])
    # And check we match substrings of a 'finding'.
    self.assertCheckDetectedAnom(
        "EXISTS", failing_checks, sym="Found: An issue.", findings=["Fin"])
    # Check we complain when the symptom doesn't match.
    self.assertRaises(
        AssertionError,
        self.assertCheckDetectedAnom,
        "EXISTS",
        failing_checks,
        sym="wrong symptom",
        findings=None)
    # Check we complain when the symptom matches but the findings don't.
    self.assertRaises(
        AssertionError,
        self.assertCheckDetectedAnom,
        "EXISTS",
        failing_checks,
        sym="Found: An issue.",
        findings=["Not found"])
    # Lastly, if there is a finding in the anomaly we didn't expect, we consider
    # that a problem.
    self.assertRaises(
        AssertionError,
        self.assertCheckDetectedAnom,
        "EXISTS",
        failing_checks,
        sym="Found: An issue.",
        findings=[])

  def testGenProcessData(self):
    """Test for the GenProcessData() method."""
    # Trivial empty case.
    art_name = "ListProcessesGrr"
    context = "RAW"
    result = self.GenProcessData([])
    self.assertTrue("KnowledgeBase" in result)
    self.assertTrue(art_name in result)
    self.assertDictEqual(self.SetArtifactData(), result[art_name])
    # Now with data.
    result = self.GenProcessData([("proc1", 1, ["/bin/foo"]), ("proc2", 2,
                                                               ["/bin/bar"])])
    self.assertEquals("proc1", result[art_name][context][0].name)
    self.assertEquals(1, result[art_name][context][0].pid)
    self.assertEquals(["/bin/foo"], result[art_name][context][0].cmdline)
    self.assertEquals("proc2", result[art_name][context][1].name)
    self.assertEquals(2, result[art_name][context][1].pid)
    self.assertEquals(["/bin/bar"], result[art_name][context][1].cmdline)

  def testGenFileData(self):
    """Test for the GenFileData() method."""
    # Need a parser
    self.assertRaises(ValueError, self.GenFileData, "EMPTY", [])
    # Trivial empty case.
    file_parser = parser.FileParser()
    result = self.GenFileData("EMPTY", [], file_parser)
    self.assertTrue("KnowledgeBase" in result)
    self.assertTrue("EMPTY" in result)
    self.assertDictEqual(self.SetArtifactData(), result["EMPTY"])
    # Now with data.
    result = self.GenFileData("FILES", {
        "/tmp/foo": """blah""",
        "/tmp/bar": """meh"""
    }, file_parser)
    self.assertTrue("FILES" in result)
    # No parser information should be generated.
    self.assertEquals([], result["FILES"]["PARSER"])
    # Two stat entries under raw (stat entries should exist)
    self.assertEquals(2, len(result["FILES"]["RAW"]))
    # Walk the result till we find the item we want.
    # This is to avoid a flakey test.
    statentry = None
    for r in result["FILES"]["RAW"]:
      if r.pathspec.path == "/tmp/bar":
        statentry = r
    self.assertIsInstance(statentry, rdf_client.StatEntry)
    self.assertEquals(33188, statentry.st_mode)

  def testGenSysVInitData(self):
    """Test for the GenSysVInitData() method."""
    # Trivial empty case.
    result = self.GenSysVInitData([])
    self.assertTrue("KnowledgeBase" in result)
    self.assertTrue("LinuxServices" in result)
    self.assertDictEqual(self.SetArtifactData(), result["LinuxServices"])
    # Now with data.
    result = self.GenSysVInitData(["/etc/rc2.d/S99testing"])
    self.assertTrue("LinuxServices" in result)
    self.assertEquals(1, len(result["LinuxServices"]["PARSER"]))
    result = result["LinuxServices"]["PARSER"][0]
    self.assertEquals("testing", result.name)
    self.assertEquals([2], result.start_on)
    self.assertTrue(result.starts)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
