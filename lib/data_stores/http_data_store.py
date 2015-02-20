#!/usr/bin/env python
"""A remote data store using HTTP."""


import base64
import binascii
import httplib
import random
import re
import socket
import threading
import time
import urlparse

import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.data_stores import common

from grr.server.data_server import auth
from grr.server.data_server import constants
from grr.server.data_server import utils as sutils


def CheckResponseStatus(response):
  """Catch error conditions from the response and raise them."""
  # Common case exit early.
  if response.status == rdfvalue.DataStoreResponse.Status.OK:
    return response

  elif (response.status ==
        rdfvalue.DataStoreResponse.Status.AUTHORIZATION_DENIED):
    raise access_control.UnauthorizedAccess(response.status_desc,
                                            response.failed_subject)

  elif response.status == rdfvalue.DataStoreResponse.Status.TIMEOUT_ERROR:
    raise data_store.TimeoutError(response.status_desc)

  elif response.status == rdfvalue.DataStoreResponse.Status.DATA_STORE_ERROR:
    raise data_store.Error(response.status_desc)

  raise data_store.Error("Unknown error %s" % response.status_desc)


class Error(data_store.Error):
  """Base class for remote data store errors."""
  pass


class HTTPDataStoreError(Error):
  """Raised when there is a critical error in the remote data store."""
  pass


