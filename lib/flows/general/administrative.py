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
import urllib

import logging

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils

config_lib.DEFINE_string("Monitoring.events_email", None,
                         "The email address to send events to.")


class GetClientStats(flow.GRRFlow):
  """This flow retrieves information about the GRR client process."""

  category = "/Administrative/"

  @flow.StateHandler(next_state=["StoreResults"])
  def Start(self):
    self.CallClient("GetClientStats", next_state="StoreResults")

  @flow.StateHandler()
  def StoreResults(self, responses):
    """Stores the responses."""

    if not responses.success:
      self.Error("Failed to retrieve client stats.")
      return

    for response in responses:
      self.ProcessResponse(response)

  def ProcessResponse(self, response):
    """Actually processes the contents of the response."""
    urn = aff4.ROOT_URN.Add(self.client_id).Add("stats")
    stats_fd = aff4.FACTORY.Create(urn, "ClientStats", token=self.token,
                                   mode="rw")

    # Only keep the average of all values that fall within one minute.
    response.DownSample()
    stats_fd.AddAttribute(stats_fd.Schema.STATS(response))

    stats_fd.Close()

    self.Notify("ViewObject", urn, "Client Stats")


class GetClientStatsAuto(GetClientStats, flow.WellKnownFlow):
  """This action pushes client stats to the server automatically."""

  category = None

  well_known_session_id = "aff4:/flows/W:Stats"

  def ProcessMessage(self, message):
    """Processes a stats response from the client."""
    client_stats = rdfvalue.ClientStats(message.args)
    self.client_id = message.source
    self.ProcessResponse(client_stats)


class Uninstall(flow.GRRFlow):
  """Removes the persistence mechanism which the client uses at boot.

  For Windows and OSX, this will disable the service, and then stop the service.
  For Linux this flow will fail as we haven't implemented it yet :)
  """

  category = "/Administrative/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Bool(
          name="kill",
          description="Kills the client if set."),
      )

  @flow.StateHandler(next_state=["Kill"])
  def Start(self):
    """Start the flow and determine OS support."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    system = client.Get(client.Schema.SYSTEM)

    if system == "Darwin" or system == "Windows":
      self.CallClient("Uninstall", next_state="Kill")
    else:
      self.Log("Unsupported platform for Uninstall")

  @flow.StateHandler(next_state="Confirmation")
  def Kill(self, responses):
    """Call the kill function on the client."""
    if not responses.success:
      self.Log("Failed to uninstall client.")
    else:
      self.CallClient("Kill", next_state="Confirmation")

  @flow.StateHandler(next_state="End")
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

  @flow.StateHandler(next_state="End")
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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFValueType(
          name="config",
          rdfclass=rdfvalue.GRRConfig,
          description="The config to send to the client."),
      )

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


class ExecutePythonHack(flow.GRRFlow):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="hack_name",
          description="The name of the hack to execute."),
      type_info.GenericProtoDictType(
          description="Python Hack Arguments.",
          name="py_args")
      )

  @flow.StateHandler(next_state=["End"])
  def Start(self):
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("config").Add(
        "python_hacks").Add(self.hack_name), token=self.token)

    python_blob = fd.Get(fd.Schema.BINARY)
    if python_blob is None:
      raise RuntimeError("Python hack %s not found." % self.hack_name)
    self.CallClient("ExecutePython", python_code=python_blob,
                    py_args=self.py_args, next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    response = responses.First()
    if responses.success and response:
      result = utils.SmartStr(response.return_val)
      # Send reply with full data, but only log the first 200 bytes.
      str_result = result[0:200]
      if len(result) >= 200:
        str_result += "...[truncated]"
      self.Log("Result: %s" % str_result)
      self.SendReply(rdfvalue.RDFBytes(utils.SmartStr(response.return_val)))


class ExecuteCommand(flow.GRRFlow):
  """Execute a predefined command on the client."""

  category = "/Administrative/"

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="cmd",
          description="The command to execute."),
      type_info.String(
          name="args",
          description="The arguments to the command, space separated."),
      type_info.Integer(
          name="time_limit",
          description="The time limit for this execution, -1 means unlimited.",
          default=-1),
      )

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the execute function on the client."""
    self.CallClient("ExecuteCommand", cmd=self.cmd, args=self.args.split(" "),
                    time_limit=self.time_limit, next_state="Confirmation")

  @flow.StateHandler(next_state="End")
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
  well_known_session_id = "aff4:/flows/W:Foreman"
  foreman_cache = None

  # How often we refresh the rule set from the data store.
  cache_refresh_time = 60

  def ProcessMessage(self, message):
    """Run the foreman on the client."""
    # Only accept authenticated messages
    if message.auth_state != rdfvalue.GRRMessage.Enum("AUTHENTICATED"): return

    now = time.time()

    # Maintain a cache of the foreman
    if (self.foreman_cache is None or
        now > self.foreman_cache.age + self.cache_refresh_time):
      self.foreman_cache = aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                                             token=self.token)
      self.foreman_cache.age = now

    if message.source:
      self.foreman_cache.AssignTasksToClient(message.source)


