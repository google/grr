#!/usr/bin/env python
"""Base class for all memory database tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mem


class MemoryDBTestBase(db_test_mixin.DatabaseSetupMixin):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None

  def CreateBlobStore(self):
    return self.CreateDatabase()
