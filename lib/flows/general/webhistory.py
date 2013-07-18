#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Flow to recover history files."""


import datetime
import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.parsers import chrome_history
from grr.parsers import firefox3_history


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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathTypeEnum(
          description="Type of path access to use."),
      type_info.Bool(
          description="Should we get Archived History as well (3 months old).",
          name="get_archive",
          default=False),
      type_info.String(
          description=("The user to get Chrome history for. If history_path is "
                       "not set this will be used to guess the path to the "
                       "history files. Can be in form DOMAIN\\user."),
          name="username"),
      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/chrome-{u}-{t}"),
      type_info.String(
          description=("Path to a profile directory that contains a History "
                       "file."),
          name="history_path",
          default=""),
      )

  @flow.StateHandler(next_state="ParseFiles")
  def Start(self):
    """Determine the Chrome directory."""
    self.state.Register("hist_count", 0)
    # List of paths where history files are located
    self.state.Register("history_paths", [])
    if self.state.history_path:
      self.state.history_paths.append(self.state.history_path)

    self.state.output = self.state.output.format(t=time.time(),
                                                 u=self.state.context.user)

    self.state.Register("urn", self.client_id)
    self.state.Register("out_urn", self.state.urn.Add(self.state.output))

    if not self.state.history_paths:
      self.state.history_paths = self.GuessHistoryPaths(self.state.username)

    if not self.state.history_paths:
      raise flow.FlowError("Could not find valid History paths.")

    filenames = ["History"]
    if self.state.get_archive:
      filenames.append("Archived History")

    findspecs = []
    for path in self.state.history_paths:
      for fname in filenames:
        findspec = rdfvalue.RDFFindSpec(
            max_depth=1,
            path_regex="^{0}$".format(fname),
            pathspec=rdfvalue.PathSpec(pathtype=self.state.pathtype,
                                       path=path))

        findspecs.append(findspec)

    self.CallFlow("FileDownloader", findspecs=findspecs,
                  next_state="ParseFiles")

  @flow.StateHandler()
  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    if responses:
      outfile = aff4.FACTORY.Create(self.state.out_urn, "VFSAnalysisFile",
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
        self.Log("Wrote %d Chrome History entries for user %s from %s", count,
                 self.state.username, response.pathspec.Basename())
        self.state.hist_count += count
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
    user_info = flow_utils.GetUserInfo(client, username)
    if not user_info:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = ("{app_data}\\{sw}\\User Data\\Default")
      for sw_path in ["Google\\Chrome", "Chromium"]:
        paths.append(path.format(
            app_data=user_info.special_folders.local_app_data, sw=sw_path))
    elif system == "Linux":
      path = "{homedir}/.config/{sw}/Default"
      for sw_path in ["google-chrome", "chromium"]:
        paths.append(path.format(homedir=user_info.homedir, sw=sw_path))
    elif system == "Darwin":
      path = "{homedir}/Library/Application Support/{sw}/Default"
      for sw_path in ["Google/Chrome", "Chromium"]:
        paths.append(path.format(homedir=user_info.homedir, sw=sw_path))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths

  @flow.StateHandler()
  def End(self):
    self.SendReply(self.state.out_urn)
    self.Notify("ViewObject", self.state.out_urn,
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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.PathTypeEnum(
          description="Type of path access to use."),
      type_info.Bool(
          description="Should we get Archived History as well (3 months old).",
          name="get_archive",
          default=False),
      type_info.String(
          description=("The user to get history for. If history_path is "
                       "not set this will be used to guess the path to the "
                       "history files. Can be in form DOMAIN\\user."),
          name="username"),
      type_info.String(
          description="A path relative to the client to put the output.",
          name="output",
          default="analysis/firefox-{u}-{t}"),
      type_info.String(
          description=("Path to a profile directory that contains a History "
                       "file."),
          name="history_path",
          default=""),
      )

  @flow.StateHandler(next_state="ParseFiles")
  def Start(self):
    """Determine the Firefox history directory."""
    self.state.Register("hist_count", 0)
    if self.state.history_path:
      self.state.history_paths.append(self.state.history_path)
    else:
      self.state.history_paths = self.GuessHistoryPaths(self.state.username)

      if not self.state.history_paths:
        raise flow.FlowError("Could not find valid History paths.")

    self.state.output = self.state.output.format(t=time.time(),
                                                 u=self.state.context.user)

    self.state.Register("urn", self.client_id)
    self.state.Register("out_urn", self.state.urn.Add(self.state.output))

    filename = "places.sqlite"
    findspecs = []
    for path in self.state.history_paths:
      findspec = rdfvalue.RDFFindSpec(max_depth=2, path_regex="^%s$" % filename)

      findspec.pathspec.path = path
      findspec.pathspec.pathtype = self.state.pathtype

      findspecs.append(findspec)

    self.CallFlow("FileDownloader", findspecs=findspecs,
                  next_state="ParseFiles")

  @flow.StateHandler()
  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    if responses:
      outfile = aff4.FACTORY.Create(self.state.out_urn, "VFSAnalysisFile",
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
        self.Log("Wrote %d Firefox History entries for user %s from %s", count,
                 self.state.username, response.pathspec.Basename())
        self.state.hist_count += count
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
    user_info = flow_utils.GetUserInfo(fd, username)
    if not user_info:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = "{app_data}\\Mozilla\\Firefox\\Profiles"
      paths.append(path.format(
          app_data=user_info.special_folders.app_data))
    elif system == "Linux":
      path = "{homedir}/.mozilla/firefox"
      paths.append(path.format(homedir=user_info.homedir))
    elif system == "Darwin":
      path = ("{homedir}/Library/Application Support/"
              "Firefox/Profiles")
      paths.append(path.format(homedir=user_info.homedir))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths

  @flow.StateHandler()
  def End(self):
    self.SendReply(self.state.out_urn)
    self.Notify("ViewObject", self.state.out_urn,
                "Completed retrieval of Firefox History")


BROWSER_PATHS = {
    "Linux": {
        "Firefox": ["/home/{username}/.mozilla/firefox"],
        "Chrome": ["{homedir}/.config/google-chrome",
                   "{homedir}/.config/chromium"]
    },
    "Windows": {
        "Chrome": ["{local_app_data}\\Google\\Chrome\\User Data",
                   "{local_app_data}\\Chromium\\User Data"],
        "Firefox": ["{local_app_data}\\Mozilla\\Firefox\\Profiles"],
        "IE": ["{cache}",
               "{cache}\\Low",
               "{app_data}\\Microsoft\\Windows",
              ]
    },
    "Darwin": {
        "Firefox": ["{homedir}/Library/Application Support/Firefox/Profiles"],
        "Chrome": ["{homedir}/Library/Application Support/Google/Chrome",
                   "{homedir}/Library/Application Support/Chromium"]
    }
}


class CacheGrep(flow.GRRFlow):
  """Grep the browser profile directories for a regex.

  This will check Chrome, Firefox and Internet Explorer profile directories.
  Note that for each directory we get a maximum of 50 hits returned.
  """

  category = "/Browser/"
  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.UserList(
          name="grep_users",
          description=("A list of users to check. Default all users "
                       "on the system."),
          ),

      type_info.PathTypeEnum(),

      type_info.RegularExpression(
          name="data_regex",
          description="A regular expression to search for.",
          default=""),

      type_info.String(
          description="A path relative to the client to store the output.",
          name="output",
          default="analysis/cachegrep/{u}-{t}"),

      type_info.Bool(
          name="check_chrome",
          description="Check Chrome",
          default=True),

      type_info.Bool(
          name="check_firefox",
          description="Check Firefox",
          default=True),

      type_info.Bool(
          name="check_ie",
          description="Check Internet Explorer (Not implemented yet)",
          default=True),
      )

  @flow.StateHandler(next_state="StartRequests")
  def Start(self):
    """Redirect to start on the workers and not in the UI."""

    # Figure out which paths we are going to check.
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    paths = BROWSER_PATHS.get(system)
    self.state.Register("all_paths", [])
    if self.state.check_chrome:
      self.state.all_paths += paths.get("Chrome", [])
    if self.state.check_ie:
      self.state.all_paths += paths.get("IE", [])
    if self.state.check_firefox:
      self.state.all_paths += paths.get("Firefox", [])
    if not self.state.all_paths:
      raise flow.FlowError("Unsupported system %s for CacheGrep" % system)

    self.state.output = self.state.output.format(u=self.state.context.user,
                                                 t=time.time())

    self.state.Register("users", [])
    for user in self.state.grep_users:
      user_info = flow_utils.GetUserInfo(client, user)
      if not user_info:
        raise flow.FlowError("No such user %s" % self.state.username)
      self.state.users.append(user_info)

    self.CallState(next_state="StartRequests")

  @flow.StateHandler(next_state="HandleResults")
  def StartRequests(self):
    """Generate and send the Find requests."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.state.Register("urn", self.client_id)
    self.state.Register("out_urn", self.state.urn.Add(self.state.output))
    self.state.Register("fd", aff4.FACTORY.Create(
        self.state.out_urn, "RDFValueCollection", mode="w", token=self.token))
    self.state.fd.Set(
        self.state.fd.Schema.DESCRIPTION("CacheGrep for {0}".format(
            self.state.data_regex)))

    usernames = ["%s\\%s" % (u.domain, u.username) for u in self.state.users]
    usernames = [u.lstrip("\\") for u in usernames]  # Strip \\ if no domain.

    for path in self.state.all_paths:
      full_paths = flow_utils.InterpolatePath(path, client, users=usernames)
      for full_path in full_paths:
        findspec = rdfvalue.RDFFindSpec(data_regex=self.state.data_regex)
        findspec.iterator.number = 800
        findspec.pathspec.path = full_path
        findspec.pathspec.pathtype = self.state.pathtype

        self.CallFlow("FindFiles", findspec=findspec, max_results=200,
                      next_state="HandleResults", output=None)

  @flow.StateHandler()
  def HandleResults(self, responses):
    """Take each file we retrieved and add it to the collection."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    for response in responses:
      self.state.fd.Add(response)

  @flow.StateHandler()
  def End(self):
    self.state.fd.Close()
    self.Notify("ViewObject", self.state.out_urn,
                u"CacheGrep completed. %d hits" % self.state.fd.Get("size"))
    self.SendReply(self.state.out_urn)
