#!/usr/bin/env python
"""Filesystem related client rdfvalues."""

from __future__ import absolute_import
from __future__ import division

import stat

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


# These are objects we store as attributes of the client.
class Filesystem(rdf_structs.RDFProtoStruct):
  """A filesystem on the client.

  This class describes a filesystem mounted on the client.
  """
  protobuf = sysinfo_pb2.Filesystem
  rdf_deps = [
      rdf_protodict.AttributedDict,
  ]


class Filesystems(rdf_protodict.RDFValueArray):
  """An array of client filesystems.

  This is used to represent the list of valid filesystems on the client.
  """
  rdf_type = Filesystem


class FolderInformation(rdf_structs.RDFProtoStruct):
  """Representation of Window's special folders information for a User.

  Windows maintains a list of "Special Folders" which are used to organize a
  user's home directory. Knowledge about these is required in order to resolve
  the location of user specific items, e.g. the Temporary folder, or the
  Internet cache.
  """
  protobuf = jobs_pb2.FolderInformation


class WindowsVolume(rdf_structs.RDFProtoStruct):
  """A disk volume on a windows client."""
  protobuf = sysinfo_pb2.WindowsVolume


class UnixVolume(rdf_structs.RDFProtoStruct):
  """A disk volume on a unix client."""
  protobuf = sysinfo_pb2.UnixVolume


class Volume(rdf_structs.RDFProtoStruct):
  """A disk volume on the client."""
  protobuf = sysinfo_pb2.Volume
  rdf_deps = [
      rdfvalue.RDFDatetime,
      UnixVolume,
      WindowsVolume,
  ]

  def FreeSpacePercent(self):
    try:
      return (self.actual_available_allocation_units /
              self.total_allocation_units) * 100.0
    except ZeroDivisionError:
      return 100

  def FreeSpaceBytes(self):
    return self.AUToBytes(self.actual_available_allocation_units)

  def AUToBytes(self, allocation_units):
    """Convert a number of allocation units to bytes."""
    return (allocation_units * self.sectors_per_allocation_unit *
            self.bytes_per_sector)

  def AUToGBytes(self, allocation_units):
    """Convert a number of allocation units to GigaBytes."""
    return self.AUToBytes(allocation_units) // 1000.0**3

  def Name(self):
    """Return the best available name for this volume."""
    return (self.name or self.device_path or self.windowsvolume.drive_letter or
            self.unixvolume.mount_point or None)


class DiskUsage(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.DiskUsage


class Volumes(rdf_protodict.RDFValueArray):
  """A list of disk volumes on the client."""
  rdf_type = Volume


class StatMode(rdfvalue.RDFInteger):
  """The mode of a file."""
  data_store_type = "unsigned_integer"

  def __unicode__(self):
    """Pretty print the file mode."""
    type_char = "-"

    mode = int(self)
    if stat.S_ISREG(mode):
      type_char = "-"
    elif stat.S_ISBLK(mode):
      type_char = "b"
    elif stat.S_ISCHR(mode):
      type_char = "c"
    elif stat.S_ISDIR(mode):
      type_char = "d"
    elif stat.S_ISFIFO(mode):
      type_char = "p"
    elif stat.S_ISLNK(mode):
      type_char = "l"
    elif stat.S_ISSOCK(mode):
      type_char = "s"

    mode_template = "rwx" * 3
    # Strip the "0b"
    bin_mode = bin(int(self))[2:]
    bin_mode = bin_mode[-9:]
    bin_mode = "0" * (9 - len(bin_mode)) + bin_mode

    bits = []
    for i in range(len(mode_template)):
      if bin_mode[i] == "1":
        bit = mode_template[i]
      else:
        bit = "-"

      bits.append(bit)

    if stat.S_ISUID & mode:
      bits[2] = "S"
    if stat.S_ISGID & mode:
      bits[5] = "S"
    if stat.S_ISVTX & mode:
      if bits[8] == "x":
        bits[8] = "t"
      else:
        bits[8] = "T"

    return type_char + "".join(bits)

  def __str__(self):
    return utils.SmartStr(self.__unicode__())


class StatExtFlagsOsx(rdfvalue.RDFInteger):
  """Extended file attributes for Mac (set by `chflags`)."""

  data_store_type = "unsigned_integer_32"


class StatExtFlagsLinux(rdfvalue.RDFInteger):
  """Extended file attributes as reported by `lsattr`."""

  data_store_type = "unsigned_integer_32"


class ExtAttr(rdf_structs.RDFProtoStruct):
  """An RDF value representing an extended attributes of a file."""

  protobuf = jobs_pb2.StatEntry.ExtAttr


class StatEntry(rdf_structs.RDFProtoStruct):
  """Represent an extended stat response."""
  protobuf = jobs_pb2.StatEntry
  rdf_deps = [
      rdf_protodict.DataBlob,
      rdf_paths.PathSpec,
      rdfvalue.RDFDatetimeSeconds,
      StatMode,
      StatExtFlagsOsx,
      StatExtFlagsLinux,
      ExtAttr,
  ]

  def AFF4Path(self, client_urn):
    return self.pathspec.AFF4Path(client_urn)


class FindSpec(rdf_structs.RDFProtoStruct):
  """A find specification."""
  protobuf = jobs_pb2.FindSpec
  rdf_deps = [
      rdf_paths.GlobExpression,
      rdf_client_action.Iterator,
      rdf_paths.PathSpec,
      rdfvalue.RDFDatetime,
      rdf_standard.RegularExpression,
      StatEntry,
      StatMode,
  ]

  def Validate(self):
    """Ensure the pathspec is valid."""
    self.pathspec.Validate()

    if (self.HasField("start_time") and self.HasField("end_time") and
        self.start_time > self.end_time):
      raise ValueError("Start time must be before end time.")

    if not self.path_regex and not self.data_regex and not self.path_glob:
      raise ValueError("A Find specification can not contain both an empty "
                       "path regex and an empty data regex")


class BareGrepSpec(rdf_structs.RDFProtoStruct):
  """A GrepSpec without a target."""
  protobuf = flows_pb2.BareGrepSpec
  rdf_deps = [
      rdf_standard.LiteralExpression,
      rdf_standard.RegularExpression,
  ]


class GrepSpec(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.GrepSpec
  rdf_deps = [
      rdf_standard.LiteralExpression,
      rdf_paths.PathSpec,
      rdf_standard.RegularExpression,
  ]

  def Validate(self):
    self.target.Validate()


class BlobImageChunkDescriptor(rdf_structs.RDFProtoStruct):
  """A descriptor of a file chunk stored in VFS blob image."""

  protobuf = jobs_pb2.BlobImageChunkDescriptor
  rdf_deps = []


class BlobImageDescriptor(rdf_structs.RDFProtoStruct):
  """A descriptor of a file stored as VFS blob image."""

  protobuf = jobs_pb2.BlobImageDescriptor
  rdf_deps = [BlobImageChunkDescriptor]
