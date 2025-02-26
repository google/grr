#!/usr/bin/env python
"""Flows for handling the collection for artifacts."""

import logging
from typing import Optional, Sequence

from google.protobuf import any_pb2
from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import mig_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_core.path_detection import windows as path_detection_windows
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import artifact
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import filesystem
from grr_response_server.flows.general import mig_transfer
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import mig_objects

# For file collection artifacts. pylint: disable=unused-import
# pylint: enable=unused-import
_MAX_DEBUG_RESPONSES_STRING_LENGTH = 100000


def _ReadClientKnowledgeBase(client_id, allow_uninitialized=False):
  client = data_store.REL_DB.ReadClientSnapshot(client_id)
  if client is not None:
    client = mig_objects.ToRDFClientSnapshot(client)
  return artifact.GetKnowledgeBase(
      client, allow_uninitialized=allow_uninitialized
  )


def _GetPathType(
    args: flows_pb2.ArtifactCollectorFlowArgs, client_os: str
) -> jobs_pb2.PathSpec.PathType:
  if args.use_raw_filesystem_access:
    if client_os == "Windows":
      return config.CONFIG["Server.raw_filesystem_access_pathtype"]
    else:
      return jobs_pb2.PathSpec.PathType.TSK
  else:
    return jobs_pb2.PathSpec.PathType.OS


def _GetImplementationType(
    args: flows_pb2.ArtifactCollectorFlowArgs,
) -> Optional["jobs_pb2.PathSpec.ImplementationType"]:
  if args.HasField("implementation_type"):
    return args.implementation_type
  return None


