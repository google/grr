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

"""AFF4 interface implementation.

This contains an AFF4 data model implementation.
"""


import abc
import datetime
import posixpath
import StringIO
import time
import urlparse
import zlib

from dateutil import parser

from google.protobuf import message
from grr.client import conf as flags
import logging
from grr.lib import data_store
from grr.lib import lexer
from grr.lib import registry
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_integer("aff4_cache_age", 5,
                     "The number of seconds AFF4 objects live in the cache.")

flags.DEFINE_integer("notification_rules_cache_age", 60,
                     "The number of seconds AFF4 notification rules "
                     "are cached.")

FLAGS = flags.FLAGS


# Factor to convert from seconds to microseconds
MICROSECONDS = 1000000


# Age specifications for opening AFF4 objects.
NEWEST_TIME = "NEWEST_TIME"
ALL_TIMES = "ALL_TIMES"

# Just something to write on an index attribute to make it exist.
EMPTY_DATA = "X"


class Factory(object):
  """A central factory for AFF4 objects."""

  def __init__(self):
    # This is a relatively short lived cache of objects.
    self.cache = utils.AgeBasedCache(max_size=10000,
                                     max_age=FLAGS.aff4_cache_age)
    self.intermediate_cache = utils.FastStore(100)

    # Create a token for system level actions:
    self.root_token = data_store.ACLToken(username="system",
                                          reason="Maintainance")
    self.root_token.supervisor = True

    self.notification_rules = []
    self.notification_rules_timestamp = 0

  def _ParseAgeSpecification(self, age):
    if age == NEWEST_TIME:
      return data_store.DB.NEWEST_TIMESTAMP
    elif age == ALL_TIMES:
      return data_store.DB.ALL_TIMESTAMPS
    elif isinstance(age, (int, long, RDFDatetime)):
      return (0, int(age))
    elif len(age) == 2:
      start, end = age

      return (int(start), int(end))

    raise RuntimeError("Unknown age specification: %s" % age)

  def GetAttributes(self, urns, ignore_cache=False, token=None,
                    age=NEWEST_TIME):
    """Retrieves all the attributes for all the urns."""
    urns = [utils.SmartUnicode(u) for u in set(urns)]
    try:
      if not ignore_cache:
        result = []
        for subject in urns:
          key = self._MakeCacheInvariant(subject, token, age)
          result.append((subject, self.cache.Get(key)))

        return result
    except KeyError:
      pass

    subjects = []
    result = {}
    # If there are any cache misses, we need to go to the data store. So we
    # might as well just re-fetch all the urns again in a single data store
    # round trip.
    for subject, values in data_store.DB.MultiResolveRegex(
        urns, [".*"], timestamp=self._ParseAgeSpecification(age),
        token=token, limit=None).items():

      key = self._MakeCacheInvariant(subject, token, age)
      self.cache.Put(key, values)
      result[subject] = values
      subjects.append(subject)
    return result.items()

  def SetAttributes(self, urn, attributes, to_delete, sync=False, token=None):
    """Sets the attributes in the data store and update the cache."""
    # Force a data_store lookup next.
    try:
      # Expire all entries in the cache for this urn (for all tokens, and
      # timestamps)
      self.cache.ExpireRegEx(data_store.EscapeRegex(urn) + ".+")
    except KeyError:
      pass

    attributes[AFF4Object.SchemaCls.LAST] = [
        RDFDatetime().SerializeToDataStore()]
    to_delete.add(AFF4Object.SchemaCls.LAST)
    data_store.DB.MultiSet(urn, attributes, token=token,
                           replace=False, sync=sync, to_delete=to_delete)

    # TODO(user): This can run in the thread pool since its not time
    # critical.
    self._UpdateIndex(urn, attributes, token)

  def _UpdateIndex(self, urn, attributes, token):
    """Updates any indexes we need."""
    index = {}
    for attribute, values in attributes.items():
      if attribute.index:
        for value, _ in values:
          index.setdefault(attribute.index, []).append((attribute, value))

    if index:
      for index_urn, index_data in index.items():
        aff4index = self.Create(index_urn, "AFF4Index", mode="w", token=token)
        for attribute, value in index_data:
          aff4index.Add(urn, attribute, value)
        aff4index.Flush()

    self._UpdateChildIndex(urn, token)

  def _UpdateChildIndex(self, urn, token):
    """Update the child indexes.

    This function maintains the index for direct child relations. When we set
    an AFF4 path, we always add an attribute like
    index:dir/%(childname)s to its parent. This is written
    asynchronously to its parent.

    In order to query for all direct children of an AFF4 object, we then simple
    get the attributes which match the regex index:dir/.+ which are the
    direct children.

    Args:
      urn: The AFF4 object for which we update the index.
      token: The token to use.
    """
    try:
      # Create navigation aids by touching intermediate subject names.
      while urn.Path() != "/":
        basename = urn.Basename()
        dirname = RDFURN(urn.Dirname())

        try:
          self.intermediate_cache.Get(urn.Path())
          return
        except KeyError:
          data_store.DB.MultiSet(dirname, {
              AFF4Object.SchemaCls.LAST: [RDFDatetime().SerializeToDataStore()],

              # This updates the directory index.
              "index:dir/%s" % utils.SmartStr(basename): [EMPTY_DATA],
              },
                                 token=token, replace=True, sync=False)

          self.intermediate_cache.Put(urn.Path(), 1)

          urn = dirname

    except data_store.UnauthorizedAccess:
      pass

  def _ExpandURNComponents(self, urn, unique_urns):
    """This expands URNs.

    This method breaks the urn into all the urns from its path components and
    adds them to the set unique_urns.

    Args:
      urn: An RDFURN.
      unique_urns: A set to add the components of the urn to.
    """

    x = ROOT_URN
    for component in RDFURN(urn).Path().split("/"):
      if component:
        x = x.Add(component)
        unique_urns.add(x)

  def _MakeCacheInvariant(self, urn, token, age):
    """Returns an invariant key for an AFF4 object.

    The object will be cached based on this key. This function is specifically
    extracted to ensure that we encapsulate all security critical aspects of the
    AFF4 object so that objects do not leak across security boundaries.

    Args:
       urn: The urn of the object.
       token: The access token used to receive the object.
       age: The age policy used to build this object. Should be one
            of ALL_TIMES, NEWEST_TIME or a range.

    Returns:
       A key into the cache.
    """
    return "%s:%s:%s" % (utils.SmartStr(urn), utils.SmartStr(token),
                         self._ParseAgeSpecification(age))

  def Open(self, urn, required_type=None, mode="r", ignore_cache=False,
           token=None, local_cache=None, age=NEWEST_TIME):
    """Opens the named object.

    This instantiates the object from the AFF4 data store.
    Note that the root aff4:/ object is a container for all other
    objects. Opening it for reading will instantiate a AFF4Volume instance, even
    if the row does not exist.

    The mode parameter specifies, how the object should be opened. A read only
    mode will raise when calling Set() on it, while a write only object will
    never read from the data store. Note that its impossible to open an object
    with pure write support (since we have no idea what type it should be
    without reading the data base) - use Create() instead for purely write mode.

    Args:
      urn: The urn to open.

      required_type: If this optional parameter is set, we raise an IOError if
          the object is not an instance of this type. This check is important
          when a different object can be stored in this location.

      mode: The mode to open the file with.
      ignore_cache: Forces a data store read.
      token: The Security Token to use for opening this item.
      local_cache: A dict containing a cache as returned by GetAttributes. If
                   set, this bypasses the factory cache.

      age: The age policy used to build this object. Should be one of
         NEWEST_TIME, ALL_TIMES or a time range given as a tuple (start, end) in
         microseconds since Jan 1st, 1970.

    Returns:
      An AFF4Object instance.

    Raises:
      IOError: If the object is not of the required type.
      AttributeError: If the requested mode is incorrect.
    """

    if mode not in ["w", "r", "rw"]:
      raise AttributeError("Invalid mode %s" % mode)

    if mode == "w":
      raise AttributeError("Can not open an object in write mode. "
                           "Use Create() instead.")

    urn = RDFURN(urn)

    if "r" in mode and (local_cache is None or urn not in local_cache):
      # Warm up the cache. The idea is to prefetch all the path components in
      # the same round trip and make sure this data is in cache, so that as each
      # AFF4 object is instantiated it can read attributes from cache rather
      # than round tripping to the data store.
      unique_urn = set()
      self._ExpandURNComponents(urn, unique_urn)
      local_cache = dict(
          self.GetAttributes(unique_urn,
                             age=age, ignore_cache=ignore_cache,
                             token=token))

    # Read the row from the table.
    result = AFF4Object(urn, mode=mode, token=token, local_cache=local_cache,
                        age=age)

    # Get the correct type.
    aff4_type = result.Get(result.Schema.TYPE, default="AFF4Volume")
    if aff4_type:
      result = result.Upgrade(aff4_type)
      # This is the same type that was already stored so we don't have to
      # rewrite it.
      setattr(result, "_dirty", False)
      setattr(result, "_new_version", False)

    if (required_type is not None and
        not isinstance(result, AFF4Object.classes[required_type])):
      raise IOError("Object of type %s, but required_type is %s" % (
          result.__class__.__name__, required_type))

    return result

  def MultiOpen(self, urns, mode="rw", token=None, required_type=None):
    """Opens a bunch of urns efficiently."""

    if mode not in ["w", "r", "rw"]:
      raise RuntimeError("Invalid mode %s" % mode)

    # Fill up the cache with all the urns
    unique_urn = set()
    for urn in urns:
      self._ExpandURNComponents(urn, unique_urn)

    cache = dict(self.GetAttributes(unique_urn, token=token))

    for urn in urns:
      try:
        if urn in cache:
          yield self.Open(urn, mode=mode, token=token, local_cache=cache,
                          required_type=required_type)
      except IOError:
        pass

  def Stat(self, urns, token=None):
    """Returns metadata about all urns.

    Currently the metadata include type, and last update time.

    Args:
      urns: The urns of the objects to open.
      token: The token to use.

    Yields:
      A dict of metadata.

    Raises:
      RuntimeError: A string was passed instead of an iterable.
    """

    if isinstance(urns, basestring):
      raise RuntimeError("Expected an iterable, not string.")
    for subject, values in data_store.DB.MultiResolveRegex(
        urns, ["aff4:type"], token=token).items():
      yield dict(urn=RDFURN(subject), type=values[0])

  def Create(self, urn, aff4_type, mode="w", token=None, age=NEWEST_TIME,
             ignore_cache=False):
    """Creates the urn if it does not already exist, otherwise opens it.

    If the urn exists and is of a different type, this will also promote it to
    the specified type.

    Args:
       urn: The object to create.
       aff4_type: The desired type for this object.
       mode: The desired mode for this object.
       token: The Security Token to use for opening this item.
       age: The age policy used to build this object. Only makes sense when mode
            has "r".
       ignore_cache: Bypass the aff4 cache.

    Returns:
      An AFF4 object of the desired type and mode.

    Raises:
      AttributeError: If the mode is invalid.
    """

    if mode not in ["w", "r", "rw"]:
      raise AttributeError("Invalid mode %s" % mode)

    urn = RDFURN(urn)

    if "r" in mode:
      # Check to see if an object already exists.
      try:
        return self.Open(urn, mode=mode, token=token, age=age,
                         ignore_cache=ignore_cache).Upgrade(aff4_type)
      except IOError:
        pass

    # Object does not exist, just make it.
    cls = AFF4Object.classes[str(aff4_type)]
    result = cls(urn, mode=mode, token=token, age=age)
    result.Initialize()
    setattr(result, "_new_version", True)
    setattr(result, "_dirty", True)

    return result

  def Delete(self, urn, token=None, limit=1000):
    """Drop all the information about this object.

    DANGEROUS! This recursively deletes all objects contained within the
    specified URN.

    Args:
      urn: The object to remove.
      token: The Security Token to use for opening this item.
      limit: The number of objects to remove.
    Raises:
      RuntimeError: If the urn is too short. This is a safety check to ensure
      the root is not removed.
    """

    urn = RDFURN(urn)
    if len(urn.Path()) < 1:
      raise RuntimeError("URN %s too short. Please enter a valid URN" % urn)

    # Get all the children of this URN and delete them all.
    logging.info("Recursively removing AFF4 Object %s", urn)
    fd = FACTORY.Create(urn, "AFF4Volume", mode="rw", token=token)
    count = 0
    for child in fd.ListChildren():
      logging.info("Removing child %s", child)
      self.Delete(child, token=token)
      count += 1

    if count >= limit:
      logging.info("Object limit reached, there may be further objects "
                   "to delete.")

    logging.info("Removed %s objects", count)
    data_store.DB.DeleteSubject(fd.urn, token=token)

  def RDFValue(self, name):
    return RDFValue.classes.get(name)

  def AFF4Object(self, name):
    return AFF4Object.classes.get(name)

  def Merge(self, first, second):
    """Merge two AFF4 objects and return a new object.

    Args:
      first: The first object (Can be None).
      second: The second object (Can be None).

    Returns:
      A new object with the type of the latest object, but with both first and
      second's attributes.
    """
    if first is None: return second
    if second is None: return first

    # Make first the most recent object, and second the least recent:
    if first.Get("type").age < second.Get("type").age:
      first, second = second, first

    # Merge the attributes together.
    for k, v in second.synced_attributes.items():
      first.synced_attributes.setdefault(k, []).extend(v)

    for k, v in second.new_attributes.items():
      first.new_attributes.setdefault(k, []).extend(v)

    return first

  def Flush(self):
    data_store.DB.Flush()

  def UpdateNotificationRules(self):
    fd = self.Open(RDFURN("aff4:/config/aff4_rules"), mode="r",
                   token=self.root_token)
    self.notification_rules = [rule for rule in fd.OpenChildren()
                               if isinstance(rule, AFF4NotificationRule)]

  def NotifyWriteObject(self, aff4_object):
    current_time = time.time()
    if (current_time - self.notification_rules_timestamp >
        FLAGS.notification_rules_cache_age):
      self.notification_rules_timestamp = current_time
      self.UpdateNotificationRules()

    for rule in self.notification_rules:
      try:
        rule.OnWriteObject(aff4_object)
      except Exception, e:  # pylint: disable=broad-except
        logging.error("Error while applying the rule: %s", e)


