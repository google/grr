#!/usr/bin/env python
import unittest
from grr.lib import flags
from grr.server import db_test
from grr.server.databases import mem
from grr.test_lib import test_lib

FLAGS = flags.FLAGS


class MemoryDBTest(db_test.DatabaseTestMixin, unittest.TestCase):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
