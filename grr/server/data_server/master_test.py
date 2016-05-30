#!/usr/bin/env python
"""Test the master data server abstraction."""



# pylint: disable=g-import-not-at-top
try:
  from urllib3 import connectionpool
except ImportError:
  # Urllib3 also comes as part of requests, try to fallback.
  from requests.packages.urllib3 import connectionpool

from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils as libutils
from grr.lib.rdfvalues import data_server as rdf_data_server

from grr.server.data_server import auth
from grr.server.data_server import constants
from grr.server.data_server import data_server
from grr.server.data_server import errors
from grr.server.data_server import master
from grr.server.data_server import utils

# pylint: enable=g-import-not-at-top


class MockDataStoreService(object):
  """Implements a mock DataStoreService."""

  def __init__(self):
    self.mapping = None

  def LoadServerMapping(self):
    return self.mapping

  def SaveServerMapping(self, mapping, create_pathing=False):
    _ = create_pathing
    self.mapping = mapping

  def GetComponentInformation(self):
    return 0, 0

  def Size(self):
    return 0


class MockResponse(object):

  def __init__(self, status):
    self.status = status
    self.data = ""


def GetMockHTTPConnectionPoolClass(responses_class_value):

  class MockHTTPConnectionPool(object):

    responses = responses_class_value
    requests = []

    def __init__(self, addr, port=0, maxsize=0):
      _ = addr, port, maxsize

    # pylint: disable=invalid-name
    def urlopen(self, method, url, body=None, headers=None):
      _ = method, url, headers
      self.__class__.requests.append({"method": method,
                                      "url": url,
                                      "body": body})

      return self.responses.pop(0)
    # pylint: enable=invalid-name

  return MockHTTPConnectionPool


