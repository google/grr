#!/usr/bin/env python
"""Client fixture-related test classes."""

import binascii

from grr_response_core import config
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_server import client_fixture
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects

SERIALIZED_CLIENT = ("6a3f3a1253616d706c652042494f532056656e646f72420d56657273"
                     "696f6e20312e323376121a53616d706c652053797374656d204d616e"
                     "75666163747572657230fbac8db38cb6a8023a0d220757696e646f77"
                     "73280630011a01372208362e312e3736303082012d0a2b2207756e6b"
                     "6e6f776e0a0b475252204d6f6e69746f721001320f636c69656e742d"
                     "6c6162656c2d32331800")


class ClientFixture(object):
  """A tool to create a client fixture.

  This will populate the object tree in the data store with a mock client
  filesystem, including various objects. This allows us to test various
  end-to-end aspects (e.g. GUI).
  """

  def __init__(self, client_id):
    """Constructor.

    Args:
      client_id: The unique id for the new client.
    """

    self.client_id = client_id
    self.args = {"client_id": self.client_id}
    self.CreateClientObject(client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""

    # Constructing a client snapshot from the legacy fixture is hard, we are
    # using a serialized string instead.
    data_store.REL_DB.WriteClientMetadata(
        self.client_id, fleetspeak_enabled=False)

    snapshot = rdf_objects.ClientSnapshot.FromSerializedBytes(
        binascii.unhexlify(SERIALIZED_CLIENT))
    snapshot.client_id = self.client_id
    snapshot.knowledge_base.fqdn = "Host%s" % self.client_id
    # Client version number may affect flows behavior so it's important
    # to keep it current in order for flows tests to test the most
    # recent logic.
    snapshot.startup_info.client_info.client_version = config.CONFIG[
        "Source.version_numeric"]

    data_store.REL_DB.WriteClientSnapshot(snapshot)
    client_index.ClientIndex().AddClient(snapshot)

    for path, (typ, attributes) in vfs_fixture:
      path %= self.args

      path_info = None

      components = [component for component in path.split("/") if component]
      if (len(components) > 1 and components[0] == "fs" and
          components[1] in ["os", "tsk", "ntfs"]):
        path_info = rdf_objects.PathInfo()
        if components[1] == "os":
          path_info.path_type = rdf_objects.PathInfo.PathType.OS
        elif components[1] == "ntfs":
          path_info.path_type = rdf_objects.PathInfo.PathType.NTFS
        else:
          path_info.path_type = rdf_objects.PathInfo.PathType.TSK
        path_info.components = components[2:]
        if typ == "File":
          path_info.directory = False
        elif typ == "Directory":
          path_info.directory = True
        else:
          raise ValueError("Incorrect object type: %s" % typ)

      for attribute_name in attributes:
        if attribute_name not in ["stat", "content"]:
          raise ValueError("Unknown attribute: " + attribute_name)

      stat = attributes.get("stat", None)
      if stat:
        stat_entry = rdf_client_fs.StatEntry.FromTextFormat(stat % self.args)
        if stat_entry.pathspec.pathtype != "UNSET":
          path_info = rdf_objects.PathInfo.FromStatEntry(stat_entry)

      content = attributes.get("content", None)
      if content:
        blob_id = rdf_objects.BlobID.FromBlobData(content)
        data_store.BLOBS.WriteBlobs({blob_id: content})
        blob_ref = rdf_objects.BlobReference(
            offset=0, size=len(content), blob_id=blob_id)
        hash_id = file_store.AddFileWithUnknownHash(
            db.ClientPath.FromPathInfo(self.client_id, path_info), [blob_ref])
        path_info.hash_entry.num_bytes = len(content)
        path_info.hash_entry.sha256 = hash_id.AsBytes()

      if path_info is not None:
        data_store.REL_DB.WritePathInfos(
            client_id=self.client_id, path_infos=[path_info])
