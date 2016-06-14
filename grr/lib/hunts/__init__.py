#!/usr/bin/env python
"""Hunts and hunt implementations."""


# pylint: disable=unused-import
# These imports populate the GRRHunt registry
from grr.lib import aff4
from grr.lib.hunts import implementation
from grr.lib.hunts import output_plugins
from grr.lib.hunts import process_results
from grr.lib.hunts import results
from grr.lib.hunts import standard

# Add shortcuts to hunts into this module.
for name, cls in implementation.GRRHunt.classes.items():
  if aff4.issubclass(cls, implementation.GRRHunt):
    globals()[name] = cls
