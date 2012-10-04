#!/usr/bin/env python

# Copyright 2010 Google Inc.
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

"""These are flows designed to discover information about the host."""


import os

from grr.lib import aff4
from grr.lib import constants
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class EnrolmentInterrogateEvent(flow.EventListener):
  """An event handler which will schedule interrogation on client enrollment."""
  EVENTS = ["ClientEnrollment"]
  well_known_session_id = "W:Interrogate"

  @flow.EventHandler(in_protobuf=jobs_pb2.Certificate, source_restriction="CA")
  def ProcessMessage(self, message=None, event=None):
    _ = message
    flow.FACTORY.StartFlow(event.cn, "Interrogate", token=self.token)


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Metadata/"
  client = None

  @flow.StateHandler(next_state=["Hostname", "Platform",
                                 "InstallDate", "EnumerateUsers",
                                 "EnumerateInterfaces", "EnumerateFilesystems",
                                 "ClientInfo", "ClientConfig",
                                 "VerifyUsers"])

  def Start(self):
    """Start off all the tests."""
    # Create the objects we need to exist.
    self.Load()
    fd = aff4.FACTORY.Create(self.client.urn.Add("network"), "Network",
                             token=self.token)
    fd.Close()
    self.sid_data = {}

    self.profiles_key = (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft"
                         "\Windows NT\CurrentVersion\ProfileList")

    self.CallClient("GetPlatformInfo", next_state="Platform")
    self.CallClient("GetInstallDate", next_state="InstallDate")
    user_list = jobs_pb2.Path(path=self.profiles_key,
                              pathtype=jobs_pb2.Path.REGISTRY)
    request = jobs_pb2.Find(pathspec=user_list,
                            path_regex="ProfileImagePath", max_depth=2)
    # Download all the Registry keys, it is limited by max_depth.
    request.iterator.number = 10000
    self.CallClient("Find", request, next_state="VerifyUsers")
    self.CallClient("EnumerateInterfaces", next_state="EnumerateInterfaces")
    self.CallClient("EnumerateFilesystems", next_state="EnumerateFilesystems")
    self.CallClient("GetClientInfo", next_state="ClientInfo")
    self.CallClient("GetConfig", next_state="ClientConfig")

  def Load(self):
    # Ensure there is a client object
    self.client = aff4.FACTORY.Open(self.client_id, mode="rw", token=self.token)

  def Save(self):
    # Make sure the client object is removed and closed
    if self.client:
      self.client.Close()
      self.client = None

  @flow.StateHandler(next_state=["GetFolders", "EnumerateUsers"])
  def VerifyUsers(self, responses):
    """Issues WMI queries that verify that the SIDs actually belong to users."""
    if not responses.success:
      self.Log("Cannot query registry for user information, "
               " using EnumerateUsers.")
      self.CallClient("EnumerateUsers", next_state="EnumerateUsers")
      return

    for response in responses:
      if response.hit.resident:
        # Support old clients.
        homedir = utils.SmartUnicode(response.hit.resident)
      else:
        homedir = utils.DataBlob(response.hit.registry_data).GetValue()
      # Cut away ProfilePath
      path = os.path.dirname(response.hit.pathspec.path)
      sid = os.path.basename(path)
      # This is the best way we have of deriving the username from a SID.
      user = homedir[homedir.rfind("\\") + 1:]
      self.sid_data[sid] = {"homedir": homedir,
                            "username": user,
                            "sid": sid}
      query = "SELECT * FROM Win32_UserAccount WHERE name=\"%s\"" % user
      self.CallClient("WmiQuery", query=query, next_state="GetFolders",
                      request_data={"SID": sid})

  @flow.StateHandler(next_state=["VerifyFolders"])
  def GetFolders(self, responses):
    """If the SID belongs to a user, this tries to get the special folders."""
    if not responses.success:
      return

    for response in responses:
      acc = utils.ProtoDict(response).ToDict()
      # It could happen that wmi returns an AD user with the same name as the
      # local one. In this case, we just ignore the unknown SID.
      if acc["SID"] not in self.sid_data.iterkeys():
        continue

      self.sid_data[acc["SID"]]["domain"] = acc["Domain"]
      folder_path = (r"HKEY_USERS\%s\Software\Microsoft\Windows"
                     "\CurrentVersion\Explorer\Shell Folders") % acc["SID"]
      self.CallClient("ListDirectory",
                      pathspec=jobs_pb2.Path(path=folder_path,
                                             pathtype=jobs_pb2.Path.REGISTRY),
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
                utils.DataBlob(response.registry_data).GetValue())
            break
      # Save the user pb.
      data = self.sid_data[responses.request_data["SID"]]
      data["special_folders"] = jobs_pb2.FolderInformation(**profile_folders)

      if self.OutstandingRequests() == 1:
        # This is the last response -> save all data.
        self.SaveUsers()

    else:
      # Reading from registry failed, we have to guess.
      homedir = self.sid_data[responses.request_data["SID"]]["homedir"]
      for (folder, subdirectory, pb_field) in constants.profile_folders:
        data = responses.request_data
        data["pb_field"] = pb_field
        self.CallClient("StatFile",
                        pathspec=jobs_pb2.Path(
                            path=utils.JoinPath(homedir,
                                                subdirectory),
                            pathtype=jobs_pb2.Path.OS),
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
      data = self.sid_data[responses.request_data["SID"]]
      folder_pb = jobs_pb2.FolderInformation(**profile_folders)
      try:
        data["special_folders"].MergeFrom(folder_pb)
      except KeyError:
        data["special_folders"] = folder_pb

    if self.OutstandingRequests() == 1:
      # This is the last response -> save all the data.
      self.SaveUsers()

  def SaveUsers(self):
    """This saves the collected data to the data store."""
    user_list = self.client.Schema.USER()
    usernames = []
    for sid in self.sid_data.iterkeys():
      data = self.sid_data[sid]
      usernames.append(data["username"])
      user_list.Append(jobs_pb2.UserAccount(**data))
      self.client.AddAttribute(self.client.Schema.USER, user_list)
    self.client.AddAttribute(self.client.Schema.USERNAMES(
        " ".join(usernames)))

  @flow.StateHandler()
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      # These need to be in separate attributes because they get searched on in
      # the GUI
      self.client.Set(self.client.Schema.HOSTNAME(response.node))
      self.client.Set(self.client.Schema.SYSTEM(response.system))
      self.client.Set(self.client.Schema.OS_RELEASE(response.release))
      self.client.Set(self.client.Schema.OS_VERSION(response.version))
      self.client.Set(self.client.Schema.UNAME("%s-%s-%s" % (
          response.system, response.version,
          response.release)))

      # Windows systems get registry hives
      if response.system == "Windows":
        fd = self.client.CreateMember("registry", "VFSDirectory")
        fd.Set(fd.Schema.PATHSPEC, fd.Schema.PATHSPEC(jobs_pb2.Path(
            path="/", pathtype=jobs_pb2.Path.REGISTRY)))
        fd.Close()
    else:
      self.Log("Could not retrieve Platform info.")

  @flow.StateHandler()
  def InstallDate(self, responses):
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.INSTALL_DATE(
          response.integer * 1000000))
    else:
      self.Log("Could not get InstallDate")

  @flow.StateHandler()
  def EnumerateUsers(self, responses):
    """Store all users in the data store and maintain indexes."""
    if responses.success and len(responses):
      usernames = []
      user_list = self.client.Schema.USER()
      # Add all the users to the client object
      for response in responses:
        user_list.Append(response)
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
    if responses.success and len(responses):
      net_fd = self.client.OpenMember("network", mode="rw")
      interface_list = net_fd.Schema.INTERFACES()
      mac_addresses = []
      for response in responses:
        interface_list.Append(response)

        # Add a hex encoded string for searching
        if response.mac_address != "\x00" * len(response.mac_address):
          mac_addresses.append(response.mac_address.encode("hex"))

      self.client.Set(self.client.Schema.MAC_ADDRESS(
          "\n".join(mac_addresses)))
      net_fd.Set(net_fd.Schema.INTERFACES, interface_list)
      net_fd.Close()
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
          nested_pathspec = jobs_pb2.Path(path="/",
                                          pathtype=jobs_pb2.Path.TSK)
          pathspec = jobs_pb2.Path(path=device,
                                   pathtype=jobs_pb2.Path.OS,
                                   offset=offset,
                                   nested_path=nested_pathspec)
          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = self.client.CreateMember(urn, "VFSDirectory")
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()
          continue

        if response.device:
          # Create the raw device
          urn = "devices/%s" % response.device
          nested_pathspec = jobs_pb2.Path(path="/",
                                          pathtype=jobs_pb2.Path.TSK)

          pathspec = jobs_pb2.Path(path=response.device,
                                   pathtype=jobs_pb2.Path.OS,
                                   nested_path=nested_pathspec)

          fd = self.client.CreateMember(urn, "VFSDirectory")
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

          # Create the TSK device
          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = self.client.CreateMember(urn, "VFSDirectory")
          fd.Set(fd.Schema.PATHSPEC(pathspec))
          fd.Close()

        if response.mount_point:
          # Create the OS device
          pathspec = jobs_pb2.Path(path=response.mount_point,
                                   pathtype=jobs_pb2.Path.OS)
          urn = self.client.PathspecToURN(pathspec, self.client.urn)
          fd = self.client.CreateMember(urn, "VFSDirectory")
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
      self.client.Set(self.client.Schema.CLIENT_INFO(
          jobs_pb2.ClientInformation(client_name=response.client_name,
                                     client_version=response.client_version,
                                     revision=response.revision,
                                     build_time=response.build_time,
                                    )))
    else:
      self.Log("Could not get ClientInfo.")

  @flow.StateHandler(jobs_pb2.GRRConfig)
  def ClientConfig(self, responses):
    """Process client config."""
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.GRR_CONFIG(response))
    else:
      self.Log("Could not get client config.")

  def End(self):
    """Finalize client registration."""
    # Create the bare VFS with empty virtual directories.
    fd = aff4.FACTORY.Create(self.client.urn.Add("processes"),
                             "ProcessListing", token=self.token)
    fd.Close()
    self.Notify("Discovery", self.client.urn, "Client Discovery Complete")
