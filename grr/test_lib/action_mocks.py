#!/usr/bin/env python
"""A library of client action mocks for use in tests."""

import collections
import io
import itertools
from typing import Mapping
from typing import Type

from grr_response_client import actions
from grr_response_client import client_actions
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import file_finder
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import osquery
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import cloud as rdf_cloud
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import action_registry
from grr_response_server import client_fixture
from grr_response_server import server_stubs
from grr.test_lib import client_test_lib
from grr.test_lib import worker_mocks


class ActionMock(object):
  """A client mock which runs a real action.

  This can be used as input for TestFlowHelper.

  It is possible to mix mocked actions with real actions. Simple extend this
  class and add methods for the mocked actions, while instantiating with the
  list of real actions to run:

  class MixedActionMock(ActionMock):
    def __init__(self):
      super().__init__(client_actions.RealAction)

    def MockedAction(self, args):
      return []

  Will run the real action "RealAction" at the same time as a mocked action
  MockedAction.
  """

  def __init__(self, *action_classes, **kwargs):
    self.client_id = kwargs.get("client_id")
    self.action_classes = {cls.__name__: cls for cls in action_classes}
    self.action_counts = collections.defaultdict(lambda: 0)
    self.recorded_args = {}
    self._recorded_messages = []

    self.client_worker = (
        kwargs.get("client_worker", None) or worker_mocks.FakeClientWorker())

  # TODO(hanuszczak): Ideally, the constructor of this class should be adjusted
  # so that it supports supplying registry instead of taking arbitrary class
  # types and registering them by the class name.
  #
  # However, the current usage is so prevalent across the codebase that fixing
  # this behaviour is not possible with a single change. Thus, we introduce this
  # method to allow for gradual migration.
  @classmethod
  def With(
      cls,
      registry: Mapping[str, Type[actions.ActionPlugin]],
  ) -> "ActionMock":
    """Constructs an action mock that uses the provided action registry."""
    instance = cls()
    instance.action_classes = registry
    return instance

  @classmethod
  def WithRegistry(cls) -> "ActionMock":
    """Constructs an action mock with the real action registry."""
    return cls.With(client_actions.REGISTRY)

  def _RecordCall(self, message):
    self._recorded_messages.append(message)
    self.recorded_args.setdefault(message.name, []).append(message.payload)

  def GenerateStatusMessage(self, message, response_id=1, status=None):
    return rdf_flows.GrrMessage(
        session_id=message.session_id,
        name=message.name,
        response_id=response_id,
        request_id=message.request_id,
        task_id=message.Get("task_id"),
        payload=rdf_flows.GrrStatus(
            status=status or rdf_flows.GrrStatus.ReturnedStatus.OK),
        type=rdf_flows.GrrMessage.Type.STATUS)

  def _HandleMockAction(self, message):
    """Handles the action in case it's a mock."""
    responses = getattr(self, message.name)(message.payload)
    ret = []
    for i, r in enumerate(responses):
      ret.append(
          rdf_flows.GrrMessage(
              session_id=message.session_id,
              request_id=message.request_id,
              task_id=message.Get("task_id"),
              name=message.name,
              response_id=i + 1,
              payload=r,
              type=rdf_flows.GrrMessage.Type.MESSAGE))

    ret.append(self.GenerateStatusMessage(message, response_id=len(ret) + 1))
    return ret

  def HandleMessage(self, message):
    """Consume a message and execute the client action."""
    message.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # This is a mock client action, we process this separately.
    if hasattr(self, message.name):
      return self._HandleMockAction(message)

    self._RecordCall(message)

    if message.name not in self.action_classes:
      return [
          self.GenerateStatusMessage(
              message, status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR)
      ]

    action_cls = self.action_classes[message.name]
    action = action_cls(grr_worker=self.client_worker)

    action.Execute(message)
    self.action_counts[message.name] += 1

    return self.client_worker.Drain()

  @property
  def recorded_messages(self):
    return self._recorded_messages


