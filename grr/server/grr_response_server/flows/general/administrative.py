#!/usr/bin/env python
"""Administrative flows for managing the clients state."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import shlex
import threading
import time

import jinja2

from grr_response_core import config
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import flows_pb2
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import db_compat
from grr_response_server import email_alerts
from grr_response_server import events
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import grr_collections
from grr_response_server import message_handlers
from grr_response_server import server_stubs
from grr_response_server import signed_binary_utils
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import stats as aff4_stats
from grr_response_server.flows.general import discovery
from grr_response_server.hunts import implementation


def ExtractHuntId(flow_session_id):
  hunt_str, hunt_id, _ = flow_session_id.Split(3)
  if hunt_str == "hunts":
    return aff4.ROOT_URN.Add("hunts").Add(hunt_id)


def WriteAllCrashDetails(client_id,
                         crash_details,
                         flow_session_id=None,
                         hunt_session_id=None,
                         token=None):
  """Updates the last crash attribute of the client."""
  # AFF4.
  if data_store.AFF4Enabled():
    with aff4.FACTORY.Create(
        client_id, aff4_grr.VFSGRRClient, token=token) as client_obj:
      client_obj.Set(client_obj.Schema.LAST_CRASH(crash_details))

    # Duplicate the crash information in a number of places so we can find it
    # easily.
    client_urn = rdf_client.ClientURN(client_id)
    client_crashes = aff4_grr.VFSGRRClient.CrashCollectionURNForCID(client_urn)
    with data_store.DB.GetMutationPool() as pool:
      grr_collections.CrashCollection.StaticAdd(
          client_crashes, crash_details, mutation_pool=pool)

  # Relational db.
  if data_store.RelationalDBWriteEnabled():
    try:
      data_store.REL_DB.WriteClientCrashInfo(client_id, crash_details)
    except db.UnknownClientError:
      pass

  if not flow_session_id:
    return

  if data_store.RelationalDBFlowsEnabled():
    flow_id = flow_session_id.Basename()
    data_store.REL_DB.UpdateFlow(
        client_id, flow_id, client_crash_info=crash_details)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.parent_hunt_id:
      db_compat.ProcessHuntClientCrash(
          flow_obj, client_crash_info=crash_details)

  # TODO(amoser): Registering crashes in hunts is currently not implemented for
  # the relational db.
  if not data_store.RelationalDBFlowsEnabled():
    with aff4.FACTORY.Open(
        flow_session_id,
        flow.GRRFlow,
        mode="rw",
        age=aff4.NEWEST_TIME,
        token=token) as aff4_flow:
      aff4_flow.Set(aff4_flow.Schema.CLIENT_CRASH(crash_details))

    hunt_session_id = ExtractHuntId(flow_session_id)
    if hunt_session_id and hunt_session_id != flow_session_id:
      hunt_obj = aff4.FACTORY.Open(
          hunt_session_id,
          aff4_type=implementation.GRRHunt,
          mode="rw",
          token=token)
      hunt_obj.RegisterCrash(crash_details)


class ClientCrashHandler(events.EventListener):
  """A listener for client crashes."""

  EVENTS = ["ClientCrash"]

  mail_template = jinja2.Template(
      """
<html><body><h1>GRR client crash report.</h1>

Client {{ client_id }} ({{ hostname }}) just crashed while executing an action.
Click <a href='{{ admin_ui }}#{{ url }}'>here</a> to access this machine.

<p>Thanks,</p>
<p>{{ signature }}</p>

{{ nanny_msg }}

