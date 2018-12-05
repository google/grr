#!/usr/bin/env python
"""Load all data stores so that they are visible in the registry.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# pylint: disable=g-import-not-at-top,unused-import,g-line-too-long

from grr_response_server.data_stores import fake_data_store

try:
  from grr_response_server.data_stores import mysql_advanced_data_store
except ImportError:
  pass

# Site specific data stores.
from grr_response_server.data_stores import local
