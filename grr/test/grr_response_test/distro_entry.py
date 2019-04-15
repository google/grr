#!/usr/bin/env python
"""This file defines the entry points for typical installations."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

# pylint: disable=g-import-not-at-top


def EndToEndTests():
  from grr_response_test import run_end_to_end_tests
  app.run(run_end_to_end_tests.main)


def ApiRegressionTestsGenerate():
  from grr_response_test import api_regression_test_generate
  app.run(api_regression_test_generate.main)


def DumpMySQLSchema():
  from grr_response_test import dump_mysql_schema
  app.run(dump_mysql_schema.main)
