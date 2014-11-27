#!/usr/bin/env python
"""These cron flows perform data compaction in various subsystems."""



from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue

from grr.lib.aff4_objects import collections
from grr.lib.aff4_objects import cronjobs


class PackedVersionedCollectionCompactor(cronjobs.SystemCronFlow):
  """A Compactor which runs over all versioned collections."""

  frequency = rdfvalue.Duration("5m")
  lifetime = rdfvalue.Duration("40m")

  @flow.StateHandler()
  def Start(self):
    """Check all the dirty versioned collections, and compact them."""
    # Detect all changed collections:
    processed_count = 0
    errors_count = 0

    freeze_timestamp = rdfvalue.RDFDatetime().Now()
    for urn in collections.PackedVersionedCollection.QueryNotifications(
        timestamp=freeze_timestamp, token=self.token):
      collections.PackedVersionedCollection.DeleteNotifications(
          [urn], end=freeze_timestamp, token=self.token)

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
