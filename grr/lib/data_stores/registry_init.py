#!/usr/bin/env python
"""Load all data stores so that they are visible in the registry.
"""

# pylint: disable=g-import-not-at-top,unused-import

from grr.lib.data_stores import fake_data_store

try:
  from grr.lib.data_stores import mysql_advanced_data_store
except ImportError:
  # MySql Advanced data store not supported.
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

# Site specific data stores.
from grr.lib.data_stores import local
