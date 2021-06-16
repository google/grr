#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""

import functools
import sys
from unittest import mock

from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server.blob_stores import db_blob_store
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mem
from grr_response_server.databases import mysql_test


def TestDatabases(mysql=True):
  """Decorator that creates additional RELDB-enabled test classes."""

  def _TestDatabasesDecorator(cls):
    """Decorator that creates additional RELDB-enabled test classes."""
    module = sys.modules[cls.__module__]
    cls_name = compatibility.GetName(cls)

    # Prevent MRO issues caused by inheriting the same Mixin multiple times.
    base_classes = ()
    if not issubclass(cls, db_test_mixin.GlobalDatabaseTestMixin):
      base_classes += (db_test_mixin.GlobalDatabaseTestMixin,)

    if mysql:
      db_test_cls_name = "{}_MySQLEnabled".format(cls_name)
      db_test_cls = compatibility.MakeType(
          name=db_test_cls_name,
          base_classes=base_classes +
          (mysql_test.MySQLDatabaseProviderMixin, cls),
          namespace={})
      setattr(module, db_test_cls_name, db_test_cls)

    return cls

  return _TestDatabasesDecorator


def WithDatabase(func):
  """A decorator for database-dependent test methods.

  This decorator is intended for tests that need to access database in their
  code. It will also augment the test function signature so that the database
  object is provided and can be manipulated.

  Args:
    func: A test method to be decorated.

  Returns:
    A database-aware function.
  """

  @functools.wraps(func)
  def Wrapper(*args, **kwargs):
    db = abstract_db.DatabaseValidationWrapper(mem.InMemoryDB())
    with mock.patch.object(data_store, "REL_DB", db):
      func(*(args + (db,)), **kwargs)

  return Wrapper


def WithDatabaseBlobstore(func):
  """A decorator for blobstore-dependent test methods.

  This decorator is intended for tests that need to access blobstore in their
  code. It will also augment the test function signature so that the blobstore
  object is provided and can be manipulated.

  The created test blobstore will use currently active relational database as a
  backend.

  Args:
    func: A test method to be decorated.

  Returns:
    A blobstore-aware function.
  """

  @functools.wraps(func)
  def Wrapper(*args, **kwargs):
    blobstore = db_blob_store.DbBlobStore()
    with mock.patch.object(data_store, "BLOBS", blobstore):
      func(*(args + (blobstore,)), **kwargs)

  return Wrapper