</body></html>""",
      autoescape=True)

  def ProcessMessages(self, msgs=None, token=None):
    """Processes this event."""
    nanny_msg = ""

    for crash_details in msgs:
      client_urn = crash_details.client_id
      client_id = client_urn.Basename()

      # The session id of the flow that crashed.
      session_id = crash_details.session_id

      # Log.
      logging.info("Client crash reported, client %s.", client_urn)

      # Export.
      stats_collector_instance.Get().IncrementCounter("grr_client_crashes")

      # Write crash data.
      if data_store.RelationalDBWriteEnabled():
        client = data_store.REL_DB.ReadClientSnapshot(client_id)
        if client:
          crash_details.client_info = client.startup_info.client_info
          hostname = client.knowledge_base.fqdn
        else:
          hostname = ""

      if data_store.AFF4Enabled():
        client = aff4.FACTORY.Open(client_urn, token=token)
        client_info = client.Get(client.Schema.CLIENT_INFO)
        hostname = client.Get(client.Schema.FQDN)
        if client_info:
          crash_details.client_info = client_info

      crash_details.crash_type = "Client Crash"

      WriteAllCrashDetails(
          client_id, crash_details, flow_session_id=session_id, token=token)

      # Also send email.
      to_send = []

      try:
        hunt_session_id = ExtractHuntId(session_id)
        if hunt_session_id and hunt_session_id != session_id:

          # TODO(amoser): Enable this for the relational db once we have hunt
          # metadata.
          if data_store.AFF4Enabled():
            hunt_obj = aff4.FACTORY.Open(
                hunt_session_id, aff4_type=implementation.GRRHunt, token=token)
            email = hunt_obj.runner_args.crash_alert_email

          if email:
            to_send.append(email)
      except aff4.InstantiationError:
        logging.error("Failed to open hunt %s.", hunt_session_id)

      email = config.CONFIG["Monitoring.alert_email"]
      if email:
        to_send.append(email)

      if nanny_msg:
        termination_msg = "Client crashed, " + nanny_msg
      else:
        termination_msg = "Client crashed."

      for email_address in to_send:
        if crash_details.nanny_status:
          nanny_msg = "Nanny status: %s" % crash_details.nanny_status

        body = self.__class__.mail_template.render(
            client_id=client_id,
            admin_ui=config.CONFIG["AdminUI.url"],
            hostname=utils.SmartUnicode(hostname),
            url="/clients/%s" % client_id,
            nanny_msg=utils.SmartUnicode(nanny_msg),
            signature=config.CONFIG["Email.signature"])

        email_alerts.EMAIL_ALERTER.SendEmail(
            email_address,
            "GRR server",
            "Client %s reported a crash." % client_id,
            utils.SmartStr(body),
            is_html=True)

        # Now terminate the flow.
        if data_store.RelationalDBFlowsEnabled():
          flow_id = session_id.Basename()
          flow_base.TerminateFlow(client_id, flow_id, reason=termination_msg)
        else:
          flow.GRRFlow.TerminateAFF4Flow(
              session_id, reason=termination_msg, token=token)


class GetClientStatsProcessResponseMixin(object):
  """Mixin defining ProcessResponse() that writes client stats to datastore."""

  def ProcessResponse(self, client_id, response):
    """Actually processes the contents of the response."""

    downsampled = rdf_client_stats.ClientStats.Downsampled(response)

    # TODO(amoser): We need client stats storage for the relational db.
    if not data_store.AFF4Enabled():
      return downsampled

    urn = rdf_client.ClientURN(client_id).Add("stats")

    with aff4.FACTORY.Create(
        urn, aff4_stats.ClientStats, token=self.token, mode="w") as stats_fd:
      # Only keep the average of all values that fall within one minute.
      stats_fd.AddAttribute(stats_fd.Schema.STATS, downsampled)

    return downsampled


@flow_base.DualDBFlow
class GetClientStatsMixin(GetClientStatsProcessResponseMixin):
  """This flow retrieves information about the GRR client process."""

  category = "/Administrative/"

  def Start(self):
    self.CallClient(server_stubs.GetClientStats, next_state="StoreResults")

  def StoreResults(self, responses):
    """Stores the responses."""

    if not responses.success:
      self.Error("Failed to retrieve client stats.")
      return

    for response in responses:
      downsampled = self.ProcessResponse(self.client_urn, response)
      self.SendReply(downsampled)


class GetClientStatsAuto(flow.WellKnownFlow,
                         GetClientStatsProcessResponseMixin):
  """This action pushes client stats to the server automatically."""

  category = None

  well_known_session_id = rdfvalue.SessionID(
      flow_name="Stats", queue=queues.STATS)

  def ProcessMessage(self, message):
    """Processes a stats response from the client."""
    self.ProcessResponse(message.source.Basename(), message.payload)


class ClientStatsHandler(message_handlers.MessageHandler,
                         GetClientStatsProcessResponseMixin):

  handler_name = "StatsHandler"

  def ProcessMessages(self, msgs):
    for msg in msgs:
      self.ProcessResponse(msg.client_id, msg.request.payload)


class DeleteGRRTempFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DeleteGRRTempFilesArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


@flow_base.DualDBFlow
class DeleteGRRTempFilesMixin(object):
  """Delete all the GRR temp files in path.

  If path is a directory, look in the top level for filenames beginning with
  Client.tempfile_prefix, and delete them.

  If path is a regular file and starts with Client.tempfile_prefix, delete it.
  """

  category = "/Administrative/"
  args_type = DeleteGRRTempFilesArgs

  def Start(self):
    """Issue a request to delete tempfiles in directory."""
    self.CallClient(
        server_stubs.DeleteGRRTempFiles, self.args.pathspec, next_state="Done")

  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(str(responses.status))

    for response in responses:
      self.Log(response.data)


class UninstallArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UninstallArgs


@flow_base.DualDBFlow
class UninstallMixin(object):
  """Removes the persistence mechanism which the client uses at boot.

  For Windows and OSX, this will disable the service, and then stop the service.
  For Linux this flow will fail as we haven't implemented it yet :)
  """

  category = "/Administrative/"
  args_type = UninstallArgs

  def Start(self):
    """Start the flow and determine OS support."""
    system = self.client_os

    if system == "Darwin" or system == "Windows":
      self.CallClient(server_stubs.Uninstall, next_state="Kill")
    else:
      self.Log("Unsupported platform for Uninstall")

  def Kill(self, responses):
    """Call the kill function on the client."""
    if not responses.success:
      self.Log("Failed to uninstall client.")
    elif self.args.kill:
      self.CallClient(server_stubs.Kill, next_state="Confirmation")

  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


@flow_base.DualDBFlow
class KillMixin(object):
  """Terminate a running client (does not disable, just kill)."""

  category = "/Administrative/"

  def Start(self):
    """Call the kill function on the client."""
    self.CallClient(server_stubs.Kill, next_state="Confirmation")

  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class UpdateConfigurationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateConfigurationArgs
  rdf_deps = [
      rdf_protodict.Dict,
  ]


@flow_base.DualDBFlow
class UpdateConfigurationMixin(object):
  """Update the configuration of the client.

    Note: This flow is somewhat dangerous, so we don't expose it in the UI.
  """

  # Still accessible (e.g. via ajax but not visible in the UI.)
  category = None
  args_type = UpdateConfigurationArgs

  def Start(self):
    """Call the UpdateConfiguration function on the client."""
    self.CallClient(
        server_stubs.UpdateConfiguration,
        request=self.args.config,
        next_state="Confirmation")

  def Confirmation(self, responses):
    """Confirmation."""
    if not responses.success:
      raise flow.FlowError("Failed to write config. Err: {0}".format(
          responses.status))


class ExecutePythonHackArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecutePythonHackArgs
  rdf_deps = [
      rdf_protodict.Dict,
  ]


@flow_base.DualDBFlow
class ExecutePythonHackMixin(object):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"
  args_type = ExecutePythonHackArgs

  def Start(self):
    """The start method."""
    python_hack_urn = signed_binary_utils.GetAFF4PythonHackRoot().Add(
        self.args.hack_name)

    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinary(
          python_hack_urn, token=self.token)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow.FlowError("Python hack %s not found." % self.args.hack_name)

    # TODO(amoser): This will break if someone wants to execute lots of Python.
    for python_blob in blob_iterator:
      self.CallClient(
          server_stubs.ExecutePython,
          python_code=python_blob,
          py_args=self.args.py_args,
          next_state="Done")

  def Done(self, responses):
    """Retrieves the output for the hack."""
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


@flow_base.DualDBFlow
class ExecuteCommandMixin(object):
  """Execute a predefined command on the client."""

  args_type = ExecuteCommandArgs

  def Start(self):
    """Call the execute function on the client."""
    self.CallClient(
        server_stubs.ExecuteCommand,
        cmd=self.args.cmd,
        args=shlex.split(self.args.command_line),
        time_limit=self.args.time_limit,
        next_state="Confirmation")

  def Confirmation(self, responses):
    """Confirmation."""
    if responses.success:
      response = responses.First()
      self.Log(
          ("Execution of %s %s (return value %d, "
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
        self.foreman_cache = aff4.FACTORY.Open(
            "aff4:/foreman", mode="rw", token=self.token)
        self.foreman_cache.age = now

    if message.source:
      self.foreman_cache.AssignTasksToClient(message.source.Basename())


class OnlineNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.OnlineNotificationArgs
  rdf_deps = [
      rdf_standard.DomainEmailAddress,
  ]


@flow_base.DualDBFlow
class OnlineNotificationMixin(object):
  """Notifies by email when a client comes online in GRR."""

  category = "/Administrative/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  subject_template = jinja2.Template(
      "GRR Client on {{ hostname }} became available.", autoescape=True)
  template = jinja2.Template(
      """
