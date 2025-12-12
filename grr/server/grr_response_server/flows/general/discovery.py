#!/usr/bin/env python
"""These are flows designed to discover information about the host."""

import logging

from google.protobuf import any_pb2
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import metrics
from grr_response_proto import cloud_pb2
from grr_response_proto import crowdstrike_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_proto.api import config_pb2
from grr_response_server import artifact
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_utils
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import notification
from grr_response_server import rrg_path
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import cloud
from grr_response_server.flows.general import crowdstrike
from grr_response_server.flows.general import hardware
from grr_response_server.flows.general import memsize
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto.rrg import os_pb2 as rrg_os_pb2
from grr_response_proto.rrg.action import get_system_metadata_pb2 as rrg_get_system_metadata_pb2
from grr_response_proto.rrg.action import list_interfaces_pb2 as rrg_list_interfaces_pb2
from grr_response_proto.rrg.action import list_mounts_pb2 as rrg_list_mounts_pb2
from grr_response_proto.rrg.action import query_wmi_pb2 as rrg_query_wmi_pb2

FLEETSPEAK_UNLABELED_CLIENTS = metrics.Counter("fleetspeak_unlabeled_clients")
CLOUD_METADATA_COLLECTION_ERRORS = metrics.Counter(
    "cloud_metadata_collection_errors"
)


class InterrogateArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.InterrogateArgs


