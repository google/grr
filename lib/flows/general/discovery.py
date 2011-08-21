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


from grr.lib import aff4
from grr.lib import flow

# These are the standard registry hives available on windows
REGISTRY_HIVES = [
    "HKEY_CLASSES_ROOT",
    "HKEY_CURRENT_CONFIG",
    "HKEY_CURRENT_USER",
    "HKEY_DYN_DATA",
    "HKEY_LOCAL_MACHINE",
    "HKEY_PERFORMANCE_DATA",
    "HKEY_PERFORMANCE_NLSTEXT",
    "HKEY_PERFORMANCE_TEXT",
    "HKEY_USERS",
    ]


class Interrogate(flow.GRRFlow):
  """Interrogate various things about the host."""

  category = "/Metadata/"

  @flow.StateHandler(next_state=["Hostname", "Platform",
                                 "InstallDate", "EnumerateUsers",
                                 "EnumerateInterfaces", "EnumerateFilesystems"])

  def Start(self):
    """Start off all the tests."""
    # This is used to cache the client object between consecutive State
    # execution.
    self.client = None

    self.CallClient("GetPlatformInfo", next_state="Platform")
    self.CallClient("GetInstallDate", next_state="InstallDate")
    self.CallClient("EnumerateUsers", next_state="EnumerateUsers")
    self.CallClient("EnumerateInterfaces", next_state="EnumerateInterfaces")
    self.CallClient("EnumerateFilesystems", next_state="EnumerateFilesystems")

  def Load(self):
    # Ensure there is a client object
    self.client = aff4.FACTORY.Open(self.client_id)

  def Save(self):
    # Make sure the client object is removed and closed
    if self.client:
      self.client.Close()
      self.client = None

  @flow.StateHandler()
  def Platform(self, responses):
    """Stores information about the platform."""
    if responses.success:
      response = responses.First()

      # These need to be in separate attributes because they get searched on in
      # the GUI
      self.client.Set(self.client.Schema.HOSTNAME,
                      aff4.RDFString(response.node))

      self.client.Set(self.client.Schema.SYSTEM,
                      aff4.RDFString(response.system))

      self.client.Set(self.client.Schema.OS_RELEASE,
                      aff4.RDFString(response.release))

      self.client.Set(self.client.Schema.OS_VERSION,
                      aff4.RDFString(response.version))

      self.client.Set(self.client.Schema.UNAME,
                      aff4.RDFString("%s-%s-%s" % (
                          response.system, response.version,
                          response.release)))

      # Windows systems get registry hives
      if response.system == "Windows":
        for hive in REGISTRY_HIVES:
          fd = self.client.CreateMember("registry/%s" % hive, "VFSDirectory")
          fd.Close()

  @flow.StateHandler()
  def InstallDate(self, responses):
    if responses.success:
      response = responses.First()
      self.client.Set(self.client.Schema.INSTALL_DATE,
                      aff4.RDFDatetime(response.integer * 1000000))

  @flow.StateHandler()
  def EnumerateUsers(self, responses):
    """Store all users in the data store and maintain indexes."""
    if responses.success:
      user_list = self.client.Schema.USER()
      # Add all the users to the client object
      for response in responses:
        user_list.Append(response)

      # Store it now
      self.client.AddAttribute(self.client.Schema.USER, user_list)

  @flow.StateHandler()
  def EnumerateInterfaces(self, responses):
    """Enumerates the interfaces."""
    if responses.success:
      interface_list = self.client.Schema.INTERFACE()
      mac_addresses = []
      for response in responses:
        interface_list.Append(response)

        # Add a hex encoded string for searching
        if response.mac_address != "\x00" * len(response.mac_address):
          mac_addresses.append(response.mac_address.encode("hex"))

      self.client.Set(self.client.Schema.INTERFACE, interface_list)
      self.client.Set(self.client.Schema.MAC_ADDRESS, aff4.RDFString(
          "\n".join(mac_addresses)))

  @flow.StateHandler()
  def EnumerateFilesystems(self, responses):
    """Store all the local filesystems in the client."""
    if responses.success:
      filesystems = self.client.Schema.FILESYSTEM()
      for response in responses:
        filesystems.Append(response)

        # Also create mount points for all the filesystems and raw devices.
        fd = self.client.CreateMember(response.device, "VFSDirectory")
        fd.Close()

        fd = self.client.CreateMember(response.mount_point, "VFSDirectory")
        fd.Close()

      self.client.Set(self.client.Schema.FILESYSTEM, filesystems)