class RDFValue(object):
  """Baseclass for values.

  RDFValues are serialized to and from the data store.
  """

  __metaclass__ = registry.MetaclassRegistry

  # This is how the attribute will be serialized to the data store. It must
  # indicate both the type emitted by SerializeToDataStore() and expected by
  # ParseFromDataStore()
  data_store_type = "bytes"

  def __init__(self, serialized=None, age=None):
    """Constructor must be able to take no args.

    Args:
      serialized: Optional string to construct from.
                  Equivalent to ParseFromString()

      age: The age of this entry in microseconds since epoch. If set to None the
           age is set to now.
    """
    if age is None:
      self.age = int(time.time() * MICROSECONDS)
    else:
      self.age = age

    # Allow an RDFValue to be initialized from an identical RDFValue.
    if serialized.__class__ == self.__class__:
      self.ParseFromString(serialized.SerializeToString())

    elif serialized is not None:
      self.ParseFromString(serialized)

  @property
  def age(self):
    return RDFDatetime(self._age)

  @age.setter
  def age(self, value):
    self._age = value

  def ParseFromDataStore(self, data_store_obj):
    """Serialize from an object read from the datastore."""
    return self.ParseFromString(data_store_obj)

  @abc.abstractmethod
  def ParseFromString(self, string):
    """Given a string, parse ourselves from it."""
    pass

  def SerializeToDataStore(self):
    """Serialize to a datastore compatible form."""
    return self.SerializeToString()

  @abc.abstractmethod
  def SerializeToString(self):
    """Serialize into a string which can be parsed using ParseFromString."""
    pass

  def __iter__(self):
    """This allows every RDFValue to be iterated over."""
    yield self

  def Summary(self):
    """Return a summary representation of the object."""
    return str(self)

  @classmethod
  def Fields(cls, name):
    """Return a list of fields which can be queried from this value."""
    return [name]

  @staticmethod
  def ContainsMatch(attribute, filter_implemention, regex):
    return filter_implemention.PredicateContainsFilter(attribute, regex)

  # The operators this type supports in the query language
  operators = dict(contains=(1, "ContainsMatch"))


