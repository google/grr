#!/usr/bin/env python
"""These are the various data store implementations supported by GRR."""


# pylint: disable=g-import-not-at-top,unused-import


from grr.lib.data_stores import fake_data_store
try:
  from grr.lib.data_stores import mongo_data_store
  from grr.lib.data_stores import mongo_data_store_old
except ImportError:
  # Mongo data store not supported.
  pass

try:
  from grr.lib.data_stores import mysql_data_store
except ImportError:
  # MySql data store not supported.
  pass

