#!/usr/bin/env python
"""Conditional import for Chipsec. Only Linux is supported at this stage."""

import platform
import sys

# pylint: disable=g-import-not-at-top
if hasattr(sys, "frozen"):
  if platform.system() == "Linux":
    from . import grr_chipsec
# pylint: enable=g-import-not-at-top
