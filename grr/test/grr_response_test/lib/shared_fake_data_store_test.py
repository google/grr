#!/usr/bin/env python
"""Tests the fake data store - in memory implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import errno
import socket
import threading
import time

from future.builtins import range
import portpicker

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_server import data_store
from grr_response_server import data_store_test
from grr_response_test.lib import shared_fake_data_store
from grr.test_lib import test_lib


class SharedFakeDataStoreTestMixin(object):

  @classmethod
  def _SetupServer(cls):
    for _ in range(5):
      try:
        port = portpicker.pick_unused_port()
        cls.server = shared_fake_data_store.SharedFakeDataStoreServer(port)
        config.CONFIG.Set("SharedFakeDataStore.port", port)
        return
      except socket.error as e:
        if e.errno != errno.EADDRINUSE:
          raise

    raise RuntimeError("Unable to find an unused port after 5 tries.")

  @classmethod
  def setUpClass(cls):
    super(SharedFakeDataStoreTestMixin, cls).setUpClass()

    cls._SetupServer()

    cls.server_thread = threading.Thread(
        name="SharedFDSTestThread", target=cls.server.serve_forever)
    cls.server_thread.daemon = True
    cls.server_thread.start()
    # Give the server thread a chance to start up. If we don't sleep for at
    # least a tiny amount here, the server thread might not be able to get to
    # run at all before we send the first request.
    time.sleep(0.01)

    cls.prev_data_store = data_store.DB
    data_store.DB = shared_fake_data_store.SharedFakeDataStore()

  @classmethod
  def tearDownClass(cls):
    super(SharedFakeDataStoreTestMixin, cls).tearDownClass()
    cls.server.shutdown()
    cls.server_thread.join()
    data_store.DB = cls.prev_data_store

  def testCorrectDataStore(self):
    self.assertIsInstance(data_store.DB,
                          shared_fake_data_store.SharedFakeDataStore)


class SharedFakeDataStoreTest(data_store_test.DataStoreTestMixin,
                              SharedFakeDataStoreTestMixin,
                              test_lib.GRRBaseTest):
  """Test the fake shared data store."""

  def testApi(self):
    """The fake datastore doesn't strictly conform to the api but this is ok."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
