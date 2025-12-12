#!/usr/bin/env python
"""Administrative flows for managing the clients state."""

from collections.abc import Sequence
import logging
import shlex
import time
from typing import Optional

import jinja2

from google.protobuf import any_pb2
from google.protobuf import message as pb_message
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import mig_client
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import events
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import hunt
from grr_response_server import message_handlers
from grr_response_server import server_stubs
from grr_response_server import signed_binary_utils
from grr_response_server.databases import db
from grr_response_server.flows.general import discovery
from grr_response_server.models import users as models_users
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_objects
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
      client_id,
      flow_id,
      client_crash_info=crash_details,
  )

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
Click <a href='{{ admin_ui }}v2{{ url }}'>here</a> to access this machine.

<p>Thanks,</p>
<p>{{ signature }}</p>

</body></html>""",
      autoescape=True,
  )

  def ProcessEvents(self, msgs=None, publisher_username=None):
    """Processes this event."""
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
        crash_details.client_info = mig_client.ToRDFClientInformation(
            client.startup_info.client_info
        )
        hostname = client.knowledge_base.fqdn
      else:
        hostname = ""

      crash_details.crash_type = "Client Crash"

      # Terminate the flow.
      flow_id = session_id.Basename()
      flow_base.TerminateFlow(
          client_id,
          flow_id,
          reason="Client crashed.",
          flow_state=rdf_flow_objects.Flow.FlowState.CRASHED,
      )

      crash_details = mig_client.ToProtoClientCrash(crash_details)
      WriteAllCrashDetails(client_id, crash_details, flow_session_id=session_id)

      # Also send email.
      email_address = config.CONFIG["Monitoring.alert_email"]
      if not email_address:
        return

      body = self.__class__.mail_template.render(
          client_id=client_id,
          admin_ui=config.CONFIG["AdminUI.url"],
          hostname=utils.SmartUnicode(hostname),
          url="/clients/%s" % client_id,
          signature=config.CONFIG["Email.signature"],
      )

      try:
        email_alerts.EMAIL_ALERTER.SendEmail(
            email_address,
            "GRR server",
            "Client %s reported a crash." % client_id,
            body,
            is_html=True,
        )
      except email_alerts.EmailNotSentError as e:
        # We have already written the crash details to the DB, so failing
        # to send an email isn't super-critical.
        logging.warning(e)


# TODO: Remove by EOY2024.
class ClientStatsHandler(message_handlers.MessageHandler):

  handler_name = "StatsHandler"

  def ProcessMessages(
      self, msgs: Sequence[rdf_objects.MessageHandlerRequest]
  ) -> None:
    # Keeping this for compatibility with legacy clients who still send stat
    # messages. Without this stub handler, there would be an error message
    # logged for every incoming StatsHandler request.
    pass


class RecursiveBlobUploadMixin:
  """Mixin for flows that upload blobs by executing same client action."""

  def GenerateUploadRequest(
      self, offset: int, file_size: int, blob: rdf_crypto.SignedBlob
  ) -> tuple[pb_message.Message, type[server_stubs.ClientActionStub]]:
    raise NotImplementedError()

  def StartBlobsUpload(
      self, binary_id: objects_pb2.SignedBinaryID, next_state: str
  ):
    """Starts recursive blobs upload for a given binary_id.

    Args:
      binary_id: Binary id of the binary that should be uploaded to the client.
      next_state: Name of the state to be triggered when the upload is complete.
    """

    # Fail early if the file is not there or empty.
    try:
      file_size = signed_binary_utils.FetchSizeOfSignedBinary(binary_id)
    except signed_binary_utils.SignedBinaryNotFoundError as ex:
      raise flow_base.FlowError(f"File {binary_id} not found.") from ex

    if file_size == 0:
      raise flow_base.FlowError(f"File {binary_id} is empty.")

    self.CallStateInlineProto(
        next_state=self.NextBlob.__name__,
        request_data={
            "binary_id": mig_objects.ToRDFSignedBinaryID(binary_id),
            "blob_index": 0,
            "file_offset": 0,
            "file_size": file_size,
            "next_state": next_state,
        },
    )

  @flow_base.UseProto2AnyResponses
  def NextBlob(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """Handles a successfully uploaded blob."""

    if not responses.success:
      raise flow_base.FlowError(
          f"Error while sending blobs: {responses.status})"
      )

    binary_id = responses.request_data["binary_id"]
    blob_index = responses.request_data["blob_index"]
    file_offset = responses.request_data["file_offset"]
    file_size = responses.request_data["file_size"]
    next_state = responses.request_data["next_state"]

    blob = signed_binary_utils.FetchBlobForSignedBinaryByID(
        mig_objects.ToProtoSignedBinaryID(binary_id), blob_index
    )
    more_data = file_offset + len(blob.data) < file_size

    request, client_action = self.GenerateUploadRequest(
        file_offset, file_size, blob
    )
    request_data = {
        "binary_id": binary_id,
        "blob_index": blob_index + 1,
        "file_offset": file_offset + len(blob.data),
        "file_size": file_size,
        "next_state": next_state,
    }
    self.CallClientProto(
        client_action,
        request,
        next_state=self.NextBlob.__name__ if more_data else next_state,
        request_data=request_data if more_data else {},
    )


class DeleteGRRTempFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.DeleteGRRTempFilesArgs
  rdf_deps = [
      rdf_paths.PathSpec,
  ]


class DeleteGRRTempFiles(
    flow_base.FlowBase[
        flows_pb2.DeleteGRRTempFilesArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Delete all the GRR temp files in path.

  If path is a directory, look in the top level for filenames beginning with
  Client.tempfile_prefix, and delete them.

  If path is a regular file and starts with Client.tempfile_prefix, delete it.
  """

  category = "/Administrative/"
  args_type = DeleteGRRTempFilesArgs
  proto_args_type = flows_pb2.DeleteGRRTempFilesArgs
  only_protos_allowed = True

  def Start(self):
    """Issue a request to delete tempfiles in directory."""
    self.CallClientProto(
        server_stubs.DeleteGRRTempFiles,
        self.proto_args.pathspec,
        next_state=self.Done.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def Done(self, responses: flow_responses.Responses[any_pb2.Any]):
    if not responses.success:
      raise flow_base.FlowError(str(responses.status))

    for response in responses:
      log = jobs_pb2.LogMessage()
      response.Unpack(log)
      self.Log(log.data)


class Kill(flow_base.FlowBase):
  """Terminate a running client (does not disable, just kill)."""

  category = "/Administrative/"
  only_protos_allowed = True

  def Start(self):
    """Call the kill function on the client."""
    self.CallClientProto(
        server_stubs.Kill, next_state=self.Confirmation.__name__
    )

  @flow_base.UseProto2AnyResponses
  def Confirmation(self, responses: flow_responses.Responses[any_pb2.Any]):
    """Confirmation of kill."""
    if not responses.success:
      self.Log("Kill failed on the client.")


class ExecutePythonHackArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ExecutePythonHackArgs
  rdf_deps = [
      rdf_protodict.Dict,
  ]


class ExecutePythonHackResult(rdf_structs.RDFProtoStruct):

  protobuf = flows_pb2.ExecutePythonHackResult
  rdf_deps = []


class ExecutePythonHack(
    flow_base.FlowBase[
        flows_pb2.ExecutePythonHackArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Execute a signed python hack on a client."""

  category = "/Administrative/"
  args_type = ExecutePythonHackArgs
  result_types = (ExecutePythonHackResult,)
  proto_args_type = flows_pb2.ExecutePythonHackArgs
  proto_result_types = (flows_pb2.ExecutePythonHackResult,)
  only_protos_allowed = True

  def Start(self):
    """The start method."""
    python_hack_urn = signed_binary_utils.GetAFF4PythonHackRoot().Add(
        self.args.hack_name
    )

    try:
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
          python_hack_urn
      )
    except signed_binary_utils.SignedBinaryNotFoundError as ex:
      raise flow_base.FlowError(
          "Python hack %s not found." % self.args.hack_name
      ) from ex

    # TODO(amoser): This will break if someone wants to execute lots of Python.
    for python_blob in blob_iterator:
      self.CallClientProto(
          server_stubs.ExecutePython,
          mig_client_action.ToProtoExecutePythonRequest(
              rdf_client_action.ExecutePythonRequest(
                  python_code=python_blob,
                  py_args=self.args.py_args,
              )
          ),
          next_state=self.Done.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def Done(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
    """Retrieves the output for the hack."""
    response_any = responses.First()
    if not responses.success:
      raise flow_base.FlowError(
          "Execute Python hack failed: %s" % responses.status
      )
    if response_any:
      response = jobs_pb2.ExecutePythonResponse()
      response_any.Unpack(response)
      result = response.return_val
      # Send reply with full data, but only log the first 200 bytes.
      str_result = result[0:200]
      if len(result) >= 200:
        str_result += "...[truncated]"
      self.Log("Result: %s", str_result)

      result = flows_pb2.ExecutePythonHackResult()
      result.result_string = response.return_val
      self.SendReplyProto(result)


class OnlineNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.OnlineNotificationArgs
  rdf_deps = [
      rdf_standard.DomainEmailAddress,
  ]


class OnlineNotification(
    flow_base.FlowBase[
        flows_pb2.OnlineNotificationArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Notifies by email when a client comes online in GRR."""

  category = "/Administrative/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  subject_template = jinja2.Template(
      "GRR Client on {{ hostname }} became available.", autoescape=True
  )
  template = jinja2.Template(
      """
<html><body><h1>GRR Client Online Notification.</h1>

<p>
  Client {{ client_id }} ({{ hostname }}) just came online. Click
  <a href='{{ admin_ui }}/v2{{ url }}'>here</a> to access this machine.
  <br />This notification was created by {{ creator }}.
</p>

<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
      autoescape=True,
  )

  args_type = OnlineNotificationArgs
  proto_args_type = flows_pb2.OnlineNotificationArgs
  only_protos_allowed = True

  # TODO: Review this method.
  @classmethod
  def GetDefaultArgs(cls, username=None):
    """Returns an args rdfvalue prefilled with sensible default values."""
    args = cls.args_type()
    try:
      user = data_store.REL_DB.ReadGRRUser(username)
      args.email = models_users.GetEmail(user)
    except ValueError:
      # Just set no default if the email is not well-formed. Example: when
      # username contains '@' character.
      pass

    return args

  def Start(self):
    """Starts processing."""
    if self.proto_args.email is None:
      self.proto_args.email = self.creator
    self.CallClientProto(
        server_stubs.Echo,
        jobs_pb2.EchoRequest(data="Ping"),
        next_state=self.SendMail.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def SendMail(self, responses: flow_responses.Responses[any_pb2.Any]) -> None:
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
        url=f"/clients/{self.client_id}",
        creator=self.creator,
        signature=utils.SmartUnicode(config.CONFIG["Email.signature"]),
    )

    email_alerts.EMAIL_ALERTER.SendEmail(
        self.proto_args.email, "grr-noreply", subject, body, is_html=True
    )


class UpdateClientArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.UpdateClientArgs
  rdf_deps = []


class UpdateClient(
    RecursiveBlobUploadMixin,
    flow_base.FlowBase[
        flows_pb2.UpdateClientArgs,
        flows_pb2.UpdateClientStore,
        flows_pb2.DefaultFlowProgress,
    ],
):
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
  result_types = (rdf_client_action.ExecuteBinaryResponse,)

  proto_args_type = flows_pb2.UpdateClientArgs
  proto_store_type = flows_pb2.UpdateClientStore
  proto_result_types = (jobs_pb2.ExecuteBinaryResponse,)
  only_protos_allowed = True

  def GenerateUploadRequest(
      self, offset: int, file_size: int, blob: rdf_crypto.SignedBlob
  ) -> tuple[pb_message.Message, type[server_stubs.ClientActionStub]]:
    request = mig_client_action.ToProtoExecuteBinaryRequest(
        rdf_client_action.ExecuteBinaryRequest(
            executable=blob,
            offset=offset,
            write_path=self.store.write_path,
            more_data=(offset + len(blob.data) < file_size),
            use_client_env=False,
        )
    )

    return request, server_stubs.UpdateAgent

  @property
  def _binary_id(self):
    return objects_pb2.SignedBinaryID(
        binary_type=objects_pb2.SignedBinaryID.BinaryType.EXECUTABLE,
        path=self.proto_args.binary_path,
    )

  def Start(self):
    """Start."""
    if not self.proto_args.binary_path:
      raise flow_base.FlowError("Installer binary path is not specified.")

    binary_urn = rdfvalue.RDFURN(self.proto_args.binary_path)
    self.store.write_path = "%d_%s" % (time.time(), binary_urn.Basename())

    self.StartBlobsUpload(self._binary_id, self._ProcessBlobsUpload.__name__)

  @flow_base.UseProto2AnyResponses
  def _ProcessBlobsUpload(self, responses):
    if not responses.success:
      raise flow_base.FlowError(
          "Installer reported an error: %s" % responses.status
      )
    if not list(responses):
      return
    response_any = list(responses)[0]
    response = jobs_pb2.ExecuteBinaryResponse()
    response_any.Unpack(response)

    if response.exit_status != 0:
      raise flow_base.FlowError(
          f"Installer process failed with exit code {response.exit_status}"
          f"\nstdout: {response.stdout}"
          f"\nstderr: {response.stderr}"
      )
    self.Log("Installer finished running.")
    self.SendReplyProto(response)


class ClientAlertHandler(message_handlers.MessageHandler):
  """A listener for client messages."""

  handler_name = "ClientAlertHandler"

  mail_template = jinja2.Template(
      """
<html><body><h1>GRR client message received.</h1>

The client {{ client_id }} ({{ hostname }}) just sent a message:<br>
<br>
{{ message }}
<br>
Click <a href='{{ admin_ui }}v2#{{ url }}'>here</a> to access this machine.

<p>{{ signature }}</p>

</body></html>""",
      autoescape=True,
  )

  subject = "GRR client message received from %s."

  logline = "Client message from %s: %s"

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

    crash_details = jobs_pb2.ClientCrash(
        client_id=client_id,
        crash_message=message,
        timestamp=int(time.time() * 1e6),
        crash_type="Alert",
    )

    if client_info is not None:
      crash_details.client_info.CopyFrom(client_info)

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
          message=utils.SmartUnicode(message),
      )
      email_alerts.EMAIL_ALERTER.SendEmail(
          config.CONFIG["Monitoring.alert_email"],
          "GRR server",
          self.subject % client_id,
          body,
          is_html=True,
      )

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.SendEmail(message.client_id, message.request.payload.string)


class ClientStartupHandler(message_handlers.MessageHandler):
  """MessageHandler that is invoked when the GRR client process starts."""

  handler_name = "ClientStartupHandler"

  def ProcessMessages(self, msgs):
    for message in msgs:
      self.WriteClientStartupInfo(message.client_id, message.request.payload)

  def WriteClientStartupInfo(self, client_id, new_si):
    """Handle a startup event."""
    drift = rdfvalue.Duration.From(5, rdfvalue.MINUTES)

    current_si = data_store.REL_DB.ReadClientStartupInfo(client_id)
    if current_si is not None:
      current_si = mig_client.ToRDFStartupInfo(current_si)

    # We write the updated record if the client_info has any changes
    # or the boot time is more than 5 minutes different.
    if (
        not current_si
        or current_si.client_info != new_si.client_info
        or not current_si.boot_time
        or current_si.boot_time.AbsDiff(new_si.boot_time) > drift
    ):
      new_si_proto = mig_client.ToProtoStartupInfo(new_si)
      try:
        data_store.REL_DB.WriteClientStartupInfo(client_id, new_si_proto)
        labels = new_si.client_info.labels
        if labels:
          data_store.REL_DB.AddClientLabels(client_id, "GRR", labels)
          index = client_index.ClientIndex()
          index.AddClientLabels(client_id, labels)

        # Reset foreman rules check so active hunts can match against the new
        # data
        data_store.REL_DB.WriteClientMetadata(
            client_id,
            last_foreman=data_store.REL_DB.MinTimestamp(),
        )

      except db.UnknownClientError:
        # On first contact with a new client, this write will fail.
        logging.info("Can't write StartupInfo for unknown client %s", client_id)

    # We do the interrogate-needed check even if the startup info hasn't
    # changed. This is to accommodate for cases when an interrogation is
    # requested from the client by creating a temporary file.
    if self._IsInterrogateNeeded(client_id, current_si, new_si):
      flow.StartFlow(
          client_id=client_id,
          flow_cls=discovery.Interrogate,
          creator="GRRWorker",
      )

  def _IsInterrogateNeeded(
      self,
      client_id: str,
      current_si: Optional[rdf_client.StartupInfo],
      new_si: rdf_client.StartupInfo,
  ) -> bool:
    # Interrogate the client immediately after its version has been
    # updated or an interrogate was requested on the endpoint (by the user
    # creating a file in a predefined location).
    #
    # We also start interrogation for newly enrolled endpoints (when no prior
    # startup record is available).
    if not current_si:
      return True

    if (
        current_si.client_info.client_version
        == new_si.client_info.client_version
        and (not new_si.interrogate_requested)
    ):
      return False

    min_create_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        1, rdfvalue.HOURS
    )

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=client_id,
        min_create_time=min_create_time,
        include_child_flows=False,
    )

    # Do not start an Interrogate if another Interrogate has been started
    # recently and is not yet finished.
    for f in flows:
      if (
          f.flow_class_name == discovery.Interrogate.__name__
          and f.flow_state in (f.FlowState.UNSET, f.FlowState.RUNNING)
      ):
        return False

    return True


class LaunchBinaryArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.LaunchBinaryArgs
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class LaunchBinary(
    RecursiveBlobUploadMixin,
    flow_base.FlowBase[
        flows_pb2.LaunchBinaryArgs,
        flows_pb2.LaunchBinaryStore,
        flows_pb2.DefaultFlowProgress,
    ],
):
  """Launch a signed binary on a client."""

  category = "/Administrative/"

  args_type = LaunchBinaryArgs
  result_types = (rdf_client_action.ExecuteBinaryResponse,)

  proto_args_type = flows_pb2.LaunchBinaryArgs
  proto_store_type = flows_pb2.LaunchBinaryStore
  proto_result_types = (jobs_pb2.ExecuteBinaryResponse,)
  only_protos_allowed = True

  def GenerateUploadRequest(
      self, offset: int, file_size: int, blob: rdf_crypto.SignedBlob
  ) -> tuple[pb_message.Message, type[server_stubs.ClientActionStub]]:
    # RecursiveBlobUploadMixin expected this function to be overridden.
    request = mig_client_action.ToProtoExecuteBinaryRequest(
        rdf_client_action.ExecuteBinaryRequest(
            executable=blob,
            args=shlex.split(self.proto_args.command_line),
            offset=offset,
            write_path=self.store.write_path,
            use_client_env=False,
            more_data=(offset + len(blob.data) < file_size),
        )
    )

    return request, server_stubs.ExecuteBinaryCommand

  def Start(self):
    """The start method."""
    if not self.proto_args.binary:
      raise flow_base.FlowError("Please specify a binary.")

    binary_urn = rdfvalue.RDFURN(self.args.binary)
    self.store.write_path = "%d_%s" % (time.time(), binary_urn.Basename())

    self.StartBlobsUpload(
        signed_binary_utils.SignedBinaryIDFromURN(binary_urn),
        self._ProcessBlobsUpload.__name__,
    )

  def _SanitizeOutput(self, data: bytes) -> str:
    if len(data) > 2000:
      result = data[:2000] + "... [truncated]".encode("utf-8")
    else:
      result = data

    # Output can contain arbitrary bytes. Since the goal is to produce readable
    # logs, we simply ignore weird characters.
    return result.decode("utf-8", "ignore")

  @flow_base.UseProto2AnyResponses
  def _ProcessBlobsUpload(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if not responses.success:
      raise IOError(responses.status)
    if not list(responses):
      return

    response_any = list(responses)[0]
    response = jobs_pb2.ExecuteBinaryResponse()
    response_any.Unpack(response)

    self.Log("Stdout: %s", self._SanitizeOutput(response.stdout))
    self.Log("Stderr: %s", self._SanitizeOutput(response.stderr))

    self.SendReplyProto(response)
