#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
import getpass
import re
import sys
import time

from grr.client import conf as flags
import logging

from grr.lib import registry
from grr.lib import stats
from grr.lib import utils

flags.DEFINE_string("storage", "MongoDataStore",
                    "Storage subsystem to use.")

flags.DEFINE_bool("list_storage", False,
                  "List all storage subsystems present.")

FLAGS = flags.FLAGS

# A global data store handle
DB = None

# There are stub methods that don't return/yield as indicated by the docstring.
# pylint: disable=C6112


class Error(stats.CountingExceptionMixin, Exception):
  """Base class for all exceptions in this module."""
  pass


class TransactionError(Error):
  """Raised when a transaction fails to commit."""
  counter = "grr_commit_failure"


class UnauthorizedAccess(Error):
  """Raised when a request arrived from an unauthorized source."""
  counter = "grr_unauthorised_requests"

  def __init__(self, message, subject=None, requested_access="?"):
    self.subject = subject
    self.requested_access = requested_access
    logging.warning(message)
    super(UnauthorizedAccess, self).__init__(message)


class ExpiryError(Error):
  """Raised when a token is used which is expired."""
  counter = "grr_expired_tokens"


class ACLToken(object):
  """The access control token."""

  is_emergency = False

  def __init__(self, username="", reason="", requested_access="r",
               source_ips=None, process=None, expiry=None):
    """Controls access to the data for the user.

    This ACL token should be provided for any access to the data store. This
    allows the data store to audit all access to data. Note that implementations
    should implement a mechanism for authenticating tokens, so they can not be
    forged.

    Args:
       username: The user which requires access to the data.
       reason: The stated reason for the access (e.g. case name/id).
       requested_access: The type of access this token is for.
       source_ips: Optional list of source IPs of the request.
       process: Optional name of the process issuing this token.
       expiry: When does this token expire (seconds since epoch)? Use of this
          token after this time will raise ExpiryError.
    """
    self.username = username or getpass.getuser()
    self.reason = reason
    self.requested_access = requested_access
    self.source_ips = source_ips or []
    self.process = process

    # This special bit indicates a privileged token for internal use. When this
    # bit is set, ACLs will be bypassed. There should be no way for an external
    # user to set this flag. IMPORTANT: This flag does not serialize to the
    # protobuf for the remote data store!
    self.supervisor = False

    # By default never expire.
    if expiry is None:
      expiry = sys.maxint

    self.expiry = expiry

  def CheckExpiry(self):
    if time.time() > self.expiry:
      raise ExpiryError("Token expired.")

  def __str__(self):
    return "Token(%s:%s)" % (utils.SmartStr(self.username),
                             utils.SmartStr(self.reason))

  def Copy(self):
    return ACLToken(username=self.username, reason=self.reason,
                    requested_access=self.requested_access,
                    source_ips=self.source_ips, process=self.process,
                    expiry=self.expiry)

  def ToProto(self, proto):
    """Copy ourselves into the proto."""
    # Only bother with valid tokens.
    self.CheckExpiry()
    proto.username = self.username
    proto.reason = self.reason
    proto.requested_access = self.requested_access
    proto.expiry = long(self.expiry)
    proto.source_ips.extend(self.source_ips)
    if self.process:
      proto.process = self.process


# This token will be used by default if no token was provided.
default_token = ACLToken()


class BaseAccessControlManager(object):
  """A class managing access to data resources."""

  __metaclass__ = registry.MetaclassRegistry

  def CheckAccess(self, token, subjects, requested_access="r"):
    """The main entry point for checking access to resources.

    Args:
      token: An instance of data_store.ACLToken security token.

      subjects: The list of subject URNs which the user is requesting access
         to. If any of these fail, the whole request is denied.

      requested_access: A string specifying the desired level of access ("r" for
         read and "w" for write).

    Raises:
       UnauthorizedAccess: If the user is not authorized to perform the action
       on any of the subject URNs.
    """
    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)


