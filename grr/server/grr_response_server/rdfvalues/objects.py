#!/usr/bin/env python
# Lint as: python3
"""Top level datastore objects.

This package contains the rdfvalue wrappers around the top level datastore
objects defined by objects.proto.
"""

import functools
import hashlib
import itertools
import os
import stat
from typing import Text


from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.lib.util import text
from grr_response_proto import objects_pb2

_UNKNOWN_GRR_VERSION = "Unknown-GRR-version"


class ClientLabel(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientLabel


class StringMapEntry(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.StringMapEntry


class ClientSnapshot(rdf_structs.RDFProtoStruct):
  """The client object.

  Attributes:
    timestamp: An rdfvalue.Datetime indicating when this client snapshot was
      saved to the database. Should be present in every client object loaded
      from the database, but is not serialized with the rdfvalue fields.
  """
  protobuf = objects_pb2.ClientSnapshot

  rdf_deps = [
      StringMapEntry,
      rdf_cloud.CloudInstance,
      rdf_client.EdrAgent,
      rdf_client_fs.Filesystem,
      rdf_client.HardwareInfo,
      rdf_client_network.Interface,
      rdf_client.KnowledgeBase,
      rdf_client.StartupInfo,
      rdf_client_fs.Volume,
      rdfvalue.ByteSize,
      rdfvalue.RDFDatetime,
      rdf_client.FleetspeakValidationInfo,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.timestamp = None

  def Uname(self):
    """OS summary string."""
    return "%s-%s-%s" % (self.knowledge_base.os, self.os_release,
                         self.os_version)

  def GetGRRVersionString(self):
    """Returns the client installation-name and GRR version as a string."""
    client_info = self.startup_info.client_info
    client_name = client_info.client_description or client_info.client_name
    if client_info.client_version > 0:
      client_version = str(client_info.client_version)
    else:
      client_version = _UNKNOWN_GRR_VERSION
    return " ".join([client_name, client_version])

  def GetMacAddresses(self):
    """MAC addresses from all interfaces."""
    result = set()
    for interface in self.interfaces:
      if (interface.mac_address and
          interface.mac_address != b"\x00" * len(interface.mac_address)):
        result.add(Text(interface.mac_address.human_readable_address))
    return sorted(result)

  def GetIPAddresses(self):
    """IP addresses from all interfaces."""
    result = []
    filtered_ips = ["127.0.0.1", "::1", "fe80::1"]

    for interface in self.interfaces:
      for address in interface.addresses:
        if address.human_readable_address not in filtered_ips:
          result.append(Text(address.human_readable_address))
    return sorted(result)

  def GetSummary(self):
    """Gets a client summary object.

    Returns:
      rdf_client.ClientSummary
    Raises:
      ValueError: on bad cloud type
    """
    summary = rdf_client.ClientSummary()
    summary.client_id = self.client_id
    summary.timestamp = self.timestamp

    summary.system_info.release = self.os_release
    summary.system_info.version = str(self.os_version or "")
    summary.system_info.kernel = self.kernel
    summary.system_info.machine = self.arch
    summary.system_info.install_date = self.install_time
    kb = self.knowledge_base
    if kb:
      summary.system_info.fqdn = kb.fqdn
      summary.system_info.system = kb.os
      summary.users = kb.users
      summary.interfaces = self.interfaces
      summary.client_info = self.startup_info.client_info
      if kb.os_release:
        summary.system_info.release = kb.os_release
        if kb.os_major_version:
          summary.system_info.version = "%d.%d" % (kb.os_major_version,
                                                   kb.os_minor_version)

    summary.edr_agents = self.edr_agents
    summary.fleetspeak_validation_info = self.fleetspeak_validation_info

    hwi = self.hardware_info
    if hwi:
      summary.serial_number = hwi.serial_number
      summary.system_manufacturer = hwi.system_manufacturer
      summary.system_uuid = hwi.system_uuid

    cloud_instance = self.cloud_instance
    if cloud_instance:
      summary.cloud_type = cloud_instance.cloud_type
      if cloud_instance.cloud_type == "GOOGLE":
        summary.cloud_instance_id = cloud_instance.google.unique_id
      elif cloud_instance.cloud_type == "AMAZON":
        summary.cloud_instance_id = cloud_instance.amazon.instance_id
      else:
        raise ValueError("Bad cloud type: %s" % cloud_instance.cloud_type)

    return summary


class ClientMetadata(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientMetadata

  rdf_deps = [
      rdf_client_network.NetworkAddress,
      rdf_crypto.RDFX509Cert,
      rdfvalue.RDFDatetime,
      rdf_client.FleetspeakValidationInfo,
  ]


class ClientFullInfo(rdf_structs.RDFProtoStruct):
  """ClientFullInfo object."""
  protobuf = objects_pb2.ClientFullInfo

  rdf_deps = [
      ClientMetadata,
      ClientSnapshot,
      ClientLabel,
      rdf_client.StartupInfo,
  ]

  def GetLabelsNames(self, owner=None):
    return set(
        Text(l.name) for l in self.labels if not owner or l.owner == owner)


class GRRUser(rdf_structs.RDFProtoStruct):
  """GRRUser object."""
  protobuf = objects_pb2.GRRUser
  rdf_deps = [
      rdf_crypto.Password,
  ]

  def GetEmail(self):
    """Returns the E-Mail address for the user."""
    if config.CONFIG.Get("Email.enable_custom_email_address") and self.email:
      return self.email

    return "{}@{}".format(self.username, config.CONFIG.Get("Logging.domain"))


class ApprovalGrant(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalGrant
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApprovalRequest(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
      ApprovalGrant,
  ]

  @property
  def is_expired(self):
    return self.expiration_time < rdfvalue.RDFDatetime.Now()


@functools.total_ordering
class HashID(rdfvalue.RDFValue):
  """An unique hash identifier."""

  __abstract = True  # pylint: disable=g-bad-name

  protobuf_type = "bytes"

  hash_id_length = None

  def __init__(self, initializer=None):
    if self.__class__.hash_id_length is None:
      raise TypeError("Trying to instantiate base HashID class. "
                      "hash_id_length has to be set.")

    super().__init__()

    if isinstance(initializer, HashID):
      initializer = initializer._value  # pylint: disable=protected-access

    if initializer is None:
      initializer = b"\x00" * self.__class__.hash_id_length

    precondition.AssertType(initializer, (bytes, rdfvalue.RDFBytes))

    if len(initializer) != self.__class__.hash_id_length:
      raise ValueError(
          "Expected %s bytes but got `%s` `%s` instead" %
          (self.__class__.hash_id_length, len(initializer), initializer))

    if isinstance(initializer, rdfvalue.RDFBytes):
      self._value = initializer.SerializeToBytes()
    else:
      self._value = initializer

  @classmethod
  def FromWireFormat(cls, value):
    precondition.AssertType(value, bytes)
    return cls(value)

  def SerializeToBytes(self):
    return self.AsBytes()

  @classmethod
  def FromSerializedBytes(cls, value: bytes):
    precondition.AssertType(value, bytes)
    return cls(value)

  def AsBytes(self):
    return self._value

  def AsHexString(self):
    return text.Hexify(self._value)

  def AsHashDigest(self):
    return rdfvalue.HashDigest(self._value)

  def __repr__(self):
    cls_name = compatibility.GetName(self.__class__)
    value = text.Hexify(self._value)
    return "{cls_name}('{value}')".format(cls_name=cls_name, value=value)

  def __str__(self):
    return self.__repr__()

  def __lt__(self, other):
    if isinstance(other, self.__class__):
      return self._value < other._value  # pylint: disable=protected-access
    else:
      return self._value < other

  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self._value == other._value  # pylint: disable=protected-access
    else:
      return self._value == other

  # Required, because in Python 3 overriding `__eq__` nullifies `__hash__`.
  __hash__ = rdfvalue.RDFValue.__hash__


class PathID(HashID):
  """An unique path identifier corresponding to some path.

  Args:
    components: A list of path components to construct the identifier from.
  """

  hash_id_length = 32

  @classmethod
  def FromComponents(cls, components):
    _ValidatePathComponents(components)

    if components:
      # We need a string to hash, based on components. If we simply concatenated
      # them, or used a separator that could appear in some component, odd data
      # could force a hash collision. So we explicitly include the lengths of
      # the components.
      string = "{lengths}:{path}".format(
          lengths=",".join(str(len(component)) for component in components),
          path="/".join(components))
      result = hashlib.sha256(string.encode("utf-8")).digest()
    else:
      # For an empty list of components (representing `/`, i.e. the root path),
      # we use special value: zero represented as a 256-bit number.
      result = b"\0" * 32

    return PathID(result)


class PathInfo(rdf_structs.RDFProtoStruct):
  """Basic metadata about a path which has been observed on a client."""
  protobuf = objects_pb2.PathInfo
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdf_client_fs.StatEntry,
      rdf_crypto.Hash,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    _ValidatePathComponents(self.components)

  # TODO(hanuszczak): Find a reliable way to make sure that noone ends up with
  # incorrect `PathInfo` (a one that is both root and non-directory). Simple
  # validation in a constructor has two flaws:
  #
  # a) One can still screw it up by setting directory to `False` on already
  #    constructed value.
  # b) The `Copy` method temporarily constructs an incorrect object and assigns
  #    all the fields afterwards.

  @classmethod
  def OS(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.OS, **kwargs)

  @classmethod
  def TSK(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.TSK, **kwargs)

  @classmethod
  def Registry(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.REGISTRY, **kwargs)

  @classmethod
  def NTFS(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.NTFS, **kwargs)

  @classmethod
  def PathTypeFromPathspecPathType(cls, ps_path_type):
    if ps_path_type == rdf_paths.PathSpec.PathType.OS:
      return cls.PathType.OS
    elif ps_path_type == rdf_paths.PathSpec.PathType.TSK:
      return cls.PathType.TSK
    elif ps_path_type == rdf_paths.PathSpec.PathType.REGISTRY:
      return cls.PathType.REGISTRY
    elif ps_path_type == rdf_paths.PathSpec.PathType.TMPFILE:
      return cls.PathType.TEMP
    elif ps_path_type == rdf_paths.PathSpec.PathType.NTFS:
      return cls.PathType.NTFS
    else:
      raise ValueError("Unexpected path type: %s" % ps_path_type)

  @classmethod
  def FromPathSpec(cls, pathspec):
    # Note that since PathSpec objects may contain more information than what is
    # stored in a PathInfo object, we can only create a PathInfo object from a
    # PathSpec, never the other way around.

    path_type = cls.PathTypeFromPathspecPathType(pathspec.last.pathtype)

    components = []
    for pathelem in pathspec:
      path = pathelem.path
      if pathelem.offset:
        path += ":%s" % pathelem.offset
      if pathelem.stream_name:
        path += ":%s" % pathelem.stream_name

      # TODO(hanuszczak): Sometimes the paths start with '/', sometimes they do
      # not (even though they are all supposed to be absolute). If they do start
      # with `/` we get an empty component at the beginning which needs to be
      # removed.
      #
      # It is also possible that path is simply '/' which, if split, yields two
      # empty components. To simplify things we just filter out all empty
      # components. As a side effect we also support pathological cases such as
      # '//foo//bar////baz'.
      #
      # Ideally, pathspec should only allow one format (either with or without
      # leading slash) sanitizing the input as soon as possible.
      components.extend(component for component in path.split("/") if component)

    return cls(path_type=path_type, components=components)

  @classmethod
  def FromStatEntry(cls, stat_entry):
    result = cls.FromPathSpec(stat_entry.pathspec)
    result.directory = stat.S_ISDIR(int(stat_entry.st_mode))
    result.stat_entry = stat_entry
    return result

  @property
  def root(self):
    return not self.components

  @property
  def basename(self):
    if self.root:
      return ""
    else:
      return self.components[-1]

  def GetPathID(self):
    return PathID.FromComponents(self.components)

  def GetParentPathID(self):
    return PathID.FromComponents(self.components[:-1])

  def GetParent(self):
    """Constructs a path info corresponding to the parent of current path.

    The root path (represented by an empty list of components, corresponds to
    `/` on Unix-like systems) does not have a parent.

    Returns:
      Instance of `rdf_objects.PathInfo` or `None` if parent does not exist.
    """
    if self.root:
      return None

    return PathInfo(
        components=self.components[:-1],
        path_type=self.path_type,
        directory=True)

  def GetAncestors(self):
    """Yields all ancestors of a path.

    The ancestors are returned in order from closest to the farthest one.

    Yields:
      Instances of `rdf_objects.PathInfo`.
    """
    current = self
    while True:
      current = current.GetParent()
      if current is None:
        return
      yield current

  def UpdateFrom(self, src):
    """Merge path info records.

    Merges src into self.
    Args:
      src: An rdfvalues.objects.PathInfo record, will be merged into self.

    Raises:
      ValueError: If src does not represent the same path.
    """
    if not isinstance(src, PathInfo):
      raise TypeError("expected `%s` but got `%s`" % (PathInfo, type(src)))
    if self.path_type != src.path_type:
      raise ValueError(
          "src [%s] does not represent the same path type as self [%s]" %
          (src.path_type, self.path_type))
    if self.components != src.components:
      raise ValueError(
          "src [%s] does not represent the same path as self [%s]" %
          (src.components, self.components))

    if src.HasField("stat_entry"):
      self.stat_entry = src.stat_entry

    if src.last_stat_entry_timestamp is not None:
      if self.last_stat_entry_timestamp is not None:
        self.last_stat_entry_timestamp = max(self.last_stat_entry_timestamp,
                                             src.last_stat_entry_timestamp)
      else:
        self.last_stat_entry_timestamp = src.last_stat_entry_timestamp

    self.directory = self.directory or src.directory


def _ValidatePathComponent(component):
  if not isinstance(component, Text):
    raise TypeError("Non-unicode path component")
  if not component:
    raise ValueError("Empty path component")
  if component == "." or component == "..":
    raise ValueError("Incorrect path component: '%s'" % component)


def _ValidatePathComponents(components):
  try:
    for component in components:
      _ValidatePathComponent(component)
  except ValueError as error:
    message = "Incorrect path component list '%s': %s"
    raise ValueError(message % (components, error))


# TODO(hanuszczak): Instead of these two functions for categorized paths we
# should create an RDF value that wraps a string and provides these two as
# methods.


def ParseCategorizedPath(path):
  """Parses a categorized path string into type and list of components."""
  components = tuple(component for component in path.split("/") if component)
  if components[0:2] == ("fs", "os"):
    return PathInfo.PathType.OS, components[2:]
  elif components[0:2] == ("fs", "tsk"):
    return PathInfo.PathType.TSK, components[2:]
  elif components[0:1] == ("registry",):
    return PathInfo.PathType.REGISTRY, components[1:]
  elif components[0:1] == ("temp",):
    return PathInfo.PathType.TEMP, components[1:]
  elif components[0:2] == ("fs", "ntfs"):
    return PathInfo.PathType.NTFS, components[2:]
  else:
    raise ValueError(
        "Path {!r} does not start with a VFS prefix like /fs/os/".format(path))


def ToCategorizedPath(path_type, components):
  """Translates a path type and a list of components to a categorized path."""
  try:
    prefix = {
        PathInfo.PathType.OS: ("fs", "os"),
        PathInfo.PathType.TSK: ("fs", "tsk"),
        PathInfo.PathType.REGISTRY: ("registry",),
        PathInfo.PathType.TEMP: ("temp",),
        PathInfo.PathType.NTFS: ("fs", "ntfs"),
    }[path_type]
  except KeyError:
    raise ValueError("Unknown path type: `%s`" % path_type)

  return "/".join(itertools.chain(prefix, components))


class ClientReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientReference
  rdf_deps = []


class HuntReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.HuntReference
  rdf_deps = []


class CronJobReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.CronJobReference
  rdf_deps = []


class FlowReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.FlowReference
  rdf_deps = []


class VfsFileReference(rdf_structs.RDFProtoStruct):
  """Object reference pointing to a VFS file."""

  protobuf = objects_pb2.VfsFileReference
  rdf_deps = []

  def ToPath(self):
    """Converts a reference into a VFS file path."""

    if self.path_type == PathInfo.PathType.OS:
      return os.path.join("fs", "os", *self.path_components)
    elif self.path_type == PathInfo.PathType.TSK:
      return os.path.join("fs", "tsk", *self.path_components)
    elif self.path_type == PathInfo.PathType.REGISTRY:
      return os.path.join("registry", *self.path_components)
    elif self.path_type == PathInfo.PathType.TEMP:
      return os.path.join("temp", *self.path_components)
    elif self.path_type == PathInfo.PathType.NTFS:
      return os.path.join("fs", "ntfs", *self.path_components)

    raise ValueError("Unsupported path type: %s" % self.path_type)


class ApprovalRequestReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalRequestReference
  rdf_deps = []


class ObjectReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ObjectReference
  rdf_deps = [
      ClientReference,
      HuntReference,
      CronJobReference,
      FlowReference,
      VfsFileReference,
      ApprovalRequestReference,
  ]


class UserNotification(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.UserNotification
  rdf_deps = [
      rdfvalue.RDFDatetime,
      ObjectReference,
  ]


class MessageHandlerRequest(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.MessageHandlerRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdf_protodict.EmbeddedRDFValue,
  ]


class SHA256HashID(HashID):
  """SHA-256 based hash id."""

  hash_id_length = 32

  @classmethod
  def FromData(cls, data):
    h = hashlib.sha256(data).digest()
    return SHA256HashID(h)


class BlobID(HashID):
  """Blob identificator."""

  hash_id_length = 32

  @classmethod
  def FromBlobData(cls, data):
    h = hashlib.sha256(data).digest()
    return BlobID(h)


class ClientPathID(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientPathID
  rdf_deps = [
      PathID,
  ]


class BlobReference(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.BlobReference
  rdf_deps = [
      BlobID,
  ]


class BlobReferences(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.BlobReferences
  rdf_deps = [
      BlobReference,
  ]


class SerializedValueOfUnrecognizedType(rdf_structs.RDFProtoStruct):
  """Class used to represent objects that can't be deserialized properly.

  When deserializing certain objects stored in the database (FlowResults, for
  example), we don't want to fail hard if for some reason the type of the value
  is unknown and can no longer be found in the system. When this happens,
  SerializedValueOfUnrecognizedType is used as a stub. This way, affected
  API calls won't simply fail and raise, but will rather return all the results
  they can and the user will be able to fetch the data, albeit in serialized
  form.
  """
  protobuf = objects_pb2.SerializedValueOfUnrecognizedType
  rdf_deps = []


class APIAuditEntry(rdf_structs.RDFProtoStruct):
  """Audit entry for API calls, persistend in the relational database."""
  protobuf = objects_pb2.APIAuditEntry
  rdf_deps = [rdfvalue.RDFDatetime]

  # Use dictionaries instead of if-statements to look up mappings to increase
  # branch coverage during testing. This way, all constants are accessed,
  # without requiring a test for every single one.
  _HTTP_STATUS_TO_CODE = {
      200: objects_pb2.APIAuditEntry.OK,
      403: objects_pb2.APIAuditEntry.FORBIDDEN,
      404: objects_pb2.APIAuditEntry.NOT_FOUND,
      500: objects_pb2.APIAuditEntry.ERROR,
      501: objects_pb2.APIAuditEntry.NOT_IMPLEMENTED,
  }

  @classmethod
  def FromHttpRequestResponse(cls, request, response):
    response_code = APIAuditEntry._HTTP_STATUS_TO_CODE.get(
        response.status_code, objects_pb2.APIAuditEntry.ERROR)

    return cls(
        http_request_path=request.full_path,  # include query string
        router_method_name=response.headers.get("X-API-Method", ""),
        username=request.user,
        response_code=response_code,
    )


class SignedBinaryID(rdf_structs.RDFProtoStruct):
  protobuf = objects_pb2.SignedBinaryID
