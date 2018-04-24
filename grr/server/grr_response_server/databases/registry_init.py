#!/usr/bin/env python
"""A registry of all available Databases."""

from grr.server.grr_response_server.databases import mem

# All available databases go into this registry.
REGISTRY = {}

REGISTRY["InMemoryDB"] = mem.InMemoryDB

# TODO(amoser): Import MySQL relational here.

