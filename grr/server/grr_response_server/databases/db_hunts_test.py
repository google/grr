#!/usr/bin/env python
"""Tests for the hunt database api."""

import collections
import random
from typing import Optional

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.models import hunts as models_hunts
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestHuntMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of hunts.
  """

  def _SetupHuntClientAndFlow(
      self,
      hunt_id: str = None,
      client_id: Optional[str] = None,
      flow_id: Optional[str] = None,
      flow_state: Optional[rdf_structs.EnumNamedValue] = None,
      parent_flow_id: Optional[str] = None,
  ):
    client_id = db_test_utils.InitializeClient(self.db, client_id=client_id)
    # Top-level hunt-induced flows should have hunt's id.
    flow_id = flow_id or hunt_id

    flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id,
        flow_id=flow_id,
        flow_state=flow_state,
        parent_hunt_id=hunt_id,
        parent_flow_id=parent_flow_id,
    )

    return client_id, flow_id

  def testWritingAndReadingHuntObjectWorks(self):
    then = rdfvalue.RDFDatetime.Now()

    db_test_utils.InitializeUser(self.db, "Foo")
    hunt_id = db_test_utils.InitializeHunt(
        self.db,
        creator="Foo",
        description="Lorem ipsum.",
    )

    read_hunt_obj = self.db.ReadHuntObject(hunt_id)
    self.assertEqual(read_hunt_obj.creator, "Foo")
    self.assertEqual(read_hunt_obj.description, "Lorem ipsum.")
    self.assertGreater(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            read_hunt_obj.create_time
        ),
        then,
    )
    self.assertGreater(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            read_hunt_obj.last_update_time
        ),
        then,
    )

  def testWritingHuntObjectIntegralClientRate(self):
    creator = db_test_utils.InitializeUser(self.db, "user")

    hunt_id = db_test_utils.InitializeHunt(
        self.db,
        creator="user",
        description="Lorem ipsum.",
        client_rate=42,
    )

    hunt_obj = self.db.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, creator)
    self.assertEqual(hunt_obj.description, "Lorem ipsum.")
    self.assertAlmostEqual(hunt_obj.client_rate, 42, places=5)

  def testWritingHuntObjectFractionalClientRate(self):
    creator = db_test_utils.InitializeUser(self.db, "user")

    hunt_id = db_test_utils.InitializeHunt(
        self.db,
        creator="user",
        description="Lorem ipsum.",
        client_rate=3.14,
    )

    hunt_obj = self.db.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, creator)
    self.assertEqual(hunt_obj.description, "Lorem ipsum.")
    self.assertAlmostEqual(hunt_obj.client_rate, 3.14, places=5)

  def testHuntObjectCannotBeOverwritten(self):
    db_test_utils.InitializeUser(self.db, "user")
    hunt_id = "ABCDEF42"
    hunt_obj_v1 = hunts_pb2.Hunt(
        hunt_id=hunt_id,
        hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
        description="foo",
        creator="user",
    )
    hunt_obj_v2 = hunts_pb2.Hunt(
        hunt_id=hunt_id,
        hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
        description="bar",
        creator="user",
    )
    hunt_obj_v2.hunt_id = hunt_obj_v1.hunt_id

    self.db.WriteHuntObject(hunt_obj_v1)

    with self.assertRaises(db.DuplicatedHuntError) as context:
      self.db.WriteHuntObject(hunt_obj_v2)

    self.assertEqual(context.exception.hunt_id, hunt_id)

  def testHuntObjectCannotBeWrittenInNonPausedState(self):
    db_test_utils.InitializeUser(self.db, "user")
    hunt_object = hunts_pb2.Hunt(
        hunt_id=rdf_hunt_objects.RandomHuntId(),
        hunt_state=rdf_hunt_objects.Hunt.HuntState.STARTED,
        creator="user",
    )

    with self.assertRaises(ValueError):
      self.db.WriteHuntObject(hunt_object)

  def testReadingNonExistentHuntObjectRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntObject(rdf_hunt_objects.RandomHuntId())

  def testUpdateHuntObjectRaisesIfHuntDoesNotExist(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.UpdateHuntObject(
          rdf_hunt_objects.RandomHuntId(),
          hunt_state=hunts_pb2.Hunt.HuntState.STARTED,
      )

  def testUpdateHuntObjectCorrectlyUpdatesHuntObject(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self.db.UpdateHuntObject(
        hunt_id,
        duration=rdfvalue.Duration.From(1, rdfvalue.WEEKS),
        client_rate=33,
        client_limit=48,
        hunt_state=hunts_pb2.Hunt.HuntState.STOPPED,
        hunt_state_comment="foo",
        start_time=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(43),
        num_clients_at_start_time=44,
    )

    updated_hunt_obj = self.db.ReadHuntObject(hunt_id)
    self.assertEqual(
        rdfvalue.Duration.From(updated_hunt_obj.duration, rdfvalue.SECONDS),
        rdfvalue.Duration.From(1, rdfvalue.WEEKS),
    )
    self.assertEqual(updated_hunt_obj.client_rate, 33)
    self.assertEqual(updated_hunt_obj.client_limit, 48)
    self.assertEqual(
        updated_hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.STOPPED
    )
    self.assertEqual(updated_hunt_obj.hunt_state_comment, "foo")
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            updated_hunt_obj.init_start_time
        ),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(43),
    )
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            updated_hunt_obj.last_start_time
        ),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(43),
    )
    self.assertEqual(updated_hunt_obj.num_clients_at_start_time, 44)

  def testUpdateHuntObjectCorrectlyUpdatesInitAndLastStartTime(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    timestamp_1 = rdfvalue.RDFDatetime.Now()
    self.db.UpdateHuntObject(hunt_id, start_time=timestamp_1)

    timestamp_2 = rdfvalue.RDFDatetime.Now()
    self.db.UpdateHuntObject(hunt_id, start_time=timestamp_2)

    updated_hunt_object = self.db.ReadHuntObject(hunt_id)
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            updated_hunt_object.init_start_time
        ),
        timestamp_1,
    )
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            updated_hunt_object.last_start_time
        ),
        timestamp_2,
    )

  def testDeletingHuntObjectWorks(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    # This shouldn't raise.
    self.db.ReadHuntObject(hunt_id)

    self.db.DeleteHuntObject(hunt_id)

    # The hunt is deleted: this should raise now.
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntObject(hunt_id)

  def testDeleteHuntObjectWithApprovalRequest(self):
    creator = db_test_utils.InitializeUser(self.db)
    approver = db_test_utils.InitializeUser(self.db)
    hunt_id = db_test_utils.InitializeHunt(self.db, creator=creator)

    approval = rdf_objects.ApprovalRequest()
    approval.approval_type = (
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
    )
    approval.requestor_username = creator
    approval.notified_users = [approver]
    approval.subject_id = hunt_id
    approval.expiration_time = (
        rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(1, rdfvalue.DAYS)
    )
    # TODO: Stop using `mig_objects`.
    proto_approval = mig_objects.ToProtoApprovalRequest(approval)
    approval_id = self.db.WriteApprovalRequest(proto_approval)

    self.db.DeleteHuntObject(hunt_id=hunt_id)

    with self.assertRaises(db.UnknownApprovalRequestError):
      self.db.ReadApprovalRequest(creator, approval_id)

  def testReadHuntObjectsReturnsEmptyListWhenNoHunts(self):
    self.assertEqual(self.db.ReadHuntObjects(offset=0, count=db.MAX_COUNT), [])

  def _CreateMultipleHunts(self) -> list[hunts_pb2.Hunt]:
    self._CreateMultipleUsers(["user-a", "user-b"])

    result = []
    for i in range(10):
      if i < 5:
        creator = "user-a"
      else:
        creator = "user-b"
      hunt_id = db_test_utils.InitializeHunt(
          self.db,
          creator=creator,
          description="foo_%d" % i,
      )
      result.append(self.db.ReadHuntObject(hunt_id))

    return result

  def _CreateMultipleUsers(self, users: list[str]):
    for user in users:
      db_test_utils.InitializeUser(self.db, user)

  def _CreateMultipleHuntsForUser(
      self,
      user: str,
      count: int,
  ) -> list[hunts_pb2.Hunt]:
    result = []
    for i in range(count):
      hunt_id = db_test_utils.InitializeHunt(
          self.db,
          creator=user,
          description="foo_%d" % i,
      )
      result.append(self.db.ReadHuntObject(hunt_id))
    return result

  def _CreateHuntWithState(
      self, creator: str, state: hunts_pb2.Hunt.HuntState
  ) -> hunts_pb2.Hunt:
    hunt_id = db_test_utils.InitializeHunt(self.db, creator=creator)

    self.db.UpdateHuntObject(hunt_id, hunt_state=state)
    return self.db.ReadHuntObject(hunt_id)

  def testReadHuntObjectsWithoutFiltersReadsAllHunts(self):
    expected = self._CreateMultipleHunts()
    got = self.db.ReadHuntObjects(0, db.MAX_COUNT)
    self.assertListEqual(got, list(reversed(expected)))

  def testReadHuntObjectsWithCreatorFilterIsAppliedCorrectly(self):
    all_hunts = self._CreateMultipleHunts()

    got = self.db.ReadHuntObjects(0, db.MAX_COUNT, with_creator="user-a")
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(0, db.MAX_COUNT, with_creator="user-b")
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

  def testReadHuntObjectsWithCreatedByFilterIsAppliedCorrectly(self):
    self._CreateMultipleUsers(["user-a", "user-b"])
    all_hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)

    got = self.db.ReadHuntObjects(0, db.MAX_COUNT, created_by=frozenset([]))
    self.assertListEqual(got, [])

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-a"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-a", "user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

  def testReadHuntObjectsWithCreatorAndCreatedByFilterIsAppliedCorrectly(
      self,
  ):
    self._CreateMultipleUsers(["user-a", "user-b"])
    all_hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, [])

  def testReadHuntObjectsWithNotCreatedByFilterIsAppliedCorrectly(self):
    self._CreateMultipleUsers(["user-a", "user-b"])
    all_hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)

    got = self.db.ReadHuntObjects(0, db.MAX_COUNT, not_created_by=frozenset([]))
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-a"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-a", "user-b"])
    )
    self.assertListEqual(got, [])

  def testReadHuntObjectsWithCreatorAndNotCreatedByFilterIsAppliedCorrectly(
      self,
  ):
    self._CreateMultipleUsers(["user-a", "user-b"])
    all_hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset([]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        not_created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        not_created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

  def testReadHuntObjectsCreatedAfterFilterIsAppliedCorrectly(self):
    all_hunts = self._CreateMultipleHunts()

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[0].create_time
        )
        - rdfvalue.Duration.From(1, rdfvalue.SECONDS),
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[2].create_time
        ),
    )
    self.assertListEqual(got, list(reversed(all_hunts[3:])))

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[-1].create_time
        ),
    )
    self.assertEmpty(got)

  def testReadHuntObjectsWithDescriptionMatchFilterIsAppliedCorrectly(self):
    all_hunts = self._CreateMultipleHunts()

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, with_description_match="foo_"
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, with_description_match="blah"
    )
    self.assertEmpty(got)

    got = self.db.ReadHuntObjects(
        0, db.MAX_COUNT, with_description_match="foo_3"
    )
    self.assertListEqual(got, [all_hunts[3]])

  def testReadHuntObjectsWithStatesFilterIsAppliedCorrectly(self):
    creator = "testuser"
    db_test_utils.InitializeUser(self.db, creator)
    paused_hunt = self._CreateHuntWithState(
        creator, hunts_pb2.Hunt.HuntState.PAUSED
    )
    self._CreateHuntWithState(creator, hunts_pb2.Hunt.HuntState.STARTED)
    stopped_hunt = self._CreateHuntWithState(
        creator, hunts_pb2.Hunt.HuntState.STOPPED
    )
    self._CreateHuntWithState(creator, hunts_pb2.Hunt.HuntState.COMPLETED)

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[
            hunts_pb2.Hunt.HuntState.PAUSED,
        ],
    )
    self.assertListEqual(got, [paused_hunt])

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[
            hunts_pb2.Hunt.HuntState.PAUSED,
            hunts_pb2.Hunt.HuntState.STOPPED,
        ],
    )
    self.assertCountEqual(got, [paused_hunt, stopped_hunt])

    got = self.db.ReadHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[],
    )
    self.assertListEqual(got, [])

  def testReadHuntObjectsCombinationsOfFiltersAreAppliedCorrectly(self):
    expected = self._CreateMultipleHunts()
    self.DoFilterCombinationsAndOffsetCountTest(
        self.db.ReadHuntObjects,
        conditions=dict(
            with_creator="user-a",
            created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                expected[2].create_time
            ),
            with_description_match="foo_4",
        ),
        error_desc="ReadHuntObjects",
    )

  def testListHuntObjectsReturnsEmptyListWhenNoHunts(self):
    self.assertEqual(self.db.ListHuntObjects(offset=0, count=db.MAX_COUNT), [])

  def testListHuntObjectsWithoutFiltersReadsAllHunts(self):
    hunts = self._CreateMultipleHunts()
    expected = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]
    got = self.db.ListHuntObjects(0, db.MAX_COUNT)
    self.assertListEqual(got, list(reversed(expected)))

  def testListHuntObjectsWithCreatorFilterIsAppliedCorrectly(self):
    all_hunts = self._CreateMultipleHunts()
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in all_hunts]

    got = self.db.ListHuntObjects(0, db.MAX_COUNT, with_creator="user-a")
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(0, db.MAX_COUNT, with_creator="user-b")
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

  def testListHuntObjectsWithCreatedByFilterIsAppliedCorrectly(self):
    self._CreateMultipleUsers(["user-a", "user-b"])
    hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(0, db.MAX_COUNT, created_by=frozenset([]))
    self.assertListEqual(got, [])

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-a"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, created_by=frozenset(["user-a", "user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

  def testListHuntObjectsWithCreatorAndCreatedByFilterIsAppliedCorrectly(
      self,
  ):
    self._CreateMultipleUsers(["user-a", "user-b"])
    hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, [])

  def testListHuntObjectsWithNotCreatedByFilterIsAppliedCorrectly(self):
    self._CreateMultipleUsers(["user-a", "user-b"])
    hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(0, db.MAX_COUNT, not_created_by=frozenset([]))
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-a"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-b"])
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, not_created_by=frozenset(["user-a", "user-b"])
    )
    self.assertListEqual(got, [])

  def testListHuntObjectsWithCreatorAndNotCreatedByFilterIsAppliedCorrectly(
      self,
  ):
    self._CreateMultipleUsers(["user-a", "user-b"])
    hunts = self._CreateMultipleHuntsForUser(
        "user-a", 5
    ) + self._CreateMultipleHuntsForUser("user-b", 5)

    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset([]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        not_created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, [])

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-a",
        not_created_by=frozenset(["user-b"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[:5])))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_creator="user-b",
        not_created_by=frozenset(["user-a"]),
    )
    self.assertListEqual(got, list(reversed(all_hunts[5:])))

  def testListHuntObjectsCreatedAfterFilterIsAppliedCorrectly(self):
    hunts = self._CreateMultipleHunts()
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[0].create_time
        )
        - rdfvalue.Duration.From(1, rdfvalue.SECONDS),
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[2].create_time
        ),
    )
    self.assertListEqual(got, list(reversed(all_hunts[3:])))

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            all_hunts[-1].create_time
        ),
    )
    self.assertEmpty(got)

  def testListHuntObjectsWithDescriptionMatchFilterIsAppliedCorrectly(self):
    hunts = self._CreateMultipleHunts()
    all_hunts = [models_hunts.InitHuntMetadataFromHunt(h) for h in hunts]

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, with_description_match="foo_"
    )
    self.assertListEqual(got, list(reversed(all_hunts)))

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, with_description_match="blah"
    )
    self.assertEmpty(got)

    got = self.db.ListHuntObjects(
        0, db.MAX_COUNT, with_description_match="foo_3"
    )
    self.assertListEqual(got, [all_hunts[3]])

  def testListHuntObjectsWithStatesFilterIsAppliedCorrectly(self):
    creator = "testuser"
    db_test_utils.InitializeUser(self.db, creator)
    paused_hunt = self._CreateHuntWithState(
        creator, hunts_pb2.Hunt.HuntState.PAUSED
    )
    paused_hunt_metadata = models_hunts.InitHuntMetadataFromHunt(paused_hunt)
    self._CreateHuntWithState(creator, rdf_hunt_objects.Hunt.HuntState.STARTED)
    stopped_hunt = self._CreateHuntWithState(
        creator, hunts_pb2.Hunt.HuntState.STOPPED
    )
    stopped_hunt_metadata = models_hunts.InitHuntMetadataFromHunt(stopped_hunt)
    self._CreateHuntWithState(creator, hunts_pb2.Hunt.HuntState.COMPLETED)

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[
            hunts_pb2.Hunt.HuntState.PAUSED,
        ],
    )
    self.assertCountEqual(got, [paused_hunt_metadata])

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[
            hunts_pb2.Hunt.HuntState.PAUSED,
            hunts_pb2.Hunt.HuntState.STOPPED,
        ],
    )
    self.assertCountEqual(got, [paused_hunt_metadata, stopped_hunt_metadata])

    got = self.db.ListHuntObjects(
        0,
        db.MAX_COUNT,
        with_states=[],
    )
    self.assertListEqual(got, [])

  def testListHuntObjectsCombinationsOfFiltersAreAppliedCorrectly(self):
    expected = self._CreateMultipleHunts()

    self.DoFilterCombinationsAndOffsetCountTest(
        self.db.ListHuntObjects,
        conditions=dict(
            with_creator="user-a",
            created_after=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                expected[2].create_time
            ),
            with_description_match="foo_4",
            created_by=frozenset(["user-a"]),
            not_created_by=frozenset(["user-b"]),
            with_states=[rdf_hunt_objects.Hunt.HuntState.PAUSED],
        ),
        error_desc="ListHuntObjects",
    )

  def testWritingAndReadingHuntOutputPluginsStatesWorks(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    email_args = output_plugin_pb2.EmailOutputPluginArgs(
        email_address="a@a.com"
    )
    email_args_any = any_pb2.Any()
    email_args_any.Pack(email_args)
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__, args=email_args_any
    )
    plugin_state = jobs_pb2.AttributedDict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a_foo1"),
                v=jobs_pb2.DataBlob(string="a_bar1"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="a_foo2"),
                v=jobs_pb2.DataBlob(string="a_bar2"),
            ),
        ]
    )
    state_1 = output_plugin_pb2.OutputPluginState(
        plugin_descriptor=plugin_descriptor,
        plugin_state=plugin_state,
    )

    email_args_2 = output_plugin_pb2.EmailOutputPluginArgs(
        email_address="b@b.com"
    )
    email_args_any_2 = any_pb2.Any()
    email_args_any_2.Pack(email_args_2)
    plugin_descriptor_2 = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=email_plugin.EmailOutputPlugin.__name__,
        args=email_args_any_2,
    )
    plugin_state_2 = jobs_pb2.AttributedDict(
        dat=[
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b_foo1"),
                v=jobs_pb2.DataBlob(string="b_bar1"),
            ),
            jobs_pb2.KeyValue(
                k=jobs_pb2.DataBlob(string="b_foo2"),
                v=jobs_pb2.DataBlob(string="b_bar2"),
            ),
        ]
    )
    state_2 = output_plugin_pb2.OutputPluginState(
        plugin_descriptor=plugin_descriptor_2,
        plugin_state=plugin_state_2,
    )

    written_states = [state_1, state_2]
    self.db.WriteHuntOutputPluginsStates(hunt_id, written_states)

    read_states = self.db.ReadHuntOutputPluginsStates(hunt_id)
    self.assertEqual(read_states, written_states)

  def testReadingHuntOutputPluginsReturnsThemInOrderOfWriting(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    states = []
    for i in range(100):
      states.append(
          output_plugin_pb2.OutputPluginState(
              plugin_descriptor=output_plugin_pb2.OutputPluginDescriptor(
                  plugin_name="DummyHuntOutputPlugin_%d" % i
              ),
              plugin_state=jobs_pb2.AttributedDict(),
          )
      )
    random.shuffle(states)

    self.db.WriteHuntOutputPluginsStates(hunt_id, states)

    read_states = self.db.ReadHuntOutputPluginsStates(hunt_id)
    self.assertEqual(read_states, states)

  def testWritingHuntOutputStatesForZeroPlugins(self):
    # Passing an empty list of states is always a no-op so this should not
    # raise, even if the hunt does not exist.
    self.db.WriteHuntOutputPluginsStates(rdf_hunt_objects.RandomHuntId(), [])

  def testWritingHuntOutputStatesForUnknownHuntRaises(self):
    state = output_plugin_pb2.OutputPluginState(
        plugin_descriptor=output_plugin_pb2.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin1"
        ),
        plugin_state=jobs_pb2.AttributedDict(),
    )

    with self.assertRaises(db.UnknownHuntError):
      self.db.WriteHuntOutputPluginsStates(
          rdf_hunt_objects.RandomHuntId(), [state]
      )

  def testReadingHuntOutputPluginsWithoutStates(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)
    res = self.db.ReadHuntOutputPluginsStates(hunt_id)
    self.assertEqual(res, [])

  def testReadingHuntOutputStatesForUnknownHuntRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntOutputPluginsStates(rdf_hunt_objects.RandomHuntId())

  def testUpdatingHuntOutputStateForUnknownHuntRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.UpdateHuntOutputPluginState(
          rdf_hunt_objects.RandomHuntId(), 0, lambda x: x
      )

  def testUpdatingHuntOutputStateWorksCorrectly(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    state_1 = output_plugin_pb2.OutputPluginState(
        plugin_descriptor=output_plugin_pb2.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin1"
        ),
        plugin_state=jobs_pb2.AttributedDict(),
    )

    state_2 = output_plugin_pb2.OutputPluginState(
        plugin_descriptor=output_plugin_pb2.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin2"
        ),
        plugin_state=jobs_pb2.AttributedDict(),
    )

    self.db.WriteHuntOutputPluginsStates(hunt_id, [state_1, state_2])

    def Update(s: jobs_pb2.AttributedDict) -> jobs_pb2.AttributedDict:
      el = s.dat.add()
      el.k.CopyFrom(jobs_pb2.DataBlob(string="foo"))
      el.v.CopyFrom(jobs_pb2.DataBlob(string="bar"))
      return s

    self.db.UpdateHuntOutputPluginState(hunt_id, 0, Update)

    states = self.db.ReadHuntOutputPluginsStates(hunt_id)
    self.assertEqual(
        states[0].plugin_state,
        jobs_pb2.AttributedDict(
            dat=[
                jobs_pb2.KeyValue(
                    k=jobs_pb2.DataBlob(string="foo"),
                    v=jobs_pb2.DataBlob(string="bar"),
                ),
            ]
        ),
    )
    self.assertEmpty(states[1].plugin_state.dat)

    self.db.UpdateHuntOutputPluginState(hunt_id, 1, Update)

    states = self.db.ReadHuntOutputPluginsStates(hunt_id)
    self.assertEqual(
        states[0].plugin_state,
        jobs_pb2.AttributedDict(
            dat=[
                jobs_pb2.KeyValue(
                    k=jobs_pb2.DataBlob(string="foo"),
                    v=jobs_pb2.DataBlob(string="bar"),
                ),
            ]
        ),
    )

    self.assertEqual(
        states[1].plugin_state,
        jobs_pb2.AttributedDict(
            dat=[
                jobs_pb2.KeyValue(
                    k=jobs_pb2.DataBlob(string="foo"),
                    v=jobs_pb2.DataBlob(string="bar"),
                ),
            ]
        ),
    )

  def testReadHuntLogEntriesReturnsEntryFromSingleHuntFlow(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        client_id="C.12345678901234aa", hunt_id=hunt_id
    )
    self.db.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            message="blah",
        )
    )

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_id, 0, 10)
    self.assertLen(hunt_log_entries, 1)
    self.assertIsInstance(hunt_log_entries[0], flows_pb2.FlowLogEntry)
    self.assertEqual(hunt_log_entries[0].hunt_id, hunt_id)
    self.assertEqual(hunt_log_entries[0].client_id, client_id)
    self.assertEqual(hunt_log_entries[0].flow_id, flow_id)
    self.assertEqual(hunt_log_entries[0].message, "blah")

  def _WriteNestedAndNonNestedLogEntries(self, hunt_id: str):
    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    # Top-level hunt-induced flows should have the hunt's ID.
    self.db.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            message="blah_a",
        )
    )
    self.db.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            message="blah_b",
        )
    )

    for i in range(10):
      _, nested_flow_id = self._SetupHuntClientAndFlow(
          client_id=client_id,
          parent_flow_id=flow_id,
          hunt_id=hunt_id,
          flow_id=flow.RandomFlowId(),
      )
      self.db.WriteFlowLogEntry(
          flows_pb2.FlowLogEntry(
              client_id=client_id,
              flow_id=nested_flow_id,
              hunt_id=hunt_id,
              message="blah_a_%d" % i,
          )
      )
      self.db.WriteFlowLogEntry(
          flows_pb2.FlowLogEntry(
              client_id=client_id,
              flow_id=nested_flow_id,
              hunt_id=hunt_id,
              message="blah_b_%d" % i,
          )
      )

  def testReadHuntLogEntriesIgnoresNestedFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self._WriteNestedAndNonNestedLogEntries(hunt_id)

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_id, 0, 10)
    self.assertLen(hunt_log_entries, 2)
    self.assertEqual(hunt_log_entries[0].message, "blah_a")
    self.assertEqual(hunt_log_entries[1].message, "blah_b")

  def testCountHuntLogEntriesIgnoresNestedFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self._WriteNestedAndNonNestedLogEntries(hunt_id)

    num_hunt_log_entries = self.db.CountHuntLogEntries(hunt_id)
    self.assertEqual(num_hunt_log_entries, 2)

  def _WriteHuntLogEntries(self, msg="blah") -> str:
    hunt_id = db_test_utils.InitializeHunt(self.db)

    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          client_id="C.12345678901234a%d" % i, hunt_id=hunt_id
      )
      self.db.WriteFlowLogEntry(
          flows_pb2.FlowLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              message="%s%d" % (msg, i),
          )
      )

    return hunt_id

  def testReadHuntLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    hunt_id = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_id, 0, 100)
    self.assertLen(hunt_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

  def testReadHuntLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    hunt_id = self._WriteHuntLogEntries()

    for i in range(10):
      hunt_log_entries = self.db.ReadHuntLogEntries(hunt_id, i, 1)
      self.assertLen(hunt_log_entries, 1)
      self.assertEqual(hunt_log_entries[0].message, "blah%d" % i)

  def testReadHuntLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    hunt_id = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 100, with_substring="foo"
    )
    self.assertEmpty(hunt_log_entries)

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 100, with_substring="blah"
    )
    self.assertLen(hunt_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 100, with_substring="blah1"
    )
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah1")

  def testReadHuntLogEntriesSubstringFilterIsCorrectlyEscaped(self):
    hunt_id = self._WriteHuntLogEntries("ABC%1")
    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 100, with_substring="BC%1"
    )
    self.assertLen(hunt_log_entries, 10)
    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 100, with_substring="B%1"
    )
    self.assertEmpty(hunt_log_entries)

  def testReadHuntLogEntriesCorrectlyAppliesCombinationOfFilters(self):
    hunt_id = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_id, 0, 1, with_substring="blah"
    )
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah0")

  def testCountHuntLogEntriesReturnsCorrectHuntLogEntriesCount(self):
    hunt_id = self._WriteHuntLogEntries()

    num_entries = self.db.CountHuntLogEntries(hunt_id)
    self.assertEqual(num_entries, 10)

  def _WriteHuntResults(self, sample_results: list[flows_pb2.FlowResult]):
    self.db.WriteFlowResults(sample_results)

    # Update num_replies_sent for all flows referenced in sample_results:
    # in case the DB implementation relies on this data when
    # counting results.
    results_per_flow = collections.Counter()
    for r in sample_results:
      results_per_flow[(r.client_id, r.flow_id)] += 1

    for (client_id, flow_id), delta in results_per_flow.items():
      f_obj = self.db.ReadFlowObject(client_id, flow_id)
      f_obj.num_replies_sent += delta
      self.db.UpdateFlow(client_id, flow_id, flow_obj=f_obj)

  def _SampleSingleTypeHuntResults(
      self,
      client_id=None,
      flow_id=None,
      hunt_id=None,
      serial_number=None,
      count=10,
  ) -> list[flows_pb2.FlowResult]:
    self.assertIsNotNone(client_id)
    self.assertIsNotNone(flow_id)
    self.assertIsNotNone(hunt_id)

    res = []
    for i in range(count):
      payload_any = any_pb2.Any()
      payload_any.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              system_manufacturer="manufacturer_%d" % i,
              serial_number=serial_number,
              install_date=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 + i)
              ),
          ),
      )
      res.append(
          flows_pb2.FlowResult(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              tag="tag_%d" % i,
              payload=payload_any,
          ),
      )
    return res

  def _SampleTwoTypeHuntResults(
      self,
      client_id=None,
      flow_id=None,
      hunt_id=None,
      serial_number=None,
      count_per_type=5,
      timestamp_start=10,
  ) -> list[flows_pb2.FlowResult]:
    self.assertIsNotNone(client_id)
    self.assertIsNotNone(flow_id)
    self.assertIsNotNone(hunt_id)

    res = []
    for i in range(count_per_type):
      paylad_any = any_pb2.Any()
      paylad_any.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              system_manufacturer="manufacturer_%d" % i,
              serial_number=serial_number,
              install_date=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                      timestamp_start + i
                  )
              ),
          ),
      )
      res.append(
          flows_pb2.FlowResult(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              tag="tag_%d" % i,
              payload=paylad_any,
          )
      )
    for i in range(count_per_type):
      paylad_any = any_pb2.Any()
      paylad_any.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=int(
                  rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                      timestamp_start + i
                  )
              ),
          ),
      )
      res.append(
          flows_pb2.FlowResult(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              tag="tag_%d" % i,
              payload=paylad_any,
          )
      )
    return res

  def testReadHuntResultsReadsSingleResultOfSingleType(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id, count=1
    )
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_id, 0, 10)
    self.assertLen(results, 1)
    self.assertEqual(results[0].hunt_id, hunt_id)
    self.assertEqual(results[0].payload, sample_results[0].payload)

  def testReadHuntResultsReadsMultipleResultOfSingleType(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id, count=10
    )
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_id, 0, 1000)
    self.assertLen(results, 10)
    for i in range(10):
      self.assertEqual(results[i].hunt_id, hunt_id)
      self.assertEqual(results[i].payload, sample_results[i].payload)

  def testReadHuntResultsReadsMultipleResultOfMultipleTypes(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id_1, flow_id_1 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results_1 = self._SampleTwoTypeHuntResults(
        client_id=client_id_1, flow_id=flow_id_1, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results_1)

    client_id_2, flow_id_2 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results_2 = self._SampleTwoTypeHuntResults(
        client_id=client_id_2, flow_id=flow_id_2, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results_2)

    sample_results = sample_results_1 + sample_results_2
    results = self.db.ReadHuntResults(hunt_id, 0, 1000)
    self.assertLen(results, len(sample_results))
    self.assertListEqual(
        [i.payload for i in results], [i.payload for i in sample_results]
    )

  def testReadHuntResultsCorrectlyAppliedOffsetAndCountFilters(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      results = self._SampleSingleTypeHuntResults(
          client_id=client_id, flow_id=flow_id, hunt_id=hunt_id, count=1
      )
      sample_results.extend(results)
      self._WriteHuntResults(results)

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadHuntResults(hunt_id, i, l)
        expected = sample_results[i : i + l]

        result_payloads = [x.payload for x in results]
        expected_payloads = [x.payload for x in expected]
        self.assertEqual(
            result_payloads,
            expected_payloads,
            "Results differ from expected (from %d, size %d): %s vs %s"
            % (i, l, result_payloads, expected_payloads),
        )

  def testReadHuntResultsCorrectlyAppliesWithTagFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_tag="blah")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_tag="tag")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_tag="tag_1")
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results if i.tag == "tag_1"],
    )

  def testReadHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          count_per_type=1,
      )
      sample_results.extend(results)
      self._WriteHuntResults(results)

    results = self.db.ReadHuntResults(
        hunt_id, 0, 100, with_type=jobs_pb2.ClientInformation.__name__
    )
    self.assertFalse(results)

    results = self.db.ReadHuntResults(
        hunt_id, 0, 100, with_type=jobs_pb2.ClientSummary.__name__
    )
    self.assertCountEqual(
        [i.payload for i in results],
        [
            i.payload
            for i in sample_results
            if i.payload.Is(jobs_pb2.ClientSummary.DESCRIPTOR)
        ],
    )

  def testReadHuntResultsCorrectlyAppliesWithProtoTypeUrlFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    all_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

      summary_payload = jobs_pb2.ClientSummary()
      summary_any = any_pb2.Any()
      summary_any.Pack(summary_payload)
      summary_result = flows_pb2.FlowResult(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          payload=summary_any,
      )

      crash_payload = jobs_pb2.ClientCrash()
      crash_any = any_pb2.Any()
      crash_any.Pack(crash_payload)
      crash_result = flows_pb2.FlowResult(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          payload=crash_any,
      )

      results_for_flow = [summary_result, crash_result]
      self._WriteHuntResults(results_for_flow)
      all_results.extend(results_for_flow)

    results = self.db.ReadHuntResults(
        hunt_id,
        0,
        100,
        with_proto_type_url=f"type.googleapis.com/{jobs_pb2.ClientInformation.DESCRIPTOR.full_name}",
    )
    self.assertEmpty(results)

    results = self.db.ReadHuntResults(
        hunt_id,
        0,
        100,
        with_proto_type_url=(
            f"type.googleapis.com/{jobs_pb2.ClientSummary.DESCRIPTOR.full_name}"
        ),
    )
    self.assertLen(results, 10)
    self.assertCountEqual(
        [r.payload for r in results],
        [
            r.payload
            for r in all_results
            if r.payload.Is(jobs_pb2.ClientSummary.DESCRIPTOR)
        ],
    )

  def testReadFlowResultsCorrectlyAppliesWithTypeAndProtoTypeUrlFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    any_proto = any_pb2.Any()
    any_proto.Pack(jobs_pb2.ClientSummary())
    client_summary_type_url = any_proto.type_url

    with self.assertRaises(ValueError):
      self.db.ReadFlowResults(
          client_id,
          flow_id,
          0,
          100,
          with_type=rdf_client.ClientSummary.__name__,
          with_proto_type_url=client_summary_type_url,
      )

  def testReadHuntResultsCorrectlyAppliesWithSubstringFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_substring="blah")
    self.assertEmpty(results)

    results = self.db.ReadHuntResults(
        hunt_id, 0, 100, with_substring="manufacturer"
    )
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

    results = self.db.ReadHuntResults(
        hunt_id, 0, 100, with_substring="manufacturer_1"
    )
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadHuntResultsSubstringFilterIsCorrectlyEscaped(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id,
        flow_id=flow_id,
        hunt_id=hunt_id,
        serial_number="ABC%123",
    )
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_substring="ABC%123")
    self.assertLen(results, 10)

    results = self.db.ReadHuntResults(hunt_id, 0, 100, with_substring="AB%23")
    self.assertEmpty(results)

  def testReadHuntResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          count_per_type=5,
      )
      sample_results.extend(results)
      self._WriteHuntResults(results)

    # TODO: Clean up this test.
    tags = {
        None: list(sample_results),
        "tag_1": [s for s in sample_results if s.tag == "tag_1"],
    }
    substrings = {
        None: list(sample_results),
    }
    manufacturer = []
    manufacturer_1 = []
    for s in sample_results:
      if s.payload.Is(jobs_pb2.ClientSummary.DESCRIPTOR):
        payload = jobs_pb2.ClientSummary()
      elif s.payload.Is(jobs_pb2.ClientCrash.DESCRIPTOR):
        payload = jobs_pb2.ClientCrash()
      else:
        continue
      s.payload.Unpack(payload)
      if "manufacturer" in getattr(payload, "system_manufacturer", ""):
        manufacturer.append(s)
      if "manufacturer_1" in getattr(payload, "system_manufacturer", ""):
        manufacturer_1.append(s)

    substrings["manufacturer"] = manufacturer
    substrings["manufacturer_1"] = manufacturer_1

    types = {
        None: list(sample_results),
        jobs_pb2.ClientSummary.__name__: [
            s
            for s in sample_results
            if s.payload.Is(jobs_pb2.ClientSummary.DESCRIPTOR)
        ],
    }

    for tag_value, tag_expected in tags.items():
      for substring_value, substring_expected in substrings.items():
        for type_value, type_expected in types.items():
          expected = [
              e
              for e in tag_expected
              if e in substring_expected and e in type_expected
          ]
          results = self.db.ReadHuntResults(
              hunt_id,
              0,
              100,
              with_tag=tag_value,
              with_type=type_value,
              with_substring=substring_value,
          )

          self.assertCountEqual(
              [i.payload for i in expected],
              [i.payload for i in results],
              "Result items do not match for "
              "(tag=%s, type=%s, substring=%s): %s vs %s"
              % (tag_value, type_value, substring_value, expected, results),
          )

  def testReadHuntResultsIgnoresChildFlowsResults(self):
    client_id = db_test_utils.InitializeClient(self.db)
    hunt_id = db_test_utils.InitializeHunt(self.db)

    hunt_flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    child_flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id,
        parent_flow_id=hunt_flow_id,
        parent_hunt_id=hunt_id,
    )

    hunt_flow_result = flows_pb2.FlowResult()
    hunt_flow_result.client_id = client_id
    hunt_flow_result.hunt_id = hunt_id
    hunt_flow_result.flow_id = hunt_flow_id
    hunt_flow_result.payload.Pack(jobs_pb2.Uname(fqdn="hunt.example.com"))
    self.db.WriteFlowResults([hunt_flow_result])

    child_flow_result = flows_pb2.FlowResult()
    child_flow_result.client_id = client_id
    child_flow_result.hunt_id = hunt_id
    child_flow_result.flow_id = child_flow_id
    child_flow_result.payload.Pack(jobs_pb2.Uname(fqdn="child.example.com"))
    self.db.WriteFlowResults([child_flow_result])

    results = self.db.ReadHuntResults(hunt_id, offset=0, count=1024)

    self.assertLen(results, 1)

    result = jobs_pb2.Uname()
    results[0].payload.Unpack(result)
    self.assertEqual(result.fqdn, "hunt.example.com")

  def testCountHuntResultsReturnsCorrectResultsCount(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)

    num_results = self.db.CountHuntResults(hunt_id)
    self.assertLen(sample_results, num_results)

  def testCountHuntResultsReturnsCorrectResultsWithoutSubflowResults(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    _, subflow_id = self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=hunt_id,
    )

    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)
    subflow_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=subflow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(subflow_results)

    num_results = self.db.CountHuntResults(hunt_id)
    self.assertLen(sample_results, num_results)

  def testCountHuntResultsCorrectlyAppliesWithTagFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)

    num_results = self.db.CountHuntResults(hunt_id, with_tag="blah")
    self.assertEqual(num_results, 0)

    num_results = self.db.CountHuntResults(hunt_id, with_tag="tag_1")
    self.assertEqual(num_results, 1)

  def testCountHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          count_per_type=1,
      )
      sample_results.extend(results)
      self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_id, with_type=rdf_client.ClientInformation.__name__
    )
    self.assertEqual(num_results, 0)

    num_results = self.db.CountHuntResults(
        hunt_id, with_type=rdf_client.ClientSummary.__name__
    )
    self.assertEqual(num_results, 10)

    num_results = self.db.CountHuntResults(
        hunt_id, with_type=rdf_client.ClientCrash.__name__
    )
    self.assertEqual(num_results, 10)

  def testCountHuntResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          count_per_type=5,
      )
      sample_results.extend(results)
      self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_id, with_tag="tag_1", with_type=rdf_client.ClientSummary.__name__
    )
    self.assertEqual(num_results, 10)

  def testCountHuntResultsCorrectlyAppliesWithProtoTypeUrl(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

      summary_payload = jobs_pb2.ClientSummary()
      summary_any = any_pb2.Any()
      summary_any.Pack(summary_payload)
      results.append(
          flows_pb2.FlowResult(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              payload=summary_any,
          )
      )

      if i % 2 == 0:
        crash_payload = jobs_pb2.ClientCrash()
        crash_any = any_pb2.Any()
        crash_any.Pack(crash_payload)
        results.append(
            flows_pb2.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                hunt_id=hunt_id,
                payload=crash_any,
            )
        )

    self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_id,
        with_proto_type_url=(
            f"type.googleapis.com/{jobs_pb2.ClientSummary.DESCRIPTOR.full_name}"
        ),
    )
    self.assertEqual(num_results, 10)

    num_results = self.db.CountHuntResults(
        hunt_id,
        with_proto_type_url=(
            f"type.googleapis.com/{jobs_pb2.ClientCrash.DESCRIPTOR.full_name}"
        ),
    )
    self.assertEqual(num_results, 5)

  def testCountHuntResultsCorrectlyAppliesWithTagAndWithProtoTypeUrl(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)
    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    payload = jobs_pb2.ClientSummary()
    payload_any = any_pb2.Any()
    payload_any.Pack(payload)
    results = [
        flows_pb2.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            payload=payload_any,
            tag="foo",
        ),
        flows_pb2.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            payload=payload_any,
            tag="bar",
        ),
    ]
    self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_id,
        with_tag="foo",
        with_proto_type_url=(
            f"type.googleapis.com/{jobs_pb2.ClientSummary.DESCRIPTOR.full_name}"
        ),
    )
    self.assertEqual(num_results, 1)

  def testCountHuntResultsRaisesIfBothTypeAndProtoTypeUrlAreSet(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    with self.assertRaises(ValueError):
      self.db.CountHuntResults(
          hunt_id,
          with_type="ClientSummary",
          with_proto_type_url=(
              f"type.googleapis.com/{jobs_pb2.ClientSummary.DESCRIPTOR.full_name}"
          ),
      )

  def testCountHuntResultsCorrectlyAppliesWithTimestampFilter(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
      sample_results = self._SampleSingleTypeHuntResults(
          client_id=client_id, flow_id=flow_id, hunt_id=hunt_id, count=10
      )
      self._WriteHuntResults(sample_results[:5])
      self._WriteHuntResults(sample_results[5:])

    hunt_results = self.db.ReadHuntResults(hunt_id, 0, 10)

    for hr in hunt_results:
      self.assertEqual(
          [hr],
          self.db.ReadHuntResults(
              hunt_id,
              0,
              10,
              with_timestamp=rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                  hr.timestamp
              ),
          ),
      )

  def testCountHuntResultsByTypeGroupsResultsCorrectly(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    results = self._SampleTwoTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id, count_per_type=5
    )
    self._WriteHuntResults(results)

    counts = self.db.CountHuntResultsByType(hunt_id)
    for key in counts:
      self.assertIsInstance(key, str)

    self.assertEqual(
        counts,
        {
            rdf_client.ClientSummary.__name__: 5,
            rdf_client.ClientCrash.__name__: 5,
        },
    )

  def testCountHuntResultsByProtoTypeUrl(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    results_by_type_url = self.db.CountHuntResultsByProtoTypeUrl(hunt_id)
    self.assertEmpty(results_by_type_url)

    client_id_1, flow_id_1 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    client_id_2, flow_id_2 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    any_proto = any_pb2.Any()

    any_proto.Pack(jobs_pb2.ClientSummary())
    client_summary = flows_pb2.FlowResult(
        client_id=client_id_1,
        flow_id=flow_id_1,
        hunt_id=hunt_id,
        payload=any_proto,
    )

    any_proto.Pack(jobs_pb2.ClientCrash())
    client_crash = flows_pb2.FlowResult(
        client_id=client_id_2,
        flow_id=flow_id_2,
        hunt_id=hunt_id,
        payload=any_proto,
    )

    self.db.WriteFlowResults([client_summary, client_crash, client_crash])

    results_by_type_url = self.db.CountHuntResultsByProtoTypeUrl(hunt_id)
    self.assertLen(results_by_type_url, 2)
    self.assertEqual(
        results_by_type_url[
            f"type.googleapis.com/{jobs_pb2.ClientSummary.DESCRIPTOR.full_name}"
        ],
        1,
    )
    self.assertEqual(
        results_by_type_url[
            f"type.googleapis.com/{jobs_pb2.ClientCrash.DESCRIPTOR.full_name}"
        ],
        2,
    )

  def testReadHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self.assertEmpty(self.db.ReadHuntFlows(hunt_id, 0, 10))

  def testReadHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    _, flow_id_1 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    _, flow_id_2 = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    flows = self.db.ReadHuntFlows(hunt_id, 0, 10)
    self.assertCountEqual([f.flow_id for f in flows], [flow_id_1, flow_id_2])

  def _BuildFilterConditionExpectations(self, hunt_id):
    _, running_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING, hunt_id=hunt_id
    )
    _, succeeded_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED, hunt_id=hunt_id
    )
    _, failed_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR, hunt_id=hunt_id
    )
    _, crashed_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.CRASHED, hunt_id=hunt_id
    )
    client_id, flow_with_results_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id
    )
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_with_results_id, hunt_id=hunt_id
    )
    self._WriteHuntResults(sample_results)

    return {
        db.HuntFlowsCondition.UNSET: [
            running_flow_id,
            succeeded_flow_id,
            failed_flow_id,
            crashed_flow_id,
            flow_with_results_id,
        ],
        db.HuntFlowsCondition.FAILED_FLOWS_ONLY: [failed_flow_id],
        db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY: [succeeded_flow_id],
        db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY: [
            failed_flow_id,
            succeeded_flow_id,
        ],
        db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY: [running_flow_id],
        db.HuntFlowsCondition.CRASHED_FLOWS_ONLY: [crashed_flow_id],
    }

  def testReadHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    expectations = self._BuildFilterConditionExpectations(hunt_id)
    for filter_condition, expected in expectations.items():
      results = self.db.ReadHuntFlows(
          hunt_id, 0, 10, filter_condition=filter_condition
      )
      results_ids = [r.flow_id for r in results]
      self.assertCountEqual(
          results_ids,
          expected,
          "Result items do not match for (filter_condition=%s): %s vs %s"
          % (filter_condition, expected, results_ids),
      )

  def testReadHuntFlowsCorrectlyAppliesOffsetAndCountFilters(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    expectations = self._BuildFilterConditionExpectations(hunt_id)
    for filter_condition, _ in expectations.items():
      full_results = self.db.ReadHuntFlows(
          hunt_id, 0, 1024, filter_condition=filter_condition
      )
      full_results_ids = [r.flow_id for r in full_results]
      for index in range(0, 2):
        for count in range(1, 3):
          results = self.db.ReadHuntFlows(
              hunt_id, index, count, filter_condition=filter_condition
          )
          results_ids = [r.flow_id for r in results]
          expected_ids = full_results_ids[index : index + count]
          self.assertCountEqual(
              results_ids,
              expected_ids,
              "Result items do not match for "
              "(filter_condition=%s, index=%d, count=%d): %s vs %s"
              % (filter_condition, index, count, expected_ids, results_ids),
          )

  def testReadHuntFlowsIgnoresSubflows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING
    )

    # Whatever state the subflow is in, it should be ignored.
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR,
    )
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
    )
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    for state, expected_results in [
        (db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY, 0),
        (db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY, 0),
        (db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY, 1),
    ]:
      results = self.db.ReadHuntFlows(hunt_id, 0, 10, filter_condition=state)
      self.assertLen(results, expected_results)

  def testCountHuntFlowsIgnoresSubflows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING
    )

    # Whatever state the subflow is in, it should be ignored.
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR,
    )
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
    )
    self._SetupHuntClientAndFlow(
        client_id=client_id,
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
    )

    self.assertEqual(self.db.CountHuntFlows(hunt_id), 1)

  def testCountHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self.assertEqual(self.db.CountHuntFlows(hunt_id), 0)

  def testCountHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    self.assertEqual(self.db.CountHuntFlows(hunt_id), 2)

  def testCountHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    expectations = self._BuildFilterConditionExpectations(hunt_id)
    for filter_condition, expected in expectations.items():
      result = self.db.CountHuntFlows(
          hunt_id, filter_condition=filter_condition
      )
      self.assertLen(
          expected,
          result,
          "Result count does not match for (filter_condition=%s): %d vs %d"
          % (filter_condition, len(expected), result),
      )

  def testReadHuntFlowErrors(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    flow_id_1 = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    pre_update_1_time = self.db.Now()

    flow_obj_1 = self.db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    flow_obj_1.backtrace = "File 'foo.py', line 1, in 'foo'"
    self.db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    pre_update_2_time = self.db.Now()

    flow_obj_2 = self.db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    self.db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    results = self.db.ReadHuntFlowErrors(hunt_id, offset=0, count=1024)
    self.assertLen(results, 2)

    self.assertEqual(results[client_id_1].message, "ERROR_1")
    self.assertGreater(results[client_id_1].time, pre_update_1_time)
    self.assertIsNotNone(results[client_id_1].backtrace)

    self.assertEqual(results[client_id_2].message, "ERROR_2")
    self.assertGreater(results[client_id_2].time, pre_update_2_time)
    self.assertIsNone(results[client_id_2].backtrace)

  def testReadHuntFlowErrorsIgnoreSubflows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id = db_test_utils.InitializeClient(self.db)

    flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    child_flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id,
        parent_flow_id=flow_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj = self.db.ReadFlowObject(client_id, flow_id)
    flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj.error_message = "ERROR"
    self.db.UpdateFlow(client_id, flow_id, flow_obj)

    child_flow_obj = self.db.ReadFlowObject(client_id, child_flow_id)
    child_flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
    child_flow_obj.error_message = "CHILD_ERROR"
    self.db.UpdateFlow(client_id, child_flow_id, child_flow_obj)

    results = self.db.ReadHuntFlowErrors(hunt_id, offset=0, count=1024)
    self.assertLen(results, 1)
    self.assertEqual(results[client_id].message, "ERROR")

  def testReadHuntFlowErrorsOffsetAndCount(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)
    client_id_3 = db_test_utils.InitializeClient(self.db)

    flow_id_1 = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id_1,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_2 = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id_2,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )
    flow_id_3 = db_test_utils.InitializeFlow(
        self.db,
        client_id=client_id_3,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
    )

    flow_obj_1 = self.db.ReadFlowObject(client_id_1, flow_id_1)
    flow_obj_1.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_1.error_message = "ERROR_1"
    self.db.UpdateFlow(client_id_1, flow_id_1, flow_obj_1)

    flow_obj_2 = self.db.ReadFlowObject(client_id_2, flow_id_2)
    flow_obj_2.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_2.error_message = "ERROR_2"
    self.db.UpdateFlow(client_id_2, flow_id_2, flow_obj_2)

    flow_obj_3 = self.db.ReadFlowObject(client_id_3, flow_id_3)
    flow_obj_3.flow_state = flows_pb2.Flow.FlowState.ERROR
    flow_obj_3.error_message = "ERROR_3"
    self.db.UpdateFlow(client_id_3, flow_id_3, flow_obj_3)

    results = self.db.ReadHuntFlowErrors(hunt_id, offset=1, count=1)
    self.assertLen(results, 1)
    self.assertEqual(results[client_id_2].message, "ERROR_2")

  def testReadHuntCountersForNewHunt(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)
    hunt_counters = self.db.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 0)
    self.assertEqual(hunt_counters.num_successful_clients, 0)
    self.assertEqual(hunt_counters.num_failed_clients, 0)
    self.assertEqual(hunt_counters.num_clients_with_results, 0)
    self.assertEqual(hunt_counters.num_crashed_clients, 0)
    self.assertEqual(hunt_counters.num_running_clients, 0)
    self.assertEqual(hunt_counters.num_results, 0)
    self.assertEqual(hunt_counters.total_cpu_seconds, 0)
    self.assertEqual(hunt_counters.total_network_bytes_sent, 0)

  def testReadHuntsCountersForEmptyList(self):
    hunts_counters = self.db.ReadHuntsCounters([])
    self.assertEmpty(hunts_counters)

  def testReadHuntsCountersForSeveralHunts(self):
    hunt_id_1 = db_test_utils.InitializeHunt(self.db)
    hunt_id_2 = db_test_utils.InitializeHunt(self.db)

    hunts_counters = self.db.ReadHuntsCounters([hunt_id_1, hunt_id_2])
    self.assertLen(hunts_counters, 2)
    self.assertIsInstance(hunts_counters[hunt_id_1], db.HuntCounters)
    self.assertIsInstance(hunts_counters[hunt_id_2], db.HuntCounters)

  def testReadHuntsCountersForASubsetOfCreatedHunts(self):
    db_test_utils.InitializeUser(self.db, "user")

    hunt_id_1 = db_test_utils.InitializeHunt(self.db, creator="user")
    _ = db_test_utils.InitializeHunt(self.db, creator="user")
    hunt_id_3 = db_test_utils.InitializeHunt(self.db, creator="user")

    hunts_counters = self.db.ReadHuntsCounters([hunt_id_1, hunt_id_3])

    self.assertLen(hunts_counters, 2)
    self.assertIsInstance(hunts_counters[hunt_id_1], db.HuntCounters)
    self.assertIsInstance(hunts_counters[hunt_id_3], db.HuntCounters)

  def testReadHuntsCountersReturnsSameResultAsReadHuntCounters(self):
    db_test_utils.InitializeUser(self.db, "user")

    hunt_id_1 = db_test_utils.InitializeHunt(self.db, creator="user")
    self._BuildFilterConditionExpectations(hunt_id_1)

    hunt_id_2 = db_test_utils.InitializeHunt(self.db, creator="user")
    self._BuildFilterConditionExpectations(hunt_id_2)

    hunts_counters = self.db.ReadHuntsCounters([hunt_id_1, hunt_id_2])
    self.assertLen(hunts_counters, 2)
    self.assertEqual(
        hunts_counters[hunt_id_1],
        self.db.ReadHuntCounters(hunt_id_1),
    )
    self.assertEqual(
        hunts_counters[hunt_id_2],
        self.db.ReadHuntCounters(hunt_id_2),
    )

  def testReadHuntCountersCorrectlyAggregatesResultsAmongDifferentFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    expectations = self._BuildFilterConditionExpectations(hunt_id)

    hunt_counters = self.db.ReadHuntCounters(hunt_id)
    self.assertLen(
        expectations[db.HuntFlowsCondition.UNSET], hunt_counters.num_clients
    )
    self.assertLen(
        expectations[db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY],
        hunt_counters.num_successful_clients,
    )
    self.assertLen(
        expectations[db.HuntFlowsCondition.FAILED_FLOWS_ONLY],
        hunt_counters.num_failed_clients,
    )
    self.assertLen(
        expectations[db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY],
        hunt_counters.num_running_clients,
    )

    # _BuildFilterConditionExpectations writes 10 sample results for one client.
    self.assertEqual(hunt_counters.num_clients_with_results, 1)
    self.assertLen(
        expectations[db.HuntFlowsCondition.CRASHED_FLOWS_ONLY],
        hunt_counters.num_crashed_clients,
    )

    # _BuildFilterConditionExpectations writes 10 sample results.
    self.assertEqual(hunt_counters.num_results, 10)

    self.assertEqual(hunt_counters.total_cpu_seconds, 0)
    self.assertEqual(hunt_counters.total_network_bytes_sent, 0)

    # Check that after adding a flow with resource metrics, total counters
    # get updated.
    client_id = db_test_utils.InitializeClient(self.db)
    db_test_utils.InitializeFlow(
        self.db,
        client_id,
        flow_id=hunt_id,
        parent_hunt_id=hunt_id,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=4.5, system_cpu_time=10
        ),
        network_bytes_sent=42,
    )

    hunt_counters = self.db.ReadHuntCounters(hunt_id)
    self.assertAlmostEqual(hunt_counters.total_cpu_seconds, 14.5)
    self.assertEqual(hunt_counters.total_network_bytes_sent, 42)

  def testReadHuntClientResourcesStatsIgnoresSubflows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db,
        client_id,
        flow_id=hunt_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
        parent_hunt_id=hunt_id,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=100, system_cpu_time=200
        ),
        network_bytes_sent=300,
    )

    # Create a subflow that used some resources too. This resource usage is
    # already accounted for in the parent flow so the overall hunt resource
    # usage should ignore those numbers.
    sub_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id="12345678",
        parent_flow_id=flow_id,
        parent_hunt_id=hunt_id,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=10, system_cpu_time=20
        ),
        network_bytes_sent=30,
    )
    sub_flow = mig_flow_objects.ToProtoFlow(sub_flow)
    self.db.WriteFlowObject(sub_flow)

    usage_stats = self.db.ReadHuntClientResourcesStats(hunt_id)
    network_bins = usage_stats.network_bytes_sent_stats.histogram.bins
    user_cpu_bins = usage_stats.user_cpu_stats.histogram.bins
    system_cpu_bins = usage_stats.system_cpu_stats.histogram.bins

    self.assertEqual(usage_stats.network_bytes_sent_stats.sum, 300)
    self.assertEqual(sum([b.num for b in network_bins]), 1)
    self.assertEqual(usage_stats.system_cpu_stats.sum, 200)
    self.assertEqual(sum([b.num for b in system_cpu_bins]), 1)
    self.assertEqual(usage_stats.user_cpu_stats.sum, 100)
    self.assertEqual(sum([b.num for b in user_cpu_bins]), 1)
    self.assertLen(usage_stats.worst_performers, 1)

  def testReadHuntClientResourcesStatsCorrectlyAggregatesData(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    flow_data = []

    for i in range(10):
      user_cpu_time = 4.5 + i
      system_cpu_time = 10 + i * 2
      network_bytes_sent = 42 + i * 3

      client_id = db_test_utils.InitializeClient(self.db)
      flow_id = db_test_utils.InitializeFlow(
          self.db,
          client_id,
          flow_id=hunt_id,
          flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
          parent_hunt_id=hunt_id,
          cpu_time_used=rdf_client_stats.CpuSeconds(
              user_cpu_time=user_cpu_time, system_cpu_time=system_cpu_time
          ),
          network_bytes_sent=network_bytes_sent,
      )

      flow_data.append((
          client_id,
          flow_id,
          (user_cpu_time, system_cpu_time, network_bytes_sent),
      ))

    usage_stats = self.db.ReadHuntClientResourcesStats(hunt_id)

    expected_cpu_bins = models_hunts.CPU_STATS_BINS
    expected_network_bins = models_hunts.NETWORK_STATS_BINS
    expected_user_cpu_histogram = jobs_pb2.StatsHistogram(
        bins=[
            jobs_pb2.StatsHistogramBin(num=num, range_max_value=max_range)
            for num, max_range in zip(
                12 * [0] + [1, 1, 1, 1, 1, 1, 4, 0], expected_cpu_bins
            )
        ]
    )

    expected_system_cpu_histogram = jobs_pb2.StatsHistogram(
        bins=[
            jobs_pb2.StatsHistogramBin(num=num, range_max_value=max_range)
            for num, max_range in zip(18 * [0] + [3, 7], expected_cpu_bins)
        ]
    )
    expected_network_histogram = jobs_pb2.StatsHistogram(
        bins=[
            jobs_pb2.StatsHistogramBin(num=num, range_max_value=max_range)
            for num, max_range in zip(
                [0, 0, 8, 2] + 14 * [0], expected_network_bins
            )
        ]
    )

    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.sum, 90)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.stddev, 2.87228, 5)
    self.assertLen(
        usage_stats.user_cpu_stats.histogram.bins,
        len(expected_user_cpu_histogram.bins),
    )
    for bin_index, (b, exp_b) in enumerate(
        zip(
            usage_stats.user_cpu_stats.histogram.bins,
            expected_user_cpu_histogram.bins,
        )
    ):
      self.assertAlmostEqual(
          b.range_max_value, exp_b.range_max_value, msg=f"bin index {bin_index}"
      )
      self.assertEqual(b.num, exp_b.num, msg=f"bin index {bin_index}")

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.sum, 190)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.stddev, 5.74456, 5)
    self.assertLen(
        usage_stats.system_cpu_stats.histogram.bins,
        len(expected_system_cpu_histogram.bins),
    )
    for bin_index, (b, exp_b) in enumerate(
        zip(
            usage_stats.system_cpu_stats.histogram.bins,
            expected_system_cpu_histogram.bins,
        )
    ):
      self.assertAlmostEqual(
          b.range_max_value, exp_b.range_max_value, msg=f"bin index {bin_index}"
      )
      self.assertEqual(b.num, exp_b.num, msg=f"bin index {bin_index}")

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.sum, 555)
    self.assertAlmostEqual(
        usage_stats.network_bytes_sent_stats.stddev, 8.6168, 4
    )
    self.assertLen(
        usage_stats.network_bytes_sent_stats.histogram.bins,
        len(expected_network_histogram.bins),
    )
    for bin_index, (b, model_b) in enumerate(
        zip(
            usage_stats.network_bytes_sent_stats.histogram.bins,
            expected_network_histogram.bins,
        )
    ):
      self.assertAlmostEqual(
          b.range_max_value,
          model_b.range_max_value,
          msg=f"bin index {bin_index}",
      )
      self.assertEqual(b.num, model_b.num, msg=f"bin index {bin_index}")

    self.assertLen(usage_stats.worst_performers, 10)
    for worst_performer, flow_d in zip(
        usage_stats.worst_performers, reversed(flow_data)
    ):
      (
          client_id,
          flow_id,
          (user_cpu_time, system_cpu_time, network_bytes_sent),
      ) = flow_d
      self.assertEqual(
          rdf_client.ClientURN.FromHumanReadable(
              worst_performer.client_id
          ).Basename(),
          client_id,
      )
      self.assertAlmostEqual(
          worst_performer.cpu_usage.user_cpu_time, user_cpu_time
      )
      self.assertAlmostEqual(
          worst_performer.cpu_usage.system_cpu_time, system_cpu_time
      )
      self.assertEqual(worst_performer.network_bytes_sent, network_bytes_sent)
      self.assertEqual(
          rdfvalue.SessionID.FromHumanReadable(
              worst_performer.session_id
          ).Path(),
          "/%s/%s" % (client_id, flow_id),
      )

  def testReadHuntClientResourcesStatsCorrectlyAggregatesVeryLargeNumbers(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id_1 = db_test_utils.InitializeClient(self.db)
    db_test_utils.InitializeFlow(
        self.db,
        client_id_1,
        flow_id=hunt_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
        parent_hunt_id=hunt_id,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=3810072130, system_cpu_time=3810072130
        ),
        network_bytes_sent=3810072130,
    )

    client_id_2 = db_test_utils.InitializeClient(self.db)
    db_test_utils.InitializeFlow(
        self.db,
        client_id_2,
        flow_id=hunt_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
        parent_hunt_id=hunt_id,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=2143939532, system_cpu_time=2143939532
        ),
        network_bytes_sent=2143939532,
    )

    usage_stats = self.db.ReadHuntClientResourcesStats(hunt_id)

    self.assertEqual(usage_stats.user_cpu_stats.num, 2)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.sum, 5954011662, 5)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.stddev, 833066299, 5)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.sum, 5954011662, 5)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.stddev, 833066299, 5)
    self.assertAlmostEqual(
        usage_stats.network_bytes_sent_stats.sum, 5954011662, 5
    )
    self.assertAlmostEqual(
        usage_stats.network_bytes_sent_stats.stddev, 833066299, 5
    )
    self.assertLen(usage_stats.worst_performers, 2)
    self.assertEqual(
        rdf_client.ClientURN.FromHumanReadable(
            usage_stats.worst_performers[0].client_id
        ).Path(),
        f"/{client_id_1}",
    )
    self.assertAlmostEqual(
        usage_stats.worst_performers[0].cpu_usage.user_cpu_time, 3810072130.0
    )
    self.assertAlmostEqual(
        usage_stats.worst_performers[0].cpu_usage.system_cpu_time, 3810072130.0
    )
    self.assertEqual(
        usage_stats.worst_performers[0].network_bytes_sent, 3810072130
    )
    self.assertEqual(
        rdfvalue.SessionID.FromHumanReadable(
            usage_stats.worst_performers[0].session_id
        ),
        f"/{client_id_1}/{hunt_id}",
    )
    self.assertEqual(
        rdf_client.ClientURN.FromHumanReadable(
            usage_stats.worst_performers[1].client_id
        ).Path(),
        f"/{client_id_2}",
    )
    self.assertAlmostEqual(
        usage_stats.worst_performers[1].cpu_usage.user_cpu_time, 2143939532.0
    )
    self.assertAlmostEqual(
        usage_stats.worst_performers[1].cpu_usage.system_cpu_time, 2143939532.0
    )
    self.assertEqual(
        usage_stats.worst_performers[1].network_bytes_sent, 2143939532
    )
    self.assertEqual(
        rdfvalue.SessionID.FromHumanReadable(
            usage_stats.worst_performers[1].session_id
        ),
        f"/{client_id_2}/{hunt_id}",
    )

  def testReadHuntClientResourcesStatsFiltersDirectFlowIdToMatchTheHuntID(self):
    client_id = db_test_utils.InitializeClient(self.db)
    hunt_id = db_test_utils.InitializeHunt(self.db)

    # The `flow_id` is randomly initialized, so it will not match the `hunt_id`.
    db_test_utils.InitializeFlow(
        self.db,
        client_id,
        parent_hunt_id=hunt_id,
    )

    usage_stats = self.db.ReadHuntClientResourcesStats(hunt_id)
    self.assertEqual(usage_stats.user_cpu_stats.num, 0)
    self.assertEqual(usage_stats.system_cpu_stats.num, 0)
    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 0)
    self.assertEmpty(usage_stats.worst_performers)

  def testReadHuntFlowsStatesAndTimestampsWorksCorrectlyForMultipleFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    expected = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

      if i % 2 == 0:
        flow_state = flows_pb2.Flow.FlowState.RUNNING
      else:
        flow_state = flows_pb2.Flow.FlowState.FINISHED
      self.db.UpdateFlow(client_id, flow_id, flow_state=flow_state)

      flow_obj = self.db.ReadFlowObject(client_id, flow_id)
      expected.append(
          db.FlowStateAndTimestamps(
              flow_state=flow_obj.flow_state,
              create_time=flow_obj.create_time,
              last_update_time=flow_obj.last_update_time,
          )
      )

    state_and_times = self.db.ReadHuntFlowsStatesAndTimestamps(hunt_id)
    self.assertCountEqual(state_and_times, expected)

  def testReadHuntFlowsStatesAndTimestampsIgnoresNestedFlows(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        client_id=client_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
    )

    state_and_times = self.db.ReadHuntFlowsStatesAndTimestamps(hunt_id)
    self.assertLen(state_and_times, 1)

    flow_obj = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(
        state_and_times[0],
        db.FlowStateAndTimestamps(
            flow_state=flow_obj.flow_state,
            create_time=flow_obj.create_time,
            last_update_time=flow_obj.last_update_time,
        ),
    )

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromSingleHuntFlow(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    output_plugin_id = "1"
    client_id, flow_id = self._SetupHuntClientAndFlow(
        client_id="C.12345678901234aa", hunt_id=hunt_id
    )
    self.db.WriteFlowOutputPluginLogEntry(
        flows_pb2.FlowOutputPluginLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            output_plugin_id=output_plugin_id,
            hunt_id=hunt_id,
            message="blah",
        )
    )

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id, output_plugin_id, 0, 10
    )
    self.assertLen(hunt_op_log_entries, 1)
    self.assertIsInstance(
        hunt_op_log_entries[0], flows_pb2.FlowOutputPluginLogEntry
    )
    self.assertEqual(hunt_op_log_entries[0].hunt_id, hunt_id)
    self.assertEqual(hunt_op_log_entries[0].client_id, client_id)
    self.assertEqual(hunt_op_log_entries[0].flow_id, flow_id)
    self.assertEqual(hunt_op_log_entries[0].message, "blah")

  def _WriteHuntOutputPluginLogEntries(self) -> str:
    hunt_id = db_test_utils.InitializeHunt(self.db)

    output_plugin_id = "1"
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          client_id="C.12345678901234a%d" % i, hunt_id=hunt_id
      )
      enum = flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      if i % 3 == 0:
        log_entry_type = enum.ERROR
      else:
        log_entry_type = enum.LOG
      self.db.WriteFlowOutputPluginLogEntry(
          flows_pb2.FlowOutputPluginLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              output_plugin_id=output_plugin_id,
              log_entry_type=log_entry_type,
              message="blah%d" % i,
          )
      )

    return hunt_id

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id, "1", 0, 100
    )
    self.assertLen(hunt_op_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_op_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesOffsetAndCountFilters(
      self,
  ):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    for i in range(10):
      hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
          hunt_id, "1", i, 1
      )
      self.assertLen(hunt_op_log_entries, 1)
      self.assertEqual(hunt_op_log_entries[0].message, "blah%d" % i)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesWithTypeFilter(self):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.UNSET,
    )
    self.assertEmpty(hunt_op_log_entries)

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(hunt_op_log_entries, 4)

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(hunt_op_log_entries, 6)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesCombinationOfFilters(
      self,
  ):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    hunt_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        0,
        1,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah1")

  def testCountHuntOutputPluginLogEntriesReturnsCorrectCount(self):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    num_entries = self.db.CountHuntOutputPluginLogEntries(hunt_id, "1")
    self.assertEqual(num_entries, 10)

  def testCountHuntOutputPluginLogEntriesRespectsWithTypeFilter(self):
    hunt_id = self._WriteHuntOutputPluginLogEntries()

    num_entries = self.db.CountHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertEqual(num_entries, 6)

    num_entries = self.db.CountHuntOutputPluginLogEntries(
        hunt_id,
        "1",
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertEqual(num_entries, 4)

  def testFlowStateUpdateUsingUpdateFlow(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING
    )

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY,
    )
    self.assertLen(results, 1)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY,
    )
    self.assertEmpty(results)

    proto_flow = self.db.ReadFlowObject(client_id, flow_id)
    proto_flow.flow_state = flows_pb2.Flow.FlowState.FINISHED
    self.db.UpdateFlow(client_id, proto_flow.flow_id, flow_obj=proto_flow)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY,
    )
    self.assertEmpty(results)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY,
    )
    self.assertLen(results, 1)

  def testFlowStateUpdateUsingReleaseProcessedFlow(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    flow_obj = self.db.LeaseFlowForProcessing(
        client_id, flow_id, rdfvalue.Duration.From(1, rdfvalue.MINUTES)
    )
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.UNSET)

    flow_obj.flow_state = flows_pb2.Flow.FlowState.ERROR
    self.db.ReleaseProcessedFlow(flow_obj)

    results = self.db.ReadHuntFlows(
        hunt_id, 0, 10, filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY
    )
    self.assertLen(results, 1)


# This file is a test library and thus does not require a __main__ block.
