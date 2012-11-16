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

from grr.client import conf as flags
import logging

from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_string("monitoring_email", None,
                    "The email address to send events to.")

FLAGS = flags.FLAGS


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
    stats_fd.AddAttribute(stats_fd.Schema.STATS(response))

    stats_fd.Close()

    self.Notify("ViewObject", urn, "Client Stats")


class GetClientStatsAuto(GetClientStats, flow.WellKnownFlow):
  """This action pushes client stats to the server automatically."""

  category = None

  well_known_session_id = "W:Stats"

  def ProcessMessage(self, message):
    """Processes a stats response from the client."""
    client_stats = jobs_pb2.ClientStats()
    client_stats.ParseFromString(message.args)
    self.client_id = message.source
    self.ProcessResponse(client_stats)


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


class ExecutePythonHack(flow.GRRFlow):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"

  def __init__(self, hack_name=None, **kwargs):
    self.hack_name = hack_name
    super(ExecutePythonHack, self).__init__(**kwargs)

  @flow.StateHandler(next_state=["End"])
  def Start(self):
    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("config").Add(
        "python_hacks").Add(self.hack_name), token=self.token)

    python_blob = fd.Get(fd.Schema.BINARY)
    self.CallClient("ExecutePython", python_code=python_blob.data,
                    next_state="End")

  @flow.StateHandler()
  def End(self, responses):
    response = responses.First()
    if responses.success and response:
      self.SendReply(aff4.RDFBytes(utils.SmartStr(response.return_val)))


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
  cache_refresh_time = 60

  def ProcessMessage(self, message):
    """Run the foreman on the client."""
    # Only accept authenticated messages
    if message.auth_state != jobs_pb2.GrrMessage.AUTHENTICATED: return

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

Client %(client_id)s (%(hostname)s) just came online. Click
<a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

  def __init__(self, email=None, **kwargs):
    """Init.

    Args:
      email: Email address to send to, can be comma separated. If not set, mail
      will be sent to the logged in user.
    """
    self.email = email or kwargs["context"].token.username
    flow.GRRFlow.__init__(self, **kwargs)

  @flow.StateHandler(next_state="SendMail")
  def Start(self):
    """Starts processing."""
    request = jobs_pb2.PrintStr()
    request.data = "Ping"
    self.CallClient("Echo", request,
                    next_state="SendMail")

  @flow.StateHandler()
  def SendMail(self, responses):
    """Sends a mail when the client has responded."""
    if responses.success:
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)

      url = urllib.urlencode((("c", self.client_id),
                              ("main", "HostInformation")))

      subject = "GRR Client on %s became available." % hostname

      email_alerts.SendEmail(self.email, self.token.username,
                             subject,
                             self.template % dict(
                                 client_id=self.client_id,
                                 admin_ui=FLAGS.ui_url,
                                 hostname=hostname,
                                 urn=url),
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

  def __init__(self, blob_path=None, **kw):
    """Init.

    Args:
      blob_path: An aff4 path to a GRRSignedBlob of a new client version.
    """
    super(UpdateClient, self).__init__(**kw)
    self.blob_path = blob_path

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
      req = jobs_pb2.ExecuteBinaryRequest()
      req.executable.MergeFrom(blob.data)
      self.CallClient("UpdateAgent", req, next_state="Interrogate")
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
             info.data.client_version)


class NannyMessageHandler(flow.EventListener):
  """A listener for nanny messages."""
  EVENTS = ["NannyMessage"]

  well_known_session_id = "W:NannyMessage"

  mail_template = """
<html><body><h1>GRR nanny message received.</h1>

The nanny for client %(client_id)s (%(hostname)s) just sent a message:<br>
<br>
%(message)s
<br>
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>The GRR team.

</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    """Processes this event."""
    _ = event

    client_id = message.source

    blob = jobs_pb2.DataBlob()
    blob.ParseFromString(message.args)
    message = blob.string

    logging.info("Nanny for client %s sent: %s", client_id, message)

    # Also send email.
    if FLAGS.monitoring_email:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id),
                              ("main", "HostInformation")))

      email_alerts.SendEmail(FLAGS.monitoring_email, "GRR server",
                             "GRR nanny message received from %s." % client_id,
                             self.mail_template % dict(
                                 client_id=client_id,
                                 admin_ui=FLAGS.ui_url,
                                 hostname=hostname,
                                 urn=url, message=message),
                             is_html=True)


class ClientCrashHandler(flow.EventListener):
  """A listener for client crashes."""
  EVENTS = ["ClientCrash"]

  well_known_session_id = "W:CrashHandler"

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

    flow_pb = flow.FACTORY.FetchFlow(message.session_id, token=self.token,
                                     lock=False)

    # Log.
    logging.info("Client crash reported, client %s.", client_id)

    # Export.
    stats.STATS.Increment("grr_client_crashes")

    # Also send email.
    if FLAGS.monitoring_email:
      nanny_msg = ""
      status = jobs_pb2.GrrStatus()
      status.ParseFromString(message.args)
      if status.nanny_status:
        nanny_msg = "Nanny status: %s" % status.nanny_status

      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id),
                              ("main", "HostInformation")))

      email_alerts.SendEmail(FLAGS.monitoring_email, "GRR server",
                             "Client %s reported a crash." % client_id,
                             self.mail_template % dict(
                                 client_id=client_id,
                                 admin_ui=FLAGS.ui_url,
                                 hostname=hostname,
                                 flow=utils.SmartStr(flow_pb),
                                 urn=url, nanny_msg=nanny_msg),
                             is_html=True)


class AdministrativeInit(registry.InitHook):

  pre = ["StatsInit"]

  def RunOnce(self):
    stats.STATS.RegisterVar("grr_client_crashes")


class KeepAlive(flow.GRRFlow):
  """Requests that the clients stays alive for a period of time."""

  category = "/Administrative/"

  sleep_time = 60

  def __init__(self, stayalive_time=3600, **kwargs):
    """Init.

    Args:
      stayalive_time: How long the client should be kept in the faster poll
                      state.
    """
    self.end_time = time.time() + stayalive_time
    super(KeepAlive, self).__init__(**kwargs)

  @flow.StateHandler(next_state="SendMessage")
  def Start(self):
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
