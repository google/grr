#!/usr/bin/env python
"""Helper class to migrate data."""

from grr.lib import utils
from grr.lib.rdfvalues import objects as rdf_objects
from grr.server import data_store


def ConvertVFSGRRClient(client):
  """Converts a VFSGRRClient object to and rdfvalues.objects.Client objects."""

  result = rdf_objects.Client(client_id=client.urn.Basename())

  s = client.Schema
  result.last_boot_time = client.Get(s.LAST_BOOT_TIME)
  result.filesystems = client.Get(s.FILESYSTEM)
  result.client_info = client.Get(s.CLIENT_INFO)
  result.hostname = client.Get(s.HOSTNAME)
  result.fqdn = client.Get(s.FQDN)
  result.system = client.Get(s.SYSTEM)
  result.os_release = client.Get(s.OS_RELEASE)
  result.os_version = client.Get(s.OS_VERSION)
  result.arch = client.Get(s.ARCH)
  result.install_time = client.Get(s.INSTALL_DATE)
  result.knowledge_base = client.Get(s.KNOWLEDGE_BASE)

  conf = client.Get(s.GRR_CONFIGURATION)
  for key in conf or []:
    result.grr_configuration.Append(key=key, value=utils.SmartStr(conf[key]))

  lib = client.Get(s.LIBRARY_VERSIONS)
  for key in lib or []:
    result.library_versions.Append(key=key, value=utils.SmartStr(lib[key]))

  result.kernel = client.Get(s.KERNEL)
  result.volumes = client.Get(s.VOLUMES)
  result.interfaces = client.Get(s.INTERFACES)
  result.hardware_info = client.Get(s.HARDWARE_INFO)
  result.memory_size = client.Get(s.MEMORY_SIZE)
  result.cloud_instance = client.Get(s.CLOUD_INSTANCE)

  return result


class DataMigrationHelper(object):
  """Helper class to migrate data."""

  def __init__(self):
    if not data_store.RelationalDBWriteEnabled():
      raise ValueError("No relational database available.")

  def Migrate(self):
    """This migrates data from the legacy storage to the relational database."""

    # TODO(amoser): This doesn't do anything yet.
    pass
