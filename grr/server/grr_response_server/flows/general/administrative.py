#!/usr/bin/env python
"""Administrative flows for managing the clients state."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging
import os
import shlex
import time

import jinja2
from typing import Text

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import events
from grr_response_server import flow_base
from grr_response_server import hunt
from grr_response_server import message_handlers
from grr_response_server import server_stubs
from grr_response_server import signed_binary_utils
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects

GRR_CLIENT_CRASHES = metrics.Counter("grr_client_crashes")


def WriteAllCrashDetails(client_id, crash_details, flow_session_id=None):
  """Updates the last crash attribute of the client."""
  try:
    data_store.REL_DB.WriteClientCrashInfo(client_id, crash_details)
  except db.UnknownClientError:
    pass

  if not flow_session_id:
    return

  flow_id = flow_session_id.Basename()
  data_store.REL_DB.UpdateFlow(
      client_id, flow_id, client_crash_info=crash_details)

  flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
  if flow_obj.parent_hunt_id:
    hunt.StopHuntIfCrashLimitExceeded(flow_obj.parent_hunt_id)


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
      GRR_CLIENT_CRASHES.Increment()

      # Write crash data.
      client = data_store.REL_DB.ReadClientSnapshot(client_id)
      if client:
        crash_details.client_info = client.startup_info.client_info
        hostname = client.knowledge_base.fqdn
      else:
        hostname = ""

      crash_details.crash_type = "Client Crash"

      if nanny_msg:
        termination_msg = "Client crashed, " + nanny_msg
      else:
        termination_msg = "Client crashed."

      # Terminate the flow.
      flow_id = session_id.Basename()
      flow_base.TerminateFlow(
          client_id,
          flow_id,
          reason=termination_msg,
          flow_state=rdf_flow_objects.Flow.FlowState.CRASHED)

      WriteAllCrashDetails(client_id, crash_details, flow_session_id=session_id)

      # Also send email.
      email_address = config.CONFIG["Monitoring.alert_email"]
      if not email_address:
        return

      if crash_details.nanny_status:
        nanny_msg = "Nanny status: %s" % crash_details.nanny_status

      body = self.__class__.mail_template.render(
          client_id=client_id,
          admin_ui=config.CONFIG["AdminUI.url"],
          hostname=utils.SmartUnicode(hostname),
          url="/clients/%s" % client_id,
          nanny_msg=utils.SmartUnicode(nanny_msg),
          signature=config.CONFIG["Email.signature"])

      try:
        email_alerts.EMAIL_ALERTER.SendEmail(
            email_address,
            "GRR server",
            "Client %s reported a crash." % client_id,
            body,
            is_html=True)
      except email_alerts.EmailNotSentError as e:
        # We have already written the crash details to the DB, so failing
        # to send an email isn't super-critical.
        logging.warning(e)


class GetClientStatsProcessResponseMixin(object):
  """Mixin defining ProcessResponse() that writes client stats to datastore."""

  def ProcessResponse(self, client_id, response):
    """Actually processes the contents of the response."""
    precondition.AssertType(client_id, Text)
    downsampled = rdf_client_stats.ClientStats.Downsampled(response)

    data_store.REL_DB.WriteClientStats(client_id, downsampled)

    return downsampled


class GetClientStats(flow_base.FlowBase, GetClientStatsProcessResponseMixin):
  """This flow retrieves information about the GRR client process."""

  category = "/Administrative/"

  def Start(self):
    self.CallClient(
        server_stubs.GetClientStats,
        next_state=compatibility.GetName(self.StoreResults))

  def StoreResults(self, responses):
    """Stores the responses."""

    if not responses.success:
      self.Error("Failed to retrieve client stats.")
      return

    for response in responses:
      downsampled = self.ProcessResponse(self.client_urn.Basename(), response)
      self.SendReply(downsampled)


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


class DeleteGRRTempFiles(flow_base.FlowBase):
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
        server_stubs.DeleteGRRTempFiles,
        self.args.pathspec,
        next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError(str(responses.status))

    for response in responses:
      self.Log(response.data)


class UninstallArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UninstallArgs


class Uninstall(flow_base.FlowBase):
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
      self.CallClient(
          server_stubs.Uninstall, next_state=compatibility.GetName(self.Kill))
    else:
      self.Log("Unsupported platform for Uninstall")

  def Kill(self, responses):
    """Call the kill function on the client."""
    if not responses.success:
      self.Log("Failed to uninstall client.")
    elif self.args.kill:
      self.CallClient(
          server_stubs.Kill,
          next_state=compatibility.GetName(self.Confirmation))

  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class Kill(flow_base.FlowBase):
  """Terminate a running client (does not disable, just kill)."""

  category = "/Administrative/"

  def Start(self):
    """Call the kill function on the client."""
    self.CallClient(
        server_stubs.Kill, next_state=compatibility.GetName(self.Confirmation))

  def Confirmation(self, responses):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class UpdateConfigurationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateConfigurationArgs
  rdf_deps = [
      rdf_protodict.Dict,
  ]


class UpdateConfiguration(flow_base.FlowBase):
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
        next_state=compatibility.GetName(self.Confirmation))

  def Confirmation(self, responses):
    """Confirmation."""
    if not responses.success:
      raise flow_base.FlowError("Failed to write config. Err: {0}".format(
          responses.status))


class ExecutePythonHackArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecutePythonHackArgs
  rdf_deps = [
      rdf_protodict.Dict,
  ]


class ExecutePythonHack(flow_base.FlowBase):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"
  args_type = ExecutePythonHackArgs

  def Start(self):
    """The start method."""
    python_hack_urn = signed_binary_utils.GetAFF4PythonHackRoot().Add(
        self.args.hack_name)

    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
          python_hack_urn)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow_base.FlowError("Python hack %s not found." %
                                self.args.hack_name)

    # TODO(amoser): This will break if someone wants to execute lots of Python.
    for python_blob in blob_iterator:
      self.CallClient(
          server_stubs.ExecutePython,
          python_code=python_blob,
          py_args=self.args.py_args,
          next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    """Retrieves the output for the hack."""
    response = responses.First()
    if not responses.success:
      raise flow_base.FlowError("Execute Python hack failed: %s" %
                                responses.status)
    if response:
      result = response.return_val
      # Send reply with full data, but only log the first 200 bytes.
      str_result = result[0:200]
      if len(result) >= 200:
        str_result += "...[truncated]"
      self.Log("Result: %s" % str_result)
      self.SendReply(rdfvalue.RDFString(response.return_val))


class ExecuteCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecuteCommandArgs


class ExecuteCommand(flow_base.FlowBase):
  """Execute a predefined command on the client."""

  args_type = ExecuteCommandArgs

  def Start(self):
    """Call the execute function on the client."""
    self.CallClient(
        server_stubs.ExecuteCommand,
        cmd=self.args.cmd,
        args=shlex.split(self.args.command_line),
        time_limit=self.args.time_limit,
        next_state=compatibility.GetName(self.Confirmation))

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


class OnlineNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.OnlineNotificationArgs
  rdf_deps = [
      rdf_standard.DomainEmailAddress,
  ]


class OnlineNotification(flow_base.FlowBase):
  """Notifies by email when a client comes online in GRR."""

  category = "/Administrative/"
  behaviours = flow_base.BEHAVIOUR_BASIC

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
    self.CallClient(
        server_stubs.Echo,
        data="Ping",
        next_state=compatibility.GetName(self.SendMail))

  def SendMail(self, responses):
    """Sends a mail when the client has responded."""
    if not responses.success:
      raise flow_base.FlowError("Error while pinging client.")

    client = data_store.REL_DB.ReadClientSnapshot(self.client_id)
    hostname = client.knowledge_base.fqdn

    subject = self.__class__.subject_template.render(hostname=hostname)
    body = self.__class__.template.render(
        client_id=self.client_id,
        admin_ui=config.CONFIG["AdminUI.url"],
        hostname=hostname,
        url="/clients/%s" % self.client_id,
        creator=self.token.username,
        signature=utils.SmartUnicode(config.CONFIG["Email.signature"]))

    email_alerts.EMAIL_ALERTER.SendEmail(
        self.args.email, "grr-noreply", subject, body, is_html=True)


class UpdateClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateClientArgs
  rdf_deps = []


class UpdateClient(flow_base.FlowBase):
  """Updates the GRR client to a new version replacing the current client.

  This will execute the specified installer on the client and then run
  an Interrogate flow.

  The new installer's binary has to be uploaded to GRR (as a binary, not as
  a Python hack) and must be signed using the exec signing key.

  Signing and upload of the file is done with grr_config_updater or through
  the API.
  """

  category = "/Administrative/"

  args_type = UpdateClientArgs

  def _BlobIterator(self, binary_id):
    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByID(
          binary_id)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow_base.FlowError("%s is not a valid signed binary." %
                                self.args.binary_path)
    return blob_iterator

  @property
  def _binary_id(self):
    return rdf_objects.SignedBinaryID(
        binary_type=rdf_objects.SignedBinaryID.BinaryType.EXECUTABLE,
        path=self.args.binary_path)

  def Start(self):
    """Start."""
    if not self.args.binary_path:
      raise flow_base.FlowError("Installer binary path is not specified.")

    self.state.write_path = "%d_%s" % (int(
        time.time()), os.path.basename(self.args.binary_path))

    blob_iterator = self._BlobIterator(self._binary_id)
    try:
      first_blob = next(blob_iterator)
    except StopIteration:
      raise flow_base.FlowError("File %s is empty." % self.args.blob_path)

    try:
      next(blob_iterator)
    except StopIteration:
      # This is the simple case where the binary fits into a single blob. We can
      # do all work in a single call to the client.
      self.CallClient(
          server_stubs.UpdateAgent,
          executable=first_blob,
          more_data=False,
          offset=0,
          write_path=self.state.write_path,
          next_state=compatibility.GetName(self.Interrogate),
          use_client_env=False)
      return

    self.CallClient(
        server_stubs.UpdateAgent,
        executable=first_blob,
        more_data=True,
        offset=0,
        write_path=self.state.write_path,
        next_state=compatibility.GetName(self.SendBlobs),
        use_client_env=False)

  def SendBlobs(self, responses):
    """Sends all blobs that are not the first or the last."""
    if not responses.success:
      raise flow_base.FlowError("Error while calling UpdateAgent: %s" %
                                responses.status)

    blobs = list(self._BlobIterator(self._binary_id))
    to_send = blobs[1:-1]

    if not to_send:
      self.CallStateInline(next_state=compatibility.GetName(self.SendLastBlob))
      return
    offset = len(blobs[0].data)

    for i, blob in enumerate(to_send):
      if i == len(to_send) - 1:
        next_state = "SendLastBlob"
      else:
        next_state = "CheckUpdateAgent"

      self.CallClient(
          server_stubs.UpdateAgent,
          executable=blob,
          more_data=True,
          offset=offset,
          write_path=self.state.write_path,
          next_state=next_state,
          use_client_env=False)
      offset += len(blob.data)

  def SendLastBlob(self, responses):
    """Sends the last blob."""
    if not responses.success:
      raise flow_base.FlowError("Error while calling UpdateAgent: %s" %
                                responses.status)

    blobs = list(self._BlobIterator(self._binary_id))
    offset = 0
    for b in blobs[:-1]:
      offset += len(b.data)

    self.CallClient(
        server_stubs.UpdateAgent,
        executable=blobs[-1],
        more_data=False,
        offset=offset,
        write_path=self.state.write_path,
        next_state=compatibility.GetName(self.Interrogate),
        use_client_env=False)

  def CheckUpdateAgent(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Error while calling UpdateAgent: %s" %
                                responses.status)

  def Interrogate(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Installer reported an error: %s" %
                                responses.status)

    self.Log("Installer completed.")
    self.CallFlow(
        discovery.Interrogate.__name__,
        next_state=compatibility.GetName(self.Done))

  def Done(self, responses):
    if not responses.success:
      raise flow_base.FlowError(responses.status)


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
    client = data_store.REL_DB.ReadClientSnapshot(client_id)
    if client is not None:
      client_info = client.startup_info.client_info
      hostname = client.knowledge_base.fqdn

    crash_details = rdf_client.ClientCrash(
        client_id=client_id,
        client_info=client_info,
        crash_message=message,
        timestamp=int(time.time() * 1e6),
        crash_type="Nanny Message")

    WriteAllCrashDetails(client_id, crash_details)

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
          body,
          is_html=True)


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
    drift = rdfvalue.Duration.From(5, rdfvalue.MINUTES)

    current_si = data_store.REL_DB.ReadClientStartupInfo(client_id)

    # We write the updated record if the client_info has any changes
    # or the boot time is more than 5 minutes different.
    if (not current_si or current_si.client_info != new_si.client_info or
        not current_si.boot_time or
        current_si.boot_time - new_si.boot_time > drift):
      try:
        data_store.REL_DB.WriteClientStartupInfo(client_id, new_si)
        labels = new_si.client_info.labels
        if labels:
          data_store.REL_DB.AddClientLabels(client_id, "GRR", labels)
          index = client_index.ClientIndex()
          index.AddClientLabels(client_id, labels)

      except db.UnknownClientError:
        # On first contact with a new client, this write will fail.
        logging.info("Can't write StartupInfo for unknown client %s", client_id)


class ClientStartupHandler(ClientStartupHandlerMixin,
                           message_handlers.MessageHandler):

  handler_name = "ClientStartupHandler"

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.WriteClientStartupInfo(message.client_id, message.request.payload)


class KeepAliveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.KeepAliveArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
  ]


class KeepAlive(flow_base.FlowBase):
  """Requests that the clients stays alive for a period of time."""

  category = "/Administrative/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  sleep_time = 60
  args_type = KeepAliveArgs

  def Start(self):
    self.state.end_time = self.args.duration.Expiry()
    self.CallStateInline(next_state=compatibility.GetName(self.SendMessage))

  def SendMessage(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow_base.FlowError(responses.status.error_message)

    self.CallClient(
        server_stubs.Echo,
        data="Wake up!",
        next_state=compatibility.GetName(self.Sleep))

  def Sleep(self, responses):
    if not responses.success:
      self.Log(responses.status.error_message)
      raise flow_base.FlowError(responses.status.error_message)

    if rdfvalue.RDFDatetime.Now() < self.state.end_time - self.sleep_time:
      start_time = rdfvalue.RDFDatetime.Now() + self.sleep_time
      self.CallState(
          next_state=compatibility.GetName(self.SendMessage),
          start_time=start_time)


class LaunchBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.LaunchBinaryArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class LaunchBinary(flow_base.FlowBase):
  """Launch a signed binary on a client."""

  category = "/Administrative/"

  args_type = LaunchBinaryArgs

  def _BlobIterator(self, binary_urn):
    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
          binary_urn)
    except signed_binary_utils.SignedBinaryNotFoundError:
      raise flow_base.FlowError("Executable binary %s not found." %
                                self.args.binary)

    return blob_iterator

  def Start(self):
    """The start method."""
    if not self.args.binary:
      raise flow_base.FlowError("Please specify a binary.")

    binary_urn = rdfvalue.RDFURN(self.args.binary)
    self.state.write_path = "%d_%s" % (time.time(), binary_urn.Basename())

    blob_iterator = self._BlobIterator(binary_urn)
    try:
      first_blob = next(blob_iterator)
    except StopIteration:
      raise flow_base.FlowError("File %s is empty." % self.args.binary)

    try:
      next(blob_iterator)
    except StopIteration:
      # This is the simple case where the binary fits into a single blob. We can
      # do all work in a single call to the client.
      self.CallClient(
          server_stubs.ExecuteBinaryCommand,
          executable=first_blob,
          more_data=False,
          args=shlex.split(self.args.command_line),
          offset=0,
          write_path=self.state.write_path,
          next_state=compatibility.GetName(self.End))
      return

    self.CallClient(
        server_stubs.ExecuteBinaryCommand,
        executable=first_blob,
        more_data=True,
        offset=0,
        write_path=self.state.write_path,
        next_state=compatibility.GetName(self.SendBlobs))

  def SendBlobs(self, responses):
    """Sends all blobs that are not the first or the last."""
    if not responses.success:
      raise flow_base.FlowError("Error while calling UpdateAgent: %s" %
                                responses.status)

    binary_urn = rdfvalue.RDFURN(self.args.binary)
    blobs = list(self._BlobIterator(binary_urn))
    to_send = blobs[1:-1]

    if not to_send:
      self.CallStateInline(next_state=compatibility.GetName(self.SendLastBlob))
      return
    offset = len(blobs[0].data)

    for i, blob in enumerate(to_send):
      if i == len(to_send) - 1:
        next_state = "SendLastBlob"
      else:
        next_state = "CheckResponse"

      self.CallClient(
          server_stubs.ExecuteBinaryCommand,
          executable=blob,
          more_data=True,
          offset=offset,
          write_path=self.state.write_path,
          next_state=next_state)
      offset += len(blob.data)

  def SendLastBlob(self, responses):
    """Sends the last blob."""
    if not responses.success:
      raise flow_base.FlowError("Error while calling UpdateAgent: %s" %
                                responses.status)

    binary_urn = rdfvalue.RDFURN(self.args.binary)
    blobs = list(self._BlobIterator(binary_urn))
    offset = 0
    for b in blobs[:-1]:
      offset += len(b.data)

    self.CallClient(
        server_stubs.ExecuteBinaryCommand,
        executable=blobs[-1],
        more_data=False,
        args=shlex.split(self.args.command_line),
        offset=offset,
        write_path=self.state.write_path,
        next_state=compatibility.GetName(self.End),
        use_client_env=False)

  def CheckResponse(self, responses):
    if not responses.success:
      raise flow_base.FlowError("Error while calling ExecuteBinaryCommand: %s" %
                                responses.status)

  def _SanitizeOutput(self, data):
    if len(data) > 2000:
      result = data[:2000] + "... [truncated]".encode("utf-8")
    else:
      result = data

    # Output can contain arbitrary bytes. Since the goal is to produce readable
    # logs, we simply ignore weird characters.
    return result.decode("utf-8", "ignore")

  def End(self, responses):
    if not responses.success:
      raise IOError(responses.status)

    response = responses.First()
    if response:
      self.Log("Stdout: %s", self._SanitizeOutput(response.stdout))
      self.Log("Stderr: %s", self._SanitizeOutput(response.stderr))

      self.SendReply(response)
