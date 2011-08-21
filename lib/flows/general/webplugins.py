#!/usr/bin/env python
#
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


import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import utils
from grr.proto import jobs_pb2


class ChromePlugins(flow.GRRFlow):
  """Extract information about the installed Chrome extensions.

  Default directories as per:
    http://www.chromium.org/user-experience/user-data-directory

  Windows XP
  Google Chrome:
  /c/Documents and Settings/<username>/Local Settings/
  Application Data/Google/Chrome/User Data/Default/Extensions

  Windows 7 or Vista
  /c/Users/<username>/AppData/Local/Google/Chrome/User Data/Default/Extensions

  Mac OS X
  /Users/<user>/Library/Application Support/Google/Chrome/Default/Extensions

  Linux
  /home/<user>/.config/google-chrome/Default/Extensions
  """

  category = "/Browser/"

  def __init__(self, download_files=False, path=None,
               username=None, domain=None, raw=True, **kwargs):
    """Constructor.

    Args:
      download_files: If set to 1, all files belonging to the extension
        are downloaded for analysis.

      path: A path to a Chrome Extensions directory. If path is None, the
        directory is guessed.

      username: String, the user to get Chrome extension info for. If path
        is not set this will be used to guess the path to the extensions.

      domain: For Windows clients this is the domain of the analyzed user.

      raw: Use raw access to download extension files.

      kwargs: passthrough.
    """
    self._paths = []

    if path:
      self._paths = [path]

    self._username = username
    self._domain = domain
    self._download_files = download_files
    self._storage = {}
    self._raw = raw
    if raw:
      self._ptype = jobs_pb2.Path.TSK
    else:
      self._ptype = jobs_pb2.Path.OS

    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["EnumerateExtensionDirs"])
  def Start(self):
    """Determine the Chrome directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)

    if not self._paths:
      self._paths = self.GuessExtensionPaths(self._username, self._domain)

    for path in self._paths:
      rel_path = utils.JoinPath(path, "Extensions")
      p = jobs_pb2.Path(path=rel_path, pathtype=self._ptype)
      self.CallClient("ListDirectory", next_state="EnumerateExtensionDirs",
                      pathspec=p)

  @flow.StateHandler(next_state=["EnumerateVersions"])
  def EnumerateExtensionDirs(self, responses):
    """Enumerates all extension directories."""
    if responses.success:
      for extension in responses:
        _, chromeid = os.path.split(extension.pathspec.path)
        self._storage[chromeid] = {}
        self.CallClient("ListDirectory", next_state="EnumerateVersions",
                        pathspec=extension.pathspec,
                        request_data=dict(chromeid=chromeid))

  @flow.StateHandler(next_state=["GetExtensionName"])
  def EnumerateVersions(self, responses):
    """Enumerates all extension version directories."""
    if responses.success:
      chromeid = responses.request_data["chromeid"]

      for response in responses:
        _, version = os.path.split(response.pathspec.path)
        ext_path = utils.JoinPath(response.pathspec.mountpoint,
                                  response.pathspec.path)
        manifest_path = utils.JoinPath(ext_path, "manifest.json")
        self.CallFlow("GetFile", next_state="GetExtensionName",
                      path=manifest_path, pathtype=self._ptype,
                      request_data=dict(path=ext_path,
                                        version=version,
                                        chromeid=chromeid))

  @flow.StateHandler(jobs_pb2.Path, next_state=["GetLocalizedName", "Done"])
  def GetExtensionName(self, responses):
    """Gets the name of the extension from the manifest."""
    if responses.success:
      ext_version = responses.request_data["version"]
      ext_path = responses.request_data["path"]
      chromeid = responses.request_data["chromeid"]

      aff4path = utils.PathspecToAff4(responses.First())
      fd = aff4.FACTORY.Open(self.urn.Add(aff4path))

      manifest = json.loads(fd.read(1000000))
      if chromeid not in self._storage:
        self._storage[chromeid] = {}
      manifest["ext_dir"] = ext_path
      self._storage[chromeid][ext_version] = manifest

      ext_name = manifest["name"]
      if ext_name.startswith("__MSG_"):
        # Extension has a localized name
        if "default_locale" in manifest:
          msg_path = utils.JoinPath(ext_path, "_locales",
                                    manifest["default_locale"],
                                    "messages.json")
          msg = ext_name[6:].rstrip("_")
          self.CallFlow("GetFile", next_state="GetLocalizedName",
                        path=msg_path, pathtype=self._ptype,
                        request_data=dict(ext_path=ext_path,
                                          ext_version=ext_version,
                                          msg_path=msg_path,
                                          chromeid=chromeid,
                                          msg=msg))
          return
        else:
          logging.error("Malformed extension %s, missing default_locale.",
                        chromeid)
          # Continue with __MSG_... extension name

      self.CreateAnalysisVFile(ext_name, ext_version, chromeid)

      if self._download_files:
        self.CallFlow("DownloadDirectory", next_state="Done",
                      raw=self._raw, path=ext_path)

  @flow.StateHandler(jobs_pb2.Path, next_state="Done")
  def GetLocalizedName(self, responses):
    """Determines the name of the extension if the extension uses locales."""
    ext_path = responses.request_data["ext_path"]
    ext_version = responses.request_data["ext_version"]
    chromeid = responses.request_data["chromeid"]
    msg_path = responses.request_data["msg_path"]
    ext_name = "unknown_" + chromeid

    if responses.success:
      fd = aff4.FACTORY.Open(self.urn.Add(
          utils.PathspecToAff4(responses.First())))

      try:
        messages = json.loads(fd.read(1000000))
        ext_name = messages[responses.request_data["msg"]]["message"]
      except ValueError:
        pass

    else:
      logging.error("Malformed extension: localization file not found (%s).",
                    msg_path)
    self.CreateAnalysisVFile(ext_name, ext_version, chromeid)

    if self._download_files:
      self.CallFlow("DownloadDirectory", next_state="Done",
                    path=ext_path, raw=self._raw)

  def CreateAnalysisVFile(self, name, version, chromeid):
    """Creates the analysis result object."""

    manifest = self._storage[chromeid][version]
    if "version" in manifest:
      version = manifest["version"]

    ext_path = "Analysis/Applications/Chrome/Extensions/"
    path = self.urn.Add(ext_path).Add(name).Add(version)

    fd = aff4.FACTORY.Create(path, "VFSBrowserExtension")

    fd.Set(fd.Schema.NAME, aff4.RDFString(name))
    fd.Set(fd.Schema.VERSION, aff4.RDFString(version))
    fd.Set(fd.Schema.CHROMEID, aff4.RDFString(chromeid))
    if "update_url" in manifest:
      fd.Set(fd.Schema.UPDATEURL, aff4.RDFString(manifest["update_url"]))
    if "permissions" in manifest:
      fd.Set(fd.Schema.PERMISSIONS,
             aff4.RDFString(";".join(manifest["permissions"])))
    fd.Set(fd.Schema.EXTENSIONDIR, aff4.RDFString(manifest["ext_dir"]))
    fd.Close()

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      logging.error("Error downloading directory recursively.")

  def GuessExtensionPaths(self, user, domain=None):
    """Take a user and return guessed full paths to Extension files.

    Args:
      user: Username as string.
      domain: For windows systems, the users domain.

    Returns:
      A list of strings containing paths to look for extension files in.

    Raises:
      OSError: On invalid system in the Schema.
    """
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id), mode="r")
    system = fd.Get(fd.Schema.SYSTEM)

    profile_path = "Default"

    paths = []

    home_path = flow_utils.GetHomedirPath(self.client_id, user, domain=domain)

    if not home_path:
      logging.error("User not found")
      return []

    if system == "Windows":
      version = str(fd.Get(fd.Schema.OS_VERSION)).split(".")
      major_version = int(version[0])
      if major_version < 6 or "XP" in version:  # XP
        path = ("%(home_path)s/Local Settings/"
                "Application Data/%(sw)s/User Data/%(profile)s")
      else:
        path = "%(home_path)s/AppData/Local/%(sw)s/User Data/%(profile)s"
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path % {"home_path": home_path, "sw": p,
                             "profile": profile_path})

    elif system == "Linux":
      path = "%(home_path)s/.config/%(sw)s/%(profile)s"
      for p in ["google-chrome", "chromium"]:
        paths.append(path % {"home_path": home_path, "sw": p,
                             "profile": profile_path})

    elif system == "MacOS":
      path = "%(home_path)s/Library/Application Support/%(sw)s/%(profile)s"
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path % {"home_path": home_path, "sw": p,
                             "profile": profile_path})

    else:
      logging.error("Invalid OS for Chrome extensions")
      raise OSError

    return paths
