#!/usr/bin/env python
"""API handlers for user-related data and actions."""
import collections
import email
import functools
import itertools
import logging

import jinja2

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import collection
from grr_response_proto import user_pb2
from grr_response_proto.api import user_pb2 as api_user_pb2
from grr_response_server import access_control
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import email_alerts
from grr_response_server import flow
from grr_response_server import notification as notification_lib
from grr_response_server.databases import db
from grr_response_server.flows.general import administrative
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import approval_checks

from grr_response_server.gui.api_plugins import client as api_client

from grr_response_server.gui.api_plugins import cron as api_cron
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import hunt as api_hunt

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

  def InitFromObjectReference(self, ref):
    if ref.reference_type == ref.Type.UNSET:
      self.type = self.Type.UNSET

    elif ref.reference_type == ref.Type.CLIENT:
      self.type = self.Type.CLIENT
      self.client.client_id = ref.client.client_id

    elif ref.reference_type == ref.Type.HUNT:
      self.type = self.Type.HUNT
      self.hunt.hunt_id = ref.hunt.hunt_id

    elif ref.reference_type == ref.Type.FLOW:
      self.type = self.Type.FLOW
      self.flow.client_id = ref.flow.client_id
      self.flow.flow_id = ref.flow.flow_id

    elif ref.reference_type == ref.Type.CRON_JOB:
      self.type = self.Type.CRON
      self.cron.cron_job_id = ref.cron_job.cron_job_id

    elif ref.reference_type == ref.Type.VFS_FILE:
      self.type = self.Type.VFS
      self.vfs.client_id = ref.vfs_file.client_id

      if ref.vfs_file.path_type == rdf_objects.PathInfo.PathType.UNSET:
        raise ValueError(
            "Can't init from VFS_FILE object reference with unset path_type.")

      self.vfs.vfs_path = ref.vfs_file.ToPath()

    elif ref.reference_type == ref.Type.APPROVAL_REQUEST:
      ref_ar = ref.approval_request

      if ref_ar.approval_type == ref_ar.ApprovalType.APPROVAL_TYPE_NONE:
        raise ValueError("Can't init from APPROVAL_REQUEST object reference "
                         "with unset approval_type.")
      elif ref_ar.approval_type == ref_ar.ApprovalType.APPROVAL_TYPE_CLIENT:
        self.type = self.Type.CLIENT_APPROVAL
        self.client_approval.approval_id = ref_ar.approval_id
        self.client_approval.username = ref_ar.requestor_username
        self.client_approval.client_id = ref_ar.subject_id
      elif ref_ar.approval_type == ref_ar.ApprovalType.APPROVAL_TYPE_HUNT:
        self.type = self.Type.HUNT_APPROVAL
        self.hunt_approval.approval_id = ref_ar.approval_id
        self.hunt_approval.username = ref_ar.requestor_username
        self.hunt_approval.hunt_id = ref_ar.subject_id
      elif ref_ar.approval_type == ref_ar.ApprovalType.APPROVAL_TYPE_CRON_JOB:
        self.type = self.Type.CRON_JOB_APPROVAL
        self.cron_job_approval.approval_id = ref_ar.approval_id
        self.cron_job_approval.username = ref_ar.requestor_username
        self.cron_job_approval.cron_job_id = ref_ar.subject_id
      else:
        raise ValueError("Unexpected APPROVAL_REQUEST object reference type "
                         "value: %d" % ref_ar.approval_type)
    else:
      raise ValueError("Unexpected reference type: %d" % ref.type)

    return self


