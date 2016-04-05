#!/usr/bin/env python
"""Unit test for check definitions."""

import glob
import os


from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.checks import checks_test_lib


class ValidFormatTest(checks_test_lib.HostCheckTest):

  def testParseChecks(self):
    """Tests if checks verify, collates errors to diagnose invalid checks."""
    # Find the configs.
    check_configs = []
    for path in config_lib.CONFIG["Checks.config_dir"]:
      check_configs.extend(glob.glob(os.path.join(path, "*.yaml")))
    # Check each config file and collate errors.
    errors = ""
    for f in check_configs:
      try:
        self.assertValidCheckFile(f)
      except AssertionError as e:
        errors += "%s\n" % e
    self.assertFalse(errors, "Errors in check configurations:\n%s" % errors)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
