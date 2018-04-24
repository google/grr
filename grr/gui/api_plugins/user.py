#!/usr/bin/env python
"""API handlers for user-related data and actions."""

import email
import functools
import itertools
import os

import jinja2

from grr import config

from grr.gui import api_call_handler_base
from grr.gui import approval_checks

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import cron as api_cron
from grr.gui.api_plugins import flow as api_flow
from grr.gui.api_plugins import hunt as api_hunt

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import user_pb2
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import db
from grr.server.grr_response_server import email_alerts
from grr.server.grr_response_server import flow

from grr.server.grr_response_server.aff4_objects import aff4_grr

from grr.server.grr_response_server.aff4_objects import cronjobs as aff4_cronjobs

from grr.server.grr_response_server.aff4_objects import security as aff4_security
from grr.server.grr_response_server.aff4_objects import users as aff4_users
from grr.server.grr_response_server.flows.general import administrative

from grr.server.grr_response_server.hunts import implementation


class GlobalNotificationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raised when a specific global notification could not be found."""


class ApprovalNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a specific approval object could not be found."""


class ApiNotificationDiscoveryReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationDiscoveryReference
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiNotificationHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationHuntReference
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class ApiNotificationCronReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationCronReference
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class ApiNotificationFlowReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationFlowReference
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiNotificationVfsReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationVfsReference
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFURN,
  ]


class ApiNotificationClientApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationClientApprovalReference
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiNotificationHuntApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationHuntApprovalReference
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiNotificationCronJobApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationCronJobApprovalReference


class ApiNotificationUnknownReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationUnknownReference
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class ApiNotificationReference(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiNotificationReference
  rdf_deps = [
      ApiNotificationClientApprovalReference,
      ApiNotificationCronJobApprovalReference,
      ApiNotificationCronReference,
      ApiNotificationDiscoveryReference,
      ApiNotificationFlowReference,
      ApiNotificationHuntApprovalReference,
      ApiNotificationHuntReference,
      ApiNotificationUnknownReference,
      ApiNotificationVfsReference,
  ]


class ApiNotification(rdf_structs.RDFProtoStruct):
  """Represents a user notification."""

  protobuf = user_pb2.ApiNotification
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
      is_pending: Indicates whether the user has already seen
          this notification or not.

    Returns:
      The current instance.
    """
    self.timestamp = notification.timestamp
    self.message = notification.message
    self.subject = str(notification.subject)
    self.is_pending = is_pending

    reference_type_enum = ApiNotificationReference.Type

    # TODO(user): refactor notifications, so that we send a meaningful
    # notification from the start, so that we don't have to do the
    # bridging/conversion/guessing here.
    components = self._GetUrnComponents(notification)
    if notification.type == "Discovery":
      self.reference.type = reference_type_enum.DISCOVERY
      self.reference.discovery = ApiNotificationDiscoveryReference(
          client_id=components[0])
    elif notification.type == "ViewObject":
      if len(components) >= 2 and components[0] == "hunts":
        self.reference.type = reference_type_enum.HUNT
        self.reference.hunt.hunt_urn = rdfvalue.RDFURN(
            os.path.join(*components[:2]))
      elif len(components) >= 2 and components[0] == "cron":
        self.reference.type = reference_type_enum.CRON
        self.reference.cron.cron_job_urn = rdfvalue.RDFURN(
            os.path.join(*components[:2]))
      elif len(components) >= 3 and components[1] == "flows":
        self.reference.type = reference_type_enum.FLOW
        self.reference.flow.flow_id = components[2]
        self.reference.flow.client_id = components[0]
      elif len(components) == 1 and rdf_client.ClientURN.Validate(
          components[0]):
        self.reference.type = reference_type_enum.DISCOVERY
        self.reference.discovery.client_id = components[0]
      else:
        if notification.subject:
          path = notification.subject.Path()
          for prefix in rdf_paths.PathSpec.AFF4_PREFIXES.values():
            part = "/%s%s" % (components[0], prefix)
            if path.startswith(part):
              self.reference.type = reference_type_enum.VFS
              self.reference.vfs.client_id = components[0]
              self.reference.vfs.vfs_path = prefix + path[len(part):]
              break

        if self.reference.type != reference_type_enum.VFS:
          self.reference.type = reference_type_enum.UNKNOWN
          self.reference.unknown.subject_urn = notification.subject

    elif notification.type == "FlowStatus":
      if not components or not rdf_client.ClientURN.Validate(components[0]):
        self.reference.type = reference_type_enum.UNKNOWN
        self.reference.unknown.subject_urn = notification.subject
      else:
        self.reference.type = reference_type_enum.FLOW
        self.reference.flow.flow_id = notification.source.Basename()
        self.reference.flow.client_id = components[0]

    # TODO(user): refactor GrantAccess notification so that we don't have
    # to infer approval type from the URN.
    elif notification.type == "GrantAccess":
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


class ApiGrrUserInterfaceTraits(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiGrrUserInterfaceTraits

  def EnableAll(self):
    for type_descriptor in self.type_infos:
      self.Set(type_descriptor.name, True)

    return self


class ApiGrrUser(rdf_structs.RDFProtoStruct):
  """API object describing the user."""

  protobuf = user_pb2.ApiGrrUser
  rdf_deps = [
      ApiGrrUserInterfaceTraits,
      aff4_users.GUISettings,
  ]

  def InitFromAff4Object(self, aff4_obj):
    self.username = aff4_obj.urn.Basename()
    self.settings = aff4_obj.Get(aff4_obj.Schema.GUI_SETTINGS)

    if "admin" in aff4_obj.GetLabelsNames(owner="GRR"):
      self.user_type = self.UserType.USER_TYPE_ADMIN
    else:
      self.user_type = self.UserType.USER_TYPE_STANDARD

    return self

  def InitFromDatabaseObject(self, db_obj):
    self.username = db_obj.username

    if db_obj.user_type == db_obj.UserType.USER_TYPE_ADMIN:
      self.user_type = self.UserType.USER_TYPE_ADMIN
    else:
      self.user_type = self.UserType.USER_TYPE_STANDARD

    self.settings.mode = db_obj.ui_mode
    self.settings.canary_mode = db_obj.canary_mode

    return self


def _InitApiApprovalFromAff4Object(api_approval, approval_obj):
  """Initializes Api(Client|Hunt|CronJob)Approval from an AFF4 object."""

  api_approval.id = approval_obj.urn.Basename()
  api_approval.reason = approval_obj.Get(approval_obj.Schema.REASON)
  api_approval.requestor = approval_obj.Get(approval_obj.Schema.REQUESTOR)

  # We should check the approval validity from the standpoint of the user
  # who had requested it.
  test_token = access_control.ACLToken(
      username=approval_obj.Get(approval_obj.Schema.REQUESTOR))
  try:
    approval_obj.CheckAccess(test_token)
    api_approval.is_valid = True
  except access_control.UnauthorizedAccess as e:
    api_approval.is_valid = False
    api_approval.is_valid_message = utils.SmartStr(e)

  notified_users = approval_obj.Get(approval_obj.Schema.NOTIFIED_USERS)
  if notified_users:
    api_approval.notified_users = sorted(
        u.strip() for u in notified_users.split(","))

  api_approval.email_message_id = approval_obj.Get(
      approval_obj.Schema.EMAIL_MSG_ID)

  email_cc = approval_obj.Get(approval_obj.Schema.EMAIL_CC)
  email_cc_addresses = sorted(s.strip() for s in email_cc.split(","))
  api_approval.email_cc_addresses = (
      set(email_cc_addresses) - set(api_approval.notified_users))

  api_approval.approvers = sorted(approval_obj.GetNonExpiredApprovers())

  return api_approval


def _InitApiApprovalFromDatabaseObject(api_approval, db_obj):
  """Initializes Api(Client|Hunt|CronJob)Approval from the database object."""

  try:
    approval_checks.CheckApprovalRequest(db_obj)
    api_approval.is_valid = True
  except access_control.UnauthorizedAccess as e:
    api_approval.is_valid = False
    api_approval.is_valid_message = utils.SmartStr(e)

  api_approval.id = db_obj.approval_id
  api_approval.requestor = db_obj.requestor_username
  api_approval.reason = db_obj.reason

  api_approval.notified_users = sorted(db_obj.notified_users)
  api_approval.email_cc_addresses = sorted(db_obj.email_cc_addresses)
  api_approval.email_message_id = db_obj.email_message_id

  api_approval.approvers = sorted([g.grantor_username for g in db_obj.grants])

  return api_approval


class ApiClientApproval(rdf_structs.RDFProtoStruct):
  """API client approval object."""

  protobuf = user_pb2.ApiClientApproval
  rdf_deps = [
      api_client.ApiClient,
  ]

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          approval_obj.Get(approval_obj.Schema.SUBJECT),
          aff4_type=aff4_grr.VFSGRRClient,
          token=approval_obj.token)
    self.subject = api_client.ApiClient().InitFromAff4Object(
        approval_subject_obj)

    return _InitApiApprovalFromAff4Object(self, approval_obj)

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = data_store.REL_DB.ReadClientFullInfo(
          db_obj.subject_id)
    self.subject = api_client.ApiClient().InitFromClientInfo(
        approval_subject_obj)

    return _InitApiApprovalFromDatabaseObject(self, db_obj)

  @property
  def subject_title(self):
    return u"GRR client %s (%s)" % (self.subject.client_id,
                                    self.subject.knowledge_base.fqdn)

  @property
  def review_url_path(self):
    return "/".join([
        "users", self.requestor, "approvals", "client",
        utils.SmartStr(self.subject.client_id),
        utils.SmartStr(self.id)
    ])

  @property
  def subject_url_path(self):
    return "/clients/%s" % utils.SmartStr(self.subject.client_id)

  @property
  def legacy_subject_urn(self):
    return aff4.ROOT_URN.Add(utils.SmartStr(self.subject.client_id))

  @property
  def legacy_approval_object_urn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.legacy_subject_urn.Path()).Add(
        self.requestor).Add(self.id)


class ApiHuntApproval(rdf_structs.RDFProtoStruct):
  """API hunt approval object."""

  protobuf = user_pb2.ApiHuntApproval
  rdf_deps = [
      api_flow.ApiFlow,
      api_hunt.ApiHunt,
  ]

  def _FillInSubject(self, subject_urn, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          subject_urn, aff4_type=implementation.GRRHunt)
    self.subject = api_hunt.ApiHunt().InitFromAff4Object(
        approval_subject_obj, with_full_summary=True)

    original_object = approval_subject_obj.runner_args.original_object
    if original_object.object_type == "FLOW_REFERENCE":
      urn = original_object.flow_reference.ToFlowURN()
      original_flow = aff4.FACTORY.Open(urn, aff4_type=flow.GRRFlow)
      self.copied_from_flow = api_flow.ApiFlow().InitFromAff4Object(
          original_flow, flow_id=original_flow.urn.Basename())
    elif original_object.object_type == "HUNT_REFERENCE":
      urn = original_object.hunt_reference.ToHuntURN()
      original_hunt = aff4.FACTORY.Open(urn, aff4_type=implementation.GRRHunt)
      self.copied_from_hunt = api_hunt.ApiHunt().InitFromAff4Object(
          original_hunt, with_full_summary=True)

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    _InitApiApprovalFromAff4Object(self, approval_obj)
    self._FillInSubject(
        approval_obj.Get(approval_obj.Schema.SUBJECT),
        approval_subject_obj=approval_subject_obj)
    return self

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    _InitApiApprovalFromDatabaseObject(self, db_obj)
    self._FillInSubject(
        aff4.ROOT_URN.Add("hunts").Add(db_obj.subject_id),
        approval_subject_obj=approval_subject_obj)
    return self

  @property
  def subject_title(self):
    return u"hunt %s" % (self.subject.hunt_id)

  @property
  def review_url_path(self):
    return "/".join([
        "users", self.requestor, "approvals", "hunt",
        utils.SmartStr(self.subject.hunt_id),
        utils.SmartStr(self.id)
    ])

  @property
  def subject_url_path(self):
    return "/hunts/%s" % utils.SmartStr(self.subject.hunt_id)

  @property
  def legacy_subject_urn(self):
    return aff4.ROOT_URN.Add("hunts").Add(utils.SmartStr(self.subject.hunt_id))

  @property
  def legacy_approval_object_urn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.legacy_subject_urn.Path()).Add(
        self.requestor).Add(self.id)


class ApiCronJobApproval(rdf_structs.RDFProtoStruct):
  """API cron job approval object."""

  protobuf = user_pb2.ApiCronJobApproval
  rdf_deps = [
      api_cron.ApiCronJob,
  ]

  def _FillInSubject(self, subject_urn, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          subject_urn, aff4_type=aff4_cronjobs.CronJob)
      self.subject = api_cron.ApiCronJob().InitFromAff4Object(
          approval_subject_obj)

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    _InitApiApprovalFromAff4Object(self, approval_obj)
    self._FillInSubject(
        approval_obj.Get(approval_obj.Schema.SUBJECT),
        approval_subject_obj=approval_subject_obj)
    return self

  def InitFromDatabaseObject(self, db_obj, approval_subject_obj=None):
    _InitApiApprovalFromDatabaseObject(self, db_obj)
    self._FillInSubject(
        rdfvalue.RDFURN("aff4:/cron").Add(db_obj.subject_id),
        approval_subject_obj=approval_subject_obj)
    return self

  @property
  def subject_title(self):
    return u"a cron job %s" % (self.subject.cron_job_id)

  @property
  def review_url_path(self):
    return "/".join([
        "users", self.requestor, "approvals", "cron-job",
        utils.SmartStr(self.subject.cron_job_id),
        utils.SmartStr(self.id)
    ])

  @property
  def subject_url_path(self):
    return "/crons/%s" % utils.SmartStr(self.subject.cron_job_id)

  @property
  def legacy_subject_urn(self):
    return aff4.ROOT_URN.Add("cron").Add(
        utils.SmartStr(self.subject.cron_job_id))

  @property
  def legacy_approval_object_urn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.legacy_subject_urn.Path()).Add(
        self.requestor).Add(self.id)


class ApiCreateApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class for all Crate*Approval handlers."""

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  # Requestor to be used to request the approval. Class is expected. Should be
  # set by a subclass.
  approval_requestor = None

  def HandleLegacy(self, args, token=None):
    requestor = self.__class__.approval_requestor(  # pylint: disable=not-callable
        reason=args.approval.reason,
        approver=",".join(args.approval.notified_users),
        email_cc_address=",".join(args.approval.email_cc_addresses),
        subject_urn=args.BuildSubjectUrn(),
        token=token)
    approval_urn = requestor.Request()

    approval_obj = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.__class__.approval_aff4_type,
        age=aff4.ALL_TIMES,
        token=token)

    return self.__class__.result_type().InitFromAff4Object(approval_obj)

  def HandleRelationalDB(self, args, token=None):
    expiry = config.CONFIG["ACL.token_expiry"]

    request = rdf_objects.ApprovalRequest(
        requestor_username=token.username,
        approval_type=self.__class__.approval_type,
        reason=args.approval.reason,
        notified_users=args.approval.notified_users,
        email_cc_addresses=args.approval.email_cc_addresses,
        subject_id=args.BuildSubjectId(),
        expiration_time=rdfvalue.RDFDatetime.Now() + expiry,
        email_message_id=email.utils.make_msgid(),
        grants=[
            rdf_objects.ApprovalGrant(
                grantor_username=token.username,
                timestamp=rdfvalue.RDFDatetime.Now())
        ])
    request.approval_id = data_store.REL_DB.WriteApprovalRequest(request)

    # Only return the object if database reads are enabled, since
    # initializing the approval also requires reading its subject.
    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      return self.__class__.result_type().InitFromDatabaseObject(request)

  def SendApprovalEmail(self, approval):
    if not config.CONFIG.Get("Email.send_approval_emails"):
      return

    subject_template = jinja2.Template(
        "Approval for {{ user }} to access {{ subject }}.", autoescape=True)
    subject = subject_template.render(
        user=utils.SmartUnicode(approval.requestor),
        subject=utils.SmartUnicode(approval.subject_title))

    template = jinja2.Template(
        """
<html><body><h1>Approval to access
<a href='{{ admin_ui }}/#/{{ approval_url }}'>{{ subject_title }}</a>
requested.</h1>

The user "{{ username }}" has requested access to
<a href='{{ admin_ui }}/#/{{ approval_url }}'>{{ subject_title }}</a>
for the purpose of <em>{{ reason }}</em>.

Please click <a href='{{ admin_ui }}/#/{{ approval_url }}'>
here
</a> to review this request and then grant access.

<p>Thanks,</p>
<p>{{ signature }}</p>
<p>{{ image|safe }}</p>
</body></html>""",
        autoescape=True)

    body = template.render(
        username=utils.SmartUnicode(approval.requestor),
        reason=utils.SmartUnicode(approval.reason),
        admin_ui=utils.SmartUnicode(config.CONFIG["AdminUI.url"]),
        subject_title=utils.SmartUnicode(approval.subject_title),
        approval_url=utils.SmartUnicode(approval.review_url_path),
        # If you feel like it, add a funny cat picture here :)
        image=utils.SmartUnicode(config.CONFIG["Email.approval_signature"]),
        signature=utils.SmartUnicode(config.CONFIG["Email.signature"]))

    email_alerts.EMAIL_ALERTER.SendEmail(
        ",".join(approval.notified_users),
        utils.SmartStr(approval.requestor),
        utils.SmartStr(subject),
        utils.SmartStr(body),
        is_html=True,
        cc_addresses=",".join(approval.email_cc_addresses),
        message_id=approval.email_message_id)

  # TODO(user): migrate notifications to REL-DB.
  def CreateApprovalNotification(self, approval):
    for user in approval.notified_users:
      user = user.strip()
      try:
        fd = aff4.FACTORY.Open(
            aff4.ROOT_URN.Add("users").Add(user),
            aff4_type=aff4_users.GRRUser,
            mode="rw")
      except aff4.InstantiationError:
        continue

      fd.Notify("GrantAccess", approval.legacy_approval_object_urn,
                "Please grant access to %s" % approval.subject_title, "")
      fd.Close()

  def Handle(self, args, token=None):
    if not args.approval.reason:
      raise ValueError("Approval reason can't be empty.")

    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      result = self.HandleRelationalDB(args, token=token)
    else:
      result = self.HandleLegacy(args, token=token)

    self.SendApprovalEmail(result)
    self.CreateApprovalNotification(result)
    return result


