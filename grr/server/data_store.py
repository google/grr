#!/usr/bin/env python
"""The main data store abstraction.

The data store is responsible for storing AFF4 objects permanently. This file
defines the basic interface of the data store, but there is no specific
implementation. Concrete implementations should extend the DataStore class and
provide non-abstract methods.

The data store is essentially an object store. Objects have a subject (a unique
identifying name) and a series of arbitrary attributes. Attributes also have a
name and can only store a number of well defined types.

Some data stores have internal capability to filter and search for objects based
on attribute conditions. Due to the variability of this capability in
implementations, the Filter() class is defined inside the DataStore class
itself. This allows callers to create a data store specific filter
implementation, with no prior knowledge of the concrete implementation.

In order to accommodate for the data store's basic filtering capabilities it is
important to allow the data store to store attribute values using the most
appropriate types.

The currently supported data store storage types are:
  - Integer
  - Bytes
  - String (unicode object).

This means that if one stores an attribute containing an integer, and then
retrieves this attribute, the data store guarantees that an integer is
returned (although it may be stored internally as something else).

More complex types should be encoded into bytes and stored in the data store as
bytes. The data store can then treat the type as an opaque type (and will not be
able to filter it directly).
"""


import abc
import atexit
import logging
import random
import sys
import time

from grr import config
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.server import access_control
from grr.server import blob_store

flags.DEFINE_bool("list_storage", False, "List all storage subsystems present.")

# A global data store handle
DB = None

# There are stub methods that don't return/yield as indicated by the docstring.
# pylint: disable=g-doc-return-or-yield


class Error(stats.CountingExceptionMixin, Exception):
  """Base class for all exceptions in this module."""
  pass


class TimeoutError(Exception):
  """Raised when an access times out."""
  pass


class DBSubjectLockError(Error):
  """Raised when a lock fails to commit."""
  counter = "grr_commit_failure"


# This token will be used by default if no token was provided.
default_token = None


def GetDefaultToken(token):
  """Returns the provided token or the default token.

  Args:
    token: A token or None.

  Raises:
    access_control.UnauthorizedAccess, if no token was provided.
  """
  if token is None:
    token = default_token

  if not isinstance(token, access_control.ACLToken):
    raise access_control.UnauthorizedAccess(
        "Token is not properly specified. It should be an "
        "instance of grr.lib.access_control.ACLToken()")

  return token