class DataServerConnection(object):
  """Represents one connection to a data server."""

  def __init__(self, server):
    self.conn = None
    self.sock = None
    self.lock = threading.Lock()
    self.server = server
    # Mark pending requests and subjects that are scheduled to change on
    # the database.
    self.requests = []
    self._DoConnection()

  def Address(self):
    return self.server.Address()

  def Port(self):
    return self.server.Port()

  def _ReadExactly(self, n):
    ret = ""
    left = n
    while left:
      ret += self.sock.recv(left)
      left = n - len(ret)
    return ret

  def _ReadReply(self):
    try:
      replylen_str = self._ReadExactly(sutils.SIZE_PACKER.size)
      if not replylen_str:
        raise HTTPDataStoreError("Could not read reply from data server.")
      replylen = sutils.SIZE_PACKER.unpack(replylen_str)[0]
      reply = self._ReadExactly(replylen)
      response = rdfvalue.DataStoreResponse(reply)
      CheckResponseStatus(response)
      return response
    except (socket.error, socket.timeout):
      logging.warning("Cannot read reply from server %s:%d", self.Address(),
                      self.Port())
      return None

  def _Sync(self):
    """Read responses from the pending requests."""
    self.sock.settimeout(config_lib.CONFIG["HTTPDataStore.read_timeout"])
    while self.requests:
      response = self._ReadReply()
      if not response:
        # Could not read response. Let's exit and force a reconnection
        # followed by a replay.
        # TODO(user): Maybe we need to assign an unique ID for each
        # request so that the server knows which ones were already applied.
        return False
      self.requests.pop()
    return True

  def _SendRequest(self, command):
    request_str = command.SerializeToString()
    request_body = sutils.SIZE_PACKER.pack(len(request_str)) + request_str
    self.sock.settimeout(config_lib.CONFIG["HTTPDataStore.send_timeout"])
    try:
      self.sock.sendall(request_body)
      return True
    except (socket.error, socket.timeout):
      logging.warning("Could not send request to server %s:%d", self.Address(),
                      self.Port())
      return False

  def _Reconnect(self):
    """Reconnect to the data server."""
    try:
      if self.sock:
        self.sock.close()
    except socket.error:
      pass
    try:
      if self.conn:
        self.conn.close()
    except httplib.HTTPException:
      pass
    try:
      logging.info("Attempting to connect to data server %s:%d",
                   self.Address(), self.Port())
      self.conn = httplib.HTTPConnection(self.Address(), self.Port())
      username = config_lib.CONFIG.Get("HTTPDataStore.username")
      password = config_lib.CONFIG.Get("HTTPDataStore.password")
      if not username:
        raise HTTPDataStoreError("HTTPDataStore.username not provided")
      if not password:
        raise HTTPDataStoreError("HTTPDataStore.password not provided")
      # We ask the server for a nonce.
      self.conn.request("POST", "/client/handshake", "", {})
      response = self.conn.getresponse()
      if response.status != constants.RESPONSE_OK:
        logging.warning("Could not handshake the server %s:%d", self.Address(),
                        self.Port())
        return False
      # Generate the authentication token.
      size_nonce = int(response.getheader("Content-Length"))
      nonce = response.read(size_nonce)
      rdf_token = auth.NonceStore.GenerateAuthToken(nonce, username, password)
      token = rdf_token.SerializeToString()
      # We trick HTTP here and use the underlying socket to pipeline requests.
      headers = {"Content-Length": len(token)}
      self.conn.request("POST", "/client/start", token, headers)
      self.sock = self.conn.sock
      # Confirm handshake.
      self.sock.setblocking(1)
      self.sock.settimeout(config_lib.CONFIG["HTTPDataStore.login_timeout"])
      ack = self._ReadExactly(3)
      if ack == "IP\n":
        raise HTTPDataStoreError("Invalid data server username/password.")
      if ack != "OK\n":
        return False
      logging.info("Connected to data server %s:%d", self.Address(),
                   self.Port())
      return True
    except httplib.HTTPException as e:
      logging.warning("Httplib problem when connecting to %s:%d: %s",
                      self.Address(), self.Port(), str(e))
      return False
    except (socket.error, socket.timeout):
      logging.warning("Socket problem when connecting to %s:%d",
                      self.Address(), self.Port())
      return False
    return False

  def _ReplaySync(self):
    """Send all the requests again."""
    if self.requests:
      logging.info("Replaying the failed requests")
    while self.requests:
      req = self.requests[-1]
      if not self._SendRequest(req):
        return False
      self.sock.settimeout(config_lib.CONFIG["HTTPDataStore.replay_timeout"])
      response = self._ReadReply()
      if not response:
        # Could not read response. Let's exit and force a reconnection
        # followed by a replay.
        # TODO(user): Maybe we need to assign an unique ID for each
        # request so that the server knows which ones were already applied.
        return False
      self.requests.pop()
    return True

  def _DoConnection(self):
    """Cleanups the current connection and creates another one."""
    started = time.time()
    while True:
      if self._Reconnect() and self._ReplaySync():
        break
      else:
        logging.warning("Had to connect to %s:%d but failed. Trying again...",
                        self.Address(), self.Port())
        # Sleep for some time before trying again.
        time.sleep(config_lib.CONFIG["HTTPDataStore.retry_time"])
      if time.time() - started >= config_lib.CONFIG[
          "HTTPDataStore.reconnect_timeout"]:
        raise HTTPDataStoreError("Could not connect to %s:%d. Giving up." %
                                 (self.Address(), self.Port()))

  def _RedoConnection(self):
    logging.warning("Attempt to reconnect with %s:%d", self.Address(),
                    self.Port())
    self._DoConnection()

  @utils.Synchronized
  def MakeRequestAndContinue(self, command, unused_subject):
    """Make request but do not sync with the data server."""
    while not self._SendRequest(command):
      self._RedoConnection()
    self.requests.insert(0, command)
    return None

  @utils.Synchronized
  def SyncAndMakeRequest(self, command):
    """Make a request to the data server and return the response."""
    if not self._Sync():
      # Must reconnect and resend requests.
      self._RedoConnection()
    # At this point, we have a synchronized connection.
    while not self._SendRequest(command):
      self._RedoConnection()
    self.sock.settimeout(config_lib.CONFIG["HTTPDataStore.read_timeout"])
    response = self._ReadReply()
    if not response:
      # Must reconnect and resend the request.
      while True:
        self._RedoConnection()
        if not self._SendRequest(command):
          continue
        response = self._ReadReply()
        if response:
          break
    return response

  @utils.Synchronized
  def Sync(self):
    self._Sync()

  def NumPendingRequests(self):
    return len(self.requests)

  def Close(self):
    self.conn.close()


