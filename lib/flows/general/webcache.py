#!/usr/bin/env python
# Copyright 2012 Google Inc.
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

"""Flows to handle web cache."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import flow_utils
from grr.lib import type_info
from grr.proto import jobs_pb2


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
  flow_typeinfo = {"users": type_info.UserListOrNone(),
                   "data_regex": type_info.String(),
                   "pathtype": type_info.ProtoEnum(jobs_pb2.Path, "PathType")}

  def __init__(self, users=None, data_regex="",
               check_chrome=True, check_firefox=True, check_ie=True,
               pathtype=jobs_pb2.Path.TSK,
               output="analysis/cachegrep-{t}",
               **kwargs):
    """Constructor.

    Args:
      users: A list of users to check or None for all users on the system.
      data_regex: The string to grep for.
      check_chrome: Look in the Chrome directories.
      check_firefox: Look in the Firefox directories.
      check_ie: Look in the Internet Explorer directories.
      pathtype: Type of path to use.
      output: A path relative to the client to put the output.

    Raises:
      RuntimeError: On invalid arguments.
    """
    flow.GRRFlow.__init__(self, **kwargs)

    if len(data_regex) < 5:
      raise RuntimeError("Please specify a valid data regex.")

    self.tmp_users = users
    self.data_regex = data_regex

    # Figure out which paths we are going to check.
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)
    paths = BROWSER_PATHS.get(system)
    self.all_paths = []
    if check_chrome:
      self.all_paths += paths.get("Chrome", [])
    if check_ie:
      self.all_paths += paths.get("IE", [])
    if check_firefox:
      self.all_paths += paths.get("Firefox", [])
    if not self.all_paths:
      raise flow.FlowError("Unsupported system %s for CacheGrep" % system)

    self.pathtype = pathtype
    self.output = output.format(t=time.time())
    self.received_count = 0

    self.users = []
    for user in self.tmp_users:
      user_info = flow_utils.GetUserInfo(client, user)
      if not user_info:
        raise flow.FlowError("No such user %s" % self.username)
      self.users.append(user_info)

  @flow.StateHandler(next_state="StartRequests")
  def Start(self):
    """Redirect to start on the workers and not in the UI."""
    self.CallState(next_state="StartRequests")

  @flow.StateHandler(next_state="HandleResults")
  def StartRequests(self):
    """Generate and send the Find requests."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    self.urn = aff4.ROOT_URN.Add(self.client_id)
    self.out_urn = self.urn.Add(self.output)

    # Prepare the output collection.
    self.out_urn = aff4.ROOT_URN.Add(self.client_id).Add(self.output)
    self.fd = aff4.FACTORY.Create(self.out_urn, "AFF4Collection", mode="w",
                                  token=self.token)
    self.fd.Set(self.fd.Schema.DESCRIPTION("CacheGrep for {0}".format(
        self.data_regex)))
    self.collection_list = self.fd.Schema.COLLECTION()

    usernames = ["%s\\%s" % (u.domain, u.username) for u in self.users]
    usernames = [u.lstrip("\\") for u in usernames]  # Strip \\ if no domain.

    for path in self.all_paths:
      full_paths = flow_utils.InterpolatePath(path, client, users=usernames)
      for full_path in full_paths:
        self.CallFlow("FindFiles", pathtype=self.pathtype,
                      data_regex=self.data_regex, path=full_path,
                      iterate_on_number=800, max_results=50,
                      next_state="HandleResults", output=None)

  @flow.StateHandler(jobs_pb2.StatResponse)
  def HandleResults(self, responses):
    """Take each file we retrieved and add it to the collection."""
    # Note that some of these Find requests will fail because some paths don't
    # exist, e.g. Chromium on most machines, so we don't check for success.
    for response in responses:
      self.collection_list.Append(response)
      self.received_count += len(responses)

  @flow.StateHandler()
  def End(self):
    self.fd.Set(self.fd.Schema.COLLECTION, self.collection_list)
    self.fd.Close()
    self.Notify("ViewObject", self.out_urn,
                u"CacheGrep completed. %d hits" % len(self.collection_list))
    self.SendReply(self.out_urn)
