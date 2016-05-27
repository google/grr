#!/usr/bin/env python
"""Base classes for artifacts."""

import logging

from grr.lib import aff4
from grr.lib import artifact_registry
from grr.lib import artifact_utils
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import software
from grr.lib.rdfvalues import anomaly
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
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
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "KnowledgeBase empty for %s." % client_obj.urn)
    if not kb.os:
      raise artifact_utils.KnowledgeBaseAttributesMissingError(
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


class CollectArtifactDependenciesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CollectArtifactDependenciesArgs


class CollectArtifactDependencies(flow.GRRFlow):
  """Collect knowledgebase dependencies for a list of artifacts.

  We determine what knowledgebase attributes are required to collect and parse
  the given list of artifacts. They are then collected and stored in the
  knowledgebase.

  We don't try to fulfill dependencies in the tree order, the reasoning is that
  some artifacts may fail, and some artifacts provide the same dependency.

  Instead we take an iterative approach and keep requesting artifacts until
  all dependencies have been met.  If there is more than one artifact that
  provides a dependency we will collect them all as they likely have
  different performance characteristics, e.g. accuracy and client impact.

  Note that running a full KnowledgeBaseInitializationFlow is the most complete
  way to ensure all dependencies have been collected.  We collect explicit
  dependencies here, but for example if a registry key value retrieved contains
  an environment variable not already collected it may not get expanded.
  """
  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = CollectArtifactDependenciesArgs

  @flow.StateHandler(next_state=["ProcessBase"])
  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.state.Register("knowledge_base", None)
    self.state.Register("fulfilled_deps", [])
    self.state.Register("partial_fulfilled_deps", set())
    self.state.Register("all_deps", set())
    self.state.Register("in_flight_artifacts", [])
    self.state.Register("awaiting_deps_artifacts", [])
    self.state.Register("completed_artifacts", [])

    self.InitializeKnowledgeBase()
    first_flows = self.GetFirstFlowsForCollection()

    # Send each artifact independently so we can track which artifact produced
    # it when it comes back.
    # TODO(user): tag SendReplys with the flow that
    # generated them.
    for artifact_name in first_flows:
      self.state.in_flight_artifacts.append(artifact_name)
      self.CallFlow("ArtifactCollectorFlow",
                    artifact_list=[artifact_name],
                    knowledge_base=self.state.knowledge_base,
                    store_results_in_aff4=False,
                    next_state="ProcessBase",
                    request_data={"artifact_name": artifact_name})

  def GetFirstFlowsForCollection(self):
    """Initialize dependencies and calculate first round of flows.

    Returns:
      set of artifact names with no dependencies that should be collected first.
    """
    artifact_set = set(self.args.artifact_list)

    deps = artifact_registry.REGISTRY.SearchDependencies(
        self.state.knowledge_base.os, artifact_set)
    name_deps, self.state.all_deps = deps

    # Find the any dependencies that don't have dependencies themselves as our
    # starting point.
    check_deps = name_deps.union(artifact_set)
    no_deps_names = artifact_registry.REGISTRY.GetArtifactNames(
        os_name=self.state.knowledge_base.os,
        name_list=check_deps,
        exclude_dependents=True)

    # If the only artifacts with no dependencies are the ones we want to collect
    # that means there is nothing to do.
    if no_deps_names == artifact_set:
      return []

    # We're going to collect everything that doesn't have a dependency first.
    # Anything else we're waiting on a dependency before we can collect.

    # We exclude the original artifacts since we're just fulfilling
    # dependencies, the original flow will collect the artifacts once the
    # dependencies are ready.
    self.state.awaiting_deps_artifacts = list(name_deps - no_deps_names -
                                              artifact_set)
    return no_deps_names

  def InitializeKnowledgeBase(self):
    """Get the existing KB or create a new one if none exists."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.knowledge_base = GetArtifactKnowledgeBase(
        self.client, allow_uninitialized=True)

    if not self.state.knowledge_base.os:
      # If we don't know what OS this is, there is no way to proceed.
      raise flow.FlowError("Client OS not set for: %s, cannot initialize"
                           " KnowledgeBase" % self.client_id)

  def _ScheduleCollection(self):
    # Schedule any new artifacts for which we have now fulfilled dependencies.
    for artifact_name in self.state.awaiting_deps_artifacts:
      artifact_obj = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      deps = artifact_obj.GetArtifactPathDependencies()
      if set(deps).issubset(self.state.fulfilled_deps):
        self.state.in_flight_artifacts.append(artifact_name)
        self.state.awaiting_deps_artifacts.remove(artifact_name)
        self.CallFlow("ArtifactCollectorFlow",
                      artifact_list=[artifact_name],
                      store_results_in_aff4=False,
                      next_state="ProcessBase",
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
      deps = self.SetKBValue(responses.request_data["artifact_name"], responses)
      if deps:
        # If we fulfilled a dependency, make sure we have collected all
        # artifacts that provide the dependency before marking it as fulfilled.
        for dep in deps:
          required_artifacts = (artifact_registry.REGISTRY.GetArtifactNames(
              os_name=self.state.knowledge_base.os,
              provides=[dep]))
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
                   "Missing: %s. Completed: %s" %
                   (self.state.awaiting_deps_artifacts, missing_deps,
                    self.state.completed_artifacts))

  def SetKBValue(self, artifact_name, responses):
    """Set values in the knowledge base based on responses."""
    artifact_obj = artifact_registry.REGISTRY.GetArtifact(artifact_name)
    if not responses:
      return None

    provided = set()  # Track which deps have been provided.

    for response in responses:
      if isinstance(response, anomaly.Anomaly):
        logging.error("Artifact %s returned an Anomaly: %s", artifact_name,
                      response)
        continue
      if isinstance(response, rdf_client.User):
        # MergeOrAddUser will update or add a user based on the attributes
        # returned by the artifact in the User.
        attrs_provided, merge_conflicts = (
            self.state.knowledge_base.MergeOrAddUser(response))
        provided.update(attrs_provided)
        for key, old_val, val in merge_conflicts:
          self.Log("User merge conflict in %s. Old value: %s, "
                   "Newly written value: %s", key, old_val, val)

      else:
        artifact_provides = artifact_obj.provides
        if isinstance(response, rdf_protodict.Dict):
          # Attempting to fulfil provides with a Dict response means we are
          # supporting multiple provides based on the keys of the dict.
          kb_dict = response.ToDict()
        else:
          if len(artifact_provides) == 1:
            # If its not a dict we only support a single value.
            kb_dict = {artifact_provides[0]: response}
          else:
            raise RuntimeError("Attempt to set a knowledge base value with "
                               "multiple provides clauses without using Dict."
                               ": %s" % artifact_obj)

        for provides, value in kb_dict.iteritems():
          if provides not in artifact_provides:
            raise RuntimeError("Attempt to provide knowledge base value %s "
                               "without this being set in the artifact "
                               "provides setting: %s" % (provides,
                                                         artifact_obj))

          if isinstance(value, rdfvalue.RDFString):
            value = utils.SmartStr(value)
          elif hasattr(value, "registry_data"):
            value = value.registry_data.GetValue()

          if value:
            logging.debug("Set KB %s to %s", provides, value)
            self.state.knowledge_base.Set(provides, value)
            provided.add(provides)
          else:
            logging.debug("Empty KB return value for %s", provides)

    return provided

  def CopyUserNamesFromKnowledgeBase(self, client):
    """Copy usernames from knowledgebase to USERNAMES.

    Args:
      client: client object open for writing
    """
    kb = self.state.knowledge_base.users
    usernames = [user.username for user in kb if user.username]
    client.AddAttribute(client.Schema.USERNAMES(" ".join(usernames)))

  def CopyOSReleaseFromKnowledgeBase(self, client):
    """Copy os release and version from KB to client object."""
    if self.state.knowledge_base.os_release:
      os_release = self.state.knowledge_base.os_release
      client.Set(client.Schema.OS_RELEASE(os_release))

      # Override OS version field too.
      # TODO(user): this actually results in incorrect versions for things
      #                like Ubuntu (14.4 instead of 14.04). I don't think zero-
      #                padding is always correct, however.
      os_version = "%d.%d" % (self.state.knowledge_base.os_major_version,
                              self.state.knowledge_base.os_minor_version)
      client.Set(client.Schema.OS_VERSION(os_version))

  @flow.StateHandler()
  def End(self, unused_responses):
    """Finish up and write the results."""
    client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)
    client.Set(client.Schema.KNOWLEDGE_BASE, self.state.knowledge_base)
    self.CopyUserNamesFromKnowledgeBase(client)
    self.CopyOSReleaseFromKnowledgeBase(client)
    client.Flush()
    self.Notify("ViewObject", client.urn, "Knowledge Base Updated.")
    self.SendReply(self.state.knowledge_base)


class KnowledgeBaseInitializationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KnowledgeBaseInitializationArgs


class KnowledgeBaseInitializationFlow(CollectArtifactDependencies):
  """Flow that atttempts to initialize the knowledge base.

  This flow processes all artifacts specified by the Artifacts.knowledge_base
  config.  It it is a CollectArtifactDependencies flow with slightly different
  setup.
  """
  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = KnowledgeBaseInitializationArgs

  def GetFirstFlowsForCollection(self):
    """Initialize dependencies and calculate first round of flows.

    Returns:
      set of artifact names with no dependencies that should be collected first.

    Raises:
      RuntimeError: On bad artifact configuration parameters.
    """
    kb_base_set = set(config_lib.CONFIG["Artifacts.knowledge_base"])
    kb_add = set(config_lib.CONFIG["Artifacts.knowledge_base_additions"])
    kb_skip = set(config_lib.CONFIG["Artifacts.knowledge_base_skip"])
    if self.args.lightweight:
      kb_skip.update(config_lib.CONFIG["Artifacts.knowledge_base_heavyweight"])
    kb_set = kb_base_set.union(kb_add) - kb_skip

    for artifact_name in kb_set:
      artifact_registry.REGISTRY.GetArtifact(artifact_name)

    no_deps_names = artifact_registry.REGISTRY.GetArtifactNames(
        os_name=self.state.knowledge_base.os,
        name_list=kb_set,
        exclude_dependents=True)

    name_deps, self.state.all_deps = (
        artifact_registry.REGISTRY.SearchDependencies(
            self.state.knowledge_base.os, kb_set))

    # We only retrieve artifacts that are explicitly listed in
    # Artifacts.knowledge_base + additions - skip.
    name_deps = name_deps.intersection(kb_set)

    # We're going to collect everything that doesn't have a dependency first.
    # Anything else we're waiting on a dependency before we can collect.
    self.state.awaiting_deps_artifacts = list(name_deps - no_deps_names)

    return no_deps_names

  def InitializeKnowledgeBase(self):
    """Get the existing KB or create a new one if none exists."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

    # Always create a new KB to override any old values.
    self.state.knowledge_base = rdf_client.KnowledgeBase()
    SetCoreGRRKnowledgeBaseValues(self.state.knowledge_base, self.client)
    if not self.state.knowledge_base.os:
      # If we don't know what OS this is, there is no way to proceed.
      raise flow.FlowError("Client OS not set for: %s, cannot initialize"
                           " KnowledgeBase" % self.client_id)


def ApplyParserToResponses(processor_obj, responses, source, state, token):
  """Parse responses using the specified processor and the right args.

  Args:
    processor_obj: A Processor object that inherits from Parser.
    responses: A list of, or single response depending on the processors
       process_together setting.
    source: The source responsible for producing the responses.
    state: The current state of an artifact collection flow.
    token: The token used in an artifact collection flow.

  Raises:
    RuntimeError: On bad parser.

  Returns:
    An iterator of the processor responses.
  """
  if not processor_obj:
    # We don't do any parsing, the results are raw as they came back.
    # If this is an RDFValue we don't want to unpack it further
    if isinstance(responses, rdfvalue.RDFValue):
      result_iterator = [responses]
    else:
      result_iterator = responses

  else:
    # We have some processors to run.
    if processor_obj.process_together:
      # We are processing things in a group which requires specialized
      # handling by the parser. This is used when multiple responses need to
      # be combined to parse successfully. E.g parsing passwd and shadow files
      # together.
      parse_method = processor_obj.ParseMultiple
    else:
      parse_method = processor_obj.Parse

    if isinstance(processor_obj, parsers.CommandParser):
      # Command processor only supports one response at a time.
      response = responses
      result_iterator = parse_method(cmd=response.request.cmd,
                                     args=response.request.args,
                                     stdout=response.stdout,
                                     stderr=response.stderr,
                                     return_val=response.exit_status,
                                     time_taken=response.time_used,
                                     knowledge_base=state.knowledge_base)

    elif isinstance(processor_obj, parsers.WMIQueryParser):
      query = source["attributes"]["query"]
      result_iterator = parse_method(query, responses, state.knowledge_base)

    elif isinstance(processor_obj, parsers.FileParser):
      if processor_obj.process_together:
        file_objects = [aff4.FACTORY.Open(r.aff4path, token=token)
                        for r in responses]
        result_iterator = parse_method(responses, file_objects,
                                       state.knowledge_base)
      else:
        fd = aff4.FACTORY.Open(responses.aff4path, token=token)
        result_iterator = parse_method(responses, fd, state.knowledge_base)

    elif isinstance(processor_obj,
                    (parsers.RegistryParser, parsers.RekallPluginParser,
                     parsers.RegistryValueParser, parsers.GenericResponseParser,
                     parsers.GrepParser)):
      result_iterator = parse_method(responses, state.knowledge_base)

    elif isinstance(processor_obj, (parsers.ArtifactFilesParser)):
      result_iterator = parse_method(responses, state.knowledge_base,
                                     state.path_type)

    else:
      raise RuntimeError("Unsupported parser detected %s" % processor_obj)
  return result_iterator


def UploadArtifactYamlFile(file_content,
                           base_urn=None,
                           token=None,
                           overwrite=True):
  """Upload a yaml or json file as an artifact to the datastore."""
  _ = overwrite
  loaded_artifacts = []
  if not base_urn:
    base_urn = aff4.ROOT_URN.Add("artifact_store")
  registry_obj = artifact_registry.REGISTRY

  new_artifacts = registry_obj.ArtifactsFromYaml(file_content)
  # A quick syntax check before we upload anything.
  for artifact_value in new_artifacts:
    artifact_value.ValidateSyntax()

  # Iterate through each artifact adding it to the collection.
  with aff4.FACTORY.Create(base_urn,
                           aff4_type=collects.RDFValueCollection,
                           token=token,
                           mode="rw") as artifact_coll:
    for artifact_value in new_artifacts:
      artifact_coll.Add(artifact_value)
      registry_obj.RegisterArtifact(artifact_value,
                                    source="datastore:%s" % base_urn,
                                    overwrite_if_exists=overwrite)
      loaded_artifacts.append(artifact_value)
      logging.info("Uploaded artifact %s to %s", artifact_value.name, base_urn)

  # Once all artifacts are loaded we can validate, as validation of dependencies
  # requires the group are all loaded before doing the validation.
  for artifact_value in loaded_artifacts:
    artifact_value.Validate()

  return base_urn


class ArtifactFallbackCollectorArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFallbackCollectorArgs


class ArtifactFallbackCollector(flow.GRRFlow):
  """Abstract class for artifact fallback flows.

  If an artifact can't be collected by normal means a flow can be registered
  with a fallback means of collection by subclassing this class. This is useful
  when an artifact is critical to the collection of other artifacts so we want
  to try harder to make sure its collected.

  The flow will be called from
  lib.flows.general.collectors.ArtifactCollectorFlow. The flow should SendReply
  the artifact value in the same format as would have been returned by the
  original artifact collection.
  """
  __metaclass__ = registry.MetaclassRegistry
  args_type = ArtifactFallbackCollectorArgs

  # List of artifact names for which we are registering as the fallback
  artifacts = []


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
      "SoftwarePackage": ("info/software",
                          software.InstalledSoftwarePackages.__name__,
                          "INSTALLED_PACKAGES", "Append"),
      "Volume": ("", aff4_grr.VFSGRRClient.__name__, "VOLUMES", "Append"),
      "HardwareInfo": ("", aff4_grr.VFSGRRClient.__name__, "HARDWARE_INFO",
                       "Overwrite")
  }


class ArtifactLoader(registry.InitHook):
  """Loads artifacts from the datastore and from the filesystem.

  Datastore gets loaded second so it can override Artifacts in the files.
  """

  pre = ["AFF4InitHook"]

  def RunOnce(self):
    for path in config_lib.CONFIG["Artifacts.artifact_dirs"]:
      artifact_registry.REGISTRY.AddDirSource(path)

    artifact_registry.REGISTRY.AddDatastoreSources([aff4.ROOT_URN.Add(
        "artifact_store")])
