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

"""Flow to recover history files."""


import datetime

import logging

from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.parsers import chrome_history


class ChromeHistory(flow.GRRFlow):
  """Retrieve and analyze the chrome history for a machine.

  Default directories as per:
    http://www.chromium.org/user-experience/user-data-directory

  Windows XP
  Google Chrome:
  /c/Documents and Settings/<username>/Local Settings/Application Data/Google/Chrome/User Data/Default

  Windows 7 or Vista
  /c/Users/<username>/AppData/Local/Google/Chrome/User Data/Default

  Mac OS X
  /Users/<user>/Library/Application Support/Google/Chrome/Default

  Linux
  /home/<user>/.config/google-chrome/Default
  """

  category = "/Browser/"

  def __init__(self, user, history_path=None, **kwargs):
    """Constructor.

    Args:
      user: String, the user to get Chrome history for. If history_path is not
        set this will be used to guess the path to the history files.
      history_path: A specific file to parse.

      kwargs: passthrough.
    """
    self.history_paths = []   # List of paths where history files are located
    if history_path:
      self.history_paths = [history_path]
    self.user = user

    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state=["ParseFiles"])
  def Start(self):
    """Determine the Chrome directory."""
    self.urn = aff4.ROOT_URN.Copy().Add(self.client_id)
    if not self.history_paths:
      self.history_paths = self.GuessHistoryPaths(self.user)

    for path in self.history_paths:
      # History is the main file, Archived History contains data older than
      # 3 months.
      for f in ["History", "Archived History"]:
        full_path = self.urn.Copy().Add(path).Add(f)
        rel_path = "/" + full_path.RelativeName(self.urn)
        #TODO(user): Add args to response object to remove need for data.
        self.CallFlow("GetFile", next_state="ParseFiles", path=rel_path,
                      request_data=dict(path=utils.SmartStr(rel_path)))

  @flow.StateHandler()
  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    if responses.success:
      outfile = aff4.FACTORY.Create(self.urn.Copy().Add("analysis/chrome.txt"),
                                    "VFSAnalysisFile")
      fd = aff4.FACTORY.Open(self.urn.Copy().Add(
          responses.request_data["path"]))
      hist = chrome_history.ChromeParser(fd)
      count = 0
      temp = []
      for epoch64, dtype, url, dat1, dat2 in hist.Parse():
        count += 1
        str_entry = "%s %s %s %s %s" % (
            datetime.datetime.utcfromtimestamp(epoch64/1e6), url,
            dat1, dat2, dtype)
        temp.append(utils.SmartStr(str_entry))
        if not count % 10000:  # Write in batches to avoid datastore hits
          outfile.write("\n".join(temp))
          temp = []
      outfile.write("\n".join(temp))

      self.Log("Wrote %d Chrome History entries for user %s", count, self.user)
      outfile.Close()

  def GuessHistoryPaths(self, user, driveroot=None):
    """Take a user and return guessed full paths to History files.

    Args:
      user: Username as string.
      driveroot: Path to drive root, e.g. /dev/c or /c

    Returns:
      A list of strings containing paths to look for history files in.

    Raises:
      OSError: On invalid system in the Schema
    """
    # TODO(user): Split a GetHomedir function into a utility function.
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Copy().Add(self.client_id), mode="r")
    system = fd.Get(fd.Schema.SYSTEM)
    release = str(fd.Get(fd.Schema.OS_RELEASE))
    version = str(fd.Get(fd.Schema.OS_VERSION)).split(".")
    major_version = int(version[0])
    paths = []

    if system == "Windows":
      if major_version < 6 or "XP" in release:  # XP
        path = ("{driveroot}/Documents and Settings/{user}/Local Settings/"
                "Application Data/{sw}/User Data/Default")
      else:
        path = "{driveroot}/Users/{user}/AppData/Local/{sw}/User Data/Default"
      if driveroot is None:
        driveroot = "/dev/c"    # default to raw reads.
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path.format(driveroot=driveroot, user=user, sw=p))

    elif system == "Linux":
      #TODO(user): This won't work on non /home homedirs, need to parse
      #              /etc/passwd to get the real one.
      path = "{homeroot}/{user}/.config/{sw}/Default"
      if driveroot is None:
        filesystems = aff4.FACTORY.Open(self.urn).Get(fd.Schema.FILESYSTEM)
        home = [x for x in filesystems if x.mount_point == "/home"]
        if home:
          homeroot = home[0].device
        else:
          root = [x for x in filesystems if x.mount_point == "/"]
          if root:
            homeroot = root[0].device + "/home"
          else:
            homeroot = "/home"

      for p in ["google-chrome", "chromium"]:
        paths.append(path.format(homeroot=homeroot, user=user, sw=p))

    elif system == "MacOS":
      #TODO(user): what is the real path?
      path = "{driveroot}/Users/{user}/Library/Application Support/{sw}/Default"
      if driveroot is None:
        driveroot = "/dev"    # default to raw reads.
      for p in ["Google/Chrome", "Chromium"]:
        paths.append(path.format(driveroot=driveroot, user=user, sw=p))

    else:
      logging.error("Invalid OS for Chrome History")
      raise OSError
    return paths