class ApiListApprovalsHandlerBase(api_call_handler_base.ApiCallHandler):
  """Renders list of all user approvals."""

  def _GetApprovals(self,
                    approval_type,
                    offset,
                    count,
                    filter_func=None,
                    token=None):
    """Gets all approvals for a given user and approval type.

    Args:
      approval_type: The type of approvals to get.
      offset: The starting index within the collection.
      count: The number of items to return.
      filter_func: A predicate function, returning True if a specific approval
        should be included in the result and False otherwise.
      token: The token identifying the user.

    Returns:
      A list of approvals of the given approval type.
    """
    approvals_base_urn = aff4.ROOT_URN.Add("users").Add(
        token.username).Add("approvals").Add(approval_type)

    all_children = aff4.FACTORY.RecursiveMultiListChildren([approvals_base_urn])

    approvals_urns = []
    for subject, children in all_children:
      # We only want to process leaf nodes.
      if children:
        continue
      approvals_urns.append(subject)

    approvals_urns.sort(key=lambda x: x.age, reverse=True)
    approvals = list(
        aff4.FACTORY.MultiOpen(
            approvals_urns,
            mode="r",
            aff4_type=aff4_security.Approval,
            age=aff4.ALL_TIMES,
            token=token))
    approvals_by_urn = {}
    for approval in approvals:
      approvals_by_urn[approval.symlink_urn or approval.urn] = approval

    cur_offset = 0
    sorted_approvals = []
    for approval_urn in approvals_urns:
      try:
        approval = approvals_by_urn[approval_urn]
      except KeyError:
        continue

      if filter_func is not None and not filter_func(approval):
        continue
      cur_offset += 1
      if cur_offset <= offset:
        continue
      if count and len(sorted_approvals) >= count:
        break
      sorted_approvals.append(approval)

    subjects_urns = [a.Get(a.Schema.SUBJECT) for a in approvals]
    subjects_by_urn = {}
    for subject in aff4.FACTORY.MultiOpen(subjects_urns, mode="r", token=token):
      subjects_by_urn[subject.urn] = subject

    return sorted_approvals, subjects_by_urn

  def _HandleApprovals(self, approvals, subjects_by_urn, convert_func):
    converted_approvals = []
    for approval in approvals:
      try:
        subject = subjects_by_urn[approval.Get(approval.Schema.SUBJECT)]
      except KeyError:
        continue

      converted_approval = convert_func(approval, subject)
      converted_approvals.append(converted_approval)

    return converted_approvals

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

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  def HandleLegacy(self, args, token=None):
    approval_urn = args.BuildApprovalObjUrn()
    try:
      approval_obj = aff4.FACTORY.Open(
          approval_urn,
          aff4_type=self.__class__.approval_aff4_type,
          age=aff4.ALL_TIMES,
          token=token)
    except IOError as e:
      raise ApprovalNotFoundError(e)

    return self.__class__.result_type().InitFromAff4Object(approval_obj)

  def HandleRelationalDB(self, args, token=None):
    try:
      approval_obj = data_store.REL_DB.ReadApprovalRequest(
          args.username, args.approval_id)
    except db.UnknownApprovalRequestError:
      raise ApprovalNotFoundError(
          "No approval with id=%s, type=%s, subject=%s could be found."
          % (args.approval_id, self.__class__.approval_type,
             args.BuildSubjectId()))

    if approval_obj.approval_type != self.__class__.approval_type:
      raise ValueError(
          "Unexpected approval type: %s, expected: %s" %
          (approval_obj.approval_type, self.__class__.approval_type))

    if approval_obj.subject_id != args.BuildSubjectId():
      raise ValueError("Unexpected subject id: %s, expected: %s" %
                       (approval_obj.subject_id, args.BuildSubjectId()))

    return self.__class__.result_type().InitFromDatabaseObject(approval_obj)

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      return self.HandleRelationalDB(args, token=token)
    else:
      return self.HandleLegacy(args, token=token)


class ApiGrantApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class reused by all client approval handlers."""

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  # objects.ApprovalRequest.ApprovalType value describing the approval type.
  approval_type = None

  # Class to be used to grant the approval. Should be set by a subclass.
  approval_grantor = None

  def HandleRelationalDB(self, args, token=None):
    try:
      data_store.REL_DB.GrantApproval(args.username, args.approval_id,
                                      token.username)

      approval_obj = data_store.REL_DB.ReadApprovalRequest(
          args.username, args.approval_id)
    except db.UnknownApprovalRequestError:
      raise ApprovalNotFoundError(
          "No approval with id=%s, type=%s, subject=%s could be found."
          % (args.approval_id, self.__class__.approval_type,
             args.BuildSubjectId()))

    return self.__class__.result_type().InitFromDatabaseObject(approval_obj)

  def HandleLegacy(self, args, token=None):
    subject_urn = args.BuildSubjectUrn()
    approval_urn = args.BuildApprovalObjUrn()

    approval_request = aff4.FACTORY.Open(
        approval_urn, aff4_type=self.__class__.approval_aff4_type, token=token)
    reason = approval_request.Get(approval_request.Schema.REASON)

    grantor = self.__class__.approval_grantor(  # pylint: disable=not-callable
        reason=reason,
        delegate=args.username,
        subject_urn=subject_urn,
        token=token)
    grantor.Grant()

    approval_request = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.__class__.approval_aff4_type,
        age=aff4.ALL_TIMES,
        token=token)
    return self.__class__.result_type().InitFromAff4Object(approval_request)

  def SendGrantEmail(self, approval, token=None):
    if not config.CONFIG.Get("Email.send_approval_emails"):
      return

    subject_template = jinja2.Template(
        "Approval for {{ user }} to access {{ subject }}.", autoescape=True)
    subject = subject_template.render(
        user=utils.SmartUnicode(approval.requestor),
        subject=utils.SmartUnicode(approval.subject_title))

    template = jinja2.Template(
        """
