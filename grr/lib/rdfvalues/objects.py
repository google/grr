#!/usr/bin/env python
"""Top level datastore objects.

This package contains the rdfvalue wrappers around the top level datastore
objects defined by objects.proto.
"""
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import structs
from grr.proto import objects_pb2


class Client(structs.RDFProtoStruct):
  """The client object.

  Attributes:

    timestamp: An rdfvalue.Datetime indicating when this client snapshot was
      saved to the database. Should be present in every client object loaded
      from the database, but is not serialized with the rdfvalue fields.
  """
  protobuf = objects_pb2.Client

  rdf_deps = [
      rdf_client.Filesystem,
      rdfvalue.RDFDatetime,
      rdf_client.ClientInformation,
      rdf_client.VersionString,
      rdf_client.KnowledgeBase,
      protodict.Dict,
      rdf_client.Volume,
      rdf_client.Interface,
      rdf_client.HardwareInfo,
      rdfvalue.ByteSize,
      cloud.CloudInstance,
  ]

  def __init__(self, *args, **kwargs):
    super(Client, self).__init__(*args, **kwargs)
    self.timestamp = None

  def Uname(self):
    """OS summary string."""
    return "%s-%s-%s" % (self.system, self.os_release, self.os_version)

  def GetMacAddresses(self):
    """MAC addresses from all interfaces."""
    result = []
    for interface in self.interfaces:
      if (interface.mac_address and
          interface.mac_address != "\x00" * len(interface.mac_address)):
        result.append(interface.mac_address.human_readable_address)
        return result

  def GetIPAddresses(self):
    """IP addresses from all interfaces."""
    result = []
    filtered_ips = ["127.0.0.1", "::1", "fe80::1"]

    for interface in self.interfaces:
      for address in interface.addresses:
        if address.human_readable_address not in filtered_ips:
          result.append(address.human_readable_address)
    return result

  def GetSummary(self):
    """Gets a client summary object.

    Returns:
      rdf_client.ClientSummary
    Raises:
      ValueError: on bad cloud type
    """
    summary = rdf_client.ClientSummary()
    summary.system_info.node = self.hostname
    summary.system_info.system = self.system
    summary.system_info.release = self.os_release
    summary.system_info.version = str(self.os_version or "")
    summary.system_info.kernel = self.kernel
    summary.system_info.fqdn = self.fqdn
    summary.system_info.machine = self.arch
    summary.system_info.install_date = self.install_time
    kb = self.knowledge_base
    if kb:
      summary.users = kb.users
      summary.interfaces = self.interfaces
      summary.client_info = self.client_info
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
      rdf_client.ClientCrash,
      rdf_client.NetworkAddress,
      rdf_crypto.RDFX509Cert,
      rdfvalue.RDFDatetime,
  ]
