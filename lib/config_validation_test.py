#!/usr/bin/env python
"""Tests for validating the configs we have."""

import glob
import os

import logging

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib


flags.PARSER.add_argument("config", nargs="?",
                          help="Config file to parse")


def ValidateConfig(config_file):
  logging.debug("Processing %s", config_file)
  conf_obj = config_lib.LoadConfig(None, config_file)

  all_sections = conf_obj.GetSections()
  errors = conf_obj.Validate(sections=all_sections)

  return errors


class BuildConfigTests(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  # Server configuration files do not normally have valid client keys.
  exceptions = ["Client.private_key"]

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    configs = []
    configs.append(os.path.join(config_lib.CONFIG.parser.filename))
    for config_file in configs:
      errors = ValidateConfig(config_file)

      for exception in self.exceptions:
        errors.pop(exception, None)

      if errors:
        self.fail("Validation of %s returned errors: %s" % (
            config_file, errors))


def main(argv):
  config_lib.CONFIG.context = flags.FLAGS.context

  if flags.FLAGS.config:
    print "Evaluating config using the context: %s\n" % (
        config_lib.CONFIG.context)

    for error, description in ValidateConfig(flags.FLAGS.config).items():
      print "%s: %s" % (error, description)
  else:
    test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
