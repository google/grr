#!/usr/bin/env python
"""Tests for validating the configs we have."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import logging
import os

from grr_response_core import config
from grr_response_core.lib import config_testing_lib
from grr_response_core.lib import flags
from grr.test_lib import test_lib


class BuildConfigTests(config_testing_lib.BuildConfigTestsBase):

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    # Test the current loaded configuration.
    configs = [config.CONFIG]

    # Test all the other configs in the server config dir (/etc/grr by default)
    glob_path = os.path.join(config.CONFIG["Config.directory"], "*.yaml")
    for cfg_file in glob.glob(glob_path):
      if os.access(cfg_file, os.R_OK):
        configs.append(cfg_file)
      else:
        logging.info("Skipping checking %s, you probably need to be root",
                     cfg_file)

    self.ValidateConfigs(configs)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