class DataServer(object):
  """A DataServer object contains connections a data server."""

  def __init__(self, addr, port):
    self.addr = addr
    self.port = port
    self.conn = httplib.HTTPConnection(self.Address(), self.Port())
    self.lock = threading.Lock()
    self.max_connections = config_lib.CONFIG["Dataserver.max_connections"]
    # Start with a single connection.
    self.connections = [DataServerConnection(self)]

  def Port(self):
    return self.port

  def Address(self):
    return self.addr

  def Close(self):
    for conn in self.connections:
      conn.Close()
    self.connections = []
    if self.conn:
      self.conn.close()
      self.conn = None

  @utils.Synchronized
  def Sync(self):
    for conn in self.connections:
      conn.Sync()

  @utils.Synchronized
  def GetConnection(self):
    """Return a connection to the data server."""
    best = min(self.connections, key=lambda x: x.NumPendingRequests())
    if best.NumPendingRequests():
      if len(self.connections) == self.max_connections:
        # Too many connections, use this one.
        return best
      new = DataServerConnection(self)
      self.connections.append(new)
      return new
    else:
      return best

    # Attempt to get one connection with no pending requests.
    return self.connections[0]

  def _FetchMapping(self):
    """Attempt to fetch mapping from the data server."""
    try:
      self.conn.request("POST", "/client/mapping")
      res = self.conn.getresponse()
      if res.status != constants.RESPONSE_OK:
        return None
      return res.read()
    except httplib.HTTPException:
      logging.warning("Could not connect server %s:%d", self.Address(),
                      self.Port())
      return None

  def LoadMapping(self):
    """Load mapping from the data server."""
    started = time.time()
    while True:
      data = self._FetchMapping()
      if data:
        mapping = rdfvalue.DataServerMapping(data)
        return mapping

      if time.time() - started > config_lib.CONFIG[
          "HTTPDataStore.reconnect_timeout"]:
        raise HTTPDataStoreError("Could not get server mapping from data "
                                 "server at %s:%d." %
                                 (self.Address(), self.Port()))
      time.sleep(config_lib.CONFIG["HTTPDataStore.retry_time"])


class RemoteInquirer(object):
  """Class that holds connections to all data servers."""

  mapping = None

  def __init__(self):
    # Create a connection to all data servers
    server_list = config_lib.CONFIG["Dataserver.server_list"]
    if not server_list:
      raise HTTPDataStoreError("List of data servers is not available.")
    self.servers = []
    for location in server_list:
      loc = urlparse.urlparse(location, scheme="http")
      addr = loc.hostname
      port = loc.port
      self.servers.append(DataServer(addr, port))
    self.mapping_server = random.choice(self.servers)
    self.mapping = self.mapping_server.LoadMapping()

    if len(self.mapping.servers) != len(server_list):
      logging.warning("There is a mismatch between the data "
                      "servers and the configuration file. '%s' != '%s'",
                      self.mapping.servers,
                      server_list)
      raise HTTPDataStoreError("There is a mismatch between the data "
                               "servers and the configuration file.")
    for i, serv in enumerate(self.mapping.servers):
      target = self.servers[i]
      if target.Port() != serv.port:
        logging.warning("There is a mismatch between the data "
                        "servers and the configuration file. '%s' != '%s'",
                        self.mapping.servers,
                        server_list)
        raise HTTPDataStoreError("There is a mismatch between the data "
                                 "servers and the configuration file.")

  def MapKey(self, key):
    """Return the data server responsible for a given key."""
    sid = sutils.MapKeyToServer(self.mapping, key)
    return self.servers[sid]

  def GetPathing(self):
    return self.GetMapping().pathing

  def RenewMapping(self):
    self.mapping = self.mapping_server.LoadMapping()
    return self.mapping

  def GetMapping(self):
    return self.mapping

  def Flush(self):
    for serv in self.servers:
      serv.Sync()

  def CloseConnections(self):
    for serv in self.servers:
      serv.Close()


