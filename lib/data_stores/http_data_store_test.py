#!/usr/bin/env python
"""Tests the HTTP remote data store abstraction."""


import httplib
import socket
import threading



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.data_stores import http_data_store
from grr.lib.data_stores import sqlite_data_store

from grr.server.data_server import data_server


class StoppableHTTPServer(data_server.ThreadedHTTPServer):
  """HTTP server that can be stopped."""

  STOP = False

  def serve_forever(self):
    self.socket.settimeout(1)
    while not self.STOP:
      self.handle_request()
    self.socket.shutdown(socket.SHUT_RDWR)
    self.socket.close()


class MockRequestHandler(data_server.DataServerHandler):
  """Mock request handler that can stop a server."""

  def do_POST(self):  # pylint: disable=invalid-name
    if self.path == "/exit":
      StoppableHTTPServer.STOP = True
      return self._EmptyResponse(200)
    else:
      return super(MockRequestHandler, self).do_POST()


STARTED_SERVER = None
HTTP_DB = None
PORT = None


def _StartServer(temp_dir):
  global HTTP_DB
  global STARTED_SERVER
  HTTP_DB = sqlite_data_store.SqliteDataStore(temp_dir)
  STARTED_SERVER = threading.Thread(
      target=data_server.Start,
      args=(HTTP_DB, PORT, True, StoppableHTTPServer, MockRequestHandler))
  STARTED_SERVER.start()


def _CloseServer():
  # Send an exit request.
  conn = httplib.HTTPConnection("127.0.0.1", PORT)
  conn.request("POST", "/exit")
  conn.getresponse()


def _SetConfig(path):
  config_lib.CONFIG.Set("Dataserver.server_list",
                        ["http://127.0.0.1:" + str(PORT)])
  config_lib.CONFIG.Set("Dataserver.server_username", "root")
  config_lib.CONFIG.Set("Dataserver.server_password", "root")
  config_lib.CONFIG.Set("Dataserver.client_credentials", ["user:user:rw"])
  config_lib.CONFIG.Set("HTTPDataStore.username", "user")
  config_lib.CONFIG.Set("HTTPDataStore.password", "user")
  config_lib.CONFIG.Set("Datastore.location", path)


def tearDownModule():
  _CloseServer()


class HTTPDataStoreMixin(object):

  def InitDatastore(self):
    global PORT
    if not PORT:
      PORT = 7000
    _SetConfig(self.temp_dir)
    if not STARTED_SERVER:
      _StartServer(self.temp_dir)
    else:
      # Change location of the database.
      HTTP_DB.ChangeLocation(self.temp_dir)
    try:
      data_store.DB = http_data_store.HTTPDataStore()
    except http_data_store.HTTPDataStoreError as e:
      data_store.DB = None
      _CloseServer()
      self.fail("Error: %s" % str(e))

    self.old_security_manager = None

  def _InstallACLChecks(self, forbidden_access):
    if self.old_security_manager:
      raise RuntimeError("Seems like _InstallACLChecks was called twice in one "
                         "test")

    # HTTP_DB doesn't get recreated every time this test runs. So make sure
    # that we can restore previous security manager later.
    self.old_security_manager = HTTP_DB.security_manager

    # We have to install tuned MockSecurityManager not on data_store.DB, which
    # is a HttpDataStore, but on HTTP_DB which is an SqliteDataStore that
    # eventuall gets queries from HttpDataStore.
    HTTP_DB.security_manager = test_lib.MockSecurityManager(
        forbidden_datastore_access=forbidden_access)

  def DestroyDatastore(self):
    if self.old_security_manager:
      HTTP_DB.security_manager = self.old_security_manager

    # Close connections with the server.
    if data_store.DB:
      data_store.DB.CloseConnections()


class HTTPDataStoreTest(HTTPDataStoreMixin,
                        data_store_test._DataStoreTest):
  """Test the remote data store."""

  def testRDFDatetimeTimestamps(self):
    # Disabled for now.
    pass


class HTTPDataStoreBenchmarks(HTTPDataStoreMixin,
                              data_store_test.DataStoreBenchmarks):
  """Benchmark the HTTP remote data store abstraction."""


class HTTPDataStoreCSVBenchmarks(HTTPDataStoreMixin,
                                 data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the HTTP remote data store."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
