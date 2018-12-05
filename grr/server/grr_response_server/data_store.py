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
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import abc
import atexit
import collections
import logging
import random
import sys
import time


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import iterkeys
from future.utils import with_metaclass

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils
from grr_response_server import access_control
from grr_response_server import blob_store
from grr_response_server import db
from grr_response_server import stats_values
from grr_response_server.databases import registry_init
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner

flags.DEFINE_bool("list_storage", False, "List all storage subsystems present.")

# A global data store handle
DB = None
# The global relational db handle.
REL_DB = None
# The global blobstore handle.
BLOBS = None


def RelationalDBWriteEnabled():
  """Returns True if write to a relational database are enabled."""
  return bool(REL_DB)


def RelationalDBReadEnabled(category=None):
  """Returns True if reads from a relational database are enabled.

  Args:
    category: string identifying the category. Useful when a large piece of
      functionality gets converted to REL_DB iteratively, step by step and when
      enabling already implemented steps may break the rest of the system. For
      example - reading single approvals is implemented, but listing them is
      not.

  Returns:
    True if reads are enabled, False otherwise.
  """
  flag = config.CONFIG["Database.useForReads"]

  if category:
    return flag and config.CONFIG["Database.useForReads.%s" % category]

  return flag


def RelationalDBFlowsEnabled():
  """Returns True if relational flows are enabled.

  Even with RelationalDBReadEnabled() returning True, this can be False.

  Returns: True if relational flows are enabled.

  """
  return config.CONFIG["Database.useRelationalFlows"]


def AFF4Enabled():
  return config.CONFIG["Database.aff4_enabled"]


# There are stub methods that don't return/yield as indicated by the docstring.
# pylint: disable=g-doc-return-or-yield


