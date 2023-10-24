#!/usr/bin/env python
"""Base classes for artifacts."""
import logging
import ntpath
import os
import pathlib
import stat
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
from grr_response_core.lib.parsers import linux_release_parser
from grr_response_core.lib.parsers import windows_registry_parser
from grr_response_core.lib.rdfvalues import anomaly as rdf_anomaly
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
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
          next_state=self.ProcessBase.__name__,
          request_data={"artifact_name": artifact_name})

    if self.client_os == "Linux":
      if artifact_registry.REGISTRY.Exists("LinuxReleaseInfo"):
        self.CallFlow(
            "ArtifactCollectorFlow",
            artifact_list=["LinuxReleaseInfo"],
            knowledge_base=self.state.knowledge_base,
            next_state=self._ProcessLinuxReleaseInfo.__name__,
        )
      else:
        self.Log("`LinuxReleaseInfo` artifact not found, skipping...")

      self.CallClient(
          server_stubs.EnumerateUsers,
          next_state=self._ProcessLinuxEnumerateUsers.__name__,
      )
    elif self.client_os == "Darwin":
      list_users_dir_request = rdf_client_action.ListDirRequest()
      list_users_dir_request.pathspec.pathtype = rdf_paths.PathSpec.PathType.OS
      list_users_dir_request.pathspec.path = "/Users"

      self.CallClient(
          server_stubs.ListDirectory,
          request=list_users_dir_request,
          next_state=self._ProcessMacosListUsersDirectory.__name__,
      )
    elif self.client_os == "Windows":
      # pylint: disable=line-too-long
      # pyformat: disable
      #
      # TODO: There is no dedicated action for obtaining registry
      # values. The existing artifact collector uses `GetFileStat` action for
      # this which is horrible.
      args = rdf_client_action.GetFileStatRequest()
      args.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\SystemRoot"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvSystemRoot.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\ProgramFilesDir"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvProgramFilesDir.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\ProgramFilesDir (x86)"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvProgramFilesDirX86.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\CommonFilesDir"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvCommonFilesDir.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\CommonFilesDir (x86)"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvCommonFilesDirX86.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\ProgramData"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvProgramData.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment\DriverData"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvDriverData.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\Select\Current"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsCurrentControlSet.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Nls\CodePage\ACP"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsCodePage.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Services\Tcpip\Parameters\Domain"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsDomain.__name__,
      )

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\TimeZoneInformation\TimeZoneKeyName"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsTimeZoneKeyName.__name__,
      )

      args = rdf_file_finder.FileFinderArgs()
      # TODO: There is no dedicated action for obtaining registry
      # values but `STAT` action of the file-finder will get it. This should be
      # refactored once registry-specific actions are available.
      args.action.action_type = rdf_file_finder.FileFinderAction.Action.STAT
      args.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
      args.paths = [r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\*\ProfileImagePath"]
      self.CallClient(
          server_stubs.VfsFileFinder,
          args,
          next_state=self._ProcessWindowsProfiles.__name__,
      )
      # TODO: We pretend that `WindowsRegistryProfiles` is being
      # collected to avoid issues with the flow failing due its dependees not
      # being possible to satisfy. Once the dependees are refactored not to be
      # artifacts this can be removed.
      self.state.in_flight_artifacts.add("WindowsRegistryProfiles")
      # pylint: enable=line-too-long
      # pyformat: enable

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
            next_state=self.ProcessBase.__name__,
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

  def _ProcessLinuxReleaseInfo(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to get Linux release information: %s", responses.status)
      return

    knowledge_base = self.state.knowledge_base

    pathspecs: list[rdf_paths.PathSpec] = []
    files: list[file_store.BlobStream] = []

    for response in responses:
      if not isinstance(response, rdf_client_fs.StatEntry):
        self.Log("Unexpected response type: '%s'", type(response))
        continue

      path = db.ClientPath.FromPathSpec(self.client_id, response.pathspec)

      pathspecs.append(response.pathspec)
      files.append(file_store.OpenFile(path))

    parser = linux_release_parser.LinuxReleaseParser()

    for info in parser.ParseFiles(knowledge_base, pathspecs, files):
      # The parser can sometimes yield an anomaly object.
      if not (isinstance(info, dict) or isinstance(info, rdf_protodict.Dict)):
        self.Log("Invalid release information: %s", info)
        continue

      if os_release := info.get("os_release"):
        self.state.knowledge_base.os_release = os_release

      if os_major_version := info.get("os_major_version"):
        self.state.knowledge_base.os_major_version = os_major_version

      if os_minor_version := info.get("os_minor_version"):
        self.state.knowledge_base.os_minor_version = os_minor_version

  def _ProcessLinuxEnumerateUsers(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to enumerate Linux users: %s", responses.status)
      return

    for response in responses:
      if not isinstance(response, rdf_client.User):
        self.Log("Unexpected response type: '%s'", type(response))
        continue

      self.state.knowledge_base.MergeOrAddUser(response)

  def _ProcessMacosListUsersDirectory(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to list macOS users directory: %s", responses.status)
      return

    for response in responses:
      if not isinstance(response, rdf_client_fs.StatEntry):
        self.Log("Unexpected response type: '%s'", type(response))
        continue

      # TODO: `st_mode` should be an `int`, not `StatMode`.
      if not stat.S_ISDIR(int(response.st_mode)):
        self.Log("Unexpected users directory entry mode: %s", response.st_mode)
        continue

      username = os.path.basename(response.pathspec.path)
      if username == "Shared":
        # `Shared` is a special entry in the `Users` directory that we do not
        # want to report as an actual user.
        continue

      user = rdf_client.User()
      user.username = username
      user.homedir = response.pathspec.path
      self.state.knowledge_base.MergeOrAddUser(user)

  def _ProcessWindowsEnvSystemRoot(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%SystemRoot%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    system_root = response.registry_data.string
    system_drive = pathlib.PureWindowsPath(system_root).drive

    self.state.knowledge_base.environ_systemroot = system_root
    self.state.knowledge_base.environ_systemdrive = system_drive

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_systemroot")
    self.state.fulfilled_deps.add("environ_systemdrive")

    # pylint: disable=line-too-long
    # pyformat: disable
    #
    # TODO: The following values depend on `SystemRoot` so we have
    # to schedule its collection after we have root. However, this requires
    # intrinsic knowledge and is not much better than just hardcoding them.
    # Instead, we should collect all variables as they are and then do the
    # interpolation without hardcoding the dependencies.
    #
    # TODO: There is no dedicated action for obtaining registry
    # values. The existing artifact collector uses `GetFileStat` action for
    # this which is horrible.
    args = rdf_client_action.GetFileStatRequest()
    args.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY

    args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment\TEMP"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsEnvTemp.__name__,
    )

    args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment\Path"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsEnvPath.__name__,
    )

    args.pathspec.path = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment\ComSpec"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsEnvComSpec.__name__,
    )

    args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment\windir"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsEnvWindir.__name__,
    )

    args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\ProfilesDirectory"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsProfilesDirectory.__name__,
    )
    # pylint: enable=line-too-long
    # pyformat: enable

  def _ProcessWindowsEnvProgramFilesDir(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%ProgramFiles%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    program_files = response.registry_data.string

    self.state.knowledge_base.environ_programfiles = program_files

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_programfiles")

  def _ProcessWindowsEnvProgramFilesDirX86(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%ProgramFiles%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    program_files_x86 = response.registry_data.string

    self.state.knowledge_base.environ_programfilesx86 = program_files_x86

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_programfilesx86")

  def _ProcessWindowsEnvCommonFilesDir(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      status = responses.status
      self.Log("Failed to obtain `%%CommonProgramFiles%%`: %s", status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    common_files = response.registry_data.string

    self.state.knowledge_base.environ_commonprogramfiles = common_files

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_commonprogramfiles")

  def _ProcessWindowsEnvCommonFilesDirX86(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      status = responses.status
      self.Log("Failed to obtain `%%CommonProgramFiles (x86)%%`: %s", status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    common_files_x86 = response.registry_data.string

    self.state.knowledge_base.environ_commonprogramfilesx86 = common_files_x86

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_commonprogramfilesx86")

  def _ProcessWindowsEnvProgramData(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%ProgramData%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    program_data = response.registry_data.string
    # TODO: We should not hardcode the dependency on `%SystemRoot%`
    # and do an interpolation pass once all variables are there.
    program_data = artifact_utils.ExpandWindowsEnvironmentVariables(
        program_data,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_programdata = program_data
    # TODO: Remove once this knowledge base field is removed.
    self.state.knowledge_base.environ_allusersappdata = program_data

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_programdata")
    self.state.fulfilled_deps.add("environ_allusersappdata")

    # pylint: disable=line-too-long
    # pyformat: disable
    #
    # Interestingly, it looks like there is no such value in the registry on
    # Windows 10. But the original artifact uses this path and there are other
    # websites stating that it should be there [1, 2] we try this anyway.
    #
    # According to Wikipedia [3] this value since Windows Vista is deprecated in
    # favour of `%PRORGAMDATA%` so e fallback to that in case we cannot retrieve
    # it.
    #
    # [1]: https://renenyffenegger.ch/notes/Windows/dirs/ProgramData/index
    # [2]: https://winreg-kb.readthedocs.io/en/latest/sources/system-keys/Environment-variables.html#currentversion-profilelist-key
    # [3]: https://en.wikipedia.org/wiki/Environment_variable#ALLUSERSPROFILE
    #
    # TODO: There is no dedicated action for obtaining registry
    # values. The existing artifact collector uses `GetFileStat` action for
    # this which is horrible.
    args = rdf_client_action.GetFileStatRequest()
    args.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
    args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\AllUsersProfile"
    self.CallClient(
        server_stubs.GetFileStat,
        args,
        next_state=self._ProcessWindowsEnvAllUsersProfile.__name__,
    )
    # pylint: enable=line-too-long
    # pyformat: enable

  def _ProcessWindowsEnvDriverData(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%DriverData%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    driver_data = response.registry_data.string

    self.state.knowledge_base.environ_driverdata = driver_data

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_driverdata")

  def _ProcessWindowsCurrentControlSet(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain current control set: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    current = response.registry_data.integer
    if not (0 < current < 1000):
      raise flow_base.FlowError(f"Unexpected control set index: {current}")

    current_control_set = rf"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet{current:03}"

    self.state.knowledge_base.current_control_set = current_control_set

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("current_control_set")

  def _ProcessWindowsCodePage(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain code page: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    code_page = f"cp_{response.registry_data.string}"

    self.state.knowledge_base.code_page = code_page

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("code_page")

  def _ProcessWindowsDomain(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain domain: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    self.state.knowledge_base.domain = response.registry_data.string

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("domain")

  def _ProcessWindowsTimeZoneKeyName(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    def CollectWindowsTimeZoneStandardName():
      # TODO: There is no dedicated action for obtaining registry
      # values. The existing artifact collector uses `GetFileStat` action for
      # this which is horrible.
      #
      # pylint: disable=line-too-long
      # pyformat: disable
      args = rdf_client_action.GetFileStatRequest()
      args.pathspec.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
      args.pathspec.path = r"HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\TimeZoneInformation\StandardName"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsTimeZoneStandardName.__name__,
      )
      # pylint: enable=line-too-long
      # pyformat: enable

    if not responses.success:
      self.Log("Failed to obtain time zone key name: %s", responses.status)
      CollectWindowsTimeZoneStandardName()
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    time_zone_key_name = response.registry_data.string
    try:
      time_zone = windows_registry_parser.ZONE_LIST[time_zone_key_name]
    except KeyError:
      self.Log("Failed to parse time zone key name: %r", time_zone_key_name)
      # We set the time zone as "unknown" with the raw value in case the call
      # to get the standard name time zone also fails.
      self.state.knowledge_base.time_zone = f"Unknown ({time_zone_key_name!r})"
      CollectWindowsTimeZoneStandardName()
      return

    self.state.knowledge_base.time_zone = time_zone

    # TODO: This should be deleted once `provides` sections are
    # no longer used.
    self.state.fulfilled_deps.add("time_zone")

  def _ProcessWindowsTimeZoneStandardName(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain time zone standard name: %s", responses.status)
      # At this point it is possible that we have set the timezone to unknown
      # with the raw value if we managed to at least get the time zone key name
      # in the _ProcessWindowsTimeZoneKeyName` method.
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    time_zone_standard_name = response.registry_data.string
    try:
      time_zone = windows_registry_parser.ZONE_LIST[time_zone_standard_name]
    except KeyError:
      self.Log(
          "Failed to parse time zone standard name: %r",
          time_zone_standard_name,
      )
      # We always override this value—even in case we set some "unknown" time
      # zone with a raw key name before, the "standard" one is going to be more
      # readable.
      self.state.knowledge_base.time_zone = (
          f"Unknown ({time_zone_standard_name!r})"
      )
      return

    self.state.knowledge_base.time_zone = time_zone

    # TODO: This should be deleted once `provides` sections are
    # no longer used.
    self.state.fulfilled_deps.add("time_zone")

  def _ProcessWindowsEnvTemp(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%TEMP%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    temp = response.registry_data.string
    # TODO: We should not hardcode the dependency of `TEMP` on
    # `SystemRoot` and do an interpolation pass once all variables are there.
    temp = artifact_utils.ExpandWindowsEnvironmentVariables(
        temp,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_temp = temp

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_temp")

  def _ProcessWindowsEnvPath(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%Path%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    path = response.registry_data.string
    # TODO: We should not hardcode the dependency of `Path` on
    # `SystemRoot` and do an interpolation pass once all variables are there.
    path = artifact_utils.ExpandWindowsEnvironmentVariables(
        path,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_path = path

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_path")

  def _ProcessWindowsEnvComSpec(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%ComSpec%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    com_spec = response.registry_data.string
    # TODO: We should not hardcode the dependency of `ComSpec` on
    # `SystemRoot` and do an interpolation pass once all variables are there.
    com_spec = artifact_utils.ExpandWindowsEnvironmentVariables(
        com_spec,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_comspec = com_spec

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_comspec")

  def _ProcessWindowsEnvWindir(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain `%%windir%%`: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    windir = response.registry_data.string
    # TODO: We should not hardcode the dependency of `windir` on
    # `SystemRoot` and do an interpolation pass once all variables are there.
    windir = artifact_utils.ExpandWindowsEnvironmentVariables(
        windir,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_windir = windir

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_windir")

  def _ProcessWindowsProfilesDirectory(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain profiles directory: %s", responses.status)
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    profiles_directory = response.registry_data.string
    # TODO: We should not hardcode the dependency on `SystemDrive`
    # and do an interpolation pass once all variables are there.
    profiles_directory = artifact_utils.ExpandWindowsEnvironmentVariables(
        profiles_directory,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_profilesdirectory = profiles_directory

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_profilesdirectory")

  def _ProcessWindowsEnvAllUsersProfile(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if responses.success:
      if len(responses) != 1:
        message = f"Unexpected number of responses: {len(responses)}"
        raise flow_base.FlowError(message)

      response = responses.First()
      if not isinstance(response, rdf_client_fs.StatEntry):
        message = f"Unexpected response type: {type(response)}"
        raise flow_base.FlowError(message)

      allusersprofile = response.registry_data.string
    else:
      # Since Windows Vista `%PROGRAMDATA%` superseded `%ALLUSERSPROFILE%` [1],
      # so we fall back to that in case we cannot obtain it (which is expected
      # on most modern machines and thus we don't even log an error).
      #
      # [1]: https://en.wikipedia.org/wiki/Environment_variable#ALLUSERSPROFILE
      allusersprofile = self.state.knowledge_base.environ_programdata

    # TODO: We should not hardcode dependency on `%ProgramData%`
    # and do an interpolation pass once all variables are there.
    allusersprofile = artifact_utils.ExpandWindowsEnvironmentVariables(
        allusersprofile,
        self.state.knowledge_base,
    )

    self.state.knowledge_base.environ_allusersprofile = allusersprofile

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("environ_allusersprofile")

  def _ProcessWindowsProfiles(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    # TODO: Delete this once dependent artifacts are removed.
    self.state.in_flight_artifacts.remove("WindowsRegistryProfiles")

    if not responses.success:
      self.Log("Failed to obtain Windows profiles: %s", responses.status)
      return

    for response in responses:
      if not isinstance(response, rdf_file_finder.FileFinderResult):
        raise flow_base.FlowError(f"Unexpected response type: {type(response)}")

      sid = ntpath.basename(ntpath.dirname(response.stat_entry.pathspec.path))
      home = response.stat_entry.registry_data.string

      if not windows_registry_parser.SID_RE.match(sid):
        # There are some system profiles that do not match, so we don't log any
        # errors and just silently continue.
        continue

      user = rdf_client.User()
      user.sid = sid
      user.homedir = user.userprofile = home
      user.username = ntpath.basename(home)

      self.state.knowledge_base.users.append(user)

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("users.sid")
    self.state.fulfilled_deps.add("users.userprofile")
    self.state.fulfilled_deps.add("users.homedir")
    self.state.fulfilled_deps.add("users.username")

    args = rdf_file_finder.FileFinderArgs()
    # TODO: There is no dedicated action for obtaining registry
    # values but `STAT` action of the file-finder will get it. This should be
    # refactored once registry-specific actions are available.
    args.action.action_type = rdf_file_finder.FileFinderAction.Action.STAT
    args.pathtype = rdf_paths.PathSpec.PathType.REGISTRY

    for user in self.state.knowledge_base.users:
      # pylint: disable=line-too-long
      # pyformat: disable
      args.paths.extend([
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\*",
          rf"HKEY_USERS\{user.sid}\Environment\*",
          rf"HKEY_USERS\{user.sid}\Volatile Environment\*",
      ])
      # pylint: enable=line-too-long
      # pyformat: enable

    self.CallClient(
        server_stubs.VfsFileFinder,
        args,
        next_state=self._ProcessWindowsProfileExtras.__name__,
    )

    # WMI queries are slow, so we consider them "heavyweight".
    if not self.args.lightweight:
      users = self.state.knowledge_base.users

      args = rdf_client_action.WMIRequest()
      args.query = f"""
      SELECT *
        FROM Win32_UserAccount
       WHERE {" OR ".join(f"name = '{user.username}'" for user in users)}
      """
      self.CallClient(
          server_stubs.WmiQuery,
          args,
          next_state=self._ProcessWindowsWMIUserAccounts.__name__,
      )

  def _ProcessWindowsProfileExtras(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain Windows profile extras: %s", responses.status)
      return

    users_by_sid = {user.sid: user for user in self.state.knowledge_base.users}

    for response in responses:
      if not isinstance(response, rdf_file_finder.FileFinderResult):
        raise flow_base.FlowError(f"Unexpected response type: {type(response)}")

      path = pathlib.PureWindowsPath(response.stat_entry.pathspec.path)
      parts = path.parts

      # TODO: Sometimes we get leading slashes and sometimes not,
      # so `parts` can have inconsistent prefix. We locate `HKEY_USERS` instead.
      # Once we have dedicated action for retrieving data from the registry in
      # a consistent way, we should remove this workaround.
      try:
        hive_index = parts.index("HKEY_USERS")
      except ValueError:
        self.Log("Registry hive not found for %r", path)
        continue

      sid = parts[hive_index + 1]
      if not windows_registry_parser.SID_RE.match(sid):
        self.Log("Unexpected registry SID for %r", path)
        continue

      try:
        user = users_by_sid[sid]
      except KeyError:
        self.Log("Missing users with SID %r", sid)
        continue

      registry_key = parts[-2]
      registry_value = parts[-1]
      registry_data = response.stat_entry.registry_data.string

      attrs = windows_registry_parser.WinUserSpecialDirs.key_var_mapping
      try:
        attr = attrs[registry_key][registry_value]
      except KeyError:
        self.Log("Invalid registry value for %r", path)
        continue

      setattr(user, attr, registry_data)

  def _ProcessWindowsWMIUserAccounts(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain WMI user accounts: %s", responses.status)
      return

    users_by_sid = {user.sid: user for user in self.state.knowledge_base.users}

    for response in responses:
      if not isinstance(response, rdf_protodict.Dict):
        raise flow_base.FlowError(f"Unexpected response type: {type(response)}")

      try:
        sid = response["SID"]
      except KeyError:
        self.Log("Missing 'SID' from WMI result")
        continue

      try:
        domain = response["Domain"]
      except KeyError:
        self.Log("Missing 'Domain' from WMI result")
        continue

      try:
        user = users_by_sid[sid]
      except KeyError:
        self.Log("Missing user with SID %r", sid)
        continue

      user.userdomain = domain

    # TODO: This should be deleted once `provides` sections are no
    # longer used.
    self.state.fulfilled_deps.add("users.userdomain")

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

    # If `kb_set` is empty, `GetArtifactNames` returns *all* artifacts in the
    # system for the given platform, which is not what we want.
    if kb_set:
      no_deps_names = artifact_registry.REGISTRY.GetArtifactNames(
          os_name=self.state.knowledge_base.os,
          name_list=kb_set,
          exclude_dependents=True,
      )
    else:
      no_deps_names = set()

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
    self._responses: List[rdfvalue.RDFValue] = []
    self._errors: List[parsers.ParseError] = []

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

    # File parsers accept only stat responses. It might be possible that an
    # artifact declares multiple sources and has multiple parsers attached (each
    # for different kind of source). Thus, artifacts are not "well typed" now
    # we must supply parsers only with something they support.
    stat_responses: List[rdf_client_fs.StatEntry] = []
    for response in responses:
      if isinstance(response, rdf_client_fs.StatEntry):
        stat_responses.append(response)

    has_single_file_parsers = self._factory.HasSingleFileParsers()
    has_multi_file_parsers = self._factory.HasMultiFileParsers()

    if has_single_file_parsers or has_multi_file_parsers:
      pathspecs = [response.pathspec for response in stat_responses]
      # It might be also the case that artifact has both regular response parser
      # and file parser attached and sources that don't collect files but yield
      # stat entries.
      #
      # TODO(hanuszczak): This is a quick workaround that works for now, but
      # can lead to spurious file being parsed if the file was collected in the
      # past and now only a stat entry response came. A proper solution would be
      # to tag responses with artifact source and then make parsers define what
      # sources they support.
      pathspecs = list(filter(self._HasFile, pathspecs))
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

  def _HasFile(self, pathspec: rdf_paths.PathSpec) -> bool:
    """Checks whether any file for the given pathspec was ever collected."""
    client_path = db.ClientPath.FromPathSpec(self._client_id, pathspec)
    return file_store.GetLastCollectionPathInfo(client_path) is not None

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
