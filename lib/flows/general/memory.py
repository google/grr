#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Flows for controlling access to memory.

These flows allow for distributing memory access modules to clients and
performing basic analysis.
"""



from grr.client import conf as flags
import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.lib.flows.general import grep

from grr.proto import jobs_pb2

FLAGS = flags.FLAGS


# File names for memory drivers.
WIN_MEM = "winpmem.{arch}.sys"
LIN_MEM = "pmem-{kernel}.ko"
OSX_MEM = "pmem"

DRIVER_BASE = "/config/drivers/{os}/memory/"

WIN_DRV_PATH = "c:\\windows\\system32\\drivers\\{name}.sys"
LIN_DRV_PATH = "/tmp/{name}"
OSX_DRV_PATH = "/tmp/{name}"


class LoadMemoryDriver(flow.GRRFlow):
  """Load a memory driver on the client."""

  category = "/Memory/"
  out_protobuf = jobs_pb2.MemoryInfomation
  flow_typeinfo = {"driver_installer": type_info.ProtoOrNone(
      jobs_pb2.InstallDriverRequest)}

  def __init__(self, driver_installer=None, **kwargs):
    """Constructor.

    Args:
      driver_installer: An optional InstallDriverRequest proto to control driver
         installation. If not set, the default installation proto will be used.
    """
    self.driver_installer = driver_installer
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["InstallDriver", "GetMemoryInformation"])
  def Start(self):
    """Start processing."""
    if self.driver_installer is None:
      module = self.GetMemoryModule(self.client_id)
      if not module:
        raise IOError("No memory driver currently available for this system.")

      # Create a protobuf containing the request.
      self.driver_installer.driver.MergeFrom(module)

    # We want to force unload old driver and reload the current one.
    self.driver_installer.force_reload = 1
    self.CallClient("InstallDriver", self.driver_installer,
                    next_state="InstallDriver")

    self.CallClient("GetMemoryInformation",
                    jobs_pb2.Path(path=self.driver_installer.device_path,
                                  pathtype=jobs_pb2.Path.MEMORY),
                    next_state="GetMemoryInformation")

  @flow.StateHandler()
  def InstallDriver(self, responses):
    if not responses.success:
      self.Log("Failed to install memory driver: %s",
               responses.status)

  @flow.StateHandler()
  def GetMemoryInformation(self, responses):
    """Confirm the driver initialized and add it to the VFS."""
    if responses.success:
      response = responses.First()

      self._device_urn = aff4.ROOT_URN.Add(self.client_id).Add(
          "devices/memory")

      fd = aff4.FACTORY.Create(self._device_urn, "MemoryImage",
                               token=self.token)
      layout = fd.Schema.LAYOUT(response)
      fd.Set(fd.Schema.PATHSPEC(response.device))
      fd.Set(layout)
      fd.Close()

      # Let a parent flow know which driver was installed.
      self.SendReply(layout)
    else:
      raise flow.FlowError("Failed to query device %s" %
                           self.driver_installer.device_path)

  @flow.StateHandler()
  def End(self):
    if self.flow_pb.state != jobs_pb2.FlowPB.ERROR:
      self.Notify("ViewObject", self._device_urn,
                  "Driver successfully initialized.")

  def GetMemoryModule(self, client_id):
    """Given a host, return an appropriate memory module.

    Args:
      client_id: The client_id of the host to use.

    Returns:
      A GRRSignedDriver object or None.

    Raises:
      IOError: on inability to get driver.

    The driver we are sending should have a signature associated
    This would get verified by the client (independently of OS driver signing).
    Having this mechanism will allow for offline signing of drivers to reduce
    the risk of the system being used to deploy evil things.
    """

    client = aff4.FACTORY.Open(client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    release = client.Get(client.Schema.OS_RELEASE)

    if system == "Windows":
      # TODO(user): Gather Windows 64 bitness to select driver correctly.
      path = WIN_MEM.format(arch="64")
      sys_os = "windows"
      inst_path = WIN_DRV_PATH
    elif system == "Darwin":
      path = OSX_MEM
      sys_os = "osx"
      inst_path = OSX_DRV_PATH
    elif system == "Linux":
      sys_os = "linux"
      path = LIN_MEM.format(kernel=release)
      inst_path = LIN_DRV_PATH
    else:
      raise IOError("No OS Memory support for platform %s" % system)

    driver_path = utils.JoinPath(DRIVER_BASE.format(os=sys_os), path)
    fd = aff4.FACTORY.Create(driver_path, "GRRMemoryDriver",
                             mode="r", token=self.token)

    # Get the signed driver.
    driver_blob = fd.Get(fd.Schema.BINARY)
    if not driver_blob:
      msg = "No OS Memory module available for %s %s" % (system, release)
      logging.info(msg)
      raise IOError(msg)

    logging.info("Found driver %s", driver_path)

    # How should this driver be installed?
    self.driver_installer = fd.Get(fd.Schema.INSTALLATION).data

    # If we didn't get a write path, we make one.
    if not self.driver_installer.write_path:
      if self.driver_installer.driver_name:
        self.driver_installer.write_path = inst_path.format(
            name=self.driver_installer.driver_name)
      else:
        self.driver_installer.write_path = inst_path.format(name="pmem")

    return driver_blob.data


class AnalyseClientMemory(flow.GRRFlow):
  """Runs client side analysis using volatility."""

  category = "/Memory/"

  def __init__(self, plugins="pslist,dlllist,modules", driver_installer=None,
               profile=None, **kwargs):
    """Runs volatility plugins on the client.

    Args:
      plugins: A list of volatility plugins to run on the client.
      driver_installer: An optional driver installer protobuf.
      profile: A volatility profile. None guesses.
    """
    super(AnalyseClientMemory, self).__init__(**kwargs)
    self.plugins = plugins
    self.driver_installer = driver_installer
    self.profile = profile

  @flow.StateHandler(next_state=["RunVolatilityPlugins"])
  def Start(self):
    self.CallFlow("LoadMemoryDriver", next_state="RunVolatilityPlugins",
                  driver_installer=self.driver_installer)

  @flow.StateHandler(next_state=["ProcessVolatilityPlugins", "Done"])
  def RunVolatilityPlugins(self, responses):
    """Run all the plugins and process the responses."""
    if responses.success:
      memory_information = responses.First()

      self.CallFlow("VolatilityPlugins", plugins=self.plugins,
                    devicepath=memory_information.device, profile=self.profile,
                    next_state="Done")
    else:
      raise flow.FlowError("Failed to Load driver: %s" % responses.status)

  @flow.StateHandler()
  def Done(self, responses):
    pass

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.device_urn,
                "Completed execution of volatility plugins.")


class UnloadMemoryDriver(LoadMemoryDriver):
  """Unloads a memory driver on the client."""

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    """Start processing."""
    module = self.GetMemoryModule(self.client_id)
    if not module:
      raise IOError("No memory driver currently available for this system.")

    # Create a protobuf containing the request.
    self.driver_installer.driver.MergeFrom(module)

    self.CallClient("UninstallDriver", self.driver_installer,
                    next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed to uninstall memory driver: %s",
                           responses.status)

  @flow.StateHandler()
  def End(self):
    pass


class GrepAndDownload(grep.Grep):
  """Downloads client memory if a signature is found."""

  category = "/Memory/"

  def __init__(self, load_driver=True, **kwargs):
    """Downloads client memory if a signature is found.

    This flow greps memory or a file on the client for a pattern or a regex
    and, if the pattern is found, downloads the file/memory.

    Args:
      load_driver: Load the memory driver before grepping.
    """

    self.load_driver = load_driver
    super(GrepAndDownload, self).__init__(**kwargs)

  @flow.StateHandler(next_state=["Start", "StoreResults"])
  def Start(self, responses):
    if not responses.success:
      self.Log("Error while loading memory driver: %s" % responses.status)
      return

    if self.load_driver:
      self.load_driver = False
      self.CallFlow("LoadMemoryDriver", next_state="Start")
    else:
      super(GrepAndDownload, self). Start()

  @flow.StateHandler(next_state=["Done"])
  def StoreResults(self, responses):
    if not responses.success:
      self.Log("Error grepping file: %s.", responses.status)
      return

    super(GrepAndDownload, self).StoreResults(responses)

    if responses:
      self.CallFlow("GetFile", pathspec=self.request.target,
                    next_state="Done")
    else:
      self.Log("Grep did not yield any results.")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      self.Log("Error while downloading memory image: %s" % responses.status)
    else:
      self.Log("Memory image successfully downloaded.")