class ApiNotification(rdf_structs.RDFProtoStruct):
  """Represents a user notification."""

  protobuf = api_user_pb2.ApiNotification
  rdf_deps = [
      ApiNotificationReference,
      rdfvalue.RDFDatetime,
  ]

  def _GetUrnComponents(self, notification):
    # Still display if subject doesn't get set, this will appear in the GUI with
    # a target of "None"
    urn = "/"
    if notification.subject is not None:
      urn = notification.subject

    path = rdfvalue.RDFURN(urn)
    return path.Path().split("/")[1:]

  def InitFromNotification(self, notification, is_pending=False):
    """Initializes this object from an existing notification.

    Args:
      notification: A rdfvalues.flows.Notification object.
      is_pending: Indicates whether the user has already seen this notification
        or not.

    Returns:
      The current instance.
    """
    self.timestamp = notification.timestamp
    self.message = notification.message
    self.subject = str(notification.subject)
    self.is_pending = is_pending

    reference_type_enum = ApiNotificationReference.Type

    # Please see the comments to notification.Notify implementation
    # for the details of notification.type format. Short summary:
    # notification.type may be one of legacy values (i.e. "ViewObject") or
    # have a format of "[legacy value]:[new-style notification type]", i.e.
    # "ViewObject:TYPE_CLIENT_INTERROGATED".
    if ":" in notification.type:
      legacy_type, new_type = notification.type.split(":", 2)
      self.notification_type = new_type
    else:
      legacy_type = notification.type

    # TODO(user): refactor notifications, so that we send a meaningful
    # notification from the start, so that we don't have to do the
    # bridging/conversion/guessing here.
    components = self._GetUrnComponents(notification)
    if legacy_type == "Discovery":
      self.reference.type = reference_type_enum.CLIENT
      self.reference.client = ApiNotificationClientReference(
          client_id=components[0])
    elif legacy_type == "ViewObject":
      if len(components) >= 2 and components[0] == "hunts":
        self.reference.type = reference_type_enum.HUNT
        self.reference.hunt.hunt_id = components[1]
      elif len(components) >= 2 and components[0] == "cron":
        self.reference.type = reference_type_enum.CRON
        self.reference.cron.cron_job_id = components[1]
      elif len(components) >= 3 and components[1] == "flows":
        self.reference.type = reference_type_enum.FLOW
        self.reference.flow.flow_id = components[2]
        self.reference.flow.client_id = components[0]
      elif len(components) == 1 and rdf_client.ClientURN.Validate(
          components[0]):
        self.reference.type = reference_type_enum.CLIENT
        self.reference.client.client_id = components[0]
      else:
        if notification.subject:
          path = notification.subject.Path()
          for prefix in rdf_paths.PathSpec.AFF4_PREFIXES.values():
            part = "/%s%s" % (components[0], prefix)
            if path.startswith(part):
              self.reference.type = reference_type_enum.VFS
              self.reference.vfs.client_id = components[0]
              self.reference.vfs.vfs_path = (prefix +
                                             path[len(part):]).lstrip("/")
              break

        if self.reference.type != reference_type_enum.VFS:
          self.reference.type = reference_type_enum.UNKNOWN
          self.reference.unknown.subject_urn = notification.subject

    elif legacy_type == "FlowStatus":
      if not components or not rdf_client.ClientURN.Validate(components[0]):
        self.reference.type = reference_type_enum.UNKNOWN
        self.reference.unknown.subject_urn = notification.subject
      else:
        self.reference.type = reference_type_enum.FLOW
        self.reference.flow.flow_id = notification.source.Basename()
        self.reference.flow.client_id = components[0]

    # TODO(user): refactor GrantAccess notification so that we don't have
    # to infer approval type from the URN.
    elif legacy_type == "GrantAccess":
      if rdf_client.ClientURN.Validate(components[1]):
        self.reference.type = reference_type_enum.CLIENT_APPROVAL
        self.reference.client_approval.client_id = components[1]
        self.reference.client_approval.approval_id = components[-1]
        self.reference.client_approval.username = components[-2]
      elif components[1] == "hunts":
        self.reference.type = reference_type_enum.HUNT_APPROVAL
        self.reference.hunt_approval.hunt_id = components[2]
        self.reference.hunt_approval.approval_id = components[-1]
        self.reference.hunt_approval.username = components[-2]
      elif components[1] == "cron":
        self.reference.type = reference_type_enum.CRON_JOB_APPROVAL
        self.reference.cron_job_approval.cron_job_id = components[2]
        self.reference.cron_job_approval.approval_id = components[-1]
        self.reference.cron_job_approval.username = components[-2]

    else:
      self.reference.type = reference_type_enum.UNKNOWN
      self.reference.unknown.subject_urn = notification.subject
      self.reference.unknown.source_urn = notification.source

    return self

  def InitFromUserNotification(self, notification):
    self.timestamp = notification.timestamp
    self.notification_type = notification.notification_type
    self.message = notification.message
    self.is_pending = (notification.state == notification.State.STATE_PENDING)
    try:
      self.reference = ApiNotificationReference().InitFromObjectReference(
          notification.reference)
    except ValueError as e:
      logging.exception(
          "Can't initialize notification from an "
          "object reference: %s", e)
      # In case of any initialization issue, simply create an empty reference.
      self.reference = ApiNotificationReference(
          type=ApiNotificationReference.Type.UNSET)

    return self


