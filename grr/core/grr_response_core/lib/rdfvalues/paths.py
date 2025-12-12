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

from collections.abc import Iterable, Iterator, Sequence
import itertools
import posixpath
import re
from typing import Optional

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2


class PathSpec(rdf_structs.RDFProtoStruct):
  """A path specification.

  The pathspec protobuf is a recursive protobuf which contains components. This
  class makes it easier to manipulate these structures by providing useful
  helpers.
  """

  protobuf = jobs_pb2.PathSpec
  rdf_deps = [
      rdfvalue.ByteSize,
      "PathSpec",  # TODO(user): recursive definition.
  ]

  @classmethod
  def OS(cls, **kwargs):
    return cls(pathtype=PathSpec.PathType.OS, **kwargs)

  @classmethod
  def TSK(cls, **kwargs):
    return cls(pathtype=PathSpec.PathType.TSK, **kwargs)

  @classmethod
  def NTFS(cls, **kwargs):
    return cls(pathtype=PathSpec.PathType.NTFS, **kwargs)

  @classmethod
  def Registry(cls, **kwargs):
    return cls(pathtype=PathSpec.PathType.REGISTRY, **kwargs)

  @classmethod
  def Temp(cls, **kwargs):
    return cls(pathtype=PathSpec.PathType.TMPFILE, **kwargs)

  def __len__(self):
    """Return the total number of path components."""
    i = -1
    # TODO(user):pytype: type checker doesn't treat self as iterable.
    for i, _ in enumerate(self):  # pytype: disable=wrong-arg-types
      pass

    return i + 1

  def __getitem__(self, item):
    # TODO(user):pytype: type checker doesn't treat self as iterable.
    for i, element in enumerate(self):  # pytype: disable=wrong-arg-types
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
      # TODO(user):pytype: type checker doesn't treat self as iterable.
      return list(self)[-1]  # pytype: disable=wrong-arg-types

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
    # TODO(user):pytype: type checker doesn't treat self as reversible.
    for component in reversed(self):  # pytype: disable=wrong-arg-types
      basename = posixpath.basename(component.path)
      if basename:
        return basename

    return ""

  def Validate(self):
    if not self.HasField("pathtype") or self.pathtype == self.PathType.UNSET:
      raise ValueError("No path type set in PathSpec.")

  AFF4_PREFIXES = {
      0: "/fs/os",  # PathSpec.PathType.OS
      1: "/fs/tsk",  # PathSpec.PathType.TSK
      2: "/registry",  # PathSpec.PathType.REGISTRY
      4: "/temp",  # PathSpec.PathType.TMPFILE
      5: "/fs/ntfs",  # PathSpec.PathType.NTFS
  }

  def AFF4Path(self, client_urn):
    """Returns the AFF4 URN this pathspec will be stored under.

    Args:
      client_urn: A ClientURN.

    Returns:
      A urn that corresponds to this pathspec.

    Raises:
      ValueError: If pathspec is not of the correct type.
    """
    # If the first level is OS and the second level is TSK its probably a mount
    # point resolution. We map it into the tsk branch. For example if we get:
    # path: \\\\.\\Volume{1234}\\
    # pathtype: OS
    # mount_point: /c:/
    # nested_path {
    #    path: /windows/
    #    pathtype: TSK
    # }
    # We map this to aff4://client_id/fs/tsk/\\\\.\\Volume{1234}\\/windows/
    # (The same applies for NTFS)

    if not self.HasField("pathtype"):
      raise ValueError(
          "Can't determine AFF4 path without a valid pathtype for {}.".format(
              self
          )
      )

    first_component = self[0]
    dev = first_component.path
    if first_component.HasField("offset"):
      # We divide here just to get prettier numbers in the GUI
      dev += ":{}".format(first_component.offset // 512)

    if (
        len(self) > 1
        and first_component.pathtype == PathSpec.PathType.OS
        and self[1].pathtype in (PathSpec.PathType.TSK, PathSpec.PathType.NTFS)
    ):
      result = [self.AFF4_PREFIXES[self[1].pathtype], dev]

      # Skip the top level pathspec.
      start = 1
    else:
      # For now just map the top level prefix based on the first pathtype
      result = [self.AFF4_PREFIXES[first_component.pathtype]]
      start = 0

    for p in self[start]:
      component = p.path

      # The following encode different pathspec properties into the AFF4 path in
      # such a way that unique files on the client are mapped to unique URNs in
      # the AFF4 space. Note that this transformation does not need to be
      # reversible since we always use the PathSpec when accessing files on the
      # client.
      if p.HasField("offset"):
        component += ":{}".format(p.offset // 512)

      # Support ADS names.
      if p.HasField("stream_name"):
        component += ":" + p.stream_name

      result.append(component)

    return client_urn.Add("/".join(result))


def _Unique(iterable: Iterable[str]) -> Sequence[str]:
  """Returns a list of unique values in preserved order."""
  return list(dict.fromkeys(iterable))


class GlobComponentExplanation(rdf_structs.RDFProtoStruct):
  """A sub-part of a GlobExpression with examples."""

  protobuf = flows_pb2.GlobComponentExplanation


# Grouping pattern: e.g. {test.exe,foo.doc,bar.txt}
GROUPING_PATTERN = re.compile("{([^}]+,[^}]+)}")

_VAR_PATTERN = re.compile("(" + "|".join([r"%%\w+%%", r"%%\w+\.\w+%%"]) + ")")

_REGEX_SPLIT_PATTERN = re.compile(
    "(" + "|".join(["{[^}]+,[^}]+}", "\\?", "\\*\\*\\/?", "\\*"]) + ")"
)

_COMPONENT_SPLIT_PATTERN = re.compile(
    "("
    + "|".join([
        r"{[^}]+,[^}]+}",
        r"\?",
        r"\*\*\d*/?",
        r"\*",
        r"%%\w+%%",
        r"%%\w+\.\w+%%",
    ])
    + ")"
)


class GlobExpression(rdfvalue.RDFString):
  """A glob expression for a client path.

  A glob expression represents a set of regular expressions which match files on
  the client. The Glob expression supports the following expansions:

  1) Client attribute expansions are surrounded with %% characters. They will be
     expanded from the client AFF4 object.

  2) Groupings are collections of alternates. e.g. {foo.exe,bar.sys}
  3) Wild cards like * and ?
  """

  context_help_url = "investigating-with-grr/flows/specifying-file-paths.html"

  RECURSION_REGEX = re.compile(r"\*\*(\d*)")

  def Validate(self):
    """GlobExpression is valid."""
    if len(self.RECURSION_REGEX.findall(self._value)) > 1:
      raise ValueError("Only one ** is permitted per path: %s." % self._value)

  def Interpolate(
      self,
      knowledge_base: Optional[knowledge_base_pb2.KnowledgeBase] = None,
  ) -> Iterator[str]:
    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern=self._value,
        kb=knowledge_base or knowledge_base_pb2.KnowledgeBase(),
    )

    for pattern in interpolation.results:
      # Normalize the component path (this allows us to resolve ../
      # sequences).
      pattern = utils.NormalizePath(pattern.replace("\\", "/"))

      for p in self.InterpolateGrouping(pattern):
        yield p

  def InterpolateGrouping(
      self,
      pattern: str,
  ) -> Iterator[str]:
    """Interpolate inline globbing groups."""
    components = []
    offset = 0
    for match in GROUPING_PATTERN.finditer(pattern):
      components.append([pattern[offset : match.start()]])

      # Expand the attribute into the set of possibilities:
      alternatives = match.group(1).split(",")
      components.append(_Unique(alternatives))
      offset = match.end()

    components.append([pattern[offset:]])
    # Now calculate the cartesian products of all these sets to form all
    # strings.
    for vector in itertools.product(*components):
      yield "".join(vector)

  def _ReplaceRegExGrouping(self, grouping: re.Match[str]) -> str:
    alternatives = grouping.group(1).split(",")
    return "(" + "|".join(re.escape(s) for s in alternatives) + ")"

  def _ReplaceRegExPart(self, part: str) -> str:
    if part == "**/":
      return "(?:.*\\/)?"
    elif part == "*":
      return "[^\\/]*"
    elif part == "?":
      return "[^\\/]"
    elif GROUPING_PATTERN.match(part):
      return GROUPING_PATTERN.sub(self._ReplaceRegExGrouping, part)
    else:
      return re.escape(part)

  def ExplainComponents(
      self,
      example_count: int,
      knowledge_base: knowledge_base_pb2.KnowledgeBase,
  ) -> Sequence[flows_pb2.GlobComponentExplanation]:
    """Returns a list of GlobComponentExplanations with examples."""
    parts = _COMPONENT_SPLIT_PATTERN.split(self._value)
    components = []

    for glob_part in parts:
      if not glob_part:
        continue

      component = flows_pb2.GlobComponentExplanation(glob_expression=glob_part)

      if GROUPING_PATTERN.match(glob_part):
        examples = self.InterpolateGrouping(glob_part)
      elif _VAR_PATTERN.match(glob_part):
        # Examples for variable substitutions might not be 100 % accurate,
        # because the scope is not shared between two variables. Thus,
        # if a GlobExpression uses %%users.a%% and %%users.b%%, the underlying
        # user might be different for a and b. For the sake of explaining
        # possible values, this should still be enough.
        interpolation = artifact_utils.KnowledgeBaseInterpolation(
            pattern=glob_part,
            kb=knowledge_base,
        )

        examples = interpolation.results
      else:
        examples = []

      component.examples.extend(list(itertools.islice(examples, example_count)))
      components.append(component)

    return components

  def AsRegEx(self) -> rdf_standard.RegularExpression:
    """Return the current glob as a simple regex.

    Note: No interpolation is performed.

    Returns:
      A RegularExpression() object.
    """
    parts = _REGEX_SPLIT_PATTERN.split(self._value)
    result = "".join(self._ReplaceRegExPart(p) for p in parts)

    return rdf_standard.RegularExpression("(?i)\\A%s\\Z" % result)
