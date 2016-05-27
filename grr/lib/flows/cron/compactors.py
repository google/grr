#!/usr/bin/env python
"""These cron flows perform data compaction in various subsystems."""



import logging

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats

from grr.lib.aff4_objects import collects
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
    already_locked_count = 0

    freeze_timestamp = rdfvalue.RDFDatetime().Now()
    for urn in collects.PackedVersionedCollection.QueryNotifications(
        timestamp=freeze_timestamp, token=self.token):
      collects.PackedVersionedCollection.DeleteNotifications(
          [urn], end=urn.age, token=self.token)

      self.HeartBeat()
      try:
        if self.Compact(urn):
          processed_count += 1
        else:
          already_locked_count += 1
      except IOError:
        self.Log("Error while processing %s", urn)
        errors_count += 1

    self.Log("Total processed collections: %d, successful: %d, failed: %d, "
             "already locked: %d", processed_count + errors_count,
             processed_count, errors_count, already_locked_count)

  def Compact(self, urn):
    """Run a compaction cycle on a PackedVersionedCollection."""
    lease_time = config_lib.CONFIG["Worker.compaction_lease_time"]

    try:
      with aff4.FACTORY.OpenWithLock(
          urn,
          lease_time=lease_time,
          aff4_type=collects.PackedVersionedCollection,
          blocking=False,
          age=aff4.ALL_TIMES,
          token=self.token) as fd:
        num_compacted = fd.Compact(callback=self.HeartBeat)
        self.Log("Compacted %d items in %s", num_compacted, urn)

        return True
    except aff4.LockError:
      stats.STATS.IncrementCounter("compactor_locking_errors")
      logging.error("Trying to compact locked collection: %s", urn)

      return False


class CompactorsInitHook(registry.InitHook):

  def RunOnce(self):
    """Register compactors-related stats."""
    stats.STATS.RegisterCounterMetric("compactor_locking_errors")
