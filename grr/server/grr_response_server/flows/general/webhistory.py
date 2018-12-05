#!/usr/bin/env python
"""Flow to recover history files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

# DISABLED for now until it gets converted to artifacts.

import datetime
import os

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.parsers import chrome_history
from grr_response_core.lib.parsers import firefox3_history
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_utils
from grr_response_server.flows.general import file_finder


class ChromeHistoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ChromeHistoryArgs


@flow_base.DualDBFlow
class ChromeHistoryMixin(object):
  r"""Retrieve and analyze the chrome history for a machine.

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
  args_type = ChromeHistoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    """Determine the Chrome directory."""
    self.state.hist_count = 0
    # List of paths where history files are located
    self.state.history_paths = []
    if self.args.history_path:
      self.state.history_paths.append(self.args.history_path)

    if not self.state.history_paths:
      self.state.history_paths = self.GuessHistoryPaths(self.args.username)

    if not self.state.history_paths:
      raise flow.FlowError("Could not find valid History paths.")

    filenames = ["History"]
    if self.args.get_archive:
      filenames.append("Archived History")

    for path in self.state.history_paths:
      for fname in filenames:
        self.CallFlow(
            file_finder.FileFinder.__name__,
            paths=[os.path.join(path, fname)],
            pathtype=self.args.pathtype,
            action=rdf_file_finder.FileFinderAction.Download(),
            next_state="ParseFiles")

  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    if responses:
      for response in responses:
        if data_store.RelationalDBReadEnabled("filestore"):
          client_path = db.ClientPath.FromPathSpec(self.client_id,
                                                   response.stat_entry.pathspec)
          fd = file_store.OpenFile(client_path)
        else:
          fd = aff4.FACTORY.Open(
              response.stat_entry.AFF4Path(self.client_urn), token=self.token)

        hist = chrome_history.ChromeParser(fd)
        count = 0
        for epoch64, dtype, url, dat1, dat2, dat3 in hist.Parse():
          count += 1
          str_entry = "%s %s %s %s %s %s" % (datetime.datetime.utcfromtimestamp(
              epoch64 / 1e6), url, dat1, dat2, dat3, dtype)
          self.SendReply(rdfvalue.RDFString(utils.SmartStr(str_entry)))

        self.Log("Wrote %d Chrome History entries for user %s from %s", count,
                 self.args.username, response.stat_entry.pathspec.Basename())
        self.state.hist_count += count

  def GuessHistoryPaths(self, username):
    """Take a user and return guessed full paths to History files.

    Args:
      username: Username as string.

    Returns:
      A list of strings containing paths to look for history files in.

    Raises:
      OSError: On invalid system in the Schema
    """
    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      system = client.knowledge_base.os
      user_info = flow_utils.GetUserInfo(client.knowledge_base, username)
    else:
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      system = client.Get(client.Schema.SYSTEM)
      kb = client.Get(client.Schema.KNOWLEDGE_BASE)
      user_info = flow_utils.GetUserInfo(kb, username)

    if not user_info:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = ("{app_data}\\{sw}\\User Data\\Default\\")
      for sw_path in ["Google\\Chrome", "Chromium"]:
        paths.append(path.format(app_data=user_info.localappdata, sw=sw_path))
    elif system == "Linux":
      path = "{homedir}/.config/{sw}/Default/"
      for sw_path in ["google-chrome", "chromium"]:
        paths.append(path.format(homedir=user_info.homedir, sw=sw_path))
    elif system == "Darwin":
      path = "{homedir}/Library/Application Support/{sw}/Default/"
      for sw_path in ["Google/Chrome", "Chromium"]:
        paths.append(path.format(homedir=user_info.homedir, sw=sw_path))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths


class FirefoxHistoryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FirefoxHistoryArgs


