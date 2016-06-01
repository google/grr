#!/usr/bin/env python
"""Administrative flows for managing the clients state."""


import shlex
import threading
import time
import urllib

import logging

# pylint: disable=unused-import
from grr.gui import django_lib
# pylint: enable=unused-import
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import rendering
from grr.lib import stats
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import reports
from grr.lib.aff4_objects import stats as aff4_stats
from grr.lib.hunts import implementation
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import flows_pb2


class AdministrativeInit(registry.InitHook):
  """Initialize the Django environment."""

  def RunOnce(self):
    stats.STATS.RegisterCounterMetric("grr_client_crashes")


class ClientCrashEventListener(flow.EventListener):
  """EventListener with additional helper methods to save crash details."""

  def _AppendCrashDetails(self, path, crash_details):
    collection = aff4.FACTORY.Create(path,
                                     collects.PackedVersionedCollection,
                                     mode="rw",
                                     token=self.token)

    collection.Add(crash_details)
    collection.Close(sync=False)

  def _ExtractHuntId(self, flow_session_id):
    hunt_str, hunt_id, _ = flow_session_id.Split(3)
    if hunt_str == "hunts":
      return aff4.ROOT_URN.Add("hunts").Add(hunt_id)

  def WriteAllCrashDetails(self,
                           client_id,
                           crash_details,
                           flow_session_id=None,
                           hunt_session_id=None):
    # Update last crash attribute of the client.
    client_obj = aff4.FACTORY.Create(client_id,
                                     aff4_grr.VFSGRRClient,
                                     token=self.token)
    client_obj.Set(client_obj.Schema.LAST_CRASH(crash_details))
    client_obj.Close(sync=False)

    # Duplicate the crash information in a number of places so we can find it
    # easily.
    self._AppendCrashDetails(client_id.Add("crashes"), crash_details)
    self._AppendCrashDetails(aff4.ROOT_URN.Add("crashes"), crash_details)

    if flow_session_id:
      aff4_flow = aff4.FACTORY.Open(flow_session_id,
                                    flow.GRRFlow,
                                    mode="rw",
                                    age=aff4.NEWEST_TIME,
                                    token=self.token)

      aff4_flow.Set(aff4_flow.Schema.CLIENT_CRASH(crash_details))
      aff4_flow.Close(sync=False)

      hunt_session_id = self._ExtractHuntId(flow_session_id)
      if hunt_session_id and hunt_session_id != flow_session_id:
        self._AppendCrashDetails(hunt_session_id.Add("crashes"), crash_details)


class GetClientStatsProcessResponseMixin(object):
  """Mixin defining ProcessReponse() that writes client stats to datastore."""

  def ProcessResponse(self, client_id, response):
    """Actually processes the contents of the response."""
    urn = client_id.Add("stats")

    with aff4.FACTORY.Create(urn,
                             aff4_stats.ClientStats,
                             token=self.token,
                             mode="w") as stats_fd:
      # Only keep the average of all values that fall within one minute.
      stats_fd.AddAttribute(stats_fd.Schema.STATS, response.DownSample())


class GetClientStats(flow.GRRFlow, GetClientStatsProcessResponseMixin):
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
      self.ProcessResponse(self.client_id, response)


class GetClientStatsAuto(flow.WellKnownFlow,
                         GetClientStatsProcessResponseMixin):
  """This action pushes client stats to the server automatically."""

  category = None

  well_known_session_id = rdfvalue.SessionID(flow_name="Stats",
                                             queue=queues.STATS)

  def ProcessMessage(self, message):
    """Processes a stats response from the client."""
    client_stats = rdf_client.ClientStats(message.payload)
    self.ProcessResponse(message.source, client_stats)


class DeleteGRRTempFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DeleteGRRTempFilesArgs