class Store(server_stubs.ClientActionStub):
  """A test client action."""
  pass


action_registry.RegisterAdditionalTestClientAction(Store)


class CPULimitClientMock(ActionMock):
  """A mock for testing resource limits."""

  in_rdfvalue = rdf_protodict.DataBlob
  out_rdfvalues = []

  def __init__(self,
               storage=None,
               user_cpu_usage=None,
               system_cpu_usage=None,
               network_usage=None,
               runtime_us=None):
    super().__init__()
    if storage is not None:
      self.storage = storage
    else:
      self.storage = {}
    self.__name__ = "Store"
    self.user_cpu_usage = itertools.cycle(user_cpu_usage or [None])
    self.system_cpu_usage = itertools.cycle(system_cpu_usage or [None])
    self.network_usage = itertools.cycle(network_usage or [None])
    self.runtime_us = itertools.cycle(runtime_us or [None])

  def HandleMessage(self, message):
    self.storage.setdefault("cpulimit", []).append(message.cpu_limit)
    self.storage.setdefault("networklimit",
                            []).append(message.network_bytes_limit)
    self.storage.setdefault("runtimelimit", []).append(message.runtime_limit_us)
    return [self.GenerateStatusMessage(message)]

  def GenerateStatusMessage(self, message, response_id=1):
    cpu_time_used = rdf_client_stats.CpuSeconds(
        user_cpu_time=next(self.user_cpu_usage),
        system_cpu_time=next(self.system_cpu_usage))
    network_bytes_sent = next(self.network_usage)
    runtime_us = next(self.runtime_us)

    return rdf_flows.GrrMessage(
        session_id=message.session_id,
        name=message.name,
        response_id=response_id,
        request_id=message.request_id,
        payload=rdf_flows.GrrStatus(
            status=rdf_flows.GrrStatus.ReturnedStatus.OK,
            cpu_time_used=cpu_time_used,
            network_bytes_sent=network_bytes_sent,
            runtime_us=runtime_us),
        type=rdf_flows.GrrMessage.Type.STATUS)


class InvalidActionMock(ActionMock):
  """An action mock which raises for all actions."""

  def HandleMessage(self, unused_message):
    raise RuntimeError("Invalid Action Mock.")


class MemoryClientMock(ActionMock):
  """A mock of client state including memory actions."""

  def __init__(self, *args, **kwargs):
    super(MemoryClientMock,
          self).__init__(standard.HashBuffer, standard.HashFile,
                         standard.GetFileStat, standard.TransferBuffer, *args,
                         **kwargs)


class GetFileClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GetFileClientMock,
          self).__init__(standard.HashBuffer, standard.GetFileStat,
                         standard.TransferBuffer, *args, **kwargs)


class GetFileWithFailingStatClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GetFileWithFailingStatClientMock,
          self).__init__(standard.HashBuffer, standard.TransferBuffer, *args,
                         **kwargs)

  def GetFileStat(self, unused_message):
    raise RuntimeError("stat is intentionally failing")


class FileFinderClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(FileFinderClientMock,
          self).__init__(file_fingerprint.FingerprintFile, searching.Find,
                         searching.Grep, standard.HashBuffer, standard.HashFile,
                         standard.GetFileStat, standard.TransferBuffer, *args,
                         **kwargs)


class FileFinderClientMockWithTimestamps(FileFinderClientMock):
  """A mock for the FileFinder that adds timestamps to some files."""

  def HandleMessage(self, message):
    responses = super(FileFinderClientMockWithTimestamps,
                      self).HandleMessage(message)

    predefined_values = {
        "auth.log": (1333333330, 1333333332, 1333333334),
        "dpkg.log": (1444444440, 1444444442, 1444444444),
        "dpkg_false.log": (1555555550, 1555555552, 1555555554)
    }

    for response in responses:
      payload = response.payload
      if isinstance(payload, rdf_client_fs.StatEntry):
        basename = payload.pathspec.Basename()
        try:
          payload.st_atime = predefined_values[basename][0]
          payload.st_mtime = predefined_values[basename][1]
          payload.st_ctime = predefined_values[basename][2]
          response.payload = payload
        except KeyError:
          pass

    return responses


