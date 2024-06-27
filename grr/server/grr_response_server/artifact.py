#!/usr/bin/env python
"""Base classes for artifacts."""
import logging
import ntpath
import os
import pathlib
import re
import stat

from grr_response_core.lib import artifact_utils
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import mig_artifacts
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import mig_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_server import artifact_registry
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import distro


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

  We collect required knowledgebase attributes are required and return a filled
  knowledgebase.
  """

  category = "/Collectors/"
  behaviours = flow_base.BEHAVIOUR_ADVANCED
  args_type = KnowledgeBaseInitializationArgs
  result_types = (rdf_client.KnowledgeBase,)

  def Start(self):
    """For each artifact, create subflows for each collector."""
    self.state.knowledge_base = None

    self.InitializeKnowledgeBase()

    if self.client_os == "Linux":
      if artifact_registry.REGISTRY.Exists("LinuxReleaseInfo"):
        self.CallFlow(
            distro.CollectDistroInfo.__name__,
            next_state=self._ProcessLinuxDistroInfo.__name__,
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

      args.pathspec.path = r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\AllUsersProfile"
      self.CallClient(
          server_stubs.GetFileStat,
          args,
          next_state=self._ProcessWindowsEnvAllUsersProfile.__name__,
      )

      args = rdf_file_finder.FileFinderArgs()
      # TODO: There is no dedicated action for obtaining registry
      # values but `STAT` action of the file-finder will get it. This should be
      # refactored once registry-specific actions are available.
      args.action.action_type = rdf_file_finder.FileFinderAction.Action.STAT
      args.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
      args.paths = [r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\ProfileList\*\ProfileImagePath"]
      # TODO: remove this when the registry+sandboxing bug
      # is fixed.
      args.implementation_type = rdf_paths.PathSpec.ImplementationType.DIRECT
      self.CallClient(
          server_stubs.VfsFileFinder,
          args,
          next_state=self._ProcessWindowsProfiles.__name__,
      )

  def _ProcessLinuxDistroInfo(
      self,
      responses: flow_responses.Responses[distro.CollectDistroInfoResult],
  ) -> None:
    if not responses.success:
      self.Log("Failed to get Linux release information: %s", responses.status)
      return

    for response in responses:
      if response.name:
        self.state.knowledge_base.os_release = response.name
      if response.version_major:
        self.state.knowledge_base.os_major_version = response.version_major
      if response.version_minor:
        self.state.knowledge_base.os_minor_version = response.version_minor

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

    list_users_dir_args = jobs_pb2.ListDirRequest()
    list_users_dir_args.pathspec.pathtype = jobs_pb2.PathSpec.PathType.OS
    list_users_dir_args.pathspec.path = f"{system_drive}\\Users"
    self.CallClient(
        server_stubs.ListDirectory,
        mig_client_action.ToRDFListDirRequest(list_users_dir_args),
        next_state=self._ProcessWindowsListUsersDir.__name__,
    )

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

    self.state.knowledge_base.environ_programdata = (
        response.registry_data.string
    )

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
      time_zone = _WINDOWS_TIME_ZONE_MAP[time_zone_key_name]
    except KeyError:
      self.Log("Failed to parse time zone key name: %r", time_zone_key_name)
      # We set the time zone as "unknown" with the raw value in case the call
      # to get the standard name time zone also fails.
      self.state.knowledge_base.time_zone = f"Unknown ({time_zone_key_name!r})"
      CollectWindowsTimeZoneStandardName()
      return

    self.state.knowledge_base.time_zone = time_zone

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
      time_zone = _WINDOWS_TIME_ZONE_MAP[time_zone_standard_name]
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

    self.state.knowledge_base.environ_temp = response.registry_data.string

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

    self.state.knowledge_base.environ_path = response.registry_data.string

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

    self.state.knowledge_base.environ_comspec = response.registry_data.string

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

    self.state.knowledge_base.environ_windir = response.registry_data.string

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

    self.state.knowledge_base.environ_profilesdirectory = (
        response.registry_data.string
    )

  def _ProcessWindowsEnvAllUsersProfile(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      # Since Windows Vista `%PROGRAMDATA%` superseded `%ALLUSERSPROFILE%` [1],
      # so we actually expect this call to fail most of the time. Thus, we don't
      # log anything or raise any errors.
      #
      # [1]: https://en.wikipedia.org/wiki/Environment_variable#ALLUSERSPROFILE
      return

    if len(responses) != 1:
      message = f"Unexpected number of responses: {len(responses)}"
      raise flow_base.FlowError(message)

    response = responses.First()
    if not isinstance(response, rdf_client_fs.StatEntry):
      message = f"Unexpected response type: {type(response)}"
      raise flow_base.FlowError(message)

    self.state.knowledge_base.environ_allusersprofile = (
        response.registry_data.string
    )

  def _ProcessWindowsProfiles(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to obtain Windows profiles: %s", responses.status)
      return

    for response in responses:
      if not isinstance(response, rdf_file_finder.FileFinderResult):
        raise flow_base.FlowError(f"Unexpected response type: {type(response)}")

      sid = ntpath.basename(ntpath.dirname(response.stat_entry.pathspec.path))
      home = response.stat_entry.registry_data.string

      if not _WINDOWS_SID_REGEX.match(sid):
        # There are some system profiles that do not match, so we don't log any
        # errors and just silently continue.
        continue

      user = rdf_client.User()
      user.sid = sid
      user.homedir = user.userprofile = home
      user.username = ntpath.basename(home)

      self.state.knowledge_base.users.append(user)

    args = rdf_file_finder.FileFinderArgs()
    # TODO: There is no dedicated action for obtaining registry
    # values but `STAT` action of the file-finder will get it. This should be
    # refactored once registry-specific actions are available.
    args.action.action_type = rdf_file_finder.FileFinderAction.Action.STAT
    args.pathtype = rdf_paths.PathSpec.PathType.REGISTRY
    # TODO: remove this when the registry+sandboxing bug
    # is fixed.
    args.implementation_type = rdf_paths.PathSpec.ImplementationType.DIRECT

    for user in self.state.knowledge_base.users:
      # pylint: disable=line-too-long
      # pyformat: disable
      args.paths.extend([
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\{{A520A1A4-1780-4FF6-BD18-167343C5AF16}}",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Desktop",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\AppData",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Local AppData",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Cookies",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Cache",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Recent",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Startup",
          rf"HKEY_USERS\{user.sid}\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders\Personal",
          rf"HKEY_USERS\{user.sid}\Environment\TEMP",
          rf"HKEY_USERS\{user.sid}\Volatile Environment\USERDOMAIN",
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
      if not _WINDOWS_SID_REGEX.match(sid):
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

      # TODO: Replace with `match` once we can use Python 3.10
      # features.
      case = (registry_key, registry_value)
      if case == ("Shell Folders", "{A520A1A4-1780-4FF6-BD18-167343C5AF16}"):
        user.localappdata_low = registry_data
      elif case == ("Shell Folders", "Desktop"):
        user.desktop = registry_data
      elif case == ("Shell Folders", "AppData"):
        user.appdata = registry_data
      elif case == ("Shell Folders", "Local AppData"):
        user.localappdata = registry_data
      elif case == ("Shell Folders", "Cookies"):
        user.cookies = registry_data
      elif case == ("Shell Folders", "Cache"):
        user.internet_cache = registry_data
      elif case == ("Shell Folders", "Recent"):
        user.recent = registry_data
      elif case == ("Shell Folders", "Startup"):
        user.startup = registry_data
      elif case == ("Shell Folders", "Personal"):
        user.personal = registry_data
      elif case == ("Environment", "TEMP"):
        user.temp = registry_data
      elif case == ("Volatile Environment", "USERDOMAIN"):
        user.userdomain = registry_data
      else:
        self.Log("Invalid registry value for %r", path)
        continue

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

  def _ProcessWindowsListUsersDir(
      self,
      responses: flow_responses.Responses[rdfvalue.RDFValue],
  ) -> None:
    if not responses.success:
      self.Log("Failed to list Windows `Users` directory: %s", responses.status)
      return

    for response in responses:
      if not isinstance(response, rdf_client_fs.StatEntry):
        raise flow_base.FlowError(f"Unexpected response type: {type(response)}")

      response = mig_client_fs.ToProtoStatEntry(response)

      # There can be random files there as well. We are interested exclusively
      # in folders as file does not indicate user profile.
      if not stat.S_ISDIR(response.st_mode):
        continue

      # TODO: Remove once the `ListDirectory` action is fixed not
      # to yield results with leading slashes on Windows.
      response.pathspec.path = response.pathspec.path.removeprefix("/")

      path = pathlib.PureWindowsPath(response.pathspec.path)

      # There are certain profiles there that are not real "users" active on the
      # machine and so we should not report them as such.
      if path.name.upper() in [
          "ADMINISTRATOR",
          "ALL USERS",
          "DEFAULT",
          "DEFAULT USER",
          "DEFAULTUSER0",
          "PUBLIC",
      ]:
        continue

      user = knowledge_base_pb2.User()
      user.username = path.name
      user.homedir = str(path)

      self.state.knowledge_base.MergeOrAddUser(mig_client.ToRDFUser(user))

  def End(self, responses):
    """Finish up."""
    del responses

    if self.client_os == "Windows":
      self.state.knowledge_base = mig_client.ToRDFKnowledgeBase(
          artifact_utils.ExpandKnowledgebaseWindowsEnvVars(
              mig_client.ToProtoKnowledgeBase(self.state.knowledge_base),
          ),
      )

    # TODO: `%LOCALAPPDATA%` is a very often used variable that we
    # potentially not collect due to limitations of the Windows registry. For
    # now, in case we did not collect it, we set it to the default Windows value
    # (which should be the case almost always but is nevertheless not the most
    # way of handling it).
    #
    # Alternatively, we could develop a more general way of handling default
    # environment variable values in case they are missing.
    for user in self.state.knowledge_base.users:
      if not user.localappdata:
        self.Log(
            "Missing `%%LOCALAPPDATA%%` for '%s', using Windows default",
            user.username,
        )
        user.localappdata = rf"{user.userprofile}\AppData\Local"

    self.SendReply(self.state.knowledge_base)

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

    data_store.REL_DB.WriteArtifact(
        mig_artifacts.ToProtoArtifact(artifact_value)
    )

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


_WINDOWS_SID_REGEX = re.compile(r"^S-\d-\d+-(\d+-){1,14}\d+$")


# Pre-built from the following Windows registry key:
# `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones\`
#
# Note that these may not be consistent across Windows versions so may need
# adjustment in the future.
_WINDOWS_TIME_ZONE_MAP: dict[str, str] = {
    "IndiaStandardTime": "Asia/Kolkata",
    "EasternStandardTime": "EST5EDT",
    "EasternDaylightTime": "EST5EDT",
    "MountainStandardTime": "MST7MDT",
    "MountainDaylightTime": "MST7MDT",
    "PacificStandardTime": "PST8PDT",
    "PacificDaylightTime": "PST8PDT",
    "CentralStandardTime": "CST6CDT",
    "CentralDaylightTime": "CST6CDT",
    "SamoaStandardTime": "US/Samoa",
    "HawaiianStandardTime": "US/Hawaii",
    "AlaskanStandardTime": "US/Alaska",
    "MexicoStandardTime2": "MST7MDT",
    "USMountainStandardTime": "MST7MDT",
    "CanadaCentralStandardTime": "CST6CDT",
    "MexicoStandardTime": "CST6CDT",
    "CentralAmericaStandardTime": "CST6CDT",
    "USEasternStandardTime": "EST5EDT",
    "SAPacificStandardTime": "EST5EDT",
    "MalayPeninsulaStandardTime": "Asia/Kuching",
    "PacificSAStandardTime": "Canada/Atlantic",
    "AtlanticStandardTime": "Canada/Atlantic",
    "SAWesternStandardTime": "Canada/Atlantic",
    "NewfoundlandStandardTime": "Canada/Newfoundland",
    "AzoresStandardTime": "Atlantic/Azores",
    "CapeVerdeStandardTime": "Atlantic/Azores",
    "GMTStandardTime": "GMT",
    "GreenwichStandardTime": "GMT",
    "W.CentralAfricaStandardTime": "Europe/Belgrade",
    "W.EuropeStandardTime": "Europe/Belgrade",
    "CentralEuropeStandardTime": "Europe/Belgrade",
    "RomanceStandardTime": "Europe/Belgrade",
    "CentralEuropeanStandardTime": "Europe/Belgrade",
    "E.EuropeStandardTime": "Egypt",
    "SouthAfricaStandardTime": "Egypt",
    "IsraelStandardTime": "Egypt",
    "EgyptStandardTime": "Egypt",
    "NorthAsiaEastStandardTime": "Asia/Bangkok",
    "SingaporeStandardTime": "Asia/Bangkok",
    "ChinaStandardTime": "Asia/Bangkok",
    "W.AustraliaStandardTime": "Australia/Perth",
    "TaipeiStandardTime": "Asia/Bangkok",
    "TokyoStandardTime": "Asia/Tokyo",
    "KoreaStandardTime": "Asia/Seoul",
    "@tzres.dll,-10": "Atlantic/Azores",
    "@tzres.dll,-11": "Atlantic/Azores",
    "@tzres.dll,-12": "Atlantic/Azores",
    "@tzres.dll,-20": "Atlantic/Cape_Verde",
    "@tzres.dll,-21": "Atlantic/Cape_Verde",
    "@tzres.dll,-22": "Atlantic/Cape_Verde",
    "@tzres.dll,-40": "Brazil/East",
    "@tzres.dll,-41": "Brazil/East",
    "@tzres.dll,-42": "Brazil/East",
    "@tzres.dll,-70": "Canada/Newfoundland",
    "@tzres.dll,-71": "Canada/Newfoundland",
    "@tzres.dll,-72": "Canada/Newfoundland",
    "@tzres.dll,-80": "Canada/Atlantic",
    "@tzres.dll,-81": "Canada/Atlantic",
    "@tzres.dll,-82": "Canada/Atlantic",
    "@tzres.dll,-104": "America/Cuiaba",
    "@tzres.dll,-105": "America/Cuiaba",
    "@tzres.dll,-110": "EST5EDT",
    "@tzres.dll,-111": "EST5EDT",
    "@tzres.dll,-112": "EST5EDT",
    "@tzres.dll,-120": "EST5EDT",
    "@tzres.dll,-121": "EST5EDT",
    "@tzres.dll,-122": "EST5EDT",
    "@tzres.dll,-130": "EST5EDT",
    "@tzres.dll,-131": "EST5EDT",
    "@tzres.dll,-132": "EST5EDT",
    "@tzres.dll,-140": "CST6CDT",
    "@tzres.dll,-141": "CST6CDT",
    "@tzres.dll,-142": "CST6CDT",
    "@tzres.dll,-150": "America/Guatemala",
    "@tzres.dll,-151": "America/Guatemala",
    "@tzres.dll,-152": "America/Guatemala",
    "@tzres.dll,-160": "CST6CDT",
    "@tzres.dll,-161": "CST6CDT",
    "@tzres.dll,-162": "CST6CDT",
    "@tzres.dll,-170": "America/Mexico_City",
    "@tzres.dll,-171": "America/Mexico_City",
    "@tzres.dll,-172": "America/Mexico_City",
    "@tzres.dll,-180": "MST7MDT",
    "@tzres.dll,-181": "MST7MDT",
    "@tzres.dll,-182": "MST7MDT",
    "@tzres.dll,-190": "MST7MDT",
    "@tzres.dll,-191": "MST7MDT",
    "@tzres.dll,-192": "MST7MDT",
    "@tzres.dll,-200": "MST7MDT",
    "@tzres.dll,-201": "MST7MDT",
    "@tzres.dll,-202": "MST7MDT",
    "@tzres.dll,-210": "PST8PDT",
    "@tzres.dll,-211": "PST8PDT",
    "@tzres.dll,-212": "PST8PDT",
    "@tzres.dll,-220": "US/Alaska",
    "@tzres.dll,-221": "US/Alaska",
    "@tzres.dll,-222": "US/Alaska",
    "@tzres.dll,-230": "US/Hawaii",
    "@tzres.dll,-231": "US/Hawaii",
    "@tzres.dll,-232": "US/Hawaii",
    "@tzres.dll,-260": "GMT",
    "@tzres.dll,-261": "GMT",
    "@tzres.dll,-262": "GMT",
    "@tzres.dll,-271": "UTC",
    "@tzres.dll,-272": "UTC",
    "@tzres.dll,-280": "Europe/Budapest",
    "@tzres.dll,-281": "Europe/Budapest",
    "@tzres.dll,-282": "Europe/Budapest",
    "@tzres.dll,-290": "Europe/Warsaw",
    "@tzres.dll,-291": "Europe/Warsaw",
    "@tzres.dll,-292": "Europe/Warsaw",
    "@tzres.dll,-331": "Europe/Nicosia",
    "@tzres.dll,-332": "Europe/Nicosia",
    "@tzres.dll,-340": "Africa/Cairo",
    "@tzres.dll,-341": "Africa/Cairo",
    "@tzres.dll,-342": "Africa/Cairo",
    "@tzres.dll,-350": "Europe/Sofia",
    "@tzres.dll,-351": "Europe/Sofia",
    "@tzres.dll,-352": "Europe/Sofia",
    "@tzres.dll,-365": "Egypt",
    "@tzres.dll,-390": "Asia/Kuwait",
    "@tzres.dll,-391": "Asia/Kuwait",
    "@tzres.dll,-392": "Asia/Kuwait",
    "@tzres.dll,-400": "Asia/Baghdad",
    "@tzres.dll,-401": "Asia/Baghdad",
    "@tzres.dll,-402": "Asia/Baghdad",
    "@tzres.dll,-410": "Africa/Nairobi",
    "@tzres.dll,-411": "Africa/Nairobi",
    "@tzres.dll,-412": "Africa/Nairobi",
    "@tzres.dll,-434": "Asia/Tbilisi",
    "@tzres.dll,-435": "Asia/Tbilisi",
    "@tzres.dll,-440": "Asia/Muscat",
    "@tzres.dll,-441": "Asia/Muscat",
    "@tzres.dll,-442": "Asia/Muscat",
    "@tzres.dll,-447": "Asia/Baku",
    "@tzres.dll,-448": "Asia/Baku",
    "@tzres.dll,-449": "Asia/Baku",
    "@tzres.dll,-450": "Asia/Yerevan",
    "@tzres.dll,-451": "Asia/Yerevan",
    "@tzres.dll,-452": "Asia/Yerevan",
    "@tzres.dll,-460": "Asia/Kabul",
    "@tzres.dll,-461": "Asia/Kabul",
    "@tzres.dll,-462": "Asia/Kabul",
    "@tzres.dll,-471": "Asia/Yekaterinburg",
    "@tzres.dll,-472": "Asia/Yekaterinburg",
    "@tzres.dll,-511": "Asia/Aqtau",
    "@tzres.dll,-512": "Asia/Aqtau",
    "@tzres.dll,-570": "Asia/Chongqing",
    "@tzres.dll,-571": "Asia/Chongqing",
    "@tzres.dll,-572": "Asia/Chongqing",
    "@tzres.dll,-650": "Australia/Darwin",
    "@tzres.dll,-651": "Australia/Darwin",
    "@tzres.dll,-652": "Australia/Darwin",
    "@tzres.dll,-660": "Australia/Adelaide",
    "@tzres.dll,-661": "Australia/Adelaide",
    "@tzres.dll,-662": "Australia/Adelaide",
    "@tzres.dll,-670": "Australia/Sydney",
    "@tzres.dll,-671": "Australia/Sydney",
    "@tzres.dll,-672": "Australia/Sydney",
    "@tzres.dll,-680": "Australia/Brisbane",
    "@tzres.dll,-681": "Australia/Brisbane",
    "@tzres.dll,-682": "Australia/Brisbane",
    "@tzres.dll,-721": "Pacific/Port_Moresby",
    "@tzres.dll,-722": "Pacific/Port_Moresby",
    "@tzres.dll,-731": "Pacific/Fiji",
    "@tzres.dll,-732": "Pacific/Fiji",
    "@tzres.dll,-840": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-841": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-842": "America/Argentina/Buenos_Aires",
    "@tzres.dll,-880": "UTC",
    "@tzres.dll,-930": "UTC",
    "@tzres.dll,-931": "UTC",
    "@tzres.dll,-932": "UTC",
    "@tzres.dll,-1010": "Asia/Aqtau",
    "@tzres.dll,-1020": "Asia/Dhaka",
    "@tzres.dll,-1021": "Asia/Dhaka",
    "@tzres.dll,-1022": "Asia/Dhaka",
    "@tzres.dll,-1070": "Asia/Tbilisi",
    "@tzres.dll,-1120": "America/Cuiaba",
    "@tzres.dll,-1140": "Pacific/Fiji",
    "@tzres.dll,-1460": "Pacific/Port_Moresby",
    "@tzres.dll,-1530": "Asia/Yekaterinburg",
    "@tzres.dll,-1630": "Europe/Nicosia",
    "@tzres.dll,-1660": "America/Bahia",
    "@tzres.dll,-1661": "America/Bahia",
    "@tzres.dll,-1662": "America/Bahia",
    "Central Standard Time": "CST6CDT",
    "Pacific Standard Time": "PST8PDT",
}