class ApiGrrUserInterfaceTraits(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGrrUserInterfaceTraits

  def EnableAll(self):
    for type_descriptor in self.type_infos:
      self.Set(type_descriptor.name, True)

    return self


class ApiGrrUser(rdf_structs.RDFProtoStruct):
  """API object describing the user."""

  protobuf = api_user_pb2.ApiGrrUser
  rdf_deps = [
      ApiGrrUserInterfaceTraits,
      GUISettings,
  ]

  def InitFromDatabaseObject(self, db_obj):
    self.username = db_obj.username

    if db_obj.user_type == db_obj.UserType.USER_TYPE_ADMIN:
      self.user_type = self.UserType.USER_TYPE_ADMIN
    else:
      self.user_type = self.UserType.USER_TYPE_STANDARD

    self.settings.mode = db_obj.ui_mode
    self.settings.canary_mode = db_obj.canary_mode
    if config.CONFIG.Get("Email.enable_custom_email_address") and db_obj.email:
      self.email = db_obj.email

    return self


def _InitApiApprovalFromDatabaseObject(api_approval, db_obj):
  """Initializes Api(Client|Hunt|CronJob)Approval from the database object."""

  api_approval.id = db_obj.approval_id
  api_approval.requestor = db_obj.requestor_username
  api_approval.reason = db_obj.reason

  api_approval.notified_users = sorted(db_obj.notified_users)
  api_approval.email_cc_addresses = sorted(db_obj.email_cc_addresses)
  api_approval.email_message_id = db_obj.email_message_id

  api_approval.approvers = sorted([g.grantor_username for g in db_obj.grants])

  api_approval.expiration_time_us = db_obj.expiration_time

  try:
    approval_checks.CheckApprovalRequest(db_obj)
    api_approval.is_valid = True
  except access_control.UnauthorizedAccess as e:
    api_approval.is_valid_message = str(e)
    api_approval.is_valid = False

  return api_approval


class ApiClientApproval(rdf_structs.RDFProtoStruct):
  """API client approval object."""

  protobuf = api_user_pb2.ApiClientApproval
  rdf_deps = [
      api_client.ApiClient,
      rdfvalue.RDFDatetime,
  ]

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = data_store.REL_DB.ReadClientFullInfo(
          db_obj.subject_id)
    self.subject = api_client.ApiClient().InitFromClientInfo(
        db_obj.subject_id, approval_subject_obj)

    return _InitApiApprovalFromDatabaseObject(self, db_obj)

  @property
  def subject_title(self):
    return u"GRR client %s (%s)" % (self.subject.client_id,
                                    self.subject.knowledge_base.fqdn)

  @property
  def review_url_path(self):
    return (f"/v2/clients/{self.subject.client_id}/users/{self.requestor}"
            f"/approvals/{self.id}")

  @property
  def review_url_path_legacy(self):
    return (f"/#/users/{self.requestor}/approvals/client/"
            f"{self.subject.client_id}/{self.id}")

  @property
  def subject_url_path(self):
    return f"/v2/clients/{self.subject.client_id}"

  @property
  def subject_url_path_legacy(self):
    return f"#/clients/{self.subject.client_id}"

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.client_id),
            requestor_username=self.requestor))


class ApiHuntApproval(rdf_structs.RDFProtoStruct):
  """API hunt approval object."""

  protobuf = api_user_pb2.ApiHuntApproval
  rdf_deps = [
      api_flow.ApiFlow,
      api_hunt.ApiHunt,
  ]

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    _InitApiApprovalFromDatabaseObject(self, db_obj)

    if not approval_subject_obj:
      approval_subject_obj = data_store.REL_DB.ReadHuntObject(db_obj.subject_id)
      approval_subject_counters = data_store.REL_DB.ReadHuntCounters(
          db_obj.subject_id)
      self.subject = api_hunt.ApiHunt().InitFromHuntObject(
          approval_subject_obj,
          hunt_counters=approval_subject_counters,
          with_full_summary=True)
    original_object = approval_subject_obj.original_object

    if original_object.object_type == "FLOW_REFERENCE":
      original_flow = data_store.REL_DB.ReadFlowObject(
          original_object.flow_reference.client_id,
          original_object.flow_reference.flow_id)
      self.copied_from_flow = api_flow.ApiFlow().InitFromFlowObject(
          original_flow)
    elif original_object.object_type == "HUNT_REFERENCE":
      original_hunt = data_store.REL_DB.ReadHuntObject(
          original_object.hunt_reference.hunt_id)
      original_hunt_counters = data_store.REL_DB.ReadHuntCounters(
          original_object.hunt_reference.hunt_id)
      self.copied_from_hunt = api_hunt.ApiHunt().InitFromHuntObject(
          original_hunt,
          hunt_counters=original_hunt_counters,
          with_full_summary=True)

    return self

  @property
  def subject_title(self):
    return u"hunt %s" % (self.subject.hunt_id)

  @property
  def review_url_path(self):
    # TODO: Set to new UI after implementing approval view for
    # hunts.
    return self.review_url_path_legacy

  @property
  def review_url_path_legacy(self):
    return (f"/#/users/{self.requestor}/approvals/hunt/{self.subject.hunt_id}/"
            f"{self.id}")

  @property
  def subject_url_path(self):
    return self.subject_url_path_legacy

  @property
  def subject_url_path_legacy(self):
    return f"#/hunts/{self.subject.hunt_id}"

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.hunt_id),
            requestor_username=self.requestor))


