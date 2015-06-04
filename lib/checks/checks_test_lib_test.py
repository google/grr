#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for checks_test_lib."""

from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks
from grr.lib.checks import checks_test_lib
from grr.lib.rdfvalues import anomaly as rdf_anomaly


class CheckHelperTests(checks_test_lib.HostCheckTest):
  """Tests for common Check Helper methods."""

  def testAssertCheckUndetected(self):
    """Tests for the asertCheckUndetected() method."""
    anomaly = {"finding": ["Adware 2.1.1 is installed"],
               "explanation": "Found: Malicious software.",
               "type": "ANALYSIS_ANOMALY"}

    # Simple no anomaly case.
    no_anomaly = {"SW-CHECK": checks.CheckResult(check_id="SW-CHECK")}
    self.assertCheckUndetected("SW-CHECK", no_anomaly)

    # The case were there is an anomaly in the results, just not the check
    # we are looking for.
    other_anomaly = {
        "SW-CHECK": checks.CheckResult(check_id="SW-CHECK"),
        "OTHER": checks.CheckResult(
            check_id="OTHER", anomaly=rdf_anomaly.Anomaly(**anomaly))}
    self.assertCheckUndetected("SW-CHECK", other_anomaly)

    # Check the simple failure case works.
    has_anomaly = {"SW-CHECK": checks.CheckResult(
        check_id="SW-CHECK", anomaly=rdf_anomaly.Anomaly(**anomaly))}
    self.assertRaises(AssertionError,
                      self.assertCheckUndetected, "SW-CHECK", has_anomaly)

  def testAssertRanChecks(self):
    """Test for the assertRanChecks() method."""
    no_checks = {}
    some_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}

    self.assertRanChecks(["EXISTS"], some_checks)
    self.assertRaises(AssertionError,
                      self.assertRanChecks,
                      ["EXISTS"], no_checks)
    self.assertRaises(AssertionError,
                      self.assertRanChecks,
                      ["FOOBAR"], some_checks)

  def testAssertChecksNotRun(self):
    """Test for the assertChecksNotRun() method."""
    no_checks = {}
    some_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}

    self.assertChecksNotRun(["FOOBAR"], no_checks)
    self.assertChecksNotRun(["FOO", "BAR"], no_checks)
    self.assertChecksNotRun(["FOOBAR"], some_checks)
    self.assertChecksNotRun(["FOO", "BAR"], some_checks)

    self.assertRaises(AssertionError,
                      self.assertChecksNotRun,
                      ["EXISTS"], some_checks)
    self.assertRaises(AssertionError,
                      self.assertChecksNotRun,
                      ["FOO", "EXISTS", "BAR"], some_checks)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
