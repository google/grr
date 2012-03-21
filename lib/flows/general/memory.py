#!/usr/bin/env python
#
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
from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils

from grr.proto import jobs_pb2

FLAGS = flags.FLAGS


# File names for memory drivers.
WIN_MEM = "mdd.{arch}.signed.sys"
LIN_MEM = "crash-{kernel}.ko"
OSX_MEM = "osxmem"

DRIVER_BASE = "/config/drivers"


class LoadMemoryDriver(flow.GRRFlow):
  """Load a memory driver on the client."""

  category = "/Memory/"

  def __init__(self, driver_name="mdd", driver_display_name="mdd",
               driver_path="c:\\windows\\system32\\mdd.sys", **kwargs):
    self.driver_name = driver_name
    self.driver_display_name = driver_display_name
    self.driver_path = driver_path
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state="InitializeDriver")
  def Start(self):
    """Start processing."""
    self.client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.system = self.client.Get(self.client.Schema.SYSTEM)
    release = self.client.Get(self.client.Schema.OS_RELEASE)
    module = self.GetMemoryModule(self.system, release)
    if not module:
      raise IOError("No memory driver currently available for this system.")

    # Create a protobuf containing the request.
    driver_pb = module.data
    install_pb = jobs_pb2.InstallDriverRequest(driver=driver_pb)
    if self.driver_name:
      install_pb.driver_name = self.driver_name
    if self.driver_display_name:
      install_pb.driver_display_name = self.driver_display_name
    if self.driver_path:
      install_pb.write_path = self.driver_path

    # We want to force unload old driver and reload the current one.
    install_pb.force_reload = 1

    self.CallClient("InstallDriver", install_pb,
                    next_state="InitializeDriver")

  @flow.StateHandler(next_state="ConfirmInitialize")
  def InitializeDriver(self, responses):
    """Confirm the load succeeded."""
    if responses.success:
      self.Log("Successfully initialized memory driver.")
      self.CallClient("InitializeMemoryDriver",
                      jobs_pb2.Path(path=self.driver_name),
                      next_state="ConfirmInitialize")
    else:
      flow.FlowError("Memory driver failed to Load.")

  @flow.StateHandler(jobs_pb2.StatResponse)
  def ConfirmInitialize(self, responses):
    """Confirm the driver initialized and add it to the VFS."""
    if responses.success:
      response = responses.First()

      # Need somewhere in the VFS we can read this device.
      # For Windows we need to create it in devices.
      if self.system == "Windows":
        self._device_urn = aff4.ROOT_URN.Add(self.client_id).Add(
            "devices/winmemory")
      else:
        # We can trust the client to give us a sensible device path.
        self._device_urn = self.client.PathspecToURN(response.pathspec,
                                                     self.client_id)
      fd = aff4.FACTORY.Create(self._device_urn, "VFSFile", token=self.token)
      fd.Set(fd.Schema.STAT(response))
      fd.Set(fd.Schema.PATHSPEC(response.pathspec))
      fd.Close()
    else:
      raise flow.FlowError("Failed to initialize")

  def End(self):
    if self.flow_pb.state != jobs_pb2.FlowPB.ERROR:
      self.Notify("ViewObject", self._device_urn,
                  "Driver successfully initialized.")

  def GetMemoryModule(self, system, release):
    """Given a host, return an appropriate memory module.

    Args:
      system: String containing the type of system.
      release: String containing release info.

    Returns:
      A GRRSignedDriver object None.

    Raises:
      IOError: on inability to get driver.

    The driver we are sending should have a signature associated
    This would get verified by the client (independently of OS driver signing).
    Having this mechanism will allow for offline signing of drivers to reduce
    the risk of the system being used to deploy evil things.
    """
    if system == "Windows":
      # TODO(user): Gather Windows 64 bitness to select driver correctly.
      path = WIN_MEM.format(arch="64")
    elif system == "Darwin":
      path = OSX_MEM
    elif system == "Linux":
      path = LIN_MEM.format(kernel=release)
    else:
      raise IOError("No OS Memory support for platform %s" % system)

    driver_path = utils.JoinPath(DRIVER_BASE, path)
    fd = aff4.FACTORY.Open(driver_path, mode="r", token=self.token)
    driver_pb = fd.Get(fd.Schema.DRIVER)
    if not driver_pb:
      raise IOError("No OS Memory module available for %s %s" %
                    (system, release))
    return driver_pb
