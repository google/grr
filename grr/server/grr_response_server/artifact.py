#!/usr/bin/env python
# Lint as: python3
"""Base classes for artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_proto import flows_pb2
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server.databases import db


def GetKnowledgeBase(rdf_client_obj, allow_uninitialized=False):
  """Returns a knowledgebase from an rdf client object."""
  if not allow_uninitialized:
    if rdf_client_obj is None:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "No client snapshot given.")
    if rdf_client_obj.knowledge_base is None:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "KnowledgeBase empty for %s." % rdf_client_obj.client_id)
    kb = rdf_client_obj.knowledge_base
    if not kb.os:
      raise artifact_utils.KnowledgeBaseAttributesMissingError(
          "KnowledgeBase missing OS for %s. Knowledgebase content: %s" %
          (rdf_client_obj.client_id, kb))
  if rdf_client_obj is None or rdf_client_obj.knowledge_base is None:
    return rdf_client.KnowledgeBase()

  version = rdf_client_obj.os_version.split(".")
  kb = rdf_client_obj.knowledge_base
  try:
    kb.os_major_version = int(version[0])
    if len(version) > 1:
      kb.os_minor_version = int(version[1])
  except ValueError:
    pass

  return kb


class KnowledgeBaseInitializationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KnowledgeBaseInitializationArgs


class KnowledgeBaseInitializationFlow(flow_base.FlowBase):
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
  behaviours = flow_base.BEHAVIOUR_ADVANCED
  args_type = KnowledgeBaseInitializationArgs
  result_types = (rdf_client.KnowledgeBase,)

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
          next_state=compatibility.GetName(self.ProcessBase),
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
            next_state=compatibility.GetName(self.ProcessBase),
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
          raise flow_base.FlowError(
              "KnowledgeBase initialization failed as the "
              "following artifacts had dependencies that could"
              " not be fulfilled %s. Missing: %s" %
              ([str(a) for a in self.state.awaiting_deps_artifacts
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
        logging.info("Artifact %s returned an Anomaly: %s", artifact_name,
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
        continue

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

      for provides, value in kb_dict.items():
        if provides not in artifact_provides:
          raise ValueError("Attempt to provide knowledge base value %s "
                           "without this being set in the artifact "
                           "provides setting: %s" % (provides, artifact_obj))

        if hasattr(value, "registry_data"):
          value = value.registry_data.GetValue()

        if value:
          self.state.knowledge_base.Set(provides, value)
          provided.add(provides)

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
    # Always create a new KB to override any old values but keep os and
    # version so we know which artifacts we can run.
    self.state.knowledge_base = rdf_client.KnowledgeBase()
    snapshot = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    if not snapshot or not snapshot.knowledge_base:
      return

    kb = snapshot.knowledge_base
    state_kb = self.state.knowledge_base
    state_kb.os = kb.os
    state_kb.os_major_version = kb.os_major_version
    state_kb.os_minor_version = kb.os_minor_version

    if not state_kb.os_major_version and snapshot.os_version:
      version = snapshot.os_version.split(".")
      try:
        state_kb.os_major_version = int(version[0])
        if len(version) > 1:
          state_kb.os_minor_version = int(version[1])
      except ValueError:
        pass


class ParseResults(object):
  """A class representing results of parsing flow responses."""

  def __init__(self):
    self._responses = []  # type: List[rdfvalue.RDFValue]
    self._errors = []  # type: List[parsers.ParseError]

  def AddResponses(self, responses: Iterator[rdfvalue.RDFValue]) -> None:
    self._responses.extend(responses)

  def AddError(self, error: parsers.ParseError) -> None:
    self._errors.append(error)

  def Responses(self) -> Iterator[rdfvalue.RDFValue]:
    return iter(self._responses)

  def Errors(self) -> Iterator[parsers.ParseError]:
    return iter(self._errors)


class ParserApplicator(object):
  """An utility class for applying many parsers to responses."""

  def __init__(
      self,
      factory: parsers.ArtifactParserFactory,
      client_id: str,
      knowledge_base: rdf_client.KnowledgeBase,
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ):
    """Initializes the applicator.

    Args:
      factory: A parser factory that produces parsers to apply.
      client_id: An identifier of the client for which the responses were
        collected.
      knowledge_base: A knowledge base of the client from which the responses
        were collected.
      timestamp: An optional timestamp at which parsers should interpret the
        results. For example, parsers that depend on files, will receive content
        of files as it was at the given timestamp.
    """
    self._factory = factory
    self._client_id = client_id
    self._knowledge_base = knowledge_base
    self._timestamp = timestamp
    self._results = ParseResults()

  def Apply(self, responses: Sequence[rdfvalue.RDFValue]):
    """Applies all known parsers to the specified responses.

    Args:
      responses: A sequence of responses to apply the parsers to.
    """
    for response in responses:
      self._ApplySingleResponse(response)

    self._ApplyMultiResponse(responses)

    has_single_file_parsers = self._factory.HasSingleFileParsers()
    has_multi_file_parsers = self._factory.HasMultiFileParsers()

    if has_single_file_parsers or has_multi_file_parsers:
      precondition.AssertIterableType(responses, rdf_client_fs.StatEntry)
      pathspecs = [response.pathspec for response in responses]
      filedescs = [self._OpenFile(pathspec) for pathspec in pathspecs]

      for pathspec, filedesc in zip(pathspecs, filedescs):
        self._ApplySingleFile(pathspec, filedesc)

      self._ApplyMultiFile(pathspecs, filedescs)

  def Responses(self) -> Iterator[rdfvalue.RDFValue]:
    """Returns an iterator over all parsed responses."""
    yield from self._results.Responses()

  def Errors(self) -> Iterator[parsers.ParseError]:
    """Returns an iterator over errors that occurred during parsing."""
    yield from self._results.Errors()

  def _ApplySingleResponse(
      self,
      response: rdfvalue.RDFValue,
  ) -> None:
    """Applies all single-response parsers to the given response."""
    for parser in self._factory.SingleResponseParsers():
      try:
        results = parser.ParseResponse(self._knowledge_base, response)
        self._results.AddResponses(results)
      except parsers.ParseError as error:
        self._results.AddError(error)

  def _ApplyMultiResponse(
      self,
      responses: Iterable[rdfvalue.RDFValue],
  ) -> None:
    """Applies all multi-response parsers to the given responses."""
    for parser in self._factory.MultiResponseParsers():
      try:
        results = parser.ParseResponses(self._knowledge_base, responses)
        self._results.AddResponses(results)
      except parsers.ParseError as error:
        self._results.AddError(error)

  def _ApplySingleFile(
      self,
      pathspec: rdf_paths.PathSpec,
      filedesc: file_store.BlobStream,
  ) -> None:
    """Applies all single-file parsers to the given file."""
    for parser in self._factory.SingleFileParsers():
      try:
        results = parser.ParseFile(self._knowledge_base, pathspec, filedesc)
        self._results.AddResponses(results)
      except parsers.ParseError as error:
        self._results.AddError(error)

  def _ApplyMultiFile(
      self,
      pathspecs: Iterable[rdf_paths.PathSpec],
      filedescs: Iterable[file_store.BlobStream],
  ) -> None:
    """Applies all multi-file parsers to the given file."""
    for parser in self._factory.MultiFileParsers():
      try:
        results = parser.ParseFiles(self._knowledge_base, pathspecs, filedescs)
        self._results.AddResponses(results)
      except parsers.ParseError as error:
        self._results.AddError(error)

  def _OpenFile(self, pathspec: rdf_paths.PathSpec) -> file_store.BlobStream:
    # TODO(amoser): This is not super efficient, AFF4 provided an api to open
    # all pathspecs at the same time, investigate if optimizing this is worth
    # it.
    client_path = db.ClientPath.FromPathSpec(self._client_id, pathspec)
    return file_store.OpenFile(client_path, max_timestamp=self._timestamp)


def ApplyParsersToResponses(parser_factory, responses, flow_obj):
  """Parse responses with applicable parsers.

  Args:
    parser_factory: A parser factory for specific artifact.
    responses: A list of responses from the client.
    flow_obj: An artifact collection flow.

  Returns:
    A list of (possibly parsed) responses.
  """
  if not parser_factory.HasParsers():
    # If we don't have any parsers, we expect to use the unparsed responses.
    return responses

  knowledge_base = flow_obj.state.knowledge_base
  client_id = flow_obj.client_id

  applicator = ParserApplicator(parser_factory, client_id, knowledge_base)
  applicator.Apply(responses)

  for error in applicator.Errors():
    flow_obj.Log("Error encountered when parsing responses: %s", error)

  return list(applicator.Responses())


def UploadArtifactYamlFile(file_content,
                           overwrite=True,
                           overwrite_system_artifacts=False):
  """Upload a yaml or json file as an artifact to the datastore."""
  loaded_artifacts = []
  registry_obj = artifact_registry.REGISTRY

  # Make sure all artifacts are loaded so we don't accidentally overwrite one.
  registry_obj.GetArtifacts(reload_datastore_artifacts=True)

  new_artifacts = registry_obj.ArtifactsFromYaml(file_content)

  # A quick syntax check before we upload anything.
  for artifact_value in new_artifacts:
    artifact_registry.ValidateSyntax(artifact_value)

  for artifact_value in new_artifacts:
    registry_obj.RegisterArtifact(
        artifact_value,
        source="datastore",
        overwrite_if_exists=overwrite,
        overwrite_system_artifacts=overwrite_system_artifacts)

    data_store.REL_DB.WriteArtifact(artifact_value)

    loaded_artifacts.append(artifact_value)

    name = artifact_value.name
    logging.info("Uploaded artifact %s.", name)

  # Once all artifacts are loaded we can validate dependencies. Note that we do
  # not have to perform a syntax validation because it is already done after
  # YAML is parsed.
  for artifact_value in loaded_artifacts:
    artifact_registry.ValidateDependencies(artifact_value)


@utils.RunOnce
def LoadArtifactsOnce():
  """Loads artifacts from the datastore and from the filesystem.

  Datastore gets loaded second so it can override Artifacts in the files.
  """
  artifact_registry.REGISTRY.AddDefaultSources()
