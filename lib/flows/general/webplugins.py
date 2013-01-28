#!/usr/bin/env python
# Copyright 2011 Google Inc.
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


"""Parser for Google chrome/chromium History files."""



import json
import os.path
import time


import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class ChromePlugins(flow.GRRFlow):
  r"""Extract information about the installed Chrome extensions.

  Default directories as per:
    http://www.chromium.org/user-experience/user-data-directory

  Windows XP
  Google Chrome:
  c:\Documents and Settings\<username>\Local Settings\
  Application Data\Google\Chrome\User Data\Default\Extensions

  Windows 7 or Vista
  c:\Users\<username>\AppData\Local\Google\Chrome\User Data\Default\Extensions

  Mac OS X
  /Users/<user>/Library/Application Support/Google/Chrome/Default/Extensions

  Linux
  /home/<user>/.config/google-chrome/Default/Extensions
  """

  category = "/Browser/"
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description=("A path to a Chrome Extensions directory. If not set, "
                       "the path is guessed from the username."),
          name="path",
          default=""),
      type_info.PathTypeEnum(),
      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/chromeplugins-{u}-{t}"),

      type_info.String(
          description=("The user to get Chrome extensions for."),
          name="username",
          default=""),

      type_info.Bool(
          name="download_files",
          description="Should extensions be downloaded?",
          default=False),
      )

  @flow.StateHandler(next_state=["EnumerateExtensionDirs"])
  def Start(self):
    """Determine the Chrome directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    self.output = self.output.format(t=time.time(), u=self.username)
    self.out_urn = self.urn.Add(self.output)
    self._storage = {}

    if self.path:
      self._paths = [self.path]
    elif self.username:
      self._paths = self.GuessExtensionPaths(self.username)

    if not self._paths:
      raise flow.FlowError("No valid extension paths found.")

    for path in self._paths:
      rel_path = utils.JoinPath(path, "Extensions")
      pathspec = rdfvalue.RDFPathSpec(path=rel_path, pathtype=self.pathtype)
      self.CallClient("ListDirectory", next_state="EnumerateExtensionDirs",
                      pathspec=pathspec)

  @flow.StateHandler(next_state=["EnumerateVersions"])
  def EnumerateExtensionDirs(self, responses):
    """Enumerates all extension directories."""
    if responses.success:
      for response in responses:
        chromeid = os.path.basename(response.pathspec.last.path)

        self._storage[chromeid] = {}
        self.CallClient("ListDirectory", next_state="EnumerateVersions",
                        pathspec=response.pathspec)

  @flow.StateHandler(next_state=["GetExtensionName"])
  def EnumerateVersions(self, responses):
    """Enumerates all extension version directories."""
    if responses.success:
      for response in responses:
        # Get the json manifest.
        pathspec = response.pathspec
        pathspec.Append(pathtype=self.pathtype, path="manifest.json")

        self.CallFlow("GetFile", next_state="GetExtensionName",
                      pathspec=pathspec)

  @flow.StateHandler(next_state=["GetLocalizedName", "Done"])
  def GetExtensionName(self, responses):
    """Gets the name of the extension from the manifest."""
    if responses.success:
      # The pathspec to the manifest file
      file_stat = responses.First()

      extension_directory = file_stat.pathspec.Dirname()

      # Read the manifest file which should be just json - already stored in
      fd = aff4.FACTORY.Open(file_stat.aff4path, token=self.token)
      try:
        manifest_data = fd.read(1000000)
        manifest = json.loads(manifest_data)
      except ValueError:
        self.Log("Unable to parse %s as json. Continuing.", fd.urn)
        return

      ext_name = manifest.get("name", "")
      if ext_name.startswith("__MSG_"):
        # Extension has a localized name
        if "default_locale" in manifest:
          msg_path = extension_directory.Copy().Append(
              pathtype=self.pathtype,
              path="_locales/" + manifest["default_locale"] + "/messages.json")

          request_data = dict(
              manifest_data=manifest_data,
              extension_directory=extension_directory)

          self.CallFlow("GetFile", next_state="GetLocalizedName",
                        pathspec=msg_path, request_data=request_data)
          return
        else:
          logging.error("Malformed extension %s, missing default_locale.",
                        extension_directory.CollapsePath())
          # Continue with __MSG_... extension name

      self.CreateAnalysisVFile(extension_directory, manifest)

      if self.download_files:
        self.CallFlow("DownloadDirectory", next_state="Done",
                      pathspec=extension_directory)

  @flow.StateHandler(next_state="Done")
  def GetLocalizedName(self, responses):
    """Determines the name of the extension if the extension uses locales."""
    if responses.success:
      manifest = json.loads(responses.request_data["manifest_data"])
      extension_directory = responses.request_data["extension_directory"]

      # Parse the locale json.
      urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
          responses.First().pathspec, self.client_id)

      fd = aff4.FACTORY.Open(urn, token=self.token)

      msg = manifest["name"][6:].rstrip("_")

      try:
        messages = json.loads(fd.read(1000000))
        # Update the extension name from the locale messages
        manifest["name"] = messages[msg]["message"]
      except (ValueError, KeyError):
        pass

    else:
      logging.error("Malformed extension: localization file not found (%s).",
                    manifest["name"])

    self.CreateAnalysisVFile(extension_directory, manifest)

    if self.download_files:
      self.CallFlow("DownloadDirectory", next_state="Done",
                    pathspec=extension_directory)

  def CreateAnalysisVFile(self, extension_directory, manifest):
    """Creates the analysis result object."""
    version = manifest.get("version", extension_directory.Basename())
    chromeid = extension_directory.Dirname().Basename()
    name = manifest.get("name", "unknown_" + chromeid)

    ext_urn = self.out_urn.Add(name).Add(version)

    fd = aff4.FACTORY.Create(ext_urn, "VFSBrowserExtension",
                             token=self.token)

    fd.Set(fd.Schema.NAME(name))
    fd.Set(fd.Schema.VERSION(version))
    fd.Set(fd.Schema.CHROMEID(chromeid))
    if "update_url" in manifest:
      fd.Set(fd.Schema.UPDATEURL(manifest["update_url"]))
    if "permissions" in manifest:
      fd.Set(fd.Schema.PERMISSIONS(";".join(manifest["permissions"])))

    fd.Set(fd.Schema.EXTENSIONDIR(extension_directory.last.path))
    fd.Close()

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      logging.error("Error downloading directory recursively.")

  @flow.StateHandler()
  def End(self):
    self.Notify("ViewObject", self.out_urn,
                "Completed retrieval of Chrome Plugins")

  def GuessExtensionPaths(self, user):
    """Take a user and return guessed full paths to Extension files.

    Args:
      user: Username as string.

    Returns:
      A list of strings containing paths to look for extension files in.

    Raises:
      OSError: On invalid system in the Schema.
    """
    client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id),
                               token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    paths = []
    profile_path = "Default"

    user_pb = flow_utils.GetUserInfo(client, user)
    if not user_pb:
      logging.error("User not found")
      return []

    if system == "Windows":
      path = ("%(local_app_data)s/%(sw)s/User Data/%(profile)s")
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path % {
            "local_app_data": user_pb.special_folders.local_app_data, "sw": p,
            "profile": profile_path})

    elif system == "Linux":
      path = "%(home_path)s/.config/%(sw)s/%(profile)s"
      for p in ["google-chrome", "chromium"]:
        paths.append(path % {"home_path": user_pb.homedir, "sw": p,
                             "profile": profile_path})

    elif system == "Darwin":
      path = "%(home_path)s/Library/Application Support/%(sw)s/%(profile)s"
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path % {"home_path": user_pb.homedir, "sw": p,
                             "profile": profile_path})

    else:
      logging.error("Invalid OS for Chrome extensions")
      raise OSError

    return paths
