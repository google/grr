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

    self._rel_db_flows_enabled_patch = mock.patch.object(
        data_store, "RelationalDBFlowsEnabled", return_value=True)
    self._rel_db_flows_enabled_patch.start()

    # grr_response_server/foreman.py uses this configuration option
    # directly, so it has to be explicitly overridden.
    self._config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads": True,
    })
    self._config_overrider.Start()

    super(RelationalDBEnabledMixin, self).setUp()

  def tearDown(self):  # pylint: disable=invalid-name
    """Cleans up the patchers."""
    super(RelationalDBEnabledMixin, self).tearDown()

    # TODO(amoser): Enable this, see comment above.
    # self._aff4_disabler.stop()
    self._config_overrider.Stop()
    self._rel_db_flows_enabled_patch.stop()
    self._rel_db_read_enabled_patch.stop()
    self._rel_db_write_enabled_patch.stop()


class StableRelationalDBEnabledMixin(object):
  """Mixin that emulates current stable RELDB/AFF4 configuration."""

  def setUp(self):  # pylint: disable=invalid-name
    """The setUp method."""
    self._config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.artifacts": False,
        "Database.useForReads.audit": False,
        "Database.useForReads.client_messages": True,
        "Database.useForReads.client_reports": False,
        "Database.useForReads.cronjobs": True,
        "Database.useForReads.filestore": True,
        "Database.useForReads.foreman": True,
        "Database.useForReads.message_handlers": True,
        "Database.useForReads.signed_binaries": True,
        "Database.useForReads.stats": False,
        "Database.useForReads.vfs": True,
        "Database.useRelationalFlows": True,
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


def LegacyDataStoreOnly(f):
  """Decorator for tests that shouldn't run in RELDB-enabled environment."""

  @functools.wraps(f)
  def NewFunction(self, *args, **kw):
    if data_store.RelationalDBReadEnabled():
      self.skipTest("Test is not RELDB-friendly. Skipping...")

    return f(self, *args, **kw)

  return NewFunction
