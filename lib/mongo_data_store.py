#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

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

"""An implementation of a data store based on mongo."""


import logging
import random
import re
import time
from bson import binary
import pymongo
from pymongo import errors
from google.protobuf import message

from grr.client import conf as flags
from grr.lib import data_store
from grr.lib import registry
from grr.lib import utils

flags.DEFINE_string("mongo_server", "127.0.0.1:27017",
                    "The mongo server location (hostname:port). "
                    "By default use localhost.")

flags.DEFINE_string("mongo_db_name", "grr",
                    "The mongo database name")

FLAGS = flags.FLAGS


# These are filters
class Filter(object):
  """Baseclass for filters."""

  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def FilterExpression(self):
    return {}


class HasPredicateFilter(Filter):

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name
    Filter.__init__(self)

  def FilterExpression(self):
    return {EscapeKey(self.attribute_name): {
        "$exists": True}}


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def FilterExpression(self):
    return {"$and": [part.FilterExpression() for part in self.parts]}


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
    self.attribute_name = attribute_name
    super(PredicateContainsFilter, self).__init__()

  def FilterExpression(self):
    # If no search term specified we allow the column to not even be
    # set. Without this statement we produce a filter which requires
    # the column to be set.
    if not self.regex: return {}

    return {EscapeKey(self.attribute_name) + ".v":
            {"$regex": self.regex}}


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

    return {"_id": {"$regex": EscapeRegex(self.regex)}}


class PredicateGreaterThanFilter(Filter):
  """A filter to be applied to DataStore.Query.

  This filters all subjects which have this predicate greater than the value
  specified.
  """

  def __init__(self, attribute_name, value):
    """Constructor.

    Args:
       attribute_name: The attribute name must be set.
       value: The value that attribute must be less than.
    """
    self.attribute_name = attribute_name
    self.value = value
    super(PredicateGreaterThanFilter, self).__init__()

  def FilterExpression(self):
    return {EscapeKey(self.attribute_name) + ".v": {
        "$gt": long(self.value)}}


class PredicateGreaterEqualFilter(PredicateGreaterThanFilter):

  def FilterExpression(self):
    return {EscapeKey(self.attribute_name) + ".v": {
        "$ge": long(self.value)}}


class PredicateLessThanFilter(Filter):
  """A filter to be applied to DataStore.Query.

  This filters all subjects which have this predicate greater than the value
  specified.
  """

  def __init__(self, attribute_name, value):
    """Constructor.

    Args:
       attribute_name: The attribute name must be set.
       value: The value that attribute must be less than.
    """
    self.attribute_name = attribute_name
    self.value = value
    super(PredicateLessThanFilter, self).__init__()

  def FilterExpression(self):
    return {EscapeKey(self.attribute_name) + ".v": {
        "$lt": long(self.value)}}


class PredicateLessEqualFilter(PredicateLessThanFilter):

  def FilterExpression(self):
    return {EscapeKey(self.attribute_name) + ".v": {
        "$le": long(self.value)}}


