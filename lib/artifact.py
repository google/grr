#!/usr/bin/env python
"""Base classes for artifacts.

Artifacts are classes that describe a system artifact. They describe a number
of key properties about the artifact:

  Collectors: How to collect it from the client.
  Processors: How to process the data from the client.
  Storage: How to store the processed data.
"""

import logging

from grr.lib import aff4
from grr.lib import artifact_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class AFF4ResultWriter(object):
  """A wrapper class to allow writing objects to the AFF4 space."""

  def __init__(self, path, aff4_type, aff4_attribute, mode):
    self.path = path
    self.aff4_type = aff4_type
    self.aff4_attribute = aff4_attribute
    self.mode = mode


class ArtifactName(rdfvalue.RDFString):

  type = "ArtifactName"

  def ParseFromString(self, value):
    """Value must be a list of artifact names."""
    super(ArtifactName, self).ParseFromString(value)
    self.Validate(self._value)

  def Validate(self, value):
    """Validate we have a real Artifact name."""
    artifact_cls = artifact_lib.Artifact.classes.get(value)
    if (not artifact_cls or not
        issubclass(artifact_cls, artifact_lib.Artifact)):
      raise type_info.TypeValueError("%s not a valid Artifact." % value)


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

  This is needed so that the artifact library has a standardized
  interface to the data that is actually stored in the GRRClient object in
  the GRR datastore.

  We expect that the client KNOWLEDGE_BASE is already filled out through the,
  KnowledgeBaseInitialization flow, but attempt to make some intelligent
  guesses if things failed.
  """
  client_schema = client_obj.Schema
  kb = client_obj.Get(client_schema.KNOWLEDGE_BASE)
  if not allow_uninitialized and (not kb or not kb.os):
    raise artifact_lib.KnowledgeBaseUninitializedError(
        "Attempting to retreive uninitialized KnowledgeBase for %s. Failing." %
        client_obj.urn)
  if not kb:
    kb = client_schema.KNOWLEDGE_BASE()

  SetCoreGRRKnowledgeBaseValues(kb, client_obj)

  # Copy user values from client to appropriate KB variables.
  user_pb = client_obj.Get(client_obj.Schema.USER)
  if user_pb:
    for user in user_pb:
      _, merge_conflicts = kb.MergeOrAddUser(user.ToKnowledgeBaseUser())
      for key, old_val, val in merge_conflicts:
        logging.debug("KnowledgeBaseUser merge conflict in %s. Old value: %s, "
                      "Newly written value: %s", key, old_val, val)

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
  kb.os = utils.SmartUnicode(client_obj.Get(client_schema.SYSTEM))


class KnowledgeBaseInitializationFlow(flow.GRRFlow):
  """Flow that atttempts to initialize the knowledge base.

  This flow processes all artifacts that have a PROVIDES attribute, attempting
  to collect and process them to generate a knowledge base of core information
  that can be used to process other artifacts.
  """

  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="ProcessBootstrap")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    kb = rdfvalue.KnowledgeBase()
    SetCoreGRRKnowledgeBaseValues(kb, self.client)
    self.state.Register("knowledge_base", kb)
    self.state.Register("fulfilled_deps", [])
    self.state.Register("all_deps", [])
    self.state.Register("in_flight_artifacts", [])
    self.state.Register("awaiting_deps_artifacts", [])
    self.state.Register("completed_artifacts", [])

    self.CallFlow("BootStrapKnowledgeBaseFlow", next_state="ProcessBootstrap")

  @flow.StateHandler(next_state="ProcessBase")
  def ProcessBootstrap(self, responses):
    """Process the bootstrap responses."""
    # pylint: disable=g-explicit-length-test
    if not responses.success or len(responses) == 0:
      raise flow.FlowError("Failed to run BootStrapKnowledgeBaseFlow. %s" %
                           responses.status)
    for key, value in responses.First().ToDict().items():
      self.state.fulfilled_deps.append(key)
      self.state.knowledge_base.Set(key, value)

    all_kb_artifacts = artifact_lib.Artifact.GetKnowledgeBaseArtifacts()
    bootstrap_artifacts = (
        artifact_lib.Artifact.GetKnowledgeBaseBootstrapArtifacts())

    # Filter out any which are bootstrap artifacts, which have special
    # GRR specific handling in BootStrapKnowledgeBaseFlow.
    artifacts_to_process = []          # Artifacts that need processing now.
    no_deps_artifacts_names = []       # Artifacts without any dependencies.
    for artifact_cls in all_kb_artifacts:
      deps = artifact_cls.GetArtifactPathDependencies()
      if not deps:
        no_deps_artifacts_names.append(artifact_cls.__name__)
        if artifact_cls not in bootstrap_artifacts:
          # We can't process Bootstrap artifacts, they are handled separately.
          artifacts_to_process.append(artifact_cls.__name__)
      else:
        self.state.all_deps.extend(deps)

    if not artifacts_to_process:
      raise flow.FlowError("We can't bootstrap the knowledge base because we "
                           "don't have any artifacts without dependencies.")

    all_kb_artifacts_names = [a.__name__ for a in all_kb_artifacts]
    self.state.awaiting_deps_artifacts = list(set(all_kb_artifacts_names) -
                                              set(no_deps_artifacts_names))
    self.state.all_deps = list(set(self.state.all_deps))  # Dedup dependencies.

    # Now that we have the bootstrap done, run anything
    # Send each artifact independently so we can track which artifact produced
    # it when it comes back.
    # TODO(user): tag SendReplys with the flow that generated them.
    for artifact_name in artifacts_to_process:
      self.state.in_flight_artifacts.append(artifact_name)
      self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_name],
                    knowledge_base=self.state.knowledge_base,
                    store_results_in_aff4=False, next_state="ProcessBase",
                    request_data={"artifact_name": artifact_name})

  @flow.StateHandler(next_state="ProcessBase")
  def ProcessBase(self, responses):
    """Process any retrieved artifacts."""
    artifact_name = responses.request_data["artifact_name"]
    if not responses.success:
      self.Log("Failed to get artifact %s. Status: %s", artifact_name,
               responses.status)
    else:
      deps = self.SetKBValue(responses.request_data["artifact_name"],
                             responses)
      if deps:
        self.state.fulfilled_deps.extend(deps)
      else:
        self.Log("Failed to get artifact %s. Artifact failed to return value.",
                 artifact_name)

    self.state.in_flight_artifacts.remove(artifact_name)
    self.state.completed_artifacts.append(artifact_name)

    if self.state.awaiting_deps_artifacts:
      # Schedule any new artifacts for which we have now fulfilled dependencies.
      for artifact_name in self.state.awaiting_deps_artifacts:
        artifact_cls = artifact_lib.Artifact.classes[artifact_name]
        deps = artifact_cls.GetArtifactPathDependencies()
        if set(deps).issubset(self.state.fulfilled_deps):
          self.state.in_flight_artifacts.append(artifact_name)
          self.state.awaiting_deps_artifacts.remove(artifact_name)
          self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_name],
                        store_results_in_aff4=False, next_state="ProcessBase",
                        request_data={"artifact_name": artifact_name},
                        knowledge_base=self.state.knowledge_base)

      # If we fail to fulfil deps for things we're supposed to collect, raise
      # an error.
      if (self.state.awaiting_deps_artifacts and
          not self.state.in_flight_artifacts):
        missing_deps = list(set(self.state.all_deps).difference(
            self.state.fulfilled_deps))
        raise flow.FlowError("KnowledgeBase initialization failed as the "
                             "following artifacts had dependencies that could "
                             "not be fulfilled %s. Missing: %s" %
                             (self.state.awaiting_deps_artifacts, missing_deps))

  def SetKBValue(self, artifact_name, responses):
    """Set values in the knowledge base based on responses."""
    artifact_cls = artifact_lib.Artifact.classes[artifact_name]
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

      elif not isinstance(artifact_cls.PROVIDES, (list, tuple)):
        # This artifact provides a single KB attribute.
        value = None
        if isinstance(response, rdfvalue.RDFString):
          value = str(responses.First())
        elif artifact_cls.COLLECTORS[0].action == "GetRegistryValue":
          value = responses.First().registry_data.GetValue()
        if value:
          logging.debug("Set KB %s to %s", artifact_cls.PROVIDES, value)
          self.state.knowledge_base.Set(artifact_cls.PROVIDES, value)
          provided.add(artifact_cls.PROVIDES)
        else:
          logging.debug("Empty KB return value for %s", artifact_cls.PROVIDES)
      else:
        # We are setting a knowledgebase value for something with multiple
        # provides. This isn't currently supported.
        raise RuntimeError("Attempt to process broken knowledge base artifact")

    return provided

  @flow.StateHandler()
  def End(self, unused_responses):
    """Finish up and write the results."""
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.state.knowledge_base)
    client.Flush()
    self.Notify("ViewObject", client.urn, "Knowledge Base Updated.")
    self.SendReply(self.state.knowledge_base)


class GRRArtifactMappings(object):
  """SemanticProto to AFF4 storage mappings.

  Class defining mappings between RDFValues collected by Artifacts, and the
  location they are stored in the AFF4 hierarchy.

  Each entry in the map contains:
    1. Location stored relative to the client.
    2. Name of the AFF4 type.
    3. Name of the attribute to be changed.
    4. Method for adding the RDFValue to the Attribute (Set, Append)
  """

  rdf_map = {
      "SoftwarePackage": ("info/software", "InstalledSoftwarePackages",
                          "INSTALLED_PACKAGES", "Append")
      }