<html><body><h1>GRR Client Online Notification.</h1>

<p>
  Client {{ client_id }} ({{ hostname }}) just came online. Click
  <a href='{{ admin_ui }}/#{{ url }}'>here</a> to access this machine.
  <br />This notification was created by %(creator)s.
</p>

<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
      autoescape=True)

  args_type = OnlineNotificationArgs

  @classmethod
  def GetDefaultArgs(cls, username=None):
    """Returns an args rdfvalue prefilled with sensible default values."""
    args = cls.args_type()
    try:
      args.email = "%s@%s" % (username, config.CONFIG.Get("Logging.domain"))
    except ValueError:
      # Just set no default if the email is not well-formed. Example: when
      # username contains '@' character.
      pass

    return args

  def Start(self):
    """Starts processing."""
    if self.args.email is None:
      self.args.email = self.token.username
    self.CallClient(server_stubs.Echo, data="Ping", next_state="SendMail")

  def SendMail(self, responses):
    """Sends a mail when the client has responded."""
    if responses.success:
      if data_store.RelationalDBReadEnabled():
        client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
        hostname = client.knowledge_base.fqdn
      else:
        client = aff4.FACTORY.Open(self.client_id, token=self.token)
        hostname = client.Get(client.Schema.FQDN)

      subject = self.__class__.subject_template.render(hostname=hostname)
      body = self.__class__.template.render(
          client_id=self.client_id,
          admin_ui=config.CONFIG["AdminUI.url"],
          hostname=hostname,
          url="/clients/%s" % self.client_id,
          creator=self.token.username,
          signature=utils.SmartUnicode(config.CONFIG["Email.signature"]))

      email_alerts.EMAIL_ALERTER.SendEmail(
          self.args.email,
          "grr-noreply",
          utils.SmartStr(subject),
          utils.SmartStr(body),
          is_html=True)
    else:
      flow.FlowError("Error while pinging client.")


class UpdateClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateClientArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


@flow_base.DualDBFlow
class UpdateClientMixin(object):
  """Updates the GRR client to a new version replacing the current client.

  This will execute the specified installer on the client and then run
  an Interrogate flow.

  The new installer needs to be loaded into the database, generally in
  /config/executables/<platform>/installers and must be signed using the
  exec signing key.

  Signing and upload of the file is done with config_updater.
  """

  category = "/Administrative/"

  args_type = UpdateClientArgs

  def Start(self):
    """Start."""
    binary_path = self.args.blob_path
    if not binary_path:
      raise flow.FlowError("Please specify an installer binary.")

    binary_urn = rdfvalue.RDFURN(binary_path)
    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinary(
          binary_urn, token=self.token)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow.FlowError("%s is not a valid signed binary." % binary_path)

    offset = 0
    write_path = "%d_%s" % (time.time(), binary_urn.Basename())

    try:
      current_blob = next(blob_iterator)
    except StopIteration:
      current_blob = None

    while current_blob is not None:
      try:
        next_blob = next(blob_iterator)
      except StopIteration:
        next_blob = None
      more_data = next_blob is not None
      self.CallClient(
          server_stubs.UpdateAgent,
          executable=current_blob,
          more_data=more_data,
          offset=offset,
          write_path=write_path,
          next_state=("CheckUpdateAgent" if more_data else "Interrogate"),
          use_client_env=False)
      offset += len(current_blob.data)
      current_blob = next_blob

  def CheckUpdateAgent(self, responses):
    if not responses.success:
      raise flow.FlowError(
          "Error while calling UpdateAgent: %s" % responses.status)

  def Interrogate(self, responses):
    if not responses.success:
      raise flow.FlowError("Installer reported an error: %s" % responses.status)

    self.Log("Installer completed.")
    self.CallFlow(discovery.Interrogate.__name__, next_state="Done")

  def Done(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)


