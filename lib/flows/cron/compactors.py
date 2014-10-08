#!/usr/bin/env python
"""These cron flows perform data compaction in various subsystems."""



from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue

from grr.lib.aff4_objects import cronjobs


class PackedVersionedCollectionCompactor(cronjobs.SystemCronFlow):
  """A Compactor which runs over all versioned collections."""

  INDEX_URN = "aff4:/cron/versioned_collection_compactor"
  INDEX_PREDICATE = "index:changed/.+"

  frequency = rdfvalue.Duration("5m")
  lifetime = rdfvalue.Duration("40m")

  @flow.StateHandler()
  def Start(self):
    """Check all the dirty versioned collections, and compact them."""
    # Detect all changed collections:
    processed_count = 0
    errors_count = 0

    freeze_timestamp = rdfvalue.RDFDatetime().Now()
    for predicate, urn, _ in data_store.DB.ResolveRegex(
        self.INDEX_URN, self.INDEX_PREDICATE,
        timestamp=(0, freeze_timestamp), token=self.token):
      data_store.DB.DeleteAttributes(self.INDEX_URN, [predicate],
                                     end=freeze_timestamp,
                                     token=self.token)

      self.HeartBeat()
      try:
        self.Compact(urn)
        processed_count += 1
      except IOError:
        self.Log("Error while processing %s", urn)
        errors_count += 1

    self.Log("Total processed collections: %d, successful: %d, failed: %d",
             processed_count + errors_count, processed_count, errors_count)

  def Compact(self, urn):
    """Run a compaction cycle on a PackedVersionedCollection."""
    fd = aff4.FACTORY.Open(urn, aff4_type="PackedVersionedCollection",
                           mode="rw", age=aff4.ALL_TIMES, token=self.token)
    num_compacted = fd.Compact(callback=self.HeartBeat)
    # Flush to the data store.
    fd.Close()

    self.Log("Compacted %d items in %s", num_compacted, urn)