class MasterTest(test_lib.GRRBaseTest):
  """Tests the master server code."""

  def setUp(self):
    super(MasterTest, self).setUp()
    self.mock_service = MockDataStoreService()

    self.host = "127.0.0.1"

    # Ports 7000+ are typically used for GRR data servers, so they are tested
    # here for illustration and documentation purposes.
    # We're also testing port 3000 as it is unique in that it encodes
    # differently to binary. pack_int(3000) returns a byte sequence which is
    # invalid utf8 and can cause problems in certain code. This has caused
    # bugs in the past, so this constitues a regression test.

    self.ports = [7000, 7001, 7002, 3000]

    server_list = []
    for port in self.ports:
      server_list.append("http://%s:%i" % (self.host, port))

    self.server_list_overrider = test_lib.ConfigOverrider({
        "Dataserver.server_list": server_list
    })
    self.server_list_overrider.Start()

  def tearDown(self):
    super(MasterTest, self).tearDown()
    self.server_list_overrider.Stop()

  def testInvalidMaster(self):
    """Attempt to create an invalid master."""
    self.assertRaises(master.DataMasterError, master.DataMaster, 7001,
                      self.mock_service)

  def testRegister(self):
    """Create master and register other servers."""
    m = master.DataMaster(self.ports[0], self.mock_service)
    self.assertNotEqual(m, None)
    self.assertFalse(m.AllRegistered())

    servers = [None]

    for (i, port) in enumerate(self.ports):
      if i == 0:
        # Skip master server.
        continue
      self.assertFalse(m.AllRegistered())
      server = m.RegisterServer(self.host, port)
      servers.append(server)
      self.assertNotEqual(server, None)
      self.assertEqual(server.Address(), self.host)
      self.assertEqual(server.Port(), port)
      self.assertEqual(server.Index(), i)

    self.assertTrue(m.AllRegistered())

    # Try to register something that does not exist.
    self.assertFalse(m.RegisterServer(self.host, 7004))

    # Deregister a server.
    m.DeregisterServer(servers[1])
    self.assertFalse(m.AllRegistered())

    # Register again.
    m.RegisterServer(servers[1].Address(), servers[1].Port())
    self.assertTrue(m.AllRegistered())

    for port in self.ports:
      for response_sequence in [[constants.RESPONSE_OK,
                                 constants.RESPONSE_SERVER_NOT_AUTHORIZED],
                                [constants.RESPONSE_OK,
                                 constants.RESPONSE_SERVER_NOT_ALLOWED],
                                [constants.RESPONSE_OK,
                                 constants.RESPONSE_NOT_MASTER_SERVER]]:

        response_mocks = []
        for response_status in response_sequence:
          response_mocks.append(MockResponse(response_status))

        pool_class = GetMockHTTPConnectionPoolClass(response_mocks)

        with libutils.Stubber(connectionpool, "HTTPConnectionPool", pool_class):
          m = data_server.StandardDataServer(port,
                                             data_server.DataServerHandler)
          m.handler_cls.NONCE_STORE = auth.NonceStore()

          self.assertRaises(errors.DataServerError, m._DoRegister)

          # Ensure two requests have been made.
          self.assertEqual(len(pool_class.requests), 2)

          # Ensure the register body is non-empty.
          self.assertTrue(pool_class.requests[1]["body"])

          # Ensure that the register body is a valid rdfvalue.
          rdf_data_server.DataStoreRegistrationRequest(pool_class.requests[1][
              "body"])

          # Ensure the requests are POST requests.
          self.assertEqual(pool_class.requests[0]["method"], "POST")
          self.assertEqual(pool_class.requests[1]["method"], "POST")

          # Ensure the correct URLs are hit according to the API.
          self.assertEqual(pool_class.requests[0]["url"], "/server/handshake")
          self.assertEqual(pool_class.requests[1]["url"], "/server/register")

  def testMapping(self):
    """Check that the mapping is valid."""
    m = master.DataMaster(7000, self.mock_service)
    self.assertNotEqual(m, None)
    server1 = m.RegisterServer("127.0.0.1", 7001)
    server2 = m.RegisterServer("127.0.0.1", 7002)
    server3 = m.RegisterServer("127.0.0.1", 3000)
    self.assertTrue(m.AllRegistered())
    mapping = m.LoadMapping()
    self.assertNotEqual(mapping, None)
    self.assertEqual(mapping.num_servers, 4)
    self.assertEqual(len(mapping.servers), 4)

    # Check server information.
    self.assertEqual(mapping.servers[0].address, "127.0.0.1")
    self.assertEqual(mapping.servers[0].port, 7000)
    self.assertEqual(mapping.servers[0].index, 0)
    for idx, server in [(1, server1), (2, server2), (3, server3)]:
      self.assertEqual(mapping.servers[idx].address, server.Address())
      self.assertEqual(mapping.servers[idx].port, server.Port())
      self.assertEqual(mapping.servers[idx].index, server.Index())
      self.assertTrue(server.IsRegistered())

    # Check intervals.
    interval1 = server1.Interval()
    interval2 = server2.Interval()
    interval3 = server3.Interval()

    self.assertEqual(interval1.end, interval2.start)
    self.assertEqual(interval2.end, interval3.start)
    self.assertEqual(interval1.end - interval1.end,
                     interval2.end - interval2.end)
    self.assertEqual(interval1.end - interval1.end,
                     interval3.end - interval3.end)
    self.assertEqual(interval3.end, constants.MAX_RANGE)

    # Check that mapping to a server works.
    self.assertEqual(utils._FindServerInMapping(mapping, 0x0), 0)
    self.assertEqual(
        utils._FindServerInMapping(mapping, constants.MAX_RANGE / 4), 1)
    self.assertEqual(
        utils._FindServerInMapping(mapping, constants.MAX_RANGE / 4 + 1), 1)
    self.assertEqual(
        utils._FindServerInMapping(mapping, constants.MAX_RANGE / 2), 2)
    half_fifth = constants.MAX_RANGE / 2 + constants.MAX_RANGE / 5
    self.assertEqual(utils._FindServerInMapping(mapping, half_fifth), 2)
    self.assertEqual(
        utils._FindServerInMapping(mapping, constants.MAX_RANGE / 4 * 3), 3)
    self.assertEqual(
        utils._FindServerInMapping(mapping, constants.MAX_RANGE), 3)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