class ArtifactCollectorFlow(
    flow_base.FlowBase[
        flows_pb2.ArtifactCollectorFlowArgs,
        flows_pb2.ArtifactCollectorFlowStore,
    ]
):
  """Flow that takes a list of artifacts and collects them.

  This flow is the core of the Artifact implementation for GRR. Artifacts are
  defined using a standardized data format that includes what to collect and
  how to process the things collected. This flow takes that data driven format
  and makes it useful.

  The core functionality of Artifacts is split into ArtifactSources and
  Processors.

  An Artifact defines a set of ArtifactSources that are used to retrieve data
  from the client. These can specify collection of files, registry keys, command
  output and others. The first part of this flow "Collect" handles running those
  collections by issuing GRR flows and client actions.

  The results of those are then collected and GRR searches for Processors that
  know how to process the output of the ArtifactSources.

  So this flow hands off the collected rdfvalue results to the Processors which
  then return modified or different rdfvalues. These final results are then
  either:
  1. Sent to the calling flow.
  2. Written to a collection.
  """

  category = "/Collectors/"
  args_type = rdf_artifacts.ArtifactCollectorFlowArgs
  proto_args_type = flows_pb2.ArtifactCollectorFlowArgs

  progress_type = rdf_artifacts.ArtifactCollectorFlowProgress
  proto_progress_type = flows_pb2.ArtifactCollectorFlowProgress

  proto_store_type = flows_pb2.ArtifactCollectorFlowStore

  only_protos_allowed = True

  result_types = (
      rdf_protodict.Dict,
      rdf_client_fs.StatEntry,
      rdf_client_action.ExecuteResponse,
      # ArtifactCollectorFlow has many more result types. For now, only result
      # types required for UI type generation are captured here, add other
      # types when needed.
      rdfvalue.RDFValue,
  )
  proto_result_types = (
      jobs_pb2.StatEntry,
      jobs_pb2.ExecuteResponse,
      jobs_pb2.Dict,
  )
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """For each artifact, create subflows for each collector."""
    # We only want to copy if it is set and not empty.
    # ListFields returns a list of fields that are set (if empty list, we copy).
    if (
        self.proto_args.HasField("knowledge_base")
        and self.proto_args.knowledge_base.ListFields()
    ):
      self.store.knowledge_base.CopyFrom(self.proto_args.knowledge_base)
    self.progress = flows_pb2.ArtifactCollectorFlowProgress()

    if (
        self.proto_args.dependencies
        == flows_pb2.ArtifactCollectorFlowArgs.Dependency.FETCH_NOW
    ):
      # String due to dependency loop with discover.py.
      self.CallFlowProto(
          "Interrogate", next_state=self.StartCollection.__name__
      )
      return

    elif (
        self.proto_args.dependencies
        == flows_pb2.ArtifactCollectorFlowArgs.Dependency.USE_CACHED
    ) and (not self.store.HasField("knowledge_base")):
      # If not provided, get a knowledge base from the client.
      try:
        kb = mig_client.ToProtoKnowledgeBase(
            _ReadClientKnowledgeBase(self.client_id)
        )
        self.store.knowledge_base.CopyFrom(kb)
      except artifact_utils.KnowledgeBaseUninitializedError:
        # If no-one has ever initialized the knowledge base, we should do so
        # now.
        # String due to dependency loop with discover.py.
        self.CallFlowProto(
            "Interrogate", next_state=self.StartCollection.__name__
        )
        return

    # In all other cases start the collection state.
    self.CallStateProto(next_state=self.StartCollection.__name__)

  def _GetArtifactFromName(self, name):
    """Gets an artifact from the registry, refreshing the registry if needed."""
    try:
      return artifact_registry.REGISTRY.GetArtifact(name)
    except rdf_artifacts.ArtifactNotRegisteredError:
      # If we don't have an artifact, things shouldn't have passed validation
      # so we assume it's a new one in the datastore.
      artifact_registry.REGISTRY.ReloadDatastoreArtifacts()
      return artifact_registry.REGISTRY.GetArtifact(name)

  @flow_base.UseProto2AnyResponses
  def StartCollection(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Start collecting."""
    if not responses.success:
      raise artifact_utils.KnowledgeBaseUninitializedError(
          "Attempt to initialize Knowledge Base failed."
      )

    if not self.store.knowledge_base:
      self.store.knowledge_base.CopyFrom(
          mig_client.ToProtoKnowledgeBase(
              _ReadClientKnowledgeBase(self.client_id, allow_uninitialized=True)
          )
      )

    for artifact_name in self.proto_args.artifact_list:
      artifact_obj = self._GetArtifactFromName(artifact_name)

      # Ensure artifact has been written sanely. Note that this could be
      # removed if it turns out to be expensive. Artifact tests should catch
      # these.
      artifact_registry.Validate(artifact_obj)

      self._Collect(artifact_obj)

  def _Collect(self, artifact_obj: rdf_artifacts.Artifact) -> None:
    """Collect the raw data from the client for this artifact."""
    artifact_name = artifact_obj.name

    # Ensure attempted artifacts are shown in progress, even with 0 results.
    progress = self._GetOrInsertArtifactProgress(artifact_name)

    if not MeetsOSConditions(self.store.knowledge_base, artifact_obj):
      logging.debug(
          "%s: Artifact %s not supported on os %s (options %s)",
          self.client_id,
          artifact_name,
          self.store.knowledge_base.os,
          artifact_obj.supported_os,
      )
      progress.status = (
          flows_pb2.ArtifactProgress.Status.SKIPPED_DUE_TO_OS_CONDITION
      )
      return

    sources_ran = 0
    # Call the source defined action for each source.
    for source in artifact_obj.sources:
      if not MeetsOSConditions(self.store.knowledge_base, source):
        continue

      sources_ran += 1

      type_name = source.type
      source_type = rdf_artifacts.ArtifactSource.SourceType
      self.current_artifact_name = artifact_name
      if type_name == source_type.COMMAND:
        self._RunCommand(source)
      elif type_name == source_type.PATH:
        self._GetPaths(
            source,
            _GetPathType(self.proto_args, self.client_os),
            _GetImplementationType(self.proto_args),
            flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.STAT
            ),
        )
      elif type_name == source_type.FILE:
        self._GetPaths(
            source,
            _GetPathType(self.proto_args, self.client_os),
            _GetImplementationType(self.proto_args),
            flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD,
                download=flows_pb2.FileFinderDownloadActionOptions(
                    max_size=self.proto_args.max_file_size
                    if self.proto_args.HasField("max_file_size")
                    else 500000000,  # Defaults to 500 MB
                ),
            ),
        )
      elif type_name == source_type.REGISTRY_KEY:
        self._GetRegistryKey(source)
      elif type_name == source_type.REGISTRY_VALUE:
        self._GetRegistryValue(source)
      elif type_name == source_type.WMI:
        self._WMIQuery(source)
      elif type_name == source_type.ARTIFACT_GROUP:
        self._CollectArtifacts(source)
      else:
        raise RuntimeError("Invalid type %s in %s" % (type_name, artifact_name))

    if sources_ran == 0:
      logging.debug(
          "Artifact %s no sources run due to all sources "
          "having failing conditions on %s",
          artifact_name,
          self.client_id,
      )

  def _GetPaths(
      self,
      source: rdf_artifacts.ArtifactSource,
      path_type: jobs_pb2.PathSpec.PathType,
      implementation_type: Optional["jobs_pb2.PathSpec.ImplementationType"],
      action: flows_pb2.FileFinderAction,
  ):
    """Get a set of files."""
    flow_args = flows_pb2.FileFinderArgs(
        paths=self._InterpolateList(source.attributes.get("paths", [])),
        pathtype=path_type,
        action=action,
    )
    if implementation_type is not None:
      flow_args.implementation_type = implementation_type
    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=flow_args,
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessFileFinderResults.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessFileFinderResults(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Process the results of a file finder flow."""
    if not responses.success:
      self.Log(
          "Failed to fetch files %s" % responses.request_data["artifact_name"]
      )
    else:
      stat_entries = []
      for r in responses:
        result = flows_pb2.FileFinderResult()
        r.Unpack(result)
        if result.HasField("stat_entry"):
          stat_entries.append(result.stat_entry)
      self.CallStateInlineProto(
          next_state=self.ProcessCollected.__name__,
          request_data=responses.request_data,
          messages=stat_entries,
      )

  def _GetRegistryKey(self, source: rdf_artifacts.ArtifactSource) -> None:
    self.CallFlowProto(
        file_finder.ClientFileFinder.__name__,
        flow_args=mig_file_finder.ToProtoFileFinderArgs(
            rdf_file_finder.FileFinderArgs(
                paths=self._InterpolateList(source.attributes.get("keys", [])),
                pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                action=rdf_file_finder.FileFinderAction.Stat(),
            )
        ),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessFileFinderKeys.__name__,
    )

  def _GetRegistryValue(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Retrieve directly specified registry values, returning Stat objects."""
    new_paths = set()
    has_glob = False
    for kvdict in source.attributes["key_value_pairs"]:
      if "*" in kvdict["key"] or rdf_paths.GROUPING_PATTERN.search(
          kvdict["key"]
      ):
        has_glob = True

      if kvdict["value"]:
        # This currently only supports key value pairs specified using forward
        # slash.
        path = "\\".join((kvdict["key"], kvdict["value"]))
      else:
        # If value is not set, we want to get the default value. In
        # GRR this is done by specifying the key only, so this is what
        # we do here.
        path = kvdict["key"]

      interpolation = artifact_utils.KnowledgeBaseInterpolation(
          pattern=path,
          kb=self.store.knowledge_base,
      )

      for log in interpolation.logs:
        self.Log("knowledgebase registry path interpolation: %s", log)

      if (
          not interpolation.results
          and not self.proto_args.ignore_interpolation_errors
      ):
        raise flow_base.FlowError(f"Registry path {path!r} interpolation error")

      new_paths.update(interpolation.results)

    if has_glob:
      self.CallFlowProto(
          file_finder.ClientFileFinder.__name__,
          flow_args=mig_file_finder.ToProtoFileFinderArgs(
              rdf_file_finder.FileFinderArgs(
                  paths=new_paths,
                  pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
                  action=rdf_file_finder.FileFinderAction.Stat(),
              )
          ),
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessFileFinderKeys.__name__,
      )
    else:
      # We call statfile directly for keys that don't include globs because it
      # is faster and some artifacts rely on getting an IOError to trigger
      # fallback processing.
      for new_path in new_paths:
        pathspec = jobs_pb2.PathSpec(
            path=new_path, pathtype=jobs_pb2.PathSpec.PathType.REGISTRY
        )

        self.CallClientProto(
            server_stubs.GetFileStat,
            jobs_pb2.GetFileStatRequest(pathspec=pathspec),
            request_data={
                "artifact_name": self.current_artifact_name,
                "source": source.ToPrimitiveDict(),
            },
            next_state=self.ProcessCollectedRegistryStatEntry.__name__,
        )

  @flow_base.UseProto2AnyResponses
  def ProcessFileFinderKeys(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log(
          "Failed to fetch keys %s" % responses.request_data["artifact_name"]
      )
    # We're only interested in the `StatEntry`s, not  `FileFinderResult`s.
    stat_entries = []
    for r in responses:
      result = flows_pb2.FileFinderResult()
      r.Unpack(result)
      if result.HasField("stat_entry"):
        stat_entries.append(result.stat_entry)
    if stat_entries:
      self.CallStateInlineProto(
          next_state=self.ProcessCollected.__name__,
          request_data=responses.request_data,
          messages=stat_entries,
      )

  def _StartSubArtifactCollector(
      self,
      artifact_list: Sequence[rdf_artifacts.ArtifactName],
      source: rdf_artifacts.ArtifactSource,
      next_state: str,
  ) -> None:
    self.CallFlowProto(
        ArtifactCollectorFlow.__name__,
        flow_args=mig_artifacts.ToProtoArtifactCollectorFlowArgs(
            rdf_artifacts.ArtifactCollectorFlowArgs(
                artifact_list=artifact_list,
                use_raw_filesystem_access=self.args.use_raw_filesystem_access,
                implementation_type=self.args.implementation_type,
                max_file_size=self.args.max_file_size,
                ignore_interpolation_errors=self.args.ignore_interpolation_errors,
                dependencies=self.args.dependencies,
                knowledge_base=self.args.knowledge_base,
            )
        ),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=next_state,
    )

  def _CollectArtifacts(self, source: rdf_artifacts.ArtifactSource) -> None:
    self._StartSubArtifactCollector(
        artifact_list=source.attributes["names"],
        source=source,
        next_state=self.ProcessCollected.__name__,
    )

  def _RunCommand(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Run a command."""
    self.CallClientProto(
        server_stubs.ExecuteCommand,
        jobs_pb2.ExecuteRequest(
            cmd=source.attributes["cmd"],
            args=source.attributes.get("args", []),
        ),
        request_data={
            "artifact_name": self.current_artifact_name,
            "source": source.ToPrimitiveDict(),
        },
        next_state=self.ProcessCollected.__name__,
    )

  def _WMIQuery(self, source: rdf_artifacts.ArtifactSource) -> None:
    """Run a Windows WMI Query."""
    query = source.attributes["query"]
    queries = self._Interpolate(query)
    base_object = source.attributes.get("base_object")
    for query in queries:
      self.CallClientProto(
          server_stubs.WmiQuery,
          jobs_pb2.WMIRequest(
              query=query,
              base_object=base_object,
          ),
          request_data={
              "artifact_name": self.current_artifact_name,
              "source": source.ToPrimitiveDict(),
          },
          next_state=self.ProcessCollected.__name__,
      )

  def _InterpolateList(self, input_list: Sequence[str]):
    """Interpolate all items from a given source array.

    Args:
      input_list: list of values to interpolate

    Returns:
      original list of values extended with strings interpolated
    """
    new_args = []
    for value in input_list:
      if isinstance(value, str) or isinstance(value, bytes):
        results = self._Interpolate(value)

        new_args.extend(results)
      else:
        new_args.extend(value)
    return new_args

  def _Interpolate(
      self,
      pattern: str,
  ) -> Sequence[str]:
    """Performs a knowledgebase interpolation.

    Args:
      pattern: A pattern to interpolate.

    Returns:
      A list of possible interpolation results.
    """
    interpolation = artifact_utils.KnowledgeBaseInterpolation(
        pattern=pattern,
        kb=self.store.knowledge_base,
    )

    for log in interpolation.logs:
      self.Log("knowledgebase interpolation: %s", log)

    if not interpolation.results:
      if not self.proto_args.ignore_interpolation_errors:
        raise flow_base.FlowError(f"{pattern} interpolation error")

    return interpolation.results

  @flow_base.UseProto2AnyResponses
  def ProcessCollected(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Each individual collector will call back into here.

    Args:
      responses: Responses from the collection.

    Raises:
      artifact_utils.ArtifactDefinitionError: On bad definition.
      artifact_utils.ArtifactProcessingError: On failure to process.
    """
    flow_name = self.__class__.__name__
    artifact_name = str(responses.request_data["artifact_name"])

    progress = self._GetOrInsertArtifactProgress(artifact_name)

    if responses.success:
      self.Log(
          "Artifact data collection %s completed successfully in flow %s "
          "with %d responses",
          artifact_name,
          flow_name,
          len(responses),
      )
      progress.status = flows_pb2.ArtifactProgress.Status.SUCCESS
    else:
      self.Log(
          "Artifact %s data collection failed. Status: %s.",
          artifact_name,
          responses.status,
      )
      progress.status = flows_pb2.ArtifactProgress.Status.FAILURE

    # Increment artifact result count in flow progress.
    progress.num_results += len(responses)

    skipped_result_types = set()

    for result in responses:
      # All paths should lead to this "sink" state. Right now, we are not sure
      # from which path we were called, so we need to check the type of the
      # result and unpack it before moving on.
      # Here's the current map of callers:
      #   * CollectArtifacts (sub artifact collector) - One of the ones below
      #   * ProcessFileFinderResults - jobs_pb2.StatEntry
      #   * ProcessFileFinderKeys - jobs_pb2.StatEntry
      #   * RunCommand - jobs_pb2.ExecuteResponse
      #   * WMIQuery - jobs_pb2.Dict
      #   * ProcessCollectedRegistryStatEntry - jobs_pb2.StatEntry
      #   * ProcessCollectedArtifactFiles/MultiGetFile - jobs_pb2.StatEntry
      if result.Is(jobs_pb2.StatEntry.DESCRIPTOR):
        unpacked_result = jobs_pb2.StatEntry()
      elif result.Is(jobs_pb2.ExecuteResponse.DESCRIPTOR):
        unpacked_result = jobs_pb2.ExecuteResponse()
      elif result.Is(jobs_pb2.Dict.DESCRIPTOR):
        unpacked_result = jobs_pb2.Dict()
      else:
        skipped_result_types.add(result.type_url)
        continue

      result.Unpack(unpacked_result)
      self.SendReplyProto(unpacked_result, tag=f"artifact:{artifact_name}")

    if skipped_result_types:
      self.Error(
          "Skipped unrecognized result types: %s",
          ", ".join(skipped_result_types),
      )

  @flow_base.UseProto2AnyResponses
  def ProcessCollectedRegistryStatEntry(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Create AFF4 objects for registry statentries.

    We need to do this explicitly because we call StatFile client action
    directly for performance reasons rather than using one of the flows that do
    this step automatically.

    Args:
      responses: Response objects from the artifact source.
    """
    if not responses.success:
      self.CallStateInlineProtoWithResponses(
          next_state=self.ProcessCollected.__name__, responses=responses
      )
      return

    stat_entries = []
    rdf_stat_entries = []
    for response in responses:
      result = jobs_pb2.StatEntry()
      response.Unpack(result)
      stat_entries.append(result)
      rdf_stat_entries.append(mig_client_fs.ToRDFStatEntry(result))
    filesystem.WriteStatEntries(rdf_stat_entries, client_id=self.client_id)

    self.CallStateInlineProto(
        next_state=self.ProcessCollected.__name__,
        request_data=responses.request_data,
        messages=stat_entries,
    )

  def ProcessCollectedArtifactFiles(self, responses):
    """Schedule files for download based on pathspec attribute.

    Args:
      responses: Response objects from the artifact source.

    Raises:
      RuntimeError: if pathspec value is not a PathSpec instance and not
                    a str.
    """
    self.download_list = []
    for response in responses:
      pathspec = response

      # Check the default .pathspec attribute.
      if not isinstance(pathspec, rdf_paths.PathSpec):
        try:
          pathspec = response.pathspec
        except AttributeError:
          pass

      if isinstance(pathspec, str):
        pathspec = rdf_paths.PathSpec(path=pathspec)

      if isinstance(pathspec, rdf_paths.PathSpec):
        if not pathspec.path:
          self.Log("Skipping empty pathspec.")
          continue
        if self.proto_args.use_raw_filesystem_access:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.TSK
        else:
          pathspec.pathtype = rdf_paths.PathSpec.PathType.OS

        self.download_list.append(pathspec)

      else:
        raise RuntimeError(
            "Response must be a string path, a pathspec, or have "
            "pathspec_attribute set. Got: %s" % pathspec
        )

    if self.download_list:
      request_data = responses.request_data.ToDict()
      self.CallFlowProto(
          transfer.MultiGetFile.__name__,
          flow_args=mig_transfer.ToProtoMultiGetFileArgs(
              transfer.MultiGetFileArgs(
                  pathspecs=self.download_list,
                  request_data=request_data,
              )
          ),
          next_state=self.ProcessCollected.__name__,
      )
    else:
      self.Log("No files to download")

  # TODO: Remove this method.
  def GetProgress(self) -> rdf_artifacts.ArtifactCollectorFlowProgress:
    return mig_artifacts.ToRDFArtifactCollectorFlowProgress(self.progress)

  def GetProgressProto(self) -> flows_pb2.ArtifactCollectorFlowProgress:
    return self.progress

  def _GetOrInsertArtifactProgress(
      self, name: rdf_artifacts.ArtifactName
  ) -> flows_pb2.ArtifactProgress:
    name = str(name)
    try:
      return next(
          a for a in self.GetProgressProto().artifacts if a.name == name
      )
    except StopIteration:
      progress = flows_pb2.ArtifactProgress(name=name)
      self.GetProgressProto().artifacts.append(progress)
      return progress

  def _ReceivedAnyResult(self) -> bool:
    for artifact_progress in self.GetProgressProto().artifacts:
      if artifact_progress.num_results > 0:
        return True
    return False

  def End(self) -> None:
    # If we got no responses, and user asked for it, we error out.
    if self.proto_args.error_on_no_results and not self._ReceivedAnyResult():
      raise artifact_utils.ArtifactProcessingError(
          "Artifact collector returned 0 responses."
      )


class ArtifactFilesDownloaderFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderFlowArgs
  rdf_deps = [
      rdf_artifacts.ArtifactName,
      rdfvalue.ByteSize,
  ]


class ArtifactFilesDownloaderResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactFilesDownloaderResult
  rdf_deps = [
      rdf_paths.PathSpec,
      rdf_client_fs.StatEntry,
  ]

  def GetOriginalResultType(self):
    if self.HasField("original_result_type"):
      return rdfvalue.RDFValue.classes.get(self.original_result_type)


class ArtifactFilesDownloaderFlow(
    transfer.MultiGetFileLogic, flow_base.FlowBase
):
  """Flow that downloads files referenced by collected artifacts."""

  category = "/Collectors/"
  args_type = ArtifactFilesDownloaderFlowArgs
  result_types = (ArtifactFilesDownloaderResult,)

  def _FindMatchingPathspecs(self, response):
    # If we're dealing with plain file StatEntry, just
    # return it's pathspec - there's nothing to parse
    # and guess.
    if isinstance(response, rdf_client_fs.StatEntry):
      if response.pathspec.pathtype in [
          rdf_paths.PathSpec.PathType.TSK,
          rdf_paths.PathSpec.PathType.OS,
          rdf_paths.PathSpec.PathType.NTFS,
      ]:
        yield response.pathspec

      if response.pathspec.pathtype in [
          rdf_paths.PathSpec.PathType.REGISTRY,
      ]:
        knowledge_base = _ReadClientKnowledgeBase(self.client_id)

        if self.args.use_raw_filesystem_access:
          path_type = rdf_paths.PathSpec.PathType.TSK
        else:
          path_type = rdf_paths.PathSpec.PathType.OS

        for path in path_detection_windows.DetectExecutablePaths(
            [response.registry_data.string],
            artifact_utils.GetWindowsEnvironmentVariablesMap(knowledge_base),
        ):
          yield rdf_paths.PathSpec(path=path, pathtype=path_type)

  def Start(self):
    super().Start()

    self.state.file_size = self.args.max_file_size
    self.state.results_to_download = []

    if self.args.HasField("implementation_type"):
      implementation_type = self.args.implementation_type
    else:
      implementation_type = None

    self.CallFlow(
        ArtifactCollectorFlow.__name__,
        next_state=self._DownloadFiles.__name__,
        flow_args=rdf_artifacts.ArtifactCollectorFlowArgs(
            artifact_list=self.args.artifact_list,
            use_raw_filesystem_access=self.args.use_raw_filesystem_access,
            implementation_type=implementation_type,
            max_file_size=self.args.max_file_size,
        ),
    )

  def _DownloadFiles(self, responses):
    if not responses.success:
      self.Log("Failed to run ArtifactCollectorFlow: %s", responses.status)
      return

    results_with_pathspecs = []
    results_without_pathspecs = []
    for response in responses:
      pathspecs = list(self._FindMatchingPathspecs(response))
      if pathspecs:
        for pathspec in pathspecs:
          result = ArtifactFilesDownloaderResult(
              original_result_type=response.__class__.__name__,
              original_result=response,
              found_pathspec=pathspec,
          )
          results_with_pathspecs.append(result)
      else:
        result = ArtifactFilesDownloaderResult(
            original_result_type=response.__class__.__name__,
            original_result=response,
        )
        results_without_pathspecs.append(result)

    grouped_results = collection.Group(
        results_with_pathspecs, lambda x: x.found_pathspec.CollapsePath()
    )
    for _, group in grouped_results.items():
      self.StartFileFetch(
          group[0].found_pathspec, request_data=dict(results=group)
      )

    for result in results_without_pathspecs:
      self.SendReply(result)

  def ReceiveFetchedFile(
      self, stat_entry, file_hash, request_data=None, is_duplicate=False
  ):
    """See MultiGetFileLogic."""
    del is_duplicate  # Unused.

    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    for result in request_data["results"]:
      result.downloaded_file = stat_entry
      self.SendReply(result)

  def FileFetchFailed(self, pathspec, request_data=None, status=None):
    """See MultiGetFileLogic."""
    if not request_data:
      raise RuntimeError("Expected non-empty request_data")

    for result in request_data["results"]:
      self.SendReply(result)


def MeetsOSConditions(knowledge_base, source):
  """Check supported OS on the source."""
  if source.supported_os and knowledge_base.os not in source.supported_os:
    return False

  return True
