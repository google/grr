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

"""These are standard aff4 objects."""


import stat
import urllib

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


def DateTime(value):
  """Convert an integer in seconds into an RDFDatetime object."""
  return aff4.RDFDatetime(value * aff4.MICROSECONDS)


class StatEntry(aff4.RDFProto):
  """Represent an extended stat response."""
  _proto = jobs_pb2.StatResponse

  # Translate these fields as RDFValue objects.
  rdf_map = dict(st_mtime=DateTime,
                 st_atime=DateTime,
                 st_ctime=DateTime,
                 st_inode=aff4.RDFInteger,
                 st_dev=aff4.RDFInteger,
                 st_nlink=aff4.RDFInteger,
                 st_size=aff4.RDFInteger)


class DirectoryInode(aff4.RDFProto):
  """Allows the DirectoryINode which allows it to be stored as an RDFValue."""
  _proto = jobs_pb2.DirectoryINode

  def AddDirectoryEntry(self, entry):
    self.data.children.extend([entry])

  def __iter__(self):
    for child in self.data.children:
      yield child


class VFSDirectory(aff4.AFF4Volume):
  """This represents a directory from the client."""
  default_container = "VFSDirectory"

  # We contain other objects within the tree.
  _behaviours = frozenset(["Container"])

  def Query(self, filter_string="", filter_obj=None):
    # Parse the query string
    ast = aff4.AFF4QueryParser(filter_string).Parse()

    # Query our own data store
    filter_obj = ast.Compile(aff4.AFF4Filter)

    for child in filter_obj.Filter(self.OpenChildren()):
      yield child

  def _OpenDirectory(self, child, stem, mode, age):
    """Open the direct_child as a directory."""
    # No it does not already exist - we create it
    result = self.CreateMember(child.path, self.default_container,
                               clone={}, mode=mode)

    result.Set(result.Schema.STAT, StatEntry(child, age=age))
    if stem:
      result = result.Open(stem)

    return result

  def _OpenDirectChildAsFile(self, child, mode, age):
    """Opens the direct_child as a file or psuedo-file."""
    # Does the child already exist? If so just open it
    fd = aff4.FACTORY.AFF4Object("VFSMemoryFile")(
        self.urn.Add(child.path), mode)
    # Pass some common attributes to it from the DirectoryINode
    fd.Set(fd.Schema.STORED, self.urn)
    fd.Set(fd.Schema.SIZE, aff4.RDFInteger(child.st_size, age=age))
    fd.Set(fd.Schema.STAT, StatEntry(child, age=age))

    if child.resident:
      fd.Write(child.resident)
      fd.Seek(0)

    return fd

  def Open(self, path, mode="r"):
    """If this directory contains a resident file, we just serve it directly."""
    result = None
    path_elements = path.split("/", 1)
    direct_child = path_elements[0]
    try:
      stem = "/".join(path_elements[1:])
    except IndexError:
      stem = ""

    result = self._OpenDirectChild(direct_child, stem, mode)
    if stem:
      result = result.Open(stem)

    return result

  def _OpenDirectChild(self, direct_child, stem, mode="r"):
    """Open the direct child."""
    # Try to open this as a regular AFF4 object
    try:
      return super(VFSDirectory, self).Open(direct_child, mode)
    except IOError:
      return self._OpenVirtualisedChild(direct_child, stem, mode="r")

  def _OpenVirtualisedChild(self, direct_child, stem, mode="r"):
    # Following here we virtualize the object, making it not necessary to have
    # specialized storage for it, we just use the DIRECTORY attribute to work
    # out what objects we should contain.
    directory = self.Get(self.Schema.DIRECTORY)
    if directory:
      for child in directory:
        # Found the direct_child in the DIRECTORY attribute
        if child.path == direct_child:
          # Is the child a directory?
          if stat.S_ISDIR(child.st_mode):
            return self._OpenDirectory(child, stem, mode, directory.age)
          # Prepare a one time memory resident file - this saves us from
          # actually storing it in the data store separately
          else:
            return self._OpenDirectChildAsFile(child, mode, directory.age)

    # Otherwise we dont have this file
    raise IOError("File does not exist")

  def ListChildren(self):
    """List our children.

    In addition to the regular way, we also list the objects which are contained
    in our DIRECTORY attribute. Note that the objects might not actually exist
    in our data store - we just infer their existence from our Directory Inode
    structure. Typically users can try to open the child and if that fails,
    issue a flow to recover it.

    Returns:
       A dict of all direct children and their types.
    """
    results, age = super(VFSDirectory, self).ListChildren()

    directory = self.Get(self.Schema.DIRECTORY)
    if directory:
      age = directory.age
      for child in directory:
        if child.resident:
          child_type = "AFF4MemoryStream"
        elif stat.S_ISDIR(child.st_mode):
          child_type = "VFSDirectory"
        else:
          child_type = "AFF4Stream"

        child_urn = self.urn.Add(child.path)
        results[child_urn] = child_type

    return results, age

  def OpenChildren(self, children=None, mode="r"):
    """Add children from DIRECTORY attribute."""
    if children is None:
      children, _ = self.ListChildren()

    # Convert all children to RDFURNs
    urn_children = []
    for child in children:
      if not isinstance(child, aff4.RDFURN):
        child = self.urn.Add(child)

      urn_children.append(child)

    results = {}

    # Get those children from the baseclass
    for fd in super(VFSDirectory, self).OpenChildren(
        mode=mode, children=urn_children):
      results[fd.urn] = fd

    # These should be virtualized and therefore very fast.
    for child in urn_children:
      if child not in results:
        results[child] = self._OpenVirtualisedChild(
            child.RelativeName(self.urn), "", mode=mode)

    for child in urn_children:
      yield results[child]

  def Update(self, attribute=None, user=None):
    """Refresh an old attribute.

    Note that refreshing the attribute is asynchronous. It does not change
    anything about the current object - you need to reopen the same URN some
    time later to get fresh data.

    Attributes:
       CONTAINS - Refresh the content of the directory listing.

    Args:
       attribute: An attribute object as listed above.
       user: The username which makes this request.

    Returns:
       The Flow ID that is pending
    """
    if attribute == self.Schema.DIRECTORY:
      path_elements = [urllib.unquote(x) for x in self.urn.Path().split("/")]
      client_id = path_elements[1]
      path = "/" + "/".join(path_elements[2:]) + "/"

      p = utils.Aff4ToPathspec(path)
      flow_id = flow.FACTORY.StartFlow(client_id, "ListDirectory", user=user,
                                       path=p.path, pathtype=p.pathtype)

      return flow_id

  class Schema(aff4.AFF4Volume.Schema):
    """Attributes specific to VFSDirectory."""
    DIRECTORY = aff4.Attribute("aff4:directory_listing", DirectoryInode,
                               "A list of StatResponses of contained files.")

    STAT = aff4.Attribute("aff4:stat", StatEntry,
                          "A StatResponse protobuf describing this file.",
                          "Stat")
