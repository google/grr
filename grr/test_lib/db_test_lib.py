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
from grr_response_server import db_test_mixin
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

    rel_db_read_enabled_patch = mock.patch.object(
        data_store, "RelationalDBReadEnabled", return_value=True)
    rel_db_read_enabled_patch.start()
    self.addCleanup(rel_db_read_enabled_patch.stop)

    rel_db_write_enabled_patch = mock.patch.object(
        data_store, "RelationalDBWriteEnabled", return_value=True)
    rel_db_write_enabled_patch.start()
    self.addCleanup(rel_db_write_enabled_patch.stop)

    rel_db_flows_enabled_patch = mock.patch.object(
        data_store, "RelationalDBFlowsEnabled", return_value=True)
    rel_db_flows_enabled_patch.start()
    self.addCleanup(rel_db_flows_enabled_patch.stop)

    # grr_response_server/foreman.py uses this configuration option
    # directly, so it has to be explicitly overridden.
    config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads": True,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    super(RelationalDBEnabledMixin, self).setUp()


class StableRelationalDBEnabledMixin(object):
  """Mixin that emulates current stable RELDB/AFF4 configuration."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""
    config_overrider = test_lib.ConfigOverrider({
        "Database.aff4_enabled": True,
        "Database.useForReads": True,
        "Database.useForReads.artifacts": True,
        "Database.useForReads.audit": True,
        "Database.useForReads.client_messages": True,
        "Database.useForReads.client_reports": True,
        "Database.useForReads.client_stats": False,
        "Database.useForReads.cronjobs": True,
        "Database.useForReads.filestore": True,
        "Database.useForReads.foreman": True,
        "Database.useForReads.hunts": False,
        "Database.useForReads.message_handlers": True,
        "Database.useForReads.signed_binaries": True,
        "Database.useForReads.vfs": True,
        "Database.useRelationalFlows": True,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    super(StableRelationalDBEnabledMixin, self).setUp()


def DualDBTest(cls):
  """Decorator that creates an additional RELDB-enabled test class."""
  module = sys.modules[cls.__module__]
  cls_name = compatibility.GetName(cls)

  db_test_cls_name = "{}_RelationalDBEnabled".format(cls_name)
  db_test_cls = compatibility.MakeType(
      name=db_test_cls_name,
      base_classes=(RelationalDBEnabledMixin, cls),
      namespace={})
  setattr(module, db_test_cls_name, db_test_cls)

  db_test_cls_name = "{}_StableRelationalDBEnabled".format(cls_name)
  db_test_cls = compatibility.MakeType(
      name=db_test_cls_name,
      base_classes=(StableRelationalDBEnabledMixin, cls),
      namespace={})
  setattr(module, db_test_cls_name, db_test_cls)

  return cls


def TestDatabases(mysql=True):
  """Decorator that creates additional RELDB-enabled test classes."""

  def _TestDatabasesDecorator(cls):
    """Decorator that creates additional RELDB-enabled test classes."""
    module = sys.modules[cls.__module__]
    cls_name = compatibility.GetName(cls)
    DualDBTest(cls)

    if mysql:
      db_test_cls_name = "{}_MySQLEnabled".format(cls_name)
      db_test_cls = compatibility.MakeType(
          name=db_test_cls_name,
          base_classes=(RelationalDBEnabledMixin,
                        db_test_mixin.GlobalDatabaseTestMixin,
                        mysql_test.MySQLDatabaseProviderMixin, cls),
          namespace={})
      setattr(module, db_test_cls_name, db_test_cls)

    return cls

  return _TestDatabasesDecorator


def LegacyDataStoreOnly(f):
  """Decorator for tests that shouldn't run in RELDB-enabled environment."""

  @functools.wraps(f)
  def NewFunction(self, *args, **kw):
    if data_store.RelationalDBReadEnabled():
      self.skipTest("Test is not RELDB-friendly. Skipping...")

    return f(self, *args, **kw)

  return NewFunction