class MutationPool(object):
  """A mutation pool.

  This is a pool to group a number of mutations together and apply
  them at the same time. Note that there are no guarantees about the
  atomicity of the mutations. Currently, no mutation will be applied
  before Flush() is called on the pool. If datastore errors occur
  during application, some mutations might be applied while others are
  not.
  """

  def __init__(self, token=None):
    self.token = token
    self.delete_subject_requests = []
    self.set_requests = []
    self.delete_attributes_requests = []

    self.new_notifications = []

  def DeleteSubjects(self, subjects):
    self.delete_subject_requests.extend(subjects)

  def DeleteSubject(self, subject):
    self.delete_subject_requests.append(subject)

  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               to_delete=None):
    self.set_requests.append((subject, values, timestamp, replace, to_delete))

  def Set(self, subject, attribute, value, timestamp=None, replace=True):
    self.MultiSet(
        subject, {attribute: [value]}, timestamp=timestamp, replace=replace)

  def DeleteAttributes(self, subject, attributes, start=None, end=None):
    self.delete_attributes_requests.append((subject, attributes, start, end))

  def Flush(self):
    """Flushing actually applies all the operations in the pool."""
    DB.DeleteSubjects(
        self.delete_subject_requests, token=self.token, sync=False)

    for req in self.delete_attributes_requests:
      subject, attributes, start, end = req
      DB.DeleteAttributes(
          subject,
          attributes,
          start=start,
          end=end,
          token=self.token,
          sync=False)

    for req in self.set_requests:
      subject, values, timestamp, replace, to_delete = req
      DB.MultiSet(
          subject,
          values,
          timestamp=timestamp,
          replace=replace,
          to_delete=to_delete,
          token=self.token,
          sync=False)

    if (self.delete_subject_requests or self.delete_attributes_requests or
        self.set_requests):
      DB.Flush()

    for queue, notifications in self.new_notifications:
      DB.CreateNotifications(queue, notifications, token=self.token)
    self.new_notifications = []

    self.delete_subject_requests = []
    self.set_requests = []
    self.delete_attributes_requests = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Flush()

  def Size(self):
    return (len(self.delete_subject_requests) + len(self.set_requests) +
            len(self.delete_attributes_requests))

  # Notification handling
  def CreateNotifications(self, queue, notifications):
    self.new_notifications.append((queue, notifications))

  def CollectionAddItem(self,
                        collection_id,
                        item,
                        timestamp,
                        suffix=None,
                        replace=True):

    result_subject, timestamp, suffix = DataStore.CollectionMakeURN(
        collection_id, timestamp, suffix=suffix)
    self.Set(
        result_subject,
        DataStore.COLLECTION_ATTRIBUTE,
        item.SerializeToString(),
        timestamp=timestamp,
        replace=replace)
    return result_subject, timestamp, suffix

  def CollectionAddIndex(self, collection_id, index, timestamp, suffix):
    self.Set(
        collection_id,
        DataStore.COLLECTION_INDEX_ATTRIBUTE_PREFIX + "%08x" % index,
        "%06x" % suffix,
        timestamp=timestamp,
        replace=True)

  def CollectionAddStoredTypeIndex(self, collection_id, stored_type):
    self.Set(
        collection_id,
        "%s%s" % (DataStore.COLLECTION_VALUE_TYPE_PREFIX, stored_type),
        1,
        timestamp=0)

  def CollectionDelete(self, collection_id):
    for subject, _, _ in DB.ScanAttribute(
        collection_id.Add("Results"),
        DataStore.COLLECTION_ATTRIBUTE,
        token=self.token):
      self.DeleteSubject(subject)
      if self.Size() > 50000:
        self.Flush()

  def QueueAddItem(self, queue_id, item, timestamp):
    result_subject, timestamp, _ = DataStore.CollectionMakeURN(
        queue_id, timestamp, suffix=None, subpath="Records")
    self.Set(
        result_subject,
        DataStore.COLLECTION_ATTRIBUTE,
        item.SerializeToString(),
        timestamp=timestamp)

  def QueueClaimRecords(self,
                        queue_id,
                        item_rdf_type,
                        limit=10000,
                        timeout="30m",
                        start_time=None,
                        record_filter=lambda x: False,
                        max_filtered=1000):
    """Claims records from a queue. See server/aff4_objects/queue.py."""
    now = rdfvalue.RDFDatetime.Now()
    expiration = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration(timeout)

    after_urn = None
    if start_time:
      after_urn, _, _ = DataStore.CollectionMakeURN(
          queue_id, start_time.AsMicroSecondsFromEpoch(), 0, subpath="Records")
    results = []

    filtered_count = 0

    for subject, values in DB.ScanAttributes(
        queue_id.Add("Records"),
        [DataStore.COLLECTION_ATTRIBUTE, DataStore.QUEUE_LOCK_ATTRIBUTE],
        max_records=4 * limit,
        after_urn=after_urn,
        token=self.token):
      if DataStore.COLLECTION_ATTRIBUTE not in values:
        # Unlikely case, but could happen if, say, a thread called RefreshClaims
        # so late that another thread already deleted the record. Go ahead and
        # clean this up.
        self.DeleteAttributes(subject, [DataStore.QUEUE_LOCK_ATTRIBUTE])
        continue
      if DataStore.QUEUE_LOCK_ATTRIBUTE in values:
        timestamp = rdfvalue.RDFDatetime.FromSerializedString(
            values[DataStore.QUEUE_LOCK_ATTRIBUTE][1])
        if timestamp > now:
          continue
      rdf_value = item_rdf_type.FromSerializedString(
          values[DataStore.COLLECTION_ATTRIBUTE][1])
      if record_filter(rdf_value):
        filtered_count += 1
        if max_filtered and filtered_count >= max_filtered:
          break
        continue
      results.append((subject, rdf_value))
      self.Set(subject, DataStore.QUEUE_LOCK_ATTRIBUTE, expiration)

      filtered_count = 0
      if len(results) >= limit:
        break

    return results

  def QueueRefreshClaims(self, ids, timeout="30m"):
    expiration = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration(timeout)
    for subject in ids:
      self.Set(subject, DataStore.QUEUE_LOCK_ATTRIBUTE, expiration)

  def QueueDeleteRecords(self, ids):
    for i in ids:
      self.DeleteAttributes(
          i, [DataStore.QUEUE_LOCK_ATTRIBUTE, DataStore.COLLECTION_ATTRIBUTE])

  def QueueReleaseRecords(self, ids):
    for i in ids:
      self.DeleteAttributes(i, [DataStore.QUEUE_LOCK_ATTRIBUTE])


