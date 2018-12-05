#!/usr/bin/env python
"""Unit test for check definitions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import os


from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_server.check_lib import checks_test_lib
from grr.test_lib import test_lib


class ValidFormatTest(checks_test_lib.HostCheckTest):

  def testParseChecks(self):
    """Tests if checks verify, collates errors to diagnose invalid checks."""
    # Find the configs.
    check_configs = []
    for path in config.CONFIG["Checks.config_dir"]:
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
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