class RDFBytes(RDFValue):
  """An attribute which holds bytes."""
  data_store_type = "bytes"

  def ParseFromString(self, string):
    self.value = string

  def SerializeToString(self):
    return self.value

  def __str__(self):
    return utils.SmartStr(self.value)

  def __eq__(self, other):
    return self.value == other

  def __ne__(self, other):
    return self.value != other

  def __hash__(self):
    return hash(self.value)

  def __int__(self):
    return int(self.value)

  def __bool__(self):
    return bool(self.value)

  def __nonzero__(self):
    return bool(self.value)


class RDFString(RDFBytes):
  """Represent a simple string."""

  data_store_type = "string"

  @staticmethod
  def Startswith(attribute, filter_implemention, string):
    return filter_implemention.PredicateContainsFilter(
        attribute, "^" + data_store.EscapeRegex(string))

  operators = RDFValue.operators.copy()
  operators["matches"] = (1, "ContainsMatch")
  operators["="] = (1, "ContainsMatch")
  operators["startswith"] = (1, "Startswith")

  def __unicode__(self):
    return utils.SmartUnicode(self.value)

  def SerializeToString(self):
    return utils.SmartStr(self.value)

  def SerializeToDataStore(self):
    return utils.SmartUnicode(self.value)


class RDFSHAValue(RDFBytes):
  """SHA256 hash."""

  data_store_type = "bytes"

  def __str__(self):
    return self.value.encode("hex")


class RDFInteger(RDFString):
  """Represent an integer."""

  data_store_type = "integer"

  def __init__(self, serialized=None, age=None):
    super(RDFInteger, self).__init__(serialized, age)
    if serialized is None:
      self.value = 0

  def ParseFromString(self, string):
    self.value = 0
    if string:
      self.value = int(string)

  def SerializeToDataStore(self):
    """Use varint to store the integer."""
    return int(self.value)

  def Set(self, value):
    if isinstance(value, (long, int)):
      self.value = value
    else:
      self.ParseFromString(value)

  def __long__(self):
    return long(self.value)

  def __int__(self):
    return int(self.value)

  def __lt__(self, other):
    return self.value < other

  def __gt__(self, other):
    return self.value > other

  def __le__(self, other):
    return self.value <= other

  def __ge__(self, other):
    return self.value >= other

  def __add__(self, other):
    return self.value + other

  def __radd__(self, other):
    return self.value + other

  def __iadd__(self, other):
    self.value += other
    return self

  def __mul__(self, other):
    return self.value * other

  def __div__(self, other):
    return self.value / other

  @staticmethod
  def LessThan(attribute, filter_implemention, value):
    return filter_implemention.PredicateLessThanFilter(attribute, long(value))

  @staticmethod
  def GreaterThan(attribute, filter_implemention, value):
    return filter_implemention.PredicateGreaterThanFilter(
        attribute, long(value))

  @staticmethod
  def Equal(attribute, filter_implemention, value):
    return filter_implemention.PredicateNumericEqualFilter(
        attribute, long(value))

  operators = {"<": (1, "LessThan"),
               ">": (1, "GreaterThan"),
               "=": (1, "Equal")}


class RDFDatetime(RDFInteger):
  """A date and time internally stored in MICROSECONDS."""
  converter = MICROSECONDS

  # For now we just store as an integer number of microseconds since the epoch

  def __init__(self, serialized=None, age=None):
    super(RDFDatetime, self).__init__(serialized, age)
    if serialized is None:
      self.Now()

  def Now(self):
    self.value = int(time.time() * self.converter)
    return self

  def __str__(self):
    """Return the date in human readable (UTC)."""
    value = self.value / self.converter
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(value))

  def __unicode__(self):
    return utils.SmartUnicode(str(self))

  def __long__(self):
    return long(self.value)

  def __iadd__(self, other):
    self.value += other
    return self

  def __isub__(self, other):
    return int(other) - self.value

  def __gt__(self, other):
    return self.value > other

  def __lt__(self, other):
    return self.value < other

  def __sub__(self, other):
    return self.value - int(other)

  def __add__(self, other):
    return self.value + other

  @classmethod
  def ParseFromHumanReadable(cls, string, eoy=False):
    """Parse a human readable string of a timestamp (in local time).

    Args:
      string: The string to parse.
      eoy: If True, sets the default value to the end of the year.
           Usually this method returns a timestamp where each field that is
           not present in the given string is filled with values from the date
           January 1st of the current year, midnight. Sometimes it makes more
           sense to compare against the end of a period so if eoy is set, the
           default values are copied from the 31st of December of the current
           year, 23:59h.

    Returns:
      The parsed timestamp.
    """
    if eoy:
      default = datetime.datetime(time.gmtime().tm_year, 12, 31, 23, 59)
    else:
      default = datetime.datetime(time.gmtime().tm_year, 1, 1, 0, 0)
    timestamp = parser.parse(string, default=default)
    return time.mktime(timestamp.utctimetuple()) * cls.converter

  @classmethod
  def LessThanEq(cls, attribute, filter_implemention, value):
    return filter_implemention.PredicateLesserEqualFilter(
        attribute, cls.ParseFromHumanReadable(value, eoy=True))

  @classmethod
  def LessThan(cls, attribute, filter_implemention, value):
    """For dates we want to recognize a variety of values."""
    return filter_implemention.PredicateLesserEqualFilter(
        attribute, cls.ParseFromHumanReadable(value))

  @classmethod
  def GreaterThanEq(cls, attribute, filter_implemention, value):
    return filter_implemention.PredicateGreaterEqualFilter(
        attribute, cls.ParseFromHumanReadable(value))

  @classmethod
  def GreaterThan(cls, attribute, filter_implemention, value):
    return filter_implemention.PredicateGreaterEqualFilter(
        attribute, cls.ParseFromHumanReadable(value, eoy=True))

  operators = {"<": (1, "LessThan"),
               ">": (1, "GreaterThan"),
               "<=": (1, "LessThanEq"),
               ">=": (1, "GreaterThanEq")}


class RDFDatetimeSeconds(RDFDatetime):
  """A DateTime class which is stored in whole seconds."""
  converter = 1


class RDFProto(RDFValue):
  """A baseclass for using a protobuff as a RDFValue."""
  # This should be overriden with a protobuf class
  _proto = None
  data = None

  # This is a map between protobuf fields and RDFValue objects.
  rdf_map = {}

  data_store_type = "bytes"

  def __init__(self, serialized=None, age=None):
    # Allow ourselves to be instantiated from a protobuf
    if self._proto is None or isinstance(serialized, self._proto):
      self.data = serialized
      super(RDFProto, self).__init__(None, age)
    else:
      self.data = self._proto()
      super(RDFProto, self).__init__(serialized, age)

  def ParseFromString(self, string):
    self.data.ParseFromString(utils.SmartStr(string))

  def SerializeToString(self):
    return self.data.SerializeToString()

  def GetFields(self, field_names):
    value = self.data
    rdf_class = self

    for field_name in field_names:
      rdf_class = rdf_class.rdf_map.get(field_name, RDFString)
      value = getattr(value, field_name)

    return [rdf_class(value)]

  def __str__(self):
    return self.data.__str__()

  @classmethod
  def Fields(cls, name):
    return ["%s.%s" % (name, x.name) for x in cls._proto.DESCRIPTOR.fields]

  def __getattr__(self, attr):
    # Delegate to the protobuf if possible, but do not proxy private methods.
    if not attr.startswith("_"):
      return getattr(self.data, attr)

    raise AttributeError(AttributeError)

  def __setattr__(self, attr, value):
    """If this attr does not belong to ourselves set in the proxied protobuf.

    Args:
      attr: The attribute to set.
      value: The value to set.
    """
    if hasattr(self.data, attr) and not hasattr(self.__class__, attr):
      setattr(self.data, attr, value)
    else:
      object.__setattr__(self, attr, value)


class RDFProtoDict(RDFProto):
  _proto = jobs_pb2.Dict


class LabelList(RDFProto):
  """A list of labels."""
  _proto = jobs_pb2.LabelList


