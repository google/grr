#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""

import functools
import sys

import mock

from grr.server.grr_response_server import data_store


class RelationalDBEnabledMixin(object):
  """Mixin that enables RELDB in setUp/tearDown methods."""

  def setUp(self):  # pylint: disable=invalid-name
    self._rel_db_read_enabled_patch = mock.patch.object(
        data_store, "RelationalDBReadEnabled", return_value=True)
    self._rel_db_read_enabled_patch.start()

    self._rel_db_write_enabled_patch = mock.patch.object(
        data_store, "RelationalDBWriteEnabled", return_value=True)
    self._rel_db_write_enabled_patch.start()

    super(RelationalDBEnabledMixin, self).setUp()

  def tearDown(self):  # pylint: disable=invalid-name
    super(RelationalDBEnabledMixin, self).tearDown()

    self._rel_db_read_enabled_patch.stop()
    self._rel_db_write_enabled_patch.stop()


def DualDBTest(cls):
  """Decorator that creates an additional RELDB-enabled test class."""

  db_test_cls_name = cls.__name__ + "_RelationalDBEnabled"
  db_test_cls = type(db_test_cls_name, (RelationalDBEnabledMixin, cls), {})
  module = sys.modules[cls.__module__]
  setattr(module, db_test_cls_name, db_test_cls)

  return cls


def LegacyDataStoreOnly(f):
  """Decorator for tests that shouldn't run in RELDB-enabled environemnt."""

  @functools.wraps(f)
  def NewFunction(self, *args, **kw):
    if data_store.RelationalDBReadEnabled():
      self.skipTest("Test is not RELDB-friendly. Skipping...")

    return f(self, *args, **kw)

  return NewFunction
