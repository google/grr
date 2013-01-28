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
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections


class Network(collections.AFF4Collection):
  """A class abstracting Network information on the client."""

  class SchemaCls(collections.AFF4Collection.SchemaCls):
    """Schema of the network object."""

    INTERFACES = aff4.Attribute("aff4:interfaces", rdfvalue.Interfaces,
                                "Network interfaces.", "Interfaces")

    CONNECTIONS = aff4.Attribute("aff4:connections",
                                 rdfvalue.Connections,
                                 "Network Connections", "Connections")