class RDFProtoArray(RDFProto):
  """A baseclass for using an array of protobufs as RDFValue."""
  # This should be overridden as the proto in the array
  _proto = lambda: None

  # This is where we store all the protobufs in the array.
  data = None

  def __init__(self, serialized=None, age=None):
    super(RDFProtoArray, self).__init__(age=age)
    self.data = []
    if isinstance(serialized, self._proto):
      self.data.append(serialized)

    elif serialized is not None:
      self.ParseFromString(utils.SmartStr(serialized))

  def ParseFromString(self, string):
    myarray = jobs_pb2.BlobArray()
    myarray.ParseFromString(string)

    self.data = []
    for data_blob in myarray.content:
      member = self._proto()
      member.ParseFromString(data_blob.data)
      self.data.append(member)

  def GetFields(self, field_names):
    """Recurse into an attribute to get sub fields by name."""
    result = []
    for value in self.data:
      rdf_class = self

      for field_name in field_names:
        rdf_class = rdf_class.rdf_map.get(field_name, RDFString)
        value = getattr(value, field_name)

      result.append(rdf_class(value))

    return result

  def Append(self, member=None, **kwargs):
    """Add another member to the array.

    Args:
      member: A new protobuf to append to the array. Must be of the correct
          type.

      **kwargs: if member is not specified, a new array member is created and
          these kwargs are passed to the protobuf constructor.

    Raises:
       TypeError: If the member is not of the correct type.
    """
    if member is None:
      member = self._proto(**kwargs)

    # Allow the member to be an RDFProto instance.
    elif isinstance(member, RDFProto):
      member = member.data

    if type(member) != self._proto:
      raise TypeError("Can not append a %s to %s" % (
          type(member), self.__class__.__name__))

    self.data.append(member)

  def SerializeToString(self):
    myarray = jobs_pb2.BlobArray()
    for member in self.data:
      myarray.content.add(data=member.SerializeToString())

    return myarray.SerializeToString()

  def __iter__(self):
    return self.data.__iter__()

  def __len__(self):
    return self.data.__len__()

  def __nonzero__(self):
    return bool(self.data)

  def Pop(self, index=0):
    self.data.pop(index)

  def __str__(self):
    results = [str(x) for x in self.data]
    return "\n\n".join(results)

  def __getitem__(self, item):
    return self.data.__getitem__(item)


class RDFURN(RDFValue):
  """An object to abstract URL manipulation."""

  data_store_type = "string"

  def __init__(self, urn=None, age=None):
    """Constructor.

    Args:
      urn: A string or another RDFURN.
      age: The age of this entry.
    """
    if type(urn) == RDFURN:
      # Make a direct copy of the other object
      # pylint: disable=W0212
      self._urn = urn._urn
      self._string_urn = urn._string_urn
      super(RDFURN, self).__init__(None, age)
      return

    super(RDFURN, self).__init__(urn, age)

  def ParseFromString(self, serialized=None):
    self._urn = urlparse.urlparse(serialized, scheme="aff4")
    # Normalize the URN path component
    # namedtuple _replace() is not really private.
    # pylint: disable=W0212
    self._urn = self._urn._replace(path=utils.NormalizePath(self._urn.path))
    if not self._urn.scheme:
      self._urn = self._urn._replace(scheme="aff4")

    self._string_urn = self._urn.geturl()

  def SerializeToString(self):
    return str(self)

  def Dirname(self):
    return posixpath.dirname(self.SerializeToString())

  def Basename(self):
    return posixpath.basename(self.Path())

  def Add(self, urn, age=None):
    """Add a relative stem to the current value and return a new RDFURN.

    If urn is a fully qualified URN, replace the current value with it.

    Args:
      urn: A string containing a relative or absolute URN.
      age: The age of the object. If None set to current time.

    Returns:
       A new RDFURN that can be chained.
    """
    if isinstance(urn, RDFURN):
      return urn

    parsed = urlparse.urlparse(urn)
    if parsed.scheme != "aff4":
      # Relative name - just append to us.
      result = self.Copy(age)
      result.Update(path=utils.JoinPath(self._urn.path, urn))
    else:
      # Make a copy of the arg
      result = RDFURN(urn, age)

    return result

  def Update(self, url=None, **kwargs):
    """Update one of the fields.

    Args:
       url: An optional string containing a URL.
       **kwargs: Can be one of "schema", "netloc", "query", "fragment"
    """
    if url: self.ParseFromString(url)

    self._urn = self._urn._replace(**kwargs)  # pylint: disable=W0212
    self._string_urn = self._urn.geturl()

  def Copy(self, age=None):
    """Make a copy of ourselves."""
    if age is None:
      age = int(time.time() * MICROSECONDS)
    return RDFURN(str(self), age=age)

  def __str__(self):
    return utils.SmartStr(self._string_urn)

  def __unicode__(self):
    return utils.SmartUnicode(self._string_urn)

  def __eq__(self, other):
    return utils.SmartStr(self) == utils.SmartStr(other)

  def __ne__(self, other):
    return str(self) != str(other)

  def __lt__(self, other):
    return self._string_urn < other

  def __gt__(self, other):
    return self._string_urn > other

  def Path(self):
    """Return the path of the urn."""
    return self._urn.path

  @property
  def scheme(self):
    return self._urn.scheme

  def Split(self, count=None):
    """Returns all the path components.

    Args:
      count: If count is specified, the output will be exactly this many path
        components, possibly extended with the empty string. This is useful for
        tuple assignments without worrying about ValueErrors:

           namespace, path = urn.Split(2)

    Returns:
      A list of path components of this URN.
    """
    if count:
      result = filter(None, self.Path().split("/", count))
      while len(result) < count:
        result.append("")

      return result

    else:
      return filter(None, self.Path().split("/"))

  def RelativeName(self, volume):
    """Given a volume URN return the relative URN as a unicode string.

    We remove the volume prefix from our own.
    Args:
      volume: An RDFURN or fully qualified url string.

    Returns:
      A string of the url relative from the volume or None if our URN does not
      start with the volume prefix.
    """
    string_url = utils.SmartUnicode(self)
    volume_url = utils.SmartUnicode(volume)
    if string_url.startswith(volume_url):
      result = string_url[len(volume_url):]
      # Must always return a relative path
      while result.startswith("/"): result = result[1:]

      # Should return a unicode string.
      return utils.SmartUnicode(result)

    return None

  def __hash__(self):
    return hash(utils.SmartUnicode(self))

  def __repr__(self):
    return "<RDFURN@%X = %s age=%s>" % (hash(self), str(self), self.age)


class RDFFingerprintValue(RDFProto):
  """Proto containing dicts with hashes."""
  _proto = jobs_pb2.FingerprintResponse
  # TODO(user): Add reasonable accessors for UI/console integration.
  # This includes parsing out the SignatureBlob for windows binaries.

  def Get(self, name):
    """Gets the first fingerprint type from the protobuf."""
    for result in self.data.fingerprint_results:
      result = utils.ProtoDict(result)
      if result.Get("name") == name:
        return result


class Subject(RDFURN):
  """A psuedo attribute representing the subject of an AFF4 object."""

  @staticmethod
  def ContainsMatch(unused_attribute, filter_implemention, regex):
    return filter_implemention.SubjectContainsFilter(regex)

  @staticmethod
  def Startswith(unused_attribute, filter_implemention, string):
    return filter_implemention.SubjectContainsFilter(
        "^" + data_store.EscapeRegex(string))

  @staticmethod
  def HasAttribute(unused_attribute, filter_implemention, string):
    return filter_implemention.HasPredicateFilter(string)

  operators = dict(matches=(1, "ContainsMatch"),
                   contains=(1, "ContainsMatch"),
                   startswith=(1, "Startswith"),
                   has=(1, "HasAttribute"))


