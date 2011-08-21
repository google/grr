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

"""Stubs of client actions which can not be loaded on the server.

For example, some client actions require modules which only exist on the client
operating system (e.g. windows specific client actions can not load on the
server.)
"""


from grr.client import actions
from grr.proto import jobs_pb2


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_protobuf = jobs_pb2.WmiRequest
  out_protobuf = jobs_pb2.Dict
