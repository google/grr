#!/usr/bin/env python
"""Tests for the hunt database api."""

import re

from absl.testing import absltest

from grr_response_server.databases import db_test_utils
from grr_response_server.databases import mem as mem_db


class TestOffsetAndCountTest(db_test_utils.QueryTestHelpersMixin,
                             absltest.TestCase):

  def testDoesNotRaiseWhenWorksAsExpected(self):
    items = range(10)
    self.DoOffsetAndCountTest(
        lambda: items,
        lambda offset, count: items[offset:offset + count],
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):
    items = range(10)

    def FetchRangeFn(offset, count):
      # Deliberate bug for offset > 5.
      if offset > 5:
        return []
      else:
        return items[offset:offset + count]

    with self.assertRaisesRegex(
        AssertionError,
        re.escape(
            "Results differ from expected (offset 6, count 1, foo): [] vs [6]")
    ):
      self.DoOffsetAndCountTest(lambda: items, FetchRangeFn, error_desc="foo")


class TestFilterCombinations(db_test_utils.QueryTestHelpersMixin,
                             absltest.TestCase):

  def testDoesNotRaiseWhenWorkingAsExpected(self):

    def FetchFn(bigger_than_3_only=None, less_than_7_only=None, even_only=None):
      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result

    self.DoFilterCombinationsTest(
        FetchFn,
        dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):

    def FetchFn(bigger_than_3_only=None, less_than_7_only=None, even_only=None):
      result = []
      for i in range(10):
        # This line introduces a bug.
        if bigger_than_3_only and less_than_7_only and i == 4:
          continue

        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result

    with self.assertRaisesRegex(
        AssertionError,
        re.escape(
            "Results differ from expected "
            "({'bigger_than_3_only': True, 'less_than_7_only': True}, foo): "
            "[5, 6] vs [4, 5, 6]")):
      self.DoFilterCombinationsTest(
          FetchFn,
          dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
          error_desc="foo")


class TestFilterCombinationsAndOffsetCountTest(
    db_test_utils.QueryTestHelpersMixin, absltest.TestCase):

  def testDoesNotRaiseWhenWorksAsExpected(self):

    def FetchFn(offset,
                count,
                bigger_than_3_only=None,
                less_than_7_only=None,
                even_only=None):
      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      return result[offset:offset + count]

    self.DoFilterCombinationsAndOffsetCountTest(
        FetchFn,
        dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
        error_desc="foo")

  def testRaisesWhenDoesNotWorkAsExpected(self):

    def FetchFn(offset,
                count,
                bigger_than_3_only=None,
                less_than_7_only=None,
                even_only=None):
      del offset  # Unused.

      result = []
      for i in range(10):
        if bigger_than_3_only and i <= 3:
          continue

        if less_than_7_only and i >= 7:
          continue

        if even_only and i % 2 != 0:
          continue

        result.append(i)

      # An intentionally buggy line.
      # Should have been: result[offset:offset + count]
      return result[0:count]

    with self.assertRaisesRegex(
        AssertionError,
        re.escape("Results differ from expected "
                  "(offset 1, count 1, {'bigger_than_3_only': True}, foo): "
                  "[4] vs [5]")):
      self.DoFilterCombinationsAndOffsetCountTest(
          FetchFn,
          dict(bigger_than_3_only=True, less_than_7_only=True, even_only=True),
          error_desc="foo")


class InitializeClientTest(absltest.TestCase):

  def testRandom(self):
    db = mem_db.InMemoryDB()

    client_id = db_test_utils.InitializeClient(db)
    self.assertIsNotNone(db.ReadClientMetadata(client_id))

  def testSupplied(self):
    db = mem_db.InMemoryDB()

    client_id = db_test_utils.InitializeClient(db, "C.012345678ABCDEFAA")
    self.assertEqual(client_id, "C.012345678ABCDEFAA")
    self.assertIsNotNone(db.ReadClientMetadata(client_id))


class InitializeUserTest(absltest.TestCase):

  def testRandom(self):
    db = mem_db.InMemoryDB()

    username = db_test_utils.InitializeUser(db)
    self.assertIsNotNone(db.ReadGRRUser(username))

  def testSupplied(self):
    db = mem_db.InMemoryDB()

    username = db_test_utils.InitializeUser(db, username="foobar")
    self.assertEqual(username, "foobar")
    self.assertIsNotNone(db.ReadGRRUser(username))


class InitializeFlowTest(absltest.TestCase):

  def testRandom(self):
    db = mem_db.InMemoryDB()

    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertIsNotNone(flow_obj)

  def testSupplied(self):
    db = mem_db.InMemoryDB()

    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id, flow_id="ABCDEF42")
    self.assertEqual(flow_id, "ABCDEF42")

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertIsNotNone(flow_obj)

  def testKwargs(self):
    db = mem_db.InMemoryDB()

    username = db_test_utils.InitializeUser(db)
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id, creator=username)

    flow_obj = db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.creator, username)


class InitializeHuntTest(absltest.TestCase):

  def testRandom(self):
    db = mem_db.InMemoryDB()

    hunt_id = db_test_utils.InitializeHunt(db)
    hunt_obj = db.ReadHuntObject(hunt_id)
    self.assertIsNotNone(hunt_obj)
    self.assertIsNotNone(db.ReadGRRUser(hunt_obj.creator))

  def testSupplied(self):
    db = mem_db.InMemoryDB()

    hunt_id = db_test_utils.InitializeHunt(db, hunt_id="ABCDEF42")
    self.assertEqual(hunt_id, "ABCDEF42")
    self.assertIsNotNone(db.ReadHuntObject(hunt_id))


class InitializeCronJobTest(absltest.TestCase):

  def testRandom(self):
    db = mem_db.InMemoryDB()

    cron_job_id = db_test_utils.InitializeCronJob(db)
    self.assertIsNotNone(db.ReadCronJob(cron_job_id))

  def testSupplied(self):
    db = mem_db.InMemoryDB()

    cron_job_id = db_test_utils.InitializeCronJob(db, cron_job_id="QUUX1337")
    self.assertEqual(cron_job_id, "QUUX1337")
    self.assertIsNotNone(db.ReadCronJob(cron_job_id))


if __name__ == "__main__":
  absltest.main()