class DeleteGRRTempFiles(flow.GRRFlow):
  """Delete all the GRR temp files in path.

  If path is a directory, look in the top level for filenames beginning with
  Client.tempfile_prefix, and delete them.

  If path is a regular file and starts with Client.tempfile_prefix, delete it.
  """

  category = "/Administrative/"
  args_type = DeleteGRRTempFilesArgs

  @flow.StateHandler(next_state="Done")
  def Start(self):
    """Issue a request to delete tempfiles in directory."""
    self.CallClient("DeleteGRRTempFiles", self.args.pathspec, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    for response in responses:
      self.Log(response.data)


class UninstallArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UninstallArgs


class Uninstall(flow.GRRFlow):
  """Removes the persistence mechanism which the client uses at boot.

  For Windows and OSX, this will disable the service, and then stop the service.
  For Linux this flow will fail as we haven't implemented it yet :)
  """

  category = "/Administrative/"
  args_type = UninstallArgs

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
    elif self.args.kill:
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


class UpdateConfigurationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateConfigurationArgs


class UpdateConfiguration(flow.GRRFlow):
  """Update the configuration of the client.

    Note: This flow is somewhat dangerous, so we don't expose it in the UI.
  """

  # Still accessible (e.g. via ajax but not visible in the UI.)
  category = None
  args_type = UpdateConfigurationArgs

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the UpdateConfiguration function on the client."""
    self.CallClient("UpdateConfiguration",
                    request=self.args.config,
                    next_state="Confirmation")

  @flow.StateHandler(next_state="End")
  def Confirmation(self, responses):
    """Confirmation."""
    if not responses.success:
      raise flow.FlowError("Failed to write config. Err: {0}".format(
          responses.status))


class ExecutePythonHackArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecutePythonHackArgs


class ExecutePythonHack(flow.GRRFlow):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"
  args_type = ExecutePythonHackArgs

  @flow.StateHandler(next_state=["Done"])
  def Start(self):
    python_hack_root_urn = config_lib.CONFIG.Get("Config.python_hack_root")
    fd = aff4.FACTORY.Open(
        python_hack_root_urn.Add(self.args.hack_name),
        token=self.token)

    if not isinstance(fd, collects.GRRSignedBlob):
      raise RuntimeError("Python hack %s not found." % self.args.hack_name)

    # TODO(user): This will break if someone wants to execute lots of Python.
    for python_blob in fd:
      self.CallClient("ExecutePython",
                      python_code=python_blob,
                      py_args=self.args.py_args,
                      next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    response = responses.First()
    if not responses.success:
      raise flow.FlowError("Execute Python hack failed: %s" % responses.status)
    if response:
      result = utils.SmartStr(response.return_val)
      # Send reply with full data, but only log the first 200 bytes.
      str_result = result[0:200]
      if len(result) >= 200:
        str_result += "...[truncated]"
      self.Log("Result: %s" % str_result)
      self.SendReply(rdfvalue.RDFBytes(utils.SmartStr(response.return_val)))


class ExecuteCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecuteCommandArgs


class ExecuteCommand(flow.GRRFlow):
  """Execute a predefined command on the client."""

  args_type = ExecuteCommandArgs

  @flow.StateHandler(next_state=["Confirmation"])
  def Start(self):
    """Call the execute function on the client."""
    self.CallClient("ExecuteCommand",
                    cmd=self.args.cmd,
                    args=shlex.split(self.args.command_line),
                    time_limit=self.args.time_limit,
                    next_state="Confirmation")

  @flow.StateHandler(next_state="End")
  def Confirmation(self, responses):
    """Confirmation."""
    if responses.success:
      response = responses.First()
      self.Log(("Execution of %s %s (return value %d, "
                "ran for %f seconds):"),
               response.request.cmd,
               " ".join(response.request.command_line),
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
  well_known_session_id = rdfvalue.SessionID(flow_name="Foreman")
  foreman_cache = None

  # How often we refresh the rule set from the data store.
  cache_refresh_time = 60

  lock = threading.Lock()

  def ProcessMessage(self, message):
    """Run the foreman on the client."""
    # Only accept authenticated messages
    if (message.auth_state !=
        rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
      return

    now = time.time()

    # Maintain a cache of the foreman
    with self.lock:
      if (self.foreman_cache is None or
          now > self.foreman_cache.age + self.cache_refresh_time):
        self.foreman_cache = aff4.FACTORY.Open("aff4:/foreman",
                                               mode="rw",
                                               token=self.token)
        self.foreman_cache.age = now

    if message.source:
      self.foreman_cache.AssignTasksToClient(message.source)


class OnlineNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.OnlineNotificationArgs


class OnlineNotification(flow.GRRFlow):
  """Notifies by email when a client comes online in GRR."""

  category = "/Administrative/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  template = """
<html><body><h1>GRR Client Online Notification.</h1>

<p>
  Client %(client_id)s (%(hostname)s) just came online. Click
  <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.
  <br />This notification was created by %(creator)s.
</p>

<p>Thanks,</p>
<p>%(signature)s</p>
</body></html>"""

  args_type = OnlineNotificationArgs

  @classmethod
  def GetDefaultArgs(cls, token=None):
    return cls.args_type(email="%s@%s" %
                         (token.username,
                          config_lib.CONFIG.Get("Logging.domain")))

  @flow.StateHandler(next_state="SendMail")
  def Start(self):
    """Starts processing."""
    if self.args.email is None:
      self.args.email = self.token.username
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

      email_alerts.EMAIL_ALERTER.SendEmail(
          self.args.email,
          "grr-noreply",
          subject,
          self.template % dict(client_id=self.client_id,
                               admin_ui=config_lib.CONFIG["AdminUI.url"],
                               hostname=hostname,
                               urn=url,
                               creator=self.token.username,
                               signature=config_lib.CONFIG["Email.signature"]),
          is_html=True)
    else:
      flow.FlowError("Error while pinging client.")


class UpdateClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateClientArgs


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
      "Darwin": "darwin",
      "Linux": "linux",
      "Windows": "windows"
  }

  args_type = UpdateClientArgs

  @flow.StateHandler(next_state="Interrogate")
  def Start(self):
    """Start."""
    blob_path = self.args.blob_path
    if not blob_path:
      # No explicit path was given, we guess a reasonable default here.
      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      client_platform = client.Get(client.Schema.SYSTEM)
      if not client_platform:
        raise RuntimeError("Can't determine client platform, please specify.")
      blob_urn = "aff4:/config/executables/%s/agentupdates" % (
          self.system_platform_mapping[client_platform])
      blob_dir = aff4.FACTORY.Open(blob_urn, token=self.token)
      updates = sorted(list(blob_dir.ListChildren()))
      if not updates:
        raise RuntimeError(
            "No matching updates found, please specify one manually.")
      blob_path = updates[-1]

    if not ("windows" in utils.SmartStr(self.args.blob_path) or
            "darwin" in utils.SmartStr(self.args.blob_path) or
            "linux" in utils.SmartStr(self.args.blob_path)):
      raise RuntimeError("Update not supported for this urn, use aff4:/config"
                         "/executables/<platform>/agentupdates/<version>")

    aff4_blobs = aff4.FACTORY.Open(blob_path, token=self.token)
    if not isinstance(aff4_blobs, collects.GRRSignedBlob):
      raise RuntimeError("%s is not a valid GRRSignedBlob." % blob_path)

    offset = 0
    write_path = "%d_%s" % (time.time(), aff4_blobs.urn.Basename())
    for i, blob in enumerate(aff4_blobs):
      self.CallClient("UpdateAgent",
                      executable=blob,
                      more_data=i < aff4_blobs.chunks - 1,
                      offset=offset,
                      write_path=write_path,
                      next_state="Interrogate",
                      use_client_env=False)

      offset += len(blob.data)

  @flow.StateHandler(next_state="Done")
  def Interrogate(self, responses):
    if not responses.success:
      self.Log("Installer reported an error: %s" % responses.status)
    else:
      self.Log("Installer completed.")
      self.CallFlow("Interrogate", next_state="Done")

  @flow.StateHandler()
  def Done(self):
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    info = client.Get(client.Schema.CLIENT_INFO)
    self.Log("Client update completed, new version: %s" % info.client_version)


class NannyMessageHandler(ClientCrashEventListener):
  """A listener for nanny messages."""
  EVENTS = ["NannyMessage"]

  well_known_session_id = rdfvalue.SessionID(flow_name="NannyMessage")

  mail_template = """
<html><body><h1>GRR nanny message received.</h1>

The nanny for client %(client_id)s (%(hostname)s) just sent a message:<br>
<br>
%(message)s
<br>
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>%(signature)s</p>

</body></html>"""

  subject = "GRR nanny message received from %s."

  logline = "Nanny for client %s sent: %s"

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    """Processes this event."""
    _ = event

    client_id = message.source

    message = message.payload.string

    logging.info(self.logline, client_id, message)

    # Write crash data to AFF4.
    client = aff4.FACTORY.Open(client_id, token=self.token)
    client_info = client.Get(client.Schema.CLIENT_INFO)

    crash_details = rdf_client.ClientCrash(
        client_id=client_id,
        client_info=client_info,
        crash_message=message,
        timestamp=long(time.time() * 1e6),
        crash_type=self.well_known_session_id)

    self.WriteAllCrashDetails(client_id, crash_details)

    # Also send email.
    if config_lib.CONFIG["Monitoring.alert_email"]:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id), ("main", "HostInformation")))

      email_alerts.EMAIL_ALERTER.SendEmail(
          config_lib.CONFIG["Monitoring.alert_email"],
          "GRR server",
          self.subject % client_id,
          self.mail_template %
          dict(client_id=client_id,
               admin_ui=config_lib.CONFIG["AdminUI.url"],
               hostname=hostname,
               signature=config_lib.CONFIG["Email.signature"],
               urn=url,
               message=message),
          is_html=True)


class ClientAlertHandler(NannyMessageHandler):
  """A listener for client messages."""
  EVENTS = ["ClientAlert"]

  well_known_session_id = rdfvalue.SessionID(flow_name="ClientAlert")

  mail_template = """
<html><body><h1>GRR client message received.</h1>

The client %(client_id)s (%(hostname)s) just sent a message:<br>
<br>
%(message)s
<br>
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>%(signature)s</p>

</body></html>"""

  subject = "GRR client message received from %s."

  logline = "Client message from %s: %s"


class ClientCrashHandler(ClientCrashEventListener):
  """A listener for client crashes."""
  EVENTS = ["ClientCrash"]

  well_known_session_id = rdfvalue.SessionID(flow_name="CrashHandler")

  mail_template = """
<html><body><h1>GRR client crash report.</h1>

Client %(client_id)s (%(hostname)s) just crashed while executing an action.
Click <a href='%(admin_ui)s/#%(urn)s'> here </a> to access this machine.

<p>Thanks,</p>
<p>%(signature)s</p>
<p>
P.S. The state of the failing flow was:
%(state)s

%(nanny_msg)s

</body></html>"""

  @flow.EventHandler(allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    """Processes this event."""
    _ = event
    client_id = message.source
    nanny_msg = ""

    flow_obj = aff4.FACTORY.Open(message.session_id, token=self.token)

    # Log.
    logging.info("Client crash reported, client %s.", client_id)

    # Only kill the flow it is does not handle its own crashes. Some flows
    # restart the client and therefore expect to get a crash notification.
    if flow_obj.handles_crashes:
      return

    # Export.
    stats.STATS.IncrementCounter("grr_client_crashes")

    # Write crash data to AFF4.
    client = aff4.FACTORY.Open(client_id, token=self.token)
    client_info = client.Get(client.Schema.CLIENT_INFO)

    status = rdf_flows.GrrStatus(message.payload)
    crash_details = rdf_client.ClientCrash(
        client_id=client_id,
        session_id=message.session_id,
        client_info=client_info,
        crash_message=status.error_message,
        timestamp=rdfvalue.RDFDatetime().Now(),
        crash_type=self.well_known_session_id)

    self.WriteAllCrashDetails(client_id,
                              crash_details,
                              flow_session_id=message.session_id)

    # Also send email.
    to_send = []

    try:
      hunt_session_id = self._ExtractHuntId(message.session_id)
      if hunt_session_id and hunt_session_id != message.session_id:
        hunt_obj = aff4.FACTORY.Open(hunt_session_id,
                                     aff4_type=implementation.GRRHunt,
                                     token=self.token)
        email = hunt_obj.GetRunner().args.crash_alert_email
        if email:
          to_send.append(email)
    except aff4.InstantiationError:
      logging.error("Failed to open hunt %s.", hunt_session_id)

    email = config_lib.CONFIG["Monitoring.alert_email"]
    if email:
      to_send.append(email)

    for email_address in to_send:
      if status.nanny_status:
        nanny_msg = "Nanny status: %s" % status.nanny_status

      client = aff4.FACTORY.Open(client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)
      url = urllib.urlencode((("c", client_id), ("main", "HostInformation")))

      renderer = rendering.FindRendererForObject(flow_obj.state)

      email_alerts.EMAIL_ALERTER.SendEmail(
          email_address,
          "GRR server",
          "Client %s reported a crash." % client_id,
          self.mail_template %
          dict(client_id=client_id,
               admin_ui=config_lib.CONFIG["AdminUI.url"],
               hostname=hostname,
               state=renderer.RawHTML(),
               urn=url,
               nanny_msg=nanny_msg,
               signature=config_lib.CONFIG["Email.signature"]),
          is_html=True)

    if nanny_msg:
      msg = "Client crashed, " + nanny_msg
    else:
      msg = "Client crashed."

    # Now terminate the flow.
    flow.GRRFlow.TerminateFlow(message.session_id,
                               reason=msg,
                               token=self.token,
                               force=True)


class ClientStartupHandler(flow.EventListener):

  well_known_session_id = rdfvalue.SessionID(flow_name="Startup")

  @flow.EventHandler(allow_client_access=True, auth_required=False)
  def ProcessMessage(self, message=None, event=None):
    """Handle a startup event."""
    _ = event
    # We accept unauthenticated messages so there are no errors but we don't
    # store the results.
    if (message.auth_state !=
        rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
      return

    client_id = message.source

    client = aff4.FACTORY.Create(client_id,
                                 aff4_grr.VFSGRRClient,
                                 mode="rw",
                                 token=self.token)
    old_info = client.Get(client.Schema.CLIENT_INFO)
    old_boot = client.Get(client.Schema.LAST_BOOT_TIME, 0)
    startup_info = rdf_client.StartupInfo(message.payload)
    info = startup_info.client_info

    # Only write to the datastore if we have new information.
    new_data = (info.client_name, info.client_version, info.revision,
                info.build_time, info.client_description)
    old_data = (old_info.client_name, old_info.client_version,
                old_info.revision, old_info.build_time,
                old_info.client_description)

    if new_data != old_data:
      client.Set(client.Schema.CLIENT_INFO(info))

    client.AddLabels(*info.labels, owner="GRR")

    # Allow for some drift in the boot times (5 minutes).
    if abs(int(old_boot) - int(startup_info.boot_time)) > 300 * 1e6:
      client.Set(client.Schema.LAST_BOOT_TIME(startup_info.boot_time))

    client.Close()

    flow.Events.PublishEventInline("ClientStartup", message, token=self.token)


class IgnoreResponses(flow.WellKnownFlow):
  """This flow exists so other well known flows can delegate their responses."""

  category = None

  well_known_session_id = rdfvalue.SessionID(flow_name="DevNull")

  def ProcessMessage(self, message):
    pass


class KeepAliveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KeepAliveArgs


class KeepAlive(flow.GRRFlow):
  """Requests that the clients stays alive for a period of time."""

  # We already want to run this flow while waiting for a client approval.
  # Note that this can potentially be abused to launch a DDOS attack against
  # the frontend server(s) by putting all clients into fastpoll mode. The load
  # of idle polling messages is not that high though and this can only be done
  # by users that have a GRR account already so the risk is acceptable.
  ACL_ENFORCED = False

  category = "/Administrative/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  sleep_time = 60
  args_type = KeepAliveArgs

  @flow.StateHandler(next_state="SendMessage")
  def Start(self):
    self.state.Register("end_time", self.args.duration.Expiry())
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

    if rdfvalue.RDFDatetime().Now() < self.state.end_time - self.sleep_time:
      start_time = rdfvalue.RDFDatetime().Now() + self.sleep_time
      self.CallState(next_state="SendMessage", start_time=start_time)


class TerminateFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.TerminateFlowArgs


class TerminateFlow(flow.GRRFlow):
  """Terminate a flow with a given URN."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False
  args_type = TerminateFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Terminate a flow. User has to have access to the flow."""
    # We have to create special token here, because within the flow
    # token has supervisor access.
    check_token = access_control.ACLToken(username=self.token.username,
                                          reason=self.token.reason)
    # If we can read the flow, we're allowed to terminate it.
    data_store.DB.security_manager.CheckDataStoreAccess(check_token,
                                                        [self.args.flow_urn],
                                                        "r")

    flow.GRRFlow.TerminateFlow(self.args.flow_urn,
                               reason=self.args.reason,
                               token=self.token,
                               force=True)


class LaunchBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.LaunchBinaryArgs


class LaunchBinary(flow.GRRFlow):
  """Launch a signed binary on a client."""

  category = "/Administrative/"

  AUTHORIZED_LABELS = ["admin"]
  args_type = LaunchBinaryArgs

  @flow.StateHandler(next_state=["End"])
  def Start(self):
    fd = aff4.FACTORY.Open(self.args.binary, token=self.token)
    if not isinstance(fd, collects.GRRSignedBlob):
      raise RuntimeError("Executable binary %s not found." % self.args.binary)

    offset = 0
    write_path = "%d" % time.time()
    for i, blob in enumerate(fd):
      self.CallClient("ExecuteBinaryCommand",
                      executable=blob,
                      more_data=i < fd.chunks - 1,
                      args=shlex.split(self.args.command_line),
                      offset=offset,
                      write_path=write_path,
                      next_state="End")

      offset += len(blob.data)

  def _TruncateResult(self, data):
    if len(data) > 2000:
      result = data[:2000] + "... [truncated]"
    else:
      result = data

    return result

  @flow.StateHandler()
  def End(self, responses):
    if not responses.success:
      raise IOError(responses.status)

    response = responses.First()
    if response:
      self.Log("Stdout: %s" % self._TruncateResult(response.stdout))
      self.Log("Stderr: %s" % self._TruncateResult(response.stderr))

      self.SendReply(response)


class RunReportFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RunReportFlowArgs


class RunReport(flow.GRRGlobalFlow):
  """Run a report and send the result via email."""

  category = "/Reporting/"

  args_type = RunReportFlowArgs
  behaviours = flow.GRRGlobalFlow.behaviours + "BASIC"

  ACL_ENFORCED = False

  # Only admins are allows to run reports.
  AUTHORIZED_LABELS = ["admin"]

  @flow.StateHandler(next_state="RunReport")
  def Start(self):
    if self.state.args.report_name not in reports.Report.classes:
      raise flow.FlowError("No such report %s" % self.state.args.report_name)
    else:
      self.CallState(next_state="RunReport")

  @flow.StateHandler(next_state="EmailReport")
  def RunReport(self):
    """Run the report."""
    report_cls = reports.Report.GetPlugin(self.state.args.report_name)
    report_obj = report_cls(token=self.token)
    report_obj.Run()
    report_obj.MailReport(self.state.args.email)
