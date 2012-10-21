#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Modules to perform filtering of objects based on their data members."""



import abc
import logging
import re

from grr.lib import utils
from grr.proto import objectfilter_pb2


class Error(Exception):
  """Base module exception."""


class MalformedQueryError(Error):
  """The provided filter query is malformed."""


class ParseError(Error):
  """The parser for textual queries returned invalid results."""


class InvalidNumberOfOperands(Error):
  """The number of operands provided to this operator is wrong."""


class Filter(object):
  """Base class for every filter."""

  def __init__(self, children=None):
    self.children = []
    logging.debug('Adding %s', children)
    if children:
      self.children.extend(children)

  @abc.abstractmethod
  def Matches(self, obj):
    """Whether object obj matches this filter."""

  def Filter(self, objects):
    """Returns a list of objects that pass the filter."""
    return filter(self.Matches, objects)

  def __str__(self):
    return '%s(%s)' % (self.__class__.__name__,
                       ', '.join([str(child) for child in self.children]))


class AndFilter(Filter):
  """A filter that performs a boolean AND of the children filters.

    Note that if no conditions are passed, all objects will pass.
  """

  def Matches(self, obj):
    for child in self.children:
      if not child.Matches(obj):
        return False
    return True


class OrFilter(Filter):
  """Performs a boolean OR of the children filters.

  Note that if no conditions are passed, all objects will pass.
  """

  def Matches(self, obj):
    for child in self.children:
      if child.Matches(obj):
        return True
    return False


class Operator(Filter):
  """Base class for all operators. Takes a path as the first child.

  A path is a list of members that will be traversed for each object to
  match.
  """

  operation = None

  def Operate(self, values):
    # pylint: disable=E1102
    return self.operation(values)

  def Matches(self, obj):
    key = self.children[0]
    values = ExpandValues(obj, key)
    if values and self.Operate(values):
      return True
    return False


class UnaryOperator(Operator):
  """Base class for unary operators."""

  def __init__(self, children):
    super(UnaryOperator, self).__init__(children)
    if len(self.children) != 1:
      raise InvalidNumberOfOperands('Only one operand is accepted by %s. '
                                    'Received %d.' % (self.__class__.__name__,
                                                      len(self.children)))


class BinaryOperator(Operator):
  """Base class for binary operators.

  The left operand is always a path into the object. The right operand is a
  value defined by the operator itself and is stored at self.comp_value.
  """

  def __init__(self, children):
    super(BinaryOperator, self).__init__(children)
    if len(self.children) != 2:
      raise InvalidNumberOfOperands('Only two operands are accepted by %s. '
                                    'Received %d.' % (self.__class__.__name__,
                                                      len(self.children)))
    self.comp_value = self.children[1]

  def Operate(self, values):
    # pylint: disable=E1102
    return self.operation(values, self.comp_value)


class GenericBinaryOperator(BinaryOperator):
  """Allows easy implementations of simple binary operators."""

  def Operate(self, values):
    """Takes a list of values and if at least one matches, returns True."""
    for val in values:
      try:
        logging.debug('Operating %s with x=%s and y=%s',
                      self.__class__.__name__, val, self.comp_value)
        # pylint: disable=E1102
        if val and self.operation(val, self.comp_value): return True
      except (ValueError, TypeError):
        continue
    return False


class Is(GenericBinaryOperator):
  """Operator that returns objects when it matches against a given value."""
  operation = lambda self, x, y: utils.SmartUnicode(x) == utils.SmartUnicode(y)


class IsNot(GenericBinaryOperator):
  """Operator that returns objects when it doesn't match an explicit value."""

  def Operate(self, values):
    return not Is(self.children).Operate(values)


class Less(GenericBinaryOperator):
  """Performs numerical < comparisons against a given value."""
  operation = lambda self, x, y: long(x) < long(y)


class LessEqual(GenericBinaryOperator):
  """Performs numerical <= comparisons against the right operand."""
  operation = lambda self, x, y: long(x) <= long(y)


class Greater(GenericBinaryOperator):
  """Performs numerical > comparisons against the right operand."""
  operation = lambda self, x, y: long(x) > long(y)


class GreaterEqual(GenericBinaryOperator):
  """Performs numerical >= comparisons against the right operand."""
  operation = lambda self, x, y: long(x) >= long(y)


class Contains(GenericBinaryOperator):
  """Performs a textual contains operation against a given value."""
  operation = lambda self, x, y: utils.SmartUnicode(y) in utils.SmartUnicode(x)


class NotContains(GenericBinaryOperator):
  """Whether the right operand is not contained in any of the values."""

  def Operate(self, values):
    return not Contains(self.children).Operate(values)


