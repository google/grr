#!/usr/bin/env python
"""Tests for validating the configs we have."""

import glob
import os

import logging

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils


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

  # The executables dir may be missing
  exceptions.append("ClientBuilder.executables_dir")

  disabled_filters = [
  ]

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    # Test the current loaded configuration.
    configs = [config_lib.CONFIG]

    # Test all the other configs in the server config dir (/etc/grr by default)
    glob_path = os.path.join(config_lib.CONFIG["Config.directory"], "*.yaml")
    for cfg_file in glob.glob(glob_path):
      if os.access(cfg_file, os.R_OK):
        configs.append(cfg_file)
      else:
        logging.info(
            "Skipping checking %s, you probably need to be root" % cfg_file)

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
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
