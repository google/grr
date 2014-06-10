#!/usr/bin/env python
"""Base classes for artifacts."""

import logging

from grr.lib import aff4
from grr.lib import artifact_lib
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.proto import flows_pb2


class AFF4ResultWriter(object):
  """A wrapper class to allow writing objects to the AFF4 space."""

  def __init__(self, path, aff4_type, aff4_attribute, mode):
    self.path = path
    self.aff4_type = aff4_type
    self.aff4_attribute = aff4_attribute
    self.mode = mode


def GetArtifactKnowledgeBase(client_obj, allow_uninitialized=False):
  """This generates an artifact knowledge base from a GRR client.

  Args:
    client_obj: A GRRClient object which is opened for reading.
    allow_uninitialized: If True we accept an uninitialized knowledge_base.

  Returns:
    A KnowledgeBase semantic value.

  Raises:
    ArtifactProcessingError: If called when the knowledge base has not been
    initialized.
    KnowledgeBaseUninitializedError: If we failed to initialize the knowledge
    base.

  This is needed so that the artifact library has a standardized
  interface to the data that is actually stored in the GRRClient object in
  the GRR datastore.

  We expect that the client KNOWLEDGE_BASE is already filled out through the,
  KnowledgeBaseInitialization flow, but attempt to make some intelligent
  guesses if things failed.
  """
  client_schema = client_obj.Schema
  kb = client_obj.Get(client_schema.KNOWLEDGE_BASE)
  if not allow_uninitialized:
    if not kb:
      raise artifact_lib.KnowledgeBaseUninitializedError(
          "KnowledgeBase empty for %s." % client_obj.urn)
    if not kb.os:
      raise artifact_lib.KnowledgeBaseAttributesMissingError(
          "KnowledgeBase missing OS for %s. Knowledgebase content: %s" %
          (client_obj.urn, kb))
  if not kb:
    kb = client_schema.KNOWLEDGE_BASE()

  SetCoreGRRKnowledgeBaseValues(kb, client_obj)

  if kb.os == "Windows":
    # Add fallback values.
    if not kb.environ_allusersappdata and kb.environ_allusersprofile:
      # Guess if we don't have it already.
      if kb.os_major_version >= 6:
        kb.environ_allusersappdata = u"c:\\programdata"
        kb.environ_allusersprofile = u"c:\\programdata"
      else:
        kb.environ_allusersappdata = (u"c:\\documents and settings\\All Users\\"
                                      "Application Data")
        kb.environ_allusersprofile = u"c:\\documents and settings\\All Users"

  return kb


def SetCoreGRRKnowledgeBaseValues(kb, client_obj):
  """Set core values from GRR into the knowledgebase."""
  client_schema = client_obj.Schema
  kb.hostname = utils.SmartUnicode(client_obj.Get(client_schema.FQDN, ""))
  if not kb.hostname:
    kb.hostname = utils.SmartUnicode(client_obj.Get(client_schema.HOSTNAME, ""))
  versions = client_obj.Get(client_schema.OS_VERSION)
  if versions and versions.versions:
    kb.os_major_version = versions.versions[0]
    kb.os_minor_version = versions.versions[1]
  client_os = client_obj.Get(client_schema.SYSTEM)
  if client_os:
    kb.os = utils.SmartUnicode(client_obj.Get(client_schema.SYSTEM))


class KnowledgeBaseInitializationArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.KnowledgeBaseInitializationArgs