class Transaction(data_store.Transaction):
  """Implement transactions in mongo."""

  def __init__(self, ds, subject, token=None):
    ds.security_manager.CheckAccess(token, [subject], "w")
    self.collection = ds.collection
    self.subject = subject
    self.token = token

    # Bring all the data over to minimize round trips
    encoded_cache = self.collection.find_one(EscapeKey(subject)) or {}
    self._cache = {}
    for (k, v) in encoded_cache.items():
      self._cache[DecodeKey(k)] = v

    # Initial lock number is a random number to avoid a race on creating new
    # documents.
    self.version = self._cache.get("_lock")
    if not self.version:
      # This object is not currently present or versioned, Create it
      try:
        self.collection.update(dict(_id=EscapeKey(subject)),
                               {"$set": {"_lock": random.randint(1, 1e6)}},
                               upsert=True, safe=True)
        # Re-read the lock to ensure we do not have a race
        self._cache = self.collection.find_one(EscapeKey(subject))
        self.version = self._cache.get("_lock")
      except errors.PyMongoError as e:
        logging.error(u"Mongo Error %s", utils.SmartUnicode(e))
        raise data_store.TransactionError(utils.SmartUnicode(e))

    self._to_update = {}
    self._committed = False

  def Set(self, predicate, value, timestamp=None, replace=True):
    """Set a new value for this subject's predicate."""
    if not replace:
      # Merge with old values
      values = self._cache.get(predicate, [])
    else:
      # clear all values
      values = []

    predicate = utils.SmartUnicode(predicate)

    if timestamp is None:
      timestamp = time.time() * 1e6

    values.append(dict(v=_Encode(value), t=timestamp))

    self._cache[predicate] = values
    self._to_update[EscapeKey(predicate)] = values

  def ResolveRegex(self, predicate_regex, decoder=None,
                   timestamp=None):
    """Retrieve a set of value matching for this subject's predicate."""
    regex = re.compile(predicate_regex)
    results = {}

    for key, values in self._cache.items():
      if regex.match(key):
        results.setdefault(key, []).extend(values)

    # Sort by ascending timestamp
    for value in results.values():
      value.sort(key=lambda x: x["t"])

    keys = results.keys()
    keys.sort()

    for key in keys:
      values = results[key]

      if timestamp is None or timestamp == data_store.DB.NEWEST_TIMESTAMP:
        value = _Decode(values[-1]["v"], decoder)
        value_timestamp = values[-1]["t"]
        yield (key, value, value_timestamp)
      else:
        try:
          start, end = timestamp
        except ValueError:
          start, end = 0, timestamp

        for value_dict in values:
          value = _Decode(value_dict["v"], decoder)
          value_timestamp = value_dict["t"]

          if (timestamp == data_store.DB.ALL_TIMESTAMPS or
              (value_timestamp > start and value_timestamp <= end)):
            yield (key, value, value_timestamp)

  def ResolveMulti(self, predicates, decoder=None):
    for predicate in predicates:
      if predicate in self._cache:
        values = self._cache.get(predicate, [])
        if values:
          yield predicate, _Decode(values[-1]["v"], decoder), values[-1]["t"]

  def Resolve(self, predicate, decoder=None):
    for _, value, timestamp in self.ResolveMulti([predicate], decoder=decoder):
      return value, timestamp

    return None, 0

  def DeleteAttribute(self, predicate):
    predicate = utils.SmartUnicode(predicate)
    self._cache[predicate] = self._to_update[predicate] = []

  def Commit(self):
    """Commit the transaction."""
    if self._committed:
      logging.error("Attempt to commit transaction multiple times...")
      return

    self._committed = True

    # We set the entire object now:
    if self._to_update:
      spec = dict(_id=URNEncode(EscapeKey(self.subject)))
      try:
        spec["_lock"] = self._cache["_lock"]
      except KeyError:
        pass

      self._to_update["_lock"] = self.version + 1
      # There are basically three cases here:

      # 1) The document does not already exist. Nothing will match spec, and
      #    this will insert a new document (because of the upsert=True). The
      #    transaction succeeds.

      # 2) The document exists and matches spec - the same document will be
      #    updated. The _lock version will be incremented. The transaction
      #    succeeds.

      # 3) The document exists but does not match spec. This is likely because
      #    someone else has modified it since we opened for read. We will try to
      #    add a new document (as in 1 above), but this will raise because there
      #    already is a document with the same ID. We therefore trap this
      #    exception and emit a TransactionError. Transaction fails.
      try:
        self.collection.update(spec, {"$set": self._to_update},
                               upsert=True, safe=True)
      except errors.OperationFailure as e:
        # Transaction failed.
        raise data_store.TransactionError(utils.SmartUnicode(e))

  def Abort(self):
    # Nothing to do if we abort
    pass


def EscapeKey(key):
  return utils.SmartUnicode(key).replace(u".", u"¿")


def DecodeKey(key):
  return utils.SmartUnicode(key).replace(u"¿", u".")


def EscapeRegex(regex):
  # TODO(user): This is not perfect, but it's really hard to parse the regex
  # correctly to do the right thing so we just use this heuristics for now.
  return regex.replace(r"\.", u"¿")


