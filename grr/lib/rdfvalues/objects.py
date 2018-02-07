#!/usr/bin/env python
"""Top level datastore objects.

This package contains the rdfvalue wrappers around the top level datastore
objects defined by objects.proto.
"""
import re

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import structs
from grr_response_proto import objects_pb2


class ClientLabel(structs.RDFProtoStruct):
  protobuf = objects_pb2.ClientLabel


class StringMapEntry(structs.RDFProtoStruct):
  protobuf = objects_pb2.StringMapEntry


class Client(structs.RDFProtoStruct):
  """The client object.

  Attributes:

    timestamp: An rdfvalue.Datetime indicating when this client snapshot was
      saved to the database. Should be present in every client object loaded
      from the database, but is not serialized with the rdfvalue fields.
  """
  protobuf = objects_pb2.Client

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
    super(Client, self).__init__(*args, **kwargs)
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
    summary.timestamp = self.age
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


class GRRUser(structs.RDFProtoStruct):
  protobuf = objects_pb2.GRRUser
  rdf_deps = [
      rdf_crypto.Password,
  ]
