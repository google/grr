#!/usr/bin/env python
"""These are standard aff4 objects."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.builtins import range

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow


class VFSDirectory(aff4.AFF4Volume):
  """This represents a directory from the client."""

  # We contain other objects within the tree.
  _behaviours = frozenset(["Container"])

  def Update(self, attribute=None):
    """Refresh an old attribute.

    Note that refreshing the attribute is asynchronous. It does not change
    anything about the current object - you need to reopen the same URN some
    time later to get fresh data.

    Attributes: CONTAINS - Refresh the content of the directory listing.
    Args:
       attribute: An attribute object as listed above.

    Returns:
       The Flow ID that is pending

    Raises:
       IOError: If there has been an error starting the flow.
    """
    # client id is the first path element
    client_id = self.urn.Split()[0]

    if attribute == "CONTAINS":
      # Get the pathspec for this object
      flow_id = flow.StartAFF4Flow(
          client_id=client_id,
          # Dependency loop: aff4_objects/aff4_grr.py depends on
          # aff4_objects/standard.py that depends on flows/general/filesystem.py
          # that eventually depends on aff4_objects/aff4_grr.py
          # flow_name=filesystem.ListDirectory.__name__,
          flow_name="ListDirectory",
          pathspec=self.real_pathspec,
          notify_to_user=False,
          token=self.token)

      return flow_id

  class SchemaCls(aff4.AFF4Volume.SchemaCls):
    """Attributes specific to VFSDirectory."""
    STAT = aff4.Attribute("aff4:stat", rdf_client_fs.StatEntry,
                          "A StatEntry describing this file.", "stat")

    PATHSPEC = aff4.Attribute(
        "aff4:pathspec", rdf_paths.PathSpec,
        "The pathspec used to retrieve this object from the client.",
        "pathspec")


class HashList(rdfvalue.RDFBytes):
  """A list of hashes."""

  HASH_SIZE = 32

  def __len__(self):
    return len(self._value) // self.HASH_SIZE

  def __iter__(self):
    for i in range(len(self)):
      yield self[i]

  def __getitem__(self, idx):
    return rdfvalue.HashDigest(
        self._value[idx * self.HASH_SIZE:(idx + 1) * self.HASH_SIZE])


class LabelSet(aff4.AFF4Object):
  """An aff4 object which manages a set of labels.

  This object has no actual attributes, it simply manages the set.
  """

  # We expect the set to be quite small, so we simply store it as a collection
  # attributes of the form "index:label_<label>" all unversioned (ts = 0).

  # Location of the default set of labels, used to keep tract of active labels
  # for clients.
  CLIENT_LABELS_URN = "aff4:/index/labels/client_set"

  def __init__(self, urn, **kwargs):
    super(LabelSet, self).__init__(urn=self.CLIENT_LABELS_URN, **kwargs)

    self.to_set = set()
    self.to_delete = set()

  def Flush(self):
    """Flush the data to the index."""
    super(LabelSet, self).Flush()

    self.to_delete = self.to_delete.difference(self.to_set)

    with data_store.DB.GetMutationPool() as mutation_pool:
      mutation_pool.LabelUpdateLabels(
          self.urn, self.to_set, to_delete=self.to_delete)
    self.to_set = set()
    self.to_delete = set()

  def Close(self):
    self.Flush()
    super(LabelSet, self).Close()

  def Add(self, label):
    self.to_set.add(label)

  def Remove(self, label):
    self.to_delete.add(label)

  def ListLabels(self):
    # Flush, so that any pending changes are visible.
    if self.to_set or self.to_delete:
      self.Flush()
    return data_store.DB.LabelFetchAll(self.urn)