class OnlineNotification(flow.GRRFlow):
  """Notifies by email when a client comes online in GRR."""

  category = "/Administrative/"

  template = """
<html><body><h1>GRR Client Online Notification.</h1>

<p>
  Client %(client_id)s (%(hostname)s) just came online. Click
  <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.
  <br />This notification was created by %(creator)s.
</p>

<p>Thanks,</p>
<p>The GRR team.</p>
</body></html>"""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="email",
          description=("Email address to send to, can be comma separated. If "
                       "not set, mail will be sent to the logged in user.")),
      )

  @flow.StateHandler(next_state="SendMail")
  def Start(self):
    """Starts processing."""
    self.email = self.email or self.token.username
    self.CallClient("Echo", data="Ping", next_state="SendMail")

  @flow.StateHandler()
  def SendMail(self, responses):
    """Sends a mail when the client has responded."""
    if responses.success:
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)

      url = urllib.urlencode((("c", self.client_id),
                              ("main", "HostInformation")))

      subject = "GRR Client on %s became available." % hostname

      email_alerts.SendEmail(
          self.email, "grr-noreply",
          subject,
          self.template % dict(
              client_id=self.client_id,
              admin_ui=config_lib.CONFIG["ServerFlags.ui_url"],
              hostname=hostname,
              urn=url,
              creator=self.token.username),
          is_html=True)
    else:
      flow.FlowError("Error while pinging client.")


class UpdateClient(flow.GRRFlow):
  """Updates the GRR client to a new version replacing the current client.

  This will execute the specified installer on the client and then run
  an Interrogate flow.

  The new installer needs to be loaded into the database, generally in
  /config/executables/<platform>/installers and must be signed using the
  exec signing key.

  Signing and upload of the file is done with config_updater.
  """

  category = "/Administrative/"

  AUTHORIZED_LABELS = ["admin"]

  system_platform_mapping = {
      "Darwin": "osx",
      "Linux": "linux",
      "Windows": "windows"}

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="blob_path",
          description=("An aff4 path to a GRRSignedBlob of a new client "
                       "version.")),
      )

  @flow.StateHandler(next_state="Interrogate")
  def Start(self):
    """Start."""
    if not self.blob_path:
      client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(
          self.client_id), token=self.token)
      client_platform = client.Get(client.Schema.SYSTEM)
      if not client_platform:
        raise RuntimeError("Can't determine client platform, please specify.")
      blob_urn = "aff4:/config/executables/%s/agentupdates" % (
          self.system_platform_mapping[client_platform])
      blob_dir = aff4.FACTORY.Open(blob_urn, token=self.token)
      updates = sorted(list(blob_dir.OpenChildren()))
      if not updates:
        raise RuntimeError(
            "No matching updates found, please specify one manually.")
      aff4_blob = updates[-1]
      self.blob_path = aff4_blob.urn
    else:
      aff4_blob = aff4.FACTORY.Open(self.blob_path, token=self.token)

    blob = aff4_blob.Get(aff4_blob.Schema.BINARY)

    if ("windows" in utils.SmartStr(self.blob_path) or
        "osx" in utils.SmartStr(self.blob_path)):
      self.CallClient("UpdateAgent", executable=blob, next_state="Interrogate")

    else:
      raise RuntimeError("Update not supported for this urn, use aff4:/config"
                         "/executables/<platform>/agentupdates/<version>")

  @flow.StateHandler(next_state="Done")
  def Interrogate(self, responses):
    _ = responses
    self.Log("Installer completed.")
    self.CallFlow("Interrogate", next_state="Done")

  @flow.StateHandler()
  def Done(self):
    client = aff4.FACTORY.Open(aff4.ROOT_URN.Add(
        self.client_id), token=self.token)
    info = client.Get(client.Schema.CLIENT_INFO)
    self.Log("Client update completed, new version: %s" %
             info.client_version)


class NannyMessageHandler(flow.EventListener):
  """A listener for nanny messages."""
  EVENTS = ["NannyMessage"]

  well_known_session_id = "aff4:/flows/W:NannyMessage"

  mail_template = """
<html><body><h1>GRR nanny message received.</h1>

The nanny for client %(client_id)s (%(hostname)s) just sent a message:<br>
<br>
%(message)s
<br>
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>The GRR team.

</body></html>"""

  subject = "GRR nanny message received from %s."

  logline = "Nanny for client %s sent: %s"

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    """Processes this event."""
    _ = event

    client_id = message.source

    message = rdfvalue.DataBlob(message.args).string

    logging.info(self.logline, client_id, message)

    # Also send email.
    if config_lib.CONFIG["Monitoring.alert_email"]:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id),
                              ("main", "HostInformation")))

      email_alerts.SendEmail(
          config_lib.CONFIG["Monitoring.alert_email"],
          "GRR server",
          self.subject % client_id,
          self.mail_template % dict(
              client_id=client_id,
              admin_ui=config_lib.CONFIG["AdminUI.url"],
              hostname=hostname,
              urn=url, message=message),
          is_html=True)


