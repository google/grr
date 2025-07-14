"""A library with utilities for testing the Spanner database implementation."""
import os
import unittest

from typing import Optional

from absl.testing import absltest

from google.cloud import spanner_v1 as spanner_lib
from google.cloud import spanner_admin_database_v1
from google.cloud.spanner import Client, KeySet
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin

from grr_response_server.databases import spanner_utils
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import spanner as spanner_db

OPERATION_TIMEOUT_SECONDS = 240

PROD_SCHEMA_SDL_PATH = "grr/server/grr_response_server/databases/spanner.sdl"
TEST_SCHEMA_SDL_PATH = "grr/server/grr_response_server/databases/spanner_test.sdl"

PROTO_DESCRIPTOR_PATH = "grr/server/grr_response_server/databases/spanner_grr.pb"

def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value

def _readSchemaFromFile(file_path):
    """Reads DDL statements from a file."""
    with open(file_path, 'r') as f:
        # Read the whole file and split by semicolon.
        # Filter out any empty strings resulting from split.
        ddl_statements = [stmt.strip() for stmt in f.read().split(';') if stmt.strip()]
    return ddl_statements

def _readProtoDescriptorFromFile():
    """Reads DDL statements from a file."""
    with open(PROTO_DESCRIPTOR_PATH, 'rb') as f:
        proto_descriptors = f.read()
    return proto_descriptors

def Init(sdl_path: str, proto_bundle: bool) -> None:
  """Initializes the Spanner testing environment.

  This must be called only once per test process. A `setUpModule` method is
  a perfect place for it.

  """
  global _TEST_DB

  if _TEST_DB is not None:
    raise AssertionError("Spanner test library already initialized")

  project_id = _GetEnvironOrSkip("SPANNER_PROJECT_ID")
  instance_id = _GetEnvironOrSkip("SPANNER_INSTANCE")
  database_id = _GetEnvironOrSkip("SPANNER_DATABASE")

  spanner_client = Client(project_id)
  database_admin_api = spanner_client.database_admin_api

  ddl_statements = _readSchemaFromFile(sdl_path)

  proto_descriptors = bytes()

  if proto_bundle:
    proto_descriptors = _readProtoDescriptorFromFile()

  request = spanner_database_admin.CreateDatabaseRequest(
    parent=database_admin_api.instance_path(spanner_client.project, instance_id),
    create_statement=f"CREATE DATABASE `{database_id}`",
    extra_statements=ddl_statements,
    proto_descriptors=proto_descriptors
  )

  operation = database_admin_api.create_database(request=request)

  print("Waiting for operation to complete...")
  database = operation.result(OPERATION_TIMEOUT_SECONDS)

  print(
    "Created database {} on instance {}".format(
            database.name,
            database_admin_api.instance_path(spanner_client.project, instance_id),
    )
  )

  instance = spanner_client.instance(instance_id)
  _TEST_DB = instance.database(database_id)
 

def TearDown() -> None:
  """Tears down the Spanner testing environment.

  This must be called once per process after all the tests.
  A `tearDownModule` is a perfect place for it.
  """
  if _TEST_DB is not None:
    # Create a client
    _TEST_DB.drop()


class TestCase(absltest.TestCase):
  """A base test case class for Spanner tests.

  This class takes care of setting up a clean database for every test method. It
  is intended to be used with database test suite mixins.
  """

  project_id = None

  def setUp(self):
    super().setUp()

    self.project_id = _GetEnvironOrSkip("PROJECT_ID")

    _clean_database()

    self.raw_db = spanner_utils.Database(_TEST_DB, self.project_id)

    spannerDB = spanner_db.SpannerDB(self.raw_db)
    self.db = abstract_db.DatabaseValidationWrapper(spannerDB)

def _get_table_names(db):
    with db.snapshot() as snapshot:
        query_result = snapshot.execute_sql(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';"
        )
        table_names = set()
        for row in query_result:
            table_names.add(row[0])

        return table_names


def _clean_database() -> None:
  """Creates an empty test spanner database."""

  table_names = _get_table_names(_TEST_DB)
  keyset = KeySet(all_=True)

  with _TEST_DB.batch() as batch:
    # Deletes sample data from all tables in the given database.
    for table_name in table_names:
      batch.delete(table_name, keyset)

_TEST_DB: spanner_lib.database = None