class Interrogate(
    flow_base.FlowBase[
        flows_pb2.InterrogateArgs,
        flows_pb2.InterrogateStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Interrogate various things about the host."""

  category = "/Administrative/"
  args_type = InterrogateArgs
  result_types = (rdf_objects.ClientSnapshot,)
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.InterrogateArgs
  proto_result_types = (objects_pb2.ClientSnapshot,)
  proto_store_type = flows_pb2.InterrogateStore

  only_protos_allowed = True

  def Start(self):
    """Start off all the tests."""
    if not self.python_agent_support and not self.rrg_support:
      raise flow_base.FlowError("Neither Python nor RRG agent is supported")

    self.store.client_snapshot.client_id = self.client_id
    self.store.client_snapshot.metadata.source_flow_id = self.rdf_flow.flow_id

    # There are three possible scenarios:
    #
    #   1. Only Python agent is supported.
    #   2. Only RRG is supported.
    #   3. Both RRG and Python agent are supported.
    #
    # Additionally, for backward compatibility we assume that if RRG is not
    # explicitly supported, then GRR is definitely supported. This assumption
    # may be revisited in the future.
    #
    # Anyway, if both agents are supported we need to get metadata about both
    # of them. If only one is supported we need to get metadata about that one
    # and only that one. It is important not to issue the request to the other
    # one as the flow will get stuck awaiting the response to come.
    if self.python_agent_support:
      # These are features specific to the legacy agent (as RRG reports its
      # configuration as part of its startup metadata and does not have any
      # Python libraries as dependencies).

      # `ClientInfo` should be collected early on since we might need the client
      # version later on to know what actions a client supports.
      self.CallClientProto(
          server_stubs.GetClientInfo,
          next_state=self.ClientInfo.__name__,
      )
      self.CallClientProto(
          server_stubs.GetConfiguration,
          next_state=self.ClientConfiguration.__name__,
      )
      self.CallClientProto(
          server_stubs.GetLibraryVersions,
          next_state=self.ClientLibraries.__name__,
      )

    if self.rrg_support:
      rrg_stubs.GetSystemMetadata().Call(self.HandleRRGGetSystemMetadata)
      rrg_stubs.ListInterfaces().Call(self.HandleRRGListInterfaces)
      rrg_stubs.ListMounts().Call(self.HandleRRGListMounts)

      # For RRG-enabled endpoints we can collect CrowdStrike ID collection right
      # away because we always know the operating system. For Python agent-only
      # endpoints it is handled after the call to `GetPlatformInfo` returns.
      if config.CONFIG["Interrogate.collect_crowdstrike_agent_id"]:
        self.CallFlowProto(
            crowdstrike.GetCrowdStrikeAgentID.__name__,
            next_state=self.ProcessGetCrowdStrikeAgentID.__name__,
        )
    else:
      self.CallClientProto(
          server_stubs.GetPlatformInfo, next_state=self.Platform.__name__
      )
      self.CallClientProto(
          server_stubs.GetInstallDate, next_state=self.InstallDate.__name__
      )
      self.CallClientProto(
          server_stubs.EnumerateInterfaces,
          next_state=self.EnumerateInterfaces.__name__,
      )
      self.CallClientProto(
          server_stubs.EnumerateFilesystems,
          next_state=self.EnumerateFilesystems.__name__,
      )

    self.CallFlowProto(
        memsize.GetMemorySize.__name__,
        next_state=self.StoreMemorySize.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def HandleRRGGetSystemMetadata(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Handles responses from RRG `GET_SYSTEM_METADATA` action."""
    if not responses.success:
      message = f"RRG system metadata collection failed: {responses.status}"
      raise flow_base.FlowError(message)

    if len(responses) != 1:
      message = (
          "Unexpected number of RRG system metadata responses: "
          f"{len(responses)}"
      )
      raise flow_base.FlowError(message)

    result = rrg_get_system_metadata_pb2.Result()
    result.ParseFromString(list(responses)[0].value)

    if result.type == rrg_os_pb2.Type.LINUX:
      self.store.client_snapshot.knowledge_base.os = "Linux"
    elif result.type == rrg_os_pb2.Type.MACOS:
      self.store.client_snapshot.knowledge_base.os = "Darwin"
    elif result.type == rrg_os_pb2.Type.WINDOWS:
      self.store.client_snapshot.knowledge_base.os = "Windows"
    else:
      raise flow_base.FlowError(f"Unexpected operating system: {result.type}")

    self.store.client_snapshot.arch = result.arch
    # TODO: https://github.com/google/rrg/issues/58 - Remove once FQDN collec-
    # tion is working reliably on all platforms.
    #
    # FQDN collection is broken at macOS at the moment so we use hostname in
    # case it is missing. This is not perfect but necessary as FQDN is often
    # used for searching and display in the UI.
    if result.fqdn:
      self.store.client_snapshot.knowledge_base.fqdn = result.fqdn
    else:
      self.Log("FQDN unavailable, using hostname fallback: %s", result.hostname)
      self.store.client_snapshot.knowledge_base.fqdn = result.hostname
    self.store.client_snapshot.os_version = result.version
    self.store.client_snapshot.install_time = (
        result.install_time.ToMicroseconds()
    )

    # TODO: Remove these lines.
    #
    # At the moment `ProcessKnowledgeBase` uses `state.fqdn` and `state.os` for
    # knowledgebase and overrides everything else. The code should be refactored
    # to merge knowledgebase from individual client calls and the knowledgebase
    # initialization flow.
    self.store.fqdn = self.store.client_snapshot.knowledge_base.fqdn
    self.store.os = self.store.client_snapshot.knowledge_base.os

    if result.type in [rrg_os_pb2.Type.LINUX, rrg_os_pb2.Type.WINDOWS]:
      self.CallFlowProto(
          cloud.CollectCloudVMMetadata.__name__,
          next_state=self._ProcessCollectCloudVMMetadata.__name__,
      )

    args = flows_pb2.KnowledgeBaseInitializationArgs()
    args.require_complete = False  # Not all dependencies are known yet.
    args.lightweight = (
        self.proto_args.lightweight
        if self.proto_args.HasField("lightweight")
        else True
    )

    self.CallFlowProto(
        flow_name=artifact.KnowledgeBaseInitializationFlow.__name__,
        flow_args=args,
        next_state=self.ProcessKnowledgeBase.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def HandleRRGListInterfaces(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to list interfaces: %s", responses.status)
      return

    # TODO: Replace with `clear()` once upgraded.
    del self.store.client_snapshot.interfaces[:]

    for response in responses:
      result = rrg_list_interfaces_pb2.Result()
      result.ParseFromString(response.value)

      iface = self.store.client_snapshot.interfaces.add()
      iface.ifname = result.interface.name
      iface.mac_address = result.interface.mac_address.octets

      for result_ip_address in result.interface.ip_addresses:
        iface_address = jobs_pb2.NetworkAddress()
        iface_address.packed_bytes = result_ip_address.octets

        if len(result_ip_address.octets) == 4:
          iface_address.address_type = jobs_pb2.NetworkAddress.Family.INET
        elif len(result_ip_address.octets) == 16:
          iface_address.address_type = jobs_pb2.NetworkAddress.Family.INET6
        else:
          self.Log("Invalid IP address octets: %s", result_ip_address.octets)
          continue

        iface.addresses.append(iface_address)

  @flow_base.UseProto2AnyResponses
  def HandleRRGListMounts(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to list mounts: %s", responses.status)
      return

    # TODO: Replace with `clear()` once upgraded.
    del self.store.client_snapshot.filesystems[:]

    for response in responses:
      result = rrg_list_mounts_pb2.Result()
      result.ParseFromString(response.value)

      filesystem = self.store.client_snapshot.filesystems.add()
      filesystem.device = result.mount.name
      filesystem.type = result.mount.fs_type

      if self.rrg_version >= (0, 0, 4):
        filesystem.mount_point = str(
            rrg_path.PurePath.For(self.rrg_os_type, result.mount.path)
        )
      else:
        # TODO: https://github.com/google/rrg/issues/133 - Remove once we no
        # longer support version <0.0.4.
        filesystem.mount_point = result.mount.path.raw_bytes.decode(
            "utf-8",
            errors="replace",
        )

  @flow_base.UseProto2AnyResponses
  def _ProcessCollectCloudVMMetadata(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Process cloud metadata and store in the client."""
    if not responses.success:
      CLOUD_METADATA_COLLECTION_ERRORS.Increment()

      # We want to log this but it's not serious enough to kill the whole flow.
      self.Log("Failed to collect cloud metadata: %s" % responses.status)
      return

    # Expected for non-cloud machines.
    if not list(responses):
      return

    result = cloud_pb2.CollectCloudVMMetadataResult()
    result.ParseFromString(list(responses)[0].value)

    self.store.client_snapshot.cloud_instance.CopyFrom(result.vm_metadata)

  @flow_base.UseProto2AnyResponses
  def StoreMemorySize(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Stores the memory size."""
    if not responses.success or not list(responses):
      return

    response = flows_pb2.GetMemorySizeResult()
    response.ParseFromString(list(responses)[0].value)

    self.store.client_snapshot.memory_size = response.total_bytes

  @flow_base.UseProto2AnyResponses
  def Platform(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Stores information about the platform."""
    if not responses.success or not list(responses):
      # We failed to get the Platform info, maybe there is a stored
      # system we can use to get at least some data.
      client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      known_system_type = client and client.knowledge_base.os

      self.Log("Could not retrieve Platform info.")
    else:  # responses.success and list(responses)
      response = jobs_pb2.Uname()
      list(responses)[0].Unpack(response)

      client = self.store.client_snapshot
      client.os_release = response.release
      client.os_version = response.version
      client.kernel = response.kernel
      client.arch = response.machine
      client.knowledge_base.os = response.system
      # Store these for later, there might be more accurate data
      # coming in from the artifact collector.
      self.store.fqdn = response.fqdn
      self.store.os = response.system

      existing_client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      if existing_client is None:
        # This is the first time we interrogate this client. In that case, we
        # need to store basic information about this client right away so
        # follow up flows work properly.
        data_store.REL_DB.WriteClientSnapshot(self.store.client_snapshot)

      try:
        # Update the client index
        client_index.ClientIndex().AddClient(
            mig_objects.ToRDFClientSnapshot(client)
        )
      except db.UnknownClientError:
        pass

      # No support for OS X cloud machines as yet.
      if response.system in ["Linux", "Windows"]:
        self.CallFlowProto(
            cloud.CollectCloudVMMetadata.__name__,
            next_state=self._ProcessCollectCloudVMMetadata.__name__,
        )

      known_system_type = True

    if known_system_type:
      # Crowdstrike id collection is platform-dependent and can only be done
      # if we know the system type.
      if config.CONFIG["Interrogate.collect_crowdstrike_agent_id"]:
        self.CallFlowProto(
            crowdstrike.GetCrowdStrikeAgentID.__name__,
            next_state=self.ProcessGetCrowdStrikeAgentID.__name__,
        )

      # We will accept a partial KBInit rather than raise, so pass
      # require_complete=False.
      args = flows_pb2.KnowledgeBaseInitializationArgs(
          require_complete=False,
          lightweight=self.proto_args.lightweight
          if self.proto_args.HasField("lightweight")
          else True,
      )
      self.CallFlowProto(
          artifact.KnowledgeBaseInitializationFlow.__name__,
          flow_args=args,
          next_state=self.ProcessKnowledgeBase.__name__,
      )
    else:
      log_msg = "Unknown system type, skipping KnowledgeBaseInitializationFlow"
      if config.CONFIG["Interrogate.collect_crowdstrike_agent_id"]:
        log_msg += " and GetCrowdStrikeAgentID"
      self.Log(log_msg)

  @flow_base.UseProto2AnyResponses
  def InstallDate(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Stores the time when the OS was installed on the client."""
    if not responses.success or not list(responses):
      self.Log("Could not get InstallDate")
      return

    response = list(responses)[0]

    # When using relational flows, the response is serialized as an any value
    # and we get an equivalent RDFInteger here so we need to check for both.
    if response.Is(config_pb2.Int64Value.DESCRIPTOR):
      # New clients send the correct values already.
      date = config_pb2.Int64Value()
      date.ParseFromString(response.value)
      install_date = date.value
    elif response.Is(jobs_pb2.DataBlob.DESCRIPTOR):
      # For backwards compatibility.
      date = jobs_pb2.DataBlob()
      date.ParseFromString(response.value)
      install_date = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
          date.integer
      ).AsMicrosecondsSinceEpoch()
    else:
      self.Log("Unknown response type for InstallDate: %s" % type(response))
      return

    self.store.client_snapshot.install_time = install_date

  @flow_base.UseProto2AnyResponses
  def ProcessKnowledgeBase(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ):
    """Collect and store any extra non-kb artifacts."""
    if not responses.success or not list(responses):
      raise flow_base.FlowError(
          "Error while collecting the knowledge base: %s" % responses.status
      )

    kb = knowledge_base_pb2.KnowledgeBase()
    list(responses)[0].Unpack(kb)

    # Information already present in the knowledge base takes precedence.
    if not kb.os:
      kb.os = self.store.os

    if not kb.fqdn:
      kb.fqdn = self.store.fqdn

    self.store.client_snapshot.knowledge_base.CopyFrom(kb)

    if (
        config.CONFIG["Interrogate.collect_passwd_cache_users"]
        and kb.os == "Linux"
        # RRG agents always collect `passwd.cache` users as part of their
        # knowledgebase initialization flow.
        and self.python_agent_support
    ):
      condition = flows_pb2.FileFinderCondition()
      condition.condition_type = (
          flows_pb2.FileFinderCondition.Type.CONTENTS_REGEX_MATCH
      )
      condition.contents_regex_match.regex = (
          b"^%%users.username%%:[^:]*:[^:]*:[^:]*:[^:]*:[^:]+:[^:]*\n"
      )

      args = flows_pb2.FileFinderArgs()
      args.paths.append("/etc/passwd.cache")
      args.conditions.append(condition)

      self.CallClientProto(
          server_stubs.FileFinderOS,
          args,
          next_state=self.ProcessPasswdCacheUsers.__name__,
      )

    self.CallFlowProto(
        hardware.CollectHardwareInfo.__name__,
        next_state=self.ProcessHardwareInfo.__name__,
    )

    if (
        (kb.os == "Linux" or kb.os == "Darwin")
        # TODO: In RRG-based installations, this call should not be
        # necessary as this information should be collected as part of the mount
        # listing routine.
        and self.python_agent_support
    ):
      self.CallClientProto(
          server_stubs.StatFS,
          jobs_pb2.StatFSRequest(
              path_list=["/"],
          ),
          next_state=self.ProcessRootStatFS.__name__,
      )
    elif kb.os == "Windows":
      if self.rrg_support:
        action = rrg_stubs.QueryWmi()
        action.args.query = """
        SELECT
          VolumeName, VolumeSerialNumber, DeviceID, FileSystem,
          Size, FreeSpace
        FROM
          Win32_LogicalDisk
        """
        action.Call(self.ProcessRRGWin32LogicalDisk)
      else:
        self.CallClientProto(
            server_stubs.WmiQuery,
            jobs_pb2.WMIRequest(
                query="""
                SELECT *
                  FROM Win32_LogicalDisk
                """.strip(),
            ),
            next_state=self.ProcessWin32LogicalDisk.__name__,
        )

    try:
      # Update the client index for the rdf_objects.ClientSnapshot.
      client_index.ClientIndex().AddClient(
          mig_objects.ToRDFClientSnapshot(self.store.client_snapshot)
      )
    except db.UnknownClientError:
      pass

  @flow_base.UseProto2AnyResponses
  def ProcessHardwareInfo(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect hardware information: %s", responses.status)
      return

    for res in responses:
      response = sysinfo_pb2.HardwareInfo()
      res.Unpack(response)
      self.store.client_snapshot.hardware_info.CopyFrom(response)

  @flow_base.UseProto2AnyResponses
  def ProcessRootStatFS(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to get root filesystem metadata: %s", responses.status)
      return

    for response in responses:
      volume = sysinfo_pb2.Volume()
      response.Unpack(volume)
      self.store.client_snapshot.volumes.append(volume)

  @flow_base.UseProto2AnyResponses
  def ProcessRRGWin32LogicalDisk(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect `Win32_LogicalDisk`: %s", responses.status)
      return

    for response_any in responses:
      response = rrg_query_wmi_pb2.Result()
      response.ParseFromString(response_any.value)

      volume = self.store.client_snapshot.volumes.add()

      if "VolumeName" in response.row:
        volume.name = response.row["VolumeName"].string

      if "VolumeSerialNumber" in response.row:
        volume.serial_number = response.row["VolumeSerialNumber"].string

      if "DeviceID" in response.row:
        volume.windowsvolume.drive_letter = response.row["DeviceID"].string

      if "FileSystem" in response.row:
        volume.file_system_type = response.row["FileSystem"].string

      if "Size" in response.row:
        try:
          value = int(response.row["Size"].string)
        except (ValueError, TypeError) as error:
          self.Log(
              "Invalid Windows volume size: %s (%s)",
              response.row["Size"],
              error,
          )
        else:
          volume.total_allocation_units = value

      if "FreeSpace" in response.row:
        try:
          value = int(response.row["FreeSpace"].string)
        except (ValueError, TypeError) as error:
          self.Log(
              "Invalid Windows volume space: %s (%s)",
              response.row["FreeSpace"],
              error,
          )
        else:
          volume.actual_available_allocation_units = value

      # WMI gives us size and free space in bytes and does not give us sector
      # sizes, we use 1 for these. It is not clear how correct doing it is but
      # this is what the original parser did, so we replicate the behaviour.
      volume.bytes_per_sector = 1
      volume.sectors_per_allocation_unit = 1

  @flow_base.UseProto2AnyResponses
  def ProcessWin32LogicalDisk(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      self.Log("Failed to collect `Win32_LogicalDisk`: %s", responses.status)
      return

    for response in responses:
      response_proto_dict = jobs_pb2.Dict()
      response.Unpack(response_proto_dict)

      volume = sysinfo_pb2.Volume()

      for pair in response_proto_dict.dat:
        key = pair.k.string
        value = pair.v
        if key == "VolumeName":
          volume.name = value.string
        elif key == "VolumeSerialNumber":
          volume.serial_number = value.string
        elif key == "FileSystem":
          volume.file_system_type = value.string
        elif key == "DeviceID":
          volume.windowsvolume.drive_letter = value.string
        elif key == "DriveType":
          try:
            volume.windowsvolume.drive_type = value.integer
          except (ValueError, TypeError) as error:
            self.Log("Invalid Windows volume drive type: %s (%s)", value, error)
        elif key == "Size":
          try:
            volume.total_allocation_units = int(value.string)
          except (ValueError, TypeError) as error:
            self.Log("Invalid Windows volume size: %s (%s)", value, error)
        elif key == "FreeSpace":
          try:
            volume.actual_available_allocation_units = int(value.string)
          except (ValueError, TypeError) as error:
            self.Log("Invalid Windows volume space: %s (%s)", value, error)

      # WMI gives us size and free space in bytes and does not give us sector
      # sizes, we use 1 for these. It is not clear how correct doing it is but
      # this is what the original parser did, so we replicate the behaviour.
      volume.bytes_per_sector = 1
      volume.sectors_per_allocation_unit = 1

      self.store.client_snapshot.volumes.append(volume)

  FILTERED_IPS = ["127.0.0.1", "::1", "fe80::1"]

  @flow_base.UseProto2AnyResponses
  def EnumerateInterfaces(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Enumerates the interfaces."""
    if not (responses.success and responses):
      self.Log("Could not enumerate interfaces: %s" % responses.status)
      return

    interfaces: list[jobs_pb2.Interface] = []
    for response in responses:
      network_interface = jobs_pb2.Interface()
      response.Unpack(network_interface)
      interfaces.append(network_interface)
    interfaces.sort(key=lambda i: i.ifname)

    # TODO: Replace with `clear()` once upgraded.
    del self.store.client_snapshot.interfaces[:]
    self.store.client_snapshot.interfaces.extend(interfaces)

  @flow_base.UseProto2AnyResponses
  def EnumerateFilesystems(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Store all the local filesystems in the client."""
    if not responses.success or not responses:
      self.Log("Could not enumerate file systems.")
      return

    proto_filesystems = []
    for response in responses:
      filesystem = sysinfo_pb2.Filesystem()
      response.Unpack(filesystem)
      proto_filesystems.append(filesystem)

    del self.store.client_snapshot.filesystems[:]
    self.store.client_snapshot.filesystems.extend(proto_filesystems)

  def _ValidateLabel(self, label):
    if not label:
      raise ValueError("Label name cannot be empty.")

    is_valid = lambda char: char.isalnum() or char in " _./:-"
    if not all(map(is_valid, label)):
      raise ValueError(
          "Label name can only contain: a-zA-Z0-9_./:- but got: '%s'" % label
      )

  @flow_base.UseProto2AnyResponses
  def ClientInfo(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Obtain some information about the GRR client running."""
    if not responses.success or not list(responses):
      self.Log("Could not get ClientInfo.")
      return

    client_info = jobs_pb2.ClientInformation()
    list(responses)[0].Unpack(client_info)

    # Fetch labels for the client from Fleetspeak. If Fleetspeak doesn't
    # have any labels for the GRR client, fall back to labels reported by
    # the client.
    fleetspeak_labels = fleetspeak_utils.GetLabelsFromFleetspeak(self.client_id)
    if fleetspeak_labels:
      # TODO: Replace with `clear()` once upgraded.
      del client_info.labels[:]
      client_info.labels.extend(fleetspeak_labels)
      data_store.REL_DB.AddClientLabels(
          client_id=self.client_id, owner="GRR", labels=fleetspeak_labels
      )
    else:
      FLEETSPEAK_UNLABELED_CLIENTS.Increment()
      logging.warning(
          "Failed to get labels for Fleetspeak client %s.", self.client_id
      )

    sanitized_labels = []
    for label in client_info.labels:
      try:
        self._ValidateLabel(label)
        sanitized_labels.append(label)
      except ValueError:
        self.Log("Got invalid label: %s", label)

    # TODO: Replace with `clear()` once upgraded.
    del client_info.labels[:]
    client_info.labels.extend(sanitized_labels)

    self.store.client_snapshot.startup_info.client_info.CopyFrom(client_info)

    metadata = data_store.REL_DB.ReadClientMetadata(self.client_id)
    if metadata and metadata.last_fleetspeak_validation_info:
      self.store.client_snapshot.fleetspeak_validation_info.CopyFrom(
          metadata.last_fleetspeak_validation_info
      )

  @flow_base.UseProto2AnyResponses
  def ClientConfiguration(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Process client config."""
    if not responses.success or not list(responses):
      return

    response = jobs_pb2.Dict()
    list(responses)[0].Unpack(response)

    for pair in response.dat:
      str_v = str(mig_protodict.ToRDFDataBlob(pair.v).GetValue())
      self.store.client_snapshot.grr_configuration.append(
          objects_pb2.StringMapEntry(key=pair.k.string, value=str_v)
      )

  @flow_base.UseProto2AnyResponses
  def ClientLibraries(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Process client library information."""
    if not responses.success or not list(responses):
      return

    response = jobs_pb2.Dict()
    list(responses)[0].Unpack(response)
    for pair in response.dat:
      str_v = str(mig_protodict.ToRDFDataBlob(pair.v).GetValue())
      self.store.client_snapshot.library_versions.append(
          objects_pb2.StringMapEntry(key=pair.k.string, value=str_v)
      )

  @flow_base.UseProto2AnyResponses
  def ProcessGetCrowdStrikeAgentID(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      status = responses.status
      self.Log("Failed to obtain CrowdStrike agent identifier: %s", status)
      return

    for res in responses:
      if not res.Is(crowdstrike_pb2.GetCrowdstrikeAgentIdResult.DESCRIPTOR):
        raise TypeError(f"Unexpected response type: {res.type_url}")

      response = crowdstrike_pb2.GetCrowdstrikeAgentIdResult()
      res.Unpack(response)

      edr_agent = jobs_pb2.EdrAgent()
      edr_agent.name = "CrowdStrike"
      edr_agent.agent_id = response.agent_id
      self.store.client_snapshot.edr_agents.append(edr_agent)

  @flow_base.UseProto2AnyResponses
  def ProcessPasswdCacheUsers(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Processes user information obtained from the `/etc/passwd.cache` file."""
    if not responses.success or not list(responses):
      status = responses.status
      self.Log("failed to collect users from `/etc/passwd.cache`: %s", status)
      return

    users: list[knowledge_base_pb2.User] = []

    for response_any in responses:
      if not response_any.Is(flows_pb2.FileFinderResult.DESCRIPTOR):
        raise flow_base.FlowError(
            f"Unexpected response type: {response_any.type_url}"
        )

      response = flows_pb2.FileFinderResult()
      response_any.Unpack(response)

      for match in response.matches:
        match = match.data.decode("utf-8", "backslashreplace").strip()
        if not match:
          continue

        try:
          (username, _, uid, gid, full_name, homedir, shell) = match.split(":")
        except ValueError:
          self.Log("Unexpected `/etc/passwd.cache` line format: %s", match)
          continue

        try:
          uid = int(uid)
        except ValueError:
          self.Log("Invalid `/etc/passwd.cache` UID: %s", uid)
          continue

        try:
          gid = int(gid)
        except ValueError:
          self.Log("Invalid `/etc/passwd.cache` GID: %s", gid)
          continue

        users.append(
            knowledge_base_pb2.User(
                username=username,
                uid=uid,
                gid=gid,
                full_name=full_name,
                homedir=homedir,
                shell=shell,
            )
        )

    kb_users_by_username: dict[str, knowledge_base_pb2.User] = {
        user.username: user
        for user in self.store.client_snapshot.knowledge_base.users
    }

    for user in users:
      # User lookup should never fail as we only grepped for known users. If
      # this assumption does not hold for whatever reason, it is better to fail
      # loudly.
      kb_user = kb_users_by_username[user.username]

      if not kb_user.uid and user.uid:
        kb_user.uid = user.uid

      if not kb_user.gid and user.gid:
        kb_user.gid = user.gid

      if not kb_user.full_name and user.full_name:
        kb_user.full_name = user.full_name

      if not kb_user.homedir and user.homedir:
        kb_user.homedir = user.homedir

      if not kb_user.shell and user.shell:
        kb_user.shell = user.shell

  def NotifyAboutEnd(self):
    notification.Notify(
        self.creator,
        objects_pb2.UserNotification.Type.TYPE_CLIENT_INTERROGATED,
        "",
        objects_pb2.ObjectReference(
            reference_type=objects_pb2.ObjectReference.Type.CLIENT,
            client=objects_pb2.ClientReference(client_id=self.client_id),
        ),
    )

  def End(self) -> None:
    """Finalize client registration."""
    # Update summary and publish to the Discovery queue.
    try:
      data_store.REL_DB.WriteClientSnapshot(self.store.client_snapshot)
    except db.UnknownClientError:
      pass

    rdf_snapshot = mig_objects.ToRDFClientSnapshot(self.store.client_snapshot)
    rdf_summary = rdf_snapshot.GetSummary()
    rdf_summary.client_id = self.client_id
    rdf_summary.timestamp = rdfvalue.RDFDatetime.Now()
    rdf_summary.last_ping = rdf_summary.timestamp
    # Note that we do not use `self.rrg_version` as this one can include flow-
    # specific overrides (e.g. when RRG support is disabled) and so is less
    # reliable to use as a source for metadata.
    rdf_summary.rrg_version_major = self.rrg_startup.metadata.version.major
    rdf_summary.rrg_version_minor = self.rrg_startup.metadata.version.minor
    rdf_summary.rrg_version_patch = self.rrg_startup.metadata.version.patch
    rdf_summary.rrg_version_pre = self.rrg_startup.metadata.version.pre

    events.Events.PublishEvent("Discovery", rdf_summary, username=self.creator)

    self.SendReplyProto(self.store.client_snapshot)

    index = client_index.ClientIndex()
    index.AddClient(mig_objects.ToRDFClientSnapshot(self.store.client_snapshot))
    labels = self.store.client_snapshot.startup_info.client_info.labels
    if labels:
      data_store.REL_DB.AddClientLabels(
          self.store.client_snapshot.client_id, "GRR", labels
      )

    # Reset foreman rules check so active hunts can match against the new data
    data_store.REL_DB.WriteClientMetadata(
        self.client_id,
        last_foreman=data_store.REL_DB.MinTimestamp(),
    )
