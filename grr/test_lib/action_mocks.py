#!/usr/bin/env python
"""A library of client action mocks for use in tests."""

import socket

from grr import config
from grr_response_client.client_actions import admin
from grr_response_client.client_actions import file_finder
from grr_response_client.client_actions import file_fingerprint
from grr_response_client.client_actions import searching
from grr_response_client.client_actions import standard
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import cloud
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.server.grr_response_server import client_fixture
from grr.server.grr_response_server import server_stubs
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
      super(MixedActionMock, self).__init__(client_actions.RealAction)

    def MockedAction(self, args):
      return []

  Will run the real action "RealAction" at the same time as a mocked action
  MockedAction.
  """

  def __init__(self, *action_classes, **kwargs):
    self.client_id = kwargs.get("client_id")
    self.action_classes = {cls.__name__: cls for cls in action_classes}
    self.action_counts = dict((cls_name, 0) for cls_name in self.action_classes)
    self.recorded_args = {}

    self.client_worker = (
        kwargs.get("client_worker", None) or worker_mocks.FakeClientWorker())

  def RecordCall(self, action_name, action_args):
    self.recorded_args.setdefault(action_name, []).append(action_args)

  def HandleMessage(self, message):
    """Consume a message and execute the client action."""
    message.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # We allow special methods to be specified for certain actions.
    if hasattr(self, message.name):
      return getattr(self, message.name)(message.payload)

    self.RecordCall(message.name, message.payload)
    action_cls = self.action_classes[message.name]
    action = action_cls(grr_worker=self.client_worker)

    action.Execute(message)
    self.action_counts[message.name] += 1

    return self.client_worker.Drain()


class CPULimitClientMock(object):
  """A mock for testing resource limits."""

  in_rdfvalue = rdf_protodict.DataBlob

  def __init__(self, storage):
    # Register us as an action plugin.
    # TODO(user): this is a hacky shortcut and should be fixed.
    server_stubs.ClientActionStub.classes["Store"] = self
    self.storage = storage
    self.__name__ = "Store"

  def HandleMessage(self, message):
    self.storage.setdefault("cpulimit", []).append(message.cpu_limit)
    self.storage.setdefault("networklimit",
                            []).append(message.network_bytes_limit)


class InvalidActionMock(object):
  """An action mock which raises for all actions."""

  def HandleMessage(self, unused_message):
    raise RuntimeError("Invalid Action Mock.")


class MemoryClientMock(ActionMock):
  """A mock of client state including memory actions."""

  def __init__(self, *args, **kwargs):
    super(MemoryClientMock, self).__init__(
        standard.HashBuffer, standard.HashFile, standard.GetFileStat,
        standard.TransferBuffer, *args, **kwargs)


class GetFileClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GetFileClientMock,
          self).__init__(standard.HashBuffer, standard.GetFileStat,
                         standard.TransferBuffer, *args, **kwargs)


class FileFinderClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(FileFinderClientMock, self).__init__(
        file_fingerprint.FingerprintFile, searching.Find, searching.Grep,
        standard.HashBuffer, standard.HashFile, standard.GetFileStat,
        standard.TransferBuffer, *args, **kwargs)


class ListProcessesMock(FileFinderClientMock):
  """Client with real file actions and mocked-out ListProcesses."""

  def __init__(self, processes_list):
    super(ListProcessesMock, self).__init__()
    self.processes_list = processes_list

  def ListProcesses(self, _):
    return self.processes_list


class ClientFileFinderClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(ClientFileFinderClientMock, self).__init__(file_finder.FileFinderOS,
                                                     *args, **kwargs)


class MultiGetFileClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(MultiGetFileClientMock, self).__init__(
        standard.HashFile, standard.GetFileStat, standard.HashBuffer,
        standard.TransferBuffer, file_fingerprint.FingerprintFile, *args,
        **kwargs)


class ListDirectoryClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(ListDirectoryClientMock, self).__init__(
        standard.ListDirectory, standard.GetFileStat, *args, **kwargs)


class GlobClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GlobClientMock, self).__init__(searching.Find, standard.GetFileStat,
                                         *args, **kwargs)


class GrepClientMock(ActionMock):

  def __init__(self, *args, **kwargs):
    super(GrepClientMock, self).__init__(
        file_fingerprint.FingerprintFile, searching.Find, searching.Grep,
        standard.HashBuffer, standard.GetFileStat, standard.TransferBuffer,
        *args, **kwargs)


class InterrogatedClient(ActionMock):
  """A mock of client state."""

  def __init__(self, *args, **kwargs):
    super(InterrogatedClient, self).__init__(
        admin.GetLibraryVersions, file_fingerprint.FingerprintFile,
        searching.Find, standard.GetMemorySize, standard.HashBuffer,
        standard.HashFile, standard.ListDirectory, standard.GetFileStat,
        standard.TransferBuffer, *args, **kwargs)

  def InitializeClient(self,
                       system="Linux",
                       version="12.04",
                       kernel="3.13.0-39-generic",
                       fqdn="test_node.test"):
    self.system = system
    self.version = version
    self.kernel = kernel
    self.response_count = 0
    self.recorded_messages = []
    self.fqdn = fqdn

  def HandleMessage(self, message):
    """Record all messages."""
    self.recorded_messages.append(message)
    return super(InterrogatedClient, self).HandleMessage(message)

  def GetPlatformInfo(self, _):
    self.response_count += 1
    return [
        rdf_client.Uname(
            system=self.system,
            fqdn=self.fqdn,
            release="5",
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
        rdf_client.Interface(
            mac_address="123456",
            addresses=[
                rdf_client.NetworkAddress(
                    address_type=rdf_client.NetworkAddress.Family.INET,
                    human_readable="100.100.100.1",
                    packed_bytes=socket.inet_pton(socket.AF_INET,
                                                  "100.100.100.1"),
                )
            ])
    ]

  def EnumerateFilesystems(self, _):
    self.response_count += 1
    return [rdf_client.Filesystem(device="/dev/sda", mount_point="/mnt/data")]

  def GetClientInfo(self, _):
    self.response_count += 1
    return [
        rdf_client.ClientInformation(
            client_name=config.CONFIG["Client.name"],
            client_version=int(config.CONFIG["Source.version_numeric"]),
            build_time=config.CONFIG["Client.build_time"],
            labels=["GRRLabel1", "Label2"],
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
            "Client.server_urls": ["http://localhost:8001/"],
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
      wmi_properties = mock.__dict__.iteritems()
      for key, value in wmi_properties:
        if not key.startswith("__"):
          try:
            rdf_dict[key] = value
          except TypeError:
            rdf_dict[key] = "Failed to encode: %s" % value
      return [rdf_dict]
    else:
      return None

  def GetCloudVMMetadata(self, args):
    result_list = []
    for request in args.requests:
      result_list.append(
          cloud.CloudMetadataResponse(
              label=request.label or request.url, text=request.label))
    return [
        cloud.CloudMetadataResponses(
            responses=result_list, instance_type="GOOGLE")
    ]


class UnixVolumeClientMock(ListDirectoryClientMock):
  """A mock of client filesystem volumes."""
  unix_local = rdf_client.UnixVolume(mount_point="/usr")
  unix_home = rdf_client.UnixVolume(mount_point="/")
  path_results = [
      rdf_client.Volume(
          unixvolume=unix_local,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50,
          total_allocation_units=100),
      rdf_client.Volume(
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
  windows_d = rdf_client.WindowsVolume(drive_letter="D:")
  windows_c = rdf_client.WindowsVolume(drive_letter="C:")
  path_results = [
      rdf_client.Volume(
          windowsvolume=windows_d,
          bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50,
          total_allocation_units=100),
      rdf_client.Volume(
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
