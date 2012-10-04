#!/usr/bin/env python
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

"""AFF4 object representing network data."""


from grr.lib import aff4
from grr.lib.aff4_objects import aff4_grr
from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2


class Connections(aff4.RDFProtoArray):
  """An RDFValue class representing a list of connections on the host."""
  _proto = sysinfo_pb2.NetworkConnection


class Interfaces(aff4.RDFProtoArray):
  """An RDFValue class representing an list of interfaces on the host."""
  _proto = jobs_pb2.Interface


class Network(aff4_grr.AFF4Collection):
  """A class abstracting Network information on the client."""

  class SchemaCls(aff4_grr.AFF4Collection.SchemaCls):
    """Schema of the network object."""

    INTERFACES = aff4.Attribute("aff4:interfaces", Interfaces,
                                "Network interfaces.", "Interfaces")

    CONNECTIONS = aff4.Attribute("aff4:connections", Connections,
                                 "Network Connections", "Connections")
