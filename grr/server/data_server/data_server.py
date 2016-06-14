#!/usr/bin/env python
"""A data store server."""


from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import socket
import SocketServer
import time
import urlparse
import uuid

# pylint: disable=unused-import,g-bad-import-order,g-import-not-at-top
try:
  import urllib3
  from urllib3 import connectionpool
except ImportError:
  # Urllib3 also comes as part of requests, try to fallback.
  from requests.packages import urllib3
  from requests.packages.urllib3 import connectionpool

from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order,g-import-not-at-top

import logging

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import registry
from grr.lib import startup
from grr.lib import stats
from grr.lib import utils

from grr.lib.rdfvalues import data_server as rdf_data_server
from grr.lib.rdfvalues import data_store as rdf_data_store

from grr.server.data_server import auth
from grr.server.data_server import constants
from grr.server.data_server import errors
from grr.server.data_server import master
from grr.server.data_server import rebalance
from grr.server.data_server import store
from grr.server.data_server import utils as sutils

flags.DEFINE_integer("port", None, "Specify the data server port.")

flags.DEFINE_string("path", None, "Specify the data store path.")

flags.DEFINE_bool("master", False, "Mark this data server as the master.")


class DataServerHandler(BaseHTTPRequestHandler, object):
  """Handler for HTTP requests to the data server."""

  # Data store service.
  SERVICE = None
  # MASTER is set if this data server is also running as master.
  MASTER = None
  # Set if the server is not the master.
  DATA_SERVER = None
  # Mapping information sent/created by the master.
  MAPPING = None
  CMDTABLE = None
  # Nonce store used for authentication.
  NONCE_STORE = None

  @classmethod
  def InitMasterServer(cls, port):
    cls.MASTER = master.DataMaster(port, cls.SERVICE)
    cls.MAPPING = cls.MASTER.LoadMapping()
    # Master is the only data server that knows about the client credentials.
    # The credentials will be sent to other data servers once they login.
    creds = auth.ClientCredentials()
    creds.InitializeFromConfig()
    cls.NONCE_STORE.SetClientCredentials(creds)
    logging.info("Starting Data Master/Server on port %d ...", port)

  @classmethod
  def InitDataServer(cls, port):
    """Initiates regular data server."""
    cls.DATA_SERVER = StandardDataServer(port, cls)
    # Connect to master server.
    cls.DATA_SERVER.Register()
    cls.MAPPING = cls.DATA_SERVER.LoadMapping()
    cls.DATA_SERVER.PeriodicallySendStatistics()
    logging.info("Starting Data Server on port %d ...", port)

  @classmethod
  def InitHandlerTables(cls):
    """Initializes tables of handler callbacks."""
    cls.HTTP_TABLE = {
        "/manage": cls.HandleManager,
        "/server/handshake": cls.HandleServerHandshake,
        "/server/register": cls.HandleRegister,
        "/server/state": cls.HandleState,
        "/server/mapping": cls.HandleMapping,
        "/client/start": cls.HandleDataStoreService,
        "/client/handshake": cls.HandleClientHandshake,
        "/client/mapping": cls.HandleMapping,
        "/rebalance/phase1": cls.HandleRebalancePhase1,
        "/rebalance/phase2": cls.HandleRebalancePhase2,
        "/rebalance/statistics": cls.HandleRebalanceStatistics,
        "/rebalance/copy": cls.HandleRebalanceCopy,
        "/rebalance/commit": cls.HandleRebalanceCommit,
        "/rebalance/perform": cls.HandleRebalancePerform,
        "/rebalance/recover": cls.HandleRebalanceRecover,
        "/servers/add/check": cls.HandleServerAddCheck,
        "/servers/add": cls.HandleServerAdd,
        "/servers/rem/check": cls.HandleServerRemCheck,
        "/servers/rem": cls.HandleServerRem,
        "/servers/sync": cls.HandleServerSync,
        "/servers/sync-all": cls.HandleServerSyncAll
    }

    cls.STREAMING_TABLE = {
        "/rebalance/copy-file": cls.HandleRebalanceCopyFile,
    }

  @classmethod
  def GetStatistics(cls):
    """Build statistics object for the server."""
    ok = rdf_data_server.DataServerState.Status.AVAILABLE
    num_components, avg_component = cls.SERVICE.GetComponentInformation()
    stat = rdf_data_server.DataServerState(size=cls.SERVICE.Size(),
                                           load=0,
                                           status=ok,
                                           num_components=num_components,
                                           avg_component=avg_component)
    return stat

  protocol_version = "HTTP/1.1"

  # How much to wait.
  CLIENT_TIMEOUT_TIME = 600
  SEND_TIMEOUT = 5
  READ_TIMEOUT = 5
  LOGIN_TIMEOUT = 5

  def __init__(self, request, client_address, server):
    # Data server reference for the master.
    self.data_server = None
    self.rebalance_id = None
    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

  def _Response(self, code, body):
    reply = ("HTTP/1.1 " + str(code) + " OK\n"
             "Content-Length: " + str(len(body)) + "\n"
             "\n" + body)
    self.wfile.write(reply)
    return

  def _EmptyResponse(self, code):
    return self._Response(code, "")

  def _ReadExactly(self, sock, n):
    ret = ""
    left = n
    while left:
      ret += sock.recv(left)
      left = n - len(ret)
    return ret

  def _ReadExactlyFailAfterFirst(self, sock, n):
    """Read from socket but return nothing if we get an exception."""
    ret = ""
    left = n
    while left:
      try:
        ret += sock.recv(left)
        if not ret:
          return ""
        left = n - len(ret)
      except socket.timeout:
        if left < n:
          # We have already read some data, so we just give up.
          return ""
      except socket.error:
        return ""
    return ret

  def HandleClient(self, sock, permissions):
    """Handles new client requests readable from 'read'."""
    # Use a long timeout here.
    sock.settimeout(self.CLIENT_TIMEOUT_TIME)
    cmdlen_str = self._ReadExactlyFailAfterFirst(sock, sutils.SIZE_PACKER.size)
    if not cmdlen_str:
      return ""
    cmdlen = sutils.SIZE_PACKER.unpack(cmdlen_str)[0]
    # Full request must be here.
    sock.settimeout(self.READ_TIMEOUT)
    try:
      cmd_str = self._ReadExactly(sock, cmdlen)
    except (socket.timeout, socket.error):
      return ""
    cmd = rdf_data_server.DataStoreCommand(cmd_str)

    request = cmd.request
    op = cmd.command

    cmdinfo = self.CMDTABLE.get(op)
    if not cmdinfo:
      logging.error("Unrecognized command %d", op)
      return ""
    method, perm = cmdinfo
    if perm in permissions:
      response = method(request)
    else:
      status_desc = ("Operation not allowed: required %s but only have "
                     "%s permissions" % (perm, permissions))
      resp = rdf_data_store.DataStoreResponse(
          request=cmd.request,
          status_desc=status_desc,
          status=rdf_data_store.DataStoreResponse.Status.AUTHORIZATION_DENIED)
      response = resp.SerializeToString()

    return sutils.SIZE_PACKER.pack(len(response)) + response

  def HandleRegister(self):
    """Registers a data server in the master."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    request = rdf_data_server.DataStoreRegistrationRequest(self.post_data)

    port = request.port
    addr = self.client_address[0]
    token = request.token
    if not self.NONCE_STORE.ValidateAuthTokenServer(token):
      self._EmptyResponse(constants.RESPONSE_SERVER_NOT_AUTHORIZED)
      return
    newserver = self.MASTER.RegisterServer(addr, port)
    if newserver:
      self.data_server = newserver
      index = newserver.Index()
      body = sutils.SIZE_PACKER.pack(index)
      # Need to send back the encrypted client credentials.
      body += self.NONCE_STORE.EncryptClientCredentials()
      self._Response(constants.RESPONSE_OK, body)
    else:
      # Could not register the Data Server.
      logging.warning("Could not register server %s:%d. Maybe not allowed?",
                      addr, port)
      self._EmptyResponse(constants.RESPONSE_SERVER_NOT_ALLOWED)

  def HandleState(self):
    """Respond to /server/state."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    if not self.data_server:
      logging.error("Server %s attempting to update its state but "
                    "is not registered yet", self.client_address)
      self._EmptyResponse(constants.RESPONSE_SERVER_NOT_REGISTERED)
      return
    state = rdf_data_server.DataServerState(self.post_data)
    self.data_server.UpdateState(state)
    logging.info("Received new state from server %s", self.client_address)
    # Response with our mapping.
    body = self.MAPPING.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleHandshake(self):
    """Return a nonce to either a server or client."""
    nonce = self.NONCE_STORE.NewNonce()
    if not nonce:
      raise errors.DataServerError("Could not generate new nonces! Too many "
                                   "requests and/or clients.")
    self._Response(constants.RESPONSE_OK, nonce)

  def HandleClientHandshake(self):
    """Starts the handshake with data server clients."""
    self.HandleHandshake()

  def HandleServerHandshake(self):
    """Starts the handshake with data servers."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    self.HandleHandshake()

  def HandleDataStoreService(self):
    """Initiate a conversation for handling data store commands."""
    if self.data_server:
      # If the data server is connected, this does not make sense.
      self._EmptyResponse(constants.RESPONSE_NOT_A_CLIENT)
      return
    # We never return anything for this request.
    # Simply use the socket and serve database requests.
    sock = self.connection
    sock.setblocking(1)

    # But first we need to validate the client by reading the token.
    token = rdf_data_server.DataStoreAuthToken(self.post_data)
    perms = self.NONCE_STORE.ValidateAuthTokenClient(token)
    if not perms:
      sock.sendall("IP\n")
      sock.close()
      self.close_connection = 1
      return

    logging.info("Client %s has started using the data server",
                 self.client_address)
    try:
      # Send handshake.
      sock.settimeout(self.LOGIN_TIMEOUT)  # 10 seconds to login.
      sock.sendall("OK\n")
    except (socket.error, socket.timeout):
      logging.warning("Could not login client %s", self.client_address)
      self.close_connection = 1
      return

    while True:
      # Handle requests
      replybody = self.HandleClient(sock, perms)

      if not replybody:
        # Client probably died or there was an error in the connection.
        # Force the client to reconnect and send the command again.
        sock.close()
        self.close_connection = 1
        return

      try:
        sock.settimeout(self.SEND_TIMEOUT)  # 1 minute timeout.
        sock.sendall(replybody)
      except (socket.error, socket.timeout):
        # At this point, there is no way to know how much data was actually
        # sent. Therefore, we close the connection and force the client to
        # reconnect. When the client gets an error, he should assume that
        # the command was not successful
        sock.close()
        self.close_connection = 1
        return

  def HandleMapping(self):
    """Returns the mapping to a client or server."""
    if not self.MAPPING:
      self._EmptyResponse(constants.RESPONSE_MAPPING_NOT_FOUND)
      return
    body = self.MAPPING.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleManager(self):
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    # Response with our mapping.
    body = self.MAPPING.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleRebalancePhase1(self):
    """Call master to perform phase 1 of the rebalancing operation."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    if self.MASTER.IsRebalancing():
      self._EmptyResponse(constants.RESPONSE_MASTER_IS_REBALANCING)
      return
    new_mapping = rdf_data_server.DataServerMapping(self.post_data)
    rebalance_id = str(uuid.uuid4())
    reb = rdf_data_server.DataServerRebalance(id=rebalance_id,
                                              mapping=new_mapping)
    if not self.MASTER.SetRebalancing(reb):
      logging.warning("Could not contact servers for rebalancing")
      self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
      return
    if not self.MASTER.FetchRebalanceInformation():
      logging.warning("Could not contact servers for rebalancing statistics")
      self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
      return
    self.rebalance_id = rebalance_id
    body = reb.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleRebalanceStatistics(self):
    """Call data server to count how much data needs to move in rebalancing."""
    reb = rdf_data_server.DataServerRebalance(self.post_data)
    mapping = reb.mapping
    index = 0
    if not self.MASTER:
      index = self.DATA_SERVER.Index()
    moving = rebalance.ComputeRebalanceSize(mapping, index)
    reb.moving.Append(moving)
    body = reb.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleRebalanceCopy(self):
    reb = rdf_data_server.DataServerRebalance(self.post_data)
    index = 0
    if not self.MASTER:
      index = self.DATA_SERVER.Index()
    rebalance.CopyFiles(reb, index)
    self._EmptyResponse(constants.RESPONSE_OK)

  def HandleRebalanceCopyFile(self):
    if not rebalance.SaveTemporaryFile(self.rfile):
      return self._EmptyResponse(constants.RESPONSE_FILE_NOT_SAVED)
    self._EmptyResponse(constants.RESPONSE_OK)

  def HandleRebalancePhase2(self):
    """Call master to perform phase 2 of rebalancing."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    reb = rdf_data_server.DataServerRebalance(self.post_data)
    current = self.MASTER.IsRebalancing()
    if not current or current.id != reb.id:
      # Not the same ID.
      self._EmptyResponse(constants.RESPONSE_WRONG_TRANSACTION)
      return
    if not self.MASTER.CopyRebalanceFiles():
      self._EmptyResponse(constants.RESPONSE_FILES_NOT_COPIED)
      return
    self._EmptyResponse(constants.RESPONSE_OK)

  def HandleRebalanceCommit(self):
    """Call master to commit rebalance transaction."""
    if not self.MASTER:
      self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
      return
    reb = rdf_data_server.DataServerRebalance(self.post_data)
    current = self.MASTER.IsRebalancing()
    if not current or current.id != reb.id:
      # Not the same ID.
      self._EmptyResponse(constants.RESPONSE_WRONG_TRANSACTION)
      return
    new_mapping = self.MASTER.RebalanceCommit()
    if not new_mapping:
      self._EmptyResponse(constants.RESPONSE_NOT_COMMITED)
      return
    self._Response(constants.RESPONSE_OK, self.MAPPING.SerializeToString())

  def HandleRebalancePerform(self):
    """Call data server to perform rebalance transaction."""
    reb = rdf_data_server.DataServerRebalance(self.post_data)
    if not rebalance.MoveFiles(reb, self.MASTER):
      logging.critical("Failed to perform transaction %s", reb.id)
      self._EmptyResponse(constants.RESPONSE_FILES_NOT_MOVED)
      return
    # Update range of servers.
    # But only for regular data servers since the master is responsible for
    # starting the operation.
    if self.DATA_SERVER:
      for i, serv in enumerate(list(reb.mapping.servers)):
        self.MAPPING.servers[i].interval.start = serv.interval.start
        self.MAPPING.servers[i].interval.end = serv.interval.end
      self.DATA_SERVER.SetMapping(self.MAPPING)
    # Send back server state.
    stat = self.GetStatistics()
    body = stat.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def HandleRebalanceRecover(self):
    """Call master to recover rebalance transaction."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    transid = self.post_data
    logging.info("Attempting to recover transaction %s", transid)
    reb = rebalance.GetCommitInformation(transid)
    if not reb:
      self._EmptyResponse(constants.RESPONSE_TRANSACTION_NOT_FOUND)
      return
    if not self.MASTER.SetRebalancing(reb):
      logging.warning("Could not contact servers for rebalancing")
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    body = reb.SerializeToString()
    self._Response(constants.RESPONSE_OK, body)

  def _UnpackNewServer(self):
    data = self.post_data
    addrlen_str = data[:sutils.SIZE_PACKER.size]
    data = data[sutils.SIZE_PACKER.size:]
    addrlen = sutils.SIZE_PACKER.unpack(addrlen_str)[0]
    addr = data[:addrlen]
    data = data[addrlen:]
    port_str = data[:sutils.PORT_PACKER.size]
    port = sutils.PORT_PACKER.unpack(port_str)[0]
    return (addr, port)

  def HandleServerAddCheck(self):
    """Check if it is possible to add a new server."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    if not self.MASTER.AllRegistered():
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    addr, port = self._UnpackNewServer()
    logging.info("Checking new server %s:%d", addr, port)
    if self.MASTER.HasServer(addr, port):
      return self._EmptyResponse(constants.RESPONSE_EQUAL_DATA_SERVER)
    else:
      return self._EmptyResponse(constants.RESPONSE_OK)

  def HandleServerSync(self):
    """Master wants to send the mapping to us."""
    if self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_IS_MASTER_SERVER)
    mapping = rdf_data_server.DataServerMapping(self.post_data)
    self.DATA_SERVER.SetMapping(mapping)
    # Return state server back.
    body = self.GetStatistics().SerializeToString()
    return self._Response(constants.RESPONSE_OK, body)

  def HandleServerAdd(self):
    """Add new server to the group."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    if not self.MASTER.AllRegistered():
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    if self.MASTER.IsRebalancing():
      return self._EmptyResponse(constants.RESPONSE_MASTER_IS_REBALANCING)
    addr, port = self._UnpackNewServer()
    logging.info("Adding new server %s:%d", addr, port)
    server = self.MASTER.AddServer(addr, port)
    if self.MASTER.SyncMapping(skip=[server]):
      body = self.MAPPING.SerializeToString()
      self._Response(constants.RESPONSE_OK, body)
    else:
      return self._EmptyResponse(constants.RESPONSE_INCOMPLETE_SYNC)

  def HandleServerSyncAll(self):
    """Send mapping information to all servers."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    if not self.MASTER.AllRegistered():
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    if self.MASTER.IsRebalancing():
      return self._EmptyResponse(constants.RESPONSE_MASTER_IS_REBALANCING)
    if self.MASTER.SyncMapping():
      body = self.MAPPING.SerializeToString()
      self._Response(constants.RESPONSE_OK, body)
    else:
      self._EmptyResponse(constants.RESPONSE_INCOMPLETE_SYNC)

  def HandleServerRemCheck(self):
    """Check if a data server can be removed."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    if not self.MASTER.AllRegistered():
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    if self.MASTER.IsRebalancing():
      return self._EmptyResponse(constants.RESPONSE_MASTER_IS_REBALANCING)
    addr, port = self._UnpackNewServer()
    server = self.MASTER.HasServer(addr, port)
    if not server:
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVER_NOT_FOUND)
    # Interval range must be 0.
    interval = server.Interval()
    if interval.start != interval.end:
      return self._EmptyResponse(constants.RESPONSE_RANGE_NOT_EMPTY)
    return self._EmptyResponse(constants.RESPONSE_OK)

  def HandleServerRem(self):
    """Remove a data server from the server group."""
    if not self.MASTER:
      return self._EmptyResponse(constants.RESPONSE_NOT_MASTER_SERVER)
    if not self.MASTER.AllRegistered():
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVERS_UNREACHABLE)
    if self.MASTER.IsRebalancing():
      return self._EmptyResponse(constants.RESPONSE_MASTER_IS_REBALANCING)
    addr, port = self._UnpackNewServer()
    logging.info("Removing server %s:%d", addr, port)
    removed_server = self.MASTER.HasServer(addr, port)
    if not removed_server:
      return self._EmptyResponse(constants.RESPONSE_DATA_SERVER_NOT_FOUND)
    if not self.MASTER.RemoveServer(removed_server):
      return self._EmptyResponse(constants.RESPONSE_RANGE_NOT_EMPTY)
    if self.MASTER.SyncMapping():
      body = self.MAPPING.SerializeToString()
      self._Response(constants.RESPONSE_OK, body)
    else:
      return self._EmptyResponse(constants.RESPONSE_INCOMPLETE_SYNC)

  def do_POST(self):  # pylint: disable=invalid-name
    self.post_data = None

    fun = self.HTTP_TABLE.get(self.path)
    if fun:
      size = self.headers.get("Content-Length")
      if size:
        self.post_data = self.rfile.read(int(size))
      fun(self)
    else:
      fun = self.STREAMING_TABLE.get(self.path)
      if fun:
        # Streaming services use the rfile directly, possibly receiving large
        # amounts of data, so we can't cache the post_data here.
        fun(self)
      else:
        return self._EmptyResponse(constants.RESPONSE_NOT_FOUND)

  def finish(self):
    BaseHTTPRequestHandler.finish(self)
    if self.data_server:
      logging.warning("Server %s disconnected", self.client_address)
      if not self.data_server.WasRemoved():
        self.MASTER.DeregisterServer(self.data_server)
      self.data_server = None
    elif self.rebalance_id:
      reb = self.MASTER.IsRebalancing()
      if reb:
        self.MASTER.CancelRebalancing()
        logging.warning("Rebalancing operation %s canceled", reb.id)
      self.rebalance_id = False
    else:
      logging.warning("Client %s has stopped using the server",
                      self.client_address)


class ThreadedHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
  """Multi-threaded http server."""

  daemon_threads = True


class StandardDataServer(object):
  """Handles the connection with the data master."""

  MASTER_RECONNECTION_TIME = 60

  def __init__(self, my_port, handler_cls):
    servers = config_lib.CONFIG["Dataserver.server_list"]
    if not servers:
      raise errors.DataServerError("List of data servers not available.")
    master_location = servers[0]
    loc = urlparse.urlparse(master_location, scheme="http")
    self.index = None
    self.master_addr = loc.hostname
    self.master_port = loc.port
    self.my_port = my_port
    self.pool = connectionpool.HTTPConnectionPool(self.master_addr,
                                                  port=int(self.master_port),
                                                  maxsize=1)
    self.registered = False
    self.periodic_fail = 0

    self.handler_cls = handler_cls

  def _DoRegister(self):
    try:
      username, password = self.handler_cls.NONCE_STORE.GetServerCredentials()
      # First get a nonce.
      res = self.pool.urlopen("POST", "/server/handshake", "", headers={})
      if res.status != constants.RESPONSE_OK:
        raise errors.DataServerError("Could not register data server at "
                                     "data master.")
      nonce = res.data
      token = self.handler_cls.NONCE_STORE.GenerateServerAuthToken(nonce)
      request = rdf_data_server.DataStoreRegistrationRequest(token=token,
                                                             port=self.my_port)
      body = request.SerializeToString()
      headers = {"Content-Length": len(body)}
      res = self.pool.urlopen("POST",
                              "/server/register",
                              headers=headers,
                              body=body)
      if res.status == constants.RESPONSE_SERVER_NOT_AUTHORIZED:
        raise errors.DataServerError("Wrong server password.")
      if res.status == constants.RESPONSE_SERVER_NOT_ALLOWED:
        raise errors.DataServerError("Server not part of this server group.")
      if res.status == constants.RESPONSE_NOT_MASTER_SERVER:
        raise errors.DataServerError("Server %s:%d is not a master server.",
                                     self.master_addr, self.master_port)
      if res.status != constants.RESPONSE_OK:
        raise errors.DataServerError("Could not register data server at data "
                                     "master.")
      logging.info("DataServer fully registered.")
      id_str = res.data[:sutils.SIZE_PACKER.size]
      self.index = sutils.SIZE_PACKER.unpack(id_str)[0]
      creds_str = res.data[sutils.SIZE_PACKER.size:]
      # Read client credentials so we know who to allow data store access.
      creds = auth.ClientCredentials()
      creds.InitializeFromEncryption(creds_str, username, password)
      self.handler_cls.NONCE_STORE.SetClientCredentials(creds)
      return True
    except (urllib3.exceptions.HTTPError, urllib3.exceptions.PoolError):
      return False

  def Register(self):
    """Attempts to register wth the data master."""
    logging.info("Registering with data master at %s:%d.", self.master_addr,
                 self.master_port)
    started = time.time()
    while True:
      if self._DoRegister():
        break
      logging.warning("Failed to connect with master on %s:%d",
                      self.master_addr, self.master_port)
      if time.time() - started > self.MASTER_RECONNECTION_TIME:
        raise errors.DataServerError("Could not connect to data master at "
                                     "%s:%d" % (self.master_addr,
                                                self.master_port))
      time.sleep(2)

    self.registered = True

  def Index(self):
    return self.index

  def SetMapping(self, mapping):
    self.handler_cls.SERVICE.SaveServerMapping(mapping)
    self.handler_cls.MAPPING = mapping

  def _SendStatistics(self):
    """Send statistics to server."""
    try:
      stat = self.handler_cls.GetStatistics()
      body = stat.SerializeToString()
      headers = {"Content-Length": len(body)}
      res = self.pool.urlopen("POST",
                              "/server/state",
                              headers=headers,
                              body=body)
      if res.status == constants.RESPONSE_SERVER_NOT_REGISTERED:
        # The connection has probably been dropped and we need to register
        # again.
        self.Register()
        return True
      if res.status != constants.RESPONSE_OK:
        logging.warning("Could not send statistics to data master.")
        return False
      # Also receive the new mapping with new statistics.
      mapping = rdf_data_server.DataServerMapping(res.data)
      self.handler_cls.SERVICE.SaveServerMapping(mapping)
      return True
    except (urllib3.exceptions.MaxRetryError, errors.DataServerError):
      logging.warning("Could not send statistics to data master.")
      return False

  def _PeriodicThread(self):
    if self._SendStatistics():
      self.periodic_fail = 0
    else:
      self.periodic_fail += 1
      if self.periodic_fail >= 5:
        logging.warning("Could not contact data master. Waiting...")
        time.sleep(self.MASTER_RECONNECTION_TIME)
        self.registered = False
        self.Register()

  def PeriodicallySendStatistics(self):
    """Periodically send statistics to master server."""
    sleep = config_lib.CONFIG["Dataserver.stats_frequency"]
    self.failed = 0
    self.stat_thread = utils.InterruptableThread(target=self._PeriodicThread,
                                                 sleep_time=sleep)
    self.stat_thread.start()

  def LoadMapping(self):
    """Load mapping from either the database or the master server."""
    mapping = self.handler_cls.SERVICE.LoadServerMapping()
    if mapping:
      return mapping
    return self.RenewMapping()

  def RenewMapping(self):
    """Ask master server for mapping."""
    try:
      res = self.pool.urlopen("POST", "/server/mapping")
      if res.status != constants.RESPONSE_OK:
        raise errors.DataServerError("Could not get server mapping from data "
                                     "master.")
      mapping = rdf_data_server.DataServerMapping(res.data)
      self.handler_cls.SERVICE.SaveServerMapping(mapping)
      return mapping
    except urllib3.exceptions.MaxRetryError:
      raise errors.DataServerError("Error when attempting to communicate with"
                                   " data master.")

  def Stop(self):
    if self.stat_thread:
      self.stat_thread.Stop()


