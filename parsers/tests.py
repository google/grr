#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the grr parsers."""

# These need to register plugins so, pylint: disable=W0611

from grr.parsers import chrome_history_test
from grr.parsers import firefox3_history_test
from grr.parsers import ie_history_test
from grr.parsers import osx_launchd_test
from grr.parsers import osx_quarantine_test
from grr.parsers import sqlite_file_test
