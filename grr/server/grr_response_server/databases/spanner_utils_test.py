import datetime
from typing import Any, List

from absl.testing import absltest

from google.cloud import spanner as spanner_lib
from google.api_core.exceptions import NotFound


from grr_response_server.databases import spanner_test_lib
from grr_response_server.databases import spanner_utils

def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.TEST_SCHEMA_SDL_PATH, False)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class DatabaseTest(spanner_test_lib.TestCase):

  def setUp(self):
    super().setUp()

  #######################################
  # Transact Tests
  #######################################
  def testTransactionTransactional(self):

    def TransactionWrite(txn) -> None:
      txn.insert(
        table="Table",
        columns=("Key",),
        values=[("foo",), ("bar",)]
      )

    def TransactionRead(txn) -> List[Any]:
      result = list(txn.execute_sql("SELECT t.Key FROM Table AS t"))
      return result

    self.raw_db.Transact(TransactionWrite)
    results = self.raw_db.Transact(TransactionRead)
    self.assertCountEqual(results, [["foo"], ["bar"]])

  #######################################
  # Query Tests
  #######################################
  def testQuerySimple(self):
    results = list(self.raw_db.Query("SELECT 'foo', 42"))
    self.assertEqual(results, [["foo", 42]])

  def testQueryWithPlaceholders(self):
    results = list(self.raw_db.Query("SELECT '{}', '@p0'"))
    self.assertEqual(results, [["{}", "@p0"]])

  #######################################
  # QuerySingle Tests
  #######################################
  def testQuerySingle(self):
    result = self.raw_db.QuerySingle("SELECT 'foo', 42")
    self.assertEqual(result, ["foo", 42])

  def testQuerySingleEmpty(self):
    with self.assertRaises(NotFound):
      self.raw_db.QuerySingle("SELECT 'foo', 42 FROM UNNEST([])")

  def testQuerySingleMultiple(self):
    with self.assertRaises(ValueError):
      self.raw_db.QuerySingle("SELECT 'foo', 42 FROM UNNEST([1, 2])")

  #######################################
  # ParamQuery Tests
  #######################################
  def testParamQuerySingleParam(self):
    query = "SELECT {abc}"
    params = {"abc": 1337}

    results = list(self.raw_db.ParamQuery(query, params))
    self.assertEqual(results, [[1337,]])

  def testParamQueryMultipleParams(self):
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    query = "SELECT {int}, {str}, {timestamp}"
    params = {"int": 1337, "str": "quux", "timestamp": timestamp}

    results = list(self.raw_db.ParamQuery(query, params))
    self.assertEqual(results, [[1337, "quux", timestamp]])

  def testParamQueryMissingParams(self):
    with self.assertRaisesRegex(KeyError, "bar"):
      self.raw_db.ParamQuery("SELECT {foo}, {bar}", {"foo": 42})

  def testParamQueryExtraParams(self):
    query = "SELECT 42, {foo}"
    params = {"foo": "foo", "bar": "bar"}

    results = list(self.raw_db.ParamQuery(query, params))
    self.assertEqual(results, [[42, "foo"]])

  def testParamQueryIllegalSequence(self):
    with self.assertRaisesRegex(ValueError, "@p1337"):
      self.raw_db.ParamQuery("SELECT @p1337", {})

  def testParamQueryLegalSequence(self):
    results = list(self.raw_db.ParamQuery("SELECT '@p', '@q'", {}))
    self.assertEqual(results, [["@p", "@q"]])

  def testParamQueryBraceEscape(self):
    results = list(self.raw_db.ParamQuery("SELECT '{{foo}}'", {}))
    self.assertEqual(results, [["{foo}",]])

  #######################################
  # ParamExecute Tests
  #######################################
  def testParamExecuteSingleParam(self):
    query = """
      INSERT INTO Table(Key)
           VALUES ({key})
    """
    params = {"key": "foo"}

    self.raw_db.ParamExecute(query, params)

  #######################################
  # ParamQuerySingle Tests
  #######################################
  def testParamQuerySingle(self):
    query = "SELECT {str}, {int}"
    params = {"str": "foo", "int": 42}

    result = self.raw_db.ParamQuerySingle(query, params)
    self.assertEqual(result, ["foo", 42])

  def testParamQuerySingleEmpty(self):
    query = "SELECT {str}, {int} FROM UNNEST([])"
    params = {"str": "foo", "int": 42}

    with self.assertRaises(NotFound):
      self.raw_db.ParamQuerySingle(query, params)

  def testParamQuerySingleMultiple(self):
    query = "SELECT {str}, {int} FROM UNNEST([1, 2])"
    params = {"str": "foo", "int": 42}

    with self.assertRaises(ValueError):
      self.raw_db.ParamQuerySingle(query, params)

  #######################################
  # ExecutePartitioned Tests
  #######################################
  def testExecutePartitioned(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo"})
    self.raw_db.Insert(table="Table", row={"Key": "bar"})
    self.raw_db.Insert(table="Table", row={"Key": "baz"})

    self.raw_db.ExecutePartitioned("DELETE FROM Table AS t WHERE t.Key LIKE 'ba%'")
    
    results = list(self.raw_db.Query("SELECT t.Key FROM Table AS t"))
    self.assertLen(results, 1)
    self.assertEqual(results[0], ["foo",])

  #######################################
  # Insert Tests
  #######################################
  def testInsert(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo", "Column": "foo@x.com"})
    self.raw_db.Insert(table="Table", row={"Key": "bar", "Column": "bar@x.com"})

    results = list(self.raw_db.Query("SELECT t.Column FROM Table AS t"))
    self.assertCountEqual(results, [["foo@x.com",], ["bar@x.com",]])

  #######################################
  # Update Tests
  #######################################
  def testUpdate(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo", "Column": "bar@y.com"})
    self.raw_db.Update(table="Table", row={"Key": "foo", "Column": "qux@y.com"})

    results = list(self.raw_db.Query("SELECT t.Column FROM Table AS t"))
    self.assertEqual(results, [["qux@y.com",]])

  def testUpdateNotExisting(self):
    with self.assertRaises(NotFound):
      self.raw_db.Update(table="Table", row={"Key": "foo", "Column": "x@y.com"})

  #######################################
  # InsertOrUpdate Tests
  #######################################
  def testInsertOrUpdate(self):
    row = {"Key": "foo"}

    row["Column"] = "bar@example.com"
    self.raw_db.InsertOrUpdate(table="Table", row=row)

    row["Column"] = "baz@example.com"
    self.raw_db.InsertOrUpdate(table="Table", row=row)

    results = list(self.raw_db.Query("SELECT t.Column FROM Table AS t"))
    self.assertEqual(results, [["baz@example.com",]])

  #######################################
  # Delete Tests
  #######################################
  def testDelete(self):
    self.raw_db.InsertOrUpdate(table="Table", row={"Key": "foo"})
    self.raw_db.Delete(table="Table", key=("foo",))

    results = list(self.raw_db.Query("SELECT t.Key FROM Table AS t"))
    self.assertEmpty(results)

  def testDeleteSingle(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo"})
    self.raw_db.InsertOrUpdate(table="Table", row={"Key": "bar"})
    self.raw_db.Delete(table="Table", key=("foo",))

    results = list(self.raw_db.Query("SELECT t.Key FROM Table AS t"))
    self.assertEqual(results, [["bar",]])

  def testDeleteNotExisting(self):
    # Should not raise.
    self.raw_db.Delete(table="Table", key=("foo",))

  #######################################
  # DeleteWithPrefix Tests
  #######################################
  def testDeleteWithPrefix(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo"})
    self.raw_db.Insert(table="Table", row={"Key": "quux"})

    self.raw_db.Insert(table="Subtable", row={"Key": "foo", "Subkey": "bar"})
    self.raw_db.Insert(table="Subtable", row={"Key": "foo", "Subkey": "baz"})
    self.raw_db.Insert(table="Subtable", row={"Key": "quux", "Subkey": "norf"})

    self.raw_db.DeleteWithPrefix(table="Subtable", key_prefix=["foo"])

    results = list(self.raw_db.Query("SELECT t.Key, t.Subkey FROM Subtable AS t"))
    self.assertLen(results, 1)
    self.assertEqual(results[0], ["quux", "norf"])

  #######################################
  # Read Tests
  #######################################
  def testReadSimple(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo", "Column": "foo@x.com"})

    result = self.raw_db.Read(table="Table", key=("foo",), cols=("Column",))
    self.assertEqual(result, ["foo@x.com"])

  def testReadNotExisting(self):
    with self.assertRaises(NotFound):
      self.raw_db.Read(table="Table", key=("foo",), cols=("Column",))
  
  #######################################
  # ReadSet Tests
  #######################################
  def testReadSetEmpty(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo", "Column": "foo@x.com"})

    rows = spanner_lib.KeySet()
    results = list(self.raw_db.ReadSet(table="Table", rows=rows, cols=("Column",)))

    self.assertEmpty(results)

  def testReadSetSimple(self):
    self.raw_db.Insert(table="Table", row={"Key": "foo", "Column": "foo@x.com"})
    self.raw_db.Insert(table="Table", row={"Key": "bar", "Column": "bar@y.com"})
    self.raw_db.Insert(table="Table", row={"Key": "baz", "Column": "baz@z.com"})

    keyset = spanner_lib.KeySet(keys=[["foo"], ["bar"]])
    results = list(self.raw_db.ReadSet(table="Table", rows=keyset, cols=("Column",)))

    self.assertIn(["foo@x.com"], results)
    self.assertIn(["bar@y.com"], results)
    self.assertNotIn(["baz@z.com"], results)

  #######################################
  # Mutate Tests
  #######################################
  def testMutateSimple(self):

    def Mutation(mut) -> None:
      mut.insert(
        table="Table",
        columns=("Key",),
        values=[("foo",)]
      )
      mut.insert(
        table="Table",
        columns=("Key",),
        values=[("bar",)]
      )

    self.raw_db.Mutate(Mutation)

    results = list(self.raw_db.Query("SELECT t.Key FROM Table AS t"))
    self.assertCountEqual(results, [["foo",], ["bar",]])

  def testMutateException(self):

    def Mutation(mut) -> None:
      mut.insert(
        table="Table",
        columns=("Key",),
        values=[("foo",)]
      )
      raise RuntimeError()

    with self.assertRaises(RuntimeError):
      self.raw_db.Mutate(Mutation)

if __name__ == "__main__":
  absltest.main()
