#!/usr/bin/env python
"""Classes to store and manage hunt results.
"""

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.aff4_objects import queue as aff4_queue
from grr.lib.aff4_objects import sequential_collection
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class HuntResultNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntResultNotification


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
      A pair (collection, results) where collection is the collection that
      notifications were retrieved for and results is a list of tuples (id,
      timestamp, suffix) where id identifies the notification within the queue
      and (stimestmp, suffix) identifies the GrrMessage within the result
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
    with aff4.FACTORY.OpenWithLock(RESULT_NOTIFICATION_QUEUE,
                                   aff4_type=HuntResultQueue,
                                   lease_time=300,
                                   blocking=True,
                                   blocking_sleep_interval=15,
                                   blocking_lock_timeout=600,
                                   token=token) as queue:
      for record_id, value in queue.ClaimRecords(record_filter=f.FilterRecord,
                                                 start_time=start_time,
                                                 timeout=lease_time,
                                                 limit=100000):
        results.append((record_id, value.timestamp, value.suffix))
    return (f.collection, results)

  @classmethod
  def DeleteNotifications(cls, record_ids, token=None):
    """Delete hunt notifications."""
    with aff4.FACTORY.Open(RESULT_NOTIFICATION_QUEUE,
                           aff4_type=HuntResultQueue,
                           token=token) as queue:
      queue.DeleteRecords(record_ids)


class HuntResultCollection(sequential_collection.IndexedSequentialCollection):
  """Sequential HuntResultCollection."""
  RDF_TYPE = rdf_flows.GrrMessage

  @classmethod
  def StaticAdd(cls,
                collection_urn,
                token,
                rdf_value,
                timestamp=None,
                suffix=None,
                **kwargs):
    ts = super(HuntResultCollection, cls).StaticAdd(collection_urn,
                                                    token,
                                                    rdf_value,
                                                    timestamp=timestamp,
                                                    suffix=suffix,
                                                    **kwargs)
    HuntResultQueue.StaticAdd(RESULT_NOTIFICATION_QUEUE,
                              token,
                              HuntResultNotification(
                                  result_collection_urn=collection_urn,
                                  timestamp=ts[0],
                                  suffix=ts[1]))
    return ts

  def AddAsMessage(self, rdfvalue_in, source):
    """Helper method to add rdfvalues as GrrMessages for testing."""
    self.Add(rdf_flows.GrrMessage(payload=rdfvalue_in, source=source))


class ResultQueueInitHook(registry.InitHook):
  pre = ["AFF4InitHook"]

  def Run(self):
    try:
      with aff4.FACTORY.Create(RESULT_NOTIFICATION_QUEUE,
                               HuntResultQueue,
                               mode="w",
                               token=aff4.FACTORY.root_token):
        pass
    except access_control.UnauthorizedAccess:
      pass
