#!/usr/bin/env python
"""API handlers for user-related data and actions."""

import collections
import email
import itertools
import logging
from typing import Iterable, Optional, Sequence, Union

import jinja2

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_proto import objects_pb2
from grr_response_proto import user_pb2
from grr_response_proto.api import hunt_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import access_control
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow
from grr_response_server import notification as notification_lib
from grr_response_server.databases import db
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import approval_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt
from grr_response_server.models import clients
from grr_response_server.models import protobuf_utils
from grr_response_server.models import users
from grr_response_server.rdfvalues import mig_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects


class ApprovalNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a specific approval object could not be found."""


class GUISettings(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.GUISettings


class ApiNotificationClientReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationClientReference
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiNotificationHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationHuntReference
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiNotificationCronReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationCronReference
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiNotificationFlowReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationFlowReference
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiNotificationVfsReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationVfsReference
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiNotificationClientApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationClientApprovalReference
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiNotificationHuntApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationHuntApprovalReference
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiNotificationCronJobApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationCronJobApprovalReference
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiNotificationUnknownReference(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiNotificationUnknownReference
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class ApiNotificationReference(rdf_structs.RDFProtoStruct):
  """Object reference used in ApiNotifications."""

  protobuf = api_user_pb2.ApiNotificationReference
  rdf_deps = [
      ApiNotificationClientReference,
      ApiNotificationClientApprovalReference,
      ApiNotificationCronJobApprovalReference,
      ApiNotificationCronReference,
      ApiNotificationFlowReference,
      ApiNotificationHuntApprovalReference,
      ApiNotificationHuntReference,
      ApiNotificationUnknownReference,
      ApiNotificationVfsReference,
  ]


def InitApiNotificationReferenceFromObjectReference(
    reference: objects_pb2.ObjectReference,
) -> api_user_pb2.ApiNotificationReference:
  """Initializes ApiNotificationReference from an ObjectReference."""

  api_reference = api_user_pb2.ApiNotificationReference()

  if reference.reference_type == objects_pb2.ObjectReference.Type.UNSET:
    api_reference.type = api_reference.Type.UNSET

  elif reference.reference_type == objects_pb2.ObjectReference.CLIENT:
    api_reference.type = api_reference.Type.CLIENT
    api_reference.client.client_id = reference.client.client_id

  elif reference.reference_type == objects_pb2.ObjectReference.HUNT:
    api_reference.type = api_reference.Type.HUNT
    api_reference.hunt.hunt_id = reference.hunt.hunt_id

  elif reference.reference_type == objects_pb2.ObjectReference.FLOW:
    api_reference.type = api_reference.Type.FLOW
    api_reference.flow.client_id = reference.flow.client_id
    api_reference.flow.flow_id = reference.flow.flow_id

  elif reference.reference_type == objects_pb2.ObjectReference.CRON_JOB:
    api_reference.type = api_reference.Type.CRON
    api_reference.cron.cron_job_id = reference.cron_job.cron_job_id

  elif reference.reference_type == objects_pb2.ObjectReference.VFS_FILE:
    api_reference.type = api_reference.Type.VFS
    api_reference.vfs.client_id = reference.vfs_file.client_id

    if reference.vfs_file.path_type == objects_pb2.PathInfo.PathType.UNSET:
      raise ValueError(
          "Can't init from VFS_FILE object reference with unset path_type."
      )

    api_reference.vfs.vfs_path = rdf_objects.VfsFileReferenceToPath(
        reference.vfs_file
    )

  elif reference.reference_type == objects_pb2.ObjectReference.APPROVAL_REQUEST:
    ref_ar = reference.approval_request

    if (
        ref_ar.approval_type
        == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_NONE
    ):
      raise ValueError(
          "Can't init from APPROVAL_REQUEST object reference "
          "with unset approval_type."
      )
    elif (
        ref_ar.approval_type
        == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
    ):
      api_reference.type = api_reference.Type.CLIENT_APPROVAL
      api_reference.client_approval.approval_id = ref_ar.approval_id
      api_reference.client_approval.username = ref_ar.requestor_username
      api_reference.client_approval.client_id = ref_ar.subject_id
    elif (
        ref_ar.approval_type
        == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
    ):
      api_reference.type = api_reference.Type.HUNT_APPROVAL
      api_reference.hunt_approval.approval_id = ref_ar.approval_id
      api_reference.hunt_approval.username = ref_ar.requestor_username
      api_reference.hunt_approval.hunt_id = ref_ar.subject_id
    elif (
        ref_ar.approval_type
        == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
    ):
      api_reference.type = api_reference.Type.CRON_JOB_APPROVAL
      api_reference.cron_job_approval.approval_id = ref_ar.approval_id
      api_reference.cron_job_approval.username = ref_ar.requestor_username
      api_reference.cron_job_approval.cron_job_id = ref_ar.subject_id
    else:
      raise ValueError("Unexpected approval type: %d" % ref_ar.approval_type)
  else:
    raise ValueError("Unexpected reference type: %d" % reference.reference_type)

  return api_reference


class ApiNotification(rdf_structs.RDFProtoStruct):
  """Represents a user notification."""

  protobuf = api_user_pb2.ApiNotification
  rdf_deps = [
      ApiNotificationReference,
      rdfvalue.RDFDatetime,
  ]


def InitApiNotificationFromUserNotification(
    notification: objects_pb2.UserNotification,
) -> api_user_pb2.ApiNotification:
  """Initializes an ApiNotification from a UserNotification."""

  api_notification = api_user_pb2.ApiNotification()
  protobuf_utils.CopyAttr(notification, api_notification, "timestamp")
  protobuf_utils.CopyAttr(notification, api_notification, "notification_type")
  protobuf_utils.CopyAttr(notification, api_notification, "message")
  api_notification.is_pending = (
      notification.state == objects_pb2.UserNotification.State.STATE_PENDING
  )
  try:
    api_notification.reference.CopyFrom(
        InitApiNotificationReferenceFromObjectReference(notification.reference)
    )
  except ValueError as e:
    logging.exception(
        "Can't initialize notification from an object reference: %s", e
    )
    # In case of any initialization issue, simply create an empty reference.
    api_notification.reference.CopyFrom(
        api_user_pb2.ApiNotificationReference(
            type=api_user_pb2.ApiNotificationReference.Type.UNSET
        )
    )

  return api_notification


def InitApiGrrUserFromGrrUser(
    user: objects_pb2.GRRUser,
) -> api_user_pb2.ApiGrrUser:
  """Initializes ApiGrrUser from a GRRUser."""

  api_user = api_user_pb2.ApiGrrUser()
  api_user.username = user.username

  if user.user_type == objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN:
    api_user.user_type = api_user.UserType.USER_TYPE_ADMIN
  else:
    api_user.user_type = api_user.UserType.USER_TYPE_STANDARD

  # Intentionally set default values if the user has no settings set.
  api_user.settings.mode = user.ui_mode
  api_user.settings.canary_mode = user.canary_mode

  if config.CONFIG.Get("Email.enable_custom_email_address") and user.email:
    api_user.email = user.email

  return api_user


class ApiGrrUserInterfaceTraits(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGrrUserInterfaceTraits


class ApiGrrUser(rdf_structs.RDFProtoStruct):
  """API object describing the user."""

  protobuf = api_user_pb2.ApiGrrUser
  rdf_deps = [
      ApiGrrUserInterfaceTraits,
      GUISettings,
  ]


def InitApiHuntApprovalFromApprovalRequest(
    approval_request: objects_pb2.ApprovalRequest,
) -> api_user_pb2.ApiHuntApproval:
  """Initializes ApiHuntApproval from an ApprovalRequest."""
  api_hunt_approval = api_user_pb2.ApiHuntApproval()

  _FillApiApprovalFromApprovalRequest(api_hunt_approval, approval_request)

  approval_subject_obj = data_store.REL_DB.ReadHuntObject(
      approval_request.subject_id
  )

  approval_subject_counters = data_store.REL_DB.ReadHuntCounters(
      approval_request.subject_id
  )
  api_hunt_approval.subject.CopyFrom(
      api_hunt.InitApiHuntFromHuntObject(
          approval_subject_obj,
          hunt_counters=approval_subject_counters,
          with_full_summary=True,
      )
  )
  original_object = approval_subject_obj.original_object

  if (
      original_object.object_type
      == hunt_pb2.ApiFlowLikeObjectReference.ObjectType.FLOW_REFERENCE
  ):
    original_flow = data_store.REL_DB.ReadFlowObject(
        original_object.flow_reference.client_id,
        original_object.flow_reference.flow_id,
    )
    api_hunt_approval.copied_from_flow.CopyFrom(
        api_flow.InitApiFlowFromFlowObject(original_flow)
    )

  elif (
      original_object.object_type
      == hunt_pb2.ApiFlowLikeObjectReference.ObjectType.HUNT_REFERENCE
  ):
    original_hunt = data_store.REL_DB.ReadHuntObject(
        original_object.hunt_reference.hunt_id
    )
    original_hunt_counters = data_store.REL_DB.ReadHuntCounters(
        original_object.hunt_reference.hunt_id
    )
    api_hunt_approval.copied_from_hunt.CopyFrom(
        api_hunt.InitApiHuntFromHuntObject(
            original_hunt,
            hunt_counters=original_hunt_counters,
            with_full_summary=True,
        )
    )

  return api_hunt_approval


def InitApiClientApprovalFromApprovalRequest(
    approval_request: objects_pb2.ApprovalRequest,
) -> api_user_pb2.ApiClientApproval:
  """Initializes ApiClientApproval from an ApprovalRequest."""

  api_client_approval = api_user_pb2.ApiClientApproval()

  client_full_info = data_store.REL_DB.ReadClientFullInfo(
      approval_request.subject_id
  )
  api_client_approval.subject.CopyFrom(
      clients.ApiClientFromClientFullInfo(
          approval_request.subject_id, client_full_info
      )
  )

  _FillApiApprovalFromApprovalRequest(api_client_approval, approval_request)
  return api_client_approval


def InitApiCronJobApprovalFromApprovalRequest(
    approval_request: objects_pb2.ApprovalRequest,
) -> api_user_pb2.ApiCronJobApproval:
  """Initializes ApiCronJobApproval from an ApprovalRequest."""

  api_cron_job_approval = api_user_pb2.ApiCronJobApproval()
  _FillApiApprovalFromApprovalRequest(api_cron_job_approval, approval_request)

  approval_subject_obj = cronjobs.CronManager().ReadJob(
      approval_request.subject_id
  )
  approval_subject_obj = mig_cronjobs.ToProtoCronJob(approval_subject_obj)
  api_cron_job_approval.subject.CopyFrom(
      api_cron.InitApiCronJobFromCronJob(approval_subject_obj)
  )

  return api_cron_job_approval


def _FillApiApprovalFromApprovalRequest(
    api_approval: Union[
        api_user_pb2.ApiClientApproval,
        api_user_pb2.ApiHuntApproval,
        api_user_pb2.ApiCronJobApproval,
    ],
    approval_request: objects_pb2.ApprovalRequest,
):
  """Fills a given Api(Client|Hunt|CronJob)Approval with data from an ApprovalRequest."""

  protobuf_utils.CopyAttr(approval_request, api_approval, "approval_id", "id")
  protobuf_utils.CopyAttr(
      approval_request, api_approval, "requestor_username", "requestor"
  )
  protobuf_utils.CopyAttr(approval_request, api_approval, "reason", "reason")
  protobuf_utils.CopyAttr(approval_request, api_approval, "email_message_id")

  api_approval.notified_users.extend(sorted(approval_request.notified_users))
  api_approval.email_cc_addresses.extend(
      sorted(approval_request.email_cc_addresses)
  )

  api_approval.approvers.extend(
      sorted([g.grantor_username for g in approval_request.grants])
  )
  # TODO(user): Remove this once Cron jobs are removed.
  if not isinstance(api_approval, api_user_pb2.ApiCronJobApproval):
    protobuf_utils.CopyAttr(
        approval_request, api_approval, "expiration_time", "expiration_time_us"
    )

  try:
    approval_checks.CheckApprovalRequest(approval_request)
    api_approval.is_valid = True
  except access_control.UnauthorizedAccess as e:
    api_approval.is_valid_message = str(e)
    api_approval.is_valid = False

  return api_approval


def GetSubjectTitleForHuntApproval(
    approval: api_user_pb2.ApiHuntApproval,
) -> str:
  """Returns a human-readable title for a hunt approval."""
  return f"hunt {approval.subject.hunt_id}"


def GetSubjectTitleForCronJobApproval(
    approval: api_user_pb2.ApiCronJobApproval,
) -> str:
  """Returns a human-readable title for a cron job approval."""
  return f"a cron job {approval.subject.cron_job_id}"


def GetSubjectTitleForClientApproval(
    approval: api_user_pb2.ApiClientApproval,
) -> str:
  """Returns a human-readable title for a client approval."""
  return (
      f"GRR client {approval.subject.client_id} "
      f"({approval.subject.knowledge_base.fqdn})"
  )


class ApiClientApproval(rdf_structs.RDFProtoStruct):
  """API client approval object."""

  protobuf = api_user_pb2.ApiClientApproval
  rdf_deps = [
      api_client.ApiClient,
      rdfvalue.RDFDatetime,
  ]

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.client_id),
            requestor_username=self.requestor,
        ),
    )


class ApiHuntApproval(rdf_structs.RDFProtoStruct):
  """API hunt approval object."""

  protobuf = api_user_pb2.ApiHuntApproval
  rdf_deps = [
      api_flow.ApiFlow,
      api_hunt.ApiHunt,
      rdfvalue.RDFDatetime,
  ]

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.hunt_id),
            requestor_username=self.requestor,
        ),
    )


class ApiCronJobApproval(rdf_structs.RDFProtoStruct):
  """API cron job approval object."""

  protobuf = api_user_pb2.ApiCronJobApproval
  rdf_deps = [
      api_cron.ApiCronJob,
  ]

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.cron_job_id),
            requestor_username=self.requestor,
        ),
    )


class ApiCreateHuntApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiCreateHuntApprovalArgs
  rdf_deps = [
      ApiHuntApproval,
      api_hunt.ApiHuntId,
  ]


class ApiGetHuntApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGetHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiCreateCronJobApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiCreateCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
      ApiCronJobApproval,
  ]


class ApiGetCronJobApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGetCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiCreateClientApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiCreateClientApprovalArgs
  rdf_deps = [
      ApiClientApproval,
      api_client.ApiClientId,
  ]


class ApiGetClientApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGetClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiListClientApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListClientApprovalsArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


_EMAIL_HEADER = """
  <!doctype html>
  <html>
    <head>
      <meta name="viewport" content="width=device-width" />
      <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
      <style type="test/css">
        .button {
          border: 1px solid;
          border-radius: 4px;
          display: inline-block;
          margin-right: 1em;
          padding: .7em 1.2em;
          text-decoration: none;
        }
      </style>
    </head>
    <body>
