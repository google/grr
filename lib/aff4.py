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
import StringIO
import time
import urlparse
import zlib

from dateutil import parser

from google.protobuf import message
import logging
from grr.lib import data_store
from grr.lib import lexer
from grr.lib import registry
from grr.lib import utils
from grr.proto import jobs_pb2


# Factor to convert from seconds to microseconds
MICROSECONDS = 1000000


class Factory(object):
  """A central factory for AFF4 objects."""

  def __init__(self):
    # The root AFF4 object - Automatically contains everything:
    self.root = AFF4Volume(ROOT_URN)
    self.root.Finish()

  def Open(self, urn, mode="r"):
    """Open the named object."""
    if urn == ROOT_URN:
      return self.root

    return self.root.Open(urn, mode)

  def MultiOpen(self, urns):
    """Opens a bunch of urns efficiently."""
    # TODO(user): Make this work properly
    for urn in urns:
      try:
        yield self.Open(urn)
      except IOError: pass

  def Create(self, urn, aff4_type="AFF4Object"):
    return self.root.CreateMember(urn, aff4_type)

  def Delete(self, urn):
    """Drop all the information about this object.

    DANGEROUS! This recursively deletes all object contained within the
    specified URN.

    Args:
      urn: The object to remove.

    Raises:
      RuntimeError: If the urn is too short. This is a safety check to ensure
      the root is not removed.
    """
    urn = RDFURN(urn)
    if len(urn.Path()) < 1:
      raise RuntimeError("URN %s too short. Please enter a valid URN" % urn)

    def _Delete(root):
      """Recursively delete all objects contained within the specified URN."""
      try:
        children, _ = root.ListChildren()
        for child in children:
          try:
            child_fd = root.OpenMember(child, "w")
            # Watch out for recursion or . directories
            if str(root.urn) != str(child):
              _Delete(child_fd)
          except IOError:
            logging.debug("IOError, could not delete %s", child)
      except AttributeError: pass

      logging.info("Deleted object %s", root.urn)
      data_store.DB.Transaction(
          utils.SmartUnicode(root.urn)).DeleteSubject().Commit()

    root = self.Open(urn)
    _Delete(root)

  def RDFValue(self, name):
    return RDFValue.classes.get(name)

  def AFF4Object(self, name):
    return AFF4Object.classes.get(name)


class RDFValue(object):
  """Baseclass for values.

  RDFValues are serialized to and from the data store.
  """

  __metaclass__ = registry.MetaclassRegistry

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

    if serialized is not None:
      self.ParseFromString(serialized)

  @abc.abstractmethod
  def ParseFromString(self, string):
    """Given a string, parse ourselves from it."""
    pass

  @abc.abstractmethod
  def SerializeToString(self):
    """Serialize into a string which can be parsed using ParseFromString."""
    pass

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


class RDFString(RDFValue):
  """Represent a simple string."""

  def ParseFromString(self, string):
    self.value = string

  def SerializeToString(self):
    return self.value

  def __str__(self):
    return str(self.value)

  def __eq__(self, other):
    return self.value == other

  def __ne__(self, other):
    return self.value != other

  def __hash__(self):
    return hash(self.value)

  @staticmethod
  def Startswith(attribute, filter_implemention, string):
    return filter_implemention.PredicateContainsFilter(
      attribute, "^" + data_store.EscapeRegex(string))

  operators = RDFValue.operators.copy()
  operators["matches"] = (1, "ContainsMatch")
  operators["="] = (1, "ContainsMatch")
  operators["startswith"] = (1, "Startswith")

class RDFSHAValue(RDFString):
  """SHA256 hash."""

  def __str__(self):
    return self.value.encode("hex")


