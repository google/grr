#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from grr_response_core.lib.util import compatibility
from grr_response_server.databases import db_test_mixin
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
