#!/usr/bin/env python
"""Base classes for artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging


from future.utils import iteritems

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_proto import flows_pb2
from grr_response_server import aff4
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import flow_base


def GetKnowledgeBase(rdf_client_obj, allow_uninitialized=False):
  """Returns a knowledgebase from an rdf client object."""
  kb = rdf_client_obj.knowledge_base
  if not allow_uninitialized:
    if not kb:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "KnowledgeBase empty for %s." % rdf_client_obj.client_id)
    if not kb.os:
      raise artifact_utils.KnowledgeBaseAttributesMissingError(
          "KnowledgeBase missing OS for %s. Knowledgebase content: %s" %
          (rdf_client_obj.client_id, kb))
  if not kb:
    return rdf_client.KnowledgeBase()

  version = unicode(rdf_client_obj.os_version)
  split_version = version.split(".")
  try:
    kb.os_major_version = int(split_version[0])
    if len(split_version) >= 1:
      kb.os_minor_version = int(split_version[1])
  except ValueError:
    pass

  return kb


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
  kb.fqdn = utils.SmartUnicode(client_obj.Get(client_schema.FQDN, ""))
  if not kb.fqdn:
    kb.fqdn = utils.SmartUnicode(client_obj.Get(client_schema.HOSTNAME, ""))
  versions = client_obj.Get(client_schema.OS_VERSION)
  if versions and versions.versions:
    try:
      kb.os_major_version = versions.versions[0]
      kb.os_minor_version = versions.versions[1]
    except IndexError:
      # Some OSs don't have a minor version.
      pass
  client_os = client_obj.Get(client_schema.SYSTEM)
  if client_os:
    kb.os = utils.SmartUnicode(client_obj.Get(client_schema.SYSTEM))


class KnowledgeBaseInitializationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KnowledgeBaseInitializationArgs


@flow_base.DualDBFlow
class KnowledgeBaseInitializationFlowMixin(object):
  """Flow that atttempts to initialize the knowledge base.

  This flow processes all artifacts specified by the
  Artifacts.knowledge_base config. We determine what knowledgebase
  attributes are required, collect them, and return a filled
  knowledgebase.

  We don't try to fulfill dependencies in the tree order, the
  reasoning is that some artifacts may fail, and some artifacts
  provide the same dependency.

  Instead we take an iterative approach and keep requesting artifacts
  until all dependencies have been met.  If there is more than one
  artifact that provides a dependency we will collect them all as they
  likely have different performance characteristics, e.g. accuracy and
  client impact.
  """

  category = "/Collectors/"
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"
  args_type = KnowledgeBaseInitializationArgs

  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.state.knowledge_base = None
    self.state.fulfilled_deps = set()
    self.state.partial_fulfilled_deps = set()
    self.state.all_deps = set()
    self.state.in_flight_artifacts = set()
    self.state.awaiting_deps_artifacts = set()
    self.state.completed_artifacts = set()

    self.InitializeKnowledgeBase()
    first_flows = self.GetFirstFlowsForCollection()

    # Send each artifact independently so we can track which artifact produced
    # it when it comes back.
    # TODO(user): tag SendReplys with the flow that
    # generated them.
    for artifact_name in first_flows:
      self.state.in_flight_artifacts.add(artifact_name)

      self.CallFlow(
          # TODO(user): dependency loop with flows/general/collectors.py.
          # collectors.ArtifactCollectorFlow.__name__,
          "ArtifactCollectorFlow",
          artifact_list=[artifact_name],
          knowledge_base=self.state.knowledge_base,
          next_state="ProcessBase",
          request_data={"artifact_name": artifact_name})

  def _ScheduleCollection(self):
    # Schedule any new artifacts for which we have now fulfilled dependencies.
    for artifact_name in self.state.awaiting_deps_artifacts:
      artifact_obj = artifact_registry.REGISTRY.GetArtifact(artifact_name)
      deps = artifact_registry.GetArtifactPathDependencies(artifact_obj)
      if set(deps).issubset(self.state.fulfilled_deps):
        self.state.in_flight_artifacts.add(artifact_name)
        self.state.awaiting_deps_artifacts.remove(artifact_name)
        self.CallFlow(
            # TODO(user): dependency loop with flows/general/collectors.py.
            # collectors.ArtifactCollectorFlow.__name__,
            "ArtifactCollectorFlow",
            artifact_list=[artifact_name],
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
        self.state.fulfilled_deps.add(partial)
        self._ScheduleCollection()

  def ProcessBase(self, responses):
    """Process any retrieved artifacts."""
    artifact_name = responses.request_data["artifact_name"]
    self.state.in_flight_artifacts.remove(artifact_name)
    self.state.completed_artifacts.add(artifact_name)

    if not responses.success:
      self.Log("Failed to get artifact %s. Status: %s", artifact_name,
               responses.status)
    else:
      deps = self.SetKBValue(responses.request_data["artifact_name"], responses)
      if deps:
        # If we fulfilled a dependency, make sure we have collected all
        # artifacts that provide the dependency before marking it as fulfilled.
        for dep in deps:
          required_artifacts = artifact_registry.REGISTRY.GetArtifactNames(
              os_name=self.state.knowledge_base.os, provides=[dep])
          if required_artifacts.issubset(self.state.completed_artifacts):
            self.state.fulfilled_deps.add(dep)
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
        missing_deps = list(
            self.state.all_deps.difference(self.state["fulfilled_deps"]))

        if self.args.require_complete:
          raise flow.FlowError(
              "KnowledgeBase initialization failed as the "
              "following artifacts had dependencies that could"
              " not be fulfilled %s. Missing: %s" % ([
                  utils.SmartStr(a) for a in self.state.awaiting_deps_artifacts
              ], missing_deps))
        else:
          self.Log("Storing incomplete KnowledgeBase. The following artifacts "
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
      if isinstance(response, rdf_anomaly.Anomaly):
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
          self.Log(
              "User merge conflict in %s. Old value: %s, "
              "Newly written value: %s", key, old_val, val)

      else:
        artifact_provides = artifact_obj.provides
        if isinstance(response, rdf_protodict.Dict):
          # Attempting to fulfil provides with a Dict response means we are
          # supporting multiple provides based on the keys of the dict.
          kb_dict = response.ToDict()
        elif len(artifact_provides) == 1:
          # If its not a dict we only support a single value.
          kb_dict = {artifact_provides[0]: response}
        elif not artifact_provides:
          raise ValueError("Artifact %s does not have a provide clause and "
                           "can't be used to populate a knowledge base value." %
                           artifact_obj)
        else:
          raise ValueError("Attempt to set a knowledge base value with "
                           "multiple provides clauses without using Dict."
                           ": %s" % artifact_obj)

        for provides, value in iteritems(kb_dict):
          if provides not in artifact_provides:
            raise ValueError("Attempt to provide knowledge base value %s "
                             "without this being set in the artifact "
                             "provides setting: %s" % (provides, artifact_obj))

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

  def End(self, responses):
    """Finish up."""
    del responses
    self.SendReply(self.state.knowledge_base)

  def GetFirstFlowsForCollection(self):
    """Initialize dependencies and calculate first round of flows.

    Returns:
      set of artifact names with no dependencies that should be collected first.

    Raises:
      RuntimeError: On bad artifact configuration parameters.
    """
    kb_base_set = set(config.CONFIG["Artifacts.knowledge_base"])
    kb_add = set(config.CONFIG["Artifacts.knowledge_base_additions"])
    kb_skip = set(config.CONFIG["Artifacts.knowledge_base_skip"])
    if self.args.lightweight:
      kb_skip.update(config.CONFIG["Artifacts.knowledge_base_heavyweight"])
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
    if data_store.AFF4Enabled():
      self.client = aff4.FACTORY.Open(self.client_id, token=self.token)

      # Always create a new KB to override any old values.
      self.state.knowledge_base = rdf_client.KnowledgeBase()
      SetCoreGRRKnowledgeBaseValues(self.state.knowledge_base, self.client)

      if not self.state.knowledge_base.os:
        # If we don't know what OS this is, there is no way to proceed.
        raise flow.FlowError("Client OS not set for: %s, cannot initialize"
                             " KnowledgeBase" % self.client_id)
    else:
      # Always create a new KB to override any old values but keep os and
      # version so we know which artifacts we can run.
      self.state.knowledge_base = rdf_client.KnowledgeBase()
      kb = data_store.REL_DB.ReadClientSnapshot(self.client_id).knowledge_base
      if kb:
        self.state.knowledge_base.os = kb.os
        self.state.knowledge_base.os_minor_version = kb.os_major_version
        self.state.knowledge_base.os_minor_version = kb.os_minor_version


def ApplyParsersToResponses(parser_factory, responses, flow_obj):
  """Parse responses with applicable parsers.

  Args:
    parser_factory: A parser factory for specific artifact.
    responses: A list of responses from the client.
    flow_obj: An artifact collection flow.

  Returns:
    A list of (possibly parsed) responses.
  """
  # We have some processors to run.
  knowledge_base = flow_obj.state.knowledge_base

  parsed_responses = []

  if parser_factory.HasSingleResponseParsers():
    for response in responses:
      for parser in parser_factory.SingleResponseParsers():
        parsed_responses.extend(
            parser.ParseResponse(knowledge_base, response,
                                 flow_obj.args.path_type))

  for parser in parser_factory.MultiResponseParsers():
    parsed_responses.extend(parser.ParseResponses(knowledge_base, responses))

  has_single_file_parsers = parser_factory.HasSingleFileParsers()
  has_multi_file_parsers = parser_factory.HasMultiFileParsers()

  if has_single_file_parsers or has_multi_file_parsers:
    precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)
    pathspecs = [response.pathspec for response in responses]
    if (data_store.RelationalDBReadEnabled("vfs") and
        data_store.RelationalDBReadEnabled("filestore")):
      # TODO(amoser): This is not super efficient, AFF4 provided an api to open
      # all pathspecs at the same time, investigate if optimizing this is worth
      # it.
      filedescs = []
      for pathspec in pathspecs:
        client_path = db.ClientPath.FromPathSpec(flow_obj.client_id, pathspec)
        filedescs.append(file_store.OpenFile(client_path))
    else:
      filedescs = MultiOpenAff4File(flow_obj, pathspecs)

  if has_single_file_parsers:
    for response, filedesc in zip(responses, filedescs):
      for parser in parser_factory.SingleFileParsers():
        parsed_responses.extend(
            parser.ParseFile(knowledge_base, response.pathspec, filedesc))

  if has_multi_file_parsers:
    for parser in parser_factory.MultiFileParsers():
      parsed_responses.extend(
          parser.ParseFiles(knowledge_base, pathspecs, filedescs))

  return parsed_responses or responses


ARTIFACT_STORE_ROOT_URN = aff4.ROOT_URN.Add("artifact_store")


def UploadArtifactYamlFile(file_content,
                           overwrite=True,
                           overwrite_system_artifacts=False):
  """Upload a yaml or json file as an artifact to the datastore."""
  loaded_artifacts = []
  registry_obj = artifact_registry.REGISTRY
  # Make sure all artifacts are loaded so we don't accidentally overwrite one.
  registry_obj.GetArtifacts(reload_datastore_artifacts=True)

  new_artifacts = registry_obj.ArtifactsFromYaml(file_content)
  new_artifact_names = set()
  # A quick syntax check before we upload anything.
  for artifact_value in new_artifacts:
    artifact_registry.ValidateSyntax(artifact_value)
    new_artifact_names.add(artifact_value.name)

  # Iterate through each artifact adding it to the collection.
  artifact_coll = artifact_registry.ArtifactCollection(ARTIFACT_STORE_ROOT_URN)
  current_artifacts = list(artifact_coll)

  # We need to remove artifacts we are overwriting.
  filtered_artifacts = [
      art for art in current_artifacts if art.name not in new_artifact_names
  ]

  artifact_coll.Delete()
  with data_store.DB.GetMutationPool() as pool:
    for artifact_value in filtered_artifacts:
      artifact_coll.Add(artifact_value, mutation_pool=pool)

    for artifact_value in new_artifacts:
      registry_obj.RegisterArtifact(
          artifact_value,
          source="datastore:%s" % ARTIFACT_STORE_ROOT_URN,
          overwrite_if_exists=overwrite,
          overwrite_system_artifacts=overwrite_system_artifacts)

      artifact_coll.Add(artifact_value, mutation_pool=pool)
      if data_store.RelationalDBWriteEnabled():
        data_store.REL_DB.WriteArtifact(artifact_value)

      loaded_artifacts.append(artifact_value)

      name = artifact_value.name
      logging.info("Uploaded artifact %s to %s", name, ARTIFACT_STORE_ROOT_URN)

  # Once all artifacts are loaded we can validate dependencies. Note that we do
  # not have to perform a syntax validation because it is already done after
  # YAML is parsed.
  for artifact_value in loaded_artifacts:
    artifact_registry.ValidateDependencies(artifact_value)


# TODO(hanuszczak): This function is not very elegant and should probably be
# placed in some other module. Or maybe it should be a method of the `Flow`
# class...?
def OpenAff4File(flow_obj, pathspec):
  aff4_path = pathspec.AFF4Path(flow_obj.client_urn)
  return aff4.FACTORY.Open(aff4_path, token=flow_obj.token)


# TODO(hanuszczak): Same as above.
def MultiOpenAff4File(flow_obj, pathspecs):
  aff4_paths = [_.AFF4Path(flow_obj.client_urn) for _ in pathspecs]
  return aff4.FACTORY.MultiOpenOrdered(aff4_paths, token=flow_obj.token)


class ArtifactLoader(registry.InitHook):
  """Loads artifacts from the datastore and from the filesystem.

  Datastore gets loaded second so it can override Artifacts in the files.
  """

  pre = [aff4.AFF4InitHook]

  def RunOnce(self):
    artifact_registry.REGISTRY.AddDefaultSources()