@flow_base.DualDBFlow
class FirefoxHistoryMixin(object):
  r"""Retrieve and analyze the Firefox history for a machine.

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
  args_type = FirefoxHistoryArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    """Determine the Firefox history directory."""
    self.state.hist_count = 0
    self.state.history_paths = []

    if self.args.history_path:
      self.state.history_paths.append(self.args.history_path)
    else:
      self.state.history_paths = self.GuessHistoryPaths(self.args.username)

      if not self.state.history_paths:
        raise flow.FlowError("Could not find valid History paths.")

    filename = "places.sqlite"
    for path in self.state.history_paths:
      self.CallFlow(
          file_finder.FileFinder.__name__,
          paths=[os.path.join(path, "**2", filename)],
          pathtype=self.args.pathtype,
          action=rdf_file_finder.FileFinderAction.Download(),
          next_state="ParseFiles")

  def ParseFiles(self, responses):
    """Take each file we retrieved and get the history from it."""
    if responses:
      for response in responses:
        if data_store.RelationalDBReadEnabled("filestore"):
          client_path = db.ClientPath.FromPathSpec(self.client_id,
                                                   response.stat_entry.pathspec)
          fd = file_store.OpenFile(client_path)
        else:
          fd = aff4.FACTORY.Open(
              response.stat_entry.AFF4Path(self.client_urn), token=self.token)
        hist = firefox3_history.Firefox3History(fd)
        count = 0
        for epoch64, dtype, url, dat1, in hist.Parse():
          count += 1
          str_entry = "%s %s %s %s" % (datetime.datetime.utcfromtimestamp(
              epoch64 / 1e6), url, dat1, dtype)
          self.SendReply(rdfvalue.RDFString(utils.SmartStr(str_entry)))
        self.Log("Wrote %d Firefox History entries for user %s from %s", count,
                 self.args.username, response.stat_entry.pathspec.Basename())
        self.state.hist_count += count

  def GuessHistoryPaths(self, username):
    """Take a user and return guessed full paths to History files.

    Args:
      username: Username as string.

    Returns:
      A list of strings containing paths to look for history files in.

    Raises:
      OSError: On invalid system in the Schema
    """
    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      system = client.knowledge_base.os
      user_info = flow_utils.GetUserInfo(client.knowledge_base, username)
    else:
      fd = aff4.FACTORY.Open(self.client_id, token=self.token)
      system = fd.Get(fd.Schema.SYSTEM)
      kb = fd.Get(fd.Schema.KNOWLEDGE_BASE)
      user_info = flow_utils.GetUserInfo(kb, username)

    if not user_info:
      self.Error("Could not find homedir for user {0}".format(username))
      return

    paths = []
    if system == "Windows":
      path = "{app_data}\\Mozilla\\Firefox\\Profiles/"
      paths.append(path.format(app_data=user_info.appdata))
    elif system == "Linux":
      path = "{homedir}/.mozilla/firefox/"
      paths.append(path.format(homedir=user_info.homedir))
    elif system == "Darwin":
      path = ("{homedir}/Library/Application Support/" "Firefox/Profiles/")
      paths.append(path.format(homedir=user_info.homedir))
    else:
      raise OSError("Invalid OS for Chrome History")
    return paths


BROWSER_PATHS = {
    "Linux": {
        "Firefox": ["/home/{username}/.mozilla/firefox/"],
        "Chrome": [
            "{homedir}/.config/google-chrome/", "{homedir}/.config/chromium/"
        ]
    },
    "Windows": {
        "Chrome": [
            "{local_app_data}\\Google\\Chrome\\User Data\\",
            "{local_app_data}\\Chromium\\User Data\\"
        ],
        "Firefox": ["{local_app_data}\\Mozilla\\Firefox\\Profiles\\"],
        "IE": [
            "{cache}\\", "{cache}\\Low\\", "{app_data}\\Microsoft\\Windows\\"
        ]
    },
    "Darwin": {
        "Firefox": ["{homedir}/Library/Application Support/Firefox/Profiles/"],
        "Chrome": [
            "{homedir}/Library/Application Support/Google/Chrome/",
            "{homedir}/Library/Application Support/Chromium/"
        ]
    }
}


class CacheGrepArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CacheGrepArgs
  rdf_deps = [
      rdf_standard.RegularExpression,
  ]


@flow_base.DualDBFlow
class CacheGrepMixin(object):
  """Grep the browser profile directories for a regex.

  This will check Chrome, Firefox and Internet Explorer profile directories.
  Note that for each directory we get a maximum of 50 hits returned.
  """

  category = "/Browser/"
  args_type = CacheGrepArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    """Redirect to start on the workers and not in the UI."""

    # Figure out which paths we are going to check.
    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
      kb = client.knowledge_base
      system = kb.os
    else:
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      system = client.Get(client.Schema.SYSTEM)
      kb = client.Get(client.Schema.KNOWLEDGE_BASE)

    paths = BROWSER_PATHS.get(system)
    self.state.all_paths = []
    if self.args.check_chrome:
      self.state.all_paths += paths.get("Chrome", [])
    if self.args.check_ie:
      self.state.all_paths += paths.get("IE", [])
    if self.args.check_firefox:
      self.state.all_paths += paths.get("Firefox", [])
    if not self.state.all_paths:
      raise flow.FlowError("Unsupported system %s for CacheGrep" % system)

    self.state.users = []
    for user in self.args.grep_users:
      user_info = flow_utils.GetUserInfo(kb, user)
      if not user_info:
        raise flow.FlowError("No such user %s" % user)
      self.state.users.append(user_info)

    usernames = [
        "%s\\%s" % (u.userdomain, u.username) for u in self.state.users
    ]
    usernames = [u.lstrip("\\") for u in usernames]  # Strip \\ if no domain.

    condition = rdf_file_finder.FileFinderCondition(
        condition_type=(
            rdf_file_finder.FileFinderCondition.Type.CONTENTS_REGEX_MATCH),
        contents_regex_match=rdf_file_finder
        .FileFinderContentsRegexMatchCondition(
            regex=self.args.data_regex,
            mode=rdf_file_finder.FileFinderContentsRegexMatchCondition.Mode
            .FIRST_HIT))

    for path in self.state.all_paths:
      full_paths = flow_utils.InterpolatePath(path, kb, users=usernames)
      for full_path in full_paths:
        self.CallFlow(
            file_finder.FileFinder.__name__,
            paths=[os.path.join(full_path, "**5")],
            pathtype=self.args.pathtype,
            conditions=[condition],
            action=rdf_file_finder.FileFinderAction.Download(),
            next_state="HandleResults")

  def HandleResults(self, responses):
    """Take each file we retrieved and add it to the collection."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    for response in responses:
      self.SendReply(response.stat_entry)
