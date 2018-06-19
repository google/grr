#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""

import functools
import sys

import mock

from grr.server.grr_response_server import data_store
from grr.test_lib import test_lib


class RelationalDBEnabledMixin(object):
  """Mixin that enables RELDB in setUp/tearDown methods."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""

    self._rel_db_read_enabled_patch = mock.patch.object(
        data_store, "RelationalDBReadEnabled", return_value=True)
    self._rel_db_read_enabled_patch.start()

    self._rel_db_write_enabled_patch = mock.patch.object(
        data_store, "RelationalDBWriteEnabled", return_value=True)
    self._rel_db_write_enabled_patch.start()

    self._config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads": True
    })
    self._config_overrider.Start()

    # TODO(amoser): Remove once storing the foreman rules in the
    # relational db works.
    self._foreman_config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.foreman": True
    })
    self._foreman_config_overrider.Start()

    self._vfs_config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.vfs": True,
    })
    self._foreman_config_overrider.Start()

    super(RelationalDBEnabledMixin, self).setUp()

  def tearDown(self):  # pylint: disable=invalid-name
    super(RelationalDBEnabledMixin, self).tearDown()

    self._rel_db_read_enabled_patch.stop()
    self._rel_db_write_enabled_patch.stop()
    self._config_overrider.Stop()
    self._foreman_config_overrider.Stop()
    self._vfs_config_overrider.Stop()


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
