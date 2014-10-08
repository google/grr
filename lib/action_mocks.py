#!/usr/bin/env python
"""A library of client action mocks for use in tests."""

import socket

from grr.client import actions
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import worker_mocks
from grr.test_data import client_fixture


class ActionMock(object):
  """A client mock which runs a real action.

  This can be used as input for TestFlowHelper.

  It is possible to mix mocked actions with real actions. Simple extend this
  class and add methods for the mocked actions, while instantiating with the
  list of read actions to run:

  class MixedActionMock(ActionMock):
    def __init__(self):
      super(MixedActionMock, self).__init__("RealAction")

    def MockedAction(self, args):
      return []

  Will run the real action "RealAction" at the same time as a mocked action
  MockedAction.
  """

  def __init__(self, *action_names, **kwargs):
    self.client_id = kwargs.get("client_id")
    self.action_names = action_names
    self.action_classes = dict(
        [(k, v) for (k, v) in actions.ActionPlugin.classes.items()
         if k in action_names])
    self.action_counts = dict((x, 0) for x in action_names)

    # Create a single long lived client worker mock.
    self.client_worker = worker_mocks.FakeClientWorker()

  def RecordCall(self, action_name, action_args):
    pass

  def HandleMessage(self, message):
    """Consume a message and execute the client action."""
    message.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

    # We allow special methods to be specified for certain actions.
    if hasattr(self, message.name):
      return getattr(self, message.name)(message.payload)

    self.RecordCall(message.name, message.payload)

    # Try to retrieve a suspended action from the client worker.
    try:
      suspended_action_id = message.payload.iterator.suspended_action
      action = self.client_worker.suspended_actions[suspended_action_id]

    except (AttributeError, KeyError):
      # Otherwise make a new action instance.
      action_cls = self.action_classes[message.name]
      action = action_cls(grr_worker=self.client_worker)

    action.Execute(message)
    self.action_counts[message.name] += 1

    return self.client_worker.Drain()


class RecordingActionMock(ActionMock):

  def __init__(self, *action_names):
    super(RecordingActionMock, self).__init__(*action_names)
    self.recorded_args = {}

  def RecordCall(self, action_name, action_args):
    self.recorded_args.setdefault(action_name, []).append(action_args)


class InvalidActionMock(object):
  """An action mock which raises for all actions."""

  def HandleMessage(self, unused_message):
    raise RuntimeError("Invalid Action Mock.")


class UnixVolumeClientMock(ActionMock):
  """A mock of client filesystem volumes."""
  unix_local = rdfvalue.UnixVolume(mount_point="/usr")
  unix_home = rdfvalue.UnixVolume(mount_point="/")
  path_results = [
      rdfvalue.Volume(
          unix=unix_local, bytes_per_sector=4096, sectors_per_allocation_unit=1,
          actual_available_allocation_units=50, total_allocation_units=100),
      rdfvalue.Volume(
          unix=unix_home, bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=10,
          total_allocation_units=100)]

  def StatFS(self, _):
    return self.path_results


class WindowsVolumeClientMock(ActionMock):
  """A mock of client filesystem volumes."""
  windows_d = rdfvalue.WindowsVolume(drive_letter="D:")
  windows_c = rdfvalue.WindowsVolume(drive_letter="C:")
  path_results = [
      rdfvalue.Volume(
          windows=windows_d, bytes_per_sector=4096,
          sectors_per_allocation_unit=1,
          actual_available_allocation_units=50, total_allocation_units=100),
      rdfvalue.Volume(
          windows=windows_c, bytes_per_sector=4096,
          sectors_per_allocation_unit=1, actual_available_allocation_units=10,
          total_allocation_units=100)]

  def WmiQuery(self, query):
    if query.query == u"SELECT * FROM Win32_LogicalDisk":
      return client_fixture.WMI_SAMPLE
    else:
      return None


class MemoryClientMock(ActionMock):
  """A mock of client state including memory actions."""

  def InstallDriver(self, _):
    return []

  def UninstallDriver(self, _):
    return []

  def GetMemoryInformation(self, _):
    reply = rdfvalue.MemoryInformation(
        device=rdfvalue.PathSpec(
            path=r"\\.\pmem",
            pathtype=rdfvalue.PathSpec.PathType.MEMORY))
    reply.runs.Append(offset=0x1000, length=0x10000)
    reply.runs.Append(offset=0x20000, length=0x10000)

    return [reply]


class InterrogatedClient(ActionMock):
  """A mock of client state."""

  def InitializeClient(self, system="Linux", version="12.04"):
    self.system = system
    self.version = version
    self.response_count = 0
    self.recorded_messages = []

  def HandleMessage(self, message):
    """Record all messages."""
    self.recorded_messages.append(message)
    return super(InterrogatedClient, self).HandleMessage(message)

  def GetPlatformInfo(self, _):
    self.response_count += 1
    return [rdfvalue.Uname(
        system=self.system,
        node="test_node",
        release="5",
        version=self.version,
        machine="i386")]

  def GetInstallDate(self, _):
    self.response_count += 1
    return [rdfvalue.DataBlob(integer=100)]

  def EnumerateInterfaces(self, _):
    self.response_count += 1
    return [rdfvalue.Interface(
        mac_address="123456",
        addresses=[
            rdfvalue.NetworkAddress(
                address_type=rdfvalue.NetworkAddress.Family.INET,
                human_readable="100.100.100.1",
                packed_bytes=socket.inet_aton("100.100.100.1"),
                )]
        )]

  def EnumerateFilesystems(self, _):
    self.response_count += 1
    return [rdfvalue.Filesystem(device="/dev/sda",
                                mount_point="/mnt/data")]

  def GetClientInfo(self, _):
    self.response_count += 1
    return [rdfvalue.ClientInformation(
        client_name=config_lib.CONFIG["Client.name"],
        client_version=int(config_lib.CONFIG["Client.version_numeric"]),
        build_time=config_lib.CONFIG["Client.build_time"],
        labels=["GRRLabel1", "Label2"],
        )]

  def GetUserInfo(self, user):
    self.response_count += 1
    user.homedir = "/usr/local/home/%s" % user.username
    user.full_name = user.username.capitalize()
    return [user]

  def GetConfiguration(self, _):
    self.response_count += 1
    return [rdfvalue.Dict({"Client.control_urls":
                           ["http://localhost:8001/control"], "Client.poll_min":
                           1.0})]

  def WmiQuery(self, query):
    if query.query == u"SELECT * FROM Win32_LogicalDisk":
      self.response_count += 1
      return client_fixture.WMI_SAMPLE
    elif query.query.startswith("Select * "
                                "from Win32_NetworkAdapterConfiguration"):
      self.response_count += 1
      rdf_dict = rdfvalue.Dict()
      wmi_properties = (client_fixture.WMIWin32NetworkAdapterConfigurationMock.
                        __dict__.iteritems())
      for key, value in wmi_properties:
        if not key.startswith("__"):
          try:
            rdf_dict[key] = value
          except TypeError:
            rdf_dict[key] = "Failed to encode: %s" % value
      return [rdf_dict]
    else:
      return None

