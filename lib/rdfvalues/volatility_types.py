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

"""RDFValues used to communicate with the memory analysis framework."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class InstallDriverRequest(rdfvalue.RDFProto):
  """A request to the client to install a driver."""
  _proto = jobs_pb2.InstallDriverRequest

  rdf_map = dict(driver=rdfvalue.SignedBlob)


class VolatilityRequest(rdfvalue.RDFProto):
  """A request to the volatility subsystem on the client."""
  _proto = jobs_pb2.VolatilityRequest

  rdf_map = dict(args=rdfvalue.RDFProtoDict,
                 device=rdfvalue.RDFPathSpec,
                 session=rdfvalue.RDFProtoDict)


class MemoryInformation(rdfvalue.RDFProto):
  """Information about the client's memory geometry."""
  _proto = jobs_pb2.MemoryInformation

  rdf_map = dict(device=rdfvalue.RDFPathSpec,
                 runs=rdfvalue.BufferReference)


# The following define the data returned by Volatility plugins in a structured
# way. Volatility plugins typically produce tables, these are modeled using the
# following types.

# A Volatility plugin will produce a list of sections, each section refers to a
# different entity (e.g. information about about a different PID). Each section
# is then split into a list of tables. Tables in turn consist of a header (which
# represent the list of column names), and rows. Each row consists of a list of
# values.


class VolatilitySection(rdfvalue.RDFProto):
  """A Volatility response returns multiple sections.

  Each section typically covers a single object (e.g. a PID).
  """
  _proto = jobs_pb2.VolatilitySection


class VolatilityResult(rdfvalue.RDFProto):
  """The result of running a plugin."""
  _proto = jobs_pb2.VolatilityResponse

  rdf_map = dict(sections=VolatilitySection)
