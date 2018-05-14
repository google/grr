#!/usr/bin/env python
"""Top level datastore objects.

This package contains the rdfvalue wrappers around the top level datastore
objects defined by objects.proto.
"""
import hashlib
import re

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import structs
from grr_response_proto import objects_pb2


class ClientLabel(structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientLabel


class StringMapEntry(structs.RDFProtoStruct):
  protobuf = objects_pb2.StringMapEntry


class ClientSnapshot(structs.RDFProtoStruct):
  """The client object.

  Attributes:

    timestamp: An rdfvalue.Datetime indicating when this client snapshot was
      saved to the database. Should be present in every client object loaded
      from the database, but is not serialized with the rdfvalue fields.
  """
  protobuf = objects_pb2.ClientSnapshot

  rdf_deps = [
      StringMapEntry,
      cloud.CloudInstance,
      rdf_client.Filesystem,
      rdf_client.HardwareInfo,
      rdf_client.Interface,
      rdf_client.KnowledgeBase,
      rdf_client.StartupInfo,
      rdf_client.Volume,
      rdfvalue.ByteSize,
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, skip_verification=False, *args, **kwargs):
    super(ClientSnapshot, self).__init__(*args, **kwargs)
    if not skip_verification:
      self.ValidateClientId()
    self.timestamp = None

  def ValidateClientId(self):
    if not self.client_id:
      raise ValueError(
          "Trying to instantiate a Client object without client id.")
    if not re.match(r"C\.[0-9a-f]{16}", self.client_id):
      raise ValueError("Client id invalid: %s" % self.client_id)

  @classmethod
  def FromSerializedString(cls, value, age=None):
    res = cls(skip_verification=True)
    res.ParseFromString(value)
    if age:
      res.age = age
    res.ValidateClientId()
    return res

  def Uname(self):
    """OS summary string."""
    return "%s-%s-%s" % (self.knowledge_base.os, self.os_release,
                         self.os_version)

  def GetMacAddresses(self):
    """MAC addresses from all interfaces."""
    result = set()
    for interface in self.interfaces:
      if (interface.mac_address and
          interface.mac_address != "\x00" * len(interface.mac_address)):
        result.add(interface.mac_address.human_readable_address)
    return sorted(result)

  def GetIPAddresses(self):
    """IP addresses from all interfaces."""
    result = []
    filtered_ips = ["127.0.0.1", "::1", "fe80::1"]

    for interface in self.interfaces:
      for address in interface.addresses:
        if address.human_readable_address not in filtered_ips:
          result.append(address.human_readable_address)
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


class ClientMetadata(structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientMetadata

  rdf_deps = [
      rdf_client.NetworkAddress,
      rdf_crypto.RDFX509Cert,
      rdfvalue.RDFDatetime,
  ]


class ClientFullInfo(structs.RDFProtoStruct):
  """ClientFullInfo object."""
  protobuf = objects_pb2.ClientFullInfo

  rdf_deps = [
      ClientMetadata,
      ClientSnapshot,
      ClientLabel,
      rdf_client.StartupInfo,
  ]

  def GetLabelsNames(self, owner=None):
    return set(l.name for l in self.labels if not owner or l.owner == owner)


class GRRUser(structs.RDFProtoStruct):
  protobuf = objects_pb2.GRRUser
  rdf_deps = [
      rdf_crypto.Password,
  ]


class ApprovalGrant(structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalGrant
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApprovalRequest(structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalRequest
  rdf_deps = [
      rdfvalue.RDFDatetime,
      ApprovalGrant,
  ]

  @property
  def is_expired(self):
    return self.expiration_time < rdfvalue.RDFDatetime.Now()


class PathID(object):
  """An unique path identifier corresponding to some path.

  Args:
    components: A list of path components to construct the identifier from.
  """

  def __init__(self, components):
    # TODO(hanuszczak): `SmartStr` is terrible, lets not do that.
    components = map(utils.SmartStr, components)

    if components:
      # We need a string to hash, based on components. If we simply concatenated
      # them, or used a separator that could appear in some component, odd data
      # could force a hash collision. So we explicitly include the lengths of
      # the components.
      string = "{lengths}:{path}".format(
          lengths=",".join(str(len(component)) for component in components),
          path="/".join(components))
      self._bytes = hashlib.sha256(string).digest()
    else:
      # For an empty list of components (representing `/`, i.e. the root path),
      # we use special value: zero represented as a 256-bit number.
      self._bytes = b"\0" * 32

  def AsBytes(self):
    return self._bytes

  def __eq__(self, other):
    return self.AsBytes() == other.AsBytes()

  def __hash__(self):
    return hash(self.AsBytes())

  def __repr__(self):
    return "PathID({})".format(repr(self.AsBytes().encode("hex")))


class PathInfo(structs.RDFProtoStruct):
  """Basic metadata about a path which has been observed on a client."""
  protobuf = objects_pb2.PathInfo
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, *args, **kwargs):
    super(PathInfo, self).__init__(*args, **kwargs)
    if self.root and not self.directory:
      raise AssertionError("`PathInfo` is both root and not a directory")

  @classmethod
  def OS(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.OS, **kwargs)

  @classmethod
  def TSK(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.TSK, **kwargs)

  @classmethod
  def Registry(cls, *args, **kwargs):
    return cls(*args, path_type=cls.PathType.REGISTRY, **kwargs)

  @property
  def root(self):
    return not self.components

  def GetPathID(self):
    return PathID(self.components)

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
      raise ValueError("src [%s] does not represent the same path as self [%s]"
                       % (src.components, self.components))

    self.last_path_history_timestamp = max(self.last_path_history_timestamp,
                                           src.last_path_history_timestamp)
    self.directory |= src.directory


class ClientReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientReference
  rdf_deps = []


class HuntReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.HuntReference
  rdf_deps = []

  def ToHuntURN(self):
    return rdfvalue.RDFURN("aff4:/hunts").Add(self.hunt_id)


class CronJobReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.CronJobReference
  rdf_deps = []


class FlowReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.FlowReference
  rdf_deps = [
      rdf_client.ClientURN,
  ]

  def ToFlowURN(self):
    return self.client_id.Add("flows").Add(self.flow_id)


class VfsFileReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.VfsFileReference
  rdf_deps = []


class ApprovalRequestReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.ApprovalRequestReference
  rdf_deps = []


class ObjectReference(structs.RDFProtoStruct):
  protobuf = objects_pb2.ObjectReference
  rdf_deps = [
      ClientReference,
      HuntReference,
      CronJobReference,
      FlowReference,
      VfsFileReference,
      ApprovalRequestReference,
  ]


class UserNotification(structs.RDFProtoStruct):
  protobuf = objects_pb2.UserNotification
  rdf_deps = [
      rdfvalue.RDFDatetime,
      ObjectReference,
  ]