class Attribute(object):
  """AFF4 schema attributes are instances of this class."""

  description = ""

  # A global registry of attributes by name. This ensures we do not accidentally
  # define the same attribute with conflicting types.
  PREDICATES = {}

  # A human readable name to be used in filter queries.
  NAMES = {}

  def __init__(self, predicate, attribute_type=RDFString, description="",
               name=None, _copy=False, default=None, index=None,
               versioned=True):
    """Constructor.

    Args:
       predicate: The name of this attribute - must look like a URL
             (e.g. aff4:contains). Will be used to store the attribute.
       attribute_type: The RDFValue type of this attributes.
       description: A one line description of what this attribute represents.
       name: A human readable name for the attribute to be used in filters.
       _copy: Used internally to create a copy of this object without
          registering.
       default: A default value will be returned if the attribute is not set on
          an object. This can be a constant or a callback which receives the fd
          itself as an arg.
       index: The name of the index to use for this attribute. If None, the
          attribute will not be indexed.
       versioned: Should this attribute be versioned? Non-versioned attributes
          always overwrite other versions of the same attribute.
    """
    self.name = name
    self.predicate = predicate
    self.attribute_type = attribute_type
    self.description = description
    self.default = default
    self.index = index
    self.versioned = versioned

    # Field names can refer to a specific component of an attribute
    self.field_names = []

    if not _copy:
      # Check the attribute registry for conflicts
      try:
        old_attribute = Attribute.PREDICATES[predicate]
        if old_attribute.attribute_type != attribute_type:
          logging.error(
              "Attribute %s defined with conflicting types (%s, %s)",
              predicate, old_attribute.attribute_type.__class__.__name__,
              attribute_type.__class__.__name__)
          raise RuntimeError
      except KeyError:
        pass

      # Register
      self.PREDICATES[predicate] = self
      if name:
        self.NAMES[name] = self

  def Copy(self):
    """Return a copy without registering in the attribute registry."""
    return Attribute(self.predicate, self.attribute_type, self.description,
                     self.name, _copy=True)

  def __call__(self, *args, **kwargs):
    """A shortcut allowing us to instantiate a new type from an attribute."""
    result = self.attribute_type(*args, **kwargs)
    result.attribute_instance = self
    return result

  def __str__(self):
    return self.predicate

  def __repr__(self):
    return "<Attribute(%s, %s)>" %(self.name, self.predicate)

  def __hash__(self):
    return hash(self.predicate)

  def __eq__(self, other):
    return str(self.predicate) == str(other)

  def __ne__(self, other):
    return str(self.predicate) != str(other)

  def __getitem__(self, item):
    result = self.Copy()
    result.field_names = item.split(".")

    return result

  def Fields(self, name):
    return self.attribute_type.Fields(name)

  @classmethod
  def GetAttributeByName(cls, name):
    # Support attribute names with a . in them:
    try:
      if "." in name:
        name, field = name.split(".", 1)
        return cls.NAMES[name][field]

      return cls.NAMES[name]
    except KeyError:
      raise AttributeError("Invalid attribute")

  def GetRDFValueType(self):
    """Returns this attribute's RDFValue class."""
    result = self.attribute_type
    for field_name in self.field_names:
      result = result.rdf_map.get(field_name, RDFString)

    return result

  def GetValues(self, fd):
    """Return the values for this attribute as stored in an AFF4Object."""
    results = []
    for result in (fd.synced_attributes.get(self, []) +
                   fd.new_attributes.get(self, [])):

      # We need to interpolate sub fields in this protobuf.
      if self.field_names:
        results.extend(result.GetFields(self.field_names))
      else:
        results.append(result)

    if not results:
      default = self.GetDefault(fd)
      if default is not None:
        results.append(default)

    return results

  def GetDefault(self, fd, default=None):
    """Returns a default attribute if it is not set."""
    if callable(self.default):
      return self.default(fd)

    if self.default is not None:
      return self(self.default)

    return default


class SubjectAttribute(Attribute):
  """An attribute which virtualises the subject."""

  def __init__(self):
    Attribute.__init__(self, "aff4:subject",
                       Subject, "A subject pseodo attribute", "subject")

  def GetValues(self, fd):
    return [Subject(fd.urn)]


class ClassProperty(property):
  """A property which comes from the class object."""

  def __get__(self, _, owner):
    return self.fget.__get__(None, owner)()


class ClassInstantiator(property):
  """A property which instantiates the class on getting."""

  def __get__(self, _, owner):
    return self.fget()


