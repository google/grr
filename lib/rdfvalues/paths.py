#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
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

import posixpath

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import structs
from grr.proto import jobs_pb2


class PathSpec(structs.RDFProtoStruct):
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
      self.SetRawData(initializer.Copy().GetRawData())
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
    while element.pathtype >= 0:
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
      previous = self[index-1]
      rdfpathspec.last.nested_path = previous.nested_path
      previous.nested_path = rdfpathspec

  def Append(self, component=None, **kwarg):
    """Append a new pathspec component to this pathspec."""
    if component is None:
      component = self.__class__(**kwarg)

    if self:
      self.last.nested_path = component
    else:
      for k, v in kwarg.items():
        setattr(self, k, v)

      self.SetRawData(component.GetRawData())

    return self

  def AppendPath(self, path_component):
    self.last.path = utils.Join(self.last.path, path_component)

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
      previous = self[index-1]

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
    return list(self)[-1]

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
      if basename: return basename

    return ""


class PathTypeEnum(type_info.SemanticEnum):
  """Represent pathspec's pathtypes enum especially."""

  def __init__(self, **kwargs):
    defaults = dict(name="pathtype",
                    description="The type of access for this path.",
                    default=PathSpec.PathType.OS,
                    friendly_name="Type",
                    enum_container=PathSpec.PathType)

    defaults.update(kwargs)
    super(PathTypeEnum, self).__init__(**defaults)

  def Validate(self, value):
    if value < 0:
      raise type_info.TypeValueError("Path type must be set")

    return super(PathTypeEnum, self).Validate(value)


class PathspecType(type_info.RDFValueType):
  """A Type for handling pathspecs."""

  # These specify the child descriptors of a pathspec.
  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(description="Path to the file.",
                       name="path",
                       friendly_name="Path",
                       default="/"),
      PathTypeEnum())

  def __init__(self, **kwargs):
    defaults = dict(
        default=rdfvalue.PathSpec(
            path="/",
            pathtype=rdfvalue.PathSpec.PathType.OS),
        name="pathspec",
        rdfclass=rdfvalue.PathSpec)

    defaults.update(kwargs)
    super(PathspecType, self).__init__(**defaults)

  def GetDefault(self):
    if not self.default:
      return None
    return self.default.Copy()


class MemoryPathspecType(PathspecType):
  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(description="Path to the memory device file.",
                       name="path",
                       friendly_name="Memory device path",
                       default=r"\\.\pmem"),
      PathTypeEnum(default=rdfvalue.PathSpec.PathType.MEMORY))
