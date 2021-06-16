#!/usr/bin/env python
"""Test classes for clients-related testing."""

import codecs
import collections
import os
import platform
import subprocess
import tempfile
import types

from grr_response_client import actions
from grr_response_client.client_actions import standard

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.util import context
from grr_response_server import action_registry
from grr_response_server import server_stubs

from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


class EmptyActionTest(test_lib.GRRBaseTest):
  """Test the client Actions."""

  def tearDown(self):
    # Reset the global last progress time to prevent order-dependent tests.
    actions.ActionPlugin.last_progress_time = (
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

  def RunAction(self, action_cls, arg=None, grr_worker=None):
    if arg is None:
      arg = rdf_flows.GrrMessage()

    self.results = []
    action = self._GetActionInstance(action_cls, grr_worker=grr_worker)

    action.status = rdf_flows.GrrStatus(
        status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    action.Run(arg)

    return self.results

  def ExecuteAction(self,
                    action_cls,
                    arg=None,
                    grr_worker=None,
                    session_id=None):
    message = rdf_flows.GrrMessage(
        name=action_cls.__name__,
        payload=arg,
        auth_state="AUTHENTICATED",
        session_id=session_id)

    self.results = []
    action = self._GetActionInstance(action_cls, grr_worker=grr_worker)

    action.Execute(message)

    return self.results

  def _GetActionInstance(self, action_cls, grr_worker=None):
    """Run an action and generate responses.

    This basically emulates GRRClientWorker.HandleMessage().

    Args:
       action_cls: The action class to run.
       grr_worker: The GRRClientWorker instance to use. If not provided we make
         a new one.

    Returns:
      A list of response protobufs.
    """

    # A mock SendReply() method to collect replies.
    def mock_send_reply(mock_self, reply=None, **kwargs):
      if reply is None:
        reply = mock_self.out_rdfvalues[0](**kwargs)
      self.results.append(reply)

    if grr_worker is None:
      grr_worker = worker_mocks.FakeClientWorker()

    action = action_cls(grr_worker=grr_worker)
    action.SendReply = types.MethodType(mock_send_reply, action)

    return action


class OSSpecificClientTests(EmptyActionTest):
  """OS-specific client action tests.

  We need to temporarily disable the actionplugin class registry to avoid
  registering actions for other OSes.
  """

  def setUp(self):
    super().setUp()
    action_reg_stubber = utils.Stubber(actions.ActionPlugin, "classes", {})
    action_reg_stubber.Start()
    self.addCleanup(action_reg_stubber.Stop)
    binary_command_stubber = utils.Stubber(standard.ExecuteBinaryCommand,
                                           "classes", {})
    binary_command_stubber.Start()
    self.addCleanup(binary_command_stubber.Stop)


# pylint: disable=g-bad-name
class MockWindowsProcess(object):
  """A mock windows process."""

  def __init__(self, name="cmd", pid=10, ppid=1):

    self._name = name
    self.pid = pid
    self._ppid = ppid

  def name(self):
    return self._name

  def ppid(self):
    return self._ppid

  def exe(self):
    return "cmd.exe"

  def username(self):
    return "test"

  def cmdline(self):
    return ["c:\\Windows\\cmd.exe", "/?"]

  def create_time(self):
    return 1217061982.375000

  def status(self):
    return "running"

  def cwd(self):
    return b"X:\\RECEP\xc3\x87\xc3\x95ES"

  def num_threads(self):
    return 1

  def cpu_times(self):
    cpu_times = collections.namedtuple(
        "CPUTimes", ["user", "system", "children_user", "children_system"])
    return cpu_times(
        user=1.0, system=1.0, children_user=1.0, children_system=1.0)

  def cpu_percent(self):
    return 10.0

  def memory_info(self):
    meminfo = collections.namedtuple("Meminfo", ["rss", "vms"])
    return meminfo(rss=100000, vms=150000)

  def memory_percent(self):
    return 10.0

  def open_files(self):
    return []

  def connections(self):
    return []

  def nice(self):
    return 10

  def as_dict(self, attrs=None):
    """Return mock process as dict."""

    dic = {}
    if attrs is None:
      return dic
    for name in attrs:
      if hasattr(self, name):
        attr = getattr(self, name)
        if callable(attr):
          dic[name] = attr()
        else:
          dic[name] = attr
      else:
        dic[name] = None
    return dic

  def oneshot(self):
    return context.NullContext(None)


# pylint: enable=g-bad-name


# pylint: disable=invalid-name
class WMIWin32NetworkAdapterConfigurationMock(object):
  """Mock netadapter."""

  class UnSerializable(object):
    pass

  Caption = "[000005] Intel Gigabit Network Connection"
  DatabasePath = "%SystemRoot%\\System32\\drivers\\etc"
  DefaultIPGateway = ["192.168.1.254", "fe80::211:5eaa:fe00:222"]
  Description = "Intel Gigabit Network Connection"
  DHCPEnabled = True
  DHCPLeaseExpires = "20140825162259.123456-420"
  DHCPLeaseObtained = "20140825122259.123456-420"
  DHCPServer = "192.168.1.1"
  DNSDomain = "internal.example.com"
  DNSDomainSuffixSearchOrder = [
      "blah.example.com", "ad.example.com", "internal.example.com",
      "example.com"
  ]
  DNSEnabledForWINSResolution = False
  DNSHostName = "MYHOST-WIN"
  DNSServerSearchOrder = ["192.168.1.1", "192.168.255.81", "192.168.128.88"]
  DomainDNSRegistrationEnabled = False
  FullDNSRegistrationEnabled = True
  GatewayCostMetric = [0, 256]
  Index = 7
  InterfaceIndex = 11
  IPAddress = [
      "192.168.1.20", "ffff::ffff:aaaa:1111:aaaa",
      "dddd:0:8888:6666:bbbb:aaaa:eeee:bbbb",
      "dddd:0:8888:6666:bbbb:aaaa:ffff:bbbb"
  ]
  IPConnectionMetric = 10
  IPEnabled = True
  IPFilterSecurityEnabled = False
  IPSecPermitIPProtocols = []
  IPSecPermitTCPPorts = []
  IPSecPermitUDPPorts = []
  IPSubnet = ["255.255.254.0", "192", "168", "1"]
  MACAddress = "BB:AA:EE:CC:DD:CC"
  ServiceName = "e1e"
  SettingID = "{AAAAAAAA-EEEE-DDDD-AAAA-CCCCCCCCCCCC}"
  TcpipNetbiosOptions = 0
  WINSEnableLMHostsLookup = True
  WINSScopeID = ""
  NestingTest = {
      "one": {
          "two": [3, 4],
          "broken": UnSerializable(),
          "three": {}
      },
      "four": [],
      "five": "astring",
      "six": [None, None, ""],
      "seven": None,
      "rdfvalue": rdf_protodict.Dict(a="asdf")
  }
  OpaqueObject = UnSerializable()


# pylint: enable=invalid-name


class Popen(object):
  """A mock object for subprocess.Popen."""

  def __init__(self, run, stdout, stderr, stdin, env=None, cwd=None):
    del env, cwd  # Unused.
    Popen.running_args = run
    Popen.stdout = stdout
    Popen.stderr = stderr
    Popen.stdin = stdin
    Popen.returncode = 0

    try:
      # Store the content of the executable file.
      Popen.binary = open(run[0], "rb").read()
    except IOError:
      Popen.binary = None

  def communicate(self):  # pylint: disable=g-bad-name
    return b"stdout here", b"stderr here"


class Test(server_stubs.ClientActionStub):
  """A test action which can be used in mocks."""
  in_rdfvalue = rdf_protodict.DataBlob
  out_rdfvalues = [rdf_protodict.DataBlob]


action_registry.RegisterAdditionalTestClientAction(Test)


def import_to_registry(data):
  r"""Imports the given data to the Registry.

  Example:
    Windows Registry Editor Version 5.00

    [HKEY_LOCAL_MACHINE\SOFTWARE\GRR_TEST]
    "foobar"=dword:0
    "bar":"baz"

  Args:
    data: a unicode string of Registry data, following the .REG-format.
      See https://en.wikipedia.org/wiki/Windows_Registry#.REG_files

  Raises:
    RuntimeError: if the function is not called under Windows.
  """
  if platform.system() != "Windows":
    raise RuntimeError("import_to_registry can only be called under Windows.")

  # NamedTemporaryFile cannot be used on Win, because the file is locked while
  # open for writes and deleted as soon as it is closed.
  filehandle, filename = tempfile.mkstemp(suffix=".reg")
  try:
    with os.fdopen(filehandle, "wb") as fd:
      fd.write(codecs.BOM_UTF16_LE)
      fd.write(data.encode("utf_16_le"))
  except:
    raise
  else:
    subprocess.check_call(["REG", "IMPORT", filename])
  finally:
    os.unlink(filename)
