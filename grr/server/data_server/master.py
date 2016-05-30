#!/usr/bin/env python
"""Data master specific classes."""


import socket
import threading
import urlparse


# pylint: disable=g-import-not-at-top
try:
  import urllib3
  from urllib3 import connectionpool
except ImportError:
  # Urllib3 also comes as part of requests, try to fallback.
  from requests.packages import urllib3
  from requests.packages.urllib3 import connectionpool

import logging

from grr.lib import config_lib
from grr.lib import utils
from grr.lib.rdfvalues import data_server as rdf_data_server

from grr.server.data_server import constants
from grr.server.data_server import rebalance
from grr.server.data_server import utils as sutils

# pylint: enable=g-import-not-at-top


class DataMasterError(Exception):
  """Raised when some critical error happens in the data master."""
  pass


class DataServer(object):
  """DataServer objects for each data server."""

  def __init__(self, location, index):
    # Parse location.
    loc = urlparse.urlparse(location, scheme="http")
    offline = rdf_data_server.DataServerState.Status.OFFLINE
    state = rdf_data_server.DataServerState(size=0, load=0, status=offline)
    self.server_info = rdf_data_server.DataServerInformation(
        index=index,
        address=loc.hostname,
        port=loc.port,
        state=state)
    self.registered = False
    self.removed = False
    logging.info("Configured DataServer on %s:%d", self.Address(), self.Port())

  def SetInitialInterval(self, num_servers):
    self.server_info.interval = sutils.CreateStartInterval(self.Index(),
                                                           num_servers)

  def IsRegistered(self):
    return self.registered

  def Matches(self, addr, port):
    """Tests if add and port correspond to self.Address() / self.Port()."""
    if isinstance(addr, list):
      if self.Address() not in addr:
        return False
    else:
      # Handle hostnames and IPs.
      # TODO(user): Make this work for non IPv4.
      myip = socket.getaddrinfo(self.Address(), self.Port(), socket.AF_INET, 0,
                                socket.IPPROTO_TCP)[0][4][0]
      other_ip = socket.getaddrinfo(addr, port, socket.AF_INET, 0,
                                    socket.IPPROTO_TCP)[0][4][0]
      if myip != other_ip:
        return False
    return self.Port() == port

  def Register(self):
    """Once the server is registered, it is allowed to use the database."""
    self.registered = True

  def Deregister(self):
    self.registered = False

  def Port(self):
    return self.server_info.port

  def Address(self):
    return self.server_info.address

  def Index(self):
    return self.server_info.index

  def SetIndex(self, newindex):
    self.server_info.index = newindex

  def Size(self):
    return self.server_info.state.size

  def Load(self):
    return self.server_info.state.load

  def Interval(self):
    return self.server_info.interval

  def SetInterval(self, start, end):
    self.server_info.interval.start = start
    self.server_info.interval.end = end

  def GetInfo(self):
    return self.server_info

  def UpdateState(self, newstate):
    """Update state of server."""
    self.server_info.state = newstate

  def Remove(self):
    self.removed = True

  def WasRemoved(self):
    return self.removed


