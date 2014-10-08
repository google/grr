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
from grr.lib import rekall_profile_server
from grr.lib import utils
from grr.proto import flows_pb2


class MemoryCollectorCondition(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorCondition


class MemoryCollectorWithoutLocalCopyDumpOption(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorWithoutLocalCopyDumpOption


class MemoryCollectorWithLocalCopyDumpOption(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorWithLocalCopyDumpOption


class MemoryCollectorDumpOption(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorDumpOption


class MemoryCollectorDownloadAction(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorDownloadAction


class MemoryCollectorSendToSocketAction(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorSendToSocketAction


class MemoryCollectorAction(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorAction


class MemoryCollectorArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.MemoryCollectorArgs


class MemoryCollector(flow.GRRFlow):
  """Flow for scanning and imaging memory.

  MemoryCollector applies "action" (e.g. Download) to memory if memory contents
  match all given "conditions". Matches are then written to the results
  collection. If there are no "conditions", "action" is applied immediately.

  MemoryCollector replaces deprecated DownloadMemoryImage and
  ImageMemoryToSocket.

  When downloading memory:
  If the file transfer fails and you specified local copy, you can attempt to
  download again using the FileFinder flow without needing to copy all of memory
  to disk again.  FileFinder will only retrieve parts of the image that weren't
  already downloaded.  Note that if the flow fails, you'll need to run
  Administrative/DeleteGRRTempFiles to clean up the disk.

  When imaging memory to socket:
  Choose a key and an IV in hex format (if run from the GUI,
  there will be a pregenerated pair key and iv for you to use) and run a
  listener on the server you want to use like this:

  nc -l <port> | openssl aes-128-cbc -d -K <key> -iv <iv> > <filename>
  """
  friendly_name = "Memory Collector"
  category = "/Memory/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = MemoryCollectorArgs

  def ConditionsToFileFinderConditions(self, conditions):
    ff_condition_type_cls = rdfvalue.FileFinderCondition.Type
    result = []
    for c in conditions:
      if c.condition_type == MemoryCollectorCondition.Type.LITERAL_MATCH:
        result.append(rdfvalue.FileFinderCondition(
            condition_type=ff_condition_type_cls.CONTENTS_LITERAL_MATCH,
            contents_literal_match=c.literal_match))
      elif c.condition_type == MemoryCollectorCondition.Type.REGEX_MATCH:
        result.append(rdfvalue.FileFinderCondition(
            condition_type=ff_condition_type_cls.CONTENTS_REGEX_MATCH,
            contents_regex_match=c.regex_match))
      else:
        raise ValueError("Unknown condition type: %s", c.condition_type)

    return result

  @flow.StateHandler(next_state="StoreMemoryInformation")
  def Start(self):
    self.state.Register("memory_information", None)
    self.state.Register(
        "destdir",
        self.args.action.download.dump_option.with_local_copy.destdir)
    self.CallFlow("LoadMemoryDriver",
                  driver_installer=self.args.driver_installer,
                  next_state="StoreMemoryInformation")

  def _DiskFreeCheckRequired(self):
    # pylint: disable=line-too-long
    return (self.args.action.action_type == rdfvalue.MemoryCollectorAction.Action.DOWNLOAD
            and self.args.action.download.dump_option.option_type == rdfvalue.MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY
            and self.args.action.download.dump_option.with_local_copy.check_disk_free_space)
    # pylint: enable=line-too-long

  @flow.StateHandler(next_state=["Filter", "StoreTmpDir", "CheckDiskFree"])
  def StoreMemoryInformation(self, responses):
    if not responses.success:
      raise flow.FlowError("Failed due to no memory driver:%s." %
                           responses.status)

    self.state.memory_information = responses.First()

    if self._DiskFreeCheckRequired():
      if self.state.destdir:
        self.CallStateInline(next_state="CheckDiskFree")
      else:
        self.CallClient("GetConfiguration", next_state="StoreTmpDir")
    else:
      self.CallStateInline(next_state="Filter")

  @flow.StateHandler(next_state=["CheckDiskFree"])
  def StoreTmpDir(self, responses):
    # For local copy we need to know where the file will land to check for
    # disk free space there. The default is to leave this blank, which will
    # cause the client to use Client.tempdir
    if not responses.success:
      raise flow.FlowError("Couldn't get client config: %s." % responses.status)

    self.state.destdir = responses.First().get("Client.tempdir")

    if not self.state.destdir:
      # This means Client.tempdir wasn't explicitly defined in the client
      # config,  so we use the current server value with the right context for
      # the client instead.  This may differ from the default value deployed
      # with the client, but it's a fairly safe bet.
      self.state.destdir = config_lib.CONFIG.Get(
          "Client.tempdir",
          context=GetClientContext(self.client_id, self.token))

      if not self.state.destdir:
        raise flow.FlowError("Couldn't determine Client.tempdir file "
                             "destination, required for disk free check: %s.")

      self.Log("Couldn't get Client.tempdir from client for disk space check,"
               "guessing %s from server config", self.state.destdir)

    self.CallFlow("DiskVolumeInfo",
                  path_list=[self.state.destdir],
                  next_state="CheckDiskFree")

  @flow.StateHandler(next_state=["Filter"])
  def CheckDiskFree(self, responses):
    if not responses.success or not responses.First():
      raise flow.FlowError(
          "Couldn't determine disk free space for path %s" %
          self.args.action.download.dump_option.with_local_copy.destdir)

    free_space = responses.First().FreeSpaceBytes()

    mem_size = 0
    for run in self.state.memory_information.runs:
      mem_size += run.length

    if free_space < mem_size:
      # We expect that with compression the disk required will be significantly
      # less, so this ensures there will still be some left once we are done.
      raise flow.FlowError("Free space may be too low for local copy. Free "
                           "space on volume %s is %s bytes. Mem size is: %s "
                           "bytes. Override with check_disk_free_space=False."
                           % (self.state.destdir, free_space, mem_size))

    self.CallStateInline(next_state="Filter")

  @flow.StateHandler(next_state=["Action"])
  def Filter(self, responses):
    if self.args.conditions:
      self.CallFlow("FileFinder",
                    paths=[self.state.memory_information.device.path],
                    pathtype=rdfvalue.PathSpec.PathType.MEMORY,
                    conditions=self.ConditionsToFileFinderConditions(
                        self.args.conditions),
                    next_state="Action")
    else:
      self.CallStateInline(next_state="Action")

  @property
  def action_options(self):
    if self.args.action.action_type == MemoryCollectorAction.Action.DOWNLOAD:
      return self.args.action.download
    elif (self.args.action.action_type ==
          MemoryCollectorAction.Action.SEND_TO_SOCKET):
      return self.args.action.send_to_socket

  @flow.StateHandler(next_state=["Transfer"])
  def Action(self, responses):
    if not responses.success:
      raise flow.FlowError(
          "Applying conditions failed: %s" % (responses.status))

    if self.args.conditions:
      if not responses:
        self.Status("Memory doesn't match specified conditions.")
        return
      for response in responses:
        for match in response.matches:
          self.SendReply(match)

    if self.action_options:
      if (self.action_options.dump_option.option_type ==
          MemoryCollectorDumpOption.Option.WITHOUT_LOCAL_COPY):
        self.CallStateInline(next_state="Transfer")
      elif (self.action_options.dump_option.option_type ==
            MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY):
        dump_option = self.action_options.dump_option.with_local_copy
        self.CallClient("CopyPathToFile",
                        offset=dump_option.offset,
                        length=dump_option.length,
                        src_path=self.state.memory_information.device,
                        dest_dir=dump_option.destdir,
                        gzip_output=dump_option.gzip,
                        next_state="Transfer")
    else:
      self.Status("Nothing to do: no action specified.")

  @flow.StateHandler(next_state=["Done"])
  def Transfer(self, responses):
    # We can only get a failure if Transfer is called from CopyPathToFile
    if not responses.success:
      raise flow.FlowError("Local copy failed: %s" % (responses.status))

    if (self.action_options.dump_option.option_type ==
        MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY):
      self.state.Register("memory_src_path", responses.First().dest_path)
    else:
      self.state.Register("memory_src_path",
                          self.state.memory_information.device)

    if self.args.action.action_type == MemoryCollectorAction.Action.DOWNLOAD:
      self.CallFlow("GetFile", pathspec=self.state.memory_src_path,
                    next_state="Done")
    elif (self.args.action.action_type ==
          MemoryCollectorAction.Action.SEND_TO_SOCKET):
      options = self.state.args.action.send_to_socket
      self.CallClient("SendFile", key=utils.SmartStr(options.key),
                      iv=utils.SmartStr(options.iv),
                      pathspec=self.state.memory_src_path,
                      address_family=options.address_family,
                      host=options.host,
                      port=options.port,
                      next_state="Done")

  @flow.StateHandler(next_state=["DeleteFile"])
  def Done(self, responses):
    """'Done' state always gets executed after 'Transfer' state is done."""
    if not responses.success:
      # Leave file on disk to allow the user to retry GetFile without having to
      # copy the whole memory image again.
      raise flow.FlowError("Transfer of %s failed %s" % (
          self.state.memory_src_path, responses.status))

    if self.args.action.action_type == MemoryCollectorAction.Action.DOWNLOAD:
      stat = responses.First()
      self.state.Register("downloaded_file", stat.aff4path)
      self.Log("Downloaded %s successfully." % self.state.downloaded_file)
      self.Notify("ViewObject", self.state.downloaded_file,
                  "Memory image transferred successfully")
      self.Status("Memory image transferred successfully.")
      self.SendReply(stat)
    elif (self.args.action.action_type ==
          MemoryCollectorAction.Action.SEND_TO_SOCKET):
      self.Status("Memory image transferred successfully.")

    if (self.action_options.dump_option.option_type ==
        MemoryCollectorDumpOption.Option.WITH_LOCAL_COPY):
      self.CallClient("DeleteGRRTempFiles",
                      self.state.memory_src_path, next_state="DeleteFile")

  @flow.StateHandler()
  def DeleteFile(self, responses):
    """Checks for errors from DeleteGRRTempFiles called from 'Done' state."""
    if not responses.success:
      raise flow.FlowError("Removing local file %s failed: %s" % (
          self.state.memory_src_path, responses.status))


class DownloadMemoryImageArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.DownloadMemoryImageArgs


class DownloadMemoryImage(flow.GRRFlow):
  """Copy memory image to local disk then retrieve the file.

  DEPRECATED.
  This flow is now deprecated in favor of MemoryCollector. Please use
  MemoryCollector without conditions with "Download" action. You can
  set "dump option" to "create local copy first" or "don't create local copy".

  Returns to parent flow:
    A rdfvalue.CopyPathToFileRequest.
  """

  category = "/Memory/"
  args_type = DownloadMemoryImageArgs

  # This flow is also a basic flow.
  behaviours = flow.GRRFlow.behaviours + "ADVANCED"

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
    self.state.Register("installer_urns", [])
    self.state.Register("current_installer", None)

    if not self.args.driver_installer:
      # Fetch the driver installer from the data store.
      self.state.installer_urns = GetMemoryModules(self.client_id,
                                                   token=self.token)

      # Create a protobuf containing the request.
      if not self.state.installer_urns:
        raise IOError("Could not determine path for memory driver. No module "
                      "available for this platform.")

    if self.args.reload_if_loaded:
      self.CallStateInline(next_state="LoadDriver")
    else:
      # We just check for one of the drivers, assuming that they all use the
      # same device path.
      installer = GetDriverFromURN(self.state.installer_urns[0],
                                   token=self.token)

      self.CallClient("GetMemoryInformation",
                      rdfvalue.PathSpec(
                          path=installer.device_path,
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
    if not self.state.installer_urns:
      raise flow.FlowError("Could not find a working memory driver")

    installer_urn = self.state.installer_urns.pop(0)
    installer = GetDriverFromURN(installer_urn, token=self.token)
    self.state.current_installer = installer
    # We want to force unload old driver and reload the current one.
    installer.force_reload = 1
    self.CallClient("InstallDriver", installer, next_state="InstalledDriver")

  @flow.StateHandler(next_state=["GotMemoryInformation", "LoadDriver",
                                 "InstalledDriver"])
  def InstalledDriver(self, responses):
    if not responses.success:
      # This driver didn't work, let's try the next one.
      self.CallStateInline(next_state="LoadDriver")

    self.CallClient("GetMemoryInformation",
                    rdfvalue.PathSpec(
                        path=self.state.current_installer.device_path,
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
                           (self.state.current_installer.device_path,
                            responses.status))

  @flow.StateHandler()
  def End(self):
    if self.state.context.state != rdfvalue.Flow.State.ERROR:
      self.Notify("ViewObject", self.state.device_urn,
                  "Driver successfully initialized.")


def GetClientContext(client_id, token):
  """Get context for the given client id.

  Get platform, os release, and arch contexts for the client.

  Args:
    client_id: The client_id of the host to use.
    token: Token to use for access.
  Returns:
    array of client_context strings
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

  return client_context


def GetMemoryModules(client_id, token):
  """Given a host, returns a list of urns to appropriate memory modules.

  Args:
    client_id: The client_id of the host to use.
    token: Token to use for access.

  Returns:
    A list of URNs pointing to GRRSignedDriver objects.

  Raises:
    IOError: on inability to get any driver.

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
      MemoryDriver.aff4_paths:
        - aff4:/config/drivers/windows/pmem_amd64.sys

    Arch:i386:
      MemoryDriver.aff4_paths:
        - aff4:/config/drivers/windows/pmem_x86.sys
  """
  installer_urns = []
  for aff4_path in config_lib.CONFIG.Get(
      "MemoryDriver.aff4_paths", context=GetClientContext(client_id, token)):
    logging.debug("Will fetch driver at %s for client %s",
                  aff4_path, client_id)
    if GetDriverFromURN(aff4_path, token):
      logging.debug("Driver at %s found.", aff4_path)
      installer_urns.append(aff4_path)
    else:
      logging.debug("Unable to load driver at %s.", aff4_path)

  if not installer_urns:
    raise IOError("Unable to find a driver for client.")

  return installer_urns


def GetDriverFromURN(urn, token=None):
  """Returns the actual driver from a driver URN."""
  try:
    fd = aff4.FACTORY.Open(urn, aff4_type="GRRMemoryDriver",
                           mode="r", token=token)

    # Get the signed driver.
    for driver_blob in fd:
      # How should this driver be installed?
      driver_installer = fd.Get(fd.Schema.INSTALLATION)

      if driver_installer:
        # Add the driver to the installer.
        driver_installer.driver = driver_blob

        return driver_installer

  except IOError:
    pass

  return None


class AnalyzeClientMemoryArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.AnalyzeClientMemoryArgs


class AnalyzeClientMemory(flow.GRRFlow):
  """Runs client side analysis using Rekall.

  This flow takes a list of Rekall plugins to run. It first calls
  LoadMemoryDriver to ensure a Memory driver is loaded.
  It then sends the list of Rekall commands to the client. The client will
  run those plugins using the client's copy of Rekall.

  Each plugin will return it's results and they will be stored in
  RekallResultCollections.
  """

  category = "/Memory/"
  args_type = AnalyzeClientMemoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["RunPlugins"])
  def Start(self, _):
    # Our output collection is a RekallResultCollection.
    if self.runner.output is not None:
      self.runner.output = aff4.FACTORY.Create(
          self.runner.output.urn, "RekallResponseCollection",
          mode="rw", token=self.token)

    self.CallFlow("LoadMemoryDriver", next_state="RunPlugins",
                  driver_installer=self.args.driver_installer)

  @flow.StateHandler(next_state=["StoreResults"])
  def RunPlugins(self, responses):
    """Call the client with the Rekall actions."""
    if not responses.success:
      raise flow.FlowError("Unable to install memory driver.")

    memory_information = responses.First()
    # Update the device from the result of LoadMemoryDriver.
    self.args.request.device = memory_information.device
    self.CallClient("RekallAction", self.args.request,
                    next_state="StoreResults")

  @flow.StateHandler()
  def UpdateProfile(self, responses):
    if not responses.success:
      self.Log(responses.status)

  @flow.StateHandler(next_state=["StoreResults", "UpdateProfile"])
  def StoreResults(self, responses):
    """Stores the results."""
    if not responses.success:
      self.Error("Error running plugins: %s." % responses.status)
      return

    self.Log("Rekall returned %s responses." % len(responses))
    for response in responses:
      if response.missing_profile:
        server_type = config_lib.CONFIG["Rekall.profile_server"]
        logging.debug("Getting missing Rekall profile from %s", server_type)
        profile_server = rekall_profile_server.ProfileServer.classes[
            server_type]()
        profile = profile_server.GetProfileByName(response.missing_profile)
        if profile:
          self.CallClient("WriteRekallProfile", profile,
                          next_state="UpdateProfile")
        else:
          self.Log("Needed profile %s not found!", response.missing_profile)

      if response.json_messages:
        response.client_urn = self.client_id
        self.SendReply(response)

    if responses.iterator.state != rdfvalue.Iterator.State.FINISHED:
      self.args.request.iterator = responses.iterator
      self.CallClient("RekallAction", self.args.request,
                      next_state="StoreResults")

  @flow.StateHandler()
  def End(self):
    if self.runner.output is not None:
      self.Notify("ViewObject", self.runner.output.urn,
                  "Ran analyze client memory")


class UnloadMemoryDriver(LoadMemoryDriver):
  """Unloads a memory driver on the client."""

  category = "/Memory/"
  args_type = LoadMemoryDriverArgs

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    """Start processing."""
    self.state.Register("driver_installer", self.args.driver_installer)
    self.state.Register("success", False)

    if self.args.driver_installer:
      self.CallClient("UninstallDriver", self.state.driver_installer,
                      next_state="Done")
      return

    urns = GetMemoryModules(self.client_id, self.token)
    if not urns:
      raise IOError("No memory driver currently available for this system.")

    for urn in urns:
      installer = GetDriverFromURN(urn, token=self.token)
      self.CallClient("UninstallDriver", installer, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if responses.success:
      self.state.success = True

  @flow.StateHandler()
  def End(self):
    if not self.state.success:
      raise flow.FlowError("Failed to uninstall memory driver.")


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

    # For literal matches we xor the search term. This stops us matching the GRR
    # client itself.
    if self.args.grep.literal:
      grep_request.literal = utils.Xor(
          utils.SmartStr(self.args.grep.literal), self.XOR_IN_KEY)

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
  """Get list of all running binaries from Rekall, (optionally) fetch them.

    This flow executes the "vad" Rekall plugin to get the list of all
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
    if self.runner.output is not None:
      self.runner.output.Set(self.runner.output.Schema.DESCRIPTION(
          "GetProcessesBinariesRekall binaries (regex: %s) " %
          self.args.filename_regex or "None"))

    self.CallFlow("ArtifactCollectorFlow",
                  artifact_list=["FullVADBinaryList"],
                  store_results_in_aff4=False,
                  next_state="FetchBinaries")

  @flow.StateHandler(next_state="HandleDownloadedFiles")
  def FetchBinaries(self, responses):
    """Parses the Rekall response and initiates FileFinder flows."""
    if not responses.success:
      self.Log("Error fetching VAD data: %s", responses.status)
      return

    self.Log("Found %d binaries", len(responses))

    if self.args.filename_regex:
      binaries = []
      for response in responses:
        if self.args.filename_regex.Match(response.CollapsePath()):
          binaries.append(response)

      self.Log("Applied filename regex. Have %d files after filtering.",
               len(binaries))
    else:
      binaries = responses

    if self.args.fetch_binaries:
      self.CallFlow("FileFinder",
                    next_state="HandleDownloadedFiles",
                    paths=[rdfvalue.GlobExpression(b.CollapsePath())
                           for b in binaries],
                    pathtype=rdfvalue.PathSpec.PathType.OS,
                    action=rdfvalue.FileFinderAction(
                        action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD))
    else:
      for b in binaries:
        self.SendReply(b)

  @flow.StateHandler()
  def HandleDownloadedFiles(self, responses):
    """Handle success/failure of the FileFinder flow."""
    if responses.success:
      for file_finder_result in responses:
        self.SendReply(file_finder_result.stat_entry)
        self.Log("Downloaded %s",
                 file_finder_result.stat_entry.pathspec.CollapsePath())
    else:
      self.Log("Binaries download failed: %s", responses.status)
