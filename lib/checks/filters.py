#!/usr/bin/env python
"""Implementation of filters, which run host data through a chain of parsers."""
import collections

from grr.lib import objectfilter
from grr.lib import rdfvalue
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
    """Take the data and yield results that passed through the filters.

    The output of each filter is added to a result set. So long as the filter
    selects, but does not modify, raw data, the result count will remain
    accurate.

    Args:
      raw_data: An iterable series of rdf values.

    Returns:
      A list of rdf values that matched at least one filter.
    """
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
    raise NotImplementedError("Filter needs to have a Parse method.")

  def Validate(self, _):
    raise NotImplementedError("Filter needs to have a Validate method.")


class AttrFilter(Filter):
  """A filter that extracts target attributes into key/value fields.

  Accepts one or more attributes to collect. Optionally accepts an objectfilter
  expression to select objects from which attributes are collected.
  This filter is a convenient way to normalize the names of collected items to
  use with a generic hint.

  Args:
    expression: One or more attributes to fetch as comma separated items.

  Yields:
    Config RDF values. k is the attribute name, v is the attribute value.
  """

  def _Attrs(self, expression):
    attrs = [a.strip() for a in expression.strip().split() if a]
    if not attrs:
      raise DefinitionError("AttrFilter sets no attributes: %s" % expression)
    return attrs

  def _GetVal(self, obj, key):
    """Recurse down an attribute chain to the actual result data."""
    if "." in key:
      lhs, rhs = key.split(".", 1)
      obj2 = getattr(obj, lhs, None)
      if obj2 is None:
        return None
      return self._GetVal(obj2, rhs)
    else:
      return getattr(obj, key, None)

  def Parse(self, obj, expression):
    for key in self._Attrs(expression):
      val = self._GetVal(obj, key)
      yield rdfvalue.Config({"k": key, "v": val})

  def Validate(self, expression):
    self._Attrs(expression)


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


class ItemFilter(ObjectFilter):
  """A filter that extracts the first match item from a objectfilter expression.

  Applies an objectfilter expression to an object. The first attribute named in
  the expression is returned as a key/value item.`
  This filter is a convenient way to cherry pick selected items from an object
  for reporting or further filters.

  Args:
    expression: An objectfilter expression..

  Yields:
     Config RDF values for matching items, where k is the attribute name, and
     v is the attribute value.
  """

  def Parse(self, obj, expression):
    filt = self._Compile(expression)
    key = expression.split(None, 1)[0]
    for result in filt.Filter(obj):
      val = getattr(result, key)
      # Use a Config. KeyValueRDF values don't support attribute or dict
      # expansion for objectfilter expressions, and Dict RDF values require
      # a DictExpander. Using Config keeps the interface to objects consistent.
      yield rdfvalue.Config({"k": key, "v": val})


class RDFFilter(Filter):
  """Filter results to specified rdf types."""

  def _RDFTypes(self, names):
    for type_name in names.split(","):
      yield type_name

  def _GetClass(self, type_name):
    return rdfvalue.RDFValue.classes.get(type_name)

  def Parse(self, objs, type_names):
    """Parse one or more objects by testing if it is a known RDF class."""
    for obj in self._Iterate(objs):
      for type_name in self._RDFTypes(type_names):
        if isinstance(obj, self._GetClass(type_name)):
          yield obj

  def Validate(self, type_names):
    """Filtered types need to be RDFValues."""
    errs = [n for n in self._RDFTypes(type_names) if not self._GetClass(n)]
    if errs:
      raise DefinitionError("Undefined RDF Types: %s" % ",".join(errs))