class ApiCronJobApproval(rdf_structs.RDFProtoStruct):
  """API cron job approval object."""

  protobuf = api_user_pb2.ApiCronJobApproval
  rdf_deps = [
      api_cron.ApiCronJob,
  ]

  def _FillInSubject(self, job_id, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = cronjobs.CronManager().ReadJob(job_id)
      self.subject = api_cron.ApiCronJob.InitFromObject(approval_subject_obj)

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    _InitApiApprovalFromDatabaseObject(self, db_obj)
    self._FillInSubject(
        db_obj.subject_id, approval_subject_obj=approval_subject_obj)
    return self

  @property
  def subject_title(self):
    return u"a cron job %s" % (self.subject.cron_job_id)

  @property
  def review_url_path(self):
    return self.review_url_path_legacy

  @property
  def review_url_path_legacy(self):
    return (f"/#/users/{self.requestor}/approvals/cron-job/"
            f"{self.subject.cron_job_id}/{self.id}")

  @property
  def subject_url_path(self):
    return self.subject_url_path_legacy

  @property
  def subject_url_path_legacy(self):
    return f"#/crons/{self.subject.cron_job_id}"

  def ObjectReference(self):
    at = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.APPROVAL_REQUEST,
        approval_request=rdf_objects.ApprovalRequestReference(
            approval_type=at,
            approval_id=self.id,
            subject_id=str(self.subject.cron_job_id),
            requestor_username=self.requestor))


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


class ApiCreateApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class for all Create*Approval handlers."""

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  def SendApprovalEmail(self, approval):
    if not config.CONFIG.Get("Email.send_approval_emails"):
      return

    subject_template = jinja2.Template(
        "Approval for {{ user }} to access {{ subject }}.", autoescape=True)
    subject = subject_template.render(
        user=approval.requestor, subject=approval.subject_title)

    template = jinja2.Template(_APPROVAL_REQUESTED_TEMPLATE, autoescape=True)
    base_url = config.CONFIG["AdminUI.url"].rstrip("/") + "/"
    legacy_approval_url = base_url + approval.review_url_path_legacy.lstrip("/")
    approval_url = base_url + approval.review_url_path.lstrip("/")

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
        subject_title=approval.subject_title,
        # If you feel like it, add a cute dog picture here :)
        html_signature=config.CONFIG["Email.approval_signature"],
        text_signature=config.CONFIG["Email.signature"])

    requestor_email = data_store.REL_DB.ReadGRRUser(
        approval.requestor).GetEmail()
    notified_emails = [
        data_store.REL_DB.ReadGRRUser(user).GetEmail()
        for user in approval.notified_users
    ]

    email_alerts.EMAIL_ALERTER.SendEmail(
        to_addresses=",".join(notified_emails),
        from_address=requestor_email,
        subject=subject,
        message=body,
        is_html=True,
        cc_addresses=",".join(approval.email_cc_addresses),
        message_id=approval.email_message_id)

  def CreateApprovalNotification(self, approval):
    for user in approval.notified_users:
      try:
        notification_lib.Notify(
            user.strip(), self.__class__.approval_notification_type,
            "Please grant access to %s" % approval.subject_title,
            approval.ObjectReference())
      except db.UnknownGRRUserError:
        # The relational db does not allow sending notifications to users that
        # don't exist. This should happen rarely but we need to catch this case.
        logging.error("Notification sent for unknown user %s!", user.strip())

  def Handle(self, args, context=None):
    if not args.approval.reason:
      raise ValueError("Approval reason can't be empty.")

    expiry = config.CONFIG["ACL.token_expiry"]

    request = rdf_objects.ApprovalRequest(
        requestor_username=context.username,
        approval_type=self.__class__.approval_type,
        reason=args.approval.reason,
        notified_users=args.approval.notified_users,
        email_cc_addresses=args.approval.email_cc_addresses,
        subject_id=args.BuildSubjectId(),
        expiration_time=rdfvalue.RDFDatetime.Now() + expiry,
        email_message_id=email.utils.make_msgid())
    request.approval_id = data_store.REL_DB.WriteApprovalRequest(request)

    data_store.REL_DB.GrantApproval(
        approval_id=request.approval_id,
        requestor_username=context.username,
        grantor_username=context.username)

    result = self.__class__.result_type().InitFromDatabaseObject(request)

    self.SendApprovalEmail(result)
    self.CreateApprovalNotification(result)
    return result


class ApiListApprovalsHandlerBase(api_call_handler_base.ApiCallHandler):
  """Renders list of all user approvals."""

  def _FilterRelationalApprovalRequests(self, approval_requests,
                                        approval_create_fn, state):
    for ar in approval_requests:
      client_approval = approval_create_fn(ar)

      if state == ApiListClientApprovalsArgs.State.ANY:
        yield client_approval
      elif state == ApiListClientApprovalsArgs.State.VALID:
        if client_approval.is_valid:
          yield client_approval
      elif state == ApiListClientApprovalsArgs.State.INVALID:
        if not client_approval.is_valid:
          yield client_approval


class ApiGetApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class for all Get*Approval handlers."""

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  def Handle(self, args, context=None):
    try:
      approval_obj = data_store.REL_DB.ReadApprovalRequest(
          args.username, args.approval_id)
    except db.UnknownApprovalRequestError:
      raise ApprovalNotFoundError(
          "No approval with id=%s, type=%s, subject=%s could be found." %
          (args.approval_id, self.__class__.approval_type,
           args.BuildSubjectId()))

    if approval_obj.approval_type != self.__class__.approval_type:
      raise ValueError(
          "Unexpected approval type: %s, expected: %s" %
          (approval_obj.approval_type, self.__class__.approval_type))

    if approval_obj.subject_id != args.BuildSubjectId():
      raise ValueError("Unexpected subject id: %s, expected: %s" %
                       (approval_obj.subject_id, args.BuildSubjectId()))

    return self.__class__.result_type().InitFromDatabaseObject(approval_obj)


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


class ApiGrantApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class reused by all client approval handlers."""

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  # Class to be used to grant the approval. Should be set by a subclass.
  approval_grantor = None

  def SendGrantEmail(self, approval, context=None):
    if not config.CONFIG.Get("Email.send_approval_emails"):
      return

    subject_template = jinja2.Template(
        "Approval for {{ user }} to access {{ subject }}.", autoescape=True)
    subject = subject_template.render(
        user=approval.requestor, subject=approval.subject_title)

    template = jinja2.Template(_APPROVAL_GRANTED_TEMPLATE, autoescape=True)
    base_url = config.CONFIG["AdminUI.url"].rstrip("/") + "/"
    subject_url = base_url + approval.subject_url_path.lstrip("/")
    legacy_subject_url = base_url + approval.subject_url_path_legacy.lstrip("/")

    if subject_url == legacy_subject_url:
      # In case the new UI does not yet support showing the given subject type
      # (client, hunt, cronjob), hide the fallback link to the old UI in the
      # email template. Instead, clicking the main button will link the user to
      # the old UI.
      legacy_subject_url = None

    body = template.render(
        grantor=context.username,
        requestor=approval.requestor,
        reason=approval.reason,
        legacy_subject_url=legacy_subject_url,
        subject_url=subject_url,
        subject_title=approval.subject_title,
        html_signature=config.CONFIG["Email.approval_signature"],
        text_signature=config.CONFIG["Email.signature"])

    # Email subject should match approval request, and we add message id
    # references so they are grouped together in a thread by gmail.
    headers = {
        "In-Reply-To": approval.email_message_id,
        "References": approval.email_message_id
    }

    requestor_email = data_store.REL_DB.ReadGRRUser(
        approval.requestor).GetEmail()
    username_email = data_store.REL_DB.ReadGRRUser(context.username).GetEmail()

    email_alerts.EMAIL_ALERTER.SendEmail(
        to_addresses=requestor_email,
        from_address=username_email,
        subject=subject,
        message=body,
        is_html=True,
        cc_addresses=",".join(approval.email_cc_addresses),
        headers=headers)

  def CreateGrantNotification(self, approval, context=None):
    notification_lib.Notify(
        approval.requestor, self.__class__.approval_notification_type,
        "%s has granted you access to %s." %
        (context.username, approval.subject_title),
        approval.subject.ObjectReference())

  def Handle(self, args, context=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    try:
      data_store.REL_DB.GrantApproval(args.username, args.approval_id,
                                      context.username)

      approval_obj = data_store.REL_DB.ReadApprovalRequest(
          args.username, args.approval_id)
    except db.UnknownApprovalRequestError:
      raise ApprovalNotFoundError(
          "No approval with id=%s, type=%s, subject=%s could be found." %
          (args.approval_id, self.__class__.approval_type,
           args.BuildSubjectId()))

    result = self.__class__.result_type().InitFromDatabaseObject(approval_obj)

    self.SendGrantEmail(result, context=context)
    self.CreateGrantNotification(result, context=context)
    return result


class ApiClientApprovalArgsBase(rdf_structs.RDFProtoStruct):
  """Base class for client approvals."""

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectId(self):
    return str(self.client_id)


class ApiCreateClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_user_pb2.ApiCreateClientApprovalArgs
  rdf_deps = [
      ApiClientApproval,
      api_client.ApiClientId,
  ]


class ApiCreateClientApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user client approval and notifies requested approvers."""

  args_type = ApiCreateClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_REQUESTED)

  def Handle(self, args, context=None):
    result = super().Handle(args, context=context)

    if args.keep_client_alive:
      flow.StartFlow(
          client_id=str(args.client_id),
          flow_cls=administrative.KeepAlive,
          creator=context.username,
          duration=3600)

    return result


class ApiGetClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_user_pb2.ApiGetClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiGetClientApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about an approval for a given client and reason."""

  args_type = ApiGetClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT


class ApiGrantClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_user_pb2.ApiGrantClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiGrantClientApprovalHandler(ApiGrantApprovalHandlerBase):
  """Handle for GrantClientApproval requests."""

  args_type = ApiGrantClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_CLIENT_APPROVAL_GRANTED)

  def Handle(self, args, context=None):
    approval = super().Handle(args, context=context)

    if approval.is_valid:
      flow.StartScheduledFlows(
          client_id=str(approval.subject.client_id), creator=approval.requestor)

    return approval


class ApiListClientApprovalsArgs(ApiClientApprovalArgsBase):
  protobuf = api_user_pb2.ApiListClientApprovalsArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiListClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListClientApprovalsResult
  rdf_deps = [
      ApiClientApproval,
  ]


class ApiListClientApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's clients approvals."""

  args_type = ApiListClientApprovalsArgs
  result_type = ApiListClientApprovalsResult

  def _CheckClientId(self, client_id, approval):
    subject = approval.Get(approval.Schema.SUBJECT)
    return subject.Basename() == client_id

  def _CheckState(self, state, approval):
    try:
      approval.CheckAccess(approval.context)
      is_valid = True
    except access_control.UnauthorizedAccess:
      is_valid = False

    if state == ApiListClientApprovalsArgs.State.VALID:
      return is_valid

    if state == ApiListClientApprovalsArgs.State.INVALID:
      return not is_valid

  def _BuildFilter(self, args):
    filters = []

    if args.client_id:
      filters.append(functools.partial(self._CheckClientId, args.client_id))

    if args.state:
      filters.append(functools.partial(self._CheckState, args.state))

    if filters:

      def Filter(approval):
        for f in filters:
          if not f(approval):
            return False

        return True

      return Filter
    else:
      return lambda approval: True  # Accept all by default.

  def Handle(self, args, context=None):
    subject_id = None
    if args.client_id:
      subject_id = str(args.client_id)

    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
            subject_id=subject_id,
            include_expired=True),
        key=lambda ar: ar.timestamp,
        reverse=True)
    approvals = self._FilterRelationalApprovalRequests(
        approvals, lambda ar: ApiClientApproval().InitFromDatabaseObject(ar),
        args.state)

    if not args.count:
      end = None
    else:
      end = args.offset + args.count
    items = list(itertools.islice(approvals, args.offset, end))
    api_client.UpdateClientsFromFleetspeak([a.subject for a in items])

    return ApiListClientApprovalsResult(items=items)


class ApiHuntApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectId(self):
    return str(self.hunt_id)


class ApiCreateHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_user_pb2.ApiCreateHuntApprovalArgs
  rdf_deps = [
      ApiHuntApproval,
      api_hunt.ApiHuntId,
  ]


class ApiCreateHuntApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user hunt approval and notifies requested approvers."""

  args_type = ApiCreateHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_HUNT_APPROVAL_REQUESTED)


class ApiGetHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_user_pb2.ApiGetHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiGetHuntApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given hunt, user and approval id."""

  args_type = ApiGetHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT


class ApiGrantHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_user_pb2.ApiGrantHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiGrantHuntApprovalHandler(ApiGrantApprovalHandlerBase):
  """Handle for GrantHuntApproval requests."""

  args_type = ApiGrantHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_HUNT_APPROVAL_GRANTED)


class ApiListHuntApprovalsArgs(ApiHuntApprovalArgsBase):
  protobuf = api_user_pb2.ApiListHuntApprovalsArgs


class ApiListHuntApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListHuntApprovalsResult
  rdf_deps = [
      ApiHuntApproval,
  ]


class ApiListHuntApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's hunts approvals."""

  args_type = ApiListHuntApprovalsArgs
  result_type = ApiListHuntApprovalsResult

  def Handle(self, args, context=None):
    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT,
            subject_id=None,
            include_expired=True),
        key=lambda ar: ar.timestamp,
        reverse=True)

    if not args.count:
      end = None
    else:
      end = args.offset + args.count

    items = [
        ApiHuntApproval().InitFromDatabaseObject(ar)
        for ar in approvals[args.offset:end]
    ]

    return ApiListHuntApprovalsResult(items=items)


class ApiCronJobApprovalArgsBase(rdf_structs.RDFProtoStruct):
  """Base class for Cron Job approvals."""

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectId(self):
    return str(self.cron_job_id)


class ApiCreateCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_user_pb2.ApiCreateCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
      ApiCronJobApproval,
  ]


class ApiCreateCronJobApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user cron approval and notifies requested approvers."""

  args_type = ApiCreateCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_type = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_REQUESTED)


class ApiGetCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_user_pb2.ApiGetCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiGetCronJobApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given cron, user and approval id."""

  args_type = ApiGetCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_type = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)


class ApiGrantCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_user_pb2.ApiGrantCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiGrantCronJobApprovalHandler(ApiGrantApprovalHandlerBase):
  """Handle for GrantCronJobApproval requests."""

  args_type = ApiGrantCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_type = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)
  approval_notification_type = (
      rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_GRANTED)


class ApiListCronJobApprovalsArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_user_pb2.ApiListCronJobApprovalsArgs


class ApiListCronJobApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListCronJobApprovalsResult
  rdf_deps = [
      ApiCronJobApproval,
  ]


class ApiListCronJobApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's cron jobs approvals."""

  args_type = ApiListCronJobApprovalsArgs
  result_type = ApiListCronJobApprovalsResult

  def Handle(self, args, context=None):
    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            context.username,
            rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB,
            subject_id=None,
            include_expired=True),
        key=lambda ar: ar.timestamp,
        reverse=True)

    if not args.count:
      end = None
    else:
      end = args.offset + args.count

    items = [
        ApiCronJobApproval().InitFromDatabaseObject(ar)
        for ar in approvals[args.offset:end]
    ]

    return ApiListCronJobApprovalsResult(items=items)


class ApiGetOwnGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Renders current user settings."""

  result_type = ApiGrrUser

  def __init__(self, interface_traits=None):
    super().__init__()
    self.interface_traits = interface_traits

  def Handle(self, unused_args, context=None):
    """Fetches and renders current user's settings."""

    result = ApiGrrUser(username=context.username)

    user_record = data_store.REL_DB.ReadGRRUser(context.username)
    result.InitFromDatabaseObject(user_record)

    result.interface_traits = (
        self.interface_traits or ApiGrrUserInterfaceTraits())

    return result


class ApiUpdateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Sets current user settings."""

  args_type = ApiGrrUser

  def Handle(self, args, context=None):
    if args.username or args.HasField("interface_traits"):
      raise ValueError("Only user settings can be updated.")

    data_store.REL_DB.WriteGRRUser(
        context.username,
        ui_mode=args.settings.mode,
        canary_mode=args.settings.canary_mode)


class ApiGetPendingUserNotificationsCountResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiGetPendingUserNotificationsCountResult


class ApiGetPendingUserNotificationsCountHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  result_type = ApiGetPendingUserNotificationsCountResult

  def Handle(self, args, context=None):
    """Fetches the pending notification count."""
    ns = list(
        data_store.REL_DB.ReadUserNotifications(
            context.username,
            state=rdf_objects.UserNotification.State.STATE_PENDING))
    return ApiGetPendingUserNotificationsCountResult(count=len(ns))


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
    api_call_handler_base.ApiCallHandler):
  """Returns pending notifications for the current user."""

  args_type = ApiListPendingUserNotificationsArgs
  result_type = ApiListPendingUserNotificationsResult

  def Handle(self, args, context=None):
    """Fetches the pending notifications."""
    ns = data_store.REL_DB.ReadUserNotifications(
        context.username,
        state=rdf_objects.UserNotification.State.STATE_PENDING,
        timerange=(args.timestamp, None))

    # TODO(user): Remove this, so that the order is reversed. This will
    # be an API-breaking change.
    ns = sorted(ns, key=lambda x: x.timestamp)

    # Make sure that only notifications with timestamp > args.timestamp
    # are returned.
    # Semantics of the API call (strict >) differs slightly from the
    # semantics of the db.ReadUserNotifications call (inclusive >=).
    if ns and ns[0].timestamp == args.timestamp:
      ns.pop(0)

    return ApiListPendingUserNotificationsResult(
        items=[ApiNotification().InitFromUserNotification(n) for n in ns])


class ApiDeletePendingUserNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiDeletePendingUserNotificationArgs
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiDeletePendingUserNotificationHandler(
    api_call_handler_base.ApiCallHandler):
  """Removes the pending notification with the given timestamp."""

  args_type = ApiDeletePendingUserNotificationArgs

  def Handle(self, args, context=None):
    """Deletes the notification from the pending notifications."""
    data_store.REL_DB.UpdateUserNotifications(
        context.username, [args.timestamp],
        state=rdf_objects.UserNotification.State.STATE_NOT_PENDING)


class ApiListAndResetUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListAndResetUserNotificationsArgs


class ApiListAndResetUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListAndResetUserNotificationsResult
  rdf_deps = [
      ApiNotification,
  ]


class ApiListAndResetUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  args_type = ApiListAndResetUserNotificationsArgs
  result_type = ApiListAndResetUserNotificationsResult

  def Handle(self, args, context=None):
    """Fetches the user notifications."""
    back_timestamp = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        2 * 52, rdfvalue.WEEKS)
    ns = data_store.REL_DB.ReadUserNotifications(
        context.username, timerange=(back_timestamp, None))

    pending_timestamps = [
        n.timestamp
        for n in ns
        if n.state == rdf_objects.UserNotification.State.STATE_PENDING
    ]
    data_store.REL_DB.UpdateUserNotifications(
        context.username,
        pending_timestamps,
        state=rdf_objects.UserNotification.State.STATE_NOT_PENDING)

    total_count = len(ns)
    if args.filter:
      ns = [n for n in ns if args.filter.lower() in n.message.lower()]

    if not args.count:
      args.count = 50

    start = args.offset
    end = args.offset + args.count

    api_notifications = []

    for n in ns[start:end]:
      try:
        api_notifications.append(ApiNotification().InitFromUserNotification(n))
      except ValueError as e:
        logging.error("Unable to convert notification %s: %s", n, e)

    return ApiListAndResetUserNotificationsResult(
        items=api_notifications, total_count=total_count)


class ApiListApproverSuggestionsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsArgs
  rdf_deps = []


class ApproverSuggestion(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsResult.ApproverSuggestion
  rdf_deps = []


class ApiListApproverSuggestionsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_user_pb2.ApiListApproverSuggestionsResult
  rdf_deps = [ApproverSuggestion]


def _GetAllUsernames():
  return sorted(user.username for user in data_store.REL_DB.ReadGRRUsers())


def _GetMostRequestedUsernames(context):
  requests = data_store.REL_DB.ReadApprovalRequests(
      context.username,
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT,
      include_expired=True)
  users = collection.Flatten(req.notified_users for req in requests)
  user_counts = collections.Counter(users)
  return [username for (username, _) in user_counts.most_common()]


class ApiListApproverSuggestionsHandler(api_call_handler_base.ApiCallHandler):
  """"List suggestions for approver usernames."""

  args_type = ApiListApproverSuggestionsArgs
  result_type = ApiListApproverSuggestionsResult

  def Handle(self, args, context=None):
    all_usernames = _GetAllUsernames()
    usernames = []

    if not args.username_query:
      # When the user has not started typing a username yet, try to suggest
      # previously requested approvers. Do not suggest usernames that are not
      # actually registered users.
      all_usernames_set = set(all_usernames)
      usernames = [
          u for u in _GetMostRequestedUsernames(context)
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

    suggestions = [ApproverSuggestion(username=u) for u in usernames]
    return ApiListApproverSuggestionsResult(suggestions=suggestions)
