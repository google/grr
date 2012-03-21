#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""General purpose flows."""


# These import populate the Flow registry
from grr.lib.flows.general import administrative
from grr.lib.flows.general import discovery
from grr.lib.flows.general import filesystem
from grr.lib.flows.general import find
from grr.lib.flows.general import java_cache
from grr.lib.flows.general import memory
from grr.lib.flows.general import network
from grr.lib.flows.general import processes
from grr.lib.flows.general import registry
from grr.lib.flows.general import sophos
from grr.lib.flows.general import timelines
from grr.lib.flows.general import transfer
from grr.lib.flows.general import utilities
from grr.lib.flows.general import webhistory
from grr.lib.flows.general import webplugins