"""

_EMAIL_FOOTER = """
      <p>Thanks,</p>
      <p>{{ text_signature }}</p>
      <p>{{ html_signature|safe }}</p>
    </body>
  </html>
"""

_APPROVAL_REQUESTED_TEMPLATE = _EMAIL_HEADER + """
  <p>
    You have been asked to review and grant the following approval in GRR
    Rapid Response:
  </p>

  <table>
    <tr>
      <td><strong>Requested by:</strong></td>
      <td>{{ requestor }}</td>
    </tr>
    <tr>
      <td><strong>Subject:</strong></td>
      <td><a href="{{ approval_url}}">{{ subject_title }}</a></td>
    </tr>
    <tr>
      <td><strong>Reason:</strong></td>
      <td>{{ reason }}</td>
    </tr>
  </table>
  <p>
    <a href="{{ approval_url }}" class="button">Review approval request</a>
    {% if legacy_approval_url %}
    (or <a href="{{ legacy_approval_url }}">review in legacy UI</a>)
    {% endif %}
  </p>
""" + _EMAIL_FOOTER

_APPROVAL_GRANTED_TEMPLATE = _EMAIL_HEADER + """
  <p>
    Access has been granted:
  </p>

  <table>
    <tr>
      <td><strong>Requested by:</strong></td>
      <td>{{ requestor }}</td>
    </tr>
    <tr>
      <td><strong>Subject:</strong></td>
      <td><a href="{{ subject_url}}">{{ subject_title }}</a></td>
    </tr>
    <tr>
      <td><strong>Reason:</strong></td>
      <td>{{ reason }}</td>
    </tr>
    <tr>
      <td><strong>Granted by:</strong></td>
      <td>{{ grantor }}</td>
    </tr>
  </table>

  <p>
    <a href="{{ subject_url }}" class="button">Go to {{ subject_title }}</a>
    {% if legacy_subject_url %}
    (or <a href="{{ legacy_subject_url }}">view in legacy UI</a>)
    {% endif %}
  </p>
