#!/usr/bin/env python
"""Flows for controlling access to memory.

These flows allow for distributing memory access modules to clients and
performing basic analysis.
"""



import logging
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.flows.general import transfer
from grr.proto import flows_pb2


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

  @classmethod
  def GetDefaultArgs(cls, token=None):
    _ = token
    result = cls.args_type()
    result.length = (1024 ** 4)  # 1 TB

    return result

  @flow.StateHandler(next_state="PrepareImage")
  def Start(self):
    self.CallFlow("LoadMemoryDriver",
                  driver_installer=self.args.driver_installer,
                  next_state="PrepareImage")

  @flow.StateHandler(next_state=["DownloadFile", "Done"])
  def PrepareImage(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver.")

    memory_information = responses.First()
    if self.args.make_local_copy:
      self.CallClient("CopyPathToFile",
                      offset=self.args.offset,
                      length=self.args.length,
                      src_path=memory_information.device,
                      dest_dir=self.args.destdir,
                      gzip_output=self.args.gzip,
                      next_state="DownloadFile")
    else:
      self.CallFlow("GetFile", pathspec=memory_information.device,
                    next_state="Done")

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
      raise flow.FlowError("Could not install memory driver %s" %
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

  @flow.StateHandler(next_state=["StoreResults"])
  def RunVolatilityPlugins(self, responses):
    """Call the client with the volatility actions."""
    if not responses.success:
      raise flow.FlowError("Unable to install memory driver.")

    for plugin in self.args.request.plugins:
      if plugin not in self.args.request.args:
        self.args.request.args[plugin] = {}

    memory_information = responses.First()
    self.args.request.device = memory_information.device
    self.CallClient("VolatilityAction", self.args.request,
                    next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the results."""
    if not responses.success:
      self.Log("Error running plugins: %s.", responses.status)
      return

    self.Log("Volatility returned %s responses." % len(responses))
    for response in responses:
      self.SendReply(response)
      if self.runner.output:
        output_urn = self.runner.output.urn.Add(response.plugin)
        with aff4.FACTORY.Create(output_urn, "VolatilityResponse",
                                 mode="rw", token=self.token) as fd:
          fd.Set(fd.Schema.DESCRIPTION("Volatility plugin by %s: %s" % (
              self.state.context.user, str(self.args.request))))
          fd.Set(fd.Schema.RESULT(response))

  @flow.StateHandler()
  def End(self):
    if self.runner.output:
      self.Notify("ViewObject", self.runner.output.urn,
                  "Ran volatility plugins")


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


class ScanMemoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ScanMemoryArgs


class ScanMemory(flow.GRRFlow):
  """Grep client memory for a signature.

  This flow greps memory on the client for a pattern or a regex.

  Returns to parent flow:
      RDFValueArray of BufferReference objects.
  """

  category = "/Memory/"
  args_type = ScanMemoryArgs

  XOR_IN_KEY = 37
  XOR_OUT_KEY = 57

  @flow.StateHandler(next_state="Grep")
  def Start(self):
    self.args.grep.xor_in_key = self.XOR_IN_KEY
    self.args.grep.xor_out_key = self.XOR_OUT_KEY
    # For literal matches we xor the search term. This stops us matching the GRR
    # client itself.
    if self.args.grep.literal:
      self.args.grep.literal = utils.Xor(
          self.args.grep.literal, self.XOR_IN_KEY)

    self.CallFlow("LoadMemoryDriver", next_state="Grep")

  @flow.StateHandler(next_state="Done")
  def Grep(self, responses):
    """Run Grep on memory device pathspec."""
    if not responses.success:
      raise flow.FlowError("Error while loading memory driver: %s" %
                           responses.status.error_message)

    memory_information = responses.First()

    # Coerce the BareGrepSpec into a GrepSpec explicitly.
    grep_request = rdfvalue.GrepSpec(target=memory_information.device,
                                     **self.args.grep.AsDict())

    self.CallClient("Grep", request=grep_request, next_state="Done")

  @flow.StateHandler(next_state="End")
  def Done(self, responses):
    if responses.success:
      for hit in responses:
        # Decode the hit data from the client.
        hit.data = utils.Xor(hit.data, self.XOR_OUT_KEY)
        self.SendReply(hit)

        if self.args.also_download:
          self.CallFlow("DownloadMemoryImage", next_state="End")

    else:
      raise flow.FlowError("Error grepping memory: %s.", responses.status)


class ListVADBinariesArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ListVADBinariesArgs


class ListVADBinaries(flow.GRRFlow):
  """Get list of all running binaries from Volatility, (optionally) fetch them.

    This flow executes the "vad" Volatility plugin to get the list of all
    currently running binaries (including dynamic libraries). Then if
    fetch_binaries option is set to True, it fetches all the binaries it has
    found.

    There is a caveat regarding using the "vad" plugin to detect currently
    running executable binaries. The "Filename" member of the _FILE_OBJECT
    struct is not reliable:

      * Usually it does not include volume information: i.e.
        \\Windows\\some\\path. Therefore it's impossible to detect the actual
        volume where the executable is located.

      * If the binary is executed from a shared network volume, the Filename
        attribute is not descriptive enough to easily fetch the file.

      * If the binary is executed directly from a network location (without
        mounting the volume) Filename attribute will contain yet another
        form of path.

      * Filename attribute is not actually used by the system (it's probably
        there for debugging purposes). It can be easily overwritten by a rootkit
        without any noticeable consequences for the running system, but breaking
        our functionality as a result.

    Therefore this plugin's functionality is somewhat limited. Basically, it
    won't fetch binaries that are located on non-default volumes.

    Possible workaround (future work):
    * Find a way to map given address space into the filename on the filesystem.
    * Fetch binaries directly from memory by forcing page-ins first (via
      some debug userland-process-dump API?) and then reading the memory.
  """
  category = "/Memory/"
  args_type = ListVADBinariesArgs

  @flow.StateHandler(next_state="FetchBinaries")
  def Start(self):
    """Request VAD data."""
    if self.runner.output:
      self.runner.output.Set(self.runner.output.Schema.DESCRIPTION(
          "GetProcessesBinariesVolatility binaries (regex: %s) " %
          self.args.filename_regex or "None"))

    self.args.request.plugins.Append("vad")
    self.CallClient("VolatilityAction", self.args.request,
                    next_state="FetchBinaries")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def FetchBinaries(self, responses):
    """Parses Volatility response and initiates FetchFiles flows."""
    if not responses.success:
      self.Log("Error fetching VAD data: %s", responses.status)
      return

    binaries = set()

    # Collect binaries list from VolatilityResponse. We search for tables that
    # have "protection" and "filename" columns.
    # TODO(user): create an RDFProto class to reuse the functionality below.
    for response in responses:
      for section in response.sections:
        table = section.table

        # Find indices of "protection" and "filename" columns
        indexed_headers = dict([(header.name, i)
                                for i, header in enumerate(table.headers)])
        try:
          protection_col_index = indexed_headers["protection"]
          filename_col_index = indexed_headers["filename"]
        except KeyError:
          # If we can't find "protection" and "filename" columns, just skip
          # this section
          continue

        for row in table.rows:
          protection_attr = row.values[protection_col_index]
          filename_attr = row.values[filename_col_index]

          if protection_attr.svalue in ("EXECUTE_READ",
                                        "EXECUTE_READWRITE",
                                        "EXECUTE_WRITECOPY"):
            if filename_attr.svalue:
              binaries.add(filename_attr.svalue)

    self.Log("Found %d binaries", len(binaries))
    if self.args.filename_regex:
      binaries = filter(self.args.filename_regex.Match, binaries)
      self.Log("Applied filename regex. Will fetch %d files",
               len(binaries))

    if self.args.fetch_binaries:
      self.CallFlow("FetchFiles",
                    next_state="HandleDownloadedFiles",
                    paths=binaries, pathtype=rdfvalue.PathSpec.PathType.OS)
    else:
      for b in binaries:
        self.SendReply(rdfvalue.RDFString(b))

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FetchFiles flow."""
    if responses.success:
      for response_stat in responses:
        self.SendReply(response_stat)
        self.Log("Downloaded %s", response_stat.pathspec.CollapsePath())
    else:
      self.Log("Download of file %s failed %s",
               response_stat.pathspec.CollapsePath(), responses.status)
