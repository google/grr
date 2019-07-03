#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import sys

import mock

from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class RelationalDBEnabledMixin(object):
  """Mixin that enables RELDB in setUp/tearDown methods."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""

    aff4_disabler = mock.patch.object(
        data_store, "AFF4Enabled", return_value=False)
    aff4_disabler.start()
    self.addCleanup(aff4_disabler.stop)

    rel_db_enabled_patch = mock.patch.object(
        data_store, "RelationalDBEnabled", return_value=True)
    rel_db_enabled_patch.start()
    self.addCleanup(rel_db_enabled_patch.stop)

    # grr_response_server/foreman_rules.py uses this configuration option
    # directly, so it has to be explicitly overridden.
    config_overrider = test_lib.ConfigOverrider({
        "Database.enabled": True,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    super(RelationalDBEnabledMixin, self).setUp()


def TestDatabases(mysql=True):
  """Decorator that creates additional RELDB-enabled test classes."""

  def _TestDatabasesDecorator(cls):
    """Decorator that creates additional RELDB-enabled test classes."""
    module = sys.modules[cls.__module__]
    cls_name = compatibility.GetName(cls)

    # Prevent MRO issues caused by inheriting the same Mixin multiple times.
    base_classes = ()
    if not issubclass(cls, RelationalDBEnabledMixin):
      base_classes += (RelationalDBEnabledMixin,)
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


def LegacyDataStoreOnly(f):
  """Decorator for tests that shouldn't run in RELDB-enabled environment."""

  @functools.wraps(f)
  def NewFunction(self, *args, **kw):
    if data_store.RelationalDBEnabled():
      self.skipTest("Test is not RELDB-friendly. Skipping...")

    return f(self, *args, **kw)

  return NewFunction
