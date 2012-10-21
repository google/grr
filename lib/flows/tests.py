#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2011 Google Inc.
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


"""Loads up all flow tests."""

# pylint: disable=W0611
# These import populate the Flow test registry
from grr.lib.flows.general import administrative_test
from grr.lib.flows.general import collectors_test
from grr.lib.flows.general import discovery_test
from grr.lib.flows.general import fetch_all_files_test
from grr.lib.flows.general import filesystem_test
from grr.lib.flows.general import find_test
from grr.lib.flows.general import fingerprint_test
from grr.lib.flows.general import grep_test
from grr.lib.flows.general import memory_test
from grr.lib.flows.general import network_test
from grr.lib.flows.general import processes_test
from grr.lib.flows.general import registry_test
from grr.lib.flows.general import services_test
from grr.lib.flows.general import timelines_test
from grr.lib.flows.general import transfer_test
from grr.lib.flows.general import utilities_test
from grr.lib.flows.general import webhistory_test
from grr.lib.flows.general import webplugin_test