class NannyMessageHandlerMixin(object):
  """A listener for nanny messages."""

  mail_template = jinja2.Template(
      """
<html><body><h1>GRR nanny message received.</h1>

The nanny for client {{ client_id }} ({{ hostname }}) just sent a message:<br>
<br>
{{ message }}
<br>
Click <a href='{{ admin_ui }}/#{{ url }}'>here</a> to access this machine.

<p>{{ signature }}</p>

</body></html>""",
      autoescape=True)

  subject = "GRR nanny message received from %s."

  logline = "Nanny for client %s sent: %s"

  def SendEmail(self, client_id, message):
    """Processes this event."""
    logging.info(self.logline, client_id, message)

    client_info = None
    hostname = None

    # Write crash data.
    if data_store.RelationalDBReadEnabled():
      client = data_store.REL_DB.ReadClientSnapshot(client_id)
      if client is not None:
        client_info = client.startup_info.client_info
        hostname = client.knowledge_base.fqdn
    else:
      client = aff4.FACTORY.Open(client_id, token=self.token)
      client_info = client.Get(client.Schema.CLIENT_INFO)
      hostname = client.Get(client.Schema.FQDN)

    crash_details = rdf_client.ClientCrash(
        client_id=client_id,
        client_info=client_info,
        crash_message=message,
        timestamp=int(time.time() * 1e6),
        crash_type="Nanny Message")

    WriteAllCrashDetails(client_id, crash_details, token=self.token)

    # Also send email.
    if config.CONFIG["Monitoring.alert_email"]:
      url = "/clients/%s" % client_id
      body = self.__class__.mail_template.render(
          client_id=client_id,
          admin_ui=config.CONFIG["AdminUI.url"],
          hostname=utils.SmartUnicode(hostname),
          signature=config.CONFIG["Email.signature"],
          url=url,
          message=utils.SmartUnicode(message))
      email_alerts.EMAIL_ALERTER.SendEmail(
          config.CONFIG["Monitoring.alert_email"],
          "GRR server",
          self.subject % client_id,
          utils.SmartStr(body),
          is_html=True)


class NannyMessageHandlerFlow(NannyMessageHandlerMixin, flow.WellKnownFlow):
  """A listener for nanny messages."""

  well_known_session_id = rdfvalue.SessionID(flow_name="NannyMessage")

  def ProcessMessage(self, message=None):
    self.SendEmail(message.source.Basename(), message.payload.string)


class NannyMessageHandler(NannyMessageHandlerMixin,
                          message_handlers.MessageHandler):

  handler_name = "NannyMessageHandler"

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.SendEmail(message.client_id, message.request.payload.string)


class ClientAlertHandlerMixin(NannyMessageHandlerMixin):
  """A listener for client messages."""

  mail_template = jinja2.Template(
      """
<html><body><h1>GRR client message received.</h1>

The client {{ client_id }} ({{ hostname }}) just sent a message:<br>
<br>
{{ message }}
<br>
Click <a href='{{ admin_ui }}/#{{ url }}'>here</a> to access this machine.

<p>{{ signature }}</p>

</body></html>""",
      autoescape=True)

  subject = "GRR client message received from %s."

  logline = "Client message from %s: %s"


class ClientAlertHandlerFlow(ClientAlertHandlerMixin, flow.WellKnownFlow):

  well_known_session_id = rdfvalue.SessionID(flow_name="ClientAlert")

  def ProcessMessage(self, message=None):
    self.SendEmail(message.source.Basename(), message.payload.string)


class ClientAlertHandler(ClientAlertHandlerMixin,
                         message_handlers.MessageHandler):

  handler_name = "ClientAlertHandler"

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.SendEmail(message.client_id, message.request.payload.string)


