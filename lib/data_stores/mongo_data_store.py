#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mongo."""


import threading
import time
from bson import binary
import pymongo
from pymongo import errors

import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import registry
from grr.lib import utils

config_lib.DEFINE_string("Mongo.server", "localhost",
                         "The mongo server hostname.")

config_lib.DEFINE_integer("Mongo.port", 27017, "The mongo server port..")

config_lib.DEFINE_string("Mongo.db_name", "grr", "The mongo database name")


# These are filters
class Filter(object):
  """Baseclass for filters."""

  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def FilterExpression(self):
    """Generates a find spec.

    This returns a mongo find spec which will select the documents which satisfy
    the condition.

    Returns:
      A mongo find spec that will be used to general the initial list of
      subjects.
    """
    return {}

  def GetMatches(self, spec, collection):
    """Generates a list of subjects which match the filter.

    Args:
      spec: A spec which is used to restrict the query.
      collection: The collection this will query.

    Returns:
      A set of matching subjects.
    """
    result = set()
    spec = {"$and": [spec, self.FilterExpression()]}
    for document in collection.find(spec,
                                    dict(subject=True)):
      result.add(document["subject"])

    return result


class IdentityFilter(Filter):
  def GetMatches(self, spec, collection):
    result = set()

    # Only project the subject.
    for document in collection.find(spec, dict(subject=True)):
      result.add(document["subject"])

    return result


class HasPredicateFilter(Filter):

  def __init__(self, attribute_name):
    self.attribute_name = utils.SmartUnicode(attribute_name)
    super(HasPredicateFilter, self).__init__()

  def FilterExpression(self):
    return dict(predicate=self.attribute_name)


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    super(AndFilter, self).__init__()

  def GetMatches(self, spec, collection):
    sets = []
    for part in self.parts:
      sets.append(part.GetMatches(spec, collection))

    return set.intersection(*sets)


class OrFilter(Filter):
  """A Logical Or operator."""

  def __init__(self, *parts):
    self.parts = parts
    super(OrFilter, self).__init__()

  def FilterExpression(self):
    return {"$or": [x.FilterExpression() for x in self.parts]}


class PredicateContainsFilter(Filter):
  """Applies a RegEx on the content of an attribute."""

  def __init__(self, attribute_name, regex):
    self.regex = regex
    self.attribute_name = utils.SmartUnicode(attribute_name)
    super(PredicateContainsFilter, self).__init__()

  def FilterExpression(self):
    return dict(predicate=self.attribute_name,
                str_value={"$regex": self.regex})


