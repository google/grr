#!/usr/bin/env python
"""A simple message queue synchronized through data store locks.
"""
import random

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import rdfvalue


class Queue(aff4.AFF4Object):
  """A queue of messages which can be polled, locked and deleted in bulk."""

  # The type which we store, subclasses must set this to a subclass of RDFValue
  rdf_type = None

  # The attribute where we store value.
  VALUE_ATTRIBUTE = "aff4:sequential_value"

  # The attribute where we store locks. A lock is a timestamp indicating when
  # the lock becomes stale at the record may be claimed again.
  LOCK_ATTRIBUTE = "aff4:lease"

  # The largest possible suffix - maximum value expressible by 6 hex digits.
  MAX_SUFFIX = 0xffffff

  @classmethod
  def _MakeURN(cls, urn, timestamp, suffix=None):
    if suffix is None:
      # Disallow 0 so that subtracting 1 from a normal suffix doesn't require
      # special handling.
      suffix = random.randint(1, cls.MAX_SUFFIX)
    return urn.Add("Records").Add("%016x.%06x" % (timestamp, suffix))

  @classmethod
  def StaticAdd(cls, queue_urn, token, rdf_value):
    """Adds an rdf value the queue.

    Adds an rdf value to a queue. Does not require that the queue be locked, or
    even open. NOTE: The caller is responsible for ensuring that the queue
    exists and is of the correct type.

    Args:
      queue_urn: The urn of the queue to add to.

      token: The database access token to write with.

      rdf_value: The rdf value to add to the queue.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    if not isinstance(rdf_value, cls.rdf_type):
      raise ValueError("This collection only accepts values of type %s." %
                       cls.rdf_type.__name__)

    timestamp = rdfvalue.RDFDatetime().Now().AsMicroSecondsFromEpoch()

    if not isinstance(queue_urn, rdfvalue.RDFURN):
      queue_urn = rdfvalue.RDFURN(queue_urn)

    result_subject = cls._MakeURN(queue_urn, timestamp)
    data_store.DB.Set(result_subject,
                      cls.VALUE_ATTRIBUTE,
                      rdf_value.SerializeToString(),
                      timestamp=timestamp,
                      token=token)

  def Add(self, rdf_value):
    """Adds an rdf value to the queue.

    Adds an rdf value to the queue. Does not require that the queue be locked.

    Args:
      rdf_value: The rdf value to add to the queue.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    self.StaticAdd(self.urn, self.token, rdf_value)

  def ClaimRecords(self,
                   limit=10000,
                   timeout="30m",
                   start_time=None,
                   record_filter=lambda x: False,
                   max_filtered=1000):
    """Returns and claims up to limit unclaimed records for timeout seconds.

    Returns a list of records which are now "claimed", a claimed record will
    generally be unavailable to be claimed until the claim times out. Note
    however that in case of an unexpected timeout or other error a record might
    be claimed twice at the same time. For this reason it should be considered
    weaker than a true lock.

    Args:
      limit: The number of records to claim.

      timeout: The duration of the claim.

      start_time: The time to start claiming records at. Only records with a
        timestamp after this point will be claimed.

      record_filter: A filter method to determine if the record should be
        returned. It will be called serially on each record and the record will
        be filtered (not returned or locked) if it returns True.

      max_filtered: If non-zero, limits the number of results read when
        filtered. Specifically, if max_filtered filtered results are read
        sequentially without any unfiltered results, we stop looking for
        results.

    Returns:
      A list (id, record) where record is a self.rdf_type and id is a record
      identifier which can be used to delete or release the record.

    Raises:
      LockError: If the queue is not locked.

    """
    if not self.locked:
      raise aff4.LockError("Queue must be locked to claim records.")

    now = rdfvalue.RDFDatetime().Now()

    after_urn = None
    if start_time:
      after_urn = self._MakeURN(self.urn, start_time.AsMicroSecondsFromEpoch(),
                                0)
    results = []

    filtered_count = 0

    for subject, values in data_store.DB.ScanAttributes(
        self.urn.Add("Records"), [self.VALUE_ATTRIBUTE, self.LOCK_ATTRIBUTE],
        max_records=4 * limit,
        after_urn=after_urn,
        token=self.token):
      if self.VALUE_ATTRIBUTE not in values:
        # Unlikely case, but could happen if, say, a thread called RefreshClaims
        # so late that another thread already deleted the record.
        continue
      if self.LOCK_ATTRIBUTE in values and rdfvalue.RDFDatetime(values[
          self.LOCK_ATTRIBUTE][1]) > now:
        continue
      rdf_value = self.rdf_type(values[  # pylint: disable=not-callable
          self.VALUE_ATTRIBUTE][1])
      if record_filter(rdf_value):
        filtered_count += 1
        if max_filtered and filtered_count >= max_filtered:
          break
        continue
      results.append((subject, rdf_value))
      filtered_count = 0
      if len(results) >= limit:
        break

    expiration = rdfvalue.RDFDatetime().Now() + rdfvalue.Duration(timeout)

    with data_store.DB.GetMutationPool(token=self.token) as mutation_pool:
      for subject, _ in results:
        mutation_pool.Set(subject, self.LOCK_ATTRIBUTE, expiration)
    return results

  def RefreshClaims(self, ids, timeout="30m"):
    """Refreshes claims on records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords

      timeout: The new timeout for these claims.

    Raises:
      LockError: If the queue is not locked.

    """
    expiration = rdfvalue.RDFDatetime().Now() + rdfvalue.Duration(timeout)
    with data_store.DB.GetMutationPool(token=self.token) as mutation_pool:
      for subject in ids:
        mutation_pool.Set(subject, self.LOCK_ATTRIBUTE, expiration)

  def DeleteRecords(self, ids):
    """Delete records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords.

    Raises:
      LockError: If the queue is not locked.
    """
    data_store.DB.MultiDeleteAttributes(ids,
                                        [self.LOCK_ATTRIBUTE,
                                         self.VALUE_ATTRIBUTE],
                                        token=self.token)

  def DeleteRecord(self, record_id):
    """Delete a single record."""
    self.DeleteRecords([record_id])

  def ReleaseRecords(self, ids):
    """Release records identified by subjects.

    Releases any claim on the records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords.

    Raises:
      LockError: If the queue is not locked.
    """
    data_store.DB.MultiDeleteAttributes(ids, [self.LOCK_ATTRIBUTE],
                                        token=self.token)

  def ReleaseRecord(self, record_id):
    """Release a single record."""
    self.ReleaseRecords([record_id])
