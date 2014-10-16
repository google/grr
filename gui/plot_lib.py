#!/usr/bin/env python
"""This file initializes the matplotlib."""


import matplotlib
# This is exported for others to use.
import matplotlib.pyplot as plt  # pylint: disable=unused-import

# We need to select a non interactive backend for matplotlib.
matplotlib.use("Agg")