class RDFInteger(RDFString):
  """Represent an integer."""

  def __init__(self, serialized=None, age=None):
    super(RDFInteger, self).__init__(serialized, age)
    if serialized is None:
      self.value = 0

  def ParseFromString(self, string):
    self.value = 0
    if string: self.value = long(string)

  def SerializeToString(self):
    return str(int(self.value))

  def __long__(self):
    return long(self.value)

  def __int__(self):
    return int(self.value)

  def __lt__(self, other):
    return self.value < other

  def __gt__(self, other):
    return self.value > other

  @staticmethod
  def LessThan(attribute, filter_implemention, value):
    return filter_implemention.PredicateLessThanFilter(attribute, long(value))

  @staticmethod
  def GreaterThan(attribute, filter_implemention, value):
    return filter_implemention.PredicateGreaterThanFilter(
        attribute, long(value))

  operators = {"<": (1, "LessThan"),
               ">": (1, "GreaterThan")}


class RDFDatetime(RDFInteger):
  """A date and time."""
  # For now we just store as an integer number of microseconds since the epoch

  def __init__(self, serialized=None, age=None):
    super(RDFDatetime, self).__init__(serialized, age)
    if serialized is None:
      self.Now()

  def Now(self):
    self.value = int(time.time() * MICROSECONDS)
    return self

  def __str__(self):
    """Return the date in human readable (UTC)."""
    value = self.value / MICROSECONDS
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(value))

  def __long__(self):
    return long(self.value)

  def __iadd__(self, other):
    self.value += other
    return self

  def ParseFromHumanReadable(self, string):
    """Parse a human readable string of a timestamp (in local time)."""
    timestamp = parser.parse(string)
    self.value = time.mktime(timestamp.utctimetuple()) * MICROSECONDS


class RDFProto(RDFValue):
  """A baseclass for using a protobuff as a RDFValue."""
  # This should be overriden with a protobuf class
  _proto = lambda: None
  data = None

  # This is a map between protobuf fields and RDFValue objects.
  rdf_map = {}

  def __init__(self, serialized=None, age=None):
    # Allow ourselves to be instantiated from a protobuf
    if isinstance(serialized, self._proto):
      self.data = serialized
      super(RDFProto, self).__init__(None, age)
    else:
      self.data = self._proto()
      super(RDFProto, self).__init__(serialized, age)

  def ParseFromString(self, string):
    self.data.ParseFromString(string)

  def SerializeToString(self):
    return self.data.SerializeToString()

  def GetField(self, field_name):
    rdf_class = self.rdf_map.get(field_name, RDFString)
    value = getattr(self.data, field_name)

    return rdf_class(value)

  def __str__(self):
    return self.data.__str__()

  @classmethod
  def Fields(cls, name):
    return ["%s.%s" % (name, x.name) for x in cls._proto.DESCRIPTOR.fields]


class RDFProtoArray(RDFProto):
  """A baseclass for using an array of protobufs as RDFValue."""
  # This should be overridden as the proto in the array
  _proto = lambda: None

  def __init__(self, serialized=None, age=None):
    super(RDFProtoArray, self).__init__(age=age)
    self.data = []

    if serialized is not None:
      self.ParseFromString(utils.SmartStr(serialized))

  def ParseFromString(self, string):
    array = jobs_pb2.BlobArray()
    array.ParseFromString(string)

    self.data = []
    for data_blob in array.content:
      member = self._proto()
      member.ParseFromString(data_blob.data)
      self.data.append(member)

  def Append(self, member):
    if type(member) != self._proto:
      raise RuntimeError("Can not append a %s to %s" % (
          type(member), self.__class__.__name__))

    self.data.append(member)

  def SerializeToString(self):
    array = jobs_pb2.BlobArray()
    for member in self.data:
      array.content.add(data=member.SerializeToString())

    return array.SerializeToString()

  def __iter__(self):
    return self.data.__iter__()

  def __str__(self):
    results = [str(x) for x in self.data]
    return "\n\n".join(results)

  def __getitem__(self, item):
    return self.data.__getitem__(item)