class AFF4Object(object):
  """Base class for all objects."""

  # We are a registered class.
  __metaclass__ = registry.MetaclassRegistry
  include_plugins_as_attributes = True

  # This property is used in GUIs to define behaviours. These can take arbitrary
  # values as needed. Behaviours are read only and set in the class definition.
  _behaviours = frozenset()

  # Should this object be synced back to the data store.
  _dirty = False

  @ClassProperty
  @classmethod
  def behaviours(cls):  # pylint: disable=C6409
    return cls._behaviours

  # We define the parts of the schema for each AFF4 Object as an internal
  # class. As new objects extend this, they can add more attributes to their
  # schema by extending their parents. Note that the class must be named
  # SchemaCls.
  class SchemaCls(object):
    """The standard AFF4 schema."""
    TYPE = Attribute("aff4:type", RDFString,
                     "The name of the AFF4Object derived class.", "type")

    SUBJECT = SubjectAttribute()

    STORED = Attribute("aff4:stored", RDFURN,
                       "The AFF4 container inwhich this object is stored.")

    LAST = Attribute("metadata:last", RDFDatetime,
                     "The last time any attribute of this object was written.")

    LABEL = Attribute("aff4:labels", LabelList,
                      "Any object can have labels applied to it.", default="")

    def ListAttributes(self):
      for attr in dir(self):
        attr = getattr(self, attr)
        if isinstance(attr, Attribute):
          yield attr

    def GetAttribute(self, name):
      for i in self.ListAttributes():
        # Attributes are accessible by predicate or name
        if i.name == name or i.predicate == name:
          return i

    def __getattr__(self, attr):
      """For unknown attributes just return None.

      Often the actual object returned is not the object that is expected. In
      those cases attempting to retrieve a specific named attribute will raise,
      e.g.:

      fd = aff4.FACTORY.Open(urn)
      fd.Get(fd.Schema.SOME_ATTRIBUTE, default_value)

      This simply ensures that the default is chosen.

      Args:
        attr: Some ignored attribute.
      """
      return None

    @classmethod
    def FindAFF4Class(cls):
      """Return a list of AFF4 Object classes which use us as a Schema."""
      result = []
      for aff4cls in AFF4Object.classes.values():
        if aff4cls.SchemaCls is cls:
          result.append(aff4cls)

      return result

  # Make sure that when someone references the schema, they receive an instance
  # of the class.
  @property
  def Schema(self):   # pylint: disable=C6409
    return self.SchemaCls()

  def __init__(self, urn, mode="r", parent=None, clone=None, token=None,
               local_cache=None, age=NEWEST_TIME):
    self.urn = RDFURN(urn)
    self.mode = mode
    self.parent = parent
    self.token = token
    self.age_policy = age

    # This flag will be set whenever a versioned attribute is changed.
    self._new_version = False

    # Mark out attributes to delete when Flushing()
    self._to_delete = set()

    # We maintain two attribute caches - self.synced_attributes reflects the
    # attributes which are synced with the data_store, while self.new_attributes
    # are new attributes which still need to be flushed to the data_store. When
    # this object is instantiated we populate self.synced_attributes with the
    # data_store, while the finish method flushes new changes.
    if isinstance(clone, dict):
      # Just use these as the attributes - do not go to the data store. This is
      # a quick way of creating an object with data which was already fetched.
      self.new_attributes = {}
      self.synced_attributes = clone

    elif isinstance(clone, AFF4Object):
      # We were given another object to clone - we do not need to access the
      # data_store now.
      self.new_attributes = clone.new_attributes.copy()
      self.synced_attributes = clone.synced_attributes.copy()

    else:
      self.new_attributes = {}
      self.synced_attributes = {}

      if "r" in mode:
        if local_cache:
          try:
            for attribute, value, ts in local_cache[utils.SmartUnicode(urn)]:
              self.DecodeValueFromAttribute(attribute, value, ts)
          except KeyError:
            pass
        else:
          # Populate the caches from the data store.
          for urn, values in FACTORY.GetAttributes([urn], age=age,
                                                   token=self.token):
            for attribute_name, value, ts in values:
              self.DecodeValueFromAttribute(attribute_name, value, ts)

    # We do not initialize when we need to clone from another object.
    if clone is None:
      self.Initialize()

  def Initialize(self):
    """The method is called after construction to initialize the object.

    This will be called after construction, and each time the object is
    unserialized from the datastore.

    An AFF4 object contains attributes which can be populated from the
    database. This method is called to obtain a fully fledged object from
    a collection of attributes.
    """

  def DecodeValueFromAttribute(self, attribute_name, value, ts):
    """Given a serialized value, decode the attribute.

    Only attributes which have been previously defined are permitted.

    Args:
       attribute_name: The string name of the attribute.
       value: The serialized attribute value.
       ts: The timestamp of this attribute.
    """
    try:
      # Get the Attribute object from our schema
      attribute = Attribute.PREDICATES[attribute_name]
      cls = attribute.attribute_type
      self._AddAttributeToCache(attribute, cls(value, ts),
                                self.synced_attributes)
    except KeyError:
      if not attribute_name.startswith("index:"):
        logging.debug("Attribute %s not defined, skipping.", attribute_name)
    except (ValueError, message.DecodeError):
      logging.debug("%s: %s invalid encoding. Skipping.",
                    self.urn, attribute_name)

  def _AddAttributeToCache(self, attribute_name, value, cache):
    """Helper to add a new attribute to a cache."""
    cache.setdefault(attribute_name, []).append(value)

  def Flush(self, sync=True):
    """Syncs this object with the data store."""
    # If the object is not opened for writing we do not need to flush it to the
    # data_store.
    if "w" not in self.mode:
      return

    if self.new_attributes or self._to_delete:
      logging.debug("%s: Writing %s and deleting %s attributes", self.urn,
                    len(self.new_attributes), len(self._to_delete))

    to_set = {}
    for attribute_name, value_array in self.new_attributes.items():
      for value in value_array:
        to_set.setdefault(attribute_name, []).append(
            (value.SerializeToDataStore(), value.age))

    if self._dirty:
      # We determine this object has a new version only if any of the versioned
      # attributes have changed. Non-versioned attributes do not represent a new
      # object version. The type of an object is versioned and represents a
      # version point in the life of the object.
      if self._new_version:
        to_set[self.Schema.TYPE] = [
            (RDFString(self.__class__.__name__).SerializeToDataStore(),
             RDFDatetime())]

      # Write the attributes to the Factory cache.
      FACTORY.SetAttributes(self.urn, to_set, self._to_delete, sync=sync,
                            token=self.token)
      # Notify factory that the object got updated.
      FACTORY.NotifyWriteObject(self)

    # This effectively moves all the values from the new_attributes to the
    # _attributes caches.
    for attribute_name, value_array in self.new_attributes.items():
      self.synced_attributes.setdefault(attribute_name, []).extend(value_array)

    self.new_attributes = {}
    self._to_delete.clear()
    self._dirty = False
    self._new_version = False

    # Recurse back to all our parents and flush them
    if self.parent:
      self.parent.Flush(sync=sync)

  def _CheckAttribute(self, attribute, value):
    """Check that the value is of the expected type.

    Args:
       attribute: An instance of Attribute().
       value: An instance of RDFValue.
    Raises:
       ValueError: when the value is not of the expected type.
       AttributeError: When the attribute is not of type Attribute().
    """
    if not isinstance(attribute, Attribute):
      raise AttributeError("Attribute %s must be of type aff4.Attribute()",
                           attribute)

    if not isinstance(value, attribute.attribute_type):
      raise ValueError("Value for attribute %s must be of type %s()",
                       attribute, attribute.attribute_type.__name__)

  def Set(self, attribute, value=None):
    """Set an attribute on this object.

    If the attribute is already set, it is cleared first. If value is None,
    attribute is expected to be already initialized with a value. For example:

    fd.Set(fd.Schema.CONTAINS("some data"))

    Args:
       attribute: The attribute name.
       value: The value the attribute will be set to.

    Raises:
       IOError: If this object is read only.
    """
    if "w" not in self.mode:
      raise IOError("Writing attribute %s to read only object." % attribute)

    # Support an alternate calling style
    if value is None:
      value = attribute
      attribute = value.attribute_instance

    # Does this represent a new version?
    if attribute.versioned:
      self._new_version = True

    self._CheckAttribute(attribute, value)
    self.AddAttribute(attribute, value)

  def AddAttribute(self, attribute, value=None):
    """Add an additional attribute to this object.

    If value is None, attribute is expected to be already initialized with a
    value. For example:

    fd.AddAttribute(fd.Schema.CONTAINS("some data"))

    Args:
       attribute: The attribute name or an RDFValue derived from the attribute.
       value: The value the attribute will be set to.

    Raises:
       IOError: If this object is read only.
    """
    if "w" not in self.mode:
      raise IOError("Writing attribute %s to read only object." % attribute)

    if value is None:
      value = attribute
      attribute = value.attribute_instance

    self._CheckAttribute(attribute, value)

    # Does this represent a new version?
    if attribute.versioned:
      self._new_version = True

      # Update the time of this new attribute.
      value.age.Now()

    # Non-versioned attributes always replace previous versions and get written
    # at the earliest timestamp (so they appear in all objects).
    else:
      self._to_delete.add(attribute)
      value.age = 0

    self._AddAttributeToCache(attribute, value, self.new_attributes)
    self._dirty = True

  def DeleteAttribute(self, attribute):
    """Clears the attribute from this object."""
    if attribute in self.synced_attributes:
      self._to_delete.add(attribute)
      del self.synced_attributes[attribute]

    if attribute in self.new_attributes:
      del self.new_attributes[attribute]

    # Does this represent a new version?
    if attribute.versioned:
      self._new_version = True

    self._dirty = True

  def IsAttributeSet(self, attribute):
    """Determine if the attribute is set.

    Args:
      attribute: The attribute to check.

    Returns:
      True if set, otherwise False.

    Checking Get against None doesn't work as Get will return a default
    attribute value. This determines if the attribute has been manually set.
    """
    return (attribute in self.synced_attributes or
            attribute in self.new_attributes)

  def Get(self, attribute, default=None):
    """Gets the attribute from this object."""
    if attribute is None:
      return default

    # Allow the user to specify the attribute by name.
    elif isinstance(attribute, str):
      attribute = Attribute.GetAttributeByName(attribute)

    # Reads of un-flushed writes are still allowed.
    if "r" not in self.mode and (attribute not in self.new_attributes and
                                 attribute not in self.synced_attributes):
      # If there are defaults for this attribute - just use them.
      result = attribute.GetDefault(self)
      if result is not None:
        return result

      raise IOError(
          "Fetching %s from object not opened for reading." % attribute)

    result = list(self.GetValuesForAttribute(attribute, only_one=True))
    if not result:
      return attribute.GetDefault(self, default)

    # Get latest result
    result.sort(key=lambda x: x.age)
    return result[-1]

  def GetValuesForAttribute(self, attribute, only_one=False):
    """Returns a list of values from this attribute."""
    if not only_one and self.age_policy == NEWEST_TIME:
      raise RuntimeError("Attempting to read all attribute versions for an "
                         "object opened for NEWEST_TIME. This is probably "
                         "not what you want.")

    if attribute is None:
      return []

    elif isinstance(attribute, basestring):
      attribute = Attribute.GetAttributeByName(attribute)

    return attribute.GetValues(self)

  def Close(self, sync=True):
    """Close and destroy the object."""
    # Sync the attributes
    self.Flush(sync=sync)

  def Update(self, attribute=None, user=None):
    """Requests the object refresh an attribute from the Schema."""

  def Upgrade(self, aff4_class):
    """Upgrades this object to the type specified.

    AFF4 Objects can be upgraded on the fly to other type - As long as the new
    type is derived from the current type. This feature allows creation of
    placeholder objects which can later be upgraded to the fully featured
    object.

    Note: It is not allowed to downgrade an object if that would result in a
    loss of information (since the new object has a smaller schema). This method
    tries to store the new object with its new attributes and will fail if any
    attributes can not be mapped.

    Args:
       aff4_class: A string representing the new class.

    Returns:
       an instance of the new class with all the same attributes as this current
       object.

    Raises:
       AttributeError: When the new object can not accept some of the old
       attributes.
    """
    # We are already of the required type
    if self.__class__.__name__ == aff4_class:
      return self

    # Instantiate the right type
    cls = self.classes[str(aff4_class)]

    # NOTE: It is possible for attributes to become inaccessible here if the old
    # object has an attribute which the new object does not have in its
    # schema. The values of these attributes will not be available any longer in
    # the new object - usually because old attributes do not make sense in the
    # context of the new object.

    # Instantiate the class
    result = cls(self.urn, mode=self.mode, clone=self, parent=self.parent,
                 token=self.token, age=self.age_policy)
    result.Initialize()
    result._dirty = True
    result._new_version = True

    return result

  def __repr__(self):
    return "<%s@%X = %s>" % (self.__class__.__name__, hash(self), self.urn)

  # The following are used to ensure a bunch of AFF4Objects can be sorted on
  # their URNs.
  def __gt__(self, other):
    return self.urn > other

  def __lt__(self, other):
    return self.urn < other


