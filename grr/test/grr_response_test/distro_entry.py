#!/usr/bin/env python
"""This file defines the entry points for typical installations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags

# pylint: disable=g-import-not-at-top


def EndToEndTests():
  from grr_response_test import run_end_to_end_tests
  flags.StartMain(run_end_to_end_tests.main)


def ApiRegressionTestsGenerate():
  from grr_response_test import api_regression_test_generate
  flags.StartMain(api_regression_test_generate.main)
