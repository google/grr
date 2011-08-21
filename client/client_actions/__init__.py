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


"""A module to load all client plugins."""


# These import populate the Action registry
import platform

from grr.client.client_actions import enrol
from grr.client.client_actions import file_fingerprint
from grr.client.client_actions import standard

if platform.system() == "Linux":
  from grr.client.client_actions import linux
elif platform.system() == "Windows":
  from grr.client.client_actions import windows
  from grr.client.client_actions import wmi
elif platform.system() == "Darwin":
  from grr.client.client_actions import osx
