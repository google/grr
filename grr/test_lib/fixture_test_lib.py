#!/usr/bin/env python
"""Client fixture-related test classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems
from typing import Text

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_server import aff4
from grr_response_server import artifact
from grr_response_server import client_fixture
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import standard as aff4_standard
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib

# Make the fixture appear to be 1 week old.
FIXTURE_TIME = test_lib.FIXED_TIME

SERIALIZED_CLIENT = ("6a3f3a1253616d706c652042494f532056656e646f72420d56657273"
                     "696f6e20312e323376121a53616d706c652053797374656d204d616e"
                     "75666163747572657230fbac8db38cb6a8023a0d220757696e646f77"
                     "73280630011a01372208362e312e3736303082012d0a2b2207756e6b"
                     "6e6f776e0a0b475252204d6f6e69746f721001320f636c69656e742d"
                     "6c6162656c2d32331800")


class LegacyClientFixture(object):
  """A tool to create a client fixture.

  This will populate the AFF4 object tree in the data store with a mock client
  filesystem, including various objects. This allows us to test various
  end-to-end aspects (e.g. GUI).
  """

  def __init__(self, client_id, token=None, fixture=None, age=None, **kwargs):
    """Constructor.

    Args:
      client_id: The unique id for the new client.
      token: An instance of access_control.ACLToken security token.
      fixture: An optional fixture to install. If not provided we use
        client_fixture.VFS.
      age: Create the fixture at this timestamp. If None we use FIXTURE_TIME.
      **kwargs: Any other parameters which need to be interpolated by the
        fixture.
    """
    self.args = kwargs
    self.token = token
    self.age = age or FIXTURE_TIME.AsSecondsSinceEpoch()
    self.client_urn = rdf_client.ClientURN(client_id)
    self.client_id = self.client_urn.Basename()
    self.args["client_id"] = self.client_id
    self.args["age"] = self.age
    self.CreateClientObject(fixture or client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""

    # First remove the old fixture just in case its still there.
    aff4.FACTORY.Delete(self.client_id, token=self.token)

    # Create the fixture at a fixed time.
    with test_lib.FakeTime(self.age):

      if data_store.RelationalDBWriteEnabled():
        # Constructing a client snapshot from the aff4 fixture is only possible
        # using aff4. Using a serialized string instead.
        data_store.REL_DB.WriteClientMetadata(
            self.client_id, fleetspeak_enabled=False)

        snapshot = rdf_objects.ClientSnapshot.FromSerializedString(
            SERIALIZED_CLIENT.decode("hex"))
        snapshot.client_id = self.client_id
        snapshot.knowledge_base.fqdn = "Host%s" % self.client_id

        data_store.REL_DB.WriteClientSnapshot(snapshot)
        client_index.ClientIndex().AddClient(snapshot)

      for path, (aff4_type, attributes) in vfs_fixture:
        path %= self.args

        if data_store.AFF4Enabled():
          aff4_object = aff4.FACTORY.Create(
              self.client_urn.Add(path), aff4_type, mode="rw", token=self.token)

        path_info = None

        if data_store.RelationalDBWriteEnabled():
          components = [component for component in path.split("/") if component]
          if (len(components) > 1 and components[0] == "fs" and
              components[1] in ["os", "tsk"]):
            path_info = rdf_objects.PathInfo()
            if components[1] == "os":
              path_info.path_type = rdf_objects.PathInfo.PathType.OS
            else:
              path_info.path_type = rdf_objects.PathInfo.PathType.TSK
            path_info.components = components[2:]
            if aff4_type in [aff4_grr.VFSFile, aff4_grr.VFSMemoryFile]:
              path_info.directory = False
            elif aff4_type == aff4_standard.VFSDirectory:
              path_info.directory = True
            else:
              raise ValueError("Incorrect AFF4 type: %s" % aff4_type)

        for attribute_name, value in iteritems(attributes):
          attribute = aff4.Attribute.PREDICATES[attribute_name]
          if isinstance(value, (bytes, Text)):
            # Interpolate the value
            value %= self.args

          # Is this supposed to be an RDFValue array?
          if issubclass(attribute.attribute_type, rdf_protodict.RDFValueArray):
            rdfvalue_object = attribute()
            for item in value:
              new_object = rdfvalue_object.rdf_type.FromTextFormat(
                  utils.SmartStr(item))
              rdfvalue_object.Append(new_object)

          # It is a text serialized protobuf.
          elif issubclass(attribute.attribute_type, rdf_structs.RDFProtoStruct):
            # Use the alternate constructor - we always write protobufs in
            # textual form:
            rdfvalue_object = attribute.attribute_type.FromTextFormat(
                utils.SmartStr(value))

          elif issubclass(attribute.attribute_type, rdfvalue.RDFInteger):
            rdfvalue_object = attribute(int(value))
          else:
            rdfvalue_object = attribute(value)

          if data_store.AFF4Enabled():
            # If we don't already have a pathspec, try and get one from the
            # stat.
            if aff4_object.Get(aff4_object.Schema.PATHSPEC) is None:
              # If the attribute was a stat, it has a pathspec nested in it.
              # We should add that pathspec as an attribute.
              if attribute.attribute_type == rdf_client_fs.StatEntry:
                stat_object = attribute.attribute_type.FromTextFormat(
                    utils.SmartStr(value))
                if stat_object.pathspec:
                  pathspec_attribute = aff4.Attribute(
                      "aff4:pathspec", rdf_paths.PathSpec,
                      "The pathspec used to retrieve "
                      "this object from the client.", "pathspec")
                  aff4_object.AddAttribute(pathspec_attribute,
                                           stat_object.pathspec)

          if attribute in ["aff4:content", "aff4:content"]:
            content = rdfvalue_object.AsBytes()

            if data_store.AFF4Enabled():
              # For AFF4MemoryStreams we need to call Write() instead of
              # directly setting the contents..
              aff4_object.Write(content)

            if path_info is not None:
              blob_id = rdf_objects.BlobID.FromBlobData(content)
              data_store.BLOBS.WriteBlobs({blob_id: content})
              blob_ref = rdf_objects.BlobReference(
                  offset=0, size=len(content), blob_id=blob_id)
              hash_id = file_store.AddFileWithUnknownHash(
                  db.ClientPath.FromPathInfo(self.client_id, path_info),
                  [blob_ref])
              path_info.hash_entry.num_bytes = len(content)
              path_info.hash_entry.sha256 = hash_id.AsBytes()
          elif data_store.AFF4Enabled():
            aff4_object.AddAttribute(attribute, rdfvalue_object)

          if (isinstance(rdfvalue_object, rdf_client_fs.StatEntry) and
              rdfvalue_object.pathspec.pathtype != "UNSET"):
            if data_store.RelationalDBWriteEnabled():
              path_info = rdf_objects.PathInfo.FromStatEntry(rdfvalue_object)
              data_store.REL_DB.WritePathInfos(self.client_id, [path_info])

        # Populate the KB from the client attributes.
        if aff4_type == aff4_grr.VFSGRRClient:
          if data_store.AFF4Enabled():
            kb = rdf_client.KnowledgeBase()
            artifact.SetCoreGRRKnowledgeBaseValues(kb, aff4_object)
            aff4_object.Set(aff4_object.Schema.KNOWLEDGE_BASE, kb)

            aff4_object.Flush()

            index = client_index.CreateClientIndex(token=self.token)
            index.AddClient(aff4_object)

        if path_info is not None:
          data_store.REL_DB.WritePathInfos(
              client_id=self.client_id, path_infos=[path_info])

        if data_store.AFF4Enabled():
          aff4_object.Flush()


def ClientFixture(client_id, token=None, age=None):
  """Creates a client fixture with a predefined VFS tree."""

  if hasattr(client_id, "Basename"):
    client_id = client_id.Basename()

  # TODO(amoser): This method should be split into two.
  LegacyClientFixture(client_id, age=age, token=token)