class RemoteMappingCache(utils.FastStore):
  """A local cache for mappings between paths and data servers."""

  def __init__(self, size):
    super(RemoteMappingCache, self).__init__(size)
    self.inquirer = RemoteInquirer()
    self.path_regexes = [re.compile(x) for x in self.inquirer.GetPathing()]

  def KillObject(self, obj):
    pass

  def GetInquirer(self):
    return self.inquirer

  @utils.Synchronized
  def Get(self, subject):
    """This will create the object if needed so should not fail."""
    filename, directory = common.ResolveSubjectDestination(subject,
                                                           self.path_regexes)
    key = common.MakeDestinationKey(directory, filename)
    try:
      return super(RemoteMappingCache, self).Get(key)
    except KeyError:
      data_server = self.inquirer.MapKey(key)

      super(RemoteMappingCache, self).Put(key, data_server)

      return data_server


class HTTPDataStore(data_store.DataStore):
  """A data store which calls a remote server."""

  cache = None
  inquirer = None

  def __init__(self):
    super(HTTPDataStore, self).__init__()
    self.cache = RemoteMappingCache(1000)
    self.inquirer = self.cache.GetInquirer()
    self._ComputeNewSize(self.inquirer.GetMapping(), time.time())

  def GetServer(self, subject):
    return self.cache.Get(subject).GetConnection()

  def TimestampSpecFromTimestamp(self, timestamp):
    """Create a timestamp spec from a timestamp value.

    Args:
      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

    Returns:
       An rdfvalue.TimestampSpec() instance.
    """
    if timestamp is None:
      all_ts = rdfvalue.TimestampSpec.Type.ALL_TIMESTAMPS
      return rdfvalue.TimestampSpec(type=all_ts)

    if timestamp in (rdfvalue.TimestampSpec.Type.ALL_TIMESTAMPS,
                     rdfvalue.TimestampSpec.Type.NEWEST_TIMESTAMP):
      return rdfvalue.TimestampSpec(type=timestamp)

    if timestamp == self.NEWEST_TIMESTAMP:
      newest = rdfvalue.TimestampSpec.Type.NEWEST_TIMESTAMP
      return rdfvalue.TimestampSpec(type=newest)

    if isinstance(timestamp, (list, tuple)):
      start, end = timestamp
      return rdfvalue.TimestampSpec(
          start=start, end=end,
          type=rdfvalue.TimestampSpec.Type.RANGED_TIME)

    return rdfvalue.TimestampSpec(
        start=timestamp,
        type=rdfvalue.TimestampSpec.Type.SPECIFIC_TIME)

  def _MakeSyncRequest(self, request, typ):
    return self._MakeRequestSyncOrAsync(request, typ, True)

  def _MakeRequestSyncOrAsync(self, request, typ, sync):
    subject = request.subject[0]
    server = self.GetServer(subject)
    cmd = rdfvalue.DataStoreCommand(command=typ, request=request)
    if sync:
      return server.SyncAndMakeRequest(cmd)
    else:
      return server.MakeRequestAndContinue(cmd, subject)

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
    request = rdfvalue.DataStoreRequest(subject=[subject])

    # Set timestamp.
    start = start or 0
    if end is None:
      end = (2 ** 63) - 1  # sys.maxint

    request.timestamp = rdfvalue.TimestampSpec(
        start=start, end=end, type=rdfvalue.TimestampSpec.Type.RANGED_TIME)

    if token:
      request.token = token
    if sync:
      request.sync = sync

    for attr in attributes:
      request.values.Append(attribute=attr)

    typ = rdfvalue.DataStoreCommand.Command.DELETE_ATTRIBUTES
    self._MakeRequestSyncOrAsync(request, typ, sync)

  def DeleteSubject(self, subject, sync=False, token=None):
    request = rdfvalue.DataStoreRequest(subject=[subject])
    if token:
      request.token = token

    typ = rdfvalue.DataStoreCommand.Command.DELETE_SUBJECT
    self._MakeRequestSyncOrAsync(request, typ, sync)

  def _MakeRequest(self, subjects, attributes, timestamp=None, token=None,
                   limit=None):
    if isinstance(attributes, basestring):
      attributes = [attributes]

    request = rdfvalue.DataStoreRequest(subject=subjects)
    if limit:
      request.limit = limit

    token = token or data_store.default_token
    if token:
      request.token = token

    if timestamp is not None:
      request.timestamp = self.TimestampSpecFromTimestamp(timestamp)

    for attribute in attributes:
      request.values.Append(attribute=attribute)

    return request

  def MultiResolveRegex(self, subjects, attribute_regex,
                        timestamp=None, limit=None, token=None):
    """MultiResolveRegex."""
    typ = rdfvalue.DataStoreCommand.Command.MULTI_RESOLVE_REGEX
    results = {}
    remaining_limit = limit
    for subject in subjects:
      request = self._MakeRequest([subject], attribute_regex,
                                  timestamp=timestamp, token=token,
                                  limit=remaining_limit)

      response = self._MakeSyncRequest(request, typ)

      if response.results:
        result_set = response.results[0]
        values = [(pred, self._Decode(value), ts)
                  for (pred, value, ts) in result_set.payload]
        if limit:
          if len(values) >= remaining_limit:
            results[result_set.subject] = values[:remaining_limit]
            return results.iteritems()
          remaining_limit -= len(values)

        results[result_set.subject] = values

    return results.iteritems()

  def MultiSet(self, subject, values, timestamp=None, replace=True,
               sync=True, to_delete=None, token=None):
    """MultiSet."""
    request = rdfvalue.DataStoreRequest(sync=sync)
    token = token or data_store.default_token
    if token:
      request.token = token

    request.subject.Append(subject)
    now = time.time() * 1000000

    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = now

    to_delete = set(to_delete or [])
    for attribute in to_delete:
      if attribute not in values:
        values[attribute] = [(None, 0)]

    for k, seq in values.items():
      for v in seq:
        if isinstance(v, basestring):
          element_timestamp = timestamp
        else:
          try:
            v, element_timestamp = v
          except (TypeError, ValueError):
            element_timestamp = timestamp

        option = rdfvalue.DataStoreValue.Option.DEFAULT
        if replace or k in to_delete:
          option = rdfvalue.DataStoreValue.Option.REPLACE

        new_value = request.values.Append(
            attribute=utils.SmartUnicode(k),
            option=option)

        if element_timestamp is None:
          element_timestamp = now

        new_value.timestamp = self.TimestampSpecFromTimestamp(
            element_timestamp)

        if v is not None:
          new_value.value.SetValue(v)

    typ = rdfvalue.DataStoreCommand.Command.MULTI_SET
    self._MakeRequestSyncOrAsync(request, typ, sync)

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None,
                   token=None):
    """ResolveMulti."""
    request = self._MakeRequest([subject], attributes, timestamp=timestamp,
                                limit=limit, token=token)

    typ = rdfvalue.DataStoreCommand.Command.RESOLVE_MULTI
    response = self._MakeSyncRequest(request, typ)

    results = []
    for result in response.results:
      for (attribute, value, timestamp) in result.payload:
        results.append((attribute, self._Decode(value), timestamp))
    return results

  def _Decode(self, value):
    """Decodes strings from serialized responses."""
    result = value

    if isinstance(value, (tuple, list)):
      try:
        base64value, one = value
        if one == 1:
          result = base64.decodestring(base64value)
      except (ValueError, binascii.Error):
        pass

    return result

  def Transaction(self, subject, lease_time=None, token=None):
    """We do not support transactions directly."""
    return HTTPTransaction(self, subject, lease_time=lease_time,
                           token=token)

  def LockSubject(self, subject, lease_time, token):
    """Locks a specific subject."""
    request = rdfvalue.DataStoreRequest(subject=[subject])
    specific = rdfvalue.TimestampSpec.Type.SPECIFIC_TIME
    request.timestamp = rdfvalue.TimestampSpec(start=lease_time, type=specific)

    if token:
      request.token = token

    typ = rdfvalue.DataStoreCommand.Command.LOCK_SUBJECT
    response = self._MakeSyncRequest(request, typ)

    if not response.results:
      return None
    result = response.results[0]
    if not result.values:
      return None
    return result.values[0].value.string

  def ExtendSubjectLock(self, subject, transid, lease_time, token):
    """Extends lock of subject."""
    request = rdfvalue.DataStoreRequest(subject=[subject])
    specific = rdfvalue.TimestampSpec.Type.SPECIFIC_TIME
    request.timestamp = rdfvalue.TimestampSpec(start=lease_time, type=specific)
    if token:
      request.token = token
    blob = rdfvalue.DataBlob(string=transid)
    value = rdfvalue.DataStoreValue(value=blob)
    request.values.Append(value)

    typ = rdfvalue.DataStoreCommand.Command.EXTEND_SUBJECT
    response = self._MakeSyncRequest(request, typ)

    if not response.results:
      return None
    result = response.results[0]
    if not result.values:
      return None
    value = result.values[0].value.string
    return transid if transid == value else None

  def UnlockSubject(self, subject, transid, token):
    """Unlocks subject using transaction id."""
    request = rdfvalue.DataStoreRequest(subject=[subject])
    if token:
      request.token = token
    blob = rdfvalue.DataBlob(string=transid)
    value = rdfvalue.DataStoreValue(value=blob)
    request.values.Append(value)

    # We do not care about the server response.
    typ = rdfvalue.DataStoreCommand.Command.UNLOCK_SUBJECT
    self._MakeSyncRequest(request, typ)

    return transid

  def Flush(self):
    if self.inquirer:
      self.inquirer.Flush()

  def CloseConnections(self):
    if self.inquirer:
      self.inquirer.CloseConnections()

  def _ComputeNewSize(self, mapping, new_time):
    self.last_size = 0
    for serv in mapping.servers:
      self.last_size += serv.state.size
    self.last_size_update = new_time

  def Size(self):
    """Get size of data store."""
    now = time.time()
    if now < self.last_size_update + 60:
      return self.last_size
    mapping = self.inquirer.RenewMapping()
    self._ComputeNewSize(mapping, now)
    return self.last_size


