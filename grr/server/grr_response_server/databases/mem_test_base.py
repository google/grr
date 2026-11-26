#!/usr/bin/env python
"""Base class for all memory database tests."""

from __future__ import annotations

from collections.abc import Callable

from grr_response_server import blob_store
from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mem


class MemoryDBTestBase(db_test_mixin.DatabaseSetupMixin):

  def CreateDatabase(self) -> tuple[mem.InMemoryDB, None]:
    return mem.InMemoryDB(), None

  def CreateBlobStore(
      self,
  ) -> tuple[blob_store.BlobStore, Callable[[], None] | None]:
    return self.CreateDatabase()
