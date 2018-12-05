#!/usr/bin/env python
"""A simple message queue synchronized through data store locks.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_server import aff4
from grr_response_server import data_store


class Queue(aff4.AFF4Object):
  """A queue of messages which can be polled, locked and deleted in bulk."""

  # The type which we store, subclasses must set this to a subclass of RDFValue
  rdf_type = None

  @classmethod
  def StaticAdd(cls, queue_urn, rdf_value, mutation_pool=None):
    """Adds an rdf value the queue.

    Adds an rdf value to a queue. Does not require that the queue be locked, or
    even open. NOTE: The caller is responsible for ensuring that the queue
    exists and is of the correct type.

    Args:
      queue_urn: The urn of the queue to add to.

      rdf_value: The rdf value to add to the queue.

      mutation_pool: A MutationPool object to write to.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    if not isinstance(rdf_value, cls.rdf_type):
      raise ValueError("This collection only accepts values of type %s." %
                       cls.rdf_type.__name__)
    if mutation_pool is None:
      raise ValueError("Mutation pool can't be none.")

    timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    if not isinstance(queue_urn, rdfvalue.RDFURN):
      queue_urn = rdfvalue.RDFURN(queue_urn)

    mutation_pool.QueueAddItem(queue_urn, rdf_value, timestamp)

  def Add(self, rdf_value, mutation_pool=None):
    """Adds an rdf value to the queue.

    Adds an rdf value to the queue. Does not require that the queue be locked.

    Args:
      rdf_value: The rdf value to add to the queue.

      mutation_pool: A MutationPool object to write to.

    Raises:
      ValueError: rdf_value has unexpected type.

    """
    self.StaticAdd(self.urn, rdf_value, mutation_pool=mutation_pool)

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

    with data_store.DB.GetMutationPool() as mutation_pool:
      return mutation_pool.QueueClaimRecords(
          self.urn,
          self.rdf_type,
          limit=limit,
          timeout=timeout,
          start_time=start_time,
          record_filter=record_filter,
          max_filtered=max_filtered)

  def RefreshClaims(self, ids, timeout="30m"):
    """Refreshes claims on records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords

      timeout: The new timeout for these claims.

    Raises:
      LockError: If the queue is not locked.

    """
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.QueueRefreshClaims(ids, timeout=timeout)

  @classmethod
  def DeleteRecords(cls, ids, token):
    """Delete records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords.
      token: The database access token to delete with.

    Raises:
      LockError: If the queue is not locked.
    """
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.QueueDeleteRecords(ids)

  @classmethod
  def DeleteRecord(cls, record_id, token):
    """Delete a single record."""
    cls.DeleteRecords([record_id], token=token)

  @classmethod
  def ReleaseRecords(cls, ids, token):
    """Release records identified by subjects.

    Releases any claim on the records identified by ids.

    Args:
      ids: A list of ids provided by ClaimRecords.
      token: The database access token to write with.

    Raises:
      LockError: If the queue is not locked.
    """
    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.QueueReleaseRecords(ids)

  @classmethod
  def ReleaseRecord(cls, record_id, token):
    """Release a single record."""
    cls.ReleaseRecords([record_id], token=token)
