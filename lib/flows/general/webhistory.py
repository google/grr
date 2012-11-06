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
import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import type_info
from grr.lib import utils
from grr.parsers import chrome_history
from grr.parsers import firefox3_history
from grr.proto import jobs_pb2


class ChromeHistory(flow.GRRFlow):
  """Retrieve and analyze the chrome history for a machine.

  Default directories as per:
    http://www.chromium.org/user-experience/user-data-directory

  Windows XP
  Google Chrome:
  c:\\Documents and Settings\\<username>\\Local Settings\\Application Data\\
    Google\\Chrome\\User Data\\Default

  Windows 7 or Vista
  c:\\Users\\<username>\\AppData\\Local\\Google\\Chrome\\User Data\\Default

  Mac OS X
  /Users/<user>/Library/Application Support/Google/Chrome/Default

  Linux
  /home/<user>/.config/google-chrome/Default
  """

  category = "/Browser/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType"),
                   "get_archive": type_info.Bool()}

  def __init__(self, username="", history_path=None,
               get_archive=False,
               pathtype=jobs_pb2.Path.TSK,
               output="analysis/chrome-{u}-{t}",
               **kwargs):
    """Constructor.

    Args:
      username: String, the user to get Chrome history for. If history_path is
          not set this will be used to guess the path to the history files. Can
          be in form DOMAIN\\user.
      history_path: Path to a profile directory that contains a History file.
      get_archive: Should we get Archived History as well (3 months old).
      pathtype: Type of path to use.
      output: A path relative to the client to put the output.
      **kwargs: passthrough.
    """
    self.pathtype = pathtype
    self.username = username
    self.get_archive = get_archive
    self.hist_count = 0
    self.history_paths = []   # List of paths where history files are located
    if history_path:
      self.history_paths = [history_path]

    flow.GRRFlow.__init__(self, **kwargs)
    self.output = output.format(t=time.time(), u=self.username)

  @flow.StateHandler(next_state="ParseFiles")
  def Start(self):
    """Determine the Chrome directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    self.out_urn = self.urn.Add(self.output)
    if not self.history_paths:
      self.history_paths = self.GuessHistoryPaths(self.username)
    if not self.history_paths:
      raise flow.FlowError("Could not find valid History paths.")

    filenames = ["History"]
    if self.get_archive:
      filenames.append("Archived History")

    findspecs = []
    for path in self.history_paths:
      for fname in filenames:
        pathspec = jobs_pb2.Path(pathtype=int(self.pathtype),
                                 path=path)
        findspecs.append(
            jobs_pb2.Find(pathspec=pathspec, max_depth=1,
                          path_regex="^{0}$".format(fname)))

    self.CallFlow("FileDownloader", findspecs=findspecs,
                  next_state="ParseFiles")

  @flow.StateHandler(jobs_pb2.StatResponse)
  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    if responses:
      outfile = aff4.FACTORY.Create(self.out_urn, "VFSAnalysisFile",
                                    token=self.token)
      for response in responses:
        fd = aff4.FACTORY.Open(response.aff4path, token=self.token)
        hist = chrome_history.ChromeParser(fd)
        count = 0
        for epoch64, dtype, url, dat1, dat2, dat3 in hist.Parse():
          count += 1
          str_entry = "%s %s %s %s %s %s" % (
              datetime.datetime.utcfromtimestamp(epoch64/1e6), url,
              dat1, dat2, dat3, dtype)
          outfile.write(utils.SmartStr(str_entry) + "\n")
        path_obj = utils.Pathspec(response.pathspec)
        self.Log("Wrote %d Chrome History entries for user %s from %s", count,
                 self.user, path_obj.Basename())
        self.hist_count += count
      outfile.Close()

  def GuessHistoryPaths(self, username):
    """Take a user and return guessed full paths to History files.

    Args:
      username: Username as string.

    Returns:
      A list of strings containing paths to look for history files in.

    Raises:
      OSError: On invalid system in the Schema
    """
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    user_pb = flow_utils.GetUserInfo(client, username)
    if not user_pb:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = ("{app_data}\\{sw}\\User Data\\Default")
      for sw_path in ["Google\\Chrome", "Chromium"]:
        paths.append(path.format(
            app_data=user_pb.special_folders.local_app_data, sw=sw_path))
    elif system == "Linux":
      path = "{homedir}/.config/{sw}/Default"
      for sw_path in ["google-chrome", "chromium"]:
        paths.append(path.format(homedir=user_pb.homedir, sw=sw_path))
    elif system == "Darwin":
      path = "{homedir}/Library/Application Support/{sw}/Default"
      for sw_path in ["Google/Chrome", "Chromium"]:
        paths.append(path.format(homedir=user_pb.homedir, sw=sw_path))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths

  @flow.StateHandler()
  def End(self):
    self.SendReply(jobs_pb2.URN(urn=utils.SmartUnicode(self.out_urn)))
    self.Notify("ViewObject", self.out_urn,
                "Completed retrieval of Chrome History")


class FirefoxHistory(flow.GRRFlow):
  """Retrieve and analyze the Firefox history for a machine.

  Default directories as per:
    http://www.forensicswiki.org/wiki/Mozilla_Firefox_3_History_File_Format

  Windows XP
    C:\\Documents and Settings\\<username>\\Application Data\\Mozilla\\
      Firefox\\Profiles\\<profile folder>\\places.sqlite

  Windows Vista
    C:\\Users\\<user>\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\
      <profile folder>\\places.sqlite

  GNU/Linux
    /home/<user>/.mozilla/firefox/<profile folder>/places.sqlite

  Mac OS X
    /Users/<user>/Library/Application Support/Firefox/Profiles/
      <profile folder>/places.sqlite
  """

  category = "/Browser/"
  flow_typeinfo = {"pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType")}

  def __init__(self, username="", history_path=None,
               pathtype=jobs_pb2.Path.TSK,
               output="analysis/firefox-{u}-{t}", **kwargs):
    """Constructor.

    Args:
      username: String, the user to get the history for. If history_path is
          not set this will be used to guess the path to the history files. Can
          be in form DOMAIN\\user.
      history_path: Path to a profile directory containing a places.sqlite file.
      pathtype: Type of path to use.
      output: A path relative to the client to put the output.
      **kwargs: passthrough.
    """
    flow.GRRFlow.__init__(self, **kwargs)
    self.pathtype = pathtype
    self.username = username
    self.hist_count = 0
    self.history_paths = []   # List of paths where history files are located
    if history_path:
      self.history_paths = [history_path]
    else:
      self.history_paths = self.GuessHistoryPaths(self.username)
      if not self.history_paths:
        raise flow.FlowError("Could not find valid History paths.")

    self.output = output.format(t=time.time(), u=self.username)

  @flow.StateHandler(next_state="ParseFiles")
  def Start(self):
    """Determine the Firefox history directory."""
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    self.out_urn = self.urn.Add(self.output)

    filename = "places.sqlite"
    findspecs = []
    for path in self.history_paths:
      pathspec = jobs_pb2.Path(pathtype=int(self.pathtype),
                               path=path)
      findspecs.append(
          jobs_pb2.Find(pathspec=pathspec, max_depth=2,
                        path_regex="^%s$" % filename))
    self.CallFlow("FileDownloader", findspecs=findspecs,
                  next_state="ParseFiles")

  @flow.StateHandler()
  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    if responses:
      outfile = aff4.FACTORY.Create(self.out_urn, "VFSAnalysisFile",
                                    token=self.token)
      for response in responses:
        fd = aff4.FACTORY.Open(response.aff4path, token=self.token)
        hist = firefox3_history.Firefox3History(fd)
        count = 0
        for epoch64, dtype, url, dat1, in hist.Parse():
          count += 1
          str_entry = "%s %s %s %s" % (
              datetime.datetime.utcfromtimestamp(epoch64/1e6), url,
              dat1, dtype)
          outfile.write(utils.SmartStr(str_entry) + "\n")
        path_obj = utils.Pathspec(response.pathspec)
        self.Log("Wrote %d Firefox History entries for user %s from %s", count,
                 self.user, path_obj.Basename())
        self.hist_count += count
      outfile.Close()

  def GuessHistoryPaths(self, username):
    """Take a user and return guessed full paths to History files.

    Args:
      username: Username as string.

    Returns:
      A list of strings containing paths to look for history files in.

    Raises:
      OSError: On invalid system in the Schema
    """
    fd = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = fd.Get(fd.Schema.SYSTEM)
    user_pb = flow_utils.GetUserInfo(fd, username)
    if not user_pb:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = "{app_data}\\Mozilla\\Firefox\\Profiles"
      paths.append(path.format(
          app_data=user_pb.special_folders.app_data))
    elif system == "Linux":
      path = "{homedir}/.mozilla/firefox"
      paths.append(path.format(homedir=user_pb.homedir))
    elif system == "Darwin":
      path = ("{homedir}/Library/Application Support/"
              "Firefox/Profiles")
      paths.append(path.format(homedir=user_pb.homedir))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths

  @flow.StateHandler()
  def End(self):
    self.SendReply(jobs_pb2.URN(urn=utils.SmartUnicode(self.out_urn)))
    self.Notify("ViewObject", self.out_urn,
                "Completed retrieval of Firefox History")
