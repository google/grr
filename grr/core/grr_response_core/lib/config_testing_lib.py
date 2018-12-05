#!/usr/bin/env python
"""Helper library for config testing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import copy
import logging


from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import utils
from grr.test_lib import test_lib


class BuildConfigTestsBase(test_lib.GRRBaseTest):
  """Base for config functionality tests."""

  exceptions = [
      # Server configuration files do not normally have valid client keys.
      "Client.private_key",
      # Those keys are maybe passphrase protected so we need to skip.
      "PrivateKeys.ca_key",
      "PrivateKeys.executable_signing_private_key",
      "PrivateKeys.server_key",
  ]

  # For all the resource filters to work you need the grr-response-templates
  # package, which is big.
  disabled_filters = ["resource", "file"]

  def ValidateConfig(self, config_file=None):
    """Iterate over all the sections in the config file and validate them."""
    logging.debug("Processing %s", config_file)

    if isinstance(config_file, config_lib.GrrConfigManager):
      conf_obj = config_file
    else:
      conf_obj = config.CONFIG.MakeNewConfig()
      conf_obj.Initialize(filename=config_file, reset=True)

    with utils.MultiStubber((config, "CONFIG", conf_obj),
                            (config_lib, "_CONFIG", conf_obj)):
      all_sections = conf_obj.GetSections()
      errors = conf_obj.Validate(sections=all_sections)

    return errors

  def ValidateConfigs(self, configs):
    test_filter_map = copy.deepcopy(config_lib.ConfigFilter.classes_by_name)
    for filter_name in self.disabled_filters:
      test_filter_map[filter_name] = config_lib.ConfigFilter

    with utils.Stubber(config_lib.ConfigFilter, "classes_by_name",
                       test_filter_map):
      for config_file in configs:
        errors = self.ValidateConfig(config_file)

        for exception in self.exceptions:
          errors.pop(exception, None)

        if errors:
          logging.info("Validation of %s returned errors:", config_file)
          for config_entry, error in iteritems(errors):
            logging.info("%s:", config_entry)
            logging.info("%s", error)

          self.fail("Validation of %s returned errors: %s" % (config_file,
                                                              errors))