class Error(stats_utils.CountingExceptionMixin, Exception):
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
    access_control.UnauthorizedAccess: no token was provided.
  """
  if token is None:
    token = default_token

  if not isinstance(token, access_control.ACLToken):
    raise access_control.UnauthorizedAccess(
        "Token is not properly specified. It should be an "
        "instance of grr.lib.access_control.ACLToken()")

  return token


# This represents a record stored in a queue/collection. The attributes are:
# queue_id:  Id of the queue this record is stored in.
# timestamp: Timestamp this record was stored at.
# suffix:    A random number that is used to differentiate between records that
#            have the same timestamp.
# subpath:   Queues store records in different subpaths, this attribute
#            specifies which one was used to store the record.
# value:     The actual data that the record contains.

Record = collections.namedtuple(
    "Record", ["queue_id", "timestamp", "suffix", "subpath", "value"])


class MutationPool(object):
  """A mutation pool.

  This is a pool to group a number of mutations together and apply
  them at the same time. Note that there are no guarantees about the
  atomicity of the mutations. Currently, no mutation will be applied
  before Flush() is called on the pool. If datastore errors occur
  during application, some mutations might be applied while others are
  not.
  """

  def __init__(self):
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
    DB.DeleteSubjects(self.delete_subject_requests, sync=False)

    for req in self.delete_attributes_requests:
      subject, attributes, start, end = req
      DB.DeleteAttributes(subject, attributes, start=start, end=end, sync=False)

    for req in self.set_requests:
      subject, values, timestamp, replace, to_delete = req
      DB.MultiSet(
          subject,
          values,
          timestamp=timestamp,
          replace=replace,
          to_delete=to_delete,
          sync=False)

    if (self.delete_subject_requests or self.delete_attributes_requests or
        self.set_requests):
      DB.Flush()

    for queue, notifications in self.new_notifications:
      DB.CreateNotifications(queue, notifications)
    self.new_notifications = []

    self.delete_subject_requests = []
    self.set_requests = []
    self.delete_attributes_requests = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    self.Flush()

  def Size(self):
    return (len(self.delete_subject_requests) + len(self.set_requests) + len(
        self.delete_attributes_requests))

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
        unicode(collection_id.Add("Results")), DataStore.COLLECTION_ATTRIBUTE):
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
          queue_id, start_time.AsMicrosecondsSinceEpoch(), 0, subpath="Records")
    results = []

    filtered_count = 0

    for subject, values in DB.ScanAttributes(
        unicode(queue_id.Add("Records")),
        [DataStore.COLLECTION_ATTRIBUTE, DataStore.QUEUE_LOCK_ATTRIBUTE],
        max_records=4 * limit,
        after_urn=after_urn):
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
      results.append(
          Record(
              queue_id=queue_id,
              timestamp=values[DataStore.COLLECTION_ATTRIBUTE][0],
              suffix=int(subject[-6:], 16),
              subpath="Records",
              value=rdf_value))
      self.Set(subject, DataStore.QUEUE_LOCK_ATTRIBUTE, expiration)

      filtered_count = 0
      if len(results) >= limit:
        break

    return results

  def QueueRefreshClaims(self, records, timeout="30m"):
    expiration = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration(timeout)
    for record in records:
      subject, _, _ = DataStore.CollectionMakeURN(
          record.queue_id, record.timestamp, record.suffix, record.subpath)
      self.Set(subject, DataStore.QUEUE_LOCK_ATTRIBUTE, expiration)

  def QueueDeleteRecords(self, records):
    for record in records:
      subject, _, _ = DataStore.CollectionMakeURN(
          record.queue_id, record.timestamp, record.suffix, record.subpath)

      self.DeleteAttributes(
          subject,
          [DataStore.QUEUE_LOCK_ATTRIBUTE, DataStore.COLLECTION_ATTRIBUTE])

  def QueueReleaseRecords(self, records):
    for record in records:
      subject, _, _ = DataStore.CollectionMakeURN(
          record.queue_id, record.timestamp, record.suffix, record.subpath)
      self.DeleteAttributes(subject, [DataStore.QUEUE_LOCK_ATTRIBUTE])

  def QueueDeleteTasks(self, queue, tasks):
    """Removes the given tasks from the queue."""
    predicates = []
    for task in tasks:
      task_id = getattr(task, "task_id", None) or int(task)
      predicates.append(DataStore.QueueTaskIdToColumn(task_id))
    self.DeleteAttributes(queue, predicates)

  def QueueScheduleTasks(self, tasks, timestamp):
    for queue, queued_tasks in iteritems(
        collection.Group(tasks, lambda x: x.queue)):
      to_schedule = {}
      for task in queued_tasks:
        to_schedule[DataStore.QueueTaskIdToColumn(
            task.task_id)] = [task.SerializeToString()]
      self.MultiSet(queue, to_schedule, timestamp=timestamp)

  def QueueQueryAndOwn(self, queue, lease_seconds, limit, timestamp):
    """Returns a list of Tasks leased for a certain time.

    Args:
      queue: The queue to query from.
      lease_seconds: The tasks will be leased for this long.
      limit: Number of values to fetch.
      timestamp: Range of times for consideration.

    Returns:
        A list of GrrMessage() objects leased.
    """
    # Do the real work in a transaction
    try:
      lock = DB.LockRetryWrapper(queue, lease_time=lease_seconds)
      return self._QueueQueryAndOwn(
          lock.subject,
          lease_seconds=lease_seconds,
          limit=limit,
          timestamp=timestamp)
    except DBSubjectLockError:
      # This exception just means that we could not obtain the lock on the queue
      # so we just return an empty list, let the worker sleep and come back to
      # fetch more tasks.
      return []
    except Error as e:
      logging.warning("Datastore exception: %s", e)
      return []

  def _QueueQueryAndOwn(self,
                        subject,
                        lease_seconds=100,
                        limit=1,
                        timestamp=None):
    """Business logic helper for QueueQueryAndOwn()."""
    tasks = []

    lease = int(lease_seconds * 1e6)

    # Only grab attributes with timestamps in the past.
    delete_attrs = set()
    serialized_tasks_dict = {}
    for predicate, task, timestamp in DB.ResolvePrefix(
        subject,
        DataStore.QUEUE_TASK_PREDICATE_PREFIX,
        timestamp=(0, timestamp or rdfvalue.RDFDatetime.Now())):
      task = rdf_flows.GrrMessage.FromSerializedString(task)
      task.leased_until = timestamp
      task.leased_by = utils.ProcessIdString()
      # Decrement the ttl
      task.task_ttl -= 1
      if task.task_ttl <= 0:
        # Remove the task if ttl is exhausted.
        delete_attrs.add(predicate)
        stats_collector_instance.Get().IncrementCounter(
            "grr_task_ttl_expired_count")
      else:
        if task.task_ttl != rdf_flows.GrrMessage.max_ttl - 1:
          stats_collector_instance.Get().IncrementCounter(
              "grr_task_retransmission_count")

        serialized_tasks_dict.setdefault(predicate,
                                         []).append(task.SerializeToString())
        tasks.append(task)
        if len(tasks) >= limit:
          break

    if delete_attrs or serialized_tasks_dict:
      # Update the timestamp on claimed tasks to be in the future and decrement
      # their TTLs, delete tasks with expired ttls.
      self.MultiSet(
          subject,
          serialized_tasks_dict,
          replace=True,
          timestamp=int(time.time() * 1e6) + lease,
          to_delete=delete_attrs)

    if delete_attrs:
      logging.info("TTL exceeded for %d messages on queue %s",
                   len(delete_attrs), subject)
    return tasks

  def StatsWriteMetrics(self, subject, timestamp=None):
    """Writes stats for the given metrics to the data-store."""
    to_set = {}
    metric_metadata = stats_collector_instance.Get().GetAllMetricsMetadata()
    for name, metadata in iteritems(metric_metadata):
      if metadata.fields_defs:
        for fields_values in stats_collector_instance.Get().GetMetricFields(
            name):
          value = stats_collector_instance.Get().GetMetricValue(
              name, fields=fields_values)

          store_value = stats_values.StatsStoreValue()
          store_fields_values = []
          for field_def, field_value in zip(metadata.fields_defs,
                                            fields_values):
            store_field_value = stats_values.StatsStoreFieldValue()
            store_field_value.SetValue(field_value, field_def.field_type)
            store_fields_values.append(store_field_value)

          store_value.fields_values = store_fields_values
          store_value.SetValue(value, metadata.value_type)

          to_set.setdefault(DataStore.STATS_STORE_PREFIX + name,
                            []).append(store_value)
      else:
        value = stats_collector_instance.Get().GetMetricValue(name)
        store_value = stats_values.StatsStoreValue()
        store_value.SetValue(value, metadata.value_type)

        to_set[DataStore.STATS_STORE_PREFIX + name] = [store_value]
    self.MultiSet(subject, to_set, replace=False, timestamp=timestamp)

  def StatsDeleteStatsInRange(self, subject, timestamp):
    """Deletes all stats in the given time range."""
    if timestamp == DataStore.NEWEST_TIMESTAMP:
      raise ValueError("Can't use NEWEST_TIMESTAMP in DeleteStats.")

    predicates = []
    for key in stats_collector_instance.Get().GetAllMetricsMetadata():
      predicates.append(DataStore.STATS_STORE_PREFIX + key)

    start = None
    end = None
    if timestamp and timestamp != DataStore.ALL_TIMESTAMPS:
      start, end = timestamp

    self.DeleteAttributes(subject, predicates, start=start, end=end)

  def LabelUpdateLabels(self, subject, new_labels, to_delete):
    new_attributes = {}
    for label in new_labels:
      new_attributes[DataStore.LABEL_ATTRIBUTE_TEMPLATE % label] = (
          DataStore.EMPTY_DATA_PLACEHOLDER)
    delete_attributes = [
        DataStore.LABEL_ATTRIBUTE_TEMPLATE % label for label in to_delete
    ]
    if new_attributes or delete_attributes:
      self.MultiSet(
          subject, new_attributes, to_delete=delete_attributes, timestamp=0)

  def FileHashIndexAddItem(self, subject, file_path):
    predicate = (DataStore.FILE_HASH_TEMPLATE % file_path).lower()
    self.MultiSet(subject, {predicate: [file_path]})

  def AFF4AddChild(self, subject, child, extra_attributes=None):
    """Adds a child to the specified parent."""
    precondition.AssertType(child, unicode)

    attributes = {
        DataStore.AFF4_INDEX_DIR_TEMPLATE % child: [
            DataStore.EMPTY_DATA_PLACEHOLDER
        ]
    }
    if extra_attributes:
      attributes.update(extra_attributes)
    self.MultiSet(subject, attributes)

  def AFF4DeleteChild(self, subject, child):
    self.DeleteAttributes(
        subject, [DataStore.AFF4_INDEX_DIR_TEMPLATE % utils.SmartStr(child)])


class DataStore(with_metaclass(registry.MetaclassRegistry, object)):
  """Abstract database access."""

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

  LABEL_ATTRIBUTE_PREFIX = "index:label_"
  LABEL_ATTRIBUTE_TEMPLATE = "index:label_%s"

  EMPTY_DATA_PLACEHOLDER = "X"

  FILE_HASH_PREFIX = "index:target:"
  FILE_HASH_TEMPLATE = "index:target:%s"

  AFF4_INDEX_DIR_PREFIX = "index:dir/"
  AFF4_INDEX_DIR_TEMPLATE = "index:dir/%s"

  mutation_pool_cls = MutationPool

  flusher_thread = None
  enable_flusher_thread = True
  monitor_thread = None

  def __init__(self):
    in_test = "Test Context" in config.CONFIG.context
    if not in_test and self.enable_flusher_thread:
      # Start the flusher thread.
      self.flusher_thread = utils.InterruptableThread(
          name="DataStore flusher thread", target=self.Flush, sleep_time=0.5)
      self.flusher_thread.start()
    self.monitor_thread = None

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
    stats_collector_instance.Get().SetGaugeValue("datastore_size", self.Size())

  def Initialize(self):
    """Initialization of the datastore."""

  @abc.abstractmethod
  def DeleteSubject(self, subject, sync=False):
    """Completely deletes all information about this subject."""

  def DeleteSubjects(self, subjects, sync=False):
    """Delete multiple subjects at once."""
    for subject in subjects:
      self.DeleteSubject(subject, sync=sync)

  def Set(self,
          subject,
          attribute,
          value,
          timestamp=None,
          replace=True,
          sync=True):
    """Set a single value for this subject's attribute.

    Args:
      subject: The subject this applies to.
      attribute: Attribute name.
      value: serialized value into one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the epoch.
        If None means now.
      replace: Bool whether or not to overwrite current records.
      sync: If true we ensure the new values are committed before returning.
    """
    # TODO(user): don't allow subject = None
    self.MultiSet(
        subject, {attribute: [value]},
        timestamp=timestamp,
        replace=replace,
        sync=sync)

  def LockRetryWrapper(self,
                       subject,
                       retrywrap_timeout=1,
                       retrywrap_max_timeout=10,
                       blocking=True,
                       lease_time=None):
    """Retry a DBSubjectLock until it succeeds.

    Args:
      subject: The subject which the lock applies to.
      retrywrap_timeout: How long to wait before retrying the lock.
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
        return self.DBSubjectLock(subject, lease_time=lease_time)
      except DBSubjectLockError:
        if not blocking:
          raise
        stats_collector_instance.Get().IncrementCounter("datastore_retries")
        time.sleep(retrywrap_timeout)
        timeout += retrywrap_timeout

    raise DBSubjectLockError("Retry number exceeded.")

  @abc.abstractmethod
  def DBSubjectLock(self, subject, lease_time=None):
    """Returns a DBSubjectLock object for a subject.

    This opens a read/write lock to the subject. Any read access to the subject
    will have a consistent view between threads. Any attempts to write to the
    subject must be performed under lock. DBSubjectLocks may fail and raise the
    DBSubjectLockError() exception.

    Users should almost always call LockRetryWrapper() to retry if the lock
    isn't obtained on the first try.

    Args:
        subject: The subject which the lock applies to. Only a single subject
          may be locked in a lock.
        lease_time: The minimum amount of time the lock should remain alive.

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
               to_delete=None):
    """Set multiple attributes' values for this subject in one operation.

    Args:
      subject: The subject this applies to.
      values: A dict with keys containing attributes and values, serializations
        to be set. values can be a tuple of (value, timestamp). Value must be
        one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the epoch.
        None means now.
      replace: Bool whether or not to overwrite current records.
      sync: If true we block until the operation completes.
      to_delete: An array of attributes to clear prior to setting.
    """

  def MultiDeleteAttributes(self,
                            subjects,
                            attributes,
                            start=None,
                            end=None,
                            sync=True):
    """Remove all specified attributes from a list of subjects.

    Args:
      subjects: The list of subjects that will have these attributes removed.
      attributes: A list of attributes.
      start: A timestamp, attributes older than start will not be deleted.
      end: A timestamp, attributes newer than end will not be deleted.
      sync: If true we block until the operation completes.
    """
    for subject in subjects:
      self.DeleteAttributes(
          subject, attributes, start=start, end=end, sync=sync)

  @abc.abstractmethod
  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=True):
    """Remove all specified attributes.

    Args:
      subject: The subject that will have these attributes removed.
      attributes: A list of attributes.
      start: A timestamp, attributes older than start will not be deleted.
      end: A timestamp, attributes newer than end will not be deleted.
      sync: If true we block until the operation completes.
    """

  def Resolve(self, subject, attribute):
    """Retrieve a value set for a subject's attribute.

    This method is easy to use but always gets the latest version of the
    attribute. It is more flexible and efficient to use the other Resolve
    methods.

    Args:
      subject: The subject URN.
      attribute: The attribute.

    Returns:
      A (value, timestamp in microseconds) stored in the datastore cell, or
      (None, 0). Value will be the same type as originally stored with Set().

    Raises:
      AccessError: if anything goes wrong.
    """
    for _, value, timestamp in self.ResolveMulti(
        subject, [attribute], timestamp=self.NEWEST_TIMESTAMP):

      # Just return the first one.
      return value, timestamp

    return (None, 0)

  @abc.abstractmethod
  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None):
    """Generate a set of values matching for subjects' attribute.

    This method provides backwards compatibility for the old method of
    specifying regexes. Each datastore can move to prefix matching by
    overriding this method and ResolvePrefix below.

    Args:
      subjects: A list of subjects.
      attribute_prefix: The attribute prefix.
      timestamp: A range of times for consideration (In microseconds). Can be a
        constant such as ALL_TIMESTAMPS or NEWEST_TIMESTAMP or a tuple of ints
        (start, end). Inclusive of both lower and upper bounds.
      limit: The total number of result values to return.

    Returns:
       A dict keyed by subjects, with values being a list of (attribute, value
       string, timestamp).

       Values with the same attribute (happens when timestamp is not
       NEWEST_TIMESTAMP, but ALL_TIMESTAMPS or time range) are guaranteed
       to be ordered in the decreasing timestamp order.

    Raises:
      AccessError: if anything goes wrong.
    """

  def ResolvePrefix(self, subject, attribute_prefix, timestamp=None,
                    limit=None):
    """Retrieve a set of value matching for this subject's attribute.

    Args:
      subject: The subject that we will search.
      attribute_prefix: The attribute prefix.
      timestamp: A range of times for consideration (In microseconds). Can be a
        constant such as ALL_TIMESTAMPS or NEWEST_TIMESTAMP or a tuple of ints
        (start, end).
      limit: The number of results to fetch.

    Returns:
       A list of (attribute, value string, timestamp).

       Values with the same attribute (happens when timestamp is not
       NEWEST_TIMESTAMP, but ALL_TIMESTAMPS or time range) are guaranteed
       to be ordered in the decreasing timestamp order.

    Raises:
      AccessError: if anything goes wrong.
    """
    for _, values in self.MultiResolvePrefix([subject],
                                             attribute_prefix,
                                             timestamp=timestamp,
                                             limit=limit):
      values.sort(key=lambda a: a[0])
      return values

    return []

  @abc.abstractmethod
  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None):
    """Resolve multiple attributes for a subject.

    Results may be in unsorted order.

    Args:
      subject: The subject to resolve.
      attributes: The attribute string or list of strings to match. Note this is
        an exact match, not a regex.
      timestamp: A range of times for consideration (In microseconds). Can be a
        constant such as ALL_TIMESTAMPS or NEWEST_TIMESTAMP or a tuple of ints
        (start, end).
      limit: The maximum total number of results we return.
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
        raise ValueError("after_urn \"%s\" does not begin with prefix \"%s\"" %
                         (after_urn, subject_prefix))
    return after_urn

  @abc.abstractmethod
  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None,
                     relaxed_order=False):
    """Scan for values of multiple attributes across a range of rows.

    Scans rows for values of attribute. Reads the most recent value stored in
    each row.

    Args:
      subject_prefix: Subject beginning with this prefix can be scanned. Must be
        an aff4 object and a directory - "/" will be appended if necessary. User
        must have read and query permissions on this directory.
      attributes: A list of attribute names to scan.
      after_urn: If set, only scan records which come after this urn.
      max_records: The maximum number of records to scan.
      relaxed_order: By default, ScanAttribute yields results in lexographic
        order. If this is set, a datastore may yield results in a more
        convenient order. For certain datastores this might greatly increase the
        performance of large scans.
    Yields: Pairs (subject, result_dict) where result_dict maps attribute to
      (timestamp, value) pairs.
    """

  def ScanAttribute(self,
                    subject_prefix,
                    attribute,
                    after_urn=None,
                    max_records=None,
                    relaxed_order=False):
    for s, r in self.ScanAttributes(
        subject_prefix, [attribute],
        after_urn=after_urn,
        max_records=max_records,
        relaxed_order=relaxed_order):
      ts, v = r[attribute]
      yield (s, ts, v)

  def GetMutationPool(self):
    return self.mutation_pool_cls()

  def CreateNotifications(self, queue_shard, notifications):
    values = {}
    for notification in notifications:
      values[self.NOTIFY_PREDICATE_TEMPLATE % notification.session_id] = [
          (notification.SerializeToString(), notification.timestamp)
      ]
    self.MultiSet(queue_shard, values, replace=False, sync=True)

  def DeleteNotifications(self, queue_shards, session_ids, start, end):
    attributes = [
        self.NOTIFY_PREDICATE_TEMPLATE % session_id
        for session_id in session_ids
    ]
    self.MultiDeleteAttributes(
        queue_shards, attributes, start=start, end=end, sync=True)

  def GetNotifications(self, queue_shard, end, limit=10000):
    for predicate, serialized_notification, ts in self.ResolvePrefix(
        queue_shard,
        self.NOTIFY_PREDICATE_PREFIX,
        timestamp=(0, end),
        limit=limit):
      try:
        # Parse the notification.
        notification = rdf_flows.GrrNotification.FromSerializedString(
            serialized_notification)
      except Exception:  # pylint: disable=broad-except
        logging.exception(
            "Can't unserialize notification, deleting it: "
            "predicate=%s, ts=%d", predicate, ts)
        self.DeleteAttributes(
            queue_shard,
            [predicate],
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
                               response_limit=None):
    """Fetches all Requests and Responses for a given session_id."""
    subject = session_id.Add("state")
    requests = {}

    # Get some requests.
    for predicate, serialized, _ in self.ResolvePrefix(
        subject,
        self.FLOW_REQUEST_PREFIX,
        limit=request_limit,
        timestamp=timestamp):

      request_id = predicate.split(":", 1)[1]
      requests[str(subject.Add(request_id))] = serialized

    # And the responses for them.
    response_data = dict(
        self.MultiResolvePrefix(
            list(iterkeys(requests)),
            self.FLOW_RESPONSE_PREFIX,
            limit=response_limit,
            timestamp=timestamp))

    for urn, request_data in sorted(iteritems(requests)):
      request = rdf_flow_runner.RequestState.FromSerializedString(request_data)
      responses = []
      for _, serialized, timestamp in response_data.get(urn, []):
        msg = rdf_flows.GrrMessage.FromSerializedString(serialized)
        msg.timestamp = timestamp
        responses.append(msg)

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

  def ReadCompletedRequests(self, session_id, timestamp=None, limit=None):
    """Fetches all the requests with a status message queued for them."""
    subject = session_id.Add("state")
    requests = {}
    status = {}

    for predicate, serialized, _ in self.ResolvePrefix(
        subject, [self.FLOW_REQUEST_PREFIX, self.FLOW_STATUS_PREFIX],
        limit=limit,
        timestamp=timestamp):

      parts = predicate.split(":", 3)
      request_id = parts[2]
      if parts[1] == "status":
        status[request_id] = serialized
      else:
        requests[request_id] = serialized

    for request_id, serialized in sorted(iteritems(requests)):
      if request_id in status:
        yield (rdf_flow_runner.RequestState.FromSerializedString(serialized),
               rdf_flows.GrrMessage.FromSerializedString(status[request_id]))

  def ReadResponsesForRequestId(self, session_id, request_id, timestamp=None):
    """Reads responses for one request.

    Args:
      session_id: The session id to use.
      request_id: The id of the request.
      timestamp: A timestamp as used in the data store.

    Yields:
      fetched responses for the request
    """
    request = rdf_flow_runner.RequestState(id=request_id, session_id=session_id)
    for _, responses in self.ReadResponses([request], timestamp=timestamp):
      return responses

  def ReadResponses(self, request_list, timestamp=None):
    """Reads responses for multiple requests at the same time.

    Args:
      request_list: The list of requests the responses should be fetched for.
      timestamp: A timestamp as used in the data store.

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
            response_subjects, self.FLOW_RESPONSE_PREFIX, timestamp=timestamp))

    for response_urn, request in sorted(iteritems(response_subjects)):
      responses = []
      for _, serialized, timestamp in response_data.get(response_urn, []):
        msg = rdf_flows.GrrMessage.FromSerializedString(serialized)
        msg.timestamp = timestamp
        responses.append(msg)

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

  def StoreRequestsAndResponses(self,
                                new_requests=None,
                                new_responses=None,
                                requests_to_delete=None):
    """Stores new flow requests and responses to the data store.

    Args:
      new_requests: A list of tuples (request, timestamp) to store in the data
        store.
      new_responses: A list of tuples (response, timestamp) to store in the data
        store.
      requests_to_delete: A list of requests that should be deleted from the
        data store.
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
          sync=True)

  def CheckRequestsForCompletion(self, requests):
    """Checks if there is a status message queued for a number of requests."""

    subjects = [r.session_id.Add("state") for r in requests]

    statuses_found = {}

    for subject, result in self.MultiResolvePrefix(subjects,
                                                   self.FLOW_STATUS_PREFIX):
      for predicate, _, _ in result:
        request_nr = int(predicate.split(":")[-1], 16)
        statuses_found.setdefault(subject, set()).add(request_nr)

    status_available = set()
    for r in requests:
      if r.request_id in statuses_found.get(r.session_id.Add("state"), set()):
        status_available.add(r)

    return status_available

  def DeleteRequest(self, request):
    return self.DeleteRequests([request])

  def DeleteRequests(self, requests):
    # Efficiently drop all responses to this request.
    subjects = [
        self.GetFlowResponseSubject(request.session_id, request.id)
        for request in requests
    ]

    self.DeleteSubjects(subjects, sync=True)

  def DestroyFlowStates(self, session_id):
    return self.MultiDestroyFlowStates([session_id])

  def MultiDestroyFlowStates(self, session_ids, request_limit=None):
    """Deletes all requests and responses for the given flows.

    Args:
      session_ids: A lists of flows to destroy.
      request_limit: A limit on the number of requests to delete.

    Returns:
      A list of requests that were deleted.
    """

    subjects = [session_id.Add("state") for session_id in session_ids]
    to_delete = []
    deleted_requests = []

    for subject, values in self.MultiResolvePrefix(
        subjects, self.FLOW_REQUEST_PREFIX, limit=request_limit):
      for _, serialized, _ in values:

        request = rdf_flow_runner.RequestState.FromSerializedString(serialized)
        deleted_requests.append(request)

        # Drop all responses to this request.
        response_subject = self.GetFlowResponseSubject(request.session_id,
                                                       request.id)
        to_delete.append(response_subject)

      # Mark the request itself for deletion.
      to_delete.append(subject)

    # Drop them all at once.
    self.DeleteSubjects(to_delete, sync=True)
    return deleted_requests

  def DeleteWellKnownFlowResponses(self, session_id, responses):
    subject = session_id.Add("state/request:00000000")
    predicates = []
    for response in responses:
      predicates.append(self.FLOW_RESPONSE_TEMPLATE % (response.request_id,
                                                       response.response_id))

    self.DeleteAttributes(subject, predicates, sync=True, start=0)

  def FetchResponsesForWellKnownFlow(self, session_id, response_limit,
                                     timestamp):
    subject = session_id.Add("state/request:00000000")

    for _, serialized, timestamp in sorted(
        self.ResolvePrefix(
            subject,
            self.FLOW_RESPONSE_PREFIX,
            limit=response_limit,
            timestamp=timestamp)):
      msg = rdf_flows.GrrMessage.FromSerializedString(serialized)
      msg.timestamp = timestamp
      yield msg

  # Index handling.

  _INDEX_PREFIX = "kw_index:"
  _INDEX_PREFIX_LEN = len(_INDEX_PREFIX)
  _INDEX_COLUMN_FORMAT = _INDEX_PREFIX + "%s"

  def _KeywordToURN(self, urn, keyword):
    return urn.Add(keyword)

  def IndexAddKeywordsForName(self, index_urn, name, keywords):
    timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
    with self.GetMutationPool() as mutation_pool:
      for keyword in set(keywords):
        mutation_pool.Set(
            self._KeywordToURN(index_urn, keyword),
            self._INDEX_COLUMN_FORMAT % name,
            "",
            timestamp=timestamp)

  def IndexRemoveKeywordsForName(self, index_urn, name, keywords):
    with self.GetMutationPool() as mutation_pool:
      for keyword in set(keywords):
        mutation_pool.DeleteAttributes(
            self._KeywordToURN(index_urn, keyword),
            [self._INDEX_COLUMN_FORMAT % name])

  def IndexReadPostingLists(self,
                            index_urn,
                            keywords,
                            start_time,
                            end_time,
                            last_seen_map=None):
    """Finds all objects associated with any of the keywords.

    Args:
      index_urn: The base urn of the index.
      keywords: A collection of keywords that we are interested in.
      start_time: Only considers keywords added at or after this point in time.
      end_time: Only considers keywords at or before this point in time.
      last_seen_map: If present, is treated as a dict and populated to map pairs
        (keyword, name) to the timestamp of the latest connection found.

    Returns:
      A dict mapping each keyword to a set of relevant names.
    """
    keyword_urns = {self._KeywordToURN(index_urn, k): k for k in keywords}
    result = {}
    for kw in keywords:
      result[kw] = set()

    for keyword_urn, value in self.MultiResolvePrefix(
        list(iterkeys(keyword_urns)),
        self._INDEX_PREFIX,
        timestamp=(start_time, end_time + 1)):
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

  QUEUE_TASK_PREDICATE_PREFIX = "task:"
  QUEUE_TASK_PREDICATE_TEMPLATE = QUEUE_TASK_PREDICATE_PREFIX + "%s"

  STATS_STORE_PREFIX = "aff4:stats_store/"

  @classmethod
  def CollectionMakeURN(cls, urn, timestamp, suffix=None, subpath="Results"):
    if suffix is None:
      # Disallow 0 so that subtracting 1 from a normal suffix doesn't require
      # special handling.
      suffix = random.randint(1, DataStore.COLLECTION_MAX_SUFFIX)
    result_urn = urn.Add(subpath).Add("%016x.%06x" % (timestamp, suffix))
    return (result_urn, timestamp, suffix)

  @classmethod
  def QueueTaskIdToColumn(cls, task_id):
    """Return a predicate representing the given task."""
    return DataStore.QUEUE_TASK_PREDICATE_TEMPLATE % ("%08d" % task_id)

  def CollectionScanItems(self,
                          collection_id,
                          rdf_type,
                          after_timestamp=None,
                          after_suffix=None,
                          limit=None):
    precondition.AssertType(collection_id, rdfvalue.RDFURN)

    after_urn = None
    if after_timestamp:
      after_urn = utils.SmartStr(
          self.CollectionMakeURN(
              collection_id,
              after_timestamp,
              suffix=after_suffix or self.COLLECTION_MAX_SUFFIX)[0])

    for subject, timestamp, serialized_rdf_value in self.ScanAttribute(
        unicode(collection_id.Add("Results")),
        self.COLLECTION_ATTRIBUTE,
        after_urn=after_urn,
        max_records=limit):
      item = rdf_type.FromSerializedString(serialized_rdf_value)
      item.age = timestamp
      # The urn is timestamp.suffix where suffix is 6 hex digits.
      suffix = int(str(subject)[-6:], 16)
      yield (item, timestamp, suffix)

  def CollectionReadIndex(self, collection_id):
    """Reads all index entries for the given collection.

    Args:
      collection_id: ID of the collection for which the indexes should be
        retrieved.

    Yields:
      Tuples (index, ts, suffix).
    """
    for (attr, value, ts) in self.ResolvePrefix(
        collection_id, self.COLLECTION_INDEX_ATTRIBUTE_PREFIX):
      i = int(attr[len(self.COLLECTION_INDEX_ATTRIBUTE_PREFIX):], 16)
      yield (i, ts, int(value, 16))

  def CollectionReadStoredTypes(self, collection_id):
    for attribute, _, _ in self.ResolveRow(collection_id):
      if attribute.startswith(self.COLLECTION_VALUE_TYPE_PREFIX):
        yield attribute[len(self.COLLECTION_VALUE_TYPE_PREFIX):]

  def CollectionReadItems(self, records):
    for _, v in self.MultiResolvePrefix([
        DataStore.CollectionMakeURN(record.queue_id, record.timestamp,
                                    record.suffix, record.subpath)[0]
        for record in records
    ], DataStore.COLLECTION_ATTRIBUTE):
      _, value, timestamp = v[0]
      yield (value, timestamp)

  def QueueQueryTasks(self, queue, limit=1):
    """Retrieves tasks from a queue without leasing them.

    This is good for a read only snapshot of the tasks.

    Args:
      queue: The task queue that this task belongs to, usually client.Queue()
        where client is the ClientURN object you want to schedule msgs on.
      limit: Number of values to fetch.

    Returns:
      A list of Task() objects.
    """
    prefix = DataStore.QUEUE_TASK_PREDICATE_PREFIX
    all_tasks = []

    for _, serialized, ts in self.ResolvePrefix(
        queue, prefix, timestamp=DataStore.ALL_TIMESTAMPS):
      task = rdf_flows.GrrMessage.FromSerializedString(serialized)
      task.leased_until = ts
      all_tasks.append(task)

    return all_tasks[:limit]

  def StatsReadDataForProcesses(self,
                                processes,
                                metric_name,
                                timestamp=None,
                                limit=10000):
    """Reads historical stats data for multiple processes at once."""
    multi_query_results = self.MultiResolvePrefix(
        processes,
        DataStore.STATS_STORE_PREFIX + (metric_name or ""),
        timestamp=timestamp,
        limit=limit)

    results = {}
    for subject, subject_results in multi_query_results:
      subject = rdfvalue.RDFURN(subject)
      subject_results = sorted(subject_results, key=lambda x: x[2])

      part_results = {}
      for predicate, value_string, timestamp in subject_results:
        metric_name = predicate[len(DataStore.STATS_STORE_PREFIX):]

        try:
          metadata = stats_collector_instance.Get().GetMetricMetadata(
              metric_name)
        except KeyError:
          continue

        stored_value = stats_values.StatsStoreValue.FromSerializedString(
            value_string)

        if metadata.fields_defs:
          field_values = [v.value for v in stored_value.fields_values]
          current_dict = part_results.setdefault(metric_name, {})
          for field_value in field_values[:-1]:
            current_dict = current_dict.setdefault(field_value, {})

          result_values_list = current_dict.setdefault(field_values[-1], [])
        else:
          result_values_list = part_results.setdefault(metric_name, [])

        result_values_list.append((stored_value.value, timestamp))

      results[subject.Basename()] = part_results
    return results

  def LabelFetchAll(self, subject):
    result = []
    for attribute, _, _ in self.ResolvePrefix(subject,
                                              self.LABEL_ATTRIBUTE_PREFIX):
      result.append(attribute[len(self.LABEL_ATTRIBUTE_PREFIX):])
    return sorted(result)

  def FileHashIndexQuery(self, subject, target_prefix, limit=100):
    """Search the index for matches starting with target_prefix.

    Args:
       subject: The index to use. Should be a urn that points to the sha256
         namespace.
       target_prefix: The prefix to match against the index.
       limit: Either a tuple of (start, limit) or a maximum number of results to
         return.

    Yields:
      URNs of files which have the same data as this file - as read from the
      index.
    """
    if isinstance(limit, (tuple, list)):
      start, length = limit  # pylint: disable=unpacking-non-sequence
    else:
      start = 0
      length = limit

    prefix = (DataStore.FILE_HASH_TEMPLATE % target_prefix).lower()
    results = self.ResolvePrefix(subject, prefix, limit=limit)

    for i, (_, hit, _) in enumerate(results):
      if i < start:
        continue
      if i >= start + length:
        break
      yield rdfvalue.RDFURN(hit)

  def FileHashIndexQueryMultiple(self, locations, timestamp=None):
    results = self.MultiResolvePrefix(
        locations, DataStore.FILE_HASH_PREFIX, timestamp=timestamp)
    for hash_obj, matches in results:
      yield (hash_obj, [file_urn for _, file_urn, _ in matches])

  def AFF4FetchChildren(self, subject, timestamp=None, limit=None):
    results = self.ResolvePrefix(
        subject,
        DataStore.AFF4_INDEX_DIR_PREFIX,
        timestamp=timestamp,
        limit=limit)
    for predicate, _, timestamp in results:
      yield (predicate[len(DataStore.AFF4_INDEX_DIR_PREFIX):], timestamp)

  def AFF4MultiFetchChildren(self, subjects, timestamp=None, limit=None):
    results = self.MultiResolvePrefix(
        subjects,
        DataStore.AFF4_INDEX_DIR_PREFIX,
        timestamp=timestamp,
        limit=limit)
    for subject, matches in results:
      children = []
      for predicate, _, timestamp in matches:
        children.append((predicate[len(DataStore.AFF4_INDEX_DIR_PREFIX):],
                         timestamp))
      yield (subject, children)


