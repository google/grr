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

"""AFF4 object representing client stats."""


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import standard


class ClientStats(standard.VFSDirectory):
  """A container for all process listings."""

  class SchemaCls(standard.VFSDirectory.SchemaCls):
    STATS = aff4.Attribute("aff4:stats", rdfvalue.ClientStats,
                           "Client Stats.", "Client stats")
