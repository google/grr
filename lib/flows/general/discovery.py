#!/usr/bin/env python
"""These are flows designed to discover information about the host."""


import os

from grr.lib import aff4
from grr.lib import constants
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class EnrolmentInterrogateEvent(flow.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]
  well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:Interrogate")

  # We only accept messages that came from the CA flows.
  sourcecheck = lambda source: source.Basename().startswith("CA:")

  @flow.EventHandler(source_restriction=sourcecheck)
  def ProcessMessage(self, message=None, event=None):
    _ = message
    flow.GRRFlow.StartFlow(client_id=event,
                           flow_name="Interrogate", token=self.token)


class InterrogateArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.InterrogateArgs


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Administrative/"
  client = None
  args_type = InterrogateArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["Hostname",
                                 "Platform",
                                 "InstallDate",
                                 "EnumerateInterfaces",
                                 "EnumerateFilesystems",
                                 "ClientInfo",
                                 "ClientConfig",
                                 "ClientConfiguration"])
  def Start(self):
    """Start off all the tests."""
    self.state.Register("sid_data", {})
    self.state.Register("summary", rdfvalue.ClientSummary(
        client_id=self.client_id))

    # Create the objects we need to exist.
    self.Load()
    fd = aff4.FACTORY.Create(self.client.urn.Add("network"), "Network",
                             token=self.token)
    fd.Close()

    self.CallClient("GetPlatformInfo", next_state="Platform")
    self.CallClient("GetInstallDate", next_state="InstallDate")
    self.CallClient("GetClientInfo", next_state="ClientInfo")

    # Support both new and old clients.
    self.CallClient("GetConfig", next_state="ClientConfig")
    self.CallClient("GetConfiguration", next_state="ClientConfiguration")

    self.CallClient("EnumerateInterfaces", next_state="EnumerateInterfaces")
    self.CallClient("EnumerateFilesystems", next_state="EnumerateFilesystems")

  def Load(self):
    # Ensure there is a client object
    self.client = aff4.FACTORY.Open(self.client_id,
                                    mode="rw", token=self.token)

  def Save(self):
    # Make sure the client object is removed and closed
    if self.client:
      self.client.Close()
      self.client = None

  @flow.StateHandler(next_state=["VerifyUsers", "EnumerateUsers"])
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      self.state.summary.system_info = response

      # These need to be in separate attributes because they get searched on in
      # the GUI
      self.client.Set(self.client.Schema.HOSTNAME(response.node))
      self.client.Set(self.client.Schema.SYSTEM(response.system))
      self.client.Set(self.client.Schema.OS_RELEASE(response.release))
      self.client.Set(self.client.Schema.OS_VERSION(response.version))
      self.client.Set(self.client.Schema.FQDN(response.fqdn))

      # response.machine is the machine value of platform.uname()
      # On Windows this is the value of:
      # HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session
      # Manager\Environment\PROCESSOR_ARCHITECTURE
      # "AMD64", "IA64" or "x86"
      self.client.Set(self.client.Schema.ARCH(response.machine))
      self.client.Set(self.client.Schema.UNAME("%s-%s-%s" % (
          response.system, response.release, response.version)))

      # Windows systems get registry hives and "manual" way of enumerating
      # users.
      if response.system == "Windows":
        fd = aff4.FACTORY.Create(self.client.urn.Add("registry"),
                                 "VFSDirectory", token=self.token)
        fd.Set(fd.Schema.PATHSPEC, fd.Schema.PATHSPEC(
            path="/", pathtype=rdfvalue.PathSpec.PathType.REGISTRY))
        fd.Close()

        profiles_key = (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft"
                        r"\Windows NT\CurrentVersion\ProfileList")

        request = rdfvalue.FindSpec(path_regex="ProfileImagePath", max_depth=2)

        request.pathspec.path = profiles_key
        request.pathspec.pathtype = request.pathspec.PathType.REGISTRY

        # Download all the Registry keys, it is limited by max_depth.
        request.iterator.number = 10000
        self.CallClient("Find", request, next_state="VerifyUsers")

      else:
        self.CallClient("EnumerateUsers", next_state="EnumerateUsers")

    else:
      self.Log("Could not retrieve Platform info.")

  @flow.StateHandler(next_state=["GetFolders"])
  def VerifyUsers(self, responses):
    """Issues WMI queries that verify that the SIDs actually belong to users."""
    if not responses.success:
      self.Log("Cannot query registry for user information. ")
      return

    for response in responses:
      if response.hit.resident:
        # Support old clients.
        homedir = utils.SmartUnicode(response.hit.resident)
      else:
        homedir = response.hit.registry_data.GetValue()
      # Cut away ProfilePath
      path = os.path.dirname(response.hit.pathspec.path)
      sid = os.path.basename(path)
      # This is the best way we have of deriving the username from a SID.
      user = homedir[homedir.rfind("\\") + 1:]
      self.state.sid_data[sid] = {"homedir": homedir,
                                  "username": user,
                                  "sid": sid}

      if not self.args.lightweight:
        query = "SELECT * FROM Win32_UserAccount WHERE name=\"%s\"" % user
        self.CallClient("WmiQuery", query=query, next_state="GetFolders",
                        request_data={"SID": sid})

  @flow.StateHandler(next_state=["VerifyFolders"])
  def GetFolders(self, responses):
    """If the SID belongs to a user, this tries to get the special folders."""
    if not responses.success:
      return

    for response in responses:
      # It could happen that wmi returns an AD user with the same name as the
      # local one. In this case, we just ignore the unknown SID.
      if response["SID"] not in self.state.sid_data:
        continue

      self.state.sid_data[response["SID"]]["domain"] = response["Domain"]
      folder_path = (
          r"HKEY_USERS\%s\Software\Microsoft\Windows"
          r"\CurrentVersion\Explorer\Shell Folders") % response["SID"]
      self.CallClient("ListDirectory",
                      pathspec=rdfvalue.PathSpec(
                          path=folder_path,
                          pathtype=rdfvalue.PathSpec.PathType.REGISTRY),
                      request_data=responses.request_data,
                      next_state="VerifyFolders")

  @flow.StateHandler(next_state=["SaveFolders"])
  def VerifyFolders(self, responses):
    """This saves the returned folders."""
    if responses.success:
      profile_folders = {}
      for response in responses:
        returned_folder = os.path.basename(response.pathspec.path)
        for (folder, _, pb_field) in constants.profile_folders:
          if folder == returned_folder:
            profile_folders[pb_field] = (
                response.resident or
                response.registry_data.GetValue())
            break
      # Save the user pb.
      data = self.state.sid_data[responses.request_data["SID"]]
      data["special_folders"] = rdfvalue.FolderInformation(**profile_folders)

    else:
      # Reading from registry failed, we have to guess.
      homedir = self.state.sid_data[responses.request_data["SID"]]["homedir"]
      for (folder, subdirectory, pb_field) in constants.profile_folders:
        data = responses.request_data
        data["pb_field"] = pb_field
        self.CallClient("StatFile",
                        pathspec=rdfvalue.PathSpec(
                            path=utils.JoinPath(homedir,
                                                subdirectory),
                            pathtype=rdfvalue.PathSpec.PathType.OS),
                        request_data=data,
                        next_state="SaveFolders")

  @flow.StateHandler()
  def SaveFolders(self, responses):
    """Saves all the folders found to the user pb."""
    if responses.success:
      profile_folders = {}
      for response in responses:
        path = response.pathspec.path
        # We want to store human readable Windows paths here.
        path = path.lstrip("/").replace("/", "\\")
        profile_folders[responses.request_data["pb_field"]] = path
      data = self.state.sid_data[responses.request_data["SID"]]
      folder = rdfvalue.FolderInformation(**profile_folders)

      data["special_folders"] = folder

  def SaveUsers(self):
    """This saves the collected data to the data store."""
    user_list = self.client.Schema.USER()
    usernames = []
    for data in self.state.sid_data.itervalues():
      usernames.append(data["username"])

      user = rdfvalue.User(**data)
      self.state.summary.users.Append(user)

      user_list.Append(user)
      self.client.AddAttribute(self.client.Schema.USER, user_list)

    self.client.AddAttribute(self.client.Schema.USERNAMES(
        " ".join(sorted(usernames))))

  @flow.StateHandler()
  def InstallDate(self, responses):
    if responses.success:
      response = responses.First()
      install_date = self.client.Schema.INSTALL_DATE(
          response.integer * 1000000)
      self.client.Set(install_date)
      self.state.summary.install_date = install_date
    else:
      self.Log("Could not get InstallDate")

  @flow.StateHandler()
  def EnumerateUsers(self, responses):
    """Store all users in the data store and maintain indexes."""
    if responses.success and responses:
      usernames = []
      user_list = self.client.Schema.USER()
      # Add all the users to the client object
      for response in responses:
        user_list.Append(response)
        self.state.summary.users.Append(response)

        if response.username:
          usernames.append(response.username)

      # Store it now
      self.client.AddAttribute(self.client.Schema.USER, user_list)
      self.client.AddAttribute(self.client.Schema.USERNAMES(
          " ".join(usernames)))
    else:
      self.Log("Could not enumerate users")

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if responses.success and responses:
      net_fd = aff4.FACTORY.Create(self.client.urn.Add("network"), "Network",
                                   token=self.token)
      interface_list = net_fd.Schema.INTERFACES()
      mac_addresses = []
      for response in responses:
        interface_list.Append(response)

        # Add a hex encoded string for searching
        if (response.mac_address and
            response.mac_address != "\x00" * len(response.mac_address)):
          mac_addresses.append(response.mac_address.human_readable_address)

      self.client.Set(self.client.Schema.MAC_ADDRESS(
          "\n".join(mac_addresses)))
      net_fd.Set(net_fd.Schema.INTERFACES, interface_list)
      net_fd.Close()

      self.state.summary.interfaces = interface_list
    else:
      self.Log("Could not enumerate interfaces.")

  @flow.StateHandler()
  def EnumerateFilesystems(self, responses):
    """Store all the local filesystems in the client."""
    if responses.success and len(responses):
      filesystems = self.client.Schema.FILESYSTEM()
      for response in responses:
        filesystems.Append(response)

        if response.type == "partition":
          (device, offset) = response.device.rsplit(":", 1)

          offset = int(offset)

          pathspec = rdfvalue.PathSpec(
              path=device, pathtype=rdfvalue.PathSpec.PathType.OS,
              offset=offset)

          pathspec.Append(path="/",
                          pathtype=rdfvalue.PathSpec.PathType.TSK)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()
          continue

        if response.device:
          # Create the raw device
          urn = "devices/%s" % response.device

          pathspec = rdfvalue.PathSpec(
              path=response.device,
              pathtype=rdfvalue.PathSpec.PathType.OS)

          pathspec.Append(path="/",
                          pathtype=rdfvalue.PathSpec.PathType.TSK)

          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

          # Create the TSK device
          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

        if response.mount_point:
          # Create the OS device
          pathspec = rdfvalue.PathSpec(
              path=response.mount_point,
              pathtype=rdfvalue.PathSpec.PathType.OS)

          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = aff4.FACTORY.Create(urn, "VFSDirectory", token=self.token)
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

      self.client.Set(self.client.Schema.FILESYSTEM, filesystems)
    else:
      self.Log("Could not enumerate file systems.")

  @flow.StateHandler()
  def ClientInfo(self, responses):
    """Obtain some information about the GRR client running."""
    if responses.success:
      response = responses.First()
      self.state.summary.client_info = response
      self.client.Set(self.client.Schema.CLIENT_INFO(response))
      self.client.AddLabels(response.labels)
      self.state.summary.client_info = response
    else:
      self.Log("Could not get ClientInfo.")

  @flow.StateHandler()
  def ClientConfig(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIG(response))

  @flow.StateHandler()
  def ClientConfiguration(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIGURATION(response))

  @flow.StateHandler()
  def End(self):
    """Finalize client registration."""
    if self.state.sid_data:
      self.SaveUsers()

    # Create the bare VFS with empty virtual directories.
    fd = aff4.FACTORY.Create(self.client.urn.Add("processes"), "ProcessListing",
                             token=self.token)
    fd.Close()

    self.Notify("Discovery", self.client.urn, "Client Discovery Complete")

    # Publish this client to the Discovery queue.
    self.state.summary.timestamp = rdfvalue.RDFDatetime().Now()
    self.Publish("Discovery", self.state.summary)
    self.SendReply(self.state.summary)
    self.client.Set(self.client.Schema.SUMMARY, self.state.summary)

    # Flush the data to the data store.
    self.client.Close()