class ClientAlertHandler(NannyMessageHandler):
  """A listener for client messages."""
  EVENTS = ["ClientAlert"]

  well_known_session_id = "aff4:/flows/W:ClientAlert"

  mail_template = """
<html><body><h1>GRR client message received.</h1>

The client %(client_id)s (%(hostname)s) just sent a message:<br>
<br>
%(message)s
<br>
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>The GRR team.

</body></html>"""

  subject = "GRR client message received from %s."

  logline = "Client message from %s: %s"


class ClientCrashHandler(flow.EventListener):
  """A listener for client crashes."""
  EVENTS = ["ClientCrash"]

  well_known_session_id = "aff4:/flows/W:CrashHandler"

  mail_template = """
<html><body><h1>GRR client crash report.</h1>

Client %(client_id)s (%(hostname)s) just crashed while executing an action.
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>Thanks,</p>
<p>The GRR team.
<p>
P.S. The failing flow was:
%(flow)s

%(nanny_msg)s

</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    """Processes this event."""
    _ = event
    client_id = message.source
    nanny_msg = ""

    rdf_flow = flow.FACTORY.FetchFlow(message.session_id, token=self.token,
                                      lock=False)

    # Log.
    logging.info("Client crash reported, client %s.", client_id)

    # Export.
    stats.STATS.Increment("grr_client_crashes")

    # Also send email.
    if config_lib.CONFIG["Monitoring.alert_email"]:
      status = rdfvalue.GrrStatus(message.args)
      if status.nanny_status:
        nanny_msg = "Nanny status: %s" % status.nanny_status

      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id),
                              ("main", "HostInformation")))

      email_alerts.SendEmail(
          config_lib.CONFIG["Monitoring.alert_email"],
          "GRR server",
          "Client %s reported a crash." % client_id,
          self.mail_template % dict(
              client_id=client_id,
              admin_ui=config_lib.CONFIG["AdminUI.url"],
              hostname=hostname,
              flow=utils.SmartStr(rdf_flow),
              urn=url, nanny_msg=nanny_msg),
          is_html=True)

    if nanny_msg:
      msg = "Client crashed, " + nanny_msg
    else:
      msg = "Client crashed."
    # Now terminate the flow.
    flow.FACTORY.TerminateFlow(message.session_id, reason=msg,
                               token=self.token, force=True)


class ClientStartupHandler(flow.EventListener):
  EVENTS = ["ClientStartup"]

  well_known_session_id = "aff4:/flows/W:Startup"

  @flow.EventHandler(allow_client_access=True, auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    """Handle a startup event."""
    _ = event

    # We accept unauthenticated messages so there are no errors but we don't
    # store the results.
    if message.auth_state != rdfvalue.GRRMessage.Enum("AUTHENTICATED"):
      return

    client_id = message.source

    client = aff4.FACTORY.Create(aff4.ROOT_URN.Add(client_id),
                                 "VFSGRRClient", mode="rw", token=self.token)
    old_info = client.Get(client.Schema.CLIENT_INFO)
    old_boot = client.Get(client.Schema.LAST_BOOT_TIME, 0)
    startup_info = rdfvalue.StartupInfo(message.args)
    info = startup_info.client_info

    if old_info:
      # Only write to the datastore if we have new information.
      new_data = (info.client_name, info.client_version, info.revision,
                  startup_info.boot_time)
      old_data = (old_info.client_name, old_info.client_version,
                  old_info.revision, old_boot)

      if new_data == old_data:
        # Information has not changed, we save the write.
        return

    client.Set(client.Schema.CLIENT_INFO(info))
    client.Set(client.Schema.LAST_BOOT_TIME(startup_info.boot_time))
    client.Close()


class AdministrativeInit(registry.InitHook):

  pre = ["StatsInit"]

  def RunOnce(self):
    stats.STATS.RegisterVar("grr_client_crashes")


class KeepAlive(flow.GRRFlow):
  """Requests that the clients stays alive for a period of time."""

  category = "/Administrative/"

  sleep_time = 60

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.Integer(
          name="stayalive_time",
          default=3600,
          description=("How long the client should be kept in the faster poll "
                       "state, counting from now."))
      )

  @flow.StateHandler(next_state="SendMessage")
  def Start(self):
    self.end_time = time.time() + self.stayalive_time
    self.CallState(next_state="SendMessage")

  @flow.StateHandler(next_state="Sleep")
  def SendMessage(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)

    self.CallClient("Echo", data="Wake up!", next_state="Sleep")

  @flow.StateHandler(next_state="SendMessage")
  def Sleep(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)

    if time.time() < self.end_time - self.sleep_time:
      self.CallState(next_state="SendMessage", delay=self.sleep_time)