class RDFURN(RDFValue):
  """An object to abstract URL manipulation."""

  def __init__(self, urn=None, age=None):
    """Constructor.

    Args:
      urn: A string or another RDFURN.
      age: The age of this entry.
    """
    if type(urn) == RDFURN:
      # Make a direct copy of the other object
      self._urn = urn._urn
      self._string_urn = urn._string_urn
      super(RDFURN, self).__init__(None, age)
      return

    super(RDFURN, self).__init__(urn, age)

  def ParseFromString(self, serialized=None):
    self._urn = urlparse.urlparse(serialized)
    # Normalize the URN path component
    self._urn = self._urn._replace(path=utils.NormalizePath(self._urn.path))
    self._string_urn = self._urn.geturl()

  def SerializeToString(self):
    return str(self)

  def Add(self, urn, age=None):
    """Add a relative stem to the current value and return a new RDFURN.

    If urn is a fully qualified URN, replace the current value with it.

    Args:
      urn: A string containing a relative or absolute URN.
      age: The age of the object. If None set to current time.

    Returns:
       A new RDFURN that can be chained.
    """
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
       kwargs: Can be one of "schema", "netloc", "query", "fragment"
    """
    if url: self.ParseFromString(url)

    self._urn = self._urn._replace(**kwargs)
    self._string_urn = self._urn.geturl()

  def Copy(self, age=None):
    """Make a copy of ourselves."""
    if age is None:
      age = int(time.time() * MICROSECONDS)
    return RDFURN(str(self), age=age)

  def __str__(self):
    return utils.SmartStr(self._string_urn)

  def __eq__(self, other):
    return str(self) == str(other)

  def __ne__(self, other):
    return str(self) != str(other)

  def Path(self):
    """Return the path of the urn."""
    return self._urn.path

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
    return hash(str(self))

  def __repr__(self):
    return "<RDFURN@%X = %s age=%s>" % (hash(self), str(self), self.age)


class Subject(RDFURN):
  """A psuedo attribute representing the subject of an AFF4 object."""

  @staticmethod
  def ContainsMatch(unused_attribute, filter_implemention, regex):
    return filter_implemention.SubjectContainsFilter(regex)

  @staticmethod
  def Startswith(unused_attribute, filter_implemention, string):
    return filter_implemention.SubjectContainsFilter(
      "^" + data_store.EscapeRegex(string))


  operators = dict(matches=(1, "ContainsMatch"),
                   startswith=(1, "Startswith"))


class Attribute(object):
  """AFF4 schema attributes are instances of this class."""

  description = ""

  # A global registry of attributes by name. This ensures we do not accidentally
  # define the same attribute with conflicting types.
  PREDICATES = {}

  # A human readable name to be used in filter queries.
  NAMES = {}

  # Field name can refer to a specific component of an attribute
  field_name = None

  def __init__(self, predicate, attribute_type=RDFString, description="",
               name=None, _copy=False):
    """Constructor.

    Args:
       predicate: The name of this attribute - must look like a URL
             (e.g. aff4:contains). Will be used to store the attribute.
       attribute_type: The RDFValue type of this attributes.
       description: A one line description of what this attribute represents.
       name: A human readable name for the attribute to be used in filters.
       _copy: Used internally to create a copy of this object without
          registering.
    """
    self.name = name
    self.predicate = predicate
    self.attribute_type = attribute_type
    self.description = description

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
      except KeyError: pass

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
    return self.attribute_type(*args, **kwargs)

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
    result.field_name = item

    return result

  def Fields(self, name):
    return self.attribute_type.Fields(name)

  @classmethod
  def GetAttributeByName(cls, name):
    # Support attribute names with a . in them:
    if "." in name:
      name, field = name.split(".", 1)
      return cls.NAMES[name][field]

    return cls.NAMES[name]

  def GetRDFValueType(self):
    """Returns this attribute's RDFValue class."""
    return self.attribute_type

  def GetValues(self, fd):
    """Return the values for this attribute as stored in an AFF4Object."""
    result = (fd._attributes.get(self, []) +
              fd.new_attributes.get(self, []))

    if self.field_name:
      result = [x.GetField(self.field_name) for x in result]

    return result


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


