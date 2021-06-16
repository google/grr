#!/usr/bin/env python
"""Base class for all memory database tests."""

from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mem


class MemoryDBTestBase(db_test_mixin.DatabaseSetupMixin):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None

  def CreateBlobStore(self):
    return self.CreateDatabase()