""" + _EMAIL_FOOTER


def CreateApprovalRequest(
    args: Union[
        api_user_pb2.ApiCreateClientApprovalArgs,
        api_user_pb2.ApiCreateCronJobApprovalArgs,
        api_user_pb2.ApiCreateHuntApprovalArgs,
    ],
    approval_type: objects_pb2.ApprovalRequest.ApprovalType,
    subject_id: str,
    expiration_time: rdfvalue.RDFDatetime,
    context: api_call_context.ApiCallContext,
) -> objects_pb2.ApprovalRequest:
  """Creates an approval request.

  Args:
    args: The API call arguments.
    approval_type: The type of the approval request.
    subject_id: The subject ID of the approval request.
    expiration_time: The expiration time of the approval request.
    context: The API call context.

  Returns:
    The created approval request.

  Raises:
    ValueError: If the approval reason is empty.
  """

  if not args.approval.reason:
    raise ValueError("Empty approval reason")

  request = objects_pb2.ApprovalRequest(
      requestor_username=context.username,
      approval_type=approval_type,
      reason=args.approval.reason,
      notified_users=args.approval.notified_users,
      email_cc_addresses=args.approval.email_cc_addresses,
      subject_id=subject_id,
      expiration_time=int(expiration_time),
      email_message_id=email.utils.make_msgid(),
  )
  request.approval_id = data_store.REL_DB.WriteApprovalRequest(request)

  data_store.REL_DB.GrantApproval(
      approval_id=request.approval_id,
      requestor_username=context.username,
      grantor_username=context.username,
  )

  return GetApprovalRequest(request.approval_id, context.username)


def GetApprovalRequest(
    approval_id: str,
    username: str,
) -> objects_pb2.ApprovalRequest:
  """Gets an approval request, raises if not found.

  Args:
    approval_id: The approval ID to look for.
    username: The username of the user that is requesting the approval.

  Returns:
    The approval request.

  Raises:
    ApprovalNotFoundError: If the approval could not be found.
  """

  try:
    approval_request = data_store.REL_DB.ReadApprovalRequest(
        username, approval_id
    )
  except db.UnknownApprovalRequestError as ex:
    raise ApprovalNotFoundError(
        "No approval with (id=%s, username=%s) could be found."
        % (approval_id, username)
    ) from ex
  return approval_request


def GrantApprovalRequest(
    approval_id: str,
    requestor_username: str,
    grantor_username: str,
) -> objects_pb2.ApprovalRequest:
  """Grants an approval request.

  Args:
    approval_id: The approval ID to grant.
    requestor_username: The username of the user that is requesting the
      approval.
    grantor_username: The username of the user that is granting the approval.

  Returns:
    The approval request.

  Raises:
    ValueError: If the username is empty.
    ApprovalNotFoundError: If the approval could not be found.
  """
  if not requestor_username:
    raise ValueError("Empty requestor username")

  data_store.REL_DB.GrantApproval(
      requestor_username, approval_id, grantor_username
  )

  return GetApprovalRequest(approval_id, requestor_username)


def SendApprovalRequestEmail(
    approval: Union[
        api_user_pb2.ApiClientApproval,
        api_user_pb2.ApiHuntApproval,
        api_user_pb2.ApiCronJobApproval,
    ],
    subject_title: str,
    review_url_path: str,
    review_url_path_legacy: str,
) -> None:
  """Sends a emails about a given approval request."""

  if not config.CONFIG.Get("Email.send_approval_emails"):
    return

  subject_template = jinja2.Template(
      "Approval for {{ user }} to access {{ subject }}.", autoescape=True
  )
  subject = subject_template.render(
      user=approval.requestor, subject=subject_title
  )

  template = jinja2.Template(_APPROVAL_REQUESTED_TEMPLATE, autoescape=True)
  base_url = config.CONFIG["AdminUI.url"].rstrip("/") + "/"
  legacy_approval_url = base_url + review_url_path_legacy.lstrip("/")
  approval_url = base_url + review_url_path.lstrip("/")

  if approval_url == legacy_approval_url:
    # In case the new UI does not yet support approval reviews for the given
    # subject type (client, hunt, cronjob), hide the fallback link to the
    # old UI in the email template. Instead, clicking the main button will
    # link the user to the old UI.
    legacy_approval_url = None

  body = template.render(
      requestor=approval.requestor,
      reason=approval.reason,
      legacy_approval_url=legacy_approval_url,
      approval_url=approval_url,
      subject_title=subject_title,
      # If you feel like it, add a cute dog picture here :)
      html_signature=config.CONFIG["Email.approval_signature"],
      text_signature=config.CONFIG["Email.signature"],
  )

  requestor_email = users.GetEmail(
      data_store.REL_DB.ReadGRRUser(approval.requestor)
  )
  notified_emails = []
  for user in approval.notified_users:
    user = data_store.REL_DB.ReadGRRUser(user)
    notified_emails.append(users.GetEmail(user))

  email_alerts.EMAIL_ALERTER.SendEmail(
      to_addresses=",".join(notified_emails),
      from_address=requestor_email,
      subject=subject,
      message=body,
      is_html=True,
      cc_addresses=",".join(approval.email_cc_addresses),
      message_id=approval.email_message_id,
  )


def SendGrantEmail(
    approval: Union[
        api_user_pb2.ApiClientApproval,
        api_user_pb2.ApiHuntApproval,
        api_user_pb2.ApiCronJobApproval,
    ],
    username: str,
    subject_title: str,
    subject_url_path: str,
    subject_url_path_legacy: str,
) -> None:
  """Sends an email about a granted approval request."""

  if not config.CONFIG.Get("Email.send_approval_emails"):
    return

  subject_template = jinja2.Template(
      "Approval for {{ user }} to access {{ subject }}.", autoescape=True
  )
  subject = subject_template.render(
      user=approval.requestor, subject=subject_title
  )

  template = jinja2.Template(_APPROVAL_GRANTED_TEMPLATE, autoescape=True)
  base_url = config.CONFIG["AdminUI.url"].rstrip("/") + "/"
  subject_url = base_url + subject_url_path.lstrip("/")
  legacy_subject_url = base_url + subject_url_path_legacy.lstrip("/")

  if subject_url == legacy_subject_url:
    # In case the new UI does not yet support showing the given subject type
    # (client, hunt, cronjob), hide the fallback link to the old UI in the
    # email template. Instead, clicking the main button will link the user to
    # the old UI.
    legacy_subject_url = None

  body = template.render(
      grantor=username,
      requestor=approval.requestor,
      reason=approval.reason,
      legacy_subject_url=legacy_subject_url,
      subject_url=subject_url,
      subject_title=subject_title,
      html_signature=config.CONFIG["Email.approval_signature"],
      text_signature=config.CONFIG["Email.signature"],
  )

  # Email subject should match approval request, and we add message id
  # references so they are grouped together in a thread by gmail.
  headers = {
      "In-Reply-To": approval.email_message_id,
      "References": approval.email_message_id,
  }

  requestor = data_store.REL_DB.ReadGRRUser(approval.requestor)
  requestor_email = users.GetEmail(requestor)
  user = data_store.REL_DB.ReadGRRUser(username)
  user_email = users.GetEmail(user)

  email_alerts.EMAIL_ALERTER.SendEmail(
      to_addresses=requestor_email,
      from_address=user_email,
      subject=subject,
      message=body,
      is_html=True,
      cc_addresses=",".join(approval.email_cc_addresses),
      headers=headers,
  )


def CreateApprovalNotification(
    approval: Union[
        ApiClientApproval,
        ApiHuntApproval,
        ApiCronJobApproval,
    ],
    notification_type: rdf_objects.UserNotification.Type,
    subject_title: str,
) -> None:
  """Creates a user notification for the given approval."""

  for user in approval.notified_users:
    try:
      notification_lib.Notify(
          user.strip(),
          notification_type,
          "Please grant access to %s" % subject_title,
          approval.ObjectReference(),
      )
    except db.UnknownGRRUserError:
      # The relational db does not allow sending notifications to users that
      # don't exist. This should happen rarely but we need to catch this case.
      logging.error("Notification sent for unknown user %s!", user.strip())


def _GetTokenExpirationTime() -> rdfvalue.RDFDatetime:
  return rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_expiry"]


def _FilterApiClientApprovals(
    api_client_approval: Iterable[ApiClientApproval],
    state: api_user_pb2.ApiListClientApprovalsArgs.State,
) -> Iterable[ApiClientApproval]:
  """Filters client approvals based on the given state."""

  for approval in api_client_approval:
    if state == api_user_pb2.ApiListClientApprovalsArgs.State.ANY:
      yield approval
    elif state == api_user_pb2.ApiListClientApprovalsArgs.State.VALID:
      if approval.is_valid:
        yield approval
    elif state == api_user_pb2.ApiListClientApprovalsArgs.State.INVALID:
      if not approval.is_valid:
        yield approval


class ApiCreateClientApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Creates new user client approval and notifies requested approvers."""

  args_type = ApiCreateClientApprovalArgs
  result_type = ApiClientApproval
  proto_args_type = api_user_pb2.ApiCreateClientApprovalArgs
  proto_result_type = api_user_pb2.ApiClientApproval

  def _CalculateExpiration(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
  ) -> rdfvalue.RDFDatetime:
    if not args.approval.expiration_time_us:
      return _GetTokenExpirationTime()

    approval_expiration_time = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
        args.approval.expiration_time_us
    )
    if rdfvalue.RDFDatetime.Now() > approval_expiration_time:
      raise ValueError(
          f"Requested expiration time {approval_expiration_time} "
          "is in the past."
      )

    if approval_expiration_time > (
        rdfvalue.RDFDatetime.Now() + config.CONFIG["ACL.token_max_expiry"]
    ):
      raise ValueError(
          f"Requested expiration time {approval_expiration_time} "
          "is too far in the future."
      )
    return approval_expiration_time

  def Handle(
      self,
      args: api_user_pb2.ApiCreateClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiClientApproval:
    assert context is not None

    approval_request = CreateApprovalRequest(
        args,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
        args.client_id,
        self._CalculateExpiration(args),
        context,
    )
    api_client_approval = InitApiClientApprovalFromApprovalRequest(
        approval_request
    )

    subject_title = GetSubjectTitleForClientApproval(api_client_approval)

    review_url_path = (
        f"/v2/clients/{api_client_approval.subject.client_id}/users/"
        f"{api_client_approval.requestor}/approvals/{api_client_approval.id}"
    )

    review_url_path_legacy = (
        f"/#/users/{api_client_approval.requestor}/approvals/client/"
        f"{api_client_approval.subject.client_id}/{api_client_approval.id}"
    )

    SendApprovalRequestEmail(
        api_client_approval,
        subject_title,
        review_url_path,
        review_url_path_legacy,
    )
    rdf_api_client_approval = ToRDFApiClientApproval(api_client_approval)
    CreateApprovalNotification(
        rdf_api_client_approval,
        rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_REQUESTED,
        subject_title,
    )
    return api_client_approval


class ApiGetClientApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Returns details about an approval for a given client and reason."""

  args_type = ApiGetClientApprovalArgs
  result_type = ApiClientApproval
  proto_args_type = api_user_pb2.ApiGetClientApprovalArgs
  proto_result_type = api_user_pb2.ApiClientApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGetClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiClientApproval:
    approval_request = GetApprovalRequest(args.approval_id, args.username)

    expected_approval_type = (
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
    )
    if approval_request.approval_type != expected_approval_type:
      raise ValueError(
          "Unexpected approval type: %s, expected: %s"
          % (approval_request.approval_type, expected_approval_type)
      )

    if approval_request.subject_id != args.client_id:
      raise ValueError(
          "Unexpected subject id: %s, expected: %s"
          % (approval_request.subject_id, args.client_id)
      )

    return InitApiClientApprovalFromApprovalRequest(approval_request)


class ApiGrantClientApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGrantClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiGrantClientApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Handle for GrantClientApproval requests."""

  args_type = ApiGrantClientApprovalArgs
  result_type = ApiClientApproval
  proto_args_type = api_user_pb2.ApiGrantClientApprovalArgs
  proto_result_type = api_user_pb2.ApiClientApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGrantClientApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiClientApproval:
    assert context is not None

    approval_request = GrantApprovalRequest(
        args.approval_id, args.username, context.username
    )
    api_client_approval = InitApiClientApprovalFromApprovalRequest(
        approval_request
    )
    subject_title = GetSubjectTitleForClientApproval(api_client_approval)

    SendGrantEmail(
        api_client_approval,
        context.username,
        subject_title,
        f"/v2/clients/{api_client_approval.subject.client_id}",
        f"#/clients/{api_client_approval.subject.client_id}",
    )

    rdf_api_client_approval = ToRDFApiClientApproval(api_client_approval)
    notification_lib.Notify(
        api_client_approval.requestor,
        rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED,
        "%s has granted you access to %s." % (context.username, subject_title),
        rdf_api_client_approval.subject.ObjectReference(),
    )

    if api_client_approval.is_valid:
      flow.StartScheduledFlows(
          client_id=api_client_approval.subject.client_id,
          creator=api_client_approval.requestor,
      )

    return api_client_approval


class ApiListClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListClientApprovalsResult
  rdf_deps = [
      ApiClientApproval,
  ]


class ApiListClientApprovalsHandler(api_call_handler_base.ApiCallHandler):
  """Returns list of user's clients approvals."""

  args_type = ApiListClientApprovalsArgs
  result_type = ApiListClientApprovalsResult
  proto_args_type = api_user_pb2.ApiListClientApprovalsArgs
  proto_result_type = api_user_pb2.ApiListClientApprovalsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListClientApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListClientApprovalsResult:
    assert context is not None

    subject_id = None
    if args.client_id:
      subject_id = args.client_id

    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=subject_id,
            include_expired=True,
        ),
        key=lambda ar: ar.timestamp,
        reverse=True,
    )
    api_client_approvals = [
        InitApiClientApprovalFromApprovalRequest(ar) for ar in approvals
    ]

    api_client_approvals = _FilterApiClientApprovals(
        api_client_approvals,
        args.state,
    )

    if not args.HasField("count"):
      end = None
    else:
      end = args.offset + args.count
    items = list(itertools.islice(api_client_approvals, args.offset, end))
    api_client.UpdateClientsFromFleetspeak([a.subject for a in items])

    return api_user_pb2.ApiListClientApprovalsResult(items=items)


class ApiCreateHuntApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Creates new user hunt approval and notifies requested approvers."""

  args_type = ApiCreateHuntApprovalArgs
  result_type = ApiHuntApproval
  proto_args_type = api_user_pb2.ApiCreateHuntApprovalArgs
  proto_result_type = api_user_pb2.ApiHuntApproval

  def Handle(
      self,
      args: api_user_pb2.ApiCreateHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiHuntApproval:
    assert context is not None

    approval_request = CreateApprovalRequest(
        args,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT,
        args.hunt_id,
        _GetTokenExpirationTime(),
        context,
    )
    api_hunt_approval = InitApiHuntApprovalFromApprovalRequest(approval_request)

    subject_title = GetSubjectTitleForHuntApproval(api_hunt_approval)
    review_url_path = (
        f"/v2/hunts/{api_hunt_approval.subject.hunt_id}/users/"
        f"{api_hunt_approval.requestor}/approvals/{api_hunt_approval.id}"
    )
    review_url_path_legacy = (
        f"/#/users/{api_hunt_approval.requestor}/approvals/hunt/"
        f"{api_hunt_approval.subject.hunt_id}/{api_hunt_approval.id}"
    )

    SendApprovalRequestEmail(
        api_hunt_approval,
        subject_title,
        review_url_path,
        review_url_path_legacy,
    )

    rdf_api_hunt_approval = ToRDFApiHuntApproval(api_hunt_approval)
    CreateApprovalNotification(
        rdf_api_hunt_approval,
        rdf_objects.UserNotification.Type.TYPE_HUNT_APPROVAL_REQUESTED,
        subject_title,
    )
    return api_hunt_approval


class ApiGetHuntApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Returns details about approval for a given hunt, user and approval id."""

  args_type = ApiGetHuntApprovalArgs
  result_type = ApiHuntApproval
  proto_args_type = api_user_pb2.ApiGetHuntApprovalArgs
  proto_result_type = api_user_pb2.ApiHuntApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGetHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiHuntApproval:
    approval_obj = GetApprovalRequest(args.approval_id, args.username)

    expected_approval_type = (
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
    )
    if approval_obj.approval_type != expected_approval_type:
      raise ValueError(
          "Unexpected approval type: %s, expected: %s"
          % (approval_obj.approval_type, expected_approval_type)
      )

    if approval_obj.subject_id != args.hunt_id:
      raise ValueError(
          "Unexpected subject id: %s, expected: %s"
          % (approval_obj.subject_id, args.hunt_id)
      )

    return InitApiHuntApprovalFromApprovalRequest(approval_obj)


class ApiGrantHuntApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGrantHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiGrantHuntApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Handle for GrantHuntApproval requests."""

  args_type = ApiGrantHuntApprovalArgs
  result_type = ApiHuntApproval
  proto_args_type = api_user_pb2.ApiGrantHuntApprovalArgs
  proto_result_type = api_user_pb2.ApiHuntApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGrantHuntApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiHuntApproval:
    assert context is not None

    approval_request = GrantApprovalRequest(
        args.approval_id, args.username, context.username
    )
    api_hunt_approval = InitApiHuntApprovalFromApprovalRequest(approval_request)

    subject_title = GetSubjectTitleForHuntApproval(api_hunt_approval)

    SendGrantEmail(
        api_hunt_approval,
        context.username,
        subject_title,
        f"/v2/hunts/{api_hunt_approval.subject.hunt_id}",
        f"#/hunts/{api_hunt_approval.subject.hunt_id}",
    )
    rdf_api_hunt_approval = ToRDFApiHuntApproval(api_hunt_approval)
    notification_lib.Notify(
        api_hunt_approval.requestor,
        rdf_objects.UserNotification.Type.TYPE_HUNT_APPROVAL_GRANTED,
        "%s has granted you access to %s." % (context.username, subject_title),
        rdf_api_hunt_approval.subject.ObjectReference(),
    )

    return api_hunt_approval


class ApiListHuntApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListHuntApprovalsArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiListHuntApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListHuntApprovalsResult
  rdf_deps = [
      ApiHuntApproval,
  ]


class ApiListHuntApprovalsHandler(api_call_handler_base.ApiCallHandler):
  """Returns list of user's hunts approvals."""

  args_type = ApiListHuntApprovalsArgs
  result_type = ApiListHuntApprovalsResult
  proto_args_type = api_user_pb2.ApiListHuntApprovalsArgs
  proto_result_type = api_user_pb2.ApiListHuntApprovalsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListHuntApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListHuntApprovalsResult:
    assert context is not None

    subject_id = None
    if args.hunt_id:
      subject_id = args.hunt_id

    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT,
            subject_id=subject_id,
            include_expired=True,
        ),
        key=lambda ar: ar.timestamp,
        reverse=True,
    )

    if not args.HasField("count"):
      end = None
    else:
      end = args.offset + args.count

    return api_user_pb2.ApiListHuntApprovalsResult(
        items=[
            InitApiHuntApprovalFromApprovalRequest(ar)
            for ar in approvals[args.offset : end]
        ]
    )


class ApiCreateCronJobApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Creates new user cron approval and notifies requested approvers."""

  args_type = ApiCreateCronJobApprovalArgs
  result_type = ApiCronJobApproval
  proto_args_type = api_user_pb2.ApiCreateCronJobApprovalArgs
  proto_result_type = api_user_pb2.ApiCronJobApproval

  def Handle(
      self,
      args: api_user_pb2.ApiCreateCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiCronJobApproval:
    assert context is not None

    approval_request = CreateApprovalRequest(
        args,
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
        args.cron_job_id,
        _GetTokenExpirationTime(),
        context,
    )
    api_cron_job_approval = InitApiCronJobApprovalFromApprovalRequest(
        approval_request
    )

    subject_title = GetSubjectTitleForCronJobApproval(api_cron_job_approval)
    review_url_path = review_url_path_legacy = (
        f"/#/users/{api_cron_job_approval.requestor}/approvals/cron-job/"
        f"{api_cron_job_approval.subject.cron_job_id}/{api_cron_job_approval.id}"
    )

    SendApprovalRequestEmail(
        api_cron_job_approval,
        subject_title,
        review_url_path,
        review_url_path_legacy,
    )
    rdf_api_cron_job_approval = ToRDFApiCronJobApproval(api_cron_job_approval)
    CreateApprovalNotification(
        rdf_api_cron_job_approval,
        rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_REQUESTED,
        subject_title,
    )

    return api_cron_job_approval


class ApiGetCronJobApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Returns details about approval for a given cron, user and approval id."""

  args_type = ApiGetCronJobApprovalArgs
  result_type = ApiCronJobApproval
  proto_args_type = api_user_pb2.ApiGetCronJobApprovalArgs
  proto_result_type = api_user_pb2.ApiCronJobApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGetCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiCronJobApproval:
    approval_obj = GetApprovalRequest(args.approval_id, args.username)

    expected_approval_type = (
        objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
    )
    if approval_obj.approval_type != expected_approval_type:
      raise ValueError(
          "Unexpected approval type: %s, expected: %s"
          % (approval_obj.approval_type, expected_approval_type)
      )

    if approval_obj.subject_id != args.cron_job_id:
      raise ValueError(
          "Unexpected subject id: %s, expected: %s"
          % (approval_obj.subject_id, args.cron_job_id)
      )

    return InitApiCronJobApprovalFromApprovalRequest(approval_obj)


class ApiGrantCronJobApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGrantCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiGrantCronJobApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Handle for GrantCronJobApproval requests."""

  args_type = ApiGrantCronJobApprovalArgs
  result_type = ApiCronJobApproval
  proto_args_type = api_user_pb2.ApiGrantCronJobApprovalArgs
  proto_result_type = api_user_pb2.ApiCronJobApproval

  def Handle(
      self,
      args: api_user_pb2.ApiGrantCronJobApprovalArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiCronJobApproval:
    assert context is not None

    approval_request = GrantApprovalRequest(
        args.approval_id, args.username, context.username
    )
    api_cron_job_approval = InitApiCronJobApprovalFromApprovalRequest(
        approval_request
    )
    subject_title = GetSubjectTitleForCronJobApproval(api_cron_job_approval)

    SendGrantEmail(
        api_cron_job_approval,
        context.username,
        subject_title,
        f"#/crons/{api_cron_job_approval.subject.cron_job_id}",
        f"#/crons/{api_cron_job_approval.subject.cron_job_id}",
    )
    rdf_api_cron_job_approval = ToRDFApiCronJobApproval(api_cron_job_approval)
    notification_lib.Notify(
        api_cron_job_approval.requestor,
        rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_GRANTED,
        "%s has granted you access to %s." % (context.username, subject_title),
        rdf_api_cron_job_approval.subject.ObjectReference(),
    )

    return api_cron_job_approval


class ApiListCronJobApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListCronJobApprovalsArgs


class ApiListCronJobApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListCronJobApprovalsResult
  rdf_deps = [
      ApiCronJobApproval,
  ]


class ApiListCronJobApprovalsHandler(api_call_handler_base.ApiCallHandler):
  """Returns list of user's cron jobs approvals."""

  args_type = ApiListCronJobApprovalsArgs
  result_type = ApiListCronJobApprovalsResult
  proto_args_type = api_user_pb2.ApiListCronJobApprovalsArgs
  proto_result_type = api_user_pb2.ApiListCronJobApprovalsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListCronJobApprovalsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListCronJobApprovalsResult:
    assert context is not None

    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
            subject_id=None,
            include_expired=True,
        ),
        key=lambda ar: ar.timestamp,
        reverse=True,
    )

    if not args.HasField("count"):
      end = None
    else:
      end = args.offset + args.count

    api_approvals = [
        InitApiCronJobApprovalFromApprovalRequest(ar)
        for ar in approvals[args.offset : end]
    ]

    return api_user_pb2.ApiListCronJobApprovalsResult(items=api_approvals)


class ApiGetOwnGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Renders current user settings."""

  result_type = ApiGrrUser
  proto_result_type = api_user_pb2.ApiGrrUser

  def __init__(
      self,
      interface_traits: Optional[api_user_pb2.ApiGrrUserInterfaceTraits] = None,
  ) -> None:
    super().__init__()
    self.interface_traits = interface_traits

  def Handle(
      self,
      unused_args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGrrUser:
    """Fetches and renders current user's settings."""
    assert context is not None

    # TODO: Use function to get API from proto user.
    user_record = data_store.REL_DB.ReadGRRUser(context.username)
    api_user = InitApiGrrUserFromGrrUser(user_record)

    if self.interface_traits:
      api_user.interface_traits.CopyFrom(self.interface_traits)

    return api_user


class ApiUpdateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Sets current user settings."""

  args_type = ApiGrrUser
  proto_args_type = api_user_pb2.ApiGrrUser

  def Handle(
      self,
      args: api_user_pb2.ApiGrrUser,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGrrUser:
    assert context is not None

    if args.username or args.HasField("interface_traits"):
      raise ValueError(
          "Username or interface traits are set but cannot be updated"
      )

    data_store.REL_DB.WriteGRRUser(
        context.username,
        ui_mode=args.settings.mode,
        canary_mode=args.settings.canary_mode,
    )


class ApiGetPendingUserNotificationsCountResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGetPendingUserNotificationsCountResult


class ApiGetPendingUserNotificationsCountHandler(
    api_call_handler_base.ApiCallHandler
):
  """Returns the number of pending notifications for the current user."""

  result_type = ApiGetPendingUserNotificationsCountResult
  proto_result_type = api_user_pb2.ApiGetPendingUserNotificationsCountResult

  def Handle(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiGetPendingUserNotificationsCountResult:
    """Fetches the pending notification count."""
    assert context is not None

    user_notifications = list(
        data_store.REL_DB.ReadUserNotifications(
            context.username,
            state=objects_pb2.UserNotification.State.STATE_PENDING,
        )
    )
    return api_user_pb2.ApiGetPendingUserNotificationsCountResult(
        count=len(user_notifications)
    )


class ApiListPendingUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListPendingUserNotificationsArgs
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiListPendingUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListPendingUserNotificationsResult
  rdf_deps = [
      ApiNotification,
  ]


class ApiListPendingUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Returns pending notifications for the current user."""

  args_type = ApiListPendingUserNotificationsArgs
  result_type = ApiListPendingUserNotificationsResult
  proto_args_type = api_user_pb2.ApiListPendingUserNotificationsArgs
  proto_result_type = api_user_pb2.ApiListPendingUserNotificationsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListPendingUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListPendingUserNotificationsResult:
    """Fetches the pending notifications."""
    assert context is not None

    user_notifications = data_store.REL_DB.ReadUserNotifications(
        context.username,
        state=objects_pb2.UserNotification.State.STATE_PENDING,
        timerange=(
            rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(args.timestamp),
            None,
        ),
    )

    # TODO(user): Remove this, so that the order is reversed. This will
    # be an API-breaking change.
    user_notifications = sorted(user_notifications, key=lambda x: x.timestamp)

    # Make sure that only notifications with timestamp > args.timestamp
    # are returned.
    # Semantics of the API call (strict >) differs slightly from the
    # semantics of the db.ReadUserNotifications call (inclusive >=).
    if user_notifications and user_notifications[0].timestamp == args.timestamp:
      user_notifications.pop(0)

    return api_user_pb2.ApiListPendingUserNotificationsResult(
        items=[
            InitApiNotificationFromUserNotification(n)
            for n in user_notifications
        ]
    )


class ApiDeletePendingUserNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiDeletePendingUserNotificationArgs
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiDeletePendingUserNotificationHandler(
    api_call_handler_base.ApiCallHandler
):
  """Removes the pending notification with the given timestamp."""

  args_type = ApiDeletePendingUserNotificationArgs
  proto_args_type = api_user_pb2.ApiDeletePendingUserNotificationArgs

  def Handle(
      self,
      args: api_user_pb2.ApiDeletePendingUserNotificationArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    """Deletes the notification from the pending notifications."""
    assert context is not None

    data_store.REL_DB.UpdateUserNotifications(
        context.username,
        [rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(args.timestamp)],
        state=objects_pb2.UserNotification.State.STATE_NOT_PENDING,
    )


class ApiListAndResetUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListAndResetUserNotificationsArgs


class ApiListAndResetUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListAndResetUserNotificationsResult
  rdf_deps = [
      ApiNotification,
  ]


class ApiListAndResetUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Returns the number of pending notifications for the current user."""

  args_type = ApiListAndResetUserNotificationsArgs
  result_type = ApiListAndResetUserNotificationsResult
  proto_args_type = api_user_pb2.ApiListAndResetUserNotificationsArgs
  proto_result_type = api_user_pb2.ApiListAndResetUserNotificationsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListAndResetUserNotificationsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListAndResetUserNotificationsResult:
    """Fetches the user notifications."""
    assert context is not None

    back_timestamp = max(
        rdfvalue.RDFDatetime.Now()
        - rdfvalue.Duration.From(2 * 52, rdfvalue.WEEKS),
        data_store.REL_DB.MinTimestamp(),
    )
    user_notifications = data_store.REL_DB.ReadUserNotifications(
        context.username, timerange=(back_timestamp, None)
    )

    pending_timestamps = [
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(n.timestamp)
        for n in user_notifications
        if n.state == objects_pb2.UserNotification.State.STATE_PENDING
    ]
    data_store.REL_DB.UpdateUserNotifications(
        context.username,
        pending_timestamps,
        state=objects_pb2.UserNotification.State.STATE_NOT_PENDING,
    )

    total_count = len(user_notifications)
    if args.filter:
      user_notifications = [
          n
          for n in user_notifications
          if args.filter.lower() in n.message.lower()
      ]

    if not args.HasField("count"):
      args.count = 50

    start = args.offset
    end = args.offset + args.count

    api_notifications = []
    for user_notification in user_notifications[start:end]:
      try:
        api_notifications.append(
            InitApiNotificationFromUserNotification(user_notification)
        )
      except ValueError as e:
        logging.exception(
            "Unable to convert notification %s: %s", user_notification, e
        )

    return api_user_pb2.ApiListAndResetUserNotificationsResult(
        items=api_notifications, total_count=total_count
    )


class ApiListApproverSuggestionsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsArgs
  rdf_deps = []


class ApproverSuggestion(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsResult.ApproverSuggestion
  rdf_deps = []


class ApiListApproverSuggestionsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsResult
  rdf_deps = [ApproverSuggestion]


def _GetAllUsernames() -> Sequence[str]:
  return sorted(user.username for user in data_store.REL_DB.ReadGRRUsers())


def _GetMostRequestedUsernames(
    context: api_call_context.ApiCallContext,
) -> Sequence[str]:
  requests = data_store.REL_DB.ReadApprovalRequests(
      context.username,
      objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
      include_expired=True,
  )
  not_users = collection.Flatten(req.notified_users for req in requests)
  user_counts = collections.Counter(not_users)
  return [username for (username, _) in user_counts.most_common()]


class ApiListApproverSuggestionsHandler(api_call_handler_base.ApiCallHandler):
  """List suggestions for approver usernames."""

  args_type = ApiListApproverSuggestionsArgs
  result_type = ApiListApproverSuggestionsResult
  proto_args_type = api_user_pb2.ApiListApproverSuggestionsArgs
  proto_result_type = api_user_pb2.ApiListApproverSuggestionsResult

  def Handle(
      self,
      args: api_user_pb2.ApiListApproverSuggestionsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_user_pb2.ApiListApproverSuggestionsResult:
    assert context is not None

    all_usernames = _GetAllUsernames()
    all_usernames = sorted(set(all_usernames) - access_control.SYSTEM_USERS)
    usernames = []

    if not args.username_query:
      # When the user has not started typing a username yet, try to suggest
      # previously requested approvers. Do not suggest usernames that are not
      # actually registered users.
      all_usernames_set = set(all_usernames)
      usernames = [
          u
          for u in _GetMostRequestedUsernames(context)
          if u in all_usernames_set
      ]

    if not usernames:
      # If no previously requested approvers can be suggested, or the user
      # started typing a username, suggest names from all registered users.
      usernames = [
          u for u in all_usernames if u.startswith(args.username_query)
      ]

    try:
      # If present, remove the requestor from suggested approvers.
      usernames.remove(context.username)
    except ValueError:
      pass

    return api_user_pb2.ApiListApproverSuggestionsResult(
        suggestions=[
            api_user_pb2.ApiListApproverSuggestionsResult.ApproverSuggestion(
                username=u
            )
            for u in usernames
        ]
    )


# Copy of migration functions to avoid circular dependency.
def ToRDFApiClientApproval(
    proto: api_user_pb2.ApiClientApproval,
) -> ApiClientApproval:
  return ApiClientApproval.FromSerializedBytes(proto.SerializeToString())


def ToRDFApiHuntApproval(
    proto: api_user_pb2.ApiHuntApproval,
) -> ApiHuntApproval:
  return ApiHuntApproval.FromSerializedBytes(proto.SerializeToString())


def ToRDFApiCronJobApproval(
    proto: api_user_pb2.ApiCronJobApproval,
) -> ApiCronJobApproval:
  return ApiCronJobApproval.FromSerializedBytes(proto.SerializeToString())
