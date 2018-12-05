#!/usr/bin/env python
"""Classes to store and manage hunt results."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import sequential_collection
from grr_response_server.aff4_objects import aff4_queue


class HuntResultNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntResultNotification
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  def ResultRecord(self):
    # TODO(amoser): The subpath could be part of the notification.
    return data_store.Record(
        queue_id=self.result_collection_urn,
        timestamp=self.timestamp,
        suffix=self.suffix,
        subpath="Results",
        value=None)


RESULT_NOTIFICATION_QUEUE = rdfvalue.RDFURN("aff4:/hunt_results_queue")


class HuntResultQueue(aff4_queue.Queue):
  """A global queue of hunt results which need to be processed."""
  rdf_type = HuntResultNotification

  @classmethod
  def ClaimNotificationsForCollection(cls,
                                      token=None,
                                      start_time=None,
                                      lease_time=200,
                                      collection=None):
    """Return unclaimed hunt result notifications for collection.

    Args:
      token: The security token to perform database operations with.
      start_time: If set, an RDFDateTime indicating at what point to start
        claiming notifications. Only notifications with a timestamp after this
        point will be claimed.
      lease_time: How long to claim the notifications for.
      collection: The urn of the collection to find notifications for. If unset,
        the earliest (unclaimed) notification will determine the collection.

    Returns:
      A pair (collection, results) where collection is the collection
      that notifications were retrieved for and results is a list of
      Record objects which identify GrrMessage within the result
      collection.
    """

    class CollectionFilter(object):

      def __init__(self, collection):
        self.collection = collection

      def FilterRecord(self, notification):
        if self.collection is None:
          self.collection = notification.result_collection_urn
        return self.collection != notification.result_collection_urn

    f = CollectionFilter(collection)
    results = []
    with aff4.FACTORY.OpenWithLock(
        RESULT_NOTIFICATION_QUEUE,
        aff4_type=HuntResultQueue,
        lease_time=300,
        blocking=True,
        blocking_sleep_interval=15,
        blocking_lock_timeout=600,
        token=token) as queue:
      for record in queue.ClaimRecords(
          record_filter=f.FilterRecord,
          start_time=start_time,
          timeout=lease_time,
          limit=100000):
        results.append(record)
    return (f.collection, results)

  @classmethod
  def DeleteNotifications(cls, records, token=None):
    """Delete hunt notifications."""
    cls.DeleteRecords(records, token=token)


class HuntResultCollection(sequential_collection.GrrMessageCollection):
  """Sequential HuntResultCollection."""

  @classmethod
  def StaticAdd(cls,
                collection_urn,
                rdf_value,
                mutation_pool=None,
                timestamp=None,
                suffix=None,
                **kwargs):
    ts = super(HuntResultCollection, cls).StaticAdd(
        collection_urn,
        rdf_value,
        mutation_pool=mutation_pool,
        timestamp=timestamp,
        suffix=suffix,
        **kwargs)
    HuntResultQueue.StaticAdd(
        RESULT_NOTIFICATION_QUEUE,
        HuntResultNotification(
            result_collection_urn=collection_urn, timestamp=ts[0],
            suffix=ts[1]),
        mutation_pool=mutation_pool)
    return ts


class ResultQueueInitHook(registry.InitHook):
  pre = [aff4.AFF4InitHook]

  def Run(self):
    if not data_store.AFF4Enabled():
      return

    try:
      with aff4.FACTORY.Create(
          RESULT_NOTIFICATION_QUEUE,
          HuntResultQueue,
          mode="w",
          token=aff4.FACTORY.root_token):
        pass
    except access_control.UnauthorizedAccess:
      pass