class HTTPTransaction(data_store.CommonTransaction):
  """The opensource remote data store transaction object.

  We only ensure that two simultaneous locks can not be held on the
  same subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError. NOTE that it is still possible
  to manipulate the row without a transaction - this is a design feature!

  A lock is considered expired after a certain time.
  """

  lock_creation_lock = threading.Lock()

  locked = False

  def __init__(self, store, subject, lease_time=None, token=None):
    """Ensure we can take a lock on this subject."""
    super(HTTPTransaction, self).__init__(store,
                                          utils.SmartUnicode(subject),
                                          lease_time=lease_time,
                                          token=token)

    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    now = time.time()
    self.transid = store.LockSubject(self.subject, lease_time, self.token)
    if not self.transid:
      raise data_store.TransactionError("Unable to lock subject %s" % subject)
    self.expires = now + lease_time
    self.locked = True

  def UpdateLease(self, duration):
    now = time.time()
    ret = self.store.ExtendSubjectLock(self.subject, self.transid, duration,
                                       self.token)
    if ret != self.transid:
      raise data_store.TransactionError("Unable to update the lease on %s" %
                                        self.subject)
    self.expires = now + duration

  def Abort(self):
    if self.locked:
      self._RemoveLock()

  def Commit(self):
    if self.locked:
      super(HTTPTransaction, self).Commit()
      self._RemoveLock()

  def _RemoveLock(self):
    if self.locked:
      self.store.UnlockSubject(self.subject, self.transid, self.token)
      self.locked = False
