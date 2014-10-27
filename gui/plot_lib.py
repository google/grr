#!/usr/bin/env python
"""This file initializes the matplotlib."""


import matplotlib

# We need to select a non interactive backend for matplotlib.
matplotlib.use("Agg")

# This is exported for others to use.
# pylint: disable=unused-import, g-import-not-at-top
import matplotlib.pyplot as plt
# pylint: enable=unused-import, g-import-not-at-top