class DBSubjectLock(object):
  """Provide a simple subject lock using the database.

  This class should not be used directly. Its only safe to use via the
  DataStore.LockRetryWrapper() above which implements correct backoff and
  retry behavior.
  """

  def __init__(self, data_store, subject, lease_time=None):
    """Obtain the subject lock for lease_time seconds.

    This is never called directly but produced from the
    DataStore.LockedSubject() factory.

    Args:
      data_store: A data_store handler.
      subject: The name of a subject to lock.
      lease_time: The minimum length of time the lock will remain valid in
        seconds. Note this will be converted to usec for storage.

    Raises:
      ValueError: No lease time was provided.
    """
    self.subject = utils.SmartStr(subject)
    self.store = data_store
    # expires should be stored as usec
    self.expires = None
    self.locked = False
    if lease_time is None:
      raise ValueError("Trying to lock without a lease time.")
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

  def ExpirationAsRDFDatetime(self):
    return rdfvalue.RDFDatetime.FromSecondsSinceEpoch(self.expires / 1e6)


class DataStoreInit(registry.InitHook):
  """Initialize the data store.

  Depends on the stats module being initialized.
  """

  def _ListStorageOptions(self):
    for name, cls in iteritems(DataStore.classes):
      print("%s\t\t%s" % (name, cls.__doc__))

  def Run(self):
    """Initialize the data_store."""
    global DB  # pylint: disable=global-statement
    global REL_DB  # pylint: disable=global-statement
    global BLOBS  # pylint: disable=global-statement

    if flags.FLAGS.list_storage:
      self._ListStorageOptions()
      sys.exit(0)

    try:
      cls = DataStore.GetPlugin(config.CONFIG["Datastore.implementation"])
    except KeyError:
      msg = ("No Storage System %s found." %
             config.CONFIG["Datastore.implementation"])
      if config.CONFIG["Datastore.implementation"] == "SqliteDataStore":
        msg = "The SQLite datastore is no longer supported."
      print(msg)
      print("Available options:")
      self._ListStorageOptions()
      raise ValueError(msg)

    DB = cls()  # pylint: disable=g-bad-name
    DB.Initialize()
    atexit.register(DB.Flush)
    monitor_port = config.CONFIG["Monitoring.http_port"]
    if monitor_port != 0:
      DB.InitializeMonitorThread()

    # Initialize the blobstore.
    blobstore_name = config.CONFIG.Get("Blobstore.implementation")
    try:
      cls = blob_store.REGISTRY[blobstore_name]
    except KeyError:
      raise ValueError("No blob store %s found." % blobstore_name)
    BLOBS = blob_store.BlobStoreValidationWrapper(cls())

    # Initialize a relational DB if configured.
    rel_db_name = config.CONFIG["Database.implementation"]
    if not rel_db_name:
      return

    try:
      cls = registry_init.REGISTRY[rel_db_name]
    except KeyError:
      raise ValueError("Database %s not found." % rel_db_name)
    logging.info("Using database implementation %s", rel_db_name)
    REL_DB = db.DatabaseValidationWrapper(cls())