class DataMaster(object):
  """DataMaster information."""

  def __init__(self, myport, service):
    self.service = service
    stores = config_lib.CONFIG["Dataserver.server_list"]
    if not stores:
      logging.error("Dataserver.server_list is empty: no data servers will"
                    " be available")
      raise DataMasterError("Dataserver.server_list is empty")
    self.servers = [DataServer(loc, idx) for idx, loc in enumerate(stores)]
    self.registered_count = 0
    # Load server mapping.
    self.mapping = self.service.LoadServerMapping()
    if not self.mapping:
      # Bootstrap mapping.
      # Each server information is linked to its corresponding object.
      # Updating the data server object will reflect immediately on
      # the mapping.
      for server in self.servers:
        server.SetInitialInterval(len(self.servers))
      servers_info = [server.server_info for server in self.servers]
      self.mapping = rdf_data_server.DataServerMapping(
          version=0,
          num_servers=len(self.servers),
          servers=servers_info)
      self.service.SaveServerMapping(self.mapping, create_pathing=True)
    else:
      # Check mapping and configuration matching.
      if len(self.mapping.servers) != len(self.servers):
        raise DataMasterError("Server mapping does not correspond "
                              "to the configuration.")
      for server in self.servers:
        self._EnsureServerInMapping(server)
    # Create locks.
    self.server_lock = threading.Lock()
    # Register the master.
    self.myself = self.servers[0]
    if self.myself.Port() == myport:
      self._DoRegisterServer(self.myself)
    else:
      logging.warning("First server in Dataserver.server_list is not the "
                      "master. Found port '%i' but my port is '%i'. If you"
                      " really are running master, you may want to specify"
                      " flag --port %i.", self.myself.Port(), myport, myport)
      raise DataMasterError("First server in Dataserver.server_list must be "
                            "the master.")
    # Start database measuring thread.
    sleep = config_lib.CONFIG["Dataserver.stats_frequency"]
    self.periodic_thread = utils.InterruptableThread(
        target=self._PeriodicThread,
        sleep_time=sleep)
    self.periodic_thread.start()
    # Holds current rebalance operation.
    self.rebalance = None
    self.rebalance_pool = []

  def LoadMapping(self):
    return self.mapping

  def _PeriodicThread(self):
    """Periodically update our state and store the mappings."""
    ok = rdf_data_server.DataServerState.Status.AVAILABLE
    num_components, avg_component = self.service.GetComponentInformation()
    state = rdf_data_server.DataServerState(size=self.service.Size(),
                                            load=0,
                                            status=ok,
                                            num_components=num_components,
                                            avg_component=avg_component)
    self.myself.UpdateState(state)
    self.service.SaveServerMapping(self.mapping)

  def _EnsureServerInMapping(self, server):
    """Ensure that the data server exists on the mapping."""
    index = server.Index()
    server_info = self.mapping.servers[index]
    if server_info.address != server.Address():
      return False
    if server_info.port != server.Port():
      return False
    # Change underlying server information.
    server.server_info = server_info

  def RegisterServer(self, addr, port):
    """Register incoming data server. Return server object."""
    for server in self.servers:
      if server == self.myself:
        continue
      if server.Matches(addr, port):
        with self.server_lock:
          if server.IsRegistered():
            return None
          else:
            self._DoRegisterServer(server)
            return server
    return None

  def HasServer(self, addr, port):
    """Checks if a given server is already in the set."""
    for server in self.servers:
      if server.Matches(addr, port):
        return server
    return None

  def _DoRegisterServer(self, server):
    self.registered_count += 1
    server.Register()
    logging.info("Registered server %s:%d", server.Address(), server.Port())
    if self.AllRegistered():
      logging.info("All data servers have registered!")

  def DeregisterServer(self, server):
    """Deregister a data server."""
    with self.server_lock:
      server.Deregister()
      self.registered_count -= 1

  def AllRegistered(self):
    """Check if all servers have registered."""
    return self.registered_count == len(self.servers)

  def Stop(self):
    self.service.SaveServerMapping(self.mapping)
    self.periodic_thread.Stop()

  def SetRebalancing(self, reb):
    """Sets a new rebalance operation and starts communication with servers."""
    self.rebalance = reb
    self.rebalance_pool = []
    try:
      for serv in self.servers:
        pool = connectionpool.HTTPConnectionPool(serv.Address(),
                                                 port=serv.Port())
        self.rebalance_pool.append(pool)
    except urllib3.exceptions.MaxRetryError:
      self.CancelRebalancing()
      return False
    return True

  def CancelRebalancing(self):
    self.rebalance = None
    for pool in self.rebalance_pool:
      pool.close()
    self.rebalance_pool = []

  def IsRebalancing(self):
    return self.rebalance

  def AddServer(self, addr, port):
    """Add new server to the group."""
    server = DataServer("http://%s:%d" % (addr, port), len(self.servers))
    self.servers.append(server)
    server.SetInterval(constants.MAX_RANGE, constants.MAX_RANGE)
    self.mapping.servers.Append(server.GetInfo())
    self.mapping.num_servers += 1
    # At this point, the new server is now part of the group.
    return server

  def RemoveServer(self, removed_server):
    """Remove a server. Returns None if server interval is not empty."""
    interval = removed_server.Interval()
    # Interval range must be 0.
    if interval.start != interval.end:
      return None
    # Update ids of other servers.
    newserverlist = []
    for serv in self.servers:
      if serv == removed_server:
        continue
      if serv.Index() > removed_server.Index():
        serv.SetIndex(serv.Index() - 1)
      newserverlist.append(serv.GetInfo())
    # Change list of servers.
    self.mapping.servers = newserverlist
    self.mapping.num_servers -= 1
    self.servers.pop(removed_server.Index())
    self.DeregisterServer(removed_server)
    removed_server.Remove()
    return removed_server

  def SyncMapping(self, skip=None):
    """Syncs mapping with other servers."""
    pools = []
    try:
      # Update my state.
      self._PeriodicThread()
      for serv in self.servers[1:]:
        if skip and serv in skip:
          continue
        pool = connectionpool.HTTPConnectionPool(serv.Address(),
                                                 port=serv.Port())
        pools.append((serv, pool))
      body = self.mapping.SerializeToString()
      headers = {"Content-Length": len(body)}
      for serv, pool in pools:
        res = pool.urlopen("POST", "/servers/sync", headers=headers, body=body)
        if res.status != constants.RESPONSE_OK:
          logging.warning("Could not sync with server %s:%d", serv.Address(),
                          serv.Port())
          return False
        state = rdf_data_server.DataServerState()
        state.ParseFromString(res.data)
        serv.UpdateState(state)
    except urllib3.exceptions.MaxRetryError:
      return False
    finally:
      for _, pool in pools:
        pool.close()
    return True

  def FetchRebalanceInformation(self):
    """Asks data servers for number of changes for rebalancing."""
    body = self.rebalance.SerializeToString()
    size = len(body)
    headers = {"Content-Length": size}
    for pool in self.rebalance_pool:
      try:
        res = pool.urlopen("POST",
                           "/rebalance/statistics",
                           headers=headers,
                           body=body)
        if res.status != constants.RESPONSE_OK:
          self.CancelRebalancing()
          return False
        reb = rdf_data_server.DataServerRebalance()
        reb.ParseFromString(res.data)
        ls = list(reb.moving)
        if ls:
          logging.warning("Moving %d", ls[0])
          self.rebalance.moving.Append(ls[0])
        else:
          self.CancelRebalancing()
          return False
      except urllib3.exceptions.MaxRetryError:
        self.CancelRebalancing()
        return False
    return True

  def CopyRebalanceFiles(self):
    """Tell servers to copy files to the corresponding servers."""
    body = self.rebalance.SerializeToString()
    size = len(body)
    headers = {"Content-Length": size}
    for pool in self.rebalance_pool:
      try:
        res = pool.urlopen("POST",
                           "/rebalance/copy",
                           headers=headers,
                           body=body)
        if res.status != constants.RESPONSE_OK:
          self.CancelRebalancing()
          return False
      except urllib3.exceptions.MaxRetryError:
        self.CancelRebalancing()
        return False
    return True

  def RebalanceCommit(self):
    """Tell servers to commit rebalance changes."""
    # Save rebalance information to a file, so we can recover later.
    rebalance.SaveCommitInformation(self.rebalance)
    body = self.rebalance.SerializeToString()
    size = len(body)
    headers = {"Content-Length": size}
    for i, pool in enumerate(self.rebalance_pool):
      try:
        res = pool.urlopen("POST",
                           "/rebalance/perform",
                           headers=headers,
                           body=body)
        if res.status != constants.RESPONSE_OK:
          logging.error("Server %d failed to perform transaction %s", i,
                        self.rebalance.id)
          self.CancelRebalancing()
          return None
        stat = rdf_data_server.DataServerState()
        stat.ParseFromString(res.data)
        data_server = self.servers[i]
        data_server.UpdateState(stat)
      except urllib3.exceptions.MaxRetryError:
        self.CancelRebalancing()
        return None
    # Update server intervals.
    mapping = self.rebalance.mapping
    for i, serv in enumerate(list(self.mapping.servers)):
      serv.interval = mapping.servers[i].interval
    self.rebalance.mapping = self.mapping
    self.service.SaveServerMapping(self.mapping)
    # We can finally delete the temporary file, since we have succeeded.
    rebalance.DeleteCommitInformation(self.rebalance)
    rebalance.RemoveDirectory(self.rebalance)
    self.CancelRebalancing()
    return self.mapping