#TODO(user): Change to an N-ary Operator?
class InSet(GenericBinaryOperator):
  """Whether at least a value is contained in the list at the right operand.

  The list of values at the right operand is comma-separated.
  """

  # pylint: disable=C6402
  operation = lambda self, x, y: (utils.SmartUnicode(x) in
                                  utils.SmartUnicode(y).split(','))


class NotInSet(GenericBinaryOperator):
  """Whether no values are present in the list at the right operand."""

  def Operate(self, values):
    return not InSet(self.children).Operate(values)


class Regexp(GenericBinaryOperator):
  """Whether any of the values match the regexp in the right operand."""

  def __init__(self, children):
    super(Regexp, self).__init__(children)
    logging.debug('Compiled: %s', self.comp_value)
    try:
      self.compiled_re = re.compile(utils.SmartUnicode(self.comp_value))
    except re.error:
      raise ValueError('Regular expression "%s" is malformed.' %
                       self.comp_value)

  def Operate(self, values):
    try:
      for val in values:
        if self.compiled_re.search(utils.SmartUnicode(val)): return True
    except ValueError:
      return False
    return False


class Context(Operator):
  """Restricts the child operators to a specific context within the object.

  Solves the context problem. The context problem is the following:
  Suppose you store a list of loaded DLLs within a process. Suppose that for
  each of these DLLs you store the number of imported functions and each of the
  imported functions name.

  Imagine that a malicious DLL is injected into processes and its indicators are
  that it only imports one function and that it is RegQueryValueEx. You'd write
  your indicator like this:


  AndOperator(
    Equal('ImportedDLLs.ImpFunctions.Name', 'RegQueryValueEx'),
    Equal('ImportedDLLs.NumImpFunctions', '1')
    )

  Now imagine you have these two processes on a given system.

  Process1
  +[0]__ImportedDlls
        +[0]__Name: "notevil.dll"
        |[0]__ImpFunctions
        |     +[1]__Name: "CreateFileA"
        |[0]__NumImpFunctions: 1
        |
        +[1]__Name: "alsonotevil.dll"
        |[1]__ImpFunctions
        |     +[0]__Name: "RegQueryValueEx"
        |     +[1]__Name: "CreateFileA"
        |[1]__NumImpFunctions: 2

  Process2
  +[0]__ImportedDlls
        +[0]__Name: "evil.dll"
        |[0]__ImpFunctions
        |     +[0]__Name: "RegQueryValueEx"
        |[0]__NumImpFunctions: 1

  Both Process1 and Process2 match your query, as each of the indicators are
  evaluated separatedly. While you wanted to express "find me processes that
  have a DLL that has both one imported function and ReqQueryValueEx is in the
  list of imported functions", your indicator actually means "find processes
  that have at least a DLL with 1 imported functions and at least one DLL that
  imports the ReqQueryValueEx function".

  To write such an indicator you need to specify a context of ImportedDLLs for
  these two clauses. Such that you convert your indicator to:

  Context('ImportedDLLs',
          AndOperator(
            Equal('ImpFunctions.Name', 'RegQueryValueEx'),
            Equal('NumImpFunctions', '1')
          ))

  Context will execute the filter specified as the second parameter for each of
  the objects under 'ImportedDLLs', thus applying the condition per DLL, not per
  object and returning the right result.
  """

  def __init__(self, children):
    if len(children) != 2:
      raise InvalidNumberOfOperands('Context accepts only 2 operands.')
    super(Context, self).__init__(children)
    self.context, self.condition = self.children

  def Matches(self, obj):
    for sub_object in ExpandValues(obj, self.context):
      if self.condition.Matches(sub_object):
        return True
    return False