class DataStore(object):
  """Abstract database access."""

  __metaclass__ = registry.MetaclassRegistry

  # Constants relating to timestamps.
  ALL_TIMESTAMPS = "ALL_TIMESTAMPS"
  NEWEST_TIMESTAMP = "NEWEST_TIMESTAMP"
  TIMESTAMPS = [ALL_TIMESTAMPS, NEWEST_TIMESTAMP]
  LEASE_ATTRIBUTE = "aff4:lease"

  NOTIFY_PREDICATE_PREFIX = "notify:"
  NOTIFY_PREDICATE_TEMPLATE = NOTIFY_PREDICATE_PREFIX + "%s"

  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08X"

  FLOW_STATUS_TEMPLATE = "flow:status:%08X"
  FLOW_STATUS_PREFIX = "flow:status:"

  FLOW_RESPONSE_PREFIX = "flow:response:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%08X:%08X"

  mutation_pool_cls = MutationPool

  flusher_thread = None
  enable_flusher_thread = True
  monitor_thread = None

  def __init__(self):
    if self.enable_flusher_thread:
      # Start the flusher thread.
      self.flusher_thread = utils.InterruptableThread(
          name="DataStore flusher thread", target=self.Flush, sleep_time=0.5)
      self.flusher_thread.start()
    self.monitor_thread = None

  def InitializeBlobstore(self):
    blobstore_name = config.CONFIG.Get("Blobstore.implementation")
    try:
      cls = blob_store.Blobstore.GetPlugin(blobstore_name)
    except KeyError:
      raise RuntimeError("No blob store %s found." % blobstore_name)

    self.blobstore = cls()

  def InitializeMonitorThread(self):
    """Start the thread that registers the size of the DataStore."""
    if self.monitor_thread:
      return
    self.monitor_thread = utils.InterruptableThread(
        name="DataStore monitoring thread",
        target=self._RegisterSize,
        sleep_time=60)
    self.monitor_thread.start()

  @classmethod
  def SetupTestDB(cls):
    cls.enable_flusher_thread = False

  def ClearTestDB(self):
    pass

  def DestroyTestDB(self):
    pass

  def _RegisterSize(self):
    """Measures size of DataStore."""
    stats.STATS.SetGaugeValue("datastore_size", self.Size())

  def Initialize(self):
    """Initialization of the datastore."""
    self.InitializeBlobstore()

  @abc.abstractmethod
  def DeleteSubject(self, subject, sync=False, token=None):
    """Completely deletes all information about this subject."""

  def DeleteSubjects(self, subjects, sync=False, token=None):
    """Delete multiple subjects at once."""
    for subject in subjects:
      self.DeleteSubject(subject, sync=sync, token=token)

  def Set(self,
          subject,
          attribute,
          value,
          timestamp=None,
          token=None,
          replace=True,
          sync=True):
    """Set a single value for this subject's attribute.

    Args:
      subject: The subject this applies to.
      attribute: Attribute name.
      value: serialized value into one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. If None means now.
      token: An ACL token.
      replace: Bool whether or not to overwrite current records.
      sync: If true we ensure the new values are committed before returning.
    """
    # TODO(user): don't allow subject = None
    self.MultiSet(
        subject, {attribute: [value]},
        timestamp=timestamp,
        token=token,
        replace=replace,
        sync=sync)

  def LockRetryWrapper(self,
                       subject,
                       retrywrap_timeout=1,
                       token=None,
                       retrywrap_max_timeout=10,
                       blocking=True,
                       lease_time=None):
    """Retry a DBSubjectLock until it succeeds.

    Args:
      subject: The subject which the lock applies to.
      retrywrap_timeout: How long to wait before retrying the lock.
      token: An ACL token.
      retrywrap_max_timeout: The maximum time to wait for a retry until we
         raise.
      blocking: If False, raise on first lock failure.
      lease_time: lock lease time in seconds.

    Returns:
      The DBSubjectLock object

    Raises:
      DBSubjectLockError: If the maximum retry count has been reached.
    """
    timeout = 0
    while timeout < retrywrap_max_timeout:
      try:
        return self.DBSubjectLock(subject, token=token, lease_time=lease_time)
      except DBSubjectLockError:
        if not blocking:
          raise
        stats.STATS.IncrementCounter("datastore_retries")
        time.sleep(retrywrap_timeout)
        timeout += retrywrap_timeout

    raise DBSubjectLockError("Retry number exceeded.")

  @abc.abstractmethod
  def DBSubjectLock(self, subject, lease_time=None, token=None):
    """Returns a DBSubjectLock object for a subject.

    This opens a read/write lock to the subject. Any read access to the subject
    will have a consistent view between threads. Any attempts to write to the
    subject must be performed under lock. DBSubjectLocks may fail and raise the
    DBSubjectLockError() exception.

    Users should almost always call LockRetryWrapper() to retry if the lock
    isn't obtained on the first try.

    Args:
        subject: The subject which the lock applies to. Only a
          single subject may be locked in a lock.
        lease_time: The minimum amount of time the lock should remain
          alive.
        token: An ACL token.

    Returns:
        A lock object.
    """

  @abc.abstractmethod
  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               sync=True,
               to_delete=None,
               token=None):
    """Set multiple attributes' values for this subject in one operation.

    Args:
      subject: The subject this applies to.
      values: A dict with keys containing attributes and values, serializations
              to be set. values can be a tuple of (value, timestamp). Value must
              be one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. None means now.
      replace: Bool whether or not to overwrite current records.
      sync: If true we block until the operation completes.
      to_delete: An array of attributes to clear prior to setting.
      token: An ACL token.
    """

  def MultiDeleteAttributes(self,
                            subjects,
                            attributes,
                            start=None,
                            end=None,
                            sync=True,
                            token=None):
    """Remove all specified attributes from a list of subjects.

    Args:
      subjects: The list of subjects that will have these attributes removed.
      attributes: A list of attributes.
      start: A timestamp, attributes older than start will not be deleted.
      end: A timestamp, attributes newer than end will not be deleted.
      sync: If true we block until the operation completes.
      token: An ACL token.
    """
    for subject in subjects:
      self.DeleteAttributes(
          subject, attributes, start=start, end=end, sync=sync, token=token)

  @abc.abstractmethod
  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=True,
                       token=None):
    """Remove all specified attributes.

    Args:
      subject: The subject that will have these attributes removed.
      attributes: A list of attributes.
      start: A timestamp, attributes older than start will not be deleted.
      end: A timestamp, attributes newer than end will not be deleted.
      sync: If true we block until the operation completes.
      token: An ACL token.
    """

  def Resolve(self, subject, attribute, token=None):
    """Retrieve a value set for a subject's attribute.

    This method is easy to use but always gets the latest version of the
    attribute. It is more flexible and efficient to use the other Resolve
    methods.

    Args:
      subject: The subject URN.
      attribute: The attribute.
      token: An ACL token.

    Returns:
      A (value, timestamp in microseconds) stored in the datastore cell, or
      (None, 0). Value will be the same type as originally stored with Set().

    Raises:
      AccessError: if anything goes wrong.
    """
    for _, value, timestamp in self.ResolveMulti(
        subject, [attribute], token=token, timestamp=self.NEWEST_TIMESTAMP):

      # Just return the first one.
      return value, timestamp

    return (None, 0)

  @abc.abstractmethod
  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None,
                         token=None):
    """Generate a set of values matching for subjects' attribute.

    This method provides backwards compatibility for the old method of
    specifying regexes. Each datastore can move to prefix matching by
    overriding this method and ResolvePrefix below.

    Args:
      subjects: A list of subjects.
      attribute_prefix: The attribute prefix.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end). Inclusive of both
          lower and upper bounds.
      limit: The total number of result values to return.
      token: An ACL token.

    Returns:
       A dict keyed by subjects, with values being a list of (attribute, value
       string, timestamp).

       Values with the same attribute (happens when timestamp is not
       NEWEST_TIMESTAMP, but ALL_TIMESTAMPS or time range) are guaranteed
       to be ordered in the decreasing timestamp order.

    Raises:
      AccessError: if anything goes wrong.
    """

  def ResolvePrefix(self,
                    subject,
                    attribute_prefix,
                    timestamp=None,
                    limit=None,
                    token=None):
    """Retrieve a set of value matching for this subject's attribute.

    Args:
      subject: The subject that we will search.
      attribute_prefix: The attribute prefix.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

      limit: The number of results to fetch.
      token: An ACL token.

    Returns:
       A list of (attribute, value string, timestamp).

       Values with the same attribute (happens when timestamp is not
       NEWEST_TIMESTAMP, but ALL_TIMESTAMPS or time range) are guaranteed
       to be ordered in the decreasing timestamp order.

    Raises:
      AccessError: if anything goes wrong.
    """
    for _, values in self.MultiResolvePrefix(
        [subject],
        attribute_prefix,
        timestamp=timestamp,
        token=token,
        limit=limit):
      values.sort(key=lambda a: a[0])
      return values

    return []

  def ResolveMulti(self,
                   subject,
                   attributes,
                   timestamp=None,
                   limit=None,
                   token=None):
    """Resolve multiple attributes for a subject.

    Results may be in unsorted order.

    Args:
      subject: The subject to resolve.
      attributes: The attribute string or list of strings to match. Note this is
          an exact match, not a regex.
      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).
      limit: The maximum total number of results we return.
      token: The security token used in this call.
    """

  def ResolveRow(self, subject, **kw):
    return self.ResolvePrefix(subject, "", **kw)

  @abc.abstractmethod
  def Flush(self):
    """Flushes the DataStore."""

  def Size(self):
    """DataStore size in bytes."""
    return -1

  def __del__(self):
    if self.flusher_thread:
      self.flusher_thread.Stop()
    if self.monitor_thread:
      self.monitor_thread.Stop()
    try:
      self.Flush()
    except Exception:  # pylint: disable=broad-except
      pass

  def _CleanSubjectPrefix(self, subject_prefix):
    subject_prefix = utils.SmartStr(rdfvalue.RDFURN(subject_prefix))
    if subject_prefix[-1] != "/":
      subject_prefix += "/"
    return subject_prefix

  def _CleanAfterURN(self, after_urn, subject_prefix):
    if after_urn:
      after_urn = utils.SmartStr(after_urn)
      if not after_urn.startswith(subject_prefix):
        raise RuntimeError(
            "after_urn \"%s\" does not begin with prefix \"%s\"" %
            (after_urn, subject_prefix))
    return after_urn

  @abc.abstractmethod
  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None,
                     token=None,
                     relaxed_order=False):
    """Scan for values of multiple attributes across a range of rows.

    Scans rows for values of attribute. Reads the most recent value stored in
    each row.

    Args:
      subject_prefix: Subject beginning with this prefix can be scanned. Must
        be an aff4 object and a directory - "/" will be appended if necessary.
        User must have read and query permissions on this directory.

      attributes: A list of attribute names to scan.

      after_urn: If set, only scan records which come after this urn.

      max_records: The maximum number of records to scan.

      token: The security token to authenticate with.

      relaxed_order: By default, ScanAttribute yields results in lexographic
        order. If this is set, a datastore may yield results in a more
        convenient order. For certain datastores this might greatly increase
        the performance of large scans.


    Yields: Pairs (subject, result_dict) where result_dict maps attribute to
      (timestamp, value) pairs.

    """

  def ScanAttribute(self,
                    subject_prefix,
                    attribute,
                    after_urn=None,
                    max_records=None,
                    token=None,
                    relaxed_order=False):
    for s, r in self.ScanAttributes(
        subject_prefix, [attribute],
        after_urn=after_urn,
        max_records=max_records,
        token=token,
        relaxed_order=relaxed_order):
      ts, v = r[attribute]
      yield (s, ts, v)

  def ReadBlob(self, identifier, token=None):
    return self.ReadBlobs([identifier], token=token).values()[0]

  def ReadBlobs(self, identifiers, token=None):
    return self.blobstore.ReadBlobs(identifiers, token=token)

  def StoreBlob(self, content, token=None):
    return self.blobstore.StoreBlob(content, token=token)

  def StoreBlobs(self, contents, token=None):
    return self.blobstore.StoreBlobs(contents, token=token)

  def BlobExists(self, identifier, token=None):
    return self.BlobsExist([identifier], token=token).values()[0]

  def BlobsExist(self, identifiers, token=None):
    return self.blobstore.BlobsExist(identifiers, token=token)

  def DeleteBlob(self, identifier, token=None):
    return self.DeleteBlobs([identifier], token=token)

  def DeleteBlobs(self, identifiers, token=None):
    return self.blobstore.DeleteBlobs(identifiers, token=token)

  def GetMutationPool(self, token=None):
    return self.mutation_pool_cls(token=token)

  def CreateNotifications(self, queue_shard, notifications, token=None):
    values = {}
    for notification in notifications:
      values[self.NOTIFY_PREDICATE_TEMPLATE % notification.session_id] = [
          (notification.SerializeToString(), notification.timestamp)
      ]
    self.MultiSet(queue_shard, values, replace=False, sync=True, token=token)

  def DeleteNotifications(self,
                          queue_shards,
                          session_ids,
                          start,
                          end,
                          token=None):
    attributes = [
        self.NOTIFY_PREDICATE_TEMPLATE % session_id
        for session_id in session_ids
    ]
    self.MultiDeleteAttributes(
        queue_shards, attributes, start=start, end=end, sync=True, token=token)

  def GetNotifications(self, queue_shard, end, limit=10000, token=None):
    for predicate, serialized_notification, ts in self.ResolvePrefix(
        queue_shard,
        self.NOTIFY_PREDICATE_PREFIX,
        timestamp=(0, end),
        token=token,
        limit=limit):
      try:
        # Parse the notification.
        notification = rdf_flows.GrrNotification.FromSerializedString(
            serialized_notification)
      except Exception:  # pylint: disable=broad-except
        logging.exception("Can't unserialize notification, deleting it: "
                          "predicate=%s, ts=%d", predicate, ts)
        self.DeleteAttributes(
            queue_shard,
            [predicate],
            token=token,
            # Make the time range narrow, but be sure to include the needed
            # notification.
            start=ts,
            end=ts,
            sync=True)
        continue

      # Strip the prefix from the predicate to get the session_id.
      session_id = predicate[len(self.NOTIFY_PREDICATE_PREFIX):]
      notification.session_id = session_id
      notification.timestamp = ts

      yield notification

  def GetFlowResponseSubject(self, session_id, request_id):
    """The subject used to carry all the responses for a specific request_id."""
    return session_id.Add("state/request:%08X" % request_id)

  def ReadRequestsAndResponses(self,
                               session_id,
                               timestamp=None,
                               request_limit=None,
                               response_limit=None,
                               token=None):
    """Fetches all Requests and Responses for a given session_id."""
    subject = session_id.Add("state")
    requests = {}

    # Get some requests.
    for predicate, serialized, _ in self.ResolvePrefix(
        subject,
        self.FLOW_REQUEST_PREFIX,
        token=token,
        limit=request_limit,
        timestamp=timestamp):

      request_id = predicate.split(":", 1)[1]
      requests[str(subject.Add(request_id))] = serialized

    # And the responses for them.
    response_data = dict(
        self.MultiResolvePrefix(
            requests.keys(),
            self.FLOW_RESPONSE_PREFIX,
            limit=response_limit,
            token=token,
            timestamp=timestamp))

    for urn, request_data in sorted(requests.items()):
      request = rdf_flows.RequestState.FromSerializedString(request_data)
      responses = []
      for _, serialized, _ in response_data.get(urn, []):
        responses.append(rdf_flows.GrrMessage.FromSerializedString(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

  def ReadCompletedRequests(self,
                            session_id,
                            timestamp=None,
                            limit=None,
                            token=None):
    """Fetches all the requests with a status message queued for them."""
    subject = session_id.Add("state")
    requests = {}
    status = {}

    for predicate, serialized, _ in self.ResolvePrefix(
        subject, [self.FLOW_REQUEST_PREFIX, self.FLOW_STATUS_PREFIX],
        token=token,
        limit=limit,
        timestamp=timestamp):

      parts = predicate.split(":", 3)
      request_id = parts[2]
      if parts[1] == "status":
        status[request_id] = serialized
      else:
        requests[request_id] = serialized

    for request_id, serialized in sorted(requests.items()):
      if request_id in status:
        yield (rdf_flows.RequestState.FromSerializedString(serialized),
               rdf_flows.GrrMessage.FromSerializedString(status[request_id]))

  def ReadResponsesForRequestId(self,
                                session_id,
                                request_id,
                                timestamp=None,
                                token=None):
    """Reads responses for one request.

    Args:
      session_id: The session id to use.
      request_id: The id of the request.
      timestamp: A timestamp as used in the data store.
      token: A data store token.

    Yields:
      fetched responses for the request
    """
    request = rdf_flows.RequestState(id=request_id, session_id=session_id)
    for _, responses in self.ReadResponses(
        [request], timestamp=timestamp, token=token):
      return responses

  def ReadResponses(self, request_list, timestamp=None, token=None):
    """Reads responses for multiple requests at the same time.

    Args:
      request_list: The list of requests the responses should be fetched for.
      timestamp: A timestamp as used in the data store.
      token: A data store token.

    Yields:
      tuples (request, lists of fetched responses for the request)
    """

    response_subjects = {}
    for request in request_list:
      response_subject = self.GetFlowResponseSubject(request.session_id,
                                                     request.id)
      response_subjects[response_subject] = request

    response_data = dict(
        self.MultiResolvePrefix(
            response_subjects,
            self.FLOW_RESPONSE_PREFIX,
            token=token,
            timestamp=timestamp))

    for response_urn, request in sorted(response_subjects.items()):
      responses = []
      for _, serialized, _ in response_data.get(response_urn, []):
        responses.append(rdf_flows.GrrMessage.FromSerializedString(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

  def StoreRequestsAndResponses(self,
                                new_requests=None,
                                new_responses=None,
                                requests_to_delete=None,
                                token=None):
    """Stores new flow requests and responses to the data store.

    Args:
      new_requests: A list of tuples (request, timestamp) to store in the
                    data store.
      new_responses: A list of tuples (response, timestamp) to store in the
                     data store.
      requests_to_delete: A list of requests that should be deleted from the
                          data store.
      token: A data store token.
    """
    to_write = {}
    if new_requests is not None:
      for request, timestamp in new_requests:
        subject = request.session_id.Add("state")
        queue = to_write.setdefault(subject, {})
        queue.setdefault(self.FLOW_REQUEST_TEMPLATE % request.id, []).append(
            (request.SerializeToString(), timestamp))

    if new_responses is not None:
      for response, timestamp in new_responses:
        # Status messages cause their requests to be marked as complete. This
        # allows us to quickly enumerate all the completed requests - it is
        # essentially an index for completed requests.
        if response.type == rdf_flows.GrrMessage.Type.STATUS:
          subject = response.session_id.Add("state")
          attribute = self.FLOW_STATUS_TEMPLATE % response.request_id
          to_write.setdefault(subject, {}).setdefault(attribute, []).append(
              (response.SerializeToString(), timestamp))

        subject = self.GetFlowResponseSubject(response.session_id,
                                              response.request_id)
        attribute = self.FLOW_RESPONSE_TEMPLATE % (response.request_id,
                                                   response.response_id)
        to_write.setdefault(subject, {}).setdefault(attribute, []).append(
            (response.SerializeToString(), timestamp))

    to_delete = {}
    if requests_to_delete is not None:
      for request in requests_to_delete:
        queue = to_delete.setdefault(request.session_id.Add("state"), [])
        queue.append(self.FLOW_REQUEST_TEMPLATE % request.id)
        queue.append(self.FLOW_STATUS_TEMPLATE % request.id)

    for subject in set(to_write) | set(to_delete):
      self.MultiSet(
          subject,
          to_write.get(subject, {}),
          to_delete=to_delete.get(subject, []),
          sync=True,
          token=token)

  def CheckRequestsForCompletion(self, requests, token=None):
    """Checks if there is a status message queued for a number of requests."""

    subjects = [r.session_id.Add("state") for r in requests]

    statuses_found = {}

    for subject, result in self.MultiResolvePrefix(
        subjects, self.FLOW_STATUS_PREFIX, token=token):
      for predicate, _, _ in result:
        request_nr = int(predicate.split(":")[-1], 16)
        statuses_found.setdefault(subject, set()).add(request_nr)

    status_available = set()
    for r in requests:
      if r.request_id in statuses_found.get(r.session_id.Add("state"), set()):
        status_available.add(r)

    return status_available

  def DeleteRequest(self, request, token=None):
    return self.DeleteRequests([request], token=token)

  def DeleteRequests(self, requests, token=None):
    # Efficiently drop all responses to this request.
    subjects = [
        self.GetFlowResponseSubject(request.session_id, request.id)
        for request in requests
    ]

    self.DeleteSubjects(subjects, sync=True, token=token)

  def DestroyFlowStates(self, session_id):
    return self.MultiDestroyFlowStates([session_id])

  def MultiDestroyFlowStates(self, session_ids, request_limit=None, token=None):
    """Deletes all requests and responses for the given flows.

    Args:
      session_ids: A lists of flows to destroy.
      request_limit: A limit on the number of requests to delete.
      token: A data store token.

    Returns:
      A list of requests that were deleted.
    """

    subjects = [session_id.Add("state") for session_id in session_ids]
    to_delete = []
    deleted_requests = []

    for subject, values in self.MultiResolvePrefix(
        subjects, self.FLOW_REQUEST_PREFIX, token=token, limit=request_limit):
      for _, serialized, _ in values:

        request = rdf_flows.RequestState.FromSerializedString(serialized)
        deleted_requests.append(request)

        # Drop all responses to this request.
        response_subject = self.GetFlowResponseSubject(request.session_id,
                                                       request.id)
        to_delete.append(response_subject)

      # Mark the request itself for deletion.
      to_delete.append(subject)

    # Drop them all at once.
    self.DeleteSubjects(to_delete, sync=True, token=token)
    return deleted_requests

  def DeleteWellKnownFlowResponses(self, session_id, responses, token=None):
    subject = session_id.Add("state/request:00000000")
    predicates = []
    for response in responses:
      predicates.append(self.FLOW_RESPONSE_TEMPLATE % (response.request_id,
                                                       response.response_id))

    self.DeleteAttributes(subject, predicates, sync=True, start=0, token=token)

  def FetchResponsesForWellKnownFlow(self,
                                     session_id,
                                     response_limit,
                                     timestamp,
                                     token=None):
    subject = session_id.Add("state/request:00000000")

    for _, serialized, _ in sorted(
        self.ResolvePrefix(
            subject,
            self.FLOW_RESPONSE_PREFIX,
            token=token,
            limit=response_limit,
            timestamp=timestamp)):
      yield rdf_flows.GrrMessage.FromSerializedString(serialized)

  # Index handling.

  _INDEX_PREFIX = "kw_index:"
  _INDEX_PREFIX_LEN = len(_INDEX_PREFIX)
  _INDEX_COLUMN_FORMAT = _INDEX_PREFIX + "%s"

  def _KeywordToURN(self, urn, keyword):
    return urn.Add(keyword)

  def IndexAddKeywordsForName(self, index_urn, name, keywords, token=None):
    timestamp = rdfvalue.RDFDatetime.Now().AsMicroSecondsFromEpoch()
    with self.GetMutationPool(token=token) as mutation_pool:
      for keyword in set(keywords):
        mutation_pool.Set(
            self._KeywordToURN(index_urn, keyword),
            self._INDEX_COLUMN_FORMAT % name,
            "",
            timestamp=timestamp)

  def IndexRemoveKeywordsForName(self, index_urn, name, keywords, token=None):
    with self.GetMutationPool(token=token) as mutation_pool:
      for keyword in set(keywords):
        mutation_pool.DeleteAttributes(
            self._KeywordToURN(index_urn, keyword),
            [self._INDEX_COLUMN_FORMAT % name])

  def IndexReadPostingLists(self,
                            index_urn,
                            keywords,
                            start_time,
                            end_time,
                            last_seen_map=None,
                            token=None):
    """Finds all objects associated with any of the keywords.

    Args:
      index_urn: The base urn of the index.
      keywords: A collection of keywords that we are interested in.
      start_time: Only considers keywords added at or after this point in time.
      end_time: Only considers keywords at or before this point in time.
      last_seen_map: If present, is treated as a dict and populated to map pairs
        (keyword, name) to the timestamp of the latest connection found.
      token: A data store token.
    Returns:
      A dict mapping each keyword to a set of relevant names.
    """
    keyword_urns = {self._KeywordToURN(index_urn, k): k for k in keywords}
    result = {}
    for kw in keywords:
      result[kw] = set()

    for keyword_urn, value in self.MultiResolvePrefix(
        keyword_urns.keys(),
        self._INDEX_PREFIX,
        timestamp=(start_time, end_time + 1),
        token=token):
      for column, _, ts in value:
        kw = keyword_urns[keyword_urn]
        name = column[self._INDEX_PREFIX_LEN:]
        result[kw].add(name)
        if last_seen_map is not None:
          last_seen_map[(kw, name)] = max(last_seen_map.get((kw, name), -1), ts)

    return result

  # The largest possible suffix - maximum value expressible by 6 hex digits.
  COLLECTION_MAX_SUFFIX = 0xffffff

  # The attribute (column) where we store value.
  COLLECTION_ATTRIBUTE = "aff4:sequential_value"

  # An attribute name of the form "index:sc_<i>" at timestamp <t> indicates that
  # the item with record number i was stored at timestamp t. The timestamp
  # suffix is stored as the value.
  COLLECTION_INDEX_ATTRIBUTE_PREFIX = "index:sc_"

  # The attribute prefix to use when storing the index of stored types
  # for multi type collections.
  COLLECTION_VALUE_TYPE_PREFIX = "aff4:value_type_"

  # The attribute where we store locks. A lock is a timestamp indicating when
  # the lock becomes stale at the record may be claimed again.
  QUEUE_LOCK_ATTRIBUTE = "aff4:lease"

  @classmethod
  def CollectionMakeURN(cls, urn, timestamp, suffix=None, subpath="Results"):
    if suffix is None:
      # Disallow 0 so that subtracting 1 from a normal suffix doesn't require
      # special handling.
      suffix = random.randint(1, DataStore.COLLECTION_MAX_SUFFIX)
    result_urn = urn.Add(subpath).Add("%016x.%06x" % (timestamp, suffix))
    return (result_urn, timestamp, suffix)

  def CollectionScanItems(self,
                          collection_id,
                          rdf_type,
                          after_timestamp=None,
                          after_suffix=None,
                          limit=None,
                          token=None):
    after_urn = None
    if after_timestamp:
      after_urn = utils.SmartStr(
          self.CollectionMakeURN(
              collection_id,
              after_timestamp,
              suffix=after_suffix or self.COLLECTION_MAX_SUFFIX)[0])

    for subject, timestamp, serialized_rdf_value in self.ScanAttribute(
        collection_id.Add("Results"),
        self.COLLECTION_ATTRIBUTE,
        after_urn=after_urn,
        max_records=limit,
        token=token):
      item = rdf_type.FromSerializedString(serialized_rdf_value)
      item.age = timestamp
      # The urn is timestamp.suffix where suffix is 6 hex digits.
      suffix = int(subject[-6:], 16)
      yield (item, timestamp, suffix)

  def CollectionReadIndex(self, collection_id, token=None):
    """Reads all index entries for the given collection.

    Args:
      collection_id: ID of the collection for which the indexes should be
                     retrieved.
      token: Datastore token.

    Yields:
      Tuples (index, ts, suffix).
    """
    for (attr, value, ts) in self.ResolvePrefix(
        collection_id, self.COLLECTION_INDEX_ATTRIBUTE_PREFIX, token=token):
      i = int(attr[len(self.COLLECTION_INDEX_ATTRIBUTE_PREFIX):], 16)
      yield (i, ts, int(value, 16))

  def CollectionReadStoredTypes(self, collection_id, token=None):
    for attribute, _, _ in self.ResolveRow(collection_id, token=token):
      if attribute.startswith(self.COLLECTION_VALUE_TYPE_PREFIX):
        yield attribute[len(self.COLLECTION_VALUE_TYPE_PREFIX):]


class DBSubjectLock(object):
  """Provide a simple subject lock using the database.

  This class should not be used directly. Its only safe to use via the
  DataStore.LockRetryWrapper() above which implements correct backoff and
  retry behavior.
  """

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, data_store, subject, lease_time=None, token=None):
    """Obtain the subject lock for lease_time seconds.

    This is never called directly but produced from the
    DataStore.LockedSubject() factory.

    Args:
      data_store: A data_store handler.
      subject: The name of a subject to lock.
      lease_time: The minimum length of time the lock will remain valid in
        seconds. Note this will be converted to usec for storage.
      token: An ACL token which applies to all methods in this lock.
    Raises:
      RuntimeError: No lease time was provided.
    """
    self.subject = utils.SmartStr(subject)
    self.store = data_store
    self.token = token
    # expires should be stored as usec
    self.expires = None
    self.locked = False
    if lease_time is None:
      raise RuntimeError("Trying to lock without a lease time.")
    self._Acquire(lease_time)
    self.lease_time = lease_time

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Release()

  def _Acquire(self, lease_time):
    raise NotImplementedError

  def Release(self):
    raise NotImplementedError

  def UpdateLease(self, duration):
    """Update the lock lease time by at least the number of seconds.

    Note that not all data stores implement timed locks. This method is
    only useful for data stores which expire a lock after some time.

    Args:
      duration: The number of seconds to extend the lock lease.
    """
    raise NotImplementedError

  def CheckLease(self):
    """Return the time remaining on the lock in seconds."""
    if not self.expires:
      return 0
    return max(0, self.expires / 1e6 - time.time())

  def __del__(self):
    try:
      self.Release()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass


class DataStoreInit(registry.InitHook):
  """Initialize the data store.

  Depends on the stats module being initialized.
  """

  def _ListStorageOptions(self):
    for name, cls in DataStore.classes.items():
      print "%s\t\t%s" % (name, cls.__doc__)

  def Run(self):
    """Initialize the data_store."""
    global DB  # pylint: disable=global-statement

    if flags.FLAGS.list_storage:
      self._ListStorageOptions()
      sys.exit(0)

    try:
      cls = DataStore.GetPlugin(config.CONFIG["Datastore.implementation"])
    except KeyError:
      msg = ("No Storage System %s found." %
             config.CONFIG["Datastore.implementation"])
      print msg
      print "Available options:"
      self._ListStorageOptions()
      raise RuntimeError(msg)

    DB = cls()  # pylint: disable=g-bad-name
    DB.Initialize()
    atexit.register(DB.Flush)
    monitor_port = config.CONFIG["Monitoring.http_port"]
    if monitor_port != 0:
      stats.STATS.RegisterGaugeMetric(
          "datastore_size",
          int,
          docstring="Size of data store in bytes",
          units="BYTES")
      DB.InitializeMonitorThread()

  def RunOnce(self):
    """Initialize some Varz."""
    stats.STATS.RegisterCounterMetric("grr_commit_failure")
    stats.STATS.RegisterCounterMetric("datastore_retries")
