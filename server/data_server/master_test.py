#!/usr/bin/env python
"""Test the master data server abstraction."""



from grr.lib import config_lib
from grr.lib import flags
from grr.lib import test_lib

from grr.server.data_server import constants
from grr.server.data_server import master
from grr.server.data_server import utils


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


class MasterTest(test_lib.GRRBaseTest):
  """Tests the master server code."""

  def setUp(self):
    super(MasterTest, self).setUp()
    self.mock_service = MockDataStoreService()
    server_list = ["http://127.0.0.1:7000", "http://127.0.0.1:7001",
                   "http://127.0.0.1:7002", "http://127.0.0.1:7003"]
    config_lib.CONFIG.Set("Dataserver.server_list", server_list)

  def testInvalidMaster(self):
    """Attempt to create an invalid master."""
    self.assertRaises(
        master.DataMasterError, master.DataMaster,
        7001, self.mock_service)

  def testRegister(self):
    """Create master and register other servers."""
    m = master.DataMaster(7000, self.mock_service)
    self.assertNotEqual(m, None)
    self.assertFalse(m.AllRegistered())

    server1 = m.RegisterServer("127.0.0.1", 7001)
    self.assertNotEqual(server1, None)
    self.assertEqual(server1.Address(), "127.0.0.1")
    self.assertEqual(server1.Port(), 7001)
    self.assertEqual(server1.Index(), 1)
    self.assertFalse(m.AllRegistered())
    server2 = m.RegisterServer("127.0.0.1", 7002)
    self.assertNotEqual(server2, None)
    self.assertEqual(server2.Address(), "127.0.0.1")
    self.assertEqual(server2.Port(), 7002)
    self.assertEqual(server2.Index(), 2)
    self.assertFalse(m.AllRegistered())
    server3 = m.RegisterServer("127.0.0.1", 7003)
    self.assertNotEqual(server3, None)
    self.assertEqual(server3.Address(), "127.0.0.1")
    self.assertEqual(server3.Port(), 7003)
    self.assertEqual(server3.Index(), 3)
    self.assertTrue(m.AllRegistered())

    # Try to register something that does not exist.
    self.assertFalse(m.RegisterServer("127.0.0.1", 7004))

    # Deregister a server.
    m.DeregisterServer(server1)
    self.assertFalse(m.AllRegistered())

    # Register again.
    m.RegisterServer(server1.Address(), server1.Port())
    self.assertTrue(m.AllRegistered())

  def testMapping(self):
    """Check that the mapping is valid."""
    m = master.DataMaster(7000, self.mock_service)
    self.assertNotEqual(m, None)
    server1 = m.RegisterServer("127.0.0.1", 7001)
    server2 = m.RegisterServer("127.0.0.1", 7002)
    server3 = m.RegisterServer("127.0.0.1", 7003)
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
    self.assertEqual(utils._FindServerInMapping(mapping,
                                                constants.MAX_RANGE/4), 1)
    self.assertEqual(utils._FindServerInMapping(mapping,
                                                constants.MAX_RANGE/4 + 1), 1)
    self.assertEqual(utils._FindServerInMapping(mapping,
                                                constants.MAX_RANGE/2), 2)
    half_fifth = constants.MAX_RANGE/2 + constants.MAX_RANGE/5
    self.assertEqual(utils._FindServerInMapping(mapping, half_fifth), 2)
    self.assertEqual(utils._FindServerInMapping(mapping,
                                                constants.MAX_RANGE/4 * 3), 3)
    self.assertEqual(utils._FindServerInMapping(mapping,
                                                constants.MAX_RANGE), 3)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
