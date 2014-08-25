#!/usr/bin/env python
"""These are the various data store implementations supported by GRR."""


# pylint: disable=g-import-not-at-top,unused-import


from grr.lib.data_stores import fake_data_store
try:
  from grr.lib.data_stores import mongo_data_store
except ImportError:
  # Mongo data store not supported.
  pass

try:
  from grr.lib.data_stores import mysql_data_store
except ImportError:
  # MySql data store not supported.
  pass


# Simple data store based on the trivial database (tdb)
try:
  from grr.lib.data_stores import tdb_data_store
except ImportError:
  pass

# Simple data store based on the sqlite database (sqlite)
try:
  from grr.lib.data_stores import sqlite_data_store
except ImportError:
  pass

# HTTP remote data store.
try:
  from grr.lib.data_stores import http_data_store
except ImportError:
  pass
