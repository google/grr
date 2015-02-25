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
import re
import sys
import time

import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils

flags.DEFINE_bool("list_storage", False,
                  "List all storage subsystems present.")


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


class TransactionError(Error):
  """Raised when a transaction fails to commit."""
  counter = "grr_commit_failure"


# This token will be used by default if no token was provided.
default_token = None


class DataStore(object):
  """Abstract database access."""

  __metaclass__ = registry.MetaclassRegistry

  # Constants relating to timestamps.
  ALL_TIMESTAMPS = "ALL_TIMESTAMPS"
  NEWEST_TIMESTAMP = "NEWEST_TIMESTAMP"
  TIMESTAMPS = [ALL_TIMESTAMPS, NEWEST_TIMESTAMP]

  flusher_thread = None
  monitor_thread = None

  def __init__(self):
    security_manager = access_control.BasicAccessControlManager.GetPlugin(
        config_lib.CONFIG["Datastore.security_manager"])()
    self.security_manager = security_manager
    logging.info("Using security manager %s", security_manager)
    # Start the flusher thread.
    self.flusher_thread = utils.InterruptableThread(target=self.Flush,
                                                    sleep_time=0.5)
    self.flusher_thread.start()
    self.monitor_thread = None

  def GetRequiredResolveAccess(self, attribute_regex):
    """Returns required level of access for resolve operations.

    Args:
      attribute_regex: A string (single attribute) or a list of
                       strings (multiple attributes).

    Returns:
      "r" when only read access is needed for resolve operation to succeed.
      Read operation allows reading the object when its URN is known.
      "rq" when both read and query access is needed for resolve operation to
      succeed. Query access allows reading indices, and thus traversing
      trees of objects (see AFF4Volume.ListChildren for details).
    """

    if isinstance(attribute_regex, basestring):
      attribute_regex = [utils.SmartStr(attribute_regex)]
    else:
      attribute_regex = [utils.SmartStr(x) for x in attribute_regex]

    for regex in attribute_regex:
      if regex == ".*":
        continue

      # Extract the column family
      try:
        column_family, unused_regex = regex.split(":", 1)
      except ValueError:
        raise RuntimeError("You must have an attribute prefix "
                           "prior to the regex: " + regex)

      # Columns with index require the query permission.
      if column_family.startswith("index"):
        return "rq"

    return "r"

  def InitializeMonitorThread(self):
    """Start the thread that registers the size of the DataStore."""
    if self.monitor_thread:
      return
    self.monitor_thread = utils.InterruptableThread(target=self._RegisterSize,
                                                    sleep_time=60)
    self.monitor_thread.start()

  def _RegisterSize(self):
    """Measures size of DataStore."""
    stats.STATS.SetGaugeValue("datastore_size", self.Size())

  def Initialize(self):
    """Initialization of the datastore."""

  @abc.abstractmethod
  def DeleteSubject(self, subject, sync=False, token=None):
    """Completely deletes all information about this subject."""

  def Set(self, subject, attribute, value, timestamp=None, token=None,
          replace=True, sync=True):
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
    # TODO(user) don't allow subject = None
    self.MultiSet(subject, {attribute: [value]}, timestamp=timestamp,
                  token=token, replace=replace, sync=sync)

  def RetryWrapper(self, subject, callback, retrywrap_timeout=1, token=None,
                   retrywrap_max_timeout=10, **kw):
    """Retry a Transaction until it succeeds.

    Args:
      subject: The subject which the transaction applies to.
      callback: A callback which will receive the transaction
         object. The callback will be called repeatedly until success.
      retrywrap_timeout: How long to wait before retrying the transaction.
      token: An ACL token.
      retrywrap_max_timeout: The maximum time to wait for a retry until we
         raise.
      **kw: Args passed to the callback.

    Returns:
      The result from the callback.

    Raises:
      TransactionError: If the maximum retry count has been reached.
    """

    def Retry():
      """Retry transaction."""
      transaction = self.Transaction(subject, token=token)
      try:
        result = callback(transaction, **kw)
      finally:
        # Make sure the transaction is committed.
        transaction.Commit()

      return result

    timeout = 0
    while timeout < retrywrap_max_timeout:
      try:
        result = Retry()
        if timeout > 1:
          logging.debug("Transaction took %s tries.", timeout)
        return result
      except TransactionError:
        stats.STATS.IncrementCounter("datastore_retries")
        time.sleep(retrywrap_timeout)
        timeout += retrywrap_timeout

    raise TransactionError("Retry number exceeded.")

  @abc.abstractmethod
  def Transaction(self, subject, lease_time=None, token=None):
    """Returns a Transaction object for a subject.

    This opens a read/write lock to the subject. Any read access to the subject
    will have a consistent view between threads. Any attempts to write to the
    subject must be followed by a commit. Transactions may fail and raise the
    TransactionError() exception. A transaction may fail due to failure of the
    underlying system or another thread holding a transaction on this object at
    the same time.

    Note that concurrent writes in and out of the transaction are allowed. If
    you want to guarantee that the object is not modified during the
    transaction, it must always be accessed with a transaction. Non
    transactioned writes will be visible to transactions. This makes it possible
    to update attributes both under transaction and without a transaction, if
    these attributes are independent.

    Users should almost always call RetryWrapper() to rety the transaction if it
    fails to commit.

    Args:
        subject: The subject which the transaction applies to. Only a
          single subject may be locked in a transaction.
        lease_time: The minimum amount of time the transaction should remain
          alive.
        token: An ACL token.

    Returns:
        A transaction object.
    """

  @abc.abstractmethod
  def MultiSet(self, subject, values, timestamp=None, replace=True, sync=True,
               to_delete=None, token=None):
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

  @abc.abstractmethod
  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
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
  def MultiResolveRegex(self, subjects, attribute_regex, timestamp=None,
                        limit=None, token=None):
    """Generate a set of values matching for subjects' attribute.

    Args:
      subjects: A list of subjects.
      attribute_regex: The attribute regex.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

      limit: The number of subjects to return.
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

  def ResolveRegex(self, subject, attribute_regex, timestamp=None,
                   limit=None, token=None):
    """Retrieve a set of value matching for this subject's attribute.

    Args:
      subject: The subject that we will search.
      attribute_regex: The attribute regex.

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
    for _, values in self.MultiResolveRegex(
        [subject], attribute_regex, timestamp=timestamp, token=token,
        limit=limit):
      values.sort(key=lambda a: a[0])
      return values

    return []

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None,
                   token=None):
    """Resolve multiple attributes for a subject."""

  def ResolveRow(self, subject, **kw):
    return self.ResolveRegex(subject, ".*", **kw)

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


