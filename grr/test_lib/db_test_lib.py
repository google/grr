#!/usr/bin/env python
"""Test utilities for RELDB-related testing."""
from __future__ import absolute_import
from __future__ import division

import functools
import sys

import mock

from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr.test_lib import test_lib


class RelationalDBEnabledMixin(object):
  """Mixin that enables RELDB in setUp/tearDown methods."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""

    self._aff4_disabler = mock.patch.object(
        data_store, "AFF4Enabled", return_value=False)
    # TODO(amoser): This does not work yet. We need to clean up lots of flows
    # that still use AFF4 but also we need to make hunts work on the relational
    # db only.
    # self._aff4_disabler.start()

    self._rel_db_read_enabled_patch = mock.patch.object(
        data_store, "RelationalDBReadEnabled", return_value=True)
    self._rel_db_read_enabled_patch.start()

    self._rel_db_write_enabled_patch = mock.patch.object(
        data_store, "RelationalDBWriteEnabled", return_value=True)
    self._rel_db_write_enabled_patch.start()

    self._foreman_patch = mock.patch.object(
        foreman_rules, "RelationalDBReadEnabled", return_value=True)
    self._foreman_patch.start()

    # TODO(amoser): Remove once storing the foreman rules in the
    # relational db works.
    self._foreman_config_overrider = test_lib.ConfigOverrider(
        {"Database.useForReads.foreman": True})
    self._foreman_config_overrider.Start()

    self._vfs_config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.vfs": True,
    })
    self._vfs_config_overrider.Start()

    self._artifacts_config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.artifacts": True,
    })
    self._artifacts_config_overrider.Start()

    self._signed_binaries_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.signed_binaries": True,
    })
    self._signed_binaries_overrider.Start()

    self._rel_db_flows_enabled_patch = mock.patch.object(
        data_store, "RelationalDBFlowsEnabled", return_value=True)
    self._rel_db_flows_enabled_patch.start()

    self._filestore_config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.filestore": True,
    })
    self._filestore_config_overrider.Start()

    super(RelationalDBEnabledMixin, self).setUp()

  def tearDown(self):  # pylint: disable=invalid-name
    """Cleans up the patchers."""
    super(RelationalDBEnabledMixin, self).tearDown()

    # TODO(amoser): Enable this, see comment above.
    # self._aff4_disabler.stop()
    self._rel_db_flows_enabled_patch.stop()
    self._rel_db_read_enabled_patch.stop()
    self._rel_db_write_enabled_patch.stop()
    self._foreman_patch.stop()
    self._foreman_config_overrider.Stop()
    self._vfs_config_overrider.Stop()
    self._artifacts_config_overrider.Stop()
    self._signed_binaries_overrider.Stop()
    self._filestore_config_overrider.Stop()


class StableRelationalDBEnabledMixin(object):
  """Mixin that emulates current stable RELDB/AFF4 configuration."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""
    self._config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.foreman": True,
        "Database.useForReads.message_handlers": True,
        "Database.useForReads.stats": True,
        "Database.useForReads.signed_binaries": True,
        "Database.useForReads.cronjobs": True,
    })
    self._config_overrider.Start()

    super(StableRelationalDBEnabledMixin, self).setUp()

  def tearDown(self):  # pylint: disable=invalid-name
    """Cleans up the patchers."""
    super(StableRelationalDBEnabledMixin, self).tearDown()

    self._config_overrider.Stop()


def DualDBTest(cls):
  """Decorator that creates an additional RELDB-enabled test class."""

  module = sys.modules[cls.__module__]

  db_test_cls_name = cls.__name__ + "_RelationalDBEnabled"
  db_test_cls = type(db_test_cls_name, (RelationalDBEnabledMixin, cls), {})
  setattr(module, db_test_cls_name, db_test_cls)

  db_test_cls_name = cls.__name__ + "_StableRelationalDBEnabled"
  db_test_cls = type(db_test_cls_name, (StableRelationalDBEnabledMixin, cls),
                     {})
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
