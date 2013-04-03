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

On the server the PathSpec is represented as an RDFPathSpec object, and stored
as an attribute of the AFF4 object. This module defines this abstraction.
"""

import posixpath

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class RDFPathSpec(rdfvalue.RDFProto):
  """A path specification.

  The pathspec protobuf is a recursive protobuf which contains components. This
  class makes it easier to manipulate these structures by providing useful
  helpers.
  """
  _proto = jobs_pb2.Path

  # This is the base of the pathspec protobuf (i.e. the first outermost Path
  # component).
  _data = None

  def __init__(self, initializer=None, age=None, **kwargs):
    super(RDFPathSpec, self).__init__(age=age)

    # Create a new protobuf to work with
    if initializer is None:
      self._data = self._proto(**kwargs)

    # Instantiate from another RDFPathSpec.
    elif isinstance(initializer, RDFPathSpec):
      self._data = initializer._data  # pylint:disable=protected-access
      self.age = initializer.age

    # Allow initialization from a list of protobufs each representing a
    # component.
    elif isinstance(initializer, list):
      self._data = self._proto(**kwargs)
      for element in initializer:
        # Append the protobuf to the end of our own pathspec..
        self.last._data.MergeFrom(element)  # pylint:disable=protected-access

    # Allow ourselves to be instantiated from a single protobuf. In that case we
    # just wrap the protobuf, i.e. any changes made to the RDFPathSpec will be
    # refected in the underlying protobuf. This is useful for modifying Path
    # protobufs which are embedded inside other protobufs.
    elif isinstance(initializer, self._proto):
      self._data = initializer

    # Or we can initialize from a string.
    elif isinstance(initializer, str):
      self._data = self._proto(**kwargs)
      self.ParseFromString(initializer)

    else:
      raise TypeError("Unable to initialize")

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

    raise ValueError("Pathspec index (%s) out of range" % item)

  def __iter__(self):
    """Only iterate over all components from the current pointer."""
    element = self._data
    while element.pathtype >= 0:
      yield element
      element = element.nested_path

  def Copy(self):
    """Return a copy of this pathspec."""
    result = RDFPathSpec()
    result._data.CopyFrom(self._data)  # pylint: disable=protected-access

    return result

  def Insert(self, index, rdfpathspec=None, **kwarg):
    """Insert a single component at index."""
    if rdfpathspec:
      # Support inserting another RDFPathSpec.
      new_proto = rdfvalue.RDFPathSpec(rdfpathspec).ToProto()
    else:
      new_proto = self._proto(**kwarg)
    if index == 0:
      new_proto.nested_path.MergeFrom(self._data)
      self._data = new_proto
    else:
      previous = self[index-1]
      nested_path = jobs_pb2.Path()
      nested_path.CopyFrom(previous.nested_path)
      previous.nested_path.MergeFrom(new_proto)
      # Merging an emtpy protobuf will still set the field so we aviod this.
      if nested_path.pathtype != jobs_pb2.Path.UNSET:
        previous.nested_path.nested_path.MergeFrom(nested_path)

  def Append(self, *args, **kwarg):
    """Append a new pathspec component to this pathspec."""
    self.Insert(len(self), *args, **kwarg)
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
      result = RDFPathSpec(self._data)

      # Replace our internal data structures with the next position.
      self._data = result.nested_path.ToProto()

      # Return a fresh copy.
      result = result.Copy()
      result._data.ClearField("nested_path")  # pylint:disable=protected-access

    else:
      # Get the raw protobufs for the previous member.
      previous = self[index-1]

      result = RDFPathSpec(previous.nested_path).Copy()

      # Manipulate the previous members protobuf to patch the next component in.
      previous.ClearField("nested_path")
      previous.nested_path.MergeFrom(result.nested_path.ToProto())

      result.ClearField("nested_path")

    return result

  def __str__(self):
    return "RDFPathspec(%s)" % (utils.SmartStr(self._data))

  def __unicode__(self):
    return u"RDFPathspec(%s)" % (utils.SmartUnicode(self._data))

  @property
  def first(self):
    return self

  @property
  def last(self):
    return list(self)[-1]

  @property
  def nested_path(self):
    result = RDFPathSpec(self._data.nested_path)

    return result

  def Dirname(self):
    """Get a new copied object with only the directory path."""
    result = self.Copy()

    while result:
      last = result.Pop(len(result)-1)
      if utils.NormalizePath(last.path) != "/":
        dirname = utils.NormalizePath(posixpath.dirname(last.path))
        result.Append(path=dirname, pathtype=last.pathtype)
        break

    return result

  def Basename(self):
    for component in reversed(self):
      basename = posixpath.basename(component.path)
      if basename: return basename

    return ""


class PathTypeEnum(type_info.RDFEnum):
  """Represent pathspec's pathtypes enum especially."""

  def __init__(self, **kwargs):
    defaults = dict(name="pathtype",
                    description="The type of access for this path.",
                    default=RDFPathSpec.Enum("OS"),
                    friendly_name="Type",
                    rdfclass=RDFPathSpec,
                    enum_name="PathType")

    defaults.update(kwargs)
    super(PathTypeEnum, self).__init__(**defaults)

  def Validate(self, value):
    if value < 0:
      raise ValueError("Path type must be set")

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
        default=rdfvalue.RDFPathSpec(
            path="/",
            pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
        name="pathspec",
        rdfclass=rdfvalue.RDFPathSpec)

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
      PathTypeEnum(default=rdfvalue.RDFPathSpec.Enum("MEMORY")))