class SubjectContainsFilter(Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Args:
       regex: Must match the row name.
    """
    self.regex = regex
    super(SubjectContainsFilter, self).__init__()

  def FilterExpression(self):
    # If no search term specified we allow the column to not even be
    # set. Without this statement we produce a filter which requires
    # the column to be set.
    if not self.regex: return {}

    return dict(subject={"$regex": self.regex})


class PredicateGreaterThanFilter(Filter):
  """A filter to be applied to DataStore.Query.

  This filters all subjects which have this predicate greater than the value
  specified.
  """

  operator = "$gt"

  def __init__(self, attribute_name, value):
    """Constructor.

    Args:
       attribute_name: The attribute name must be set.
       value: The value that attribute must be less than.
    """
    self.attribute_name = utils.SmartUnicode(attribute_name)
    self.value = value
    super(PredicateGreaterThanFilter, self).__init__()

  def FilterExpression(self):
    return dict(int_value={self.operator: long(self.value)},
                predicate=self.attribute_name)


class PredicateGreaterEqualFilter(PredicateGreaterThanFilter):
  operator = "$ge"


class PredicateLessThanFilter(PredicateGreaterThanFilter):
  operator = "$lt"


class PredicateLessEqualFilter(PredicateGreaterThanFilter):
  operator = "$le"


class MongoDataStore(data_store.DataStore):
  """A Mongo based data store."""

  def __init__(self):
    super(MongoDataStore, self).__init__()
    # Support various versions on the pymongo connection object.
    try:
      connector = pymongo.MongoClient
    except AttributeError:
      connector = pymongo.Connection

    if config_lib.CONFIG["Mongo.server"]:
      mongo_client = connector(
          host=config_lib.CONFIG["Mongo.server"],
          port=int(config_lib.CONFIG["Mongo.port"]))

    else:
      mongo_client = connector()

    # For now use a single "data" collection
    self.db_handle = mongo_client[config_lib.CONFIG["Mongo.db_name"]]

    # We have two collections - the latest collection maintains the latest data
    # and the versioned collection maintains versioned data.
    self.latest_collection = self.db_handle.latest
    self.versioned_collection = self.db_handle.versioned
    self.filter = Filter

    # Ensure we have the correct indexes.
    for idx in ["subject", "predicate", "timestamp"]:
      self.latest_collection.ensure_index(idx)
      self.versioned_collection.ensure_index(idx)

  def _GetCursor(self, spec, timestamp, limit):
    """Create a mongo cursor based on the timestamp restriction."""

    if timestamp == self.NEWEST_TIMESTAMP or timestamp is None:
      collection = self.latest_collection
    elif timestamp == self.ALL_TIMESTAMPS:
      collection = self.versioned_collection
    elif isinstance(timestamp, tuple):
      collection = self.versioned_collection
      start, end = timestamp
      spec = {"$and": [dict(timestamp={"$gte": start}),
                       dict(timestamp={"$lte": end}),
                       spec]}
    else:
      raise data_store.Error("Undefined timestamp specification.")

    cursor = collection.find(spec).sort("timestamp", pymongo.DESCENDING)

    if limit:
      cursor = cursor.limit(limit)

    return cursor

  def ResolveMulti(self, subject, predicates, decoder=None, token=None,
                   timestamp=None):
    """Resolves multiple predicates at once for one subject."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    # Build a query spec.
    spec = {"$and": [
        # Subject matches any of the requested subjects.
        dict(subject=utils.SmartUnicode(subject)),
        {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in predicates]},
        ]}

    for document in self._GetCursor(spec, timestamp, 0):
      subject = document["subject"]
      value = Decode(document, decoder)
      yield (document["predicate"], value, document["timestamp"])

  def DeleteSubject(self, subject, token=None):
    """Completely deletes all information about the subject."""
    subject = utils.SmartUnicode(subject)
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    self.latest_collection.remove(dict(subject=subject))
    self.versioned_collection.remove(dict(subject=subject))

  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    if timestamp is None:
      timestamp = time.time() * 1e6

    # Prepare a mongo bulk insert for all the values.
    documents = []
    subject = utils.SmartUnicode(subject)
    to_delete = set(to_delete or [])

    latest = {}

    # Build a document for each unique timestamp.
    for attribute, sequence in values.items():
      for value in sequence:
        if isinstance(value, tuple):
          value, entry_timestamp = value
        else:
          entry_timestamp = timestamp

        predicate = utils.SmartUnicode(attribute)
        prefix = predicate.split(":", 1)[0]

        document = dict(subject=subject, timestamp=int(entry_timestamp),
                        predicate=predicate, prefix=prefix)
        _Encode(document, value)
        documents.append(document)
        latest[predicate] = document

        # Replacing means to delete all versions of the attribute first.
        if replace:
          to_delete.add(attribute)

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    # Just write using bulk insert mode.
    if documents:
      try:
        self.versioned_collection.insert(documents, w=1 if sync else 0)
      except errors.PyMongoError as e:
        logging.error("Mongo Error %s", e)
        raise data_store.Error(utils.SmartUnicode(e))

      # Maintain the latest documents in the latest collection.
      for predicate, document in latest.items():
        document.pop("_id", None)
        self.latest_collection.update(
            dict(subject=subject, predicate=predicate, prefix=prefix),
            document, upsert=True, w=1 if sync else 0)

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       token=None, sync=False):
    """Remove all the attributes from this subject."""
    _ = sync  # Unused attribute, mongo is always synced.
    # Timestamps are not implemented yet.
    if start or end:
      raise NotImplementedError("Mongo data store does not support timestamp "
                                "based deletion yet.")
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    # Build a spec to select the subject and any of the predicates.
    spec = {"$and": [
        dict(subject=utils.SmartUnicode(subject)),
        {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in attributes]},
        ]}

    self.versioned_collection.remove(spec)
    self.latest_collection.remove(spec)

  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None, limit=None):
    """Retrieves a bunch of subjects in one round trip."""
    self.security_manager.CheckDataStoreAccess(token, subjects, "r")
    if not subjects:
      return {}

    result = {}

    # Build a query spec.
    # Subject matches any of the requested subjects.
    spec = dict(subject={"$in": [utils.SmartUnicode(x) for x in subjects]})

    # For a wildcard we just select all attributes by not applying a condition
    # at all.
    if isinstance(predicate_regex, basestring):
      predicate_regex = [predicate_regex]

    if predicate_regex != [".*"]:
      spec = {"$and": [
          spec,
          {"$or": [dict(predicate={"$regex": x}) for x in predicate_regex]},
          ]}

    for document in self._GetCursor(spec, timestamp, limit):
      subject = document["subject"]
      value = Decode(document, decoder)
      predicate = document.get("predicate")
      if predicate is None:
        # This might not be a normal aff4 attribute - transactions are one
        # example for this.
        continue
      result.setdefault(subject, []).append(
          (predicate, value, document["timestamp"]))

    return result

  def MultiResolveLiteral(self, subjects, predicates, token=None,
                          decoder=None, timestamp=None, limit=None):
    """Retrieves a bunch of subjects in one round trip."""
    self.security_manager.CheckDataStoreAccess(token, subjects, "r")
    if not subjects:
      return {}

    result = {}

    # Build a query spec.
    spec = {"$and": [
        dict(subject={"$in": [utils.SmartUnicode(x) for x in subjects]}),
        dict(predicate={"$in": [utils.SmartUnicode(x) for x in predicates]}),
        ]}

    for document in self._GetCursor(spec, timestamp, limit):
      subject = document["subject"]
      value = Decode(document, decoder)
      result.setdefault(subject, []).append(
          (document["predicate"], value, document["timestamp"]))

    return result

  def Query(self, attributes=None, filter_obj=None, subject_prefix="",
            token=None, subjects=None, limit=100, timestamp=None):
    """Selects a set of subjects based on filters.

    This is not very efficient in the general case so subject_prefix must
    usually be specified to limit the number of documents examined.

    Args:
      attributes: The attributes to return.
      filter_obj: An object of Filter() baseclass.
      subject_prefix: Only consider those URNs with this subject prefix.
      token: The security token.
      subjects: Only consider the subjects from this list of URNs.
      limit: A (start, length) tuple of integers representing subjects to
          return. Useful for paging. If its a single integer we take
          it as the length limit (start=0).
      timestamp: The timestamp policy to use.

    Returns:
      A ResultSet instance.
    """
    subject_prefix = utils.SmartUnicode(subject_prefix)

    # The initial spec restricts the query to a small subset of the documents.
    if subject_prefix:
      spec = {"$and": [
          dict(subject={"$gte": subject_prefix}),
          dict(subject={"$lte": subject_prefix+"\x7f"})
          ]}

    elif subjects:
      spec = dict(subject={"$in": [
          utils.SmartUnicode(x) for x in list(subjects)]})

    else:
      spec = {}

    try:
      skip, limit = limit
    except TypeError:
      skip = 0

    if attributes is None: attributes = []

    if u"aff4:type" not in attributes:
      attributes.append(u"aff4:type")

    if filter_obj is None:
      filter_obj = IdentityFilter()

    total_hits = sorted(filter_obj.GetMatches(spec, self.versioned_collection))
    result_set = data_store.ResultSet()
    for subject, data in sorted(self.MultiResolveLiteral(
        total_hits[skip:skip+limit], attributes, token=token,
        timestamp=timestamp).items()):
      result = dict(subject=[(subject, 0)])
      for predicate, value, ts in data:
        result.setdefault(predicate, []).append((value, ts))

      try:
        self.security_manager.CheckDataStoreAccess(token, [subject], "rq")

        result_set.Append(result)
      except access_control.UnauthorizedAccess:
        continue

    result_set.total_count = len(total_hits)

    return result_set

  def Transaction(self, subject, token=None):
    return MongoTransaction(self, subject, token=token)


