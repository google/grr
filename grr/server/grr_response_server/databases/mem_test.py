#!/usr/bin/env python
import unittest
from grr.lib import flags
from grr.server.grr_response_server import db_test_mixin
from grr.server.grr_response_server.databases import mem
from grr.test_lib import test_lib

FLAGS = flags.FLAGS


class MemoryDBTest(db_test_mixin.DatabaseTestMixin, unittest.TestCase):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
