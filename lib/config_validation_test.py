#!/usr/bin/env python
"""Tests for validating the configs we have."""

import glob
import os

import logging

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


flags.PARSER.add_argument("config", nargs="?",
                          help="Config file to parse")


def ValidateConfig(config_file=None):
  """Iterate over all the sections in the config file and validate them."""
  logging.debug("Processing %s", config_file)

  if isinstance(config_file, config_lib.GrrConfigManager):
    conf_obj = config_file
  else:
    conf_obj = config_lib.CONFIG
    conf_obj.Initialize(config_file, reset=True)

  all_sections = conf_obj.GetSections()
  errors = conf_obj.Validate(sections=all_sections)

  return errors


class BuildConfigTests(test_lib.GRRBaseTest):
  """Tests for config functionality."""

  # Server configuration files do not normally have valid client keys.
  exceptions = ["Client.private_key",
                "PrivateKeys.executable_signing_private_key",
                "PrivateKeys.server_key", "PrivateKeys.ca_key",
                "PrivateKeys.driver_signing_private_key"]

  disabled_filters = [
      ]

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    configs = []

    # Test the current loaded configuration.
    configs.append(config_lib.CONFIG)

    test_filter_map = config_lib.ConfigFilter.classes_by_name
    for filter_name in self.disabled_filters:
      test_filter_map[filter_name] = config_lib.ConfigFilter

    with utils.Stubber(config_lib.ConfigFilter, "classes_by_name",
                       test_filter_map):
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