class ListProcessesMock(FileFinderClientMock):
  """Client with real file actions and mocked-out ListProcesses."""

  def __init__(self, processes_list):
    super().__init__()
    self.processes_list = processes_list

  def ListProcesses(self, _):
    return self.processes_list


class ClientFileFinderClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super().__init__(file_finder.FileFinderOS, *args, **kwargs)


class CollectMultipleFilesClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(CollectMultipleFilesClientMock,
          self).__init__(file_finder.FileFinderOS, standard.HashFile,
                         standard.GetFileStat, standard.HashBuffer,
                         standard.TransferBuffer,
                         file_fingerprint.FingerprintFile, *args, **kwargs)


class MultiGetFileClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(MultiGetFileClientMock,
          self).__init__(standard.HashFile, standard.GetFileStat,
                         standard.HashBuffer, standard.TransferBuffer,
                         file_fingerprint.FingerprintFile, *args, **kwargs)


class ListDirectoryClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(ListDirectoryClientMock,
          self).__init__(standard.ListDirectory, standard.GetFileStat, *args,
                         **kwargs)


class GlobClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super().__init__(searching.Find, standard.GetFileStat, *args, **kwargs)


class GrepClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GrepClientMock,
          self).__init__(file_fingerprint.FingerprintFile, searching.Find,
                         searching.Grep, standard.HashBuffer,
                         standard.GetFileStat, standard.TransferBuffer, *args,
                         **kwargs)


class OsqueryClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super().__init__(
        #  Osquery action mocks below
        osquery.Osquery,
        #  MultiGetFile action mocks below
        standard.HashFile,
        standard.GetFileStat,
        standard.HashBuffer,
        standard.TransferBuffer,
        file_fingerprint.FingerprintFile,
        *args,
        **kwargs)


class UpdateAgentClientMock(ActionMock):
  """Client with a mocked-out UpdateAgent client-action."""

  def __init__(self):
    super().__init__()

    self._requests = []

  def UpdateAgent(self, execute_binary_request):
    """Replacement for the real UpdateAgent client-action."""
    self._requests.append(execute_binary_request)
    return []

  def GetDownloadedFileContents(self):
    """Returns the raw contents of the file sent by the server."""
    bytes_buffer = io.BytesIO()
    requests_by_offset = {request.offset: request for request in self._requests}

    offsets = [r.offset for r in self._requests]
    if offsets[0] != 0 or max(offsets) != offsets[-1]:
      raise ValueError("Received blobs in the wrong order.")

    requests_by_offset = {request.offset: request for request in self._requests}

    expected_offset = 0
    while expected_offset in requests_by_offset:
      request = requests_by_offset[expected_offset]
      data = request.executable.data
      expected_offset += len(data)
      bytes_buffer.write(data)

    return bytes_buffer.getvalue()


