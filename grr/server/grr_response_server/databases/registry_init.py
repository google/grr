#!/usr/bin/env python
"""A registry of all available Databases."""

from grr_response_server.databases import mem
from grr_response_server.databases import mysql
from grr_response_server.databases import spanner

# All available databases go into this registry.
REGISTRY = {
    "InMemoryDB": mem.InMemoryDB,
    "MysqlDB": mysql.MysqlDB,
    "SpannerDB": spanner.SpannerDB.FromConfig,
}
