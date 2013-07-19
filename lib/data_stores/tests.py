#!/usr/bin/env python
"""GRR data store tests.

This module loads and registers all the data store tests.
"""


# These need to register plugins so, pylint: disable=unused-import,g-import-not-at-top

from grr.lib.data_stores import fake_data_store_test
try:
  from grr.lib.data_stores import mongo_data_store_test
  # This is deprecated and some tests fail.
  # pylint: disable=g-line-too-long
  # from grr.lib.data_stores import mongo_data_store_old_test
  # pylint: enable=g-line-too-long
except ImportError:
  pass

try:
  from grr.lib.data_stores import mysql_data_store_test
except ImportError:
  pass
