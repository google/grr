#!/usr/bin/env python
"""Implement rdf post-processors for running data through a chain of parsers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re
import stat


from future.utils import with_metaclass

from grr_response_core.lib import objectfilter
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import config_file
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs


class Error(Exception):
  """Base error class."""


class DefinitionError(Error):
  """A filter was defined badly."""


class ProcessingError(Error):
  """A filter encountered errors processing results."""


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
    self.raw_data = []  # Collected data to analyze.
    self.filters = []  # Filters used to process data.
    self.cmp_data = []  # Data that results will be compared against.
    self.results = []  # Residual data following filtering.
    if isinstance(filters, rdf_structs.RepeatedFieldHelper):
      self.filters = filters
      self.Validate()

  def Validate(self):
    """Verifies this filter set can process the result data."""
    # All filters can handle the input type.
    bad_filters = []
    for f in self.filters:
      try:
        f.Validate()
      except DefinitionError as e:
        bad_filters.append("%s: %s" % (f.expression, e))
    if bad_filters:
      raise DefinitionError(
          "Filters with invalid expressions: %s" % ", ".join(bad_filters))

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
    """Take the results and yield results that passed through the filters.

    The output of each filter is used as the input for successive filters.

    Args:
      raw_data: An iterable series of rdf values.

    Returns:
      A list of rdf values that matched all filters.
    """
    self.results = raw_data
    for f in self.filters:
      self.results = f.Parse(self.results)
    return self.results


class Filter(with_metaclass(registry.MetaclassRegistry, object)):
  """A class for looking up filters.

  Filters may be in other libraries or third party code. This class keeps
  references to each of them so they can be called by name by checks.
  """

  filters = {}

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

    return filt_cls()

  def ParseObjs(self, *args):
    raise NotImplementedError("Filter needs to have a ParseObjs method.")

  def Parse(self, objs, expression):
    # Filters should process collections of rdfvalues. Require lists or sets of
    # rdfvalues so that we don't pass in one (iterable) rdfvalue and get back a
    # list of it's attributes.
    if not isinstance(objs, (list, set)):
      raise ProcessingError("Filter '%s' requires a list or set, got %s" %
                            (expression, type(objs)))
    return list(self.ParseObjs(objs, expression))

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
    AttributedDict RDF values. key is the attribute name, value is the attribute
    value.
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

  def ParseObjs(self, objs, expression):
    for key in self._Attrs(expression):
      # Key needs to be a string for rdfvalue.KeyValue
      key = utils.SmartStr(key)
      for obj in objs:
        val = self._GetVal(obj, key)
        if val:
          # Dict won't accept rdfvalue.RepeatedFieldHelper
          if isinstance(val, rdf_structs.RepeatedFieldHelper):
            val = list(val)
          yield rdf_protodict.AttributedDict({"key": key, "value": val})

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

  def ParseObjs(self, objs, expression):
    """Parse one or more objects using an objectfilter expression."""
    filt = self._Compile(expression)
    for result in filt.Filter(objs):
      yield result

  def Validate(self, expression):
    self._Compile(expression)


class ForEach(ObjectFilter):
  """A filter that extracts values from a repeated field.

  This filter is a convenient way to extract repeated items from an object
  for individual processing.

  Args:
    objs: One or more objects.
    expression: An expression specifying what attribute to expand.

  Yields:
     The RDF values of elements in the repeated fields.
  """

  def Validate(self, expression):
    attrs = [x.strip() for x in expression.strip().split() if x]
    if attrs:
      if len(attrs) == 1:
        return
      raise DefinitionError("ForEach has multiple attributes: %s" % expression)
    raise DefinitionError("ForEach sets no attribute: %s" % expression)

  def ParseObjs(self, objs, expression):
    for obj in objs:
      repeated_vals = getattr(obj, expression)
      for val in repeated_vals:
        yield rdf_protodict.AttributedDict({"item": val})


class ItemFilter(ObjectFilter):
  """A filter that extracts the first match item from a objectfilter expression.

  Applies an objectfilter expression to an object. The first attribute named in
  the expression is returned as a key/value item.`
  This filter is a convenient way to cherry pick selected items from an object
  for reporting or further filters.

  Args:
    objs: One or more objects.
    expression: An objectfilter expression..

  Yields:
     AttributedDict RDF values for matching items, where key is the attribute
     name, and value is the attribute value.
  """

  def ParseObjs(self, objs, expression):
    filt = self._Compile(expression)
    key = expression.split(None, 1)[0]
    for result in filt.Filter(objs):
      val = getattr(result, key)
      yield rdf_protodict.AttributedDict({"key": key, "value": val})


class StatFilter(Filter):
  """Filters StatResult RDF Values based on file attributes.

  Filters are added as expressions that include one or more key:value inputs
  separated by spaced.

  StatResult RDF values can be filtered on several fields:
  - path_re: A regex search on the pathname attribute.
  - file_re: A regex search on the filename attribute.
  - file_type: One of BLOCK,CHARACTER,DIRECTORY,FIFO,REGULAR,SOCKET,SYMLINK
  - gid: A numeric comparison of gid values: (!|>|>=|<=|<|=)uid
  - uid: A numeric comparison of uid values: (!|>|>=|<=|<|=)uid
  - mask: The permissions bits that should be checked. Defaults to 7777.
  - mode: The permissions bits the StatResult should have after the mask is
    applied.

  Args:
    expression: A statfilter expression

  Yields:
    StatResult objects that match the filter term.
  """
  _KEYS = {"path_re", "file_re", "file_type", "uid", "gid", "mode", "mask"}
  _UID_GID_RE = re.compile(r"\A(!|>|>=|<=|<|=)([0-9]+)\Z")
  _PERM_RE = re.compile(r"\A[0-7]{4}\Z")
  _TYPES = {
      "BLOCK": stat.S_ISBLK,
      "CHARACTER": stat.S_ISCHR,
      "DIRECTORY": stat.S_ISDIR,
      "FIFO": stat.S_ISFIFO,
      "REGULAR": stat.S_ISREG,
      "SOCKET": stat.S_ISSOCK,
      "SYMLINK": stat.S_ISLNK
  }

  def _MatchFile(self, stat_entry):
    filename = os.path.basename(stat_entry.pathspec.path)
    return self.file_re.search(filename)

  def _MatchGid(self, stat_entry):
    for matcher, value in self.gid_matchers:
      if not matcher(stat_entry.st_gid, value):
        return False
    return True

  def _MatchMode(self, stat_entry):
    return stat_entry.st_mode & self.mask == self.mode

  def _MatchPath(self, stat_entry):
    return self.path_re.search(stat_entry.pathspec.path)

  def _MatchType(self, stat_entry):
    return self.file_type(stat_entry.st_mode)

  def _MatchUid(self, stat_entry):
    for matcher, value in self.uid_matchers:
      if not matcher(stat_entry.st_uid, value):
        return False
    return True

  def _Comparator(self, operator):
    """Generate lambdas for uid and gid comparison."""
    if operator == "=":
      return lambda x, y: x == y
    elif operator == ">=":
      return lambda x, y: x >= y
    elif operator == ">":
      return lambda x, y: x > y
    elif operator == "<=":
      return lambda x, y: x <= y
    elif operator == "<":
      return lambda x, y: x < y
    elif operator == "!":
      return lambda x, y: x != y
    raise DefinitionError("Invalid comparison operator %s" % operator)

  def _Flush(self):
    self.cfg = {}
    self.matchers = []
    self.mask = 0
    self.mode = 0
    self.uid_matchers = []
    self.gid_matchers = []
    self.file_type = ""
    self.file_re = ""
    self.path_re = ""

  def _Load(self, expression):
    self._Flush()
    parser = config_file.KeyValueParser(
        kv_sep=":", sep=",", term=(r"\s+", r"\n"))
    parsed = {}
    for entry in parser.ParseEntries(expression):
      parsed.update(entry)
    self.cfg = rdf_protodict.AttributedDict(parsed)
    return parsed

  def _Initialize(self):
    """Initialize the filter configuration from a validated configuration.

    The configuration is read. Active filters are added to the matcher list,
    which is used to process the Stat values.
    """

    if self.cfg.mask:
      self.mask = int(self.cfg.mask[0], 8)
    else:
      self.mask = 0o7777
    if self.cfg.mode:
      self.mode = int(self.cfg.mode[0], 8)
      self.matchers.append(self._MatchMode)

    if self.cfg.gid:
      for gid in self.cfg.gid:
        matched = self._UID_GID_RE.match(gid)
        if matched:
          o, v = matched.groups()
          self.gid_matchers.append((self._Comparator(o), int(v)))
      self.matchers.append(self._MatchGid)

    if self.cfg.uid:
      for uid in self.cfg.uid:
        matched = self._UID_GID_RE.match(uid)
        if matched:
          o, v = matched.groups()
          self.uid_matchers.append((self._Comparator(o), int(v)))
      self.matchers.append(self._MatchUid)

    if self.cfg.file_re:
      self.file_re = re.compile(self.cfg.file_re[0])
      self.matchers.append(self._MatchFile)

    if self.cfg.path_re:
      self.path_re = re.compile(self.cfg.path_re[0])
      self.matchers.append(self._MatchPath)

    if self.cfg.file_type:
      self.file_type = self._TYPES.get(self.cfg.file_type[0].upper())
      self.matchers.append(self._MatchType)

  def ParseObjs(self, objs, expression):
    """Parse one or more objects by testing if it has matching stat results.

    Args:
      objs: An iterable of objects that should be checked.
      expression: A StatFilter expression, e.g.:
        "uid:>0 gid:=0 file_type:link"

    Yields:
      matching objects.
    """
    self.Validate(expression)
    for obj in objs:
      if not isinstance(obj, rdf_client_fs.StatEntry):
        continue
      # If all match conditions pass, yield the object.
      for match in self.matchers:
        if not match(obj):
          break
      else:
        yield obj

  def Validate(self, expression):
    """Validates that a parsed rule entry is valid for fschecker.

    Args:
      expression: A rule expression.

    Raises:
      DefinitionError: If the filter definition could not be validated.

    Returns:
      True if the expression validated OK.
    """
    parsed = self._Load(expression)

    if not parsed:
      raise DefinitionError("Empty StatFilter expression.")

    bad_keys = set(parsed) - self._KEYS
    if bad_keys:
      raise DefinitionError("Invalid parameters: %s" % ",".join(bad_keys))

    if self.cfg.mask and not self.cfg.mode:
      raise DefinitionError("mode can only be set when mask is also defined.")

    if self.cfg.mask:
      if len(self.cfg.mask) > 1:
        raise DefinitionError("Too many mask values defined.")
      if not self._PERM_RE.match(self.cfg.mask[0]):
        raise DefinitionError("mask=%s is not octal, e.g. 0600" % self.cfg.mask)

    if self.cfg.mode:
      if len(self.cfg.mode) > 1:
        raise DefinitionError("Too many mode values defined.")
      if not self._PERM_RE.match(self.cfg.mode[0]):
        raise DefinitionError("mode=%s is not octal, e.g. 0600" % self.cfg.mode)

    if self.cfg.gid:
      for gid in self.cfg.gid:
        matched = self._UID_GID_RE.match(gid)
        if not matched:
          raise DefinitionError("gid: %s is not an integer preceded by "
                                "!, >, < or =." % gid)

    if self.cfg.uid:
      for uid in self.cfg.uid:
        matched = self._UID_GID_RE.match(uid)
        if not matched:
          raise DefinitionError("uid: %s is not an integer preceded by "
                                "!, >, < or =." % uid)

    if self.cfg.file_re:
      if len(self.cfg.file_re) > 1:
        raise DefinitionError("Too many regexes defined: %s" % self.cfg.file_re)
      try:
        self.file_re = re.compile(self.cfg.file_re[0])
      except (re.error, TypeError) as e:
        raise DefinitionError("Invalid file regex: %s" % e)

    if self.cfg.path_re:
      if len(self.cfg.path_re) > 1:
        raise DefinitionError("Too many regexes defined: %s" % self.cfg.path_re)
      try:
        self.path_re = re.compile(self.cfg.path_re[0])
      except (re.error, TypeError) as e:
        raise DefinitionError("Invalid path regex: %s" % e)

    if self.cfg.file_type:
      if len(self.cfg.file_type) > 1:
        raise DefinitionError(
            "Too many file types defined: %s" % self.cfg.file_type)
      file_type = self.cfg.file_type[0].upper()
      if file_type not in self._TYPES:
        raise DefinitionError("Unsupported file type %s" % file_type)

    self._Initialize()
    if not self.matchers:
      raise DefinitionError("StatFilter has no actions: %s" % expression)
    return True


class RDFFilter(Filter):
  """Filter results to specified rdf types."""

  def _RDFTypes(self, names):
    for type_name in names.split(","):
      yield type_name

  def _GetClass(self, type_name):
    return rdfvalue.RDFValue.classes.get(type_name)

  def ParseObjs(self, objs, type_names):
    """Parse one or more objects by testing if it is a known RDF class."""
    for obj in objs:
      for type_name in self._RDFTypes(type_names):
        if isinstance(obj, self._GetClass(type_name)):
          yield obj

  def Validate(self, type_names):
    """Filtered types need to be RDFValues."""
    errs = [n for n in self._RDFTypes(type_names) if not self._GetClass(n)]
    if errs:
      raise DefinitionError("Undefined RDF Types: %s" % ",".join(errs))
