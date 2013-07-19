#!/usr/bin/env python
"""Implementations of various collections."""



import struct

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr


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

    VIEW = aff4.Attribute("aff4:rdfview", aff4_grr.RDFValueCollectionView,
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
                                    aff4_type="AFF4Image", token=self.token)
      self.size = self.Get(self.Schema.SIZE)

  def Flush(self, sync=False):
    if self._dirty:
      self.fd.Flush(sync=sync)
      self.Set(self.Schema.SIZE, self.size)

    super(RDFValueCollection, self).Flush(sync=sync)

  def Close(self, sync=False):
    self.Flush(sync=sync)

  def Add(self, rdf_value=None, **kwargs):
    """Add the rdf value to the collection."""
    if rdf_value is None and self._rdf_type:
      rdf_value = self._rdf_type(**kwargs)  # pylint: disable-msg=not-callable

    if self._rdf_type and not isinstance(rdf_value, self._rdf_type):
      raise RuntimeError("This collection only accepts values of type %s" %
                         self._rdf_type.__name__)

    data = rdfvalue.EmbeddedRDFValue(payload=rdf_value).SerializeToString()
    self.fd.Write(struct.pack("<i", len(data)))
    self.fd.Write(data)
    self.size += 1
    self._dirty = True

  def __len__(self):
    return self.size

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

      yield rdfvalue.EmbeddedRDFValue(serialized_event).payload

  def __getitem__(self, index):
    if index >= 0:
      for i, item in enumerate(self):
        if i == index:
          return item
    else:
      raise RuntimeError("Index must be >= 0")


class AFF4Collection(aff4.AFF4Volume, RDFValueCollection):
  """A collection of AFF4 objects.

  The AFF4 objects themselves are opened on demand from the data store. The
  collection simply stores the RDFURNs of all aff4 objects in the collection.
  """

  _rdf_type = rdfvalue.AFF4ObjectSummary

  _behaviours = frozenset(["Collection"])

  class SchemaCls(aff4.AFF4Volume.SchemaCls, RDFValueCollection.SchemaCls):
    VIEW = aff4.Attribute("aff4:view", rdfvalue.AFF4CollectionView,
                          "The list of attributes which will show up in "
                          "the table.", default="")

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


class GrepResultsCollection(RDFValueCollection):
  """A collection of grep results."""
  _rdf_type = rdfvalue.BufferReference