class KnowledgeBaseInitializationFlow(flow.GRRFlow):
  """Flow that atttempts to initialize the knowledge base.

  This flow processes all artifacts specified by the Artifacts.knowledge_base
  config.  We search for dependent artifacts following the dependency tree
  specified by the "provides" attributes in the artifact definitions.

  We don't try to fulfill dependencies in the tree order, the reasoning is that
  some artifacts may fail, and some artifacts provide the same dependency.

  Instead we take an iterative approach and keep requesting artifacts until
  all dependencies have been met.  If there is more than one artifact that
  provides a dependency we will collect them all as they likely have
  different performance characteristics, e.g. accuracy and client impact.
  """
  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = KnowledgeBaseInitializationArgs

  @flow.StateHandler(next_state="ProcessBootstrap")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    kb = rdfvalue.KnowledgeBase()
    SetCoreGRRKnowledgeBaseValues(kb, self.client)
    if not kb.os:
      raise flow.FlowError("Client OS not set for: %s, cannot initialize"
                           " KnowledgeBase" % self.client_id)
    self.state.Register("knowledge_base", kb)
    self.state.Register("fulfilled_deps", [])
    self.state.Register("partial_fulfilled_deps", set())
    self.state.Register("all_deps", set())
    self.state.Register("in_flight_artifacts", [])
    self.state.Register("awaiting_deps_artifacts", [])
    self.state.Register("completed_artifacts", [])

    self.CallFlow("BootStrapKnowledgeBaseFlow", next_state="ProcessBootstrap")

  def _GetDependencies(self):
    bootstrap_artifact_names = artifact_lib.ArtifactRegistry.GetArtifactNames(
        os_name=self.state.knowledge_base.os, collector_action="Bootstrap")

    kb_base_set = set(config_lib.CONFIG["Artifacts.knowledge_base"])
    kb_add = set(config_lib.CONFIG["Artifacts.knowledge_base_additions"])
    kb_skip = set(config_lib.CONFIG["Artifacts.knowledge_base_skip"])
    if self.args.lightweight:
      kb_skip.update(config_lib.CONFIG["Artifacts.knowledge_base_heavyweight"])
    kb_set = kb_base_set.union(kb_add) - kb_skip

    # Ignore bootstrap dependencies since they have already been fulfilled.
    no_deps_names = artifact_lib.ArtifactRegistry.GetArtifactNames(
        os_name=self.state.knowledge_base.os,
        name_list=kb_set,
        exclude_dependents=True) - bootstrap_artifact_names

    name_deps, all_deps = artifact_lib.ArtifactRegistry.SearchDependencies(
        self.state.knowledge_base.os, kb_set)

    # We only retrieve artifacts that are explicitly listed in
    # Artifacts.knowledge_base + additions - skip.
    name_deps = name_deps.intersection(kb_set)

    self.state.all_deps = all_deps
    # Ignore bootstrap dependencies since they have already been fulfilled.
    awaiting_deps_artifacts = list(name_deps - no_deps_names
                                   - bootstrap_artifact_names)

    return no_deps_names, all_deps, awaiting_deps_artifacts

  @flow.StateHandler(next_state="ProcessBase")
  def ProcessBootstrap(self, responses):
    """Process the bootstrap responses."""
    if not responses.success:
      raise flow.FlowError("Failed to run BootStrapKnowledgeBaseFlow. %s" %
                           responses.status)

    # Store bootstrap responses
    if responses.First():
      for key, value in responses.First().ToDict().items():
        self.state.fulfilled_deps.append(key)
        self.state.knowledge_base.Set(key, value)

    (no_deps_names, self.state.all_deps,
     self.state.awaiting_deps_artifacts) = self._GetDependencies()

    # Schedule anything with no deps next
    # Send each artifact independently so we can track which artifact produced
    # it when it comes back.
    # TODO(user): tag SendReplys with the flow that generated them.
    for artifact_name in no_deps_names:
      self.state.in_flight_artifacts.append(artifact_name)
      self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_name],
                    knowledge_base=self.state.knowledge_base,
                    store_results_in_aff4=False, next_state="ProcessBase",
                    request_data={"artifact_name": artifact_name})

  def _ScheduleCollection(self):
    # Schedule any new artifacts for which we have now fulfilled dependencies.
    for artifact_name in self.state.awaiting_deps_artifacts:
      artifact_obj = artifact_lib.ArtifactRegistry.artifacts[artifact_name]
      deps = artifact_obj.GetArtifactPathDependencies()
      if set(deps).issubset(self.state.fulfilled_deps):
        self.state.in_flight_artifacts.append(artifact_name)
        self.state.awaiting_deps_artifacts.remove(artifact_name)
        self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_name],
                      store_results_in_aff4=False, next_state="ProcessBase",
                      request_data={"artifact_name": artifact_name},
                      knowledge_base=self.state.knowledge_base)

    # If we're not done but not collecting anything, start accepting the partial
    # dependencies as full, and see if we can complete.
    if (self.state.awaiting_deps_artifacts and
        not self.state.in_flight_artifacts):
      if self.state.partial_fulfilled_deps:
        partial = self.state.partial_fulfilled_deps.pop()
        self.Log("Accepting partially fulfilled dependency: %s", partial)
        self.state.fulfilled_deps.append(partial)
        self._ScheduleCollection()

  @flow.StateHandler(next_state="ProcessBase")
  def ProcessBase(self, responses):
    """Process any retrieved artifacts."""
    artifact_name = responses.request_data["artifact_name"]
    self.state.in_flight_artifacts.remove(artifact_name)
    self.state.completed_artifacts.append(artifact_name)

    if not responses.success:
      self.Log("Failed to get artifact %s. Status: %s", artifact_name,
               responses.status)
    else:
      deps = self.SetKBValue(responses.request_data["artifact_name"],
                             responses)
      if deps:
        # If we fulfilled a dependency, make sure we have collected all
        # artifacts that provide the dependency before marking it as fulfilled.
        for dep in deps:
          required_artifacts = artifact_lib.ArtifactRegistry.GetArtifactNames(
              os_name=self.state.knowledge_base.os, provides=[dep])
          if required_artifacts.issubset(self.state.completed_artifacts):
            self.state.fulfilled_deps.append(dep)
          else:
            self.state.partial_fulfilled_deps.add(dep)
      else:
        self.Log("Failed to get artifact %s. Artifact failed to return value.",
                 artifact_name)

    if self.state.awaiting_deps_artifacts:
      # Schedule any new artifacts for which we have now fulfilled dependencies.
      self._ScheduleCollection()

      # If we fail to fulfil deps for things we're supposed to collect, raise
      # an error.
      if (self.state.awaiting_deps_artifacts and
          not self.state.in_flight_artifacts):
        missing_deps = list(self.state.all_deps.difference(
            self.state.fulfilled_deps))

        if self.args.require_complete:
          raise flow.FlowError("KnowledgeBase initialization failed as the "
                               "following artifacts had dependencies that could"
                               " not be fulfilled %s. Missing: %s" %
                               (self.state.awaiting_deps_artifacts,
                                missing_deps))
        else:
          self.Log("Storing incomplete KnowledgeBase. The following artifacts"
                   "had dependencies that could not be fulfilled %s. "
                   "Missing: %s. Completed: %s" % (
                       self.state.awaiting_deps_artifacts, missing_deps,
                       self.state.completed_artifacts))

  def SetKBValue(self, artifact_name, responses):
    """Set values in the knowledge base based on responses."""
    artifact_obj = artifact_lib.ArtifactRegistry.artifacts[artifact_name]
    if not responses:
      return None

    provided = set()   # Track which deps have been provided.

    for response in responses:
      if isinstance(response, rdfvalue.KnowledgeBaseUser):
        # MergeOrAddUser will update or add a user based on the attributes
        # returned by the artifact in the KnowledgeBaseUser.
        attrs_provided, merge_conflicts = (
            self.state.knowledge_base.MergeOrAddUser(response))
        provided.update(attrs_provided)
        for key, old_val, val in merge_conflicts:
          self.Log("KnowledgeBaseUser merge conflict in %s. Old value: %s, "
                   "Newly written value: %s", key, old_val, val)

      elif len(artifact_obj.provides) == 1:
        # This artifact provides a single KB attribute.
        value = None
        provides = artifact_obj.provides[0]
        if isinstance(response, rdfvalue.RDFString):
          value = str(responses.First())
        elif artifact_obj.collectors[0].action == "GetRegistryValue":
          value = responses.First().registry_data.GetValue()
        if value:
          logging.debug("Set KB %s to %s", provides, value)
          self.state.knowledge_base.Set(provides, value)
          provided.add(provides)
        else:
          logging.debug("Empty KB return value for %s", provides)
      else:
        # We are setting a knowledgebase value for something with multiple
        # provides. This isn't currently supported.
        raise RuntimeError("Attempt to process broken knowledge base artifact")

    return provided

  def CopyUsersFromKnowledgeBase(self, client):
    """Copy users from knowledgebase to USER.

    TODO(user): deprecate USER completely in favour of KNOWLEDGE_BASE.user

    Args:
      client: client object open for writing
    """
    usernames = []
    user_list = client.Schema.USER()
    for kbuser in self.state.knowledge_base.users:
      user_list.Append(rdfvalue.User().FromKnowledgeBaseUser(kbuser))

      if kbuser.username:
        usernames.append(kbuser.username)

    # Store it now
    client.AddAttribute(client.Schema.USER, user_list)
    client.AddAttribute(client.Schema.USERNAMES(
        " ".join(usernames)))

  @flow.StateHandler()
  def End(self, unused_responses):
    """Finish up and write the results."""
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.state.knowledge_base)
    self.CopyUsersFromKnowledgeBase(client)
    client.Flush()
    self.Notify("ViewObject", client.urn, "Knowledge Base Updated.")
    self.SendReply(self.state.knowledge_base)