class ObjectFilter(object):
  """Uses an ObjectFilter proto to return a compiled filter for objects."""

  OP = {objectfilter_pb2.ObjectFilter.OP_IS: Is,
        objectfilter_pb2.ObjectFilter.OP_IS_NOT: IsNot,
        objectfilter_pb2.ObjectFilter.OP_GREATER: Greater,
        objectfilter_pb2.ObjectFilter.OP_GREATER_EQUAL: GreaterEqual,
        objectfilter_pb2.ObjectFilter.OP_LESS: Less,
        objectfilter_pb2.ObjectFilter.OP_LESS_EQUAL: LessEqual,
        objectfilter_pb2.ObjectFilter.OP_CONTAINS: Contains,
        objectfilter_pb2.ObjectFilter.OP_NOT_CONTAINS: NotContains,
        objectfilter_pb2.ObjectFilter.OP_REGEXP: Regexp,
        objectfilter_pb2.ObjectFilter.OP_IN_SET: InSet,
        objectfilter_pb2.ObjectFilter.OP_NOT_IN_SET: NotInSet,
       }

  OP2ENUM = {'is': objectfilter_pb2.ObjectFilter.OP_IS,
             'isnot': objectfilter_pb2.ObjectFilter.OP_IS_NOT,
             'contains': objectfilter_pb2.ObjectFilter.OP_CONTAINS,
             'notcontains': objectfilter_pb2.ObjectFilter.OP_NOT_CONTAINS,
             '>': objectfilter_pb2.ObjectFilter.OP_GREATER,
             '>=': objectfilter_pb2.ObjectFilter.OP_GREATER_EQUAL,
             '<': objectfilter_pb2.ObjectFilter.OP_LESS,
             '<=': objectfilter_pb2.ObjectFilter.OP_LESS_EQUAL,
             'inset': objectfilter_pb2.ObjectFilter.OP_IN_SET,
             'notinset': objectfilter_pb2.ObjectFilter.OP_NOT_IN_SET,
             'regexp': objectfilter_pb2.ObjectFilter.OP_REGEXP,
            }

  # Matches:
  # path1.path2 operation "value" AND path4.path5 operation "value2"
  finder = re.compile(r'^([^ ]+)\s+([^ ]+)\s+"([^"]+)"'
                      r'(?:(?:\s+AND\s+)([^ ]+)\s+([^ ]+)\s+"([^"]+)")*$')

  def __init__(self, filter_proto=None, filter_query=None):
    self.filter_proto = filter_proto or ParseFilterQuery(filter_query)

  def Compile(self):
    """Returns a Filter instance representing the given filter query."""

    if not self.filter_proto:
      raise ValueError('No filter supplied')

    or_children = []
    for filt in self.filter_proto.filters:
      and_children = []
      for condition in filt.conditions:
        try:
          operation = ObjectFilter.OP[condition.op]
          and_children.append(operation([condition.key, condition.value]))
        except KeyError:
          raise AttributeError('Operation %s not found' % condition.op)
      or_children.append(AndFilter(and_children))
    return OrFilter(or_children)


def ParseFilterQuery(filter_query):
  """Takes a filter in textual form and converts it to a ObjectFilter.

  The filter_query takes the form of:
    condition AND condition

  Where condition is
    key operation "value"

  The supported operations can be found in ObjectFilter.OP2ENUM.

  Args:
    filter_query: The textual filter query.

  Returns:
    An instance of an ObjectFilter with the query already parsed and
    ready to be compiled.

  Raises:
    MalformedQueryError: When the query is invalid.
    ParseError: When unexpected results were foudn while parsing the query.
  """

  try:
    found = ObjectFilter.finder.match(filter_query)
  except TypeError:
    raise MalformedQueryError('The query must be a string or buffer.')

  if not found:
    raise MalformedQueryError('Invalid query.')
  found_groups = list(found.groups())

  if (len(found_groups) % 3) != 0:
    raise ParseError('ParseFilterQuery expects conditions as 3 parameters. '
                     '%d found.' % len(found_groups))

  filter_pb = objectfilter_pb2.ObjectFilter()
  filter_pb.filters.add()

  while found_groups:
    val = found_groups.pop()
    op = found_groups.pop()
    key = found_groups.pop()

    # Special case for the second group of capturing groups
    # When a filter such as 'key op "value"' is given
    if key is op is val is None: continue

    if op in ObjectFilter.OP2ENUM.keys():
      condition = filter_pb.filters[0].conditions.add()
      condition.key = key
      condition.op = ObjectFilter.OP2ENUM[op]
      condition.value = utils.SmartUnicode(val)
  return filter_pb


def ExpandValues(obj, path):
  """Returns a list of all the values for the given path in the object obj.

  Given a path such as ['sub1', 'sub2'] it will return all the values available
  in obj.sub1.sub2 as a list. sub1 and sub2 must be data attributes or
  properties.

  If sub1 returns a list of objects, or a generator, ExpandValues aggregates
  the values for the remaining path for each of the objects, thus returning a
  list of all the values under the given path for the input object.

  Args:
    obj: An object that will be traversed for the given path
    path: A list of strings

  Yields:
    The values once the object is traversed.
  """

  if isinstance(path, basestring):
    path = path.split('.')

  attr_name = path[0].lower()
  attr_value = getattr(obj, attr_name, None)
  if attr_value is None:
    return

  if len(path) == 1:
    # If it returned an iterable and it's not a string or bytes, return its
    # values.
    if (not isinstance(attr_value, basestring)
        and not isinstance(attr_value, bytes)):
      try:
        logging.debug('Returning %s as an iterated.', attr_value)
        for value in attr_value:
          yield value
      except TypeError:
        logging.debug('This object is not iterable. Returning as is.')
        yield attr_value
    else:
      # Otherwise, return the object itself
      yield attr_value
  else:
    # If we're not in a leaf, then we recurse
    try:
      for sub_obj in attr_value:
        for value in ExpandValues(sub_obj, path[1:]):
          yield value
    except TypeError:  # This is then not iterable, we recurse with the value
      for value in ExpandValues(attr_value, path[1:]):
        yield value
