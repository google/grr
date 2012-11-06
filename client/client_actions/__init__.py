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


# pylint: disable=W0611
import platform

import logging

# These imports populate the Action registry
from grr.client import actions
from grr.client.client_actions import admin
from grr.client.client_actions import enrol
from grr.client.client_actions import file_fingerprint
from grr.client.client_actions import network
from grr.client.client_actions import searching
from grr.client.client_actions import standard
from grr.proto import jobs_pb2

# pylint: disable=C6204
# pylint: disable=C6302

try:
  from grr.client.client_actions import grr_volatility
except ImportError:
  class VolatilityAction(actions.ActionPlugin):
    """Runs a volatility command on live memory."""
    in_protobuf = jobs_pb2.VolatilityRequest
    out_protobuf = jobs_pb2.VolatilityResponse

if platform.system() == "Linux":
  from grr.client.client_actions import linux
elif platform.system() == "Windows":
  from grr.client.client_actions import windows
elif platform.system() == "Darwin":
  from grr.client.client_actions import osx
