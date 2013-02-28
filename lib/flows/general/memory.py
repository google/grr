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



import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.flows.general import grep
from grr.lib.flows.general import transfer

# File names for memory drivers.
WIN_MEM = "winpmem.{arch}.sys"
LIN_MEM = "pmem-{kernel}.ko"
OSX_MEM = "pmem"

DRIVER_BASE = "/config/drivers/{os}/memory/"

WIN_DRV_PATH = "c:\\windows\\system32\\drivers\\{name}.sys"
LIN_DRV_PATH = "/tmp/{name}"
OSX_DRV_PATH = "/tmp/{name}"


class ImageMemory(flow.GRRFlow):
  """Load a memory driver on the client.

  Note that AnalyzeClientMemory will do this for you if you call it.
  """

  category = "/Memory/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.InstallDriverRequestType(
          description=("An optional InstallDriverRequest proto to control "
                       "driver installation. If not set, the default "
                       "installation proto will be used."),
          name="driver_installer",
          default=None)
      )

  @flow.StateHandler(next_state="GetFile")
  def Start(self, _):
    self.CallFlow("LoadMemoryDriver", next_state="GetFile")

  @flow.StateHandler(next_state="Done")
  def GetFile(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver.")
    memory_information = responses.First()
    pathspec = rdfvalue.RDFPathSpec(
        path=memory_information.device.path,
        pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY"))
    self.CallFlow("GetFile", pathspec=pathspec, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError("Transfer failed %s" % responses.status)
    else:
      stat = responses.First()
      self.SendReply(stat)
      self.Notify("ViewObject", stat.aff4path, "File transferred successfully")


class ImageMemoryToSocket(transfer.SendFile):
  """This flow sends a memory image to remote listener.

  It will first initialize the memory device, then send the image to the
  specified socket.

  To use this flow, choose a key and an IV in hex format (if run from the GUI,
  there will be a pregenerated pair key and iv for you to use) and run a
  listener on the server you want to use like this:

  nc -l <port> | openssl aes-128-cbc -d -K <key> -iv <iv> > <filename>

  Returns to parent flow:
    A rdfvalue.StatEntry of the sent file.
  """

  category = "/Memory/"

  # TODO(user): Handle the path, pathtype args post refactor.

  @flow.StateHandler(next_state="SendFile")
  def Start(self):
    self.CallFlow("LoadMemoryDriver", next_state="SendFile")

  @flow.StateHandler(next_state="Done")
  def SendFile(self, responses):
    """Queue the sending of the file if the driver loaded."""
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver.")
    memory_information = responses.First()
    pathspec = rdfvalue.RDFPathSpec(
        path=memory_information.device.path,
        pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY"))
    self.CallClient("SendFile", key=utils.SmartStr(self.key),
                    iv=utils.SmartStr(self.iv),
                    pathspec=pathspec,
                    address_family=self.family,
                    host=self.host, port=self.port,
                    next_state="Done")


class LoadMemoryDriver(flow.GRRFlow):
  """Load a memory driver on the client.

  Note that AnalyzeClientMemory will do this for you if you call it.
  """
  category = "/Memory/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.InstallDriverRequestType(
          description=("An optional InstallDriverRequest proto to control "
                       "driver installation. If not set, the default "
                       "installation proto will be used."),
          name="driver_installer",
          default=None),
      type_info.Bool(
          name="reload_if_loaded",
          description=("if True and driver is already loaded we reload it."),
          default=False)
      )

  @flow.StateHandler(next_state=["LoadDriver", "CheckMemoryInformation"])
  def Start(self):
    """Check if driver is already loaded."""
    self._device_urn = aff4.ROOT_URN.Add(self.client_id).Add("devices/memory")

    if self.driver_installer is None:
      # Fetch the driver installer from the data store.
      self.driver_installer = GetMemoryModule(self.client_id, token=self.token)

      # Create a protobuf containing the request.
      if not self.driver_installer:
        raise IOError("Could not determine path for memory driver. No module "
                      "available for this platform.")

    if self.reload_if_loaded:
      self.CallState(next_state="LoadDriver")
    else:
      self.CallClient("GetMemoryInformation",
                      rdfvalue.RDFPathSpec(
                          path=self.driver_installer.device_path,
                          pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY")),
                      next_state="CheckMemoryInformation")

  @flow.StateHandler(next_state=["LoadDriver", "GotMemoryInformation"])
  def CheckMemoryInformation(self, responses):
    """Check if the driver is loaded and responding."""
    if responses.success:
      # Memory driver exists, send reply directly to GotMemoryInformation.
      self.CallState(next_state="GotMemoryInformation",
                     messages=[responses.First()])
    else:
      # Driver needs loading.
      self.CallState(next_state="LoadDriver")

  @flow.StateHandler(next_state=["InstalledDriver"])
  def LoadDriver(self, _):
    # We want to force unload old driver and reload the current one.
    self.driver_installer.force_reload = 1
    self.CallClient("InstallDriver", self.driver_installer,
                    next_state="InstalledDriver")

  @flow.StateHandler(next_state="GotMemoryInformation")
  def InstalledDriver(self, responses):
    if not responses.success:
      raise flow.FlowError("Could not install memory driver %s",
                           responses.status.error_message)

    self.CallClient("GetMemoryInformation",
                    rdfvalue.RDFPathSpec(
                        path=self.driver_installer.device_path,
                        pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY")),
                    next_state="GotMemoryInformation")

  @flow.StateHandler()
  def GotMemoryInformation(self, responses):
    """Confirm the driver initialized and add it to the VFS."""
    if responses.success:
      response = responses.First()

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
    if self.rdf_flow.state != rdfvalue.Flow.Enum("ERROR"):
      self.Notify("ViewObject", self._device_urn,
                  "Driver successfully initialized.")


def GetMemoryModule(client_id, token):
  """Given a host, return an appropriate memory module.

  Args:
    client_id: The client_id of the host to use.
    token: Token to use for access.

  Returns:
    A tuple of GRRSignedDriver, InstallDriverRequest or None, None

  Raises:
    IOError: on inability to get driver.

  The driver we are sending should have a signature associated
  This would get verified by the client (independently of OS driver signing).
  Having this mechanism will allow for offline signing of drivers to reduce
  the risk of the system being used to deploy evil things.
  """

  client = aff4.FACTORY.Open(client_id, token=token)
  system = client.Get(client.Schema.SYSTEM)
  release = client.Get(client.Schema.OS_RELEASE)

  if system == "Windows":
    arch = client.Get(client.Schema.ARCH)
    if arch == "AMD64":
      path = WIN_MEM.format(arch="64")
    elif arch == "x86":
      path = WIN_MEM.format(arch="32")
    else:
      raise IOError("No memory driver for the architecture %s" % arch)
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
                           mode="r", token=token)

  # Get the signed driver.
  driver_blob = fd.Get(fd.Schema.BINARY)
  if not driver_blob:
    msg = "No OS Memory module available for %s %s" % (system, release)
    logging.info(msg)
    raise IOError(msg)

  logging.info("Found driver %s", driver_path)

  # How should this driver be installed?
  driver_installer = fd.Get(fd.Schema.INSTALLATION)

  # If we didn't get a write path, we make one.
  if not driver_installer.write_path:
    if driver_installer.driver_name:
      driver_installer.write_path = inst_path.format(
          name=driver_installer.driver_name)
    else:
      driver_installer.write_path = inst_path.format(name="pmem")

  # Add the driver to the installer.
  driver_installer.driver = driver_blob

  return driver_installer


class AnalyzeClientMemory(flow.GRRFlow):
  """Runs client side analysis using volatility.

  This flow takes a list of volatility plugins to run. It first calls
  LoadMemoryDriver to ensure a Memory driver is loaded.
  It then sends the list of volatility commands to the client. The client will
  run those plugins using the client's copy of volatility.

  Each plugin will return it's results and they will be stored in the
  /analysis part of the vfs.
  """

  category = "/Memory/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.InstallDriverRequestType(
          description=("An optional InstallDriverRequest proto to control "
                       "driver installation. If not set, the default "
                       "installation proto will be used."),
          name="driver_installer",
          default=None),

      type_info.VolatilityRequestType(
          description="A request for the client's volatility subsystem."),

      type_info.String(
          description="""
The path to the output container for this flow. Will be created
under the client. supports format variables {u}, {p} and {t} for
user, plugin and time. E.g. /analysis/{p}/{u}-{t}.""",
          name="output",
          default="analysis/{p}/{u}-{t}"),

      type_info.String(
          description="A list of volatility plugins to run on the client.",
          name="plugins",
          default="pslist,dlllist,modules"),
      )

  @flow.StateHandler(next_state=["RunVolatilityPlugins"])
  def Start(self, _):
    self.CallFlow("LoadMemoryDriver", next_state="RunVolatilityPlugins",
                  driver_installer=self.driver_installer)

  @flow.StateHandler(next_state=["ProcessVolatilityPlugins", "Done"])
  def RunVolatilityPlugins(self, responses):
    """Run all the plugins and process the responses."""
    if responses.success:
      memory_information = responses.First()

      if memory_information:
        self.request.device = memory_information.device

      else:
        # We loaded the driver previously and stored the path in the AFF4 VFS -
        # we try to use that instead.
        device_urn = aff4.ROOT_URN.Add(self.client_id).Add("devices/memory")
        fd = aff4.FACTORY.Open(device_urn, "MemoryImage", token=self.token)
        device = fd.Get(fd.Schema.LAYOUT)
        if device:
          self.request.device = device

      self.CallFlow("VolatilityPlugins", request=self.request,
                    plugins=self.plugins, next_state="Done", output=self.output)
    else:
      raise flow.FlowError("Failed to Load driver: %s" % responses.status)

  @flow.StateHandler()
  def Done(self, responses):
    pass

  @flow.StateHandler()
  def End(self):
    out_urn = aff4.ROOT_URN.Add(self.client_id).Add("analysis")
    self.Notify("ViewObject", out_urn,
                "Completed execution of volatility plugins.")


class UnloadMemoryDriver(LoadMemoryDriver):
  """Unloads a memory driver on the client."""

  category = "/Memory/"
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.InstallDriverRequestType(
          description=("An optional InstallDriverRequest proto to control "
                       "driver installation. If not set, the default "
                       "installation proto will be used."),
          name="driver_installer",
          default=None)
      )

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    """Start processing."""
    if not self.driver_installer:
      module, self.driver_installer = GetMemoryModule(self.client_id,
                                                      self.token)
      if not module:
        raise IOError("No memory driver currently available for this system.")

      # Create a protobuf containing the request.
      self.driver_installer.driver = module.data

    self.CallClient("UninstallDriver", self.driver_installer,
                    next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed to uninstall memory driver: %s",
                           responses.status.error_message)

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
      self.Log("Error while loading memory driver: %s" %
               responses.status.error_message)
      return

    if self.load_driver:
      self.load_driver = False
      self.CallFlow("LoadMemoryDriver", next_state="Start")
    else:
      super(GrepAndDownload, self).Start()

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
      self.Log("Error while downloading memory image: %s" %
               responses.status.error_message)
    else:
      self.Log("Memory image successfully downloaded.")
