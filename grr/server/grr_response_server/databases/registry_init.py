#!/usr/bin/env python
"""A registry of all available Databases."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.databases import mem
from grr_response_server.databases import mysql

# All available databases go into this registry.
REGISTRY = {}

REGISTRY["InMemoryDB"] = mem.InMemoryDB
REGISTRY["MysqlDB"] = mysql.MysqlDB