class AttributeExpression(lexer.Expression):
  """An expression which is used to filter attributes."""

  def SetAttribute(self, attribute):
    """Checks that attribute is a valid Attribute() instance."""
    # Grab the attribute registered for this name
    self.attribute = attribute
    self.attribute_obj = Attribute.GetAttributeByName(attribute)
    if self.attribute_obj is None:
      raise lexer.ParseError("Attribute %s not defined" % attribute)

  def SetOperator(self, operator):
    """Sets the operator for this expression."""
    self.operator = operator
    # Find the appropriate list of operators for this attribute
    attribute_type = self.attribute_obj.GetRDFValueType()
    operators = attribute_type.operators

    # Do we have such an operator?
    self.number_of_args, self.operator_method = operators.get(
        operator, (0, None))

    if self.operator_method is None:
      raise lexer.ParseError("Operator %s not defined on attribute '%s'" % (
          operator, self.attribute))

    self.operator_method = getattr(attribute_type, self.operator_method)

  def Compile(self, filter_implemention):
    """Returns the data_store filter implementation from the attribute."""
    return self.operator_method(self.attribute_obj,
                                filter_implemention, *self.args)


class AFF4QueryParser(lexer.SearchParser):
  expression_cls = AttributeExpression


class AFF4Volume(AFF4Object):
  """Volumes contain other objects.

  The AFF4 concept of a volume abstracts away how objects are stored. We simply
  define an AFF4 volume as a container of other AFF4 objects. The volume may
  implement any storage mechanism it likes, including virtualizing the objects
  contained within it.
  """
  _behaviours = frozenset(["Container"])

  class SchemaCls(AFF4Object.SchemaCls):
    CONTAINS = Attribute("aff4:contains", RDFURN,
                         "An AFF4 object contained in this container.")

  def Query(self, filter_string="", filter_obj=None, limit=1000):
    """A way to query the collection based on a filter object.

    Args:
      filter_string: An optional filter applied to our members. The filter
        string should correspond to the syntax described in lexer.py.
      filter_obj: An optional compiled filter (as obtained from lexer.Compile().
      limit: A limit on the number of returned rows.

    Returns:
      A generator of all children which match the filter.
    """
    # If no filtering is required we can just use OpenChildren.
    if not filter_obj and not filter_string:
      return self.OpenChildren(limit=limit)

    if filter_obj is None and filter_string:
      # Parse the query string
      ast = AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.filter)

    result_set = data_store.DB.Query(
        [], filter_obj, limit=limit, subject_prefix=self.urn, token=self.token)

    result = data_store.ResultSet(
        self.OpenChildren([m["subject"][0] for m in result_set]))

    result.total_count = result_set.total_count
    return result

  def OpenMember(self, path, mode="r"):
    """Opens the member which is contained in us.

    Args:
       path: A string relative to our own URN or an absolute urn.
       mode: Mode for object.

    Returns:
       an AFF4Object instance.

    Raises:
      IOError: If we are unable to open the member (e.g. it does not already
      exist.)
    """
    if isinstance(path, RDFURN):
      child_urn = path
    else:
      child_urn = self.urn.Add(path)

    # Read the row from the table.
    result = AFF4Object(child_urn, mode=mode, token=self.token)

    # Get the correct type.
    aff4_type = result.Get(result.Schema.TYPE)
    if aff4_type:
      # Try to get the container.
      return result.Upgrade(aff4_type)

    raise IOError("Path %s not found" % path)

  def CreateMember(self, path, aff4_type, mode="w"):
    return FACTORY.Create(self.urn.Add(path), aff4_type, mode=mode,
                          token=self.token)

  def ListChildren(self, limit=1000000):
    """Yields RDFURNs of all the children of this object.

    Args:
      limit: Total number of items we will attempt to retrieve.

    Yields:
      RDFURNs instances of each child.
    """
    # Just grab all the children from the index.
    index_prefix = "index:dir/"
    for predicate, _, timestamp in data_store.DB.ResolveRegex(
        self.urn, index_prefix + ".+", token=self.token,
        timestamp=data_store.DB.NEWEST_TIMESTAMP, limit=limit):
      urn = self.urn.Add(predicate[len(index_prefix):])
      urn.age = RDFDatetime(timestamp)
      yield urn

  def OpenChildren(self, children=None, mode="r", limit=1000000,
                   chunk_limit=1000):
    """Yields AFF4 Objects of all our direct children.

    This method efficiently returns all attributes for our children directly, in
    a few data store round trips. We use the directory indexes to query the data
    store.

    Args:
      children: A list of children RDFURNs to open. If None open all our
             children.
      mode: The mode the files should be opened with.
      limit: Total number of items we will attempt to retrieve.
      chunk_limit: Maximum number of items to retrieve at a time.
    Yields:
      Instances for each direct child.
    """
    if children is None:
      subjects = list(self.ListChildren(limit=limit))
    else:
      subjects = list(children)
    subjects.sort()
    # Read at most limit children at a time.
    while subjects:
      to_read = subjects[:chunk_limit]
      subjects = subjects[chunk_limit:]
      for child in FACTORY.MultiOpen(to_read, mode=mode, token=self.token):
        yield child


class AFF4Root(AFF4Volume):
  """The root of the VFS.

  This virtual collection contains the entire virtual filesystem, and therefore
  can be queried across the entire data store.
  """

  def Query(self, filter_string="", filter_obj=None, subjects=None, limit=100):
    """Filter the objects contained within this collection."""
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.filter)

    subjects = []
    result_set = data_store.DB.Query([], filter_obj, subjects=subjects,
                                     limit=limit, token=self.token)
    for match in result_set:
      subjects.append(match["subject"][0])

    # Open them all at once.
    result = data_store.ResultSet(FACTORY.MultiOpen(subjects, token=self.token))
    result.total_count = result_set.total_count

    return result

  def OpenMember(self, path, mode="r"):
    """If we get to the root without a container, virtualize an empty one."""
    urn = self.urn.Add(path)
    result = AFF4Volume(urn, mode=mode, token=self.token)
    result.Initialize()

    return result


class AFF4OverlayedVolume(AFF4Volume):
  """A special kind of volume with overlayed contained objects.

  This AFF4Volume can contain virtual overlays. An overlay is a path which
  appears to be contained within our object, but is in fact the same object. For
  example if self.urn = RDFURN('aff4:/C.123/foobar'):

  Opening aff4:/C.123/foobar/overlayed/ will return a copy of aff4:/C.123/foobar
  with the variable self.overlayed_path = "overlayed".

  This is used to effectively allow a single AFF4Volume to handle overlay
  virtual paths inside itself without resorting to storing anything in the
  database for every one of these object. Thus we can have a WinRegistry
  AFF4Volume that handles any paths within without having storage for each
  registry key.
  """
  overlayed_path = ""

  def IsPathOverlayed(self, path):   # pylint: disable=W0613
    """Should this path be overlayed.

    Args:
      path: A direct_child of ours.

    Returns:
      True if the path should be overlayed.
    """
    return False

  def OpenMember(self, path, mode="rw"):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, mode=mode, clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).OpenMember(path, mode)

  def CreateMember(self, path, aff4_type, mode="w", clone=None):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, mode=mode, clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).CreateMember(
        path, aff4_type, mode=mode, clone=clone)


class AFF4Stream(AFF4Object):
  """An abstract stream for reading data."""
  __metaclass__ = abc.ABCMeta

  # The read pointer offset.
  offset = 0

  class SchemaCls(AFF4Object.SchemaCls):
    # Note that a file on the remote system might have stat.st_size > 0 but if
    # we do not have any of the data available to read: size = 0.
    SIZE = Attribute("aff4:size", RDFInteger,
                     "The total size of available data for this stream.",
                     "size", default=0)

  @abc.abstractmethod
  def Read(self, length):
    pass

  @abc.abstractmethod
  def Write(self, data):
    pass

  @abc.abstractmethod
  def Tell(self):
    pass

  @abc.abstractmethod
  def Seek(self, offset, whence=0):
    pass

  # These are file object conformant namings for library functions that
  # grr uses, and that expect to interact with 'real' file objects.
  read = utils.Proxy("Read")
  seek = utils.Proxy("Seek")
  tell = utils.Proxy("Tell")
  close = utils.Proxy("Close")
  write = utils.Proxy("Write")


