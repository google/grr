#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest
from grr_response_core.lib import flags
from grr_response_server import db_test_mixin
from grr_response_server.databases import mem
from grr.test_lib import test_lib

FLAGS = flags.FLAGS


class MemoryDBTest(db_test_mixin.DatabaseTestMixin, absltest.TestCase):

  def CreateDatabase(self):
    return mem.InMemoryDB(), None


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