class InterrogatedClient(ActionMock):
  """A mock of client state."""

  LABEL1 = "GRRLabel1"
  LABEL2 = "Label2"
  LABEL3 = "[broken]"

  def __init__(self, *args, **kwargs):
    super(InterrogatedClient,
          self).__init__(admin.GetLibraryVersions,
                         file_fingerprint.FingerprintFile, searching.Find,
                         standard.GetMemorySize, standard.HashBuffer,
                         standard.HashFile, standard.ListDirectory,
                         standard.GetFileStat, standard.TransferBuffer, *args,
                         **kwargs)

  def InitializeClient(self,
                       system="Linux",
                       version="12.04",
                       kernel="3.13.0-39-generic",
                       fqdn="test_node.test",
                       release="5"):
    self.system = system
    self.version = version
    self.kernel = kernel
    self.release = release
    self.response_count = 0
    self.fqdn = fqdn

  def GetPlatformInfo(self, _):
    self.response_count += 1
    return [
        rdf_client.Uname(
            system=self.system,
            fqdn=self.fqdn,
            release=self.release,
            version=self.version,
            kernel=self.kernel,
            machine="i386")
    ]

  def GetInstallDate(self, _):
    self.response_count += 1
    return [rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)]

  def EnumerateInterfaces(self, _):
    self.response_count += 1
    return [
        rdf_client_network.Interface(
            mac_address=b"123456",
            addresses=[
                rdf_client_network.NetworkAddress(
                    human_readable_address="100.100.100.1"),
            ])
    ]

  def EnumerateFilesystems(self, _):
    self.response_count += 1
    return [
        rdf_client_fs.Filesystem(device="/dev/sda", mount_point="/mnt/data")
    ]

  def GetClientInfo(self, _):
    self.response_count += 1
    return [
        rdf_client.ClientInformation(
            client_name=config.CONFIG["Client.name"],
            client_version=int(config.CONFIG["Source.version_numeric"]),
            build_time=config.CONFIG["Client.build_time"],
            labels=[self.LABEL1, self.LABEL2, self.LABEL3],
        )
    ]

  def GetUserInfo(self, user):
    self.response_count += 1
    user.homedir = "/usr/local/home/%s" % user.username
    user.full_name = user.username.capitalize()
    return [user]

  def GetConfiguration(self, _):
    self.response_count += 1
    return [
        rdf_protodict.Dict({
            "Client.server_urls": [u"http://localhost:8001/"],
            "Client.poll_min": 1.0
        })
    ]

  def WmiQuery(self, query):
    if query.query == u"SELECT * FROM Win32_LogicalDisk":
      self.response_count += 1
      return client_fixture.WMI_SAMPLE
    elif query.query.startswith("Select * "
                                "from Win32_NetworkAdapterConfiguration"):
      self.response_count += 1
      rdf_dict = rdf_protodict.Dict()
      mock = client_test_lib.WMIWin32NetworkAdapterConfigurationMock
      wmi_properties = mock.__dict__.items()
      for key, value in wmi_properties:
        if not key.startswith("__"):
          try:
            rdf_dict[key] = value
          except TypeError:
            rdf_dict[key] = "Failed to encode: %s" % value
      return [rdf_dict]
    else:
      return []

  def GetCloudVMMetadata(self, args):
    result_list = []
    for request in args.requests:
      result_list.append(
          rdf_cloud.CloudMetadataResponse(
              label=request.label or request.url, text=request.label))
    return [
        rdf_cloud.CloudMetadataResponses(
            responses=result_list, instance_type="GOOGLE")
    ]


class UnixVolumeClientMock(ListDirectoryClientMock):
  """A mock of client filesystem volumes."""
  unix_local = rdf_client_fs.UnixVolume(mount_point="/usr")
  unix_home = rdf_client_fs.UnixVolume(mount_point="/")
  path_results = [
      rdf_client_fs.Volume(
          unixvolume=unix_local,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50,
          total_allocation_units=100),
      rdf_client_fs.Volume(
          unixvolume=unix_home,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=10,
          total_allocation_units=100)
  ]

  def StatFS(self, _):
    return self.path_results


class WindowsVolumeClientMock(ListDirectoryClientMock):
  """A mock of client filesystem volumes."""
  windows_d = rdf_client_fs.WindowsVolume(drive_letter="D:")
  windows_c = rdf_client_fs.WindowsVolume(drive_letter="C:")
  path_results = [
      rdf_client_fs.Volume(
          windowsvolume=windows_d,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50,
          total_allocation_units=100),
      rdf_client_fs.Volume(
          windowsvolume=windows_c,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=10,
          total_allocation_units=100)
  ]

  def WmiQuery(self, query):
    if query.query == u"SELECT * FROM Win32_LogicalDisk":
      return client_fixture.WMI_SAMPLE
    else:
      return None
