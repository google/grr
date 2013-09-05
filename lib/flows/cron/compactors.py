#!/usr/bin/env python
"""These cron flows perform data compaction in various subsystems."""


from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue


class PackedVersionedCollectionCompactor(flow.GRRFlow):
  """A Compactor which runs over all versioned collections."""
  URN = "aff4:/cron/versioned_collection_compactor"

  frequency = rdfvalue.Duration("1h")
  lifetime = rdfvalue.Duration("20h")

  @flow.StateHandler(next_state="Process")
  def Start(self):
    """Calls "Process" state to avoid spending too much time in Start method."""
    self.CallState(next_state="Process")

  @flow.StateHandler()
  def Process(self):
    """Check all the dirty versioned collections, and compact them."""
    # Detect all changed collections:
    for predicate, urn, _ in data_store.DB.ResolveRegex(
        self.URN, "index:changed/.+", timestamp=data_store.DB.NEWEST_TIMESTAMP,
        token=self.token):
      data_store.DB.DeleteAttributes(self.URN, [predicate], token=self.token)
      try:
        self.Compact(urn)
      except IOError:
        pass

  def Compact(self, urn):
    """Run a compaction cycle on a PackedVersionedCollection."""
    fd = aff4.FACTORY.Open(urn, aff4_type="PackedVersionedCollection",
                           mode="rw", age=aff4.ALL_TIMES, token=self.token)

    # Update the collection size.
    size = fd.Get(fd.Schema.SIZE)

    for item in sorted(fd.GetValuesForAttribute(fd.Schema.DATA),
                       key=lambda x: x.age):
      super(fd.__class__, fd).Add(item.payload)
      size += 1

    # Clear the data predicate now that its in the aff4 stream.
    fd.DeleteAttribute(fd.Schema.DATA)
    fd.Set(size)

    # Flush to the data store.
    fd.Close()
