#!/usr/bin/env python
"""Manage data servers."""


import atexit
import os
import readline
import time
import urlparse

import urllib3
from urllib3 import connectionpool

# pylint: disable=unused-import,g-bad-import-order
from grr.client import client_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib import utils

from grr.lib.rdfvalues import data_server as rdf_data_server

from grr.server.data_server import constants
from grr.server.data_server import errors
from grr.server.data_server import utils as sutils


class Manager(object):
  """Manage a data server group using a connection to the master."""

  def __init__(self):
    servers = config_lib.CONFIG["Dataserver.server_list"]
    if not servers:
      raise errors.DataServerError("List of data servers not available.")
    master_location = servers[0]
    loc = urlparse.urlparse(master_location, scheme="http")
    self.addr = loc.hostname
    self.port = int(loc.port)
    self.pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
    self.history_path = os.path.expanduser("~/.grr-data-store-manager")
    if os.path.exists(self.history_path):
      readline.read_history_file(self.history_path)
    self.periodic_thread = None
    self.mapping = None
    self.mapping_time = 0

  def Start(self):
    self._PeriodicThread()
    self.periodic_thread = utils.InterruptableThread(
        target=self._PeriodicThread, sleep_time=10)
    self.periodic_thread.start()
    return True

  def _PeriodicThread(self):
    body = ""
    headers = {"Content-Length": len(body)}
    try:
      res = self.pool.urlopen("POST", "/manage", headers=headers, body=body)
      if res.status != constants.RESPONSE_OK:
        return False
      self.mapping = rdf_data_server.DataServerMapping(res.data)
      self.mapping_time = time.time()
    except urllib3.exceptions.MaxRetryError:
      pass

  def SaveHistory(self):
    readline.write_history_file(self.history_path)

  def _ShowServers(self):
    if not self.mapping:
      print "Server information not available"
      return
    last = time.asctime(time.localtime(self.mapping_time))
    print "Last refresh:", last
    for i, serv in enumerate(list(self.mapping.servers)):
      addr = serv.address
      port = serv.port
      size = serv.state.size
      load = serv.state.load
      ncomp = serv.state.num_components
      avgcomp = serv.state.avg_component
      print "Server %d %s:%d (Size: %dKB, Load: %d)" % (i, addr, port,
                                                        size / 1024, load)
      print "\t\t%d components %dKB average size" % (ncomp, avgcomp / 1024)

  def _ShowRanges(self):
    if not self.mapping:
      print "Server information not available"
      return
    self._ShowRange(self.mapping)

  def _ShowRange(self, mapping):
    for i, serv in enumerate(list(mapping.servers)):
      addr = serv.address
      port = serv.port
      start = serv.interval.start
      end = serv.interval.end
      perc = float(end - start) / float(2**64)
      perc *= 100
      print "Server %d %s:%d %d%% [%s, %s[" % (i, addr, port, perc,
                                               str(start).zfill(20),
                                               str(end).zfill(20))

  def _ComputeMappingSize(self, mapping):
    totalsize = 0
    servers = list(mapping.servers)
    for serv in servers:
      totalsize += serv.state.size
    return totalsize

  def _ComputeMappingFromPercentages(self, mapping, newperc):
    """Builds a new mapping based on the new server range percentages."""
    newstart = 0
    n_servers = self.mapping.num_servers
    servers = list(mapping.servers)
    new_mapping = rdf_data_server.DataServerMapping(
        version=self.mapping.version + 1,
        num_servers=n_servers,
        pathing=self.mapping.pathing)
    for i, perc in enumerate(newperc):
      quant = int(perc * constants.MAX_RANGE)
      interval = rdf_data_server.DataServerInterval(start=newstart)
      end = newstart + quant
      if i == len(newperc) - 1:
        end = constants.MAX_RANGE
      interval.end = end
      old_server = servers[i]
      newstart = end
      new_mapping.servers.Append(index=old_server.index,
                                 address=old_server.address,
                                 port=old_server.port,
                                 state=old_server.state,
                                 interval=interval)
    return new_mapping

  def _Rebalance(self):
    """Starts the rebalance process."""
    if not self.mapping:
      print "Server information not available"
      return
    # Compute total size of database.
    servers = list(self.mapping.servers)
    num_servers = len(servers)
    target = 1.0 / float(num_servers)
    perc = [target] * num_servers
    new_mapping = self._ComputeMappingFromPercentages(self.mapping, perc)
    print "The new ranges will be:"
    self._ShowRange(new_mapping)
    print
    self._DoRebalance(new_mapping)

  def _DoRebalance(self, new_mapping):
    """Performs a new rebalancing operation with the master server."""
    print "Contacting master server to start re-sharding...",
    # Send mapping information to master.
    pool = None
    try:
      pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return
    body = new_mapping.SerializeToString()
    headers = {"Content-Length": len(body)}
    res = None
    try:
      res = pool.urlopen("POST",
                         "/rebalance/phase1",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to talk with master..."
      pool.close()
      return
    if res.status != constants.RESPONSE_OK:
      print "Re-sharding cannot be done!"
      return
    rebalance = rdf_data_server.DataServerRebalance(res.data)
    print "OK"
    print
    print "The following servers will need to move data:"
    for i, move in enumerate(list(rebalance.moving)):
      print "Server %d moves %dKB" % (i, move / 1024)
    answer = raw_input("Proceed with re-sharding? (y/n) ")
    if answer != "y":
      return
    body = rebalance.SerializeToString()
    headers = {"Content-Length": len(body)}
    try:
      res = pool.urlopen("POST",
                         "/rebalance/phase2",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact server for re-sharding."
      print "Make sure the data servers are up and try again."
      return
    if res.status != constants.RESPONSE_OK:
      print "Could not start copying files for re-sharding"
      print "Make sure the data servers are up and try again."
      return

    try:
      res = pool.urlopen("POST",
                         "/rebalance/commit",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print("Could not commit the re-sharding transaction with id "
            "%s") % rebalance.id
      print "Make sure the data servers are up and then run:"
      print "'recover %s' in order to re-run transaction" % rebalance.id
      return

    if res.status != constants.RESPONSE_OK:
      print "Could not commit the transaction %s" % rebalance.id
      print "Make sure the data servers are up and then run:"
      print "'recover %s' in order to re-run transaction" % rebalance.id
      return

    self.mapping = rdf_data_server.DataServerMapping(res.data)

    print "Rebalance with id %s fully performed." % rebalance.id

  def _Recover(self, transid):
    """Completes a rebalancing transaction that was unsuccessful."""
    print "Contacting master about transaction %s..." % transid,
    pool = None
    try:
      pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    print "OK."

    try:
      body = transid
      headers = {"Content-Length": len(body)}
      res = pool.urlopen("POST",
                         "/rebalance/recover",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    if res.status == constants.RESPONSE_TRANSACTION_NOT_FOUND:
      print "Transaction %s was not found" % transid
      return
    if res.status != constants.RESPONSE_OK:
      print "Potential data master error. Giving up..."
      return
    rebalance = rdf_data_server.DataServerRebalance(res.data)
    print "Got transaction object %s" % rebalance.id
    answer = raw_input("Proceed with the recover process? (y/n) ")
    if answer != "y":
      return

    body = rebalance.SerializeToString()
    headers = {"Content-Length": len(body)}

    try:
      res = pool.urlopen("POST",
                         "/rebalance/commit",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Could not commit re-sharding transaction with id %s" % rebalance.id
      print "Make sure the data servers are up and then run:"
      print "'recover %s' in order to re-run transaction" % rebalance.id
      return

    if res.status != constants.RESPONSE_OK:
      print "Could not commit transaction %s" % rebalance.id
      print "Make sure the data servers are up and then run:"
      print "'recover %s' in order to re-run transaction" % rebalance.id
      return

    self.mapping = rdf_data_server.DataServerMapping(res.data)
    print "Rebalance with id %s fully performed." % rebalance.id

  def _PackNewServer(self, addr, port):
    body = sutils.SIZE_PACKER.pack(len(addr))
    body += addr
    body += sutils.PORT_PACKER.pack(port)
    return body

  def _AddServer(self, addr, port):
    """Starts the process of adding a new server."""
    if port <= 0:
      print "Wrong port: %d" % port
      return
    pool = None
    try:
      pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    body = self._PackNewServer(addr, port)
    headers = {"Content-Length": len(body)}
    try:
      res = pool.urlopen("POST",
                         "/servers/add/check",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    if res.status == constants.RESPONSE_EQUAL_DATA_SERVER:
      print "Master server says there is already a similar server."
      print "Giving up..."
      return

    if res.status == constants.RESPONSE_DATA_SERVERS_UNREACHABLE:
      print "Master server says that some data servers are not running."
      print "Giving up..."
      return

    if res.status != constants.RESPONSE_OK:
      print "Master server error. Is the server running?"
      return

    print "Master server allows us to add server %s:%d" % (addr, port)

    answer = raw_input("Do you really want to add server //%s:%d? (y/n) " %
                       (addr, port))
    if answer != "y":
      return

    try:
      res = pool.urlopen("POST", "/servers/add", headers=headers, body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    if res.status == constants.RESPONSE_DATA_SERVERS_UNREACHABLE:
      print "Master server says that some data servers are not running."
      print "Giving up..."
      return

    if res.status == constants.RESPONSE_INCOMPLETE_SYNC:
      print("The master server has set up the new server, but the other "
            "servers may not know about it.")
      print "Please run 'sync' to fix the problem."
      print "Afterwards, you have to rebalance server data with the following:"
      self._CompleteAddServerHelp(addr, port)
      return

    if res.status != constants.RESPONSE_OK:
      print "Failed to contact master server."
      return

    print "============================================="
    print "Operation completed."
    print "To rebalance server data you have to do the following:"
    self._CompleteAddServerHelp(addr, port)

    # Update mapping.
    self.mapping = rdf_data_server.DataServerMapping(res.data)

  def _CompleteAddServerHelp(self, addr, port):
    print("\t1. Add '//%s:%d' to Dataserver.server_list in your configuration "
          "file.") % (addr, port)
    print "\t2. Start the new server at %s:%d" % (addr, port)
    print "\t3. Run 'rebalance'"

  def _Sync(self):
    """Forces the master to sync with the other data servers."""
    pool = None
    try:
      pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
      body = ""
      headers = {"Content-Length": len(body)}
      res = pool.urlopen("POST",
                         "/servers/sync-all",
                         headers=headers,
                         body=body)

      if res.status == constants.RESPONSE_INCOMPLETE_SYNC:
        print "Master has tried to contact all the data servers, but failed."
        return False

      if res.status == constants.RESPONSE_DATA_SERVERS_UNREACHABLE:
        print "Master server says that some data servers are not running."
        print "Giving up..."
        return False

      if res.status != constants.RESPONSE_OK:
        print "Unable to sync servers."
        return False
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return False
    print "Sync done."
    # Update mapping.
    self.mapping = rdf_data_server.DataServerMapping(res.data)
    return True

  def _FindServer(self, addr, port):
    for i, serv in enumerate(self.mapping.servers):
      if serv.address == addr and serv.port == port:
        return serv, i
    return None, None

  def _DropServer(self, addr, port):
    """Remove data stored in a server."""
    # Find server.
    server, index = self._FindServer(addr, port)
    if not server:
      print "Server not found."
      return
    servers = list(self.mapping.servers)
    num_servers = len(servers)
    # Simply set everyone else with 1/(N-1).
    target = 1.0 / float(num_servers - 1)
    newperc = [target] * num_servers
    # Our server gets 0.
    newperc[index] = 0
    # Create new mapping structure.
    new_mapping = self._ComputeMappingFromPercentages(self.mapping, newperc)
    print "The new ranges will be:"
    self._ShowRange(new_mapping)
    print

    # Now, we do a rebalancing.
    self._DoRebalance(new_mapping)

  def _RemServer(self, addr, port):
    """Remove server from group."""
    # Find server.
    server, _ = self._FindServer(addr, port)
    if not server:
      print "Server not found."
      return
    if server.interval.start != server.interval.end:
      print "Server has some data in it!"
      print "Giving up..."
      return

    pool = None
    try:
      pool = connectionpool.HTTPConnectionPool(self.addr, port=self.port)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    body = self._PackNewServer(addr, port)
    headers = {"Content-Length": len(body)}
    try:
      res = pool.urlopen("POST",
                         "/servers/rem/check",
                         headers=headers,
                         body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    if res.status == constants.RESPONSE_DATA_SERVER_NOT_FOUND:
      print "Master server says the data server does not exist."
      return

    if res.status == constants.RESPONSE_RANGE_NOT_EMPTY:
      print "Master server says the data server has still some data."
      print "Giving up..."
      return

    if res.status == constants.RESPONSE_DATA_SERVERS_UNREACHABLE:
      print "Master server says some data servers are not running."
      print "Giving up..."
      return

    if res.status != constants.RESPONSE_OK:
      print "Master server error. Is the server running?"
      return

    print "Master server allows us to remove server %s:%d" % (addr, port)

    answer = raw_input("Do you really want to remove server //%s:%d? (y/n) " %
                       (addr, port))
    if answer != "y":
      return

    try:
      res = pool.urlopen("POST", "/servers/rem", headers=headers, body=body)
    except urllib3.exceptions.MaxRetryError:
      print "Unable to contact master..."
      return

    if res.status == constants.RESPONSE_DATA_SERVERS_UNREACHABLE:
      print "Master server says that some data servers are not running."
      print "Giving up..."
      return

    if res.status == constants.RESPONSE_OK:
      # Update mapping.
      self.mapping = rdf_data_server.DataServerMapping(res.data)
      self._CompleteRemServerHelpComplete(addr, port)
      return

    if res.status == constants.RESPONSE_INCOMPLETE_SYNC:
      # We were unable to sync, so we try again:
      if self._Sync():
        self._CompleteRemServerHelpComplete(addr, port)
        return
      else:
        # If we cannot sync in the second attempt, we give up.
        print("The master server has removed the new server, but the other "
              "servers may not know about it.")

        print "Please run 'sync' to fix the problem, followed by:"
        self._CompleteRemServerHelp(addr, port)
        return

    if res.status != constants.RESPONSE_OK:
      print "Master has returned an unknown error..."
      return

  def _CompleteRemServerHelpComplete(self, addr, port):
    print "Server //%s:%d has been successfully removed!" % (addr, port)
    print "Now you have to do the following:"
    self._CompleteRemServerHelp(addr, port)

  def _CompleteRemServerHelp(self, addr, port):
    print "\t1. Stop the server running on //%s:%d" % (addr, port)
    print "\t2. Remove '//%s:%d' from the configuration file." % (addr, port)
    print "\t3. Remove the data store directory"

  def _Help(self):
    """Help message."""
    print "stop\t\t\t\tStop manager."
    print "servers\t\t\t\tDisplay server information."
    print "ranges\t\t\t\tDisplay server range information."
    print "rebalance\t\t\tRebalance server load."
    print "recover <transaction id>\tComplete a pending transaction."
    print "addserver <address> <port>\tAdd new server to the group."
    print("dropserver <address> <port>\tMove all the data from the server "
          "to others.")
    print "remserver <address> <port>\tRemove server from server group."
    print "sync\t\t\t\tSync server information between data servers."

  def _HandleCommand(self, cmd, args):
    """Execute an user command."""
    if cmd == "stop" or cmd == "exit":
      return False
    elif cmd == "servers":
      self._ShowServers()
    elif cmd == "help":
      self._Help()
    elif cmd == "ranges":
      self._ShowRanges()
    elif cmd == "rebalance":
      self._Rebalance()
    elif cmd == "recover":
      if len(args) != 1:
        print "Syntax: recover <transaction-id>"
      self._Recover(args[0])
    elif cmd == "addserver":
      if len(args) != 2:
        print "Syntax: addserver <address> <port>"
      try:
        self._AddServer(args[0], int(args[1]))
      except ValueError:
        print "Invalid port number: %s" % args[1]
    elif cmd == "dropserver":
      if len(args) != 2:
        print "Syntax: dropserver <address> <port>"
      try:
        self._DropServer(args[0], int(args[1]))
      except ValueError:
        print "Invalid port number: %s" % args[1]
    elif cmd == "remserver":
      if len(args) != 2:
        print "Syntax: remserver <address> <port>"
      try:
        self._RemServer(args[0], int(args[1]))
      except ValueError:
        print "Invalid port number: %s" % args[1]
    elif cmd == "sync":
      self._Sync()
    else:
      print "No such command:", cmd
    return True

  def _NumServers(self):
    if self.mapping:
      return str(self.mapping.num_servers)
    else:
      return "-"

  def Run(self):
    while True:
      line = raw_input("Manager(%s servers)> " % self._NumServers())
      if not line:
        continue
      vec = line.split(" ")
      if not vec:
        continue
      cmd = vec[0]
      args = vec[1:]
      try:
        if not self._HandleCommand(cmd, args):
          break
      except Exception as e:  # pylint: disable=broad-except
        print "Exception:", str(e)


def main(unused_argv):
  """Main."""

  config_lib.CONFIG.AddContext("DataServer Context")
  startup.ClientInit()

  manager = Manager()
  if not manager.Start():
    print "Failed to start manager"
    return

  atexit.register(manager.SaveHistory)
  try:
    manager.Run()
  except (EOFError, KeyboardInterrupt):
    print


if __name__ == "__main__":
  flags.StartMain(main)