class MongoTransaction(data_store.Transaction):
  """The Mongo data store transaction object.

  This object does not aim to ensure ACID like consistently. We only ensure that
  two simultaneous locks can not be held on the same RDF subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError.

  A lock is considered expired after a certain time.
  """

  # The maximum time the lock remains active in seconds.
  LOCK_TIME = 60

  lock_creation_lock = threading.Lock()

  locked = False

  def __init__(self, store, subject, token=None):
    """Ensure we can take a lock on this subject."""
    self.store = store
    self.token = token
    self.subject = utils.SmartUnicode(subject)
    self.current_lock = time.time()

    self.document = self.store.latest_collection.find_and_modify(
        query={"subject": self.subject, "type": "transaction",
               "lock_time": {"$lt": time.time() - self.LOCK_TIME}},
        update=dict(subject=self.subject, type="transaction",
                    lock_time=self.current_lock),
        upsert=False, new=True)

    if self.document:
      # We hold a lock now:
      self.locked = True
      return

    # Maybe the lock did not exist yet. To create it, we use a lock to reduce
    # the chance of deleting some other lock created at the same time. Note that
    # there still exists a very small race if this happens in multiple processes
    # at the same time.
    with self.lock_creation_lock:
      document = self.store.latest_collection.find(
          {"subject": self.subject, "type": "transaction"})
      if not document.count():
        # There is no lock yet for this row, lets create one.
        self.document = dict(subject=self.subject, type="transaction",
                             lock_time=self.current_lock)
        store.latest_collection.save(self.document)

        # We hold a lock now:
        self.locked = True
        return

    raise data_store.TransactionError("Subject %s is locked" % subject)

  def DeleteAttribute(self, predicate):
    self.store.DeleteAttributes(self.subject, [predicate], sync=True,
                                token=self.token)

  def Resolve(self, predicate, decoder=None):
    return self.store.Resolve(self.subject, predicate, decoder=decoder,
                              token=self.token)

  def ResolveRegex(self, predicate_regex, decoder=None, timestamp=None):
    return self.store.ResolveRegex(self.subject, predicate_regex,
                                   decoder=decoder, token=self.token,
                                   timestamp=timestamp)

  def Set(self, predicate, value, timestamp=None, replace=None):
    self.store.Set(self.subject, predicate, value, timestamp=timestamp,
                   replace=replace, token=self.token)

  def Abort(self):
    self.Commit()

  def Commit(self):
    if self.locked:
      # Remove the lock on the document:
      if not self.store.latest_collection.find_and_modify(
          query=self.document,
          update=dict(subject=self.subject, type="transaction", lock_time=0)):
        raise data_store.TransactionError("Lock was overridden for %s." %
                                          self.subject)
      self.locked = False

  def __del__(self):
    try:
      self.Abort()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass


def Decode(document, decoder=None):
  """Decodes from a value using the protobuf specified."""
  value = document.get("int_value")
  if value is None:
    value = document.get("str_value")

  if value is None:
    value = str(document.get("value"))

  if decoder:
    result = decoder()
    # Try if the retrieved type is directly supported.
    result.ParseFromDataStore(value)
    return result

  return value


def _Encode(document, value):
  """Encodes the value into the document.

  Args:
    document: The mogo document which will receive this new value.
    value: A value to be encoded in the database.

  Returns:
    The modified document.
  """
  if hasattr(value, "SerializeToDataStore"):
    value = value.SerializeToDataStore()
  elif hasattr(value, "SerializeToString"):
    value = value.SerializeToString()

  if isinstance(value, (long, int)):
    document["int_value"] = value
  elif isinstance(value, str):
    document["value"] = binary.Binary(value)
  else:
    document["str_value"] = utils.SmartUnicode(value)

  return document
