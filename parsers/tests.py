#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the grr parsers."""

# These need to register plugins so, pylint: disable=unused-import

from grr.parsers import chrome_history_test
from grr.parsers import firefox3_history_test
from grr.parsers import ie_history_test
from grr.parsers import osx_launchd_test
from grr.parsers import osx_quarantine_test
from grr.parsers import sqlite_file_test