class AFF4Object(object):
  """Base class for all objects."""

  # We are a registered class.
  __metaclass__ = registry.MetaclassRegistry

  # This property is used in GUIs to define behaviours. These can take arbitrary
  # values as needed. Behaviours are read only and set in the class definition.
  _behaviours = frozenset()

  @ClassProperty
  @classmethod
  def behaviours(cls):
    return cls._behaviours

  # We define the parts of the schema for each AFF4 Object as an internal
  # class. As new objects extend this, they can add more attributes to their
  # schema by extending their parents.
  class Schema(object):
    """The standard AFF4 schema."""
    TYPE = Attribute("aff4:type", RDFString,
                     "The name of the AFF4Object derived class.", "type")

    SUBJECT = SubjectAttribute()

    STORED = Attribute("aff4:stored", RDFURN,
                       "The AFF4 container inwhich this object is stored.")

    @classmethod
    def ListAttributes(cls):
      for attr in dir(cls):
        attr = getattr(cls, attr)
        if isinstance(attr, Attribute):
          yield attr

    @classmethod
    def GetAttribute(cls, name):
      for i in cls.ListAttributes():
        # Attributes are accessible by predicate or name
        if i.name == name or i.predicate == name:
          return i

  def __init__(self, urn, mode="r", parent=None, clone=None):
    self.urn = RDFURN(urn)
    self.mode = mode
    self.parent = parent

    # Mark out attributes to delete when Flushing()
    self._to_delete = set()

    # We maintain two attribute caches - self._attributes reflects the
    # attributes which are synced with the data_store, while self.new_attributes
    # are new attributes which still need to be flushed to the data_store. When
    # this object is instantiated we populate self._attributes with the
    # data_store, while the finish method flushes new changes.
    if isinstance(clone, dict):
      # Just use these as the attributes - do not go to the data store. This is
      # a quick way of creating an object with data which was already fetched.
      self.new_attributes = {}
      self._attributes = clone

    elif isinstance(clone, AFF4Object):
      # We were given another object to clone - we do not need to access the
      # data_store now.
      self.new_attributes = clone.new_attributes.copy()
      self._attributes = clone._attributes.copy()
    else:
      # Populate the caches from the data store.
      self.new_attributes = {}
      self._attributes = {}
      if urn:
        # Grab all the possible column families at once to minimize round trip
        # times.
        for attribute_name, value, ts in data_store.DB.ResolveRegex(
            utils.SmartUnicode(urn), predicate_regex=[
                "aff4:.*", "metadata:.*", "fs:.*", "task:.*"],
            timestamp=data_store.ALL_TIMESTAMPS):
          self.DecodeValueFromAttribute(attribute_name, value, ts)

    # We do not initialize when we need to clone from another object.
    if clone is None:
      self.Initialize()

  def Initialize(self):
    """The method is called after construction to initialize the object."""

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
                                self._attributes)
    except KeyError:
      logging.debug("Attribute %s not defined, skipping.", attribute_name)
    except (ValueError, message.DecodeError):
      logging.debug("%s: %s invalid encoding. Skipping.",
                    self.urn, attribute_name)

  def _AddAttributeToCache(self, attribute_name, value, cache):
    """Helper to add a new attribute to a cache."""
    cache.setdefault(attribute_name, []).append(value)

  def Flush(self):
    """Alias for Finish(). Syncs this object with the data store."""
    self.Finish()

  def Finish(self):
    """Complete the object."""
    # If we dont have a type, store it now to allow us to be correctly
    # un-serialized later. Note that this effectively represents the last
    # modification time for this object.
    if self.Get(self.Schema.TYPE) != self.__class__.__name__:
      self.Set(self.Schema.TYPE, RDFString(self.__class__.__name__))

    if self.new_attributes or self._to_delete:
      logging.debug("%s: Writing %s and deleting %s attributes", self.urn,
                    len(self.new_attributes), len(self._to_delete))

    # Write all the new attributes back preserving value timestamps.
    def Dummy(transaction):
      """Update and delete attributes in a transaction."""
      # Delete all the attributes
      for attribute_name in self._to_delete:
        transaction.DeleteAttribute(attribute_name)

      for attribute_name, value_array in self.new_attributes.items():
        for value in value_array:
          transaction.Set(attribute_name, value.SerializeToString(),
                          timestamp=value.age, replace=False)

    data_store.DB.RetryWrapper(utils.SmartUnicode(self.urn), Dummy)

    # This effectively moves all the values from the new_attributes to the
    # _attributes caches.
    for attribute_name, value_array in self.new_attributes.items():
      self._attributes.setdefault(attribute_name, []).extend(value_array)

    self.new_attributes = {}
    self._to_delete.clear()

    # Recurse back to all our parents and flush them
    if self.parent:
      self.parent.Finish()

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

  def Set(self, attribute, value):
    """Set an attribute on this object.

    If the attribute is already set, it is cleared first.

    Args:
       attribute: The attribute name.
       value: The value the attribute will be set to.
    """
    self._CheckAttribute(attribute, value)

    self.DeleteAttribute(attribute)
    self.AddAttribute(attribute, value)

  def AddAttribute(self, attribute, value):
    """Add an additional attribute to this object."""
    self._CheckAttribute(attribute, value)

    self._AddAttributeToCache(attribute, value, self.new_attributes)

  def DeleteAttribute(self, attribute):
    """Clears the attribute from this object."""
    if attribute in self._attributes:
      self._to_delete.add(attribute)
      del self._attributes[attribute]

    if attribute in self.new_attributes:
      del self.new_attributes[attribute]

  def Get(self, attribute, default=None):
    result = self.GetValuesForAttribute(attribute)
    # Get latest result
    result.sort(key=lambda x: x.age)
    if result:
      return result[-1]

    return default

  def GetValuesForAttribute(self, attribute):
    """Returns a list of values from this attribute."""
    return attribute.GetValues(self)

  def Close(self):
    """Close and destroy the object."""
    # Sync the attributes
    self.Finish()

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
    # Instantiate the right type
    cls = self.classes[str(aff4_class)]

    # Check that cls has all our attributes in its schema
    names = set([str(x) for x in cls.Schema.ListAttributes()])
    for x in list(self._attributes) + list(self.new_attributes):
      if x not in names:
        raise AttributeError("Unable to upgrade object to %s - "
                             "cant store attributes %s" % (aff4_class, x))

    result = cls(self.urn, self.mode, clone=self, parent=self.parent)
    result.Initialize()
    return result

  def __repr__(self):
    return "<%s@%X = %s>" % (self.__class__.__name__, hash(self), self.urn)