class DataStore(object):
  """Abstract database access."""

  __metaclass__ = registry.MetaclassRegistry

  # This contains the supported filters by the datastore implementations.
  filter = None

  # Constants relating to timestamps.
  ALL_TIMESTAMPS = "ALL_TIMESTAMPS"
  NEWEST_TIMESTAMP = "NEWEST_TIMESTAMP"
  TIMESTAMPS = [ALL_TIMESTAMPS, NEWEST_TIMESTAMP]

  def __init__(self):
    self.security_manager = BaseAccessControlManager()

  @abc.abstractmethod
  def DeleteSubject(self, subject, token=None):
    """Completely deletes all information about this subject."""

  def Set(self, subject, predicate, value, timestamp=None, token=None,
          replace=True, sync=True):
    """Set a single value for this subject's predicate.

    Args:
      subject: The subject this applies to.
      predicate: Predicate name.
      value: serialized value into one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. If None means now.
      token: An ACL token.
      replace: Bool whether or not to overwrite current records.
      sync: If true we ensure the new values are committed before returning.
    """
    self.MultiSet(subject, {predicate: [value]}, timestamp=timestamp,
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
    while retrywrap_timeout < retrywrap_max_timeout:
      try:
        result = Retry()
        if timeout > 1:
          logging.debug("Transaction took %s tries.", timeout)
        return result
      except TransactionError:
        time.sleep(timeout)
        timeout += 1

    raise TransactionError("Retry number exceeded.")

  def Decode(self, value, decoder=None):
    if decoder:
      try:
        # Is it a protobuf?
        result = decoder()
        result.ParseFromString(value)
      except AttributeError:
        # Something else?
        result = decoder(value)

      return result

  @abc.abstractmethod
  def Transaction(self, subject, token=None):
    """Returns a Transaction object for a subject.

    This opens a read lock to the subject. Any read access to the
    subject will have a consistent view between threads. Any attempts
    to write to the subject must be followed by a commit. Transactions
    may fail and raise the TransactionError() exception. A transaction
    may fail due to failure of the underlying system or another thread
    holding a transaction on this object at the same time.

    Users should retry the transaction if it fails to commit.

    Args:
        subject: The subject which the transaction applies to. Only a
           single subject may be locked in a transaction.
        token: An ACL token.

    Returns:
        A transaction object.
    """

  @abc.abstractmethod
  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation.

    Args:
      subject: The subject this applies to.
      values: A dict with keys containing predicates and values, serializations
              to be set. values can be a tuple of (value, timestamp). Value must
              be one of the supported types.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. None means now.
      token: An ACL token.
      replace: Bool whether or not to overwrite current records.
      sync: If true we block until the operation completes.
      to_delete: An array of predicates to clear prior to setting.
    """

  @abc.abstractmethod
  def DeleteAttributes(self, subject, predicates, token=None):
    """Remove all specified predicates.

    Args:
      subject: The subject that will have these attributes removed.
      predicates: A list of predicate URN.
      token: An ACL token.
    """

  @abc.abstractmethod
  def Resolve(self, subject, predicate, decoder=None, token=None):
    """Retrieve a value set for a subject's predicate.

    Args:
      subject: The subject URN.
      predicate: The predicate URN.
      decoder: If specified the cell value will be parsed by constructing this
             class. This can also be a protobuf.
      token: An ACL token.

    Returns:
      A (value, timestamp in microseconds) stored in the datastore cell, or
      (None, 0) or a (decoded protobuf, timestamp) if protobuf was
      specified. Value will be the same type as originally stored with Set().

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None):
    """Generate a set of values matching for subjects' predicate.

    Args:
      subjects: A list of subjects.
      predicate_regex: The predicate URN regex.
      token: An ACL token.

      decoder: If specified the cell value will be parsed by
          constructing this class. This can also be a protobuf.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

    Returns:
       A dict keyed by subjects, with values being a list of (predicate, value
       string, timestamp), or a (predicate, decoded protobuf, timestamp) if
       protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def ResolveRegex(self, subject, predicate_regex, token=None,
                   decoder=None, timestamp=None, limit=1000):
    """Retrieve a set of value matching for this subject's predicate.

    Args:
      subject: The subject that we will search.
      predicate_regex: The predicate URN regex.
      token: An ACL token.

      decoder: If specified the cell value will be parsed by
          constructing this class. This can also be a protobuf.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

      limit: The number of predicates to fetch.
    Returns:
       A list of (predicate, value string, timestamp), or a (predicate, decoded
       protobuf, timestamp) if protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def Query(self, attributes=None, filter_obj="", subject_prefix="", token=None,
            subjects=None, limit=100):
    """Selects a set of subjects based on filters.

    Examples:
      Retrieves all subjects which have the attribute foobar set.

          Query(HasPredicateFilter("foobar"))

      Retrieve subjects which contain "foo" in attribute "bar":
          Query(PredicateContainsFilter("foo","bar"))

      Retrieve subjects which have both the foo and bar attributes set:
          Query(AndFilter(HasPredicateFilter("foo"),HasPredicateFilter("bar")))

    Args:
     attributes: A list of attributes to return (None returns all attributes).
     filter_obj: A Filter() instance.
     subject_prefix: A prefix restriction for subjects.
     token: An ACL token.
     subjects: A list of subject names which the query applies to.
     limit: A (start, end) tuple of integers representing subjects to
            return. Useful for paging. If its a single integer we take
            it as the end limit (start=0).

    Yields:
      A dict for each subject that matches. The Keys are named by the attributes
      requested, the values are a tuple of (value, timestamp). The special key
      "subject" represents the subject name which is always returned.

    Raises:
      AttributeError: When attributes is not a sequence of stings.
    """

  @abc.abstractmethod
  def Flush(self):
    """Flushes the DataStore."""

  def __del__(self):
    self.Flush()


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
  def __init__(self, table, subject, token=None):
    """Constructor.

    This is never called directly but produced from the
    DataStore.LockedSubject() factory.

    Args:
      table: A data_store handler.
      subject: The name of a subject to lock.
      token: An ACL token which applies to all methods in this transaction.
    """

  @abc.abstractmethod
  def DeleteAttribute(self, predicate):
    """Remove a predicate.

    Args:
      predicate: The predicate URN.
    """

  @abc.abstractmethod
  def Resolve(self, predicate, decoder=None):
    """Retrieve a value set for this subject's predicate.

    Args:
      predicate: The predicate URN.
      decoder: If specified the cell value will be parsed by constructing this
      class. This can also be a protobuf.

    Returns:
       A (string, timestamp), or (None, 0) or a (decoded protobuf, timestamp) if
       protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def ResolveRegex(self, predicate_regex, decoder=None, timestamp=None):
    """Retrieve a set of values matching for this subject's predicate.

    Args:
      predicate_regex: The predicate URN regex.
      decoder: If specified the cell value will be parsed by constructing this
      class. This can also be a protobuf.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

    Yields:
       A (predicate, value string, timestamp), or a (predicate, decoded
       protobuf, timestamp) if protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def Set(self, predicate, value, timestamp=None, replace=True):
    """Set a new value for this subject's predicate.

    Note that the value will only be set when this transaction is
    committed.

    Args:
      predicate: The attribute to be set.
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

  def __len__(self):
    return len(self.results)

  def __iadd__(self, other):
    self.results = list(self.results) + list(other)
    return self

  def Append(self, item):
    self.results.append(item)


# Regex chars that should not be in a regex
disallowed_chars = re.compile(r"[[\](){}+*?.$^\\]")


def EscapeRegex(string):
  return re.sub(disallowed_chars,
                lambda x: "\\" + x.group(0),
                utils.SmartUnicode(string))


class DataStoreInit(registry.InitHook):
  """Initialize the data store.

  Depends on the stats module being initialized.
  """

  pre = ["StatsInit"]

  def Run(self):
    """Initialize the data_store."""
    global DB  # pylint: disable=W0603

    if FLAGS.list_storage:
      for name, cls in DataStore.classes.items():
        print "%s\t\t%s" % (name, cls.__doc__)

      sys.exit(0)

    try:
      cls = DataStore.NewPlugin(FLAGS.storage)
    except KeyError:
      logging.warning("No Storage System %s found. Using FakeStorage",
                      FLAGS.storage)
      cls = DataStore.NewPlugin("FakeDataStore")

    DB = cls()  # pylint: disable=C6409

  def RunOnce(self):
    """Initialize some Varz."""
    stats.STATS.RegisterVar("grr_commit_failure")
    stats.STATS.RegisterVar("grr_expired_tokens")
    stats.STATS.RegisterVar("grr_unauthorised_requests")
