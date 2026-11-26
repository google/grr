#!/usr/bin/env python
"""A registry of all available Databases."""

from typing import Callable

from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import mem

# All available databases go into this registry.
REGISTRY: dict[str, Callable[[], abstract_db.Database]] = {
    "InMemoryDB": mem.InMemoryDB,
}

try:
  from grr_response_server.databases import mysql  # pylint: disable=g-import-not-at-top
except ImportError:
  pass
else:
  REGISTRY["MysqlDB"] = mysql.MysqlDB