def Start(db,
          port=0,
          is_master=False,
          server_cls=ThreadedHTTPServer,
          reqhandler_cls=DataServerHandler):
  """Start the data server."""
  # This is the service that will handle requests to the data store.

  if reqhandler_cls.MASTER or reqhandler_cls.DATA_SERVER:
    logging.fatal("Attempt to start server with duplicate request handler.")

  if not reqhandler_cls.SERVICE:
    reqhandler_cls.SERVICE = store.DataStoreService(db)

  # Create the command table for faster execution of remote calls.
  # Along with a method, each command has the required permissions.
  cmd = rdf_data_server.DataStoreCommand.Command
  reqhandler_cls.CMDTABLE = {
      cmd.DELETE_ATTRIBUTES: (reqhandler_cls.SERVICE.DeleteAttributes, "w"),
      cmd.DELETE_SUBJECT: (reqhandler_cls.SERVICE.DeleteSubject, "w"),
      cmd.MULTI_SET: (reqhandler_cls.SERVICE.MultiSet, "w"),
      cmd.MULTI_RESOLVE_PREFIX: (reqhandler_cls.SERVICE.MultiResolvePrefix,
                                 "r"),
      cmd.RESOLVE_MULTI: (reqhandler_cls.SERVICE.ResolveMulti, "r"),
      cmd.LOCK_SUBJECT: (reqhandler_cls.SERVICE.LockSubject, "w"),
      cmd.EXTEND_SUBJECT: (reqhandler_cls.SERVICE.ExtendSubject, "w"),
      cmd.UNLOCK_SUBJECT: (reqhandler_cls.SERVICE.UnlockSubject, "w"),
      cmd.SCAN_ATTRIBUTES: (reqhandler_cls.SERVICE.ScanAttributes, "r")
  }

  # Initialize nonce store for authentication.
  if not reqhandler_cls.NONCE_STORE:
    reqhandler_cls.NONCE_STORE = auth.NonceStore()

  if port == 0 or port is None:
    logging.debug("No port was specified as a parameter. Expecting to find "
                  "port in configuration file.")
  else:
    logging.debug("Port specified was '%i'. Ignoring configuration directive "
                  "Dataserver.port.", port)

  server_port = port or config_lib.CONFIG["Dataserver.port"]

  if is_master:
    logging.debug("Master server running on port '%i'", server_port)
    reqhandler_cls.InitMasterServer(server_port)
  else:
    logging.debug("Non-master data server running on port '%i'", server_port)
    reqhandler_cls.InitDataServer(server_port)

  reqhandler_cls.InitHandlerTables()

  logging.info("Starting! master: " + str(is_master) + " with handler " +
               reqhandler_cls.__name__)

  try:
    server = server_cls(("", server_port), reqhandler_cls)
    server.serve_forever()
  except KeyboardInterrupt:
    print "Caught keyboard interrupt, stopping server at port %s" % server_port
  except socket.error:
    print "Service already running at port %s" % server_port
  finally:
    if reqhandler_cls.MASTER:
      reqhandler_cls.MASTER.Stop()
    else:
      reqhandler_cls.DATA_SERVER.Stop()


def main(unused_argv):
  """Main."""
  # Change the startup sequence in order to set the database path, if needed.
  startup.AddConfigContext()
  config_lib.CONFIG.AddContext("DataServer Context",
                               "Context applied when running a data server.")

  startup.ConfigInit()

  if flags.FLAGS.path:
    config_lib.CONFIG.Set("Datastore.location", flags.FLAGS.path)

  startup.ServerLoggingStartupInit()
  stats.STATS = stats.StatsCollector()

  # We avoid starting some hooks because they add unneeded things
  # to the data store.
  do_not_start = set(["ConfigurationViewInitHook", "FileStoreInit",
                      "GRRAFF4Init"])
  registry.Init(skip_set=do_not_start)

  Start(data_store.DB, port=flags.FLAGS.port, is_master=flags.FLAGS.master)


if __name__ == "__main__":
  flags.StartMain(main)
