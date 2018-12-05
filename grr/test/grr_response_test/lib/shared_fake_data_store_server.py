#!/usr/bin/env python
"""Datastore server for self contained tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Importing worker main entry point to make sure shared fake data store server
# knows about all the RDFValue types that worker knows about.
# pylint: disable=unused-import,g-bad-import-order
from grr_response_server.bin import worker
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import flags
from grr_response_test.lib import shared_fake_data_store


def main(argv):
  del argv  # Unused.

  config_lib.ParseConfigCommandLine()

  port = config.CONFIG["SharedFakeDataStore.port"]
  server = shared_fake_data_store.SharedFakeDataStoreServer(port)
  server.serve_forever()


if __name__ == "__main__":
  flags.StartMain(main)