class MongoDataStore(data_store.DataStore):
  """A Mongo based data store."""

  def __init__(self):
    super(MongoDataStore, self).__init__()
    if FLAGS.mongo_server:
      location, port = FLAGS.mongo_server.split(":")
      port = int(port)

      connection = pymongo.Connection(location, port)
    else:
      connection = pymongo.Connection()

    # For now use a single "data" collection
    self.db_handle = connection[FLAGS.mongo_db_name]
    self.collection = self.db_handle.data
    self.Filter = Filter

  def Resolve(self, subject, attribute, decoder=None, token=None):
    """Retrieves a value set for a subject's predicate."""
    self.security_manager.CheckAccess(token, [subject], "r")
    attribute = EscapeKey(attribute)
    subject = EscapeKey(subject)

    records = self.collection.find_one(URNEncode(subject),
                                       fields=[URNEncode(attribute)]) or {}
    values = records.get(attribute)
    value, timestamp = None, 0
    if values:
      value = _Decode(values[0]["v"], decoder)
      timestamp = values[0]["t"]

    return value, timestamp

  def ResolveMulti(self, subject, predicates, decoder=None, token=None):
    """Resolves multiple predicates at once for one subject."""
    subject = utils.SmartUnicode(subject)
    self.security_manager.CheckAccess(token, [subject], "r")
    subject = EscapeKey(subject)

    predicates = [EscapeKey(s) for s in predicates]
    records = self.collection.find_one(URNEncode(subject), fields=predicates)
    for predicate in predicates:
      record = records.get(predicate)
      if not record:
        continue
      timestamp = record[0]["t"]
      value = _Decode(record[0]["v"], decoder)

      yield DecodeKey(predicate), value, timestamp

  def DeleteSubject(self, subject, token=None):
    """Completely deletes all information about the subject."""
    self.security_manager.CheckAccess(token, [subject], "w")
    self.collection.remove(EscapeKey(subject))

  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation."""
    _ = sync
    self.security_manager.CheckAccess(token, [subject], "w")
    subject = utils.SmartUnicode(subject)

    # TODO(user): This could probably be combined with setting.
    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    spec = dict(_id=URNEncode(EscapeKey(subject)))

    # Do we need to merge old data with the new data? If so we re-fetch the old
    # data here.
    if not replace:
      document = self.collection.find_one(
          URNEncode(EscapeKey(subject)),
          fields=[URNEncode(EscapeKey(x)) for x in values.keys()]) or {}

      if "_id" in document:
        del document["_id"]
    else:
      document = dict()

    # Merge the new data with it.
    for attribute, seq in values.items():
      for value in seq:
        try:
          value, element_timestamp = value
        except (TypeError, ValueError):
          element_timestamp = timestamp

        if element_timestamp is None:
          element_timestamp = time.time() * 1e6

        vals = document.setdefault(EscapeKey(attribute), [])
        vals.append(dict(v=_Encode(value), t=int(element_timestamp)))

    self._MultiSet(subject, document, spec)

  def _MultiSet(self, subject, document, spec):
    if document:
      # First try to update the data
      try:
        result = self.collection.update(spec, {"$set": document},
                                        upsert=False, safe=True)
      except errors.PyMongoError as e:
        logging.error("Mongo Error %s", e)
        raise data_store.Error(utils.SmartUnicode(e))

      # If the document does not already exist, just save a new one
      if not result["updatedExisting"]:
        document["_id"] = URNEncode(EscapeKey(subject))
        self.collection.save(document)

  def DeleteAttributes(self, subject, attributes, token=None):
    self.security_manager.CheckAccess(token, [subject], "w")

    to_del = dict([(EscapeKey(x), 1) for x in attributes])
    self.collection.update(dict(_id=URNEncode(EscapeKey(subject))),
                           {"$unset": to_del},
                           upsert=False, safe=False)

  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None, limit=None):
    """Retrieves a bunch of subjects in one round trip."""
    self.security_manager.CheckAccess(token, subjects, "r")

    if not subjects:
      return {}

    # Allow users to specify a single string here.
    if type(predicate_regex) == str:
      predicate_regex = [predicate_regex]

    predicate_res = [re.compile(EscapeRegex(x)) for x in predicate_regex]
    # Only fetch the subjects we care about
    spec = {"$or": [dict(_id=URNEncode(EscapeKey(x))) for x in subjects]}
    result = {}

    result_count = 0
    for document in self.collection.find(spec):
      subject = DecodeKey(document["_id"])
      for key, values in document.items():
        # only proceed if a the key matches any of the subject_res
        for predicate in predicate_res:
          if predicate.match(key) and isinstance(values, list):
            for value_obj in values:
              timestamp = value_obj["t"]
              value = _Decode(value_obj["v"], decoder)
              result.setdefault(subject, []).append(
                  (DecodeKey(key), value, timestamp))
              result_count += 1
              if limit and result_count >= limit:
                return result
            break

    return result

  def ResolveRegex(self, subject, predicate_regex, token=None,
                   decoder=None, timestamp=None, limit=None):
    result = self.MultiResolveRegex(
        [subject], predicate_regex, decoder=decoder,
        timestamp=timestamp, token=token, limit=limit).get(subject, [])
    result.sort(key=lambda a: a[0])
    return result

  def Query(self, attributes=None, filter_obj=None, subject_prefix="",
            token=None, subjects=None, limit=100):
    """Selects a set of subjects based on filters."""
    if filter_obj:
      spec = filter_obj.FilterExpression()
    else:
      spec = {}

    try:
      skip, limit = limit
    except TypeError:
      skip = 0

    if attributes is None: attributes = []

    # Make this lookup fast
    if subjects:
      subjects = set(subjects)
    attributes = [EscapeKey(x) for x in attributes]

    result_subjects = []

    if subject_prefix:
      regex = data_store.EscapeRegex(
          EscapeKey(subject_prefix))
      spec = {"$and": [spec, {"_id": {"$regex": "^" + regex}}]}

    if subjects:
      expressions = []
      for subject in subjects:
        regex = data_store.EscapeRegex(EscapeKey(subject))
        expressions.append({"_id": {"$regex": "^" + regex + "$"}})

      spec = {"$and": [spec, {"$or": expressions}]}

    for document in self.collection.find(
        spec=spec, fields=attributes, skip=skip,
        limit=limit, slave_okay=True):
      try:
        subject = DecodeKey(document["_id"])
        # Only yield those subjects which we are allowed to view.
        self.security_manager.CheckAccess(token, [subject], "r")

        result = dict(subject=(subject, 0))
        for key, values in document.items():
          if isinstance(values, list):
            result[key] = (_Decode(values[-1]["v"]), values[-1]["t"])

        result_subjects.append(result)
      except data_store.UnauthorizedAccess:
        pass

    result_subjects.sort()
    total_count = len(result_subjects)
    result_set = data_store.ResultSet(result_subjects)
    result_set.total_count = total_count
    return result_set

  def Transaction(self, subject, token=None):
    return Transaction(self, subject, token=token)

  def Flush(self):
    pass


def _Decode(value, decoder=None):
  """Decodes from a value using the protobuf specified."""
  if value and decoder:
    result = decoder()
    try:
      # Try if the retrieved type is directly supported.
      result.ParseFromDataStore(value)
      return result
    except (AttributeError, ValueError, message.DecodeError):
      pass
    try:
      result.ParseFromString(utils.SmartStr(value))
    except (message.DecodeError, UnicodeError):
      pass

    return result

  if isinstance(value, binary.Binary):
    return str(value)

  return value


def _StorableObject(obj):
  # Mongo can handle integer types directly
  if isinstance(obj, (int, long)):
    return obj
  elif isinstance(obj, str):
    return binary.Binary(obj)
  try:
    return utils.SmartUnicode(obj)
  except UnicodeError:
    # We can store a binary object but regex dont apply to it:
    return binary.Binary(obj)


def _Encode(value):
  """Encodes the value into a Binary BSON object or a unicode object.

  Mongo can only store certain types of objects in the database. We
  can store everything as a Binary blob but then regex dont work on
  it. So, we store the object as an integer or an unicode object if
  possible and, if that fails, we return a binary blob.

  Args:
    value: A value to be encoded in the database.

  Returns:
    something that mongo can store (integer, unicode or Binary blob).
  """
  if hasattr(value, "SerializeToDataStore"):
    result = value.SerializeToDataStore()
    return _StorableObject(result)

  if hasattr(value, "SerializeToString"):
    result = value.SerializeToString()
    return _StorableObject(result)

  return _StorableObject(value)


def URNEncode(value):
  return utils.SmartStr(value)
