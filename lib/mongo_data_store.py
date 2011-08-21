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

"""An implementation of a data store based on mongo."""


import logging
import random
import re
import time
from bson import binary
from google.protobuf import message
import pymongo
from pymongo import errors

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


class HasPredicateFilter(Filter):

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name
    Filter.__init__(self)

  def FilterExpression(self):
    return {utils.SmartUnicode(self.attribute_name): {"$exists": True}}


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def FilterExpression(self):
    spec = {}
    for part in self.parts:
      spec.update(part.FilterExpression())

    return spec


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

    return {utils.SmartUnicode(self.attribute_name) + ".v":
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

    return {"_id": {"$regex": self.regex}}


class Transaction(data_store.Transaction):
  """Implement transactions in mongo."""

  def __init__(self, ds, subject):
    self.collection = ds.collection
    self.subject = subject

    # Bring all the data over to minimize round trips
    self._cache = self.collection.find_one(subject) or {}

    # Initial lock number is a random number to avoid a race on creating new
    # documents.
    self.version = self._cache.get("_lock")
    if not self.version:
      # This object is not currently present or versioned, Create it
      try:
        self.collection.update(dict(_id=subject),
                               {"$set": {"_lock": random.randint(1, 1e6)}},
                               upsert=True, safe=True)
        # Re-read the lock to ensure we do not have a race
        self._cache = self.collection.find_one(subject)
        self.version = self._cache.get("_lock")
      except errors.PyMongoError, e:
        logging.error("Mongo Error %s", e)
        raise data_store.Error(str(e))

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
    self._to_update[predicate] = values

  def ResolveRegex(self, predicate_regex, decoder=None,
                   timestamp=data_store.NEWEST_TIMESTAMP):
    """Retrieve a set of value matching for this subject's predicate."""
    regex = re.compile(predicate_regex)
    results = {}

    for key, values in self._cache.items():
      if regex.match(key):
        results.setdefault(key, []).extend(values)

    # Sort by ascending timestamp
    for value in results.values():
      value.sort(key=lambda x: x["t"])

    for key, values in results.items():
      if timestamp == data_store.NEWEST_TIMESTAMP:
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

          if (timestamp == data_store.ALL_TIMESTAMPS or
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

  def DeleteSubject(self):
    self.collection.remove(self.subject)
    return self

  def Commit(self):
    """Commit the transaction."""
    if self._committed:
      logging.error("Attempt to commit transaction multiple times...")
      return

    self._committed = True

    # We set the entire object now:
    if self._to_update:
      spec = dict(_id=URNEncode(self.subject))
      try:
        spec["_lock"] = self._cache["_lock"]
      except KeyError: pass

      self._to_update["_lock"] = self.version + 1
      # There are basically three cases here:

      #1) The document does not already exist. Nothing will match spec, and this
      #   will insert a new document (because of the upsert=True). The
      #   transaction succeeds.

      #2) The document exists and matches spec - the same document will be
      #   updated. The _lock version will be incremented. The transaction
      #   succeeds.

      #3) The document exists but does not match spec. This is likely because
      #   someone else has modified it since we opened for read. We will try to
      #   add a new document (as in 1 above), but this will raise because there
      #   already is a document with the same ID. We therefore trap this
      #   exception and emit a TransactionError. Transaction fails.
      try:
        self.collection.update(spec, {"$set": self._to_update},
                               upsert=True, safe=True)
      except errors.OperationFailure, e:
        # Transaction failed.
        raise data_store.TransactionError(str(e))

  def Abort(self):
    # Nothing to do if we abort
    pass


class MongoDataStore(data_store.DataStore):
  """A Mongo based data store."""

  def __init__(self):
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

  def Set(self, subject, attribute, value, timestamp=None, replace=True,
          sync=True):
    """Set a new value for this subject's predicate."""
    if timestamp is None:
      timestamp = time.time() * 1000

    attribute = utils.SmartUnicode(attribute)
    subject = utils.SmartUnicode(subject)

    # Not replacing is expensive since we need to fetch the previous result
    # first.
    if not replace:
      records = self.collection.find_one(subject, fields=[attribute]) or {}
      values = records.get(attribute, [])
    else:
      values = []

    # Store all values as binary - we will take care of encoding ourselves.
    values.append(dict(v=_Encode(value), t=timestamp))

    # Save the data
    self.collection.save({"_id": URNEncode(subject), attribute: values})

  def Resolve(self, subject, attribute, decoder=None):
    """Retrieve a value set for a subject's predicate."""
    attribute = utils.SmartUnicode(attribute)
    subject = utils.SmartUnicode(subject)

    records = self.collection.find_one(URNEncode(subject),
                                       fields=[URNEncode(attribute)]) or {}
    values = records.get(attribute)
    value, timestamp = None, 0
    if values:
      value = _Decode(values[0]["v"], decoder)
      timestamp = values[0]["t"]

    return value, timestamp

  def MultiSet(self, subject, values, timestamp=None, replace=True, sync=True):
    """Set multiple predicates' values for this subject in one operation."""
    if timestamp is None:
      timestamp = time.time() * 1000

    subject = utils.SmartUnicode(subject)

    spec = dict(_id=URNEncode(subject))

    document = dict()
    for attribute, value in values.items():
      document.setdefault(attribute, []).append(
          dict(v=_Encode(value), t=timestamp))

    self._MultiSet(subject, document, spec)

  def _MultiSet(self, subject, document, spec):
    if document:
      # First try to update the data
      try:
        result = self.collection.update(spec, {"$set": document},
                                        upsert=False, safe=True)
      except errors.PyMongoError, e:
        logging.error("Mongo Error %s", e)
        raise data_store.Error(str(e))

      # If the document does not already exist, just save a new one
      if not result["updatedExisting"]:
        document["_id"] = URNEncode(subject)
        self.collection.save(document)

  def DeleteAttributes(self, subject, attributes):
    self.collection.update(dict(_id=URNEncode(subject)), {"$unset": dict(
        [(utils.SmartUnicode(x), 1) for x in attributes])},
                           upsert=False, safe=False)

  def MultiResolveRegex(self, subjects, predicate_regex,
                        decoder=None, timestamp=None):
    """Retrieve a bunch of subjects in one round trip."""
    # Allow users to specify a single string here.
    if type(predicate_regex) == str:
      predicate_regex = [predicate_regex]

    predicate_res = [re.compile(x) for x in predicate_regex]
    # Only fetch the subjects we care about
    spec = {"$or": [dict(_id=URNEncode(x)) for x in subjects]}
    result = {}

    for document in self.collection.find(spec):
      subject = document["_id"]
      for key, values in document.items():
        # only proceed if a the key matches any of the subject_res
        for predicate in predicate_res:
          if predicate.match(key) and isinstance(values, list):
            for value_obj in values:
              timestamp = value_obj["t"]
              value = _Decode(value_obj["v"], decoder)
              result.setdefault(subject, []).append((key, value, timestamp))
            break

    return result

  def ResolveRegex(self, subject, predicate_regex,
                   decoder=None, timestamp=None):
    result = self.MultiResolveRegex([subject], predicate_regex, decoder=decoder,
                                    timestamp=timestamp).get(subject, [])
    result.sort(key=lambda a: a[0])
    return result

  def Query(self, attributes=None, filter_obj="", subject_prefix="",
            subjects=None, limit=100):
    """Selects a set of subjects based on filters."""
    spec = filter_obj.FilterExpression()
    try:
      skip, limit = limit
    except TypeError:
      skip = 0

    if attributes is None: attributes = []

    # Make this lookup fast
    if subjects:
      subjects = set(subjects)
    attributes = [utils.SmartUnicode(x) for x in attributes]

    for document in self.collection.find(
        spec=spec, fields=attributes, skip=skip,
        limit=limit, slave_okay=True):
      subject = document["_id"]
      if not subject.startswith(subject_prefix):
        continue

      if subjects and subject not in subjects: continue

      result = dict(subject=(subject, 0))
      for key, values in document.items():
        if isinstance(values, list):
          result[key] = (_Decode(values[-1]["v"]), values[-1]["t"])

      yield result

  def Transaction(self, subject):
    return Transaction(self, subject)


def _Decode(value, decoder=None):
  """Decode from a value using the protobuf specified."""
  if value and decoder:
    result = decoder()
    try:
      result.ParseFromString(utils.SmartStr(value))
    except (message.DecodeError, UnicodeError): pass

    return result

  return value


def _Encode(value):
  """Encode the value into a Binary BSON object or a unicode object.

  Mongo can only store certain types of objects in the database. We can store
  everything as a Binary blob but then regex dont work on it. Otherwise we store
  unicode objects (or integers).

  Args:
    value: A value to be encoded in the database.

  Returns:
    something that mongo can store (unicode or Binary blob).
  """
  try:
    # We can store a binary object but regex dont apply to it:
    return binary.Binary(value.SerializeToString())
  except AttributeError:
    # Or a unicode object
    try:
      return utils.SmartUnicode(value)
    except UnicodeError:
      # Or a binary object of a string
      return binary.Binary(value)


def URNEncode(value):
  return utils.SmartStr(value)
