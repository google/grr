#!/usr/bin/env python
"""Pathspecs are methods of specifying the path on the client.

The GRR client has a number of drivers to virtualize access to different objects
to create a Virtual File System (VFS) abstraction. These are called 'VFS
Handlers' and they provide typical file-like operations (e.g. read, seek, tell
and stat).  It is possible to recursively apply different drivers in the correct
order to arrive at a certain file like object. In order to specify how drivers
should be applied we use 'Path Specifications' or pathspec.

Each VFS handler is constructed from a previous handler and a pathspec. The
pathspec is just a collection of arguments which make sense to the specific VFS
handler. The type of the handler is carried by the pathtype parameter.

On the server the PathSpec is represented as a PathSpec object, and stored
as an attribute of the AFF4 object. This module defines this abstraction.
"""


import fnmatch
import itertools
import posixpath
import re

from grr.lib import artifact_utils
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import standard as rdf_standard
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2

INTERPOLATED_REGEX = re.compile(r"%%([^%]+?)%%")

# Grouping pattern: e.g. {test.exe,foo.doc,bar.txt}
GROUPING_PATTERN = re.compile("{([^}]+,[^}]+)}")


class PathSpec(rdf_structs.RDFProtoStruct):
  """A path specification.

  The pathspec protobuf is a recursive protobuf which contains components. This
  class makes it easier to manipulate these structures by providing useful
  helpers.
  """
  protobuf = jobs_pb2.PathSpec

  def __init__(self, initializer=None, age=None, **kwargs):
    super(PathSpec, self).__init__(age=age, **kwargs)

    # Instantiate from another PathSpec.
    if isinstance(initializer, PathSpec):
      # pylint: disable=protected-access
      self.SetRawData(initializer._CopyRawData())
      # pylint: enable=protected-access
      self.age = initializer.age

    # Allow initialization from a list of protobufs each representing a
    # component.
    elif isinstance(initializer, list):
      for element in initializer:
        self.last.SetRawData(element.GetRawData())

    # Or we can initialize from a string.
    elif isinstance(initializer, str):
      self.ParseFromString(initializer)

    # Legacy protocol buffer implementation.
    elif isinstance(initializer, self.protobuf):
      self.ParseFromString(initializer.SerializeToString())

    elif initializer is not None:
      raise rdfvalue.InitializeError("Unable to initialize")

  def __len__(self):
    """Return the total number of path components."""
    i = -1
    for i, _ in enumerate(self):
      pass

    return i + 1

  def __getitem__(self, item):
    for i, element in enumerate(self):
      if i == item:
        return element

    raise IndexError("Pathspec index (%s) out of range" % item)

  def __iter__(self):
    """Only iterate over all components from the current pointer."""
    element = self
    while element.HasField("pathtype"):
      yield element

      if element.HasField("nested_path"):
        element = element.nested_path
      else:
        break

  def Insert(self, index, rdfpathspec=None, **kwarg):
    """Insert a single component at index."""
    if rdfpathspec is None:
      rdfpathspec = self.__class__(**kwarg)

    if index == 0:
      # Copy ourselves to a temp copy.
      nested_proto = self.__class__()
      nested_proto.SetRawData(self.GetRawData())

      # Replace ourselves with the new object.
      self.SetRawData(rdfpathspec.GetRawData())

      # Append the temp copy to the end.
      self.last.nested_path = nested_proto
    else:
      previous = self[index - 1]
      rdfpathspec.last.nested_path = previous.nested_path
      previous.nested_path = rdfpathspec

  def Append(self, component=None, **kwarg):
    """Append a new pathspec component to this pathspec."""
    if component is None:
      component = self.__class__(**kwarg)

    if self.HasField("pathtype"):
      self.last.nested_path = component
    else:
      for k, v in kwarg.items():
        setattr(self, k, v)

      self.SetRawData(component.GetRawData())

    return self

  def CollapsePath(self):
    return utils.JoinPath(*[x.path for x in self])

  def Pop(self, index=0):
    """Removes and returns the pathspec at the specified index."""
    if index < 0:
      index += len(self)

    if index == 0:
      result = self.__class__()
      result.SetRawData(self.GetRawData())

      self.SetRawData(self.nested_path.GetRawData())

    else:
      # Get the raw protobufs for the previous member.
      previous = self[index - 1]

      result = previous.nested_path

      # Manipulate the previous members protobuf to patch the next component in.
      previous.nested_path = result.nested_path

    result.nested_path = None

    return result

  @property
  def first(self):
    return self

  @property
  def last(self):
    if self.HasField("pathtype") and self.pathtype != self.PathType.UNSET:
      return list(self)[-1]

    return self

  def Dirname(self):
    """Get a new copied object with only the directory path."""
    result = self.Copy()

    while 1:
      last_directory = posixpath.dirname(result.last.path)
      if last_directory != "/" or len(result) <= 1:
        result.last.path = last_directory
        # Make sure to clear the inode information.
        result.last.inode = None

        break

      result.Pop(-1)

    return result

  def Basename(self):
    for component in reversed(self):
      basename = posixpath.basename(component.path)
      if basename:
        return basename

    return ""

  def Validate(self):
    if not self.HasField("pathtype") or self.pathtype == self.PathType.UNSET:
      raise ValueError("No path type set in PathSpec.")


class GlobExpression(rdfvalue.RDFString):
  """A glob expression for a client path.

  A glob expression represents a set of regular expressions which match files on
  the client. The Glob expression supports the following expansions:

  1) Client attribute expansions are surrounded with %% characters. They will be
     expanded from the client AFF4 object.

  2) Groupings are collections of alternates. e.g. {foo.exe,bar.sys}
  3) Wild cards like * and ?
  """

  context_help_url = "user_manual.html#_path_globbing"

  RECURSION_REGEX = re.compile(r"\*\*(\d*)")

  def Validate(self):
    """GlobExpression is valid."""
    if len(self.RECURSION_REGEX.findall(self._value)) > 1:
      raise ValueError("Only one ** is permitted per path: %s." % self._value)

  def Interpolate(self, client=None):
    kb = client.Get(client.Schema.KNOWLEDGE_BASE)
    patterns = artifact_utils.InterpolateKbAttributes(self._value, kb)

    for pattern in patterns:
      # Normalize the component path (this allows us to resolve ../
      # sequences).
      pattern = utils.NormalizePath(pattern.replace("\\", "/"))

      for pattern in self.InterpolateGrouping(pattern):
        yield pattern

  def InterpolateGrouping(self, pattern):
    """Interpolate inline globbing groups."""
    components = []
    offset = 0
    for match in GROUPING_PATTERN.finditer(pattern):
      components.append([pattern[offset:match.start()]])

      # Expand the attribute into the set of possibilities:
      alternatives = match.group(1).split(",")
      components.append(set(alternatives))
      offset = match.end()

    components.append([pattern[offset:]])
    # Now calculate the cartesian products of all these sets to form all
    # strings.
    for vector in itertools.product(*components):
      yield u"".join(vector)

  def AsRegEx(self):
    """Return the current glob as a simple regex.

    Note: No interpolation is performed.

    Returns:
      A RegularExpression() object.
    """
    return rdf_standard.RegularExpression("(?i)^" + fnmatch.translate(
        self._value))
