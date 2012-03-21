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

"""Administrative flows for managing the clients state."""

import time

from grr.lib import aff4
from grr.lib import flow
from grr.proto import jobs_pb2


class Uninstall(flow.GRRFlow):
  """Removes the persistence mechanism which the client uses at boot.

  For Windows and OSX, this will disable the service, and then stop the service.
  For Linux this flow will fail as we haven't implemented it yet :)
  """

  category = "/Administrative/"

  def __init__(self, kill=False, **kwargs):
    """Initialize the flow."""
    flow.GRRFlow.__init__(self, **kwargs)
    self.kill = kill

  @flow.StateHandler(next_state=["Kill"])
  def Start(self):
    """Start the flow and determine OS support."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)

    if system == "Darwin" or system == "Windows":
      self.CallClient("Uninstall", next_state="Kill")
    else:
      self.Log("Unsupported platform for Uninstall")

  @flow.StateHandler(None, next_state="Confirmation")
  def Kill(self, responses):
    """Call the kill function on the client."""
    if not responses.success:
      self.Log("Failed to uninstall client.")
    else:
      self.CallClient("Kill", next_state="Confirmation")

  @flow.StateHandler(None, next_state="End")
  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class Kill(flow.GRRFlow):
  """Terminate a running client (does not disable, just kill)."""

  category = "/Administrative/"

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the kill function on the client."""
    self.CallClient("Kill", next_state="Confirmation")

  @flow.StateHandler(None, next_state="End")
  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class UpdateConfig(flow.GRRFlow):
  """Update the configuration of the client.

    Note: This flow is somewhat dangerous, so we don't expose it in the UI.
  """

  # Still accessible (e.g. via ajax but not visible in the UI.)
  category = None

  def __init__(self, grr_config, **kwargs):
    """Initialize.

    Args:
      grr_config: a jobs_pb2.GRRConfig object.
    """
    flow.GRRFlow.__init__(self, **kwargs)
    self.grr_config = grr_config

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the GetConfig function on the client."""
    self.CallClient("UpdateConfig", self.grr_config, next_state="Confirmation")

  @flow.StateHandler(next_state="End")
  def Confirmation(self, responses):
    """Confirmation."""
    if not responses.success:
      raise flow.FlowError("Failed to write config. Err: {0}".format(
          responses.status))


class ExecuteCommand(flow.GRRFlow):
  """Execute a predefined command on the client."""

  category = "/Administrative/"

  def __init__(self, cmd=None, args=None, time_limit=-1, **kwargs):
    """Initialize the flow."""
    flow.GRRFlow.__init__(self, **kwargs)
    self.cmd = cmd
    self.args = args.split(" ")
    self.time_limit = time_limit

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the execute function on the client."""
    self.CallClient("ExecuteCommand", cmd=self.cmd, args=self.args,
                    time_limit=self.time_limit, next_state="Confirmation")

  @flow.StateHandler(None, next_state="End")
  def Confirmation(self, responses):
    """Confirmation."""
    if responses.success:
      response = responses.First()
      self.Log(("Execution of %s %s (return value %d, "
                "ran for %f seconds):"),
               response.request.cmd,
               " ".join(response.request.args),
               response.exit_status,
               # time_used is returned in microseconds.
               response.time_used / 1e6)
      try:
        # We don't want to overflow the log so we just save 100 bytes each.
        logout = response.stdout[:100]
        if len(response.stdout) > 100:
          logout += "..."
        logerr = response.stderr[:100]
        if len(response.stderr) > 100:
          logerr += "..."
        self.Log("Output: %s, %s", logout, logerr)
      except ValueError:
        # The received byte buffer does not convert to unicode.
        self.Log("Received output not convertible to unicode.")
    else:
      self.Log("Execute failed.")


class Foreman(flow.WellKnownFlow):
  """The foreman assigns new flows to clients based on their type.

  Clients periodically call the foreman flow to ask for new flows that might be
  scheduled for them based on their types. This allows the server to schedule
  flows for entire classes of machines based on certain criteria.
  """
  well_known_session_id = "W:Foreman"
  foreman_cache = None

  # How often we refresh the rule set from the data store.
  cache_refresh_time = 600

  def ProcessMessage(self, message):
    """Run the foreman on the client."""
    # Only accept authenticated messages
    if message.auth_state != jobs_pb2.GrrMessage.AUTHENTICATED: return

    now = time.time()

    # Maintain a cache of the foreman
    if (self.foreman_cache is None or
        now > self.foreman_cache.age + self.cache_refresh_time):
      self.foreman_cache = aff4.FACTORY.Open("aff4:/foreman", token=self.token)
      self.foreman_cache.age = now

    if message.source:
      self.foreman_cache.AssignTasksToClient(message.source)