class ClientStartupHandlerMixin(object):
  """Handles client startup events."""

  def WriteClientStartupInfo(self, client_id, new_si):
    """Handle a startup event."""
    drift = rdfvalue.Duration("5m")

    if data_store.RelationalDBReadEnabled():
      current_si = data_store.REL_DB.ReadClientStartupInfo(client_id)

      # We write the updated record if the client_info has any changes
      # or the boot time is more than 5 minutes different.
      if (not current_si or current_si.client_info != new_si.client_info or
          not current_si.boot_time or
          abs(current_si.boot_time - new_si.boot_time) > drift):
        try:
          data_store.REL_DB.WriteClientStartupInfo(client_id, new_si)
        except db.UnknownClientError:
          # On first contact with a new client, this write will fail.
          logging.info("Can't write StartupInfo for unknown client %s",
                       client_id)
    else:
      changes = False
      with aff4.FACTORY.Create(
          client_id, aff4_grr.VFSGRRClient, mode="rw",
          token=self.token) as client:
        old_info = client.Get(client.Schema.CLIENT_INFO)
        old_boot = client.Get(client.Schema.LAST_BOOT_TIME, 0)

        info = new_si.client_info

        # Only write to the datastore if we have new information.
        if info != old_info:
          client.Set(client.Schema.CLIENT_INFO(info))
          changes = True

        client.AddLabels(info.labels, owner="GRR")

        # Allow for some drift in the boot times (5 minutes).
        if not old_boot or abs(old_boot - new_si.boot_time) > drift:
          client.Set(client.Schema.LAST_BOOT_TIME(new_si.boot_time))
          changes = True

      if data_store.RelationalDBWriteEnabled() and changes:
        try:
          data_store.REL_DB.WriteClientStartupInfo(client_id, new_si)
        except db.UnknownClientError:
          pass


class ClientStartupHandlerFlow(ClientStartupHandlerMixin, flow.WellKnownFlow):

  well_known_session_id = rdfvalue.SessionID(flow_name="Startup")

  def ProcessMessage(self, message=None):
    self.WriteClientStartupInfo(message.source.Basename(), message.payload)


class ClientStartupHandler(ClientStartupHandlerMixin,
                           message_handlers.MessageHandler):

  handler_name = "ClientStartupHandler"

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.WriteClientStartupInfo(message.client_id, message.request.payload)


class KeepAliveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KeepAliveArgs
  rdf_deps = [
      rdfvalue.Duration,
  ]


@flow_base.DualDBFlow
class KeepAliveMixin(object):
  """Requests that the clients stays alive for a period of time."""

  category = "/Administrative/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  sleep_time = 60
  args_type = KeepAliveArgs

  def Start(self):
    self.state.end_time = self.args.duration.Expiry()
    self.CallStateInline(next_state="SendMessage")

  def SendMessage(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)

    self.CallClient(server_stubs.Echo, data="Wake up!", next_state="Sleep")

  def Sleep(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow.FlowError(responses.status.error_message)

    if rdfvalue.RDFDatetime.Now() < self.state.end_time - self.sleep_time:
      start_time = rdfvalue.RDFDatetime.Now() + self.sleep_time
      self.CallState(next_state="SendMessage", start_time=start_time)


class LaunchBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.LaunchBinaryArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


@flow_base.DualDBFlow
class LaunchBinaryMixin(object):
  """Launch a signed binary on a client."""

  category = "/Administrative/"

  args_type = LaunchBinaryArgs

  def Start(self):
    """The start method."""
    binary_urn = rdfvalue.RDFURN(self.args.binary)
    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinary(
          binary_urn, token=self.token)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow.FlowError("Executable binary %s not found." % self.args.binary)

    try:
      current_blob = next(blob_iterator)
    except StopIteration:
      current_blob = None

    offset = 0
    write_path = "%d" % time.time()
    while current_blob is not None:
      try:
        next_blob = next(blob_iterator)
      except StopIteration:
        next_blob = None
      self.CallClient(
          server_stubs.ExecuteBinaryCommand,
          executable=current_blob,
          more_data=next_blob is not None,
          args=shlex.split(self.args.command_line),
          offset=offset,
          write_path=write_path,
          next_state="End")

      offset += len(current_blob.data)
      current_blob = next_blob

  def _TruncateResult(self, data):
    if len(data) > 2000:
      result = data[:2000] + "... [truncated]"
    else:
      result = data

    return result

  def End(self, responses):
    if not responses.success:
      raise IOError(responses.status)

    response = responses.First()
    if response:
      self.Log("Stdout: %s" % self._TruncateResult(response.stdout))
      self.Log("Stderr: %s" % self._TruncateResult(response.stderr))

      self.SendReply(response)
