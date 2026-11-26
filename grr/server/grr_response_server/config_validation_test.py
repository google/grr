#!/usr/bin/env python
"""Tests for validating the configs we have."""

from collections.abc import Sequence
import glob
import logging
import os
from typing import Any

from absl import app

from grr_response_core import config
from grr_response_core.lib import config_testing_lib
from grr.test_lib import test_lib


class BuildConfigTests(config_testing_lib.BuildConfigTestsBase):

  def testAllConfigs(self):
    """Go through all our config files looking for errors."""
    # Test the current loaded configuration.
    configs: list[Any] = [config.CONFIG]

    # Test all the other configs in the server config dir (/etc/grr by default)
    glob_path = os.path.join(config.CONFIG["Config.directory"], "*.yaml")
    for cfg_file in glob.glob(glob_path):
      if os.access(cfg_file, os.R_OK):
        configs.append(cfg_file)
      else:
        logging.info(
            "Skipping checking %s, you probably need to be root", cfg_file
        )

    self.ValidateConfigs(configs)


def main(argv: Sequence[str]) -> None:
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
