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

"""Implementations of various collections."""



import struct

from grr.lib import aff4
from grr.lib.aff4_objects import aff4_grr
from grr.proto import jobs_pb2


class GRRRDFValueCollection(aff4.AFF4Object):
  """This is a collection of RDFValues."""
  _behaviours = set()

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    DESCRIPTION = aff4.Attribute("aff4:description", aff4.RDFString,
                                 "This collection's description", "description")

  def Initialize(self):
    if self.mode == "w":
      self.fd = aff4.FACTORY.Create(self.urn.Add("Stream"), "AFF4Image",
                                    token=self.token)
    elif self.mode == "r":
      self.fd = aff4.FACTORY.Open(self.urn.Add("Stream"),
                                  required_type="AFF4Image", token=self.token)
    elif self.mode == "rw":
      raise RuntimeError("Mode rw not supported for Collections.")

  def Flush(self, sync=False):
    self.fd.Flush(sync=sync)
    super(GRRRDFValueCollection, self).Flush(sync=sync)

  def Add(self, rdf_value):
    """Add the rdf value to the collection."""
    serialized_rdf_value = jobs_pb2.RDFValue(age=int(rdf_value.age),
                                             name=rdf_value.__class__.__name__,
                                             data=rdf_value.SerializeToString())

    data = serialized_rdf_value.SerializeToString()
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)

  def __iter__(self):
    """Iterate over all contained RDFValues.

    Yields:
      RDFValues stored in the collection.

    Raises:
      RuntimeError: if we are in write mode.
    """
    if self.mode == "w":
      raise RuntimeError("Can not read when in write mode.")

    self.fd.seek(0)
    while True:
      try:
        length = struct.unpack("<i", self.fd.Read(4))[0]
        serialized_event = self.fd.Read(length)
      except struct.error:
        break

      yield aff4_grr.RDFValueProto(serialized_event).AsRDFValue()
