#!/usr/bin/env python
"""Tests for grr.lib.flows.cron.compactors."""



from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib


class PackedVersionedCollectionCompactorTest(test_lib.FlowTestsBaseclass):
  """Test for PackedVersionedCollectionCompactor."""

  def testCompactsSingleCollection(self):
    with aff4.FACTORY.Create("aff4:/tmp/coll", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

    # Collection is not compacted, so recorded size is 0.
    fd = aff4.FACTORY.Open("aff4:/tmp/coll", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

    # Run the compactor.
    for _ in test_lib.TestFlowHelper("PackedVersionedCollectionCompactor",
                                     token=self.token):
      pass

    # Collection is compacted now, so recorded size is 1.
    fd = aff4.FACTORY.Open("aff4:/tmp/coll", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 1)

  def testNotificationIsRemovedAfterCompaction(self):
    with aff4.FACTORY.Create("aff4:/tmp/coll", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

    # Check that there's 1 compaction notification for our collection.
    notifications = data_store.DB.ResolveRegex(
        flow.GRRFlow.PackedVersionedCollectionCompactor.INDEX_URN,
        flow.GRRFlow.PackedVersionedCollectionCompactor.INDEX_PREDICATE,
        token=self.token)
    notifications = [n for n in notifications
                     if n[1] == "aff4:/tmp/coll"]
    self.assertEqual(len(list(notifications)), 1)

    # Run the compactor.
    for _ in test_lib.TestFlowHelper("PackedVersionedCollectionCompactor",
                                     token=self.token):
      pass

    # Check that notification for our collection is deleted after compaction.
    notifications = data_store.DB.ResolveRegex(
        flow.GRRFlow.PackedVersionedCollectionCompactor.INDEX_URN,
        flow.GRRFlow.PackedVersionedCollectionCompactor.INDEX_PREDICATE,
        token=self.token)
    notifications = [n for n in notifications
                     if n[1] == "aff4:/tmp/coll"]
    self.assertEqual(len(list(notifications)), 0)

  def testCompactsTwoCollections(self):
    with aff4.FACTORY.Create("aff4:/tmp/coll1", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

    with aff4.FACTORY.Create("aff4:/tmp/coll2", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

    # Collection is not compacted, so recorded size is 0 for both collections.
    fd = aff4.FACTORY.Open("aff4:/tmp/coll1", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

    fd = aff4.FACTORY.Open("aff4:/tmp/coll2", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

    # Run the compactor.
    for _ in test_lib.TestFlowHelper("PackedVersionedCollectionCompactor",
                                     token=self.token):
      pass

    # Collection is not compacted, so recorded size is 1 for both collections.
    fd = aff4.FACTORY.Open("aff4:/tmp/coll1", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 1)

    fd = aff4.FACTORY.Open("aff4:/tmp/coll2", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 1)

  def testSecondConsecutiveRunDoesNothing(self):
    with aff4.FACTORY.Create("aff4:/tmp/coll", "PackedVersionedCollection",
                             mode="w", token=self.token) as fd:
      fd.Add(rdfvalue.GrrMessage(request_id=1))

    # Collection is not compacted, so recorded size is 0.
    fd = aff4.FACTORY.Open("aff4:/tmp/coll", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.SIZE), 0)

    # Run the compactor and check that it reports that our collection
    # got compacted.
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name="PackedVersionedCollectionCompactor", sync=True,
        token=self.token)
    flow_fd = aff4.FACTORY.Open(flow_urn, token=self.token)
    self.assertTrue(list(l.log_message for l in flow_fd.GetLog()
                         if "aff4:/tmp/coll" in l.log_message))

    # Run the compactor again and check that our collection isn't
    # mentioned.
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name="PackedVersionedCollectionCompactor", sync=True,
        token=self.token)
    flow_fd = aff4.FACTORY.Open(flow_urn, token=self.token)
    self.assertFalse(list(l.log_message for l in flow_fd.GetLog()
                          if "aff4:/tmp/coll" in l.log_message))