class AFF4Graph(AFF4Object):
  """Just a container to hold data."""


class AttributeExpression(lexer.Expression):
  """An expression which is used to filter attributes."""

  def SetAttribute(self, attribute):
    """Checks that attribute is a valid Attribute() instance."""
    # Grab the attribute registered for this name
    self.attribute = attribute
    self.attribute_obj = Attribute.NAMES.get(attribute)
    if self.attribute_obj is None:
      raise lexer.ParseError("Attribute %s not defined" % attribute)

  def SetOperator(self, operator):
    """Sets the operator for this expression."""
    self.operator = operator
    # Find the appropriate list of operators for this attribute
    operators = self.attribute_obj.attribute_type.operators

    # Do we have such an operator?
    self.number_of_args, self.operator_method = operators.get(
        operator, (0, None))

    if self.operator_method is None:
      raise lexer.ParseError("Operator %s not defined on attribute %s" % (
          operator, self.attribute))

    self.operator_method = getattr(self.attribute_obj.attribute_type,
                                   self.operator_method)

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
  # New containers will be created with this type
  default_container = "AFF4Volume"

  class Schema(AFF4Object.Schema):
    CONTAINS = Attribute("aff4:contains", RDFURN,
                         "An AFF4 obejct contained in this container.")

  def Query(self, filter_string="", filter_obj=None):
    """A way to query the collection based on a filter object.

    Args:
      filter_string: An optional filter applied to our members. The filter
        string should correspond to the syntax described in lexer.py.
      filter_obj: An optional compiled filter (as obtained from lexer.Compile().

    Returns:
      A generator of all children which match the filter.
    """
    if filter_obj is None and filter_string:
      # Parse the query string
      ast = AFF4QueryParser(filter_string).Parse()

      # Query our own data store
      filter_obj = ast.Compile(data_store.DB.Filter)

    result = []
    for match in data_store.DB.Query([], filter_obj):
      result.append(match["subject"][0])

    return self.OpenChildren(result)

  def Open(self, urn, mode="r"):
    """Open an object contained within this volume."""
    # We automatically contain URNs which start with our own URN. For example if
    # self.urn = RDFURN("aff4:/foobar") We will automatically contain
    # RDFURN("aff4:/foobar/something"):
    if not isinstance(urn, RDFURN):
      # Interpret as a relative path
      urn = self.urn.Add(urn)

    # Are we opening a direct child?
    relative_name = urn.RelativeName(self.urn)
    if relative_name:
      path_components = [x for x in relative_name.split("/") if x]
      direct_child = path_components[0]
      stem = "/".join(path_components[1:])

      child = self.OpenMember(direct_child, mode)

      if stem: return child.Open(stem, mode)

      return child

    # Otherwise we use the CONTAINS attribute
    if urn not in self.GetValuesForAttribute(self.Schema.CONTAINS):
      raise IOError("Path %s not found in container %s." % (urn, self.urn))

    return FACTORY.Open(urn)

  def OpenMember(self, path, mode):
    """Opens the member which is contained in us.

    Args:
       path: A string relative to our own URN or an RDFURN instance.
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

    # We instantiate the child. Because we dont know what type it is yet, we use
    # the baseclass and then get the correct type:
    result = AFF4Object(child_urn, mode, parent=self)

    # Get the real class
    aff4_type = result.Get(self.Schema.TYPE)
    if aff4_type not in AFF4Object.classes:
      raise IOError("Object %s not found" % child_urn)

    # Instantiate the right type
    cls = AFF4Object.classes[str(aff4_type)]
    result = cls(child_urn, mode, clone=result, parent=self)
    result.Initialize()
    return result

  def ListChildren(self):
    """Return all our children.

    Our children are those AFF4 objects with a URL with the same prefix as
    us. For example if our urn is "aff4:/foo", then aff4:/foo/bar is a direct
    child, but aff4:/foo/bar/zoo is not a direct child.

    Returns:
      A tuple of a dict keyed by relative names and values of their type, and
      the most recent age of the entries.
    """
    results = {}
    newest_age = 0

    for row in data_store.DB.Query(
        [self.Schema.TYPE], data_store.DB.Filter.AndFilter(
            data_store.DB.Filter.HasPredicateFilter("aff4:type"),
            data_store.DB.Filter.SubjectContainsFilter(
                "%s/[^/]+$" % data_store.EscapeRegex(self.urn))),
        utils.SmartUnicode(self.urn)):

      # Return a relative path if possible
      value, age = row[self.Schema.TYPE]
      results[RDFURN(row["subject"][0], age=age)] = value

      newest_age = max(age, newest_age)

    return results, newest_age

  def OpenChildren(self, children=None, mode="r"):
    """Yields AFF4 Objects of all our direct children.

    This method efficiently returns all attributes for our children directly, in
    a single data store round trip.

    Args:
      children: A list of children RDFURNs to open. If None open all our
             children.
      mode: The mode the files should be opened with.

    Yields:
      An AFF4 Object for each one of our children.
    """
    if children is None:
      children, _ = self.ListChildren()

    if not children: return

    # Convert all children to RDFURNs
    urn_children = []
    for child in children:
      if not isinstance(child, RDFURN):
        child = self.urn.Add(child)

      urn_children.append(child)

    for child, attributes in data_store.DB.MultiResolveRegex(
        urn_children, ["aff4:.*", "metadata:.*", "fs:.*", "task:.*"],
        timestamp=data_store.ALL_TIMESTAMPS).iteritems():
      # We need to search the list for the type
      for attribute, value, _ in attributes:
        # Find the type of the object
        if attribute == "aff4:type":
          # Create a blank object
          cls = AFF4Object.classes[value]
          result = cls(RDFURN(child), mode, clone={}, parent=self)

          # Decode the attributes for the new object from existing data
          for attribute, value, ts in attributes:
            result.DecodeValueFromAttribute(attribute, value, ts)

          # Initialize the result
          result.Initialize()
          yield result
          break

  def CreateMember(self, path, aff4_type, clone=None, mode="w"):
    """Creates and adds a new member to this volume.

    Args:
       path: The URN of the member (can be a string relative to this volume or
            RDFURN).
       aff4_type: The name of the AFF4 type the new member will have.
       clone: An optional AFF4 object we copy attributes from. Can also be a
              dict of attributes.
       mode: The mode an object should have. Can be "r" or "w".
    Returns:
       an AFF4Object instance of the specified type.

    Raises:
       IOError: if the aff4_type is not registered.
    """
    stem = ""

    # We contain a fully qualified URN
    try:
      relative_path = path.RelativeName(self.urn)
      if relative_path is not None: path = relative_path
    except AttributeError: pass

    if isinstance(path, RDFURN):
      child_urn = path
      self.AddAttribute(self.Schema.CONTAINS, path)
    else:
      # path should be taken as relative to us
      try:
        direct_child, stem = path.split("/", 1)
      except ValueError:
        direct_child, stem = path, ""

      child_urn = self.urn.Add(direct_child)

    # We instantiate the child. Because we dont know what type it is yet, we use
    # the baseclass and then get the correct type:
    result = AFF4Object(child_urn, mode, parent=self, clone=clone)

    # Get the real class
    result_type = result.Get(self.Schema.TYPE)
    if not result_type:
      # The object does not exist yet
      if stem:
        # It should be a container
        result_type = self.default_container
      else:
        # Its a leaf
        result_type = aff4_type

    # Instantiate the right type
    cls = AFF4Object.classes[str(result_type)]
    result = cls(child_urn, mode, clone=result, parent=self)
    result.Initialize()

    # Do we need an intermediate container
    if stem:
      return result.CreateMember(stem, aff4_type)

    # Final leaf
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

  def IsPathOverlayed(self, path):
    """Should this path be overlayed.

    Args:
      path: A direct_child of ours.

    Returns:
      True if the path should be overlayed.
    """
    return False

  def OpenMember(self, path, mode):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, mode, clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).OpenMember(path, mode)

  def CreateMember(self, path, aff4_type):
    if self.IsPathOverlayed(path):
      result = self.__class__(self.urn, "w", clone=self, parent=self)
      result.overlayed_path = path
      return result

    return super(AFF4OverlayedVolume, self).CreateMember(path, aff4_type)


class AFF4Stream(AFF4Object):
  """An abstract stream for reading data."""
  __metaclass__ = abc.ABCMeta

  class Schema(AFF4Object.Schema):
    SIZE = Attribute("aff4:size", RDFInteger,
                     "The total size of this stream", "size")

    CONTENT = Attribute("aff4:content", RDFString,
                        "Total content of this file.")

    HASH = Attribute("aff4:sha256", RDFSHAValue,
                     "SHA256 hash.")

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

  class Schema(AFF4Stream.Schema):
    CONTENT = Attribute("aff4:content", RDFString,
                        "Total content of this file.")

  def Initialize(self):
    """Try to load the data from the store."""
    compressed_content = self.Get(self.Schema.CONTENT)
    if compressed_content:
      contents = zlib.decompress(str(compressed_content))
    else:
      contents = ""

    self.fd = StringIO.StringIO(contents)

  def Read(self, length):
    return self.fd.read(length)

  def Write(self, data):
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")
    self.dirty = True
    self.fd.write(data)

  def Tell(self):
    return self.fd.tell()

  def Seek(self, offset, whence=0):
    self.fd.seek(offset, whence)

  def Close(self):
    if self.dirty:
      compressed_content = zlib.compress(self.fd.getvalue())
      self.Set(self.Schema.CONTENT, RDFString(compressed_content))

    super(AFF4MemoryStream, self).Close()


class AFF4Image(AFF4Stream, AFF4Volume):
  """An AFF4 Image is stored in segments.

  We are both an Image here and a volume (since we store the segments inside
  us).
  """

  class Schema(AFF4Stream.Schema):
    CHUNKSIZE = Attribute("aff4:chunksize", RDFInteger,
                          "Total size of each chunk.")

  def Initialize(self):
    """Build a cache for our chunks."""
    self.offset = 0
    # A cache for segments
    self.chunk_cache = utils.FastStore(100, kill_cb=lambda x: x.Close())

    self.size = self.Get(self.Schema.SIZE)
    if self.size is None:
      self.size = RDFInteger(0)
      self.Set(self.Schema.SIZE, self.size)

    # Set reasonable defaults
    if not self.Get(self.Schema.CHUNKSIZE):
      self.Set(self.Schema.CHUNKSIZE, RDFInteger(64 * 1024))

  def Seek(self, offset, whence=0):
    if whence == 0:
      self.offset = offset
    elif whence == 1:
      self.offset += offset
    elif whence == 2:
      self.offset = long(self.size) + offset

  def Tell(self):
    return self.offset

  def _GetChunkForWriting(self, chunk):
    chunk_name = "%010X" % chunk
    try:
      fd = self.chunk_cache.Get(chunk_name)
    except KeyError:
      fd = self.CreateMember(chunk_name, "AFF4MemoryStream")
      self.chunk_cache.Put(chunk_name, fd)

    return fd

  def _GetChunkForReading(self, chunk):
    chunk_name = "%010X" % chunk
    try:
      fd = self.chunk_cache.Get(chunk_name)
    except KeyError:
      # The most common read access pattern is contiguous reading. Here we
      # readahead to reduce round trips.
      missing_chunks = []
      for chunk_number in range(chunk, chunk + 30):
        new_chunk_name = "%010X" % chunk_number
        try:
          self.chunk_cache.Get(new_chunk_name)
        except KeyError:
          missing_chunks.append(new_chunk_name)

      for child in self.OpenChildren(children=missing_chunks):
        self.chunk_cache.Put(child.urn.RelativeName(self.urn), child)

      # This should work now
      fd = self.chunk_cache.Get(chunk_name)

    return fd

  def _ReadPartial(self, length):
    """Read as much as possible, but not more than length."""
    chunksize = int(self.Get(self.Schema.CHUNKSIZE))
    chunk = self.offset / chunksize
    chunk_offset = self.offset % chunksize

    available_to_read = min(length, chunksize - chunk_offset)

    fd = self._GetChunkForReading(chunk)
    fd.Seek(chunk_offset)

    result = fd.Read(available_to_read)
    self.offset += len(result)

    return result

  def Read(self, length):
    """Read a block of data from the file."""
    result = ""

    # The total available size in the file
    length = min(length, long(self.size) - self.offset)

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

    available_to_write = min(len(data), chunksize - chunk_offset)

    fd = self._GetChunkForWriting(chunk)
    fd.Seek(chunk_offset)

    fd.Write(data[:available_to_write])
    self.offset += available_to_write

    return data[available_to_write:]

  def Write(self, data):
    if isinstance(data, unicode):
      raise IOError("Cannot write unencoded string.")
    while data:
      data = self._WritePartial(data)

    self.size = RDFInteger(max(long(self.size), self.offset))
    self.Set(self.Schema.SIZE, self.size)

  def Close(self):
    # Flush the cache
    self.chunk_cache.Flush()
    super(AFF4Image, self).Close()


# Utility functions
class AFF4InitHook(object):
  """An initializer that can be extended by plugins.

  Any classes which extend this will be instantiated exactly once when the AFF4
  subsystem is initialized. This allows plugin modules to register
  initialization routines.
  """

  __metaclass__ = registry.MetaclassRegistry

  def __init__(self, **kwargs):
    global FACTORY

    # Make sure the data store is ready
    data_store.Init(**kwargs)

    FACTORY = Factory()


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


def AFF4Init(**kwargs):
  # Prepopulate with plugins
  from grr.lib import aff4_objects
  from grr.lib import compatibility

  # This initializes any class which inherits from AFF4InitHook.
  for cls in AFF4InitHook().classes.values():
    cls(**kwargs)
