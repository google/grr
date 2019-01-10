#!/usr/bin/env python
"""A registry of all available Databases."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform

from grr_response_server.databases import mem

# All available databases go into this registry.
REGISTRY = {}

REGISTRY["InMemoryDB"] = mem.InMemoryDB

if platform.system() == "Linux":
  # When running end to end tests on Windows the MySQLDb package is not
  # available so we only do this on Linux.
  # pylint: disable=g-import-not-at-top
  from grr_response_server.databases import mysql
  # pylint: enable=g-import-not-at-top

  REGISTRY["MysqlDB"] = mysql.MysqlDB

