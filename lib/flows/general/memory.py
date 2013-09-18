#!/usr/bin/env python
"""Flows for controlling access to memory.

These flows allow for distributing memory access modules to clients and
performing basic analysis.
"""



import time

import logging
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.flows.general import transfer
from grr.proto import flows_pb2


class ImageMemoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ImageMemoryArgs


class ImageMemory(flow.GRRFlow):
  """Image a client's memory.

  This flow loads a memory driver on the client and uploads a memory image
  to the grr server. Note that this flow will take some time depending on the
  connection speed to the server so there might be substantial memory smear. If
  this is a problem, consider using the DownloadMemoryImage flow which makes a
  local copy of the image first to circumvent this problem.
  """

  category = "/Memory/"
  args_type = ImageMemoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="GetFile")
  def Start(self, _):
    self.CallFlow("LoadMemoryDriver",
                  driver_installer=self.args.driver_installer,
                  next_state="GetFile")

  @flow.StateHandler(next_state="Done")
  def GetFile(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver.")
    memory_information = responses.First()
    pathspec = rdfvalue.PathSpec(
        path=memory_information.device.path,
        pathtype=rdfvalue.PathSpec.PathType.MEMORY)
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
    pathspec = rdfvalue.PathSpec(
        path=memory_information.device.path,
        pathtype=rdfvalue.PathSpec.PathType.MEMORY)

    self.CallClient("SendFile", key=utils.SmartStr(self.state.key),
                    iv=utils.SmartStr(self.state.iv),
                    pathspec=pathspec,
                    address_family=self.state.family,
                    host=self.state.host, port=self.state.port,
                    next_state="Done")


class DownloadMemoryImageArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.DownloadMemoryImageArgs


class DownloadMemoryImage(flow.GRRFlow):
  """Copy memory image to local disk then retrieve the file.

  If the file transfer fails you can attempt to download again using the GetFile
  flow without needing to copy all of memory to disk again.  Note that if the
  flow fails, you'll need to run Administrative/DeleteGRRTempFiles to clean up
  the disk.

  Returns to parent flow:
    A rdfvalue.CopyPathToFileRequest.
  """

  category = "/Memory/"
  args_type = DownloadMemoryImageArgs

  # This flow is also a basic flow.
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="CopyFile")
  def Start(self):
    self.CallFlow("LoadMemoryDriver", next_state="CopyFile")

  @flow.StateHandler(next_state="DownloadFile")
  def CopyFile(self, responses):
    """Copy the memory image if the driver loaded."""
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver.")

    memory_information = responses.First()
    self.CallClient("CopyPathToFile",
                    offset=self.args.offset,
                    length=self.args.length,
                    src_path=memory_information.device,
                    dest_dir=self.args.destdir,
                    gzip_output=self.args.gzip,
                    next_state="DownloadFile")

  @flow.StateHandler(next_state="DeleteFile")
  def DownloadFile(self, responses):
    if not responses.success:
      raise flow.FlowError(
          "Error copying memory to file: %s." % responses.status)

    self.state.Register("dest_path", responses.First().dest_path)
    self.CallFlow("GetFile", pathspec=self.state.dest_path,
                  next_state="DeleteFile")

  @flow.StateHandler(next_state="End")
  def DeleteFile(self, responses):
    """Delete the temporary file from disk."""
    if not responses.success:
      # Leave file on disk to allow the user to retry GetFile without having to
      # copy the whole memory image again.
      raise flow.FlowError("Transfer of %s failed %s" % (self.state.dest_path,
                                                         responses.status))

    stat = responses.First()
    self.SendReply(stat)
    self.state.Register("downloaded_file", stat.aff4path)
    self.Status("Downloaded %s successfully" % self.state.downloaded_file)
    self.CallClient("DeleteGRRTempFiles",
                    self.state.dest_path, next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    if not responses.success:
      raise flow.FlowError("Delete of %s failed %s" % (self.state.dest_path,
                                                       responses.status))
    self.Notify("ViewObject", self.state.downloaded_file,
                "Memory image transferred successfully")


class LoadMemoryDriverArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.LoadMemoryDriverArgs


class LoadMemoryDriver(flow.GRRFlow):
  """Load a memory driver on the client.

  Note that AnalyzeClientMemory will do this for you if you call it.
  """
  category = "/Memory/"
  args_type = LoadMemoryDriverArgs

  @flow.StateHandler(next_state=["LoadDriver", "CheckMemoryInformation"])
  def Start(self):
    """Check if driver is already loaded."""
    self.state.Register("device_urn", self.client_id.Add("devices/memory"))
    self.state.Register("driver_installer", self.args.driver_installer)

    if not self.args.driver_installer:
      # Fetch the driver installer from the data store.
      self.state.driver_installer = GetMemoryModule(self.client_id,
                                                    token=self.token)

      # Create a protobuf containing the request.
      if not self.state.driver_installer:
        raise IOError("Could not determine path for memory driver. No module "
                      "available for this platform.")

    if self.args.reload_if_loaded:
      self.CallStateInline(next_state="LoadDriver")
    else:
      self.CallClient("GetMemoryInformation",
                      rdfvalue.PathSpec(
                          path=self.state.driver_installer.device_path,
                          pathtype=rdfvalue.PathSpec.PathType.MEMORY),
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
    self.state.driver_installer.force_reload = 1
    self.CallClient("InstallDriver", self.state.driver_installer,
                    next_state="InstalledDriver")

  @flow.StateHandler(next_state="GotMemoryInformation")
  def InstalledDriver(self, responses):
    if not responses.success:
      raise flow.FlowError("Could not install memory driver %s",
                           responses.status)

    self.CallClient("GetMemoryInformation",
                    rdfvalue.PathSpec(
                        path=self.state.driver_installer.device_path,
                        pathtype=rdfvalue.PathSpec.PathType.MEMORY),
                    next_state="GotMemoryInformation")

  @flow.StateHandler()
  def GotMemoryInformation(self, responses):
    """Confirm the driver initialized and add it to the VFS."""
    if responses.success:
      response = responses.First()

      fd = aff4.FACTORY.Create(self.state.device_urn, "MemoryImage",
                               token=self.token)
      layout = fd.Schema.LAYOUT(response)
      fd.Set(fd.Schema.PATHSPEC(response.device))
      fd.Set(layout)
      fd.Close()

      # Let a parent flow know which driver was installed.
      self.SendReply(layout)
    else:
      raise flow.FlowError("Failed to query device %s (%s)" %
                           (self.state.driver_installer.device_path,
                            responses.status))

  @flow.StateHandler()
  def End(self):
    if self.state.context.state != rdfvalue.Flow.State.ERROR:
      self.Notify("ViewObject", self.state.device_urn,
                  "Driver successfully initialized.")


def GetMemoryModule(client_id, token):
  """Given a host, return an appropriate memory module.

  Args:
    client_id: The client_id of the host to use.
    token: Token to use for access.

  Returns:
    A GRRSignedDriver.

  Raises:
    IOError: on inability to get driver.

  The driver is retrieved from the AFF4 configuration space according to the
  client's known attributes. The exact layout of the driver's configuration
  space structure is determined by the configuration system.

  The driver we are sending should have a signature associated with it. This
  would get verified by the client (independently of OS driver signing).  Having
  this mechanism will allow for offline signing of drivers to reduce the risk of
  the system being used to deploy evil things.

  Since the client itself will verify the signature of the client, on the server
  we must retrieve the corresponding private keys to the public key that the
  client has. If the keys depend on the client's architecture, and operating
  system, the configuration system will give the client different keys depending
  on its operating system or architecture. In this case we need to match these
  keys, and retrieve the correct keys.

  For example, the configuration file can specify different keys for windows and
  OSX clients:

  Platform:Windows:
    PrivateKeys.driver_signing_private_key: |
      .... Key 1 .... (Private)

    Client.driver_signing_public_key:  |
      .... Key 1 .... (Public)

    Arch:amd64:
      MemoryDriver.aff4_path:  |
          aff4:/config/drivers/windows/pmem_amd64.sys

    Arch:i386:
      MemoryDriver.aff4_path:  |
          aff4:/config/drivers/windows/pmem_x86.sys
  """
  client_context = []
  client = aff4.FACTORY.Open(client_id, token=token)
  system = client.Get(client.Schema.SYSTEM)
  if system:
    client_context.append("Platform:%s" % system)

  release = client.Get(client.Schema.OS_RELEASE)
  if release:
    client_context.append(utils.SmartStr(release))

  arch = utils.SmartStr(client.Get(client.Schema.ARCH)).lower()
  # Support synonyms for i386.
  if arch == "x86":
    arch = "i386"

  if arch:
    client_context.append("Arch:%s" % arch)

  # Now query the configuration system for the driver.
  aff4_path = config_lib.CONFIG.Get("MemoryDriver.aff4_path",
                                    context=client_context)

  if aff4_path:
    logging.debug("Will fetch driver at %s for client %s",
                  aff4_path, client_id)
    fd = aff4.FACTORY.Open(aff4_path, aff4_type="GRRMemoryDriver",
                           mode="r", token=token)

    # Get the signed driver.
    driver_blob = fd.Get(fd.Schema.BINARY)
    if driver_blob:
      # How should this driver be installed?
      driver_installer = fd.Get(fd.Schema.INSTALLATION)

      if driver_installer:
        # Add the driver to the installer.
        driver_installer.driver = driver_blob

        return driver_installer

  raise IOError("Unable to find a driver for client.")


class AnalyzeClientMemoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.AnalyzeClientMemoryArgs


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
  args_type = AnalyzeClientMemoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["RunVolatilityPlugins"])
  def Start(self, _):
    self.CallFlow("LoadMemoryDriver", next_state="RunVolatilityPlugins",
                  driver_installer=self.args.driver_installer)

  @flow.StateHandler(next_state=["Done"])
  def RunVolatilityPlugins(self, responses):
    """Run all the plugins and process the responses."""
    if responses.success:
      memory_information = responses.First()

      if memory_information:
        self.args.request.device = memory_information.device

      else:
        # We loaded the driver previously and stored the path in the AFF4 VFS -
        # we try to use that instead.
        device_urn = self.client_id.Add("devices/memory")
        fd = aff4.FACTORY.Open(device_urn, "MemoryImage", token=self.token)
        device = fd.Get(fd.Schema.LAYOUT)
        if device:
          self.args.request.device = device

      self.CallFlow("VolatilityPlugins", request=self.args.request,
                    next_state="Done", output=self.args.output)
    else:
      raise flow.FlowError("Failed to Load driver: %s" % responses.status)

  @flow.StateHandler()
  def Done(self, responses):
    pass

  @flow.StateHandler()
  def End(self):
    out_urn = self.client_id.Add("analysis")
    self.Notify("ViewObject", out_urn,
                "Completed execution of volatility plugins.")


class UnloadMemoryDriver(LoadMemoryDriver):
  """Unloads a memory driver on the client."""

  category = "/Memory/"
  args_type = LoadMemoryDriverArgs

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    """Start processing."""
    self.state.Register("driver_installer", self.args.driver_installer)

    if not self.args.driver_installer:
      self.state.driver_installer = GetMemoryModule(self.client_id, self.token)

      if not self.state.driver_installer:
        raise IOError("No memory driver currently available for this system.")

    self.CallClient("UninstallDriver", self.state.driver_installer,
                    next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed to uninstall memory driver: %s",
                           responses.status.error_message)

  @flow.StateHandler()
  def End(self):
    pass


class GrepMemoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.GrepMemoryArgs


class GrepMemory(flow.GRRFlow):
  """Grep client memory for a signature.

  This flow greps memory on the client for a pattern or a regex.

  Returns to parent flow:
      RDFValueArray of BufferReference objects.
  """

  category = "/Memory/"
  args_type = GrepMemoryArgs

  @flow.StateHandler(next_state="Grep")
  def Start(self):
    self.CallFlow("LoadMemoryDriver", next_state="Grep")
    self.state.Register("output_urn", None)

  @flow.StateHandler(next_state="Done")
  def Grep(self, responses):
    """Run Grep on memory device pathspec."""
    if not responses.success:
      raise flow.FlowError("Error while loading memory driver: %s" %
                           responses.status.error_message)

    memory_information = responses.First()

    # Coerce the BareGrepSpec into a GrepSpec explicitly.
    grep_request = rdfvalue.GrepSpec(target=memory_information.device,
                                     **self.args.request.AsDict())

    output = self.args.output.format(t=time.time(),
                                     u=self.state.context.user)
    self.state.output_urn = self.client_id.Add(output)

    self.CallFlow("Grep", request=grep_request,
                  output=output, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if responses.success:
      for response in responses:
        self.SendReply(response)
      self.state.Register("hits", len(responses))
    else:
      raise flow.FlowError("Error grepping memory: %s.", responses.status)

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.state.output_urn,
                u"Grep completed, %d hits." % self.state.hits)


class GrepAndDownloadMemory(flow.GRRFlow):
  """Downloads client memory if a signature is found.

  This flow greps memory on the client for a pattern or a regex
  and, if the pattern is found, downloads the memory image.
  """

  category = "/Memory/"
  args_type = GrepMemoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state="Download")
  def Start(self):
    output = self.args.output.format(t=time.time(),
                                     u=self.state.context.user)

    self.CallFlow("GrepMemory", request=self.state.request,
                  output=output, next_state="Download")

  @flow.StateHandler(next_state=["DownloadComplete", "End"])
  def Download(self, responses):
    if responses:
      self.Log("Grep found results: %s, downloading memory image." %
               responses.First())
      self.CallFlow("DownloadMemoryImage", next_state="DownloadComplete")
    else:
      self.Log("Grep did not yield any results.")

  @flow.StateHandler()
  def DownloadComplete(self, responses):
    if not responses.success:
      raise flow.FlowError("Error while downloading memory image: %s" %
                           responses.status)
    else:
      self.Notify("ViewObject", responses.First().aff4path,
                  "Memory image transferred successfully")
