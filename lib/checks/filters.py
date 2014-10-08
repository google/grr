#!/usr/bin/env python
"""Implementation of filters, which run host data through a chain of parsers."""
import collections

from grr.lib import objectfilter
from grr.lib import registry
from grr.lib.rdfvalues import structs


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A check was defined badly."""


def GetHandler(mode=""):
  if mode == "SERIAL":
    return SerialHandler
  elif mode == "PARALLEL":
    return ParallelHandler
  else:
    return NoOpHandler


class BaseHandler(object):
  """Abstract tests for filtering host data through a parser chain."""

  def __init__(self, artifact=None, filters=None):
    if not artifact:
      raise DefinitionError("Filter needs some data to process!")
    self.artifact = artifact
    self.raw_data = []     # Collected data to analyze.
    self.filters = []      # Filters used to process data.
    self.cmp_data = []     # Data that results will be compared against.
    self.results = []      # Residual data following filtering.
    if isinstance(filters, structs.RepeatedFieldHelper):
      self.filters = filters
      self.Validate()

  def Validate(self):
    """Verifies this filter set can process the result data."""
    # All filters can handle the input type.
    bad_filters = []
    for f in self.filters:
      try:
        f.Validate()
      except DefinitionError:
        bad_filters.append(f.expression)
    if bad_filters:
      raise DefinitionError("Filters with invalid expressions: %s" %
                            ", ".join(bad_filters))

  def Parse(self, results):
    """Take the results and yield results that passed through the filters."""
    raise NotImplementedError()


class NoOpHandler(BaseHandler):
  """Abstract parser to pass results through parsers serially."""

  def Parse(self, data):
    """Take the results and yield results that passed through the filters."""
    return data


class ParallelHandler(BaseHandler):
  """Abstract parser to pass results through parsers in parallel."""

  def Parse(self, raw_data):
    """Take the data and yield results that passed through the filters."""
    self.results = set()
    if not self.filters:
      self.results.update(raw_data)
    else:
      for f in self.filters:
        self.results.update(f.Parse(raw_data))
    return list(self.results)


class SerialHandler(BaseHandler):
  """Abstract parser to pass results through parsers serially."""

  def Parse(self, raw_data):
    """Take the results and yield results that passed through the filters."""
    self.results = raw_data
    for f in self.filters:
      self.results = f.Parse(self.results)
    return self.results


class Filter(object):
  """A class for looking up filters.

  Filters may be in other libraries or third party code. This class keeps
  references to each of them so they can be called by name by checks.
  """
  __metaclass__ = registry.MetaclassRegistry

  filters = {}

  @classmethod
  def _Iterate(cls, obj):
    if isinstance(obj, basestring) or not isinstance(obj, collections.Iterable):
      obj = [obj]
    for o in obj:
      yield o

  @classmethod
  def GetFilter(cls, filter_name):
    """Return an initialized filter. Only initialize filters once.

    Args:
      filter_name: The name of the filter, as a string.

    Returns:
      an initialized instance of the filter.

    Raises:
      DefinitionError if the type of filter has not been defined.
    """
    # Check if the filter is defined in the registry.
    try:
      filt_cls = cls.GetPlugin(filter_name)
    except KeyError:
      raise DefinitionError("Filter %s does not exist." % filter_name)
    # Return an initialized filter, after initializing it in cls.filters if it
    # doesn't exist.
    return cls.filters.setdefault(filter_name, filt_cls())

  def Parse(self, check_object, unused_arg):
    for result in self._Iterate(check_object):
      yield result

  def Validate(self, _):
    pass


class ObjectFilter(Filter):
  """An objectfilter result processor that accepts runtime parameters."""

  def _Compile(self, expression):
    try:
      of = objectfilter.Parser(expression).Parse()
      return of.Compile(objectfilter.LowercaseAttributeFilterImplementation)
    except objectfilter.Error as e:
      raise DefinitionError(e)

  def Parse(self, obj, expression):
    """Parse one or more objects using an objectfilter expression."""
    filt = self._Compile(expression)
    for result in filt.Filter(obj):
      yield result

  def Validate(self, expression):
    self._Compile(expression)
