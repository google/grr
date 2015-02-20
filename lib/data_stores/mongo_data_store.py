#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mongo."""


import hashlib
import threading
import time
from bson import binary
from bson import objectid
import pymongo
from pymongo import errors
import logging

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import utils


class MongoDataStore(data_store.DataStore):
  """A Mongo based data store."""

  def __init__(self):
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

    # Ensure we have the correct indexes.
    for idx in ["subject", "predicate", "timestamp"]:
      self.latest_collection.ensure_index(idx)
      self.versioned_collection.ensure_index(idx)

    super(MongoDataStore, self).__init__()

  def _GetCursor(self, spec, timestamp, limit):
    """Create a mongo cursor based on the timestamp restriction."""

    if timestamp == self.NEWEST_TIMESTAMP or timestamp is None:
      collection = self.latest_collection
    elif timestamp == self.ALL_TIMESTAMPS:
      collection = self.versioned_collection
    elif isinstance(timestamp, tuple):
      collection = self.versioned_collection
      start, end = timestamp
      spec = {"$and": [dict(timestamp={"$gte": int(start)}),
                       dict(timestamp={"$lte": int(end)}),
                       spec]}
    else:
      raise data_store.Error("Undefined timestamp specification.")

    cursor = collection.find(spec).sort("timestamp", pymongo.DESCENDING)

    if limit:
      cursor = cursor.limit(limit)

    return cursor

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None,
                   token=None):
    """Resolves multiple attributes at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attributes))

    # Build a query spec.
    spec = {"$and": [
        # Subject matches any of the requested subjects.
        dict(subject=utils.SmartUnicode(subject)),
        {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in attributes]},
    ]}

    results_returned = 0
    for document in self._GetCursor(spec, timestamp, 0):
      subject = document["subject"]
      value = Decode(document)
      if limit:
        if results_returned >= limit:
          return
        results_returned += 1

      yield (document["predicate"], value, document["timestamp"])

  def DeleteSubject(self, subject, sync=False, token=None):
    """Completely deletes all information about the subject."""
    _ = sync
    subject = utils.SmartUnicode(subject)
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    self.latest_collection.remove(dict(subject=subject))
    self.versioned_collection.remove(dict(subject=subject))

  def MultiSet(self, subject, values, timestamp=None, replace=True,
               sync=True, to_delete=None, token=None):
    """Set multiple attributes' values for this subject in one operation."""
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

        if entry_timestamp is None:
          entry_timestamp = timestamp

        attribute = utils.SmartUnicode(attribute)
        prefix = attribute.split(":", 1)[0]

        document = dict(subject=subject, timestamp=int(entry_timestamp),
                        predicate=attribute, prefix=prefix)
        _Encode(document, value)
        documents.append(document)
        latest[attribute] = document

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
      for attribute, document in latest.items():
        document.pop("_id", None)
        self.latest_collection.update(
            dict(subject=subject, predicate=attribute, prefix=prefix),
            document, upsert=True, w=1 if sync else 0)

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
    """Remove all the attributes from this subject."""
    _ = sync  # Unused attribute, mongo is always synced.
    subject = utils.SmartUnicode(subject)
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    if not attributes:
      # Nothing to delete.
      return

    # Build a spec to select the subject and any of the attributes.
    spec = {"$and": [
        dict(subject=subject),
        {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in attributes]},
    ]}

    if not start and not end:
      # Just delete all the versions.
      self.versioned_collection.remove(spec)
      self.latest_collection.remove(spec)
      return

    unversioned_spec = {"$and": [
        dict(subject=subject),
        {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in attributes]},
    ]}

    if start:
      spec["$and"].append(dict(timestamp={"$gte": int(start)}))

    if not end:
      # We can optimize this case since the latest version will always
      # be unchanged or deleted.
      self.versioned_collection.remove(spec)
      self.latest_collection.remove(spec)
      return

    spec["$and"].append(dict(timestamp={"$lte": int(end)}))
    self.versioned_collection.remove(spec)

    to_delete = set(attributes)
    to_set = {}
    cursor = self.versioned_collection.find(unversioned_spec).sort("timestamp")
    for document in cursor:
      value = Decode(document)
      attribute = document["predicate"]
      to_delete.discard(attribute)
      timestamp = document["timestamp"]
      prefix = attribute.split(":", 1)[0]
      document = dict(subject=subject, timestamp=timestamp,
                      predicate=attribute, prefix=prefix)
      _Encode(document, value)
      to_set[attribute] = document

    if to_delete:
      delete_spec = {"$and": [
          dict(subject=subject),
          {"$or": [dict(predicate=utils.SmartUnicode(x)) for x in attributes]},
      ]}
      self.latest_collection.remove(delete_spec)

    if to_set:
      for document in to_set.itervalues():
        self.latest_collection.update(
            dict(subject=subject, predicate=attribute, prefix=prefix),
            document, upsert=True, w=1 if sync else 0)

  def MultiResolveRegex(self, subjects, attribute_regex, timestamp=None,
                        limit=None, token=None):
    """Retrieves a bunch of subjects in one round trip."""
    self.security_manager.CheckDataStoreAccess(
        token, subjects, self.GetRequiredResolveAccess(attribute_regex))

    if not subjects:
      return {}

    result = {}
    dedup_set = set()

    # Build a query spec.
    # Subject matches any of the requested subjects.
    spec = dict(subject={"$in": [utils.SmartUnicode(x) for x in subjects]})

    # For a wildcard we just select all attributes by not applying a condition
    # at all.
    if isinstance(attribute_regex, basestring):
      attribute_regex = [attribute_regex]

    if attribute_regex != [".*"]:
      spec = {"$and": [
          spec,
          {"$or": [dict(predicate={"$regex": x}) for x in attribute_regex]},
      ]}

    for document in self._GetCursor(spec, timestamp, limit):
      subject = document["subject"]
      value = Decode(document)
      attribute = document.get("predicate")
      if attribute is None:
        # This might not be a normal aff4 attribute - transactions are one
        # example for this.
        continue

      # Sometimes due to race conditions in mongodb itself (upsert operation is
      # not atomic), the latest_collection can contain multiple versions of the
      # same attribute.
      if ((timestamp == self.NEWEST_TIMESTAMP or timestamp is None) and
          (subject, attribute) in dedup_set):
        continue

      dedup_set.add((subject, attribute))
      result.setdefault(subject, []).append(
          (attribute, value, document["timestamp"]))

    return result.iteritems()

  def MultiResolveLiteral(self, subjects, attributes, token=None,
                          timestamp=None, limit=None):
    """Retrieves a bunch of subjects in one round trip."""
    self.security_manager.CheckDataStoreAccess(
        token, subjects, self.GetRequiredResolveAccess(attributes))

    if not subjects:
      return {}

    result = {}

    # Build a query spec.
    spec = {"$and": [
        dict(subject={"$in": [utils.SmartUnicode(x) for x in subjects]}),
        dict(predicate={"$in": [utils.SmartUnicode(x) for x in attributes]}),
    ]}

    for document in self._GetCursor(spec, timestamp, limit):
      subject = document["subject"]
      value = Decode(document)
      result.setdefault(subject, []).append(
          (document["predicate"], value, document["timestamp"]))

    return result

  def Size(self):
    info = self.db_handle.command("dbStats")
    return info["storageSize"]

  def Transaction(self, subject, lease_time=None, token=None):
    return MongoTransaction(self, subject, lease_time=lease_time, token=token)


