#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server import db_test_mixin
from grr_response_server.databases import mem
from grr.test_lib import test_lib


class MemoryDBTestBase(db_test_mixin.DatabaseSetupMixin):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None

  def CreateBlobStore(self):
    return self.CreateDatabase()


class MemoryDBTest(db_test_mixin.DatabaseTestMixin, MemoryDBTestBase,
                   absltest.TestCase):
  pass


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
