#!/usr/bin/env python
#
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

"""The main data store."""


import abc
import re
import sys
import time

from grr.client import conf as flags
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


class Error(stats.CountingException):
  """Base class for all exceptions in this module."""
  pass


class TransactionError(Error):
  """Raised when a transaction fails to commit."""
  counter = "grr_commit_failure"


# Abstract some constants
ALL_TIMESTAMPS = "ALL_TIMESTAMPS"
NEWEST_TIMESTAMP = "NEWEST_TIMESTAMP"


# The following abstract classes do not return anything


class DataStore(object):
  """Abstract database access."""

  __metaclass__ = registry.MetaclassRegistry

  # This contains the supported filters by the datastore implementations.
  Filter = None

  def Set(self, subject, predicate, value, timestamp=None,
          replace=True, sync=True):
    """Set a single value for this subject's predicate.

    Args:
      subject: The subject this applies to.
      predicate: Predicate name.
      value: serialized value.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. If None means now.
      replace: Bool whether or not to overwrite current records.
      sync: If true we ensure the new values are committed before returning.
    """
    self.MultiSet(subject, {predicate: value}, timestamp, replace, sync)

  def RetryWrapper(self, subject, callback, retrywrap_timeout=1,
                   retrywrap_max_timeout=10, **kw):
    """Retry a Transaction until it succeeds.

    Args:
      subject: The subject which the transaction applies to.
      callback: A callback which will receive the transaction
         object. The callback will be called repeatedly until success.
      retrywrap_timeout: How long to wait before retrying the transaction.
      retrywrap_max_timeout: The maximum time to wait for a retry until we
         raise.
      kw: Passthrough to callback.

    Returns:
      The result from the callback.

    Raises:
      TransactionError: If the maximum retry count has been reached.
    """

    def Retry():
      """Retry transaction."""
      transaction = self.Transaction(subject)
      try:
        result = callback(transaction, **kw)
      finally:
        # Make sure the transaction is committed.
        transaction.Commit()

      return result

    timeout = 0
    while retrywrap_timeout < retrywrap_max_timeout:
      try:
        return Retry()
      except TransactionError:
        time.sleep(timeout)
        timeout += 1

    raise TransactionError("Retry number exceeded.")

  @abc.abstractmethod
  def Transaction(self, subject):
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

    Returns:
        A transaction object.
    """

  @abc.abstractmethod
  def MultiSet(self, subject, values, timestamp=None,
               replace=True, sync=True):
    """Set multiple predicates' values for this subject in one operation.

    Args:
      subject: The subject this applies to (BT row).
      values: A dict with keys containing predicates and values,
              serializations to be set.
      timestamp: The timestamp for this entry in microseconds since the
              epoch. None means now.
      replace: Bool whether or not to overwrite current records.
      sync: If true we block until the operation completes.
    """

  @abc.abstractmethod
  def DeleteAttributes(self, subject, predicates):
    """Remove all specified predicates.

    Args:
      subject: The subject that will have these attributes removed.
      predicates: A list of predicate URN.
    """

  @abc.abstractmethod
  def Resolve(self, subject, predicate, decoder=None):
    """Retrieve a value set for a subject's predicate.

    Args:
      subject: The subject URN.
      predicate: The predicate URN.
      decoder: If specified the cell value will be parsed by constructing this
             class. This can also be a protobuf.

    Returns:
      A (string, timestamp in microseconds) stored in the datastore
      cell, or (None, 0) or a (decoded protobuf, timestamp) if
      protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def MultiResolveRegex(self, subjects, predicate_regex,
                        decoder=None, timestamp=None):
    """Generate a set of values matching for subjects' predicate.

    Args:
      subjects: A list of subjects.
      predicate_regex: The predicate URN regex.

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
  def ResolveRegex(self, subject, predicate_regex,
                   decoder=None, timestamp=None):
    """Retrieve a set of value matching for this subject's predicate.

    Args:
      subject: The subject that we will search.
      predicate_regex: The predicate URN regex.

      decoder: If specified the cell value will be parsed by
          constructing this class. This can also be a protobuf.

      timestamp: A range of times for consideration (In
          microseconds). Can be a constant such as ALL_TIMESTAMPS or
          NEWEST_TIMESTAMP or a tuple of ints (start, end).

    Returns:
       A list of (predicate, value string, timestamp), or a (predicate, decoded
       protobuf, timestamp) if protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def Query(self, attributes, filter_obj="", subject_prefix="",
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
     attributes: A list of attributes to return
     filter_obj: A Filter() instance.
     subject_prefix: A prefix restriction for subjects.
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
  def __init__(self, table, subject):
    """Constructor.

    This is never called directly but produced from the
    DataStore.LockedSubject() factory.

    Args:
      table: A data_store handler.
      subject: The name of a subject to lock.
    """

  @abc.abstractmethod
  def DeleteSubject(self):
    """Completely deletes all information about this subject."""

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
  def ResolveMulti(self, predicates, decoder=None):
    """A generator over a set of predicates.

    Args:
      predicates: A list of predicates URN.
      decoder: If specified the cell value will be parsed by constructing this
      class. This can also be a protobuf.

    Yields:
       A (string, timestamp), or (None, 0) or a (decoded protobuf, timestamp) if
       protobuf was specified.

    Raises:
      AccessError: if anything goes wrong.
    """

  @abc.abstractmethod
  def ResolveRegex(self, predicate_regex, decoder=None,
                   timestamp=NEWEST_TIMESTAMP):
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

# Regex chars that should not be in a regex
disallowed_chars = re.compile("[\[\]\(\)\{\}\\\.\$\^]")


def EscapeRegex(string):
  return re.sub(disallowed_chars,
                lambda x: "\\" + x.group(0),
                utils.SmartUnicode(string))


def Init(flush=False):
  """Initialize the data_store."""
  global DB

  if FLAGS.list_storage:
    for name, cls in DataStore.classes.items():
      print "%s\t\t%s" % (name, cls.__doc__)

    sys.exit(0)

  if flush or DB is None:
    try:
      cls = DataStore.NewPlugin(FLAGS.storage)
    except KeyError:
      raise RuntimeError("No Storage System %s found." % FLAGS.storage)

    DB = cls()