class MongoTransaction(data_store.CommonTransaction):
  """The Mongo data store transaction object.

  This object does not aim to ensure ACID like consistently. We only ensure that
  two simultaneous locks can not be held on the same RDF subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError.

  A lock is considered expired after a certain time.
  """

  lock_creation_lock = threading.Lock()

  locked = False

  def __init__(self, store, subject, lease_time=None, token=None):
    """Ensure we can take a lock on this subject."""
    super(MongoTransaction, self).__init__(store, subject,
                                           lease_time=lease_time, token=token)
    self.object_id = objectid.ObjectId(
        hashlib.sha256(utils.SmartStr(self.subject)).digest()[:12])

    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    self.expires = time.time() + lease_time
    self.document = self.store.latest_collection.find_and_modify(
        query={"_id": self.object_id, "expires": {"$lt": time.time()}},
        update=dict(_id=self.object_id, expires=self.expires),
        upsert=False, new=True)

    if self.document:
      # Old transaction expired and we hold a lock now:
      self.locked = True
      return

    # Maybe the lock did not exist yet. To create it, we use a lock to reduce
    # the chance of deleting some other lock created at the same time. Note that
    # there still exists a very small race if this happens in multiple processes
    # at the same time.
    with self.lock_creation_lock:
      document = self.store.latest_collection.find({"_id": self.object_id})
      if not document.count():
        self.UpdateLease(lease_time)

        cursor = self.store.latest_collection.find({"_id": self.object_id})
        if cursor.count() != 1:
          self._DeleteLock()
          logging.warn("Multiple lock rows for %s", subject)
          raise data_store.TransactionError("Error while locking %s." % subject)

        self.document = cursor.next()

        if self.document["expires"] != self.expires:
          raise data_store.TransactionError("Subject %s is locked" % subject)

        # We hold a lock now:
        self.locked = True
        return

    raise data_store.TransactionError("Subject %s is locked" % subject)

  def UpdateLease(self, duration):
    self.expires = time.time() + duration
    self.store.latest_collection.save(
        dict(_id=self.object_id, expires=self.expires))
    if self.document:
      self.document["expires"] = self.expires

  def Abort(self):
    if self.locked:
      self._RemoveLock()

  def Commit(self):
    if self.locked:
      super(MongoTransaction, self).Commit()
      self._RemoveLock()

  def _RemoveLock(self):
    # Remove the lock on the document.
    if not self.store.latest_collection.find_and_modify(
        query=self.document, update=dict(_id=self.object_id, expires=0)):
      raise data_store.TransactionError("Lock was overridden for %s." %
                                        self.subject)
    self.locked = False

  def _DeleteLock(self):
    # Deletes the lock entirely from the document.
    document = dict(_id=self.object_id, expires=self.expires)
    if not self.store.latest_collection.remove(query=document):
      raise data_store.TransactionError(
          "Could not remove lock for %s." % self.subject)
    self.locked = False


def Decode(document):
  """Decodes from a value using the protobuf specified."""
  value = document.get("int_value")
  if value is None:
    value = document.get("str_value")

  if value is None:
    value = str(document.get("value"))

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
