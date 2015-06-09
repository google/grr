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
    """Tests for the assertRanChecks() method."""
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
    """Tests for the assertChecksNotRun() method."""
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

  def testAssertCheckDetectedAnom(self):
    """Tests for the assertCheckDetectedAnom() method."""

    # Check we fail when our checkid isn't in the results.
    no_checks = {}
    self.assertRaises(AssertionError,
                      self.assertCheckDetectedAnom,
                      "UNICORN",
                      no_checks,
                      exp=None,
                      findings=None)

    # Check we fail when our checkid is in the results but hasn't
    # produced an anomaly.
    passing_checks = {"EXISTS": checks.CheckResult(check_id="EXISTS")}
    self.assertRaises(AssertionError,
                      self.assertCheckDetectedAnom,
                      "EXISTS",
                      passing_checks,
                      exp=None,
                      findings=None)

    # On to a 'successful' cases.
    anomaly = {"finding": ["Finding"],
               "explanation": "Found: An issue.",
               "type": "ANALYSIS_ANOMALY"}
    failing_checks = {"EXISTS": checks.CheckResult(
        check_id="EXISTS",
        anomaly=rdf_anomaly.Anomaly(**anomaly))}

    # Check we pass when our check produces an anomaly and we don't care
    # about the details.
    self.assertCheckDetectedAnom("EXISTS", failing_checks,
                                 exp=None, findings=None)
    # When we do care only about the 'explanation'.
    self.assertCheckDetectedAnom("EXISTS", failing_checks,
                                 exp="Found: An issue.", findings=None)
    # And when we also care about the findings.
    self.assertCheckDetectedAnom("EXISTS", failing_checks,
                                 exp="Found: An issue.",
                                 findings=["Finding"])
    # And check we match substrings of a 'finding'.
    self.assertCheckDetectedAnom("EXISTS", failing_checks,
                                 exp="Found: An issue.",
                                 findings=["Fin"])
    # Check we complain when the explanation doesn't match.
    self.assertRaises(AssertionError,
                      self.assertCheckDetectedAnom,
                      "EXISTS",
                      failing_checks,
                      exp="wrong explanation",
                      findings=None)
    # Check we complain when the explanation matches but the findings don't.
    self.assertRaises(AssertionError,
                      self.assertCheckDetectedAnom,
                      "EXISTS",
                      failing_checks,
                      exp="Found: An issue.",
                      findings=["Not found"])
    # Lastly, if there is a finding in the anomaly we didn't expect, we consider
    # that a problem.
    self.assertRaises(AssertionError,
                      self.assertCheckDetectedAnom,
                      "EXISTS",
                      failing_checks,
                      exp="Found: An issue.",
                      findings=[])


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
