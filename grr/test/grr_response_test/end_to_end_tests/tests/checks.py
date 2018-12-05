#!/usr/bin/env python
"""End to end tests for GRR checks."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestCheckRunner(test_base.EndToEndTest):
  """Test RunChecks flow."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    check_ids = [
        "CIS-LOGIN-UNIX-HASH", "CIS-NET-SYNCOOKIES", "CIS-SSH-PROTOCOL",
        "CIS-NET-LOGMART"
    ]

    args = self.grr_api.types.CreateFlowArgs("CheckRunner")
    args.restrict_checks.extend(check_ids)
    f = self.RunFlowAndWait("CheckRunner", args=args)

    # Results are expected to be of a CheckResult type.
    results = list(f.ListResults())
    checks_run = [r.payload.check_id for r in results]
    self.assertCountEqual(check_ids, checks_run)