class Transaction(object):
  """This abstracts operations on a subject which is locked.

  If another writer obtains this subject at the same time our commit
  will raise.

  This class should not be used directly. Its only safe to use via the
  DataStore.RetryWrapper() above which implements correct backoff and
  retry behavior for the transaction.
  """

  __metaclass__ = registry.MetaclassRegistry

  @abc.abstractmethod
  def __init__(self, table, subject, lease_time=None, token=None):
    """Constructor.

    This is never called directly but produced from the
    DataStore.LockedSubject() factory.

    Args:
      table: A data_store handler.
      subject: The name of a subject to lock.
      lease_time: The minimum length of time the transaction will remain valid.
      token: An ACL token which applies to all methods in this transaction.
    """

  @abc.abstractmethod
  def DeleteAttribute(self, attribute):
    """Remove an attribute.

    Args:
      attribute: The attribute to delete.
    """

  @abc.abstractmethod
  def Resolve(self, attribute):
    """Retrieve a value set for this subject's attribute.

    Args:
      attribute: The attribute to retrieve.

    Returns:
       A (string, timestamp), or (None, 0).

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def ResolveRegex(self, attribute_regex, timestamp=None):
    """Retrieve a set of values matching for this subject's attribute.

    Args:
      attribute_regex: The attribute regex.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

    Yields:
       Tuples of the form (attribute, value string, timestamp).

    Raises:
      AccessError: if anything goes wrong.
    """

  def UpdateLease(self, duration):
    """Update the transaction lease by at least the number of seconds.

    Note that not all data stores implement timed transactions. This method is
    only useful for data stores which expire a transaction after some time.

    Args:
      duration: The number of seconds to extend the transaction lease.
    """
    raise NotImplementedError

  def CheckLease(self):
    """Checks if this transaction is still valid."""
    return True

  @abc.abstractmethod
  def Set(self, attribute, value, timestamp=None, replace=True):
    """Set a new value for this subject's attribute.

    Note that the value will only be set when this transaction is
    committed.

    Args:
      attribute: The attribute to be set.
      value:  The value to be set (Can be a protobuf).
      timestamp: (In microseconds). If specified it overrides the update
                 time of this attribute.
      replace: Bool whether or not to overwrite current records.
    """

  @abc.abstractmethod
  def Commit(self):
    """Commits this transaction.

    If the transaction fails we raise TransactionError.
    """

  @abc.abstractmethod
  def Abort(self):
    """Aborts the transaction."""


class CommonTransaction(Transaction):
  """A common transaction that saves set/delete data before commiting."""

  def __init__(self, table, subject, lease_time=None, token=None):
    super(CommonTransaction, self).__init__(table, subject,
                                            lease_time=lease_time, token=token)
    self.to_set = {}
    self.to_delete = set()
    self.subject = subject
    self.store = table
    self.token = token
    self.expires = None

  def CheckLease(self):
    if not self.expires:
      return 0
    return max(0, self.expires - time.time())

  def DeleteAttribute(self, attribute):
    self.to_delete.add(attribute)

  def ResolveRegex(self, attribute_regex, timestamp=None):
    # Break up the timestamp argument.
    if isinstance(timestamp, (list, tuple)):
      start, end = timestamp  # pylint: disable=unpacking-non-sequence
    elif isinstance(timestamp, int):
      start = timestamp
      end = timestamp
    elif timestamp == DataStore.ALL_TIMESTAMPS or timestamp is None:
      start, end = 0, (2 ** 63) - 1
      timestamp = (start, end)
    elif timestamp == DataStore.NEWEST_TIMESTAMP:
      start, end = 0, (2 ** 63) - 1
      # Do not change 'timestamp' since we will use it later.
    else:
      raise ValueError("Value %s is not a valid timestamp" %
                       utils.SmartStr(timestamp))

    start = int(start)
    end = int(end)

    # Compile the regular expression.
    regex = re.compile(attribute_regex)

    # Get all results from to_set.
    results = []
    if self.to_set:
      for attribute, values in self.to_set.items():
        if regex.match(utils.SmartStr(attribute)):
          results.extend([(attribute, value, ts) for value, ts in values
                          if start <= ts <= end])

    # And also the results from the database.
    ds_results = self.store.ResolveRegex(self.subject, attribute_regex,
                                         timestamp=timestamp,
                                         token=self.token)

    # Must filter 'to_delete' from 'ds_results'.
    if self.to_delete:
      for val in ds_results:
        attribute, value, ts = val
        if attribute not in self.to_delete:
          results.append(val)
    else:
      results.extend(ds_results)

    if timestamp == DataStore.NEWEST_TIMESTAMP:
      # For each attribute, select the value with the newest timestamp.
      newest_results = {}
      for attribute, value, ts in results:
        current = newest_results.get(attribute, None)
        if current:
          _, _, current_ts = current
          if ts > current_ts:
            newest_results[attribute] = (attribute, value, ts)
        else:
          newest_results[attribute] = (attribute, value, ts)

      results = newest_results.values()

    return sorted(results, key=lambda (a, val, ts): (a, ts, val))

  def Set(self, attribute, value, timestamp=None, replace=True):
    if replace:
      self.to_delete.add(attribute)

    if timestamp is None:
      timestamp = int(time.time() * 1e6)

    self.to_set.setdefault(attribute, []).append((value, int(timestamp)))

  def Resolve(self, attribute):
    if attribute in self.to_set:
      return max(self.to_set[attribute], key=lambda vt: vt[1])
    if attribute in self.to_delete:
      return (None, 0)

    return self.store.Resolve(self.subject, attribute, token=self.token)

  def Commit(self):
    if not self.CheckLease():
      raise TransactionError("Lease is no longer valid.")

    self.store.DeleteAttributes(self.subject, self.to_delete, sync=True,
                                token=self.token)

    self.store.MultiSet(self.subject, self.to_set, token=self.token)
    self.to_set = {}
    self.to_delete = set()

  def __del__(self):
    try:
      self.Abort()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass


class ResultSet(object):
  """A class returned from Query which contains all the result."""
  # Total number of results that could have been returned. The results returned
  # may have been limited in some way.
  total_count = 0

  def __init__(self, results=None):
    if results is None:
      results = []

    self.results = results

  def __iter__(self):
    return iter(self.results)

  def __getitem__(self, item):
    return self.results[item]

  def __len__(self):
    return len(self.results)

  def __iadd__(self, other):
    self.results = list(self.results) + list(other)
    return self

  def Append(self, item):
    self.results.append(item)


class DataStoreInit(registry.InitHook):
  """Initialize the data store.

  Depends on the stats module being initialized.
  """

  pre = ["StatsInit"]

  def Run(self):
    """Initialize the data_store."""
    global DB  # pylint: disable=global-statement

    if flags.FLAGS.list_storage:
      for name, cls in DataStore.classes.items():
        print "%s\t\t%s" % (name, cls.__doc__)

      sys.exit(0)

    try:
      cls = DataStore.GetPlugin(config_lib.CONFIG["Datastore.implementation"])
    except KeyError:
      raise RuntimeError("No Storage System %s found." %
                         config_lib.CONFIG["Datastore.implementation"])

    DB = cls()  # pylint: disable=g-bad-name
    DB.Initialize()
    atexit.register(DB.Flush)
    monitor_port = config_lib.CONFIG["Monitoring.http_port"]
    if monitor_port != 0:
      stats.STATS.RegisterGaugeMetric("datastore_size", int,
                                      docstring="Size of data store in bytes",
                                      units="BYTES")
      DB.InitializeMonitorThread()

  def RunOnce(self):
    """Initialize some Varz."""
    stats.STATS.RegisterCounterMetric("grr_commit_failure")
    stats.STATS.RegisterCounterMetric("datastore_retries")
