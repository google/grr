#!/usr/bin/env python
"""Client fixture-related test classes."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.server import aff4
from grr.server import artifact
from grr.server import client_fixture
from grr.server import client_index
from grr.server.aff4_objects import aff4_grr
from grr.test_lib import test_lib

# Make the fixture appear to be 1 week old.
FIXTURE_TIME = test_lib.FIXED_TIME


class ClientFixture(object):
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
    self.age = age or FIXTURE_TIME.AsSecondsFromEpoch()
    self.client_id = rdf_client.ClientURN(client_id)
    self.args["client_id"] = self.client_id.Basename()
    self.args["age"] = self.age
    self.CreateClientObject(fixture or client_fixture.VFS)

  def CreateClientObject(self, vfs_fixture):
    """Make a new client object."""

    # First remove the old fixture just in case its still there.
    aff4.FACTORY.Delete(self.client_id, token=self.token)

    # Create the fixture at a fixed time.
    with test_lib.FakeTime(self.age):
      for path, (aff4_type, attributes) in vfs_fixture:
        path %= self.args

        aff4_object = aff4.FACTORY.Create(
            self.client_id.Add(path), aff4_type, mode="rw", token=self.token)

        for attribute_name, value in attributes.items():
          attribute = aff4.Attribute.PREDICATES[attribute_name]
          if isinstance(value, (str, unicode)):
            # Interpolate the value
            value %= self.args

          # Is this supposed to be an RDFValue array?
          if aff4.issubclass(attribute.attribute_type,
                             rdf_protodict.RDFValueArray):
            rdfvalue_object = attribute()
            for item in value:
              new_object = rdfvalue_object.rdf_type.FromTextFormat(
                  utils.SmartStr(item))
              rdfvalue_object.Append(new_object)

          # It is a text serialized protobuf.
          elif aff4.issubclass(attribute.attribute_type,
                               rdf_structs.RDFProtoStruct):
            # Use the alternate constructor - we always write protobufs in
            # textual form:
            rdfvalue_object = attribute.attribute_type.FromTextFormat(
                utils.SmartStr(value))

          elif aff4.issubclass(attribute.attribute_type, rdfvalue.RDFInteger):
            rdfvalue_object = attribute(int(value))
          else:
            rdfvalue_object = attribute(value)

          # If we don't already have a pathspec, try and get one from the stat.
          if aff4_object.Get(aff4_object.Schema.PATHSPEC) is None:
            # If the attribute was a stat, it has a pathspec nested in it.
            # We should add that pathspec as an attribute.
            if attribute.attribute_type == rdf_client.StatEntry:
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
            # For AFF4MemoryStreams we need to call Write() instead of
            # directly setting the contents..
            aff4_object.Write(rdfvalue_object)
          else:
            aff4_object.AddAttribute(attribute, rdfvalue_object)

        # Populate the KB from the client attributes.
        if aff4_type == aff4_grr.VFSGRRClient:
          kb = rdf_client.KnowledgeBase()
          artifact.SetCoreGRRKnowledgeBaseValues(kb, aff4_object)
          aff4_object.Set(aff4_object.Schema.KNOWLEDGE_BASE, kb)

        # Make sure we do not actually close the object here - we only want to
        # sync back its attributes, not run any finalization code.
        aff4_object.Flush()
        if aff4_type == aff4_grr.VFSGRRClient:
          index = client_index.CreateClientIndex(token=self.token)
          index.AddClient(aff4_object)