class AFF4MemoryStream(AFF4Stream):
  """A stream which keeps all data in memory."""

  dirty = False

  class SchemaCls(AFF4Stream.SchemaCls):
    CONTENT = Attribute("aff4:content", RDFBytes,
                        "Total content of this file.", default="")

  def Initialize(self):
    """Try to load the data from the store."""
    contents = ""

    if "r" in self.mode:
      contents = self.Get(self.Schema.CONTENT)
      try:
        if contents is not None:
          contents = zlib.decompress(utils.SmartStr(contents))
      except zlib.error:
        pass

    self.fd = StringIO.StringIO(contents)
    self.size = RDFInteger(0)

  def Truncate(self, offset=None):
    if offset is None:
      offset = self.offset
    self.fd = StringIO.StringIO(self.fd.getvalue()[:offset])
    self.size.Set(offset)

  def Read(self, length):
    return self.fd.read(int(length))

  def Write(self, data):
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")
    self.dirty = True
    self.fd.write(data)
    self.size += len(data)

  def Tell(self):
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def Close(self, sync=True):
    if self.dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT(compressed_content))
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4MemoryStream, self).Close(sync=sync)


class AFF4ObjectCache(utils.PickleableStore):
  """A cache which closes its objects when they expire."""

  def ExpireObject(self, key):
    obj = super(AFF4ObjectCache, self).ExpireObject(key)
    if obj is not None:
      obj.Close()


class AFF4Image(AFF4Stream):
  """An AFF4 Image is stored in segments.

  We are both an Image here and a volume (since we store the segments inside
  us).
  """

  NUM_RETRIES = 10
  CHUNK_ID_TEMPLATE = "%010X"

  class SchemaCls(AFF4Stream.SchemaCls):
    CHUNKSIZE = Attribute("aff4:chunksize", RDFInteger,
                          "Total size of each chunk.", default=64*1024)

  def Initialize(self):
    """Build a cache for our chunks."""
    super(AFF4Image, self).Initialize()

    self.offset = 0
    # A cache for reading segments - When we get pickled we want to discard
    # these read only segments.
    self.read_chunk_cache = utils.FastStore(100)

    # For writing we want to hold onto these when pickled so we can continue
    # writing from where we left off - hence we use a pickleable store.
    self.write_chunk_cache = AFF4ObjectCache(10)

    if "r" in self.mode:
      self.size = int(self.Get(self.Schema.SIZE))
    else:
      self.size = 0

  def Seek(self, offset, whence=0):
    # This stream does not support random writing in "w" mode. When the stream
    # is opened in "w" mode we can not read from the data store and therefore we
    # can not merge writes with existing data. It only makes sense to append to
    # existing streams.
    if self.mode == "w":
      # Seeking to the end of the stream is ok.
      if not (whence == 2 and offset == 0):
        raise IOError("Can not seek with an AFF4Image opened for write only.")

    if whence == 0:
      self.offset = offset
    elif whence == 1:
      self.offset += offset
    elif whence == 2:
      self.offset = long(self.size) + offset

  def Tell(self):
    return self.offset

  def Truncate(self, offset=None):
    self._dirty = True
    if offset is None:
      offset = self.offset

    self.size = offset
    self.offset = offset
    self.write_chunk_cache.Flush()

  def _GetChunkForWriting(self, chunk):
    chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
    try:
      fd = self.write_chunk_cache.Get(chunk_name)
    except KeyError:
      fd = FACTORY.Create(chunk_name, "AFF4MemoryStream", mode="w",
                          token=self.token)
      self.write_chunk_cache.Put(chunk_name, fd)

    return fd

  def _GetChunkForReading(self, chunk):
    chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
    try:
      fd = self.read_chunk_cache.Get(chunk_name)
    except KeyError:
      # The most common read access pattern is contiguous reading. Here we
      # readahead to reduce round trips.
      missing_chunks = []
      for chunk_number in range(chunk, chunk + 10):
        new_chunk_name = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk_number)
        try:
          self.read_chunk_cache.Get(new_chunk_name)
        except KeyError:
          missing_chunks.append(new_chunk_name)

      for child in FACTORY.MultiOpen(
          missing_chunks, mode="r", token=self.token):
        if isinstance(child, AFF4Stream):
          self.read_chunk_cache.Put(child.urn, child)

      # This should work now - otherwise we just give up.
      try:
        fd = self.read_chunk_cache.Get(chunk_name)
      except KeyError:
        raise IOError("Cannot open chunk %s" % chunk_name)

    return fd

  def _ReadPartial(self, length):
    """Read as much as possible, but not more than length."""
    chunksize = int(self.Get(self.Schema.CHUNKSIZE))
    chunk = self.offset / chunksize
    chunk_offset = self.offset % chunksize

    available_to_read = min(length, chunksize - chunk_offset)

    retries = 0
    while retries < self.NUM_RETRIES:
      fd = self._GetChunkForReading(chunk)
      if fd:
        break
      # Arriving here means we know about blobs that cannot be found in the db.
      # The most likely reason is that they have not been synced yet so we
      # retry a couple of times just in case they come in eventually.
      logging.warning("Chunk not found.")
      time.sleep(1)
      retries += 1

    if retries >= self.NUM_RETRIES:
      raise IOError("Chunk not found for reading.")

    fd.Seek(chunk_offset)

    result = fd.Read(available_to_read)
    self.offset += len(result)

    return result

  def Read(self, length):
    """Read a block of data from the file."""
    result = ""

    # The total available size in the file
    length = int(length)
    length = min(length, self.size - self.offset)

    while length > 0:
      data = self._ReadPartial(length)
      if not data: break

      length -= len(data)
      result += data

    return result

  def _WritePartial(self, data):
    chunksize = int(self.Get(self.Schema.CHUNKSIZE))
    chunk = self.offset / chunksize
    chunk_offset = self.offset % chunksize
    data = utils.SmartStr(data)

    available_to_write = min(len(data), chunksize - chunk_offset)

    fd = self._GetChunkForWriting(chunk)
    fd.Seek(chunk_offset)

    fd.Write(data[:available_to_write])
    self.offset += available_to_write

    return data[available_to_write:]

  def Write(self, data):
    self._dirty = True
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")
    while data:
      data = self._WritePartial(data)

    self.size = max(self.size, self.offset)

  def Flush(self, sync=True):
    """This method is called to sync our data into storage.

    We must flush all the chunks in the chunk cache, but we leave the one chunk
    we still have at the moment, so that subsequent writes can add data to it.

    Args:
      sync: Should flushing be synchronous.
    """
    fd = None
    if self._dirty:
      chunksize = int(self.Get(self.Schema.CHUNKSIZE))

      chunk = self.offset / chunksize

      cache_key = self.urn.Add(self.CHUNK_ID_TEMPLATE % chunk)
      try:
        fd = self.write_chunk_cache[cache_key]
      except KeyError:
        pass

      # Flush the cache
      self.write_chunk_cache.Flush()
      self.Set(self.Schema.SIZE(self.size))

    super(AFF4Image, self).Flush(sync=sync)

    if fd:
      self.write_chunk_cache.Put(cache_key, fd)


class AFF4NotificationRule(AFF4Object):
  def OnWriteObject(self, unused_aff4_object):
    raise NotImplementedError()


# Utility functions
class AFF4InitHook(registry.InitHook):

  pre = ["DataStoreInit"]

  def Run(self):
    """Delayed loading of aff4 plugins to break import cycles."""
    # pylint: disable=W0612,W0603,C6204
    from grr.lib import aff4_objects

    global FACTORY

    FACTORY = Factory()  # pylint: disable=C6409
    # pylint: enable=W0612,W0603,C6204


class AFF4Filter(object):
  """A simple filtering system to be used with Query()."""
  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def __init__(self, *args):
    self.args = args

  @abc.abstractmethod
  def Filter(self, subjects):
    """A generator which filters the subjects.

    Args:
       subjects: An iterator of aff4 objects.

    Returns:
       A generator over all the Objects which pass the filter.
    """


# A global registry of all AFF4 classes
FACTORY = None
ROOT_URN = RDFURN("aff4:/")

# The FlowSwitch lives here.
FLOW_SWITCH_URN = ROOT_URN.Add("flows")
