#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""Parser for Google chrome/chromium History files."""



import json
import os.path


import logging
from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import flows_pb2


class ChromePluginsArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ChromePluginsArgs


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
  args_type = ChromePluginsArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler(next_state=["EnumerateExtensionDirs"])
  def Start(self):
    """Determine the Chrome directory."""
    self.state.Register("storage", {})

    if self.args.path:
      paths = [self.args.path]

    elif self.args.username:
      paths = self.GuessExtensionPaths(self.args.username)

    if not paths:
      raise flow.FlowError("No valid extension paths found.")

    for path in paths:
      rel_path = utils.JoinPath(path, "Extensions")
      pathspec = rdfvalue.PathSpec(path=rel_path,
                                   pathtype=self.args.pathtype)
      self.CallClient("ListDirectory", next_state="EnumerateExtensionDirs",
                      pathspec=pathspec)

  @flow.StateHandler(next_state=["EnumerateVersions"])
  def EnumerateExtensionDirs(self, responses):
    """Enumerates all extension directories."""
    if responses.success:
      for response in responses:
        chromeid = os.path.basename(response.pathspec.last.path)

        self.state.storage[chromeid] = {}
        self.CallClient("ListDirectory", next_state="EnumerateVersions",
                        pathspec=response.pathspec)

  @flow.StateHandler(next_state=["GetExtensionName"])
  def EnumerateVersions(self, responses):
    """Enumerates all extension version directories."""
    if responses.success:
      pathspecs = []

      for response in responses:
        # Get the json manifest.
        pathspec = response.pathspec
        pathspec.Append(pathtype=self.args.pathtype, path="manifest.json")
        pathspecs.append(pathspec)

      self.CallFlow("MultiGetFile", next_state="GetExtensionName",
                    pathspecs=pathspecs)

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
              pathtype=self.args.pathtype,
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

      if self.args.download_files:
        self.CallFlow(
            "FileFinder",
            paths=[os.path.join(extension_directory.CollapsePath(), "**3")],
            action=rdfvalue.FileFinderAction(
                action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD),
            next_state="Done")

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

    if self.args.download_files:
      self.CallFlow(
          "FileFinder",
          paths=[os.path.join(extension_directory.CollapsePath(), "**3")],
          action=rdfvalue.FileFinderAction(
              action_type=rdfvalue.FileFinderAction.Action.DOWNLOAD),
          next_state="Done")

  def CreateAnalysisVFile(self, extension_directory, manifest):
    """Creates the analysis result object."""
    if self.runner.output is None:
      return

    version = manifest.get("version", extension_directory.Basename())
    chromeid = extension_directory.Dirname().Basename()
    name = manifest.get("name", "unknown_" + chromeid)

    ext_urn = self.runner.output.urn.Add(name).Add(version)

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

  def GuessExtensionPaths(self, user):
    """Take a user and return guessed full paths to Extension files.

    Args:
      user: Username as string.

    Returns:
      A list of strings containing paths to look for extension files in.

    Raises:
      OSError: On invalid system in the Schema.
    """
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
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