def UploadArtifactYamlFile(file_content, base_urn=None, token=None,
                           overwrite=True):
  """Upload a yaml or json file as an artifact to the datastore."""
  _ = overwrite
  if not base_urn:
    base_urn = aff4.ROOT_URN.Add("artifact_store")
  with aff4.FACTORY.Create(base_urn, aff4_type="RDFValueCollection",
                           token=token, mode="rw") as artifact_coll:

    # Iterate through each artifact adding it to the collection.
    for artifact_value in artifact_lib.ArtifactsFromYaml(file_content):
      artifact_coll.Add(artifact_value)
      logging.info("Uploaded artifact %s to %s", artifact_value.name, base_urn)

  return base_urn


def LoadArtifactsFromDatastore(artifact_coll_urn=None, token=None,
                               overwrite_if_exists=True):
  """Load artifacts from the data store."""
  loaded_artifacts = []
  if not artifact_coll_urn:
    artifact_coll_urn = aff4.ROOT_URN.Add("artifact_store")
  with aff4.FACTORY.Create(artifact_coll_urn, aff4_type="RDFValueCollection",
                           token=token, mode="rw") as artifact_coll:
    for artifact_value in artifact_coll:
      artifact_lib.ArtifactRegistry.RegisterArtifact(
          artifact_value, source="datastore:%s" % artifact_coll_urn,
          overwrite_if_exists=overwrite_if_exists)
      loaded_artifacts.append(artifact_value)
      logging.debug("Loaded artifact %s from %s", artifact_value.name,
                    artifact_coll_urn)

  # Once all artifacts are loaded we can validate, as validation of dependencies
  # requires the group are all loaded before doing the validation.
  for artifact_value in loaded_artifacts:
    artifact_value.Validate()


class GRRArtifactMappings(object):
  """SemanticProto to AFF4 storage mappings.

  Class defining mappings between RDFValues collected by Artifacts, and the
  location they are stored in the AFF4 hierarchy.

  Each entry in the map contains:
    1. Location stored relative to the client.
    2. Name of the AFF4 type.
    3. Name of the attribute to be changed.
    4. Method for adding the RDFValue to the Attribute (Overwrite, Append)
  """

  rdf_map = {
      "SoftwarePackage": ("info/software", "InstalledSoftwarePackages",
                          "INSTALLED_PACKAGES", "Append"),
      "Volume": ("", "VFSGRRClient", "VOLUMES", "Append")
      }


class ArtifactLoader(registry.InitHook):
  """Loads artifacts from the datastore and from the filesystem.

  Datastore gets loaded second so it can override Artifacts in the files.
  """

  pre = ["AFF4InitHook"]

  def RunOnce(self):
    for path in config_lib.CONFIG["Artifacts.artifact_dirs"]:
      artifact_lib.LoadArtifactsFromDir(path)