<html><body><h1>Access to
<a href='{{ admin_ui }}/#/{{ subject_url }}'>{{ subject_title }}</a>
granted.</h1>

The user {{ username }} has granted access to
<a href='{{ admin_ui }}/#/{{ subject_url }}'>{{ subject_title }}</a> for the
purpose of <em>{{ reason }}</em>.

Please click <a href='{{ admin_ui }}/#/{{ subject_url }}'>here</a> to access it.

<p>Thanks,</p>
<p>{{ signature }}</p>
</body></html>""",
        autoescape=True)
    body = template.render(
        subject_title=utils.SmartUnicode(approval.subject_title),
        username=utils.SmartUnicode(token.username),
        reason=utils.SmartUnicode(approval.reason),
        admin_ui=utils.SmartUnicode(config.CONFIG["AdminUI.url"].strip("/")),
        subject_url=utils.SmartUnicode(approval.subject_url_path.strip("/")),
        signature=utils.SmartUnicode(config.CONFIG["Email.signature"]))

    # Email subject should match approval request, and we add message id
    # references so they are grouped together in a thread by gmail.
    headers = {
        "In-Reply-To": approval.email_message_id,
        "References": approval.email_message_id
    }
    email_alerts.EMAIL_ALERTER.SendEmail(
        utils.SmartStr(approval.requestor),
        utils.SmartStr(token.username),
        utils.SmartStr(subject),
        utils.SmartStr(body),
        is_html=True,
        cc_addresses=",".join(approval.email_cc_addresses),
        headers=headers)

  def CreateGrantNotification(self, approval, token=None):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(approval.requestor),
        aff4_users.GRRUser,
        mode="rw",
        token=token) as fd:
      fd.Notify(
          "ViewObject", approval.legacy_subject_urn,
          "%s has granted you access to %s." % (token.username,
                                                approval.subject_title), "")

  def Handle(self, args, token=None):
    if not args.username:
      raise ValueError("username can't be empty.")

    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      result = self.HandleRelationalDB(args, token=token)
    else:
      result = self.HandleLegacy(args, token=token)

    self.SendGrantEmail(result, token=token)
    self.CreateGrantNotification(result, token=token)
    return result


class ApiClientApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return self.client_id.ToClientURN()

  def BuildSubjectId(self):
    return utils.SmartStr(self.client_id)

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(utils.SmartStr(self.client_id)).Add(
        self.username).Add(self.approval_id)


class ApiCreateClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = user_pb2.ApiCreateClientApprovalArgs
  rdf_deps = [
      ApiClientApproval,
      api_client.ApiClientId,
  ]


class ApiCreateClientApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user client approval and notifies requested approvers."""

  args_type = ApiCreateClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT

  approval_aff4_type = aff4_security.ClientApproval
  approval_requestor = aff4_security.ClientApprovalRequestor

  def Handle(self, args, token=None):
    result = super(ApiCreateClientApprovalHandler, self).Handle(
        args, token=token)

    if args.keep_client_alive:
      flow.GRRFlow.StartFlow(
          client_id=args.client_id.ToClientURN(),
          flow_name=administrative.KeepAlive.__name__,
          duration=3600,
          token=token)

    return result


class ApiGetClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = user_pb2.ApiGetClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiGetClientApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about an approval for a given client and reason."""

  args_type = ApiGetClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT

  approval_aff4_type = aff4_security.ClientApproval


class ApiGrantClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = user_pb2.ApiGrantClientApprovalArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiGrantClientApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantClientApprovalArgs
  result_type = ApiClientApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT

  approval_aff4_type = aff4_security.ClientApproval
  approval_grantor = aff4_security.ClientApprovalGrantor


class ApiListClientApprovalsArgs(ApiClientApprovalArgsBase):
  protobuf = user_pb2.ApiListClientApprovalsArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiListClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListClientApprovalsResult
  rdf_deps = [
      ApiClientApproval,
  ]


class ApiListClientApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's clients approvals."""

  args_type = ApiListClientApprovalsArgs
  result_type = ApiListClientApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiClientApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def _CheckClientId(self, client_id, approval):
    subject = approval.Get(approval.Schema.SUBJECT)
    return subject.Basename() == client_id

  def _CheckState(self, state, approval):
    try:
      approval.CheckAccess(approval.token)
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

  def HandleLegacy(self, args, token=None):
    filter_func = self._BuildFilter(args)

    approvals, subjects_by_urn = self._GetApprovals(
        "client", args.offset, args.count, filter_func=filter_func, token=token)
    return ApiListClientApprovalsResult(
        items=self._HandleApprovals(approvals, subjects_by_urn,
                                    self._ApprovalToApiApproval))

  def HandleRelationalDB(self, args, token=None):
    subject_id = None
    if args.client_id:
      subject_id = utils.SmartStr(args.client_id)

    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            token.username,
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
    items = itertools.islice(approvals, args.offset, end)

    return ApiListClientApprovalsResult(items=list(items))

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      return self.HandleRelationalDB(args, token=token)
    else:
      return self.HandleLegacy(args, token=token)


class ApiHuntApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return self.hunt_id.ToURN()

  def BuildSubjectId(self):
    return utils.SmartStr(self.hunt_id)

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.BuildSubjectUrn().Path()).Add(
        self.username).Add(self.approval_id)


class ApiCreateHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = user_pb2.ApiCreateHuntApprovalArgs
  rdf_deps = [
      ApiHuntApproval,
      api_hunt.ApiHuntId,
  ]


class ApiCreateHuntApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user hunt approval and notifies requested approvers."""

  args_type = ApiCreateHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT

  approval_obj_type = aff4_security.HuntApproval
  approval_requestor = aff4_security.HuntApprovalRequestor


class ApiGetHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = user_pb2.ApiGetHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiGetHuntApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given hunt, user and approval id."""

  args_type = ApiGetHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT

  approval_obj_type = aff4_security.HuntApproval


class ApiGrantHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = user_pb2.ApiGrantHuntApprovalArgs
  rdf_deps = [
      api_hunt.ApiHuntId,
  ]


class ApiGrantHuntApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_type = rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_HUNT

  approval_aff4_type = aff4_security.HuntApproval
  approval_grantor = aff4_security.HuntApprovalGrantor


class ApiListHuntApprovalsArgs(ApiHuntApprovalArgsBase):
  protobuf = user_pb2.ApiListHuntApprovalsArgs


class ApiListHuntApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListHuntApprovalsResult
  rdf_deps = [
      ApiHuntApproval,
  ]


class ApiListHuntApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's hunts approvals."""

  args_type = ApiListHuntApprovalsArgs
  result_type = ApiListHuntApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiHuntApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def HandleLegacy(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "hunt", args.offset, args.count, token=token)
    return ApiListHuntApprovalsResult(
        items=self._HandleApprovals(approvals, subjects_by_urn,
                                    self._ApprovalToApiApproval))

  def HandleRelationalDB(self, args, token=None):
    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            token.username,
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

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      return self.HandleRelationalDB(args, token=token)
    else:
      return self.HandleLegacy(args, token=token)


class ApiCronJobApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return self.cron_job_id.ToURN()

  def BuildSubjectId(self):
    return utils.SmartStr(self.cron_job_id)

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.BuildSubjectUrn().Path()).Add(
        self.username).Add(self.approval_id)


class ApiCreateCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = user_pb2.ApiCreateCronJobApprovalArgs
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

  approval_aff4_type = aff4_security.CronJobApproval
  approval_requestor = aff4_security.CronJobApprovalRequestor


class ApiGetCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = user_pb2.ApiGetCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiGetCronJobApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given cron, user and approval id."""

  args_type = ApiGetCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_type = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)

  approval_aff4_type = aff4_security.CronJobApproval


class ApiGrantCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = user_pb2.ApiGrantCronJobApprovalArgs
  rdf_deps = [
      api_cron.ApiCronJobId,
  ]


class ApiGrantCronJobApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_type = (
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CRON_JOB)

  approval_aff4_type = aff4_security.CronJobApproval
  approval_grantor = aff4_security.CronJobApprovalGrantor


class ApiListCronJobApprovalsArgs(ApiCronJobApprovalArgsBase):
  protobuf = user_pb2.ApiListCronJobApprovalsArgs


class ApiListCronJobApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListCronJobApprovalsResult
  rdf_deps = [
      ApiCronJobApproval,
  ]


class ApiListCronJobApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's cron jobs approvals."""

  args_type = ApiListCronJobApprovalsArgs
  result_type = ApiListCronJobApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiCronJobApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def HandleLegacy(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "cron", args.offset, args.count, token=token)
    return ApiListCronJobApprovalsResult(
        items=self._HandleApprovals(approvals, subjects_by_urn,
                                    self._ApprovalToApiApproval))

  def HandleRelationalDB(self, args, token=None):
    approvals = sorted(
        data_store.REL_DB.ReadApprovalRequests(
            token.username,
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

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(data_store.READ_CATEGORY_APPROVALS):
      return self.HandleRelationalDB(args, token=token)
    else:
      return self.HandleLegacy(args, token=token)


class ApiGetOwnGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Renders current user settings."""

  result_type = ApiGrrUser

  def __init__(self, interface_traits=None):
    super(ApiGetOwnGrrUserHandler, self).__init__()
    self.interface_traits = interface_traits

  def Handle(self, unused_args, token=None):
    """Fetches and renders current user's settings."""

    result = ApiGrrUser(username=token.username)

    if data_store.RelationalDBReadEnabled():
      user_record = data_store.REL_DB.ReadGRRUser(token.username)
      result.InitFromDatabaseObject(user_record)
    else:
      try:
        user_record = aff4.FACTORY.Open(
            aff4.ROOT_URN.Add("users").Add(token.username),
            aff4_users.GRRUser,
            token=token)

        result.InitFromAff4Object(user_record)
      except IOError:
        result.settings = aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

    result.interface_traits = (
        self.interface_traits or ApiGrrUserInterfaceTraits())

    return result


class ApiUpdateGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Sets current user settings."""

  args_type = ApiGrrUser

  def Handle(self, args, token=None):
    if args.username or args.HasField("interface_traits"):
      raise ValueError("Only user settings can be updated.")

    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="w",
        token=token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS(args.settings))

    if data_store.RelationalDBWriteEnabled():
      data_store.REL_DB.WriteGRRUser(
          token.username,
          ui_mode=args.settings.mode,
          canary_mode=args.settings.canary_mode)


class ApiGetPendingUserNotificationsCountResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiGetPendingUserNotificationsCountResult


class ApiGetPendingUserNotificationsCountHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  result_type = ApiGetPendingUserNotificationsCountResult

  def Handle(self, args, token=None):
    """Fetches the pending notification count."""

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=token)

    notifications = user_record.Get(user_record.Schema.PENDING_NOTIFICATIONS)

    return ApiGetPendingUserNotificationsCountResult(count=len(notifications))


class ApiListPendingUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListPendingUserNotificationsArgs
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiListPendingUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListPendingUserNotificationsResult
  rdf_deps = [
      ApiNotification,
  ]


class ApiListPendingUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns pending notifications for the current user."""

  args_type = ApiListPendingUserNotificationsArgs
  result_type = ApiListPendingUserNotificationsResult

  def Handle(self, args, token=None):
    """Fetches the pending notifications."""

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=token)

    notifications = user_record.Get(user_record.Schema.PENDING_NOTIFICATIONS)

    result = [
        ApiNotification().InitFromNotification(n, is_pending=True)
        for n in notifications
        if n.timestamp > args.timestamp
    ]

    return ApiListPendingUserNotificationsResult(items=result)


class ApiDeletePendingUserNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiDeletePendingUserNotificationArgs
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class ApiDeletePendingUserNotificationHandler(
    api_call_handler_base.ApiCallHandler):
  """Removes the pending notification with the given timestamp."""

  args_type = ApiDeletePendingUserNotificationArgs

  def Handle(self, args, token=None):
    """Deletes the notification from the pending notifications."""
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=token) as user_record:
      user_record.DeletePendingNotification(args.timestamp)


class ApiListAndResetUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListAndResetUserNotificationsArgs


class ApiListAndResetUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListAndResetUserNotificationsResult
  rdf_deps = [
      ApiNotification,
  ]


class ApiListAndResetUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  args_type = ApiListAndResetUserNotificationsArgs
  result_type = ApiListAndResetUserNotificationsResult

  def Handle(self, args, token=None):
    """Fetches the user notifications."""

    user_record = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=token)

    result = []

    pending_notifications = user_record.Get(
        user_record.Schema.PENDING_NOTIFICATIONS)

    # Hack for sorting. Requires retrieval of all notifications.
    notifications = list(user_record.ShowNotifications(reset=True))
    notifications = sorted(
        notifications, key=lambda x: x.timestamp, reverse=True)

    total_count = len(notifications)

    if args.filter:
      notifications = [
          n for n in notifications if args.filter.lower() in n.message.lower()
      ]

    if not args.count:
      args.count = 50

    start = args.offset
    end = args.offset + args.count
    for notification in notifications[start:end]:
      item = ApiNotification().InitFromNotification(
          notification, is_pending=(notification in pending_notifications))
      result.append(item)

    return ApiListAndResetUserNotificationsResult(
        items=result, total_count=total_count)


class ApiListPendingGlobalNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiListPendingGlobalNotificationsResult
  rdf_deps = [
      aff4_users.GlobalNotification,
  ]


class ApiListPendingGlobalNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the pending global notifications for the current user."""

  result_type = ApiListPendingGlobalNotificationsResult

  def Handle(self, args, token=None):
    """Fetches the list of pending global notifications."""

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=token)

    notifications = user_record.GetPendingGlobalNotifications()

    return ApiListPendingGlobalNotificationsResult(items=notifications)


class ApiDeletePendingGlobalNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = user_pb2.ApiDeletePendingGlobalNotificationArgs


class ApiDeletePendingGlobalNotificationHandler(
    api_call_handler_base.ApiCallHandler):
  """Deletes the global notification from the list of unseen notifications."""

  args_type = ApiDeletePendingGlobalNotificationArgs

  def Handle(self, args, token=None):
    """Marks the given global notification as seen."""

    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=token) as user_record:

      notifications = user_record.GetPendingGlobalNotifications()
      for notif in notifications:
        if notif.type == args.type:
          user_record.MarkGlobalNotificationAsShown(notif)
          return

    raise GlobalNotificationNotFoundError()
