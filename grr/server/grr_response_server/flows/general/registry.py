#!/usr/bin/env python
"""Gather information from the registry on windows."""

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.path_detection import windows as path_detection_windows
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import transfer


class RegistryFinderCondition(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderCondition
  rdf_deps = [
      rdf_file_finder.FileFinderContentsLiteralMatchCondition,
      rdf_file_finder.FileFinderContentsRegexMatchCondition,
      rdf_file_finder.FileFinderModificationTimeCondition,
      rdf_file_finder.FileFinderSizeCondition,
  ]


class RegistryFinderArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RegistryFinderArgs
  rdf_deps = [
      rdf_paths.GlobExpression,
      RegistryFinderCondition,
  ]


def _ConditionsToFileFinderConditions(conditions):
  """Converts FileFinderSizeConditions to RegistryFinderConditions."""
  ff_condition_type_cls = rdf_file_finder.FileFinderCondition.Type
  result = []
  for c in conditions:
    if c.condition_type == RegistryFinderCondition.Type.MODIFICATION_TIME:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.MODIFICATION_TIME,
              modification_time=c.modification_time))
    elif c.condition_type == RegistryFinderCondition.Type.VALUE_LITERAL_MATCH:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.CONTENTS_LITERAL_MATCH,
              contents_literal_match=c.value_literal_match))
    elif c.condition_type == RegistryFinderCondition.Type.VALUE_REGEX_MATCH:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.CONTENTS_REGEX_MATCH,
              contents_regex_match=c.value_regex_match))
    elif c.condition_type == RegistryFinderCondition.Type.SIZE:
      result.append(
          rdf_file_finder.FileFinderCondition(
              condition_type=ff_condition_type_cls.SIZE, size=c.size))
    else:
      raise ValueError("Unknown condition type: %s" % c.condition_type)

  return result


class RegistryFinder(flow_base.FlowBase):
  """This flow looks for registry items matching given criteria."""

  friendly_name = "Registry Finder"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow_base.BEHAVIOUR_BASIC

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    return cls.args_type(keys_paths=[
        "HKEY_USERS/%%users.sid%%/Software/"
        "Microsoft/Windows/CurrentVersion/Run/*"
    ])

  def Start(self):
    self.CallFlow(
        compatibility.GetName(file_finder.FileFinder),
        paths=self.args.keys_paths,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        conditions=_ConditionsToFileFinderConditions(self.args.conditions),
        action=rdf_file_finder.FileFinderAction.Stat(),
        next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Registry search failed %s" % responses.status)

    for response in responses:
      self.SendReply(response)


class ClientRegistryFinder(flow_base.FlowBase):
  """This flow looks for registry items matching given criteria."""

  friendly_name = "Client Side Registry Finder"
  category = "/Registry/"
  args_type = RegistryFinderArgs
  behaviours = flow_base.BEHAVIOUR_ADVANCED

  @classmethod
  def GetDefaultArgs(cls, username=None):
    del username
    return cls.args_type(
        keys_paths=["HKEY_LOCAL_MACHINE/SOFTWARE/Microsoft/Windows NT/*"])

  def Start(self):
    self.CallFlow(
        compatibility.GetName(file_finder.ClientFileFinder),
        paths=self.args.keys_paths,
        pathtype=rdf_paths.PathSpec.PathType.REGISTRY,
        conditions=_ConditionsToFileFinderConditions(self.args.conditions),
        action=rdf_file_finder.FileFinderAction.Stat(),
        next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Registry search failed %s" % responses.status)

    for response in responses:
      self.SendReply(response)


class CollectRunKeyBinaries(flow_base.FlowBase):
  """Collect the binaries used by Run and RunOnce keys on the system.

  We use the RunKeys artifact to get RunKey command strings for all users and
  System. This flow guesses file paths from the strings, expands any
  windows system environment variables, and attempts to retrieve the files.
  """
  category = "/Registry/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    """Get runkeys via the ArtifactCollectorFlow."""
    self.CallFlow(
        collectors.ArtifactCollectorFlow.__name__,
        artifact_list=["WindowsRunKeys"],
        use_raw_filesystem_access=True,
        next_state=compatibility.GetName(self.ParseRunKeys))

  def ParseRunKeys(self, responses):
    """Get filenames from the RunKeys and download the files."""
    filenames = []
    client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    kb = client.knowledge_base

    for response in responses:
      runkey = response.registry_data.string

      environ_vars = artifact_utils.GetWindowsEnvironmentVariablesMap(kb)
      path_guesses = path_detection_windows.DetectExecutablePaths([runkey],
                                                                  environ_vars)

      if not path_guesses:
        self.Log("Couldn't guess path for %s", runkey)

      for path in path_guesses:
        filenames.append(
            rdf_paths.PathSpec(
                path=path,
                pathtype=config.CONFIG["Server.raw_filesystem_access_pathtype"])
        )

    if filenames:
      self.CallFlow(
          transfer.MultiGetFile.__name__,
          pathspecs=filenames,
          next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    for response in responses:
      self.SendReply(response)
