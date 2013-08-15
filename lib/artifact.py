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


class ArtifactList(type_info.TypeInfoObject):
  """A list of Artifacts names."""

  renderer = "ArtifactListRenderer"

  def Validate(self, value):
    """Value must be a list of artifact names."""
    try:
      iter(value)
    except TypeError:
      raise type_info.TypeValueError(
          "%s not a valid iterable for ArtifactList" % value)
    for val in value:
      if not isinstance(val, basestring):
        raise type_info.TypeValueError("%s not a valid instance string." % val)
      artifact_cls = artifact_lib.Artifact.classes.get(val)
      if (not artifact_cls or not
          issubclass(artifact_cls, artifact_lib.Artifact)):
        raise type_info.TypeValueError("%s not a valid Artifact class." % val)

    return value


KB_USER_MAPPING = {
    "username": "username",
    "domain": "userdomain",
    "homedir": "homedir",
    "sid": "sid",
    "special_folders.cookies": "cookies",
    "special_folders.local_settings": "local_settings",
    "special_folders.local_app_data": "localappdata",
    "special_folders.app_data": "appdata",
    "special_folders.cache": "internet_cache",
    "special_folders.personal": "personal",
    "special_folders.desktop": "desktop",
    "special_folders.startup": "startup",
    "special_folders.recent": "recent",
    # TODO(user): Add support for these properties.
    # "homedir": "userprofile",
    # "gid"
    # "uid"
}


def GetArtifactKnowledgeBase(client_obj):
  """This generates an artifact knowledge base from a GRR client.

  Args:
    client_obj: A GRRClient object which is opened for reading.

  Returns:
    A KnowledgeBase semantic value.

  This is needed so that the artifact library has a standardized
  interface to the data that is actually stored in the GRRClient object in
  the GRR datastore.

  We expect that the client KNOWLEDGE_BASE is already filled out, but attempt to
  make some intelligent guesses if things failed.
  """
  client_schema = client_obj.Schema
  kb = client_obj.Get(client_schema.KNOWLEDGE_BASE)
  if not kb:
    kb = client_schema.KNOWLEDGE_BASE()

  # Copy user values from client to appropriate KB variables.
  user_pb = client_obj.Get(client_obj.Schema.USER)
  if user_pb:
    for user in user_pb:
      new_user = rdfvalue.KnowledgeBaseUser()
      for old_pb_name, new_pb_name in KB_USER_MAPPING.items():
        if len(old_pb_name.split(".")) > 1:
          attr, old_pb_name = old_pb_name.split(".", 1)
          val = getattr(getattr(user, attr), old_pb_name)
        else:
          val = getattr(user, old_pb_name)
        setattr(new_user, new_pb_name, val)
      kb.users.Append(new_user)

  # Copy base values.
  kb.hostname = utils.SmartUnicode(client_obj.Get(client_schema.FQDN, ""))
  if not kb.hostname:
    kb.hostname = utils.SmartUnicode(client_obj.Get(client_schema.HOSTNAME, ""))
  versions = client_obj.Get(client_schema.OS_VERSION)
  if versions:
    kb.os_major_version = versions.versions[0]
    kb.os_minor_version = versions.versions[1]
  kb.os = utils.SmartUnicode(client_obj.Get(client_schema.SYSTEM))

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


class KnowledgeBaseInitializationFlow(flow.GRRFlow):
  """Flow that atttempts to initialize the knowledge base.

  This flow processes all artifacts that have a PROVIDES attribute, attempting
  to collect and process them to generate a knowledge base of core information
  that can be used to process other artifacts.
  """

  category = "/Administrative/"

  @flow.StateHandler(next_state="ProcessBootstrap")
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("knowledge_base", GetArtifactKnowledgeBase(self.client))
    self.state.Register("fulfilled_deps", [])
    self.state.Register("in_flight_artifacts", [])
    self.state.Register("awaiting_deps_artifacts", [])
    self.state.Register("completed_artifacts", [])

    self.CallFlow("BootStrapKnowledgeBaseFlow", next_state="ProcessBootstrap")

  @flow.StateHandler(next_state="ProcessBase")
  def ProcessBootstrap(self, responses):
    """Process the bootstrap responses."""
    if not responses.success:
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
      if not artifact_cls.GetArtifactDependencies():
        no_deps_artifacts_names.append(artifact_cls.__name__)
        if artifact_cls not in bootstrap_artifacts:
          # We can't process Bootstrap artifacts, they are handled separately.
          artifacts_to_process.append(artifact_cls.__name__)

    if not artifacts_to_process:
      raise flow.FlowError("We can't bootstrap the knowledge base because we "
                           "don't have any artifacts without dependencies.")

    all_kb_artifacts_names = [a.__name__ for a in all_kb_artifacts]
    self.state.awaiting_deps_artifacts = list(set(all_kb_artifacts_names) -
                                              set(no_deps_artifacts_names))

    # Now that we have the bootstrap done, run anything
    # Send each artifact independently so we can track which artifact produced
    # it when it comes back.
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
      dep = self.SetKBValue(responses.request_data["artifact_name"],
                            responses.First())
      if dep:
        self.state.fulfilled_deps.append(dep)
      else:
        self.Log("Failed to get artifact %s. Artifact failed to return value.",
                 artifact_name)

    self.state.in_flight_artifacts.remove(artifact_name)
    self.state.completed_artifacts.append(artifact_name)

    if self.state.awaiting_deps_artifacts:
      # Schedule any new artifacts for which we have now fulfilled dependencies.
      for artifact_name in self.state.awaiting_deps_artifacts:
        artifact_cls = artifact_lib.Artifact.classes[artifact_name]
        deps = artifact_cls.GetArtifactDependencies()
        if set(deps).issubset(self.state.fulfilled_deps):
          self.state.in_flight_artifacts.append(artifact_name)
          self.state.awaiting_deps_artifacts.remove(artifact_name)
          self.CallFlow("ArtifactCollectorFlow", artifact_list=[artifact_name],
                        store_results_in_aff4=False, next_state="ProcessBase",
                        request_data={"artifact_name": artifact_name},
                        knowledge_base=self.state.knowledge_base)

  def SetKBValue(self, artifact_name, value):
    """Set the value in the knowledge base."""
    artifact_cls = artifact_lib.Artifact.classes[artifact_name]
    if not value:
      return None
    elif "." in artifact_cls.PROVIDES:
      # Expect multiple values, e.g. User.homedir
      # TODO(user): Handle repeated knowledge base values.
      return
    elif isinstance(value, rdfvalue.RDFString):
      value = str(value)
    elif artifact_cls.COLLECTORS[0].action == "GetRegistryValue":
      value = value.registry_data.GetValue()

    if value:
      logging.debug("Set KB %s to %s", artifact_cls.PROVIDES, value)
      self.state.knowledge_base.Set(artifact_cls.PROVIDES, value)
      return artifact_cls.PROVIDES
    else:
      return None

  @flow.StateHandler()
  def End(self, unused_responses):
    """Finish up and write the results."""
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.state.knowledge_base)
    client.Flush()
    self.Notify("ViewObject", client.urn, "Knowledge Base Updated.")


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
