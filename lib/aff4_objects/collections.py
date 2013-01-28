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
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class RDFValueCollection(aff4.AFF4Object):
  """This is a collection of RDFValues."""
  # If this is set to an RDFValue class implementation, all the contained
  # objects must be instances of this class.
  _rdf_type = None

  _behaviours = set()
  size = 0

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    SIZE = aff4.AFF4Stream.SchemaCls.SIZE

    DESCRIPTION = aff4.Attribute("aff4:description", rdfvalue.RDFString,
                                 "This collection's description", "description")

    VIEW = aff4.Attribute("aff4:view", rdfvalue.View,
                          "The list of attributes which will show up in "
                          "the table.", default="")

  def Initialize(self):
    self.fd = None
    if "w" in self.mode:
      self.fd = aff4.FACTORY.Create(self.urn.Add("Stream"), "AFF4Image",
                                    mode=self.mode, token=self.token)

      self.fd.seek(0, 2)
      self.size = self.Schema.SIZE(0)

    if "r" in self.mode:
      if self.fd is None:
        self.fd = aff4.FACTORY.Open(self.urn.Add("Stream"),
                                    required_type="AFF4Image", token=self.token)

      self.size = self.Get(self.Schema.SIZE)

  def Flush(self, sync=False):
    self.fd.Flush(sync=sync)
    self.Set(self.Schema.SIZE, self.size)
    super(RDFValueCollection, self).Flush(sync=sync)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable-msg=not-callable

    if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
      raise RuntimeError("This collection only accepts values of type %s" %
                         self._rdf_type.__name__)

    serialized_rdf_value = jobs_pb2.RDFValue(age=int(rdf_value.age),
                                             name=rdf_value.__class__.__name__,
                                             data=rdf_value.SerializeToString())

    data = serialized_rdf_value.SerializeToString()
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)
    self.size += 1

  def __len__(self):
    return int(self.Get(self.Schema.SIZE))

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

      rdf_value_proto = jobs_pb2.RDFValue()
      rdf_value_proto.ParseFromString(serialized_event)

      result_cls = aff4.FACTORY.RDFValue(rdf_value_proto.name)
      if result_cls is None:
        result_cls = rdfvalue.RDFString

      yield result_cls(initializer=rdf_value_proto.data,
                       age=rdf_value_proto.age)


class AFF4ObjectSummary(rdfvalue.RDFProto):
  """A summary of an AFF4 object.

  AFF4Collection objects maintain a list of AFF4 objects. To make it easier to
  filter and search these collections, we need to store a summary of each AFF4
  object inside the collection (so we do not need to open every object for
  filtering).

  This summary is maintained in the RDFProto instance.
  """
  _proto = jobs_pb2.AFF4ObjectSummary

  rdf_map = dict(urn=rdfvalue.RDFURN,
                 stat=rdfvalue.StatEntry)


class AFF4Collection(aff4.AFF4Volume, RDFValueCollection):
  """A collection of AFF4 objects.

  The AFF4 objects themselves are opened on demand from the data store. The
  collection simply stores the RDFURNs of all aff4 objects in the collection.
  """

  _rdf_type = AFF4ObjectSummary

  _behaviours = frozenset(["Collection"])

  def CreateView(self, attributes):
    """Given a list of attributes, update our view.

    Args:
      attributes: is a list of attribute names.
    """
    self.Set(self.Schema.VIEW(attributes))

  def Query(self, filter_string="", filter_obj=None, subjects=None, limit=100):
    """Filter the objects contained within this collection."""
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = aff4.AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.filter)

    # We expect RDFURN objects to be stored in this collection.
    subjects = set([x.urn for x in self])
    if not subjects:
      return []
    result = []
    for match in data_store.DB.Query([], filter_obj, subjects=subjects,
                                     limit=limit, token=self.token):
      result.append(match["subject"][0][0])

    return self.OpenChildren(result)

  def ListChildren(self, **_):
    for aff4object_summary in self:
      yield aff4object_summary.urn

  class SchemaCls(aff4.AFF4Volume.SchemaCls, RDFValueCollection.SchemaCls):
    """The schema for the AFF4Collection."""
