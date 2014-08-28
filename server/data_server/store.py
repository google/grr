#!/usr/bin/env python
"""Data store proxy for a data server."""


import base64
import functools
import os
import threading
import time
import uuid

import logging

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils

from grr.lib.data_stores import common


BASE_MAP_SUBJECT = "servers_map"
MAP_SUBJECT = "aff4:/" + BASE_MAP_SUBJECT


def RPCWrapper(f):
  """A decorator for converting exceptions to rpc status messages.

  This decorator should be inserted below the rpcserver.Handler call to prevent
  normal exceptions from reaching the RCP layer. These expected exceptions are
  then encoded into the status message of the response.

  Args:
    f: The function to wrap.

  Returns:
    A decorator function.
  """

  @functools.wraps(f)
  def Wrapper(self, request):
    """Wrap the function can catch exceptions, converting them to status."""
    failed = True
    response = rdfvalue.DataStoreResponse()
    response.status = rdfvalue.DataStoreResponse.Status.OK

    try:
      f(self, request, response)
      failed = False
    except access_control.UnauthorizedAccess as e:
      # Attach a copy of the request to the response so the caller can tell why
      # we failed the request.
      response.Clear()
      response.request = request

      response.status = rdfvalue.DataStoreResponse.Status.AUTHORIZATION_DENIED
      if e.subject:
        response.failed_subject = utils.SmartUnicode(e.subject)

      response.status_desc = utils.SmartUnicode(e)

    except data_store.Error as e:
      # Attach a copy of the request to the response so the caller can tell why
      # we failed the request.
      response.Clear()
      response.request = request

      response.status = rdfvalue.DataStoreResponse.Status.DATA_STORE_ERROR
      response.status_desc = utils.SmartUnicode(e)

    except access_control.ExpiryError as e:
      # Attach a copy of the request to the response so the caller can tell why
      # we failed the request.
      response.Clear()
      response.request = request

      response.status = rdfvalue.DataStoreResponse.Status.TIMEOUT_ERROR
      response.status_desc = utils.SmartUnicode(e)

    if failed:
      # Limit the size of the error report since it can be quite large.
      logging.info("Failed: %s", utils.SmartStr(response)[:1000])
    serialized_response = response.SerializeToString()
    return serialized_response

  return Wrapper


