#!/usr/bin/env python
"""Tests for validating the configs we have."""

import glob
import os

from grr.client import conf
import logging

from grr.lib import config_lib
from grr.lib import test_lib


class BuildConfigTests(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    # TODO(user): Automatically collect the sections that are not override
    #               sections to validate.
    validate_sections = ["AdminUI", "Datastore", "Frontend", "Logging",
                         "Frontend"]

    configs = [os.path.join(config_lib.CONFIG["Test.srcdir"], "grr", "config",
                            "grr_test.conf")]

    configs.append(os.path.join(config_lib.CONFIG["Test.config"]))
    self.assertGreater(len(configs), 1)
    for config_file in configs:
      logging.debug("Processing %s", config_file)
      conf_obj = config_lib.LoadConfig(None, config_file=config_file)
      all_sections = conf_obj.GetSections()
      for section in all_sections:
        if section in validate_sections:
          conf_obj.Validate(section)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  conf.StartMain(main)