class DataStoreService(object):
  """Class that responds to DataStore requests."""

  def __init__(self, db):
    self.db = db
    self.transaction_lock = threading.Lock()
    self.transactions = {}

  # Every service method must write to the response argument.
  # The response will then be serialized to a string.

  @RPCWrapper
  def MultiSet(self, request, unused_response):
    """Set multiple attributes for a given subject at once."""

    values = {}
    to_delete = set()

    for value in request.values:
      if value.option == rdfvalue.DataStoreValue.Option.REPLACE:
        to_delete.add(value.predicate)

      timestamp = self.FromTimestampSpec(request.timestamp)
      if value.HasField("value"):
        if value.HasField("timestamp"):
          timestamp = self.FromTimestampSpec(value.timestamp)

        values.setdefault(value.predicate, []).append(
            (value.value.GetValue(), timestamp))

    self.db.MultiSet(request.subject[0], values, to_delete=to_delete,
                     sync=request.sync, replace=False,
                     token=request.token)

  @RPCWrapper
  def ResolveMulti(self, request, response):
    """Resolve multiple attributes for a given subject at once."""
    predicate_regex = []

    for v in request.values:
      predicate_regex.append(v.predicate)

    timestamp = self.FromTimestampSpec(request.timestamp)
    subject = request.subject[0]

    values = self.db.ResolveMulti(
        subject, predicate_regex, timestamp=timestamp,
        token=request.token)

    response.results.Append(
        subject=subject,
        payload=[(predicate, self._Encode(value), int(ts))
                 for (predicate, value, ts) in values if value])

  @RPCWrapper
  def MultiResolveRegex(self, request, response):
    """Resolve multiple attributes for a given subject at once."""
    predicate_regex = [utils.SmartUnicode(v.predicate) for v in request.values]

    timestamp = self.FromTimestampSpec(request.timestamp)
    subjects = list(request.subject)

    for subject, values in self.db.MultiResolveRegex(
        subjects, predicate_regex, timestamp=timestamp,
        token=request.token,
        limit=request.limit):
      response.results.Append(
          subject=subject,
          payload=[(utils.SmartStr(predicate), self._Encode(value), int(ts))
                   for (predicate, value, ts) in values])

  @RPCWrapper
  def DeleteAttributes(self, request, unused_response):
    """Delete attributes from a given subject."""
    timestamp = self.FromTimestampSpec(request.timestamp)
    subject = request.subject[0]
    sync = request.sync
    token = request.token
    attributes = [v.predicate for v in request.values]
    start, end = timestamp  # pylint: disable=unpacking-non-sequence
    self.db.DeleteAttributes(subject, attributes, start=start, end=end,
                             token=token, sync=sync)

  @RPCWrapper
  def DeleteAttributesRegex(self, request, unused_response):
    subject = request.subject[0]
    token = request.token
    attr_regexes = [v.predicate for v in request.values]
    self.db.DeleteAttributesRegex(subject, attr_regexes, token=token)

  @RPCWrapper
  def DeleteSubject(self, request, unused_response):
    subject = request.subject[0]
    token = request.token
    self.db.DeleteSubject(subject, token=token)

  def _NewTransaction(self, subject, duration, response):
    transid = utils.SmartStr(uuid.uuid4())
    now = time.time()
    self.transactions[subject] = (transid, now + duration)
    self._AddTransactionId(response, subject, transid)

  def _AddTransactionId(self, response, subject, transid):
    blob = rdfvalue.DataBlob(string=transid)
    value = rdfvalue.DataStoreValue(value=blob)
    response.results.Append(subject=subject, values=[value])

  @RPCWrapper
  def LockSubject(self, request, response):
    duration = self.FromTimestampSpec(request.timestamp)
    if not request.subject:
      # No return value.
      return
    subject = request.subject[0]
    with self.transaction_lock:
      # Check if there is a transaction.
      try:
        _, lease = self.transactions[subject]
        if time.time() > lease:
          self._NewTransaction(subject, duration, response)
        else:
          # Failed to get transaction.
          # Do not need to do anything
          pass
      except KeyError:
        return self._NewTransaction(subject, duration, response)

  def _GetTransactionId(self, request):
    return request.values[0].value.string

  @RPCWrapper
  def ExtendSubject(self, request, response):
    duration = self.FromTimestampSpec(request.timestamp)
    if not request.subject or not request.values:
      # No return value.
      return
    subject = request.subject[0]
    transid = self._GetTransactionId(request)
    with self.transaction_lock:
      # Check if there is a transaction.
      try:
        current, _ = self.transactions[subject]
        if transid != current:
          # Invalid transaction ID.
          return
        self.transactions[subject] = (transid, time.time() + duration)
        # Add return value to response.
        self._AddTransactionId(response, subject, transid)
      except KeyError:
        # Invalid transaction ID.
        pass

  @RPCWrapper
  def UnlockSubject(self, request, response):
    if not request.subject or not request.values:
      return
    subject = request.subject[0]
    transid = self._GetTransactionId(request)
    with self.transaction_lock:
      # Check if there is a transaction.
      try:
        current, _ = self.transactions[subject]
        if transid != current:
          # Invalid transaction ID.
          return
        del self.transactions[subject]
        # Add return value to response.
        self._AddTransactionId(response, subject, transid)
      except KeyError:
        # Invalid transaction ID.
        pass

  def FromTimestampSpec(self, timestamp):
    """Converts constants from TimestampSpec() to the datastore ones."""
    if timestamp.type == timestamp.Type.NEWEST_TIMESTAMP:
      return self.db.NEWEST_TIMESTAMP

    if timestamp.type == timestamp.Type.ALL_TIMESTAMPS:
      return self.db.ALL_TIMESTAMPS

    if timestamp.type == timestamp.Type.RANGED_TIME:
      return (int(timestamp.start), int(timestamp.end))

    if timestamp.type == timestamp.Type.SPECIFIC_TIME:
      return int(timestamp.start)

  def _Encode(self, value):
    if isinstance(value, str):
      return [base64.encodestring(value), 1]
    return value

  def Size(self):
    return self.db.Size()

  def LoadServerMapping(self):
    """Retrieve server mapping from database."""
    mapping_str, _ = self.db.Resolve(MAP_SUBJECT, "value")
    if not mapping_str:
      return None
    mapping = rdfvalue.DataServerMapping(mapping_str)
    return mapping

  def SaveServerMapping(self, mapping):
    self.db.MultiSet(MAP_SUBJECT, {"value": mapping})

  def GetLocation(self):
    return self.db.Location()

  def GetComponentInformation(self):
    """Return number of components and average size per component."""
    loc = self.GetLocation()
    if not os.path.exists(loc):
      return 0, 0
    if not os.path.isdir(loc):
      return 0, 0
    size, files = common.DatabaseDirectorySize(loc, self.db.FileExtension())
    if files:
      return files, int(float(size)/float(files))
    else:
      return 0, 0
