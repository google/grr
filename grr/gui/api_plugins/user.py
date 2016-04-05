#!/usr/bin/env python
"""API handlers for user-related data and actions."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.gui.api_plugins import client as api_client

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "User"


class ApiUserClientApproval(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiUserClientApproval

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          approval_obj.Get(approval_obj.Schema.SUBJECT),
          aff4_type=aff4_grr.VFSGRRClient.__name__,
          token=approval_obj.token)

    self.subject = api_client.ApiClient().InitFromAff4Object(
        approval_subject_obj)
    self.reason = approval_obj.Get(approval_obj.Schema.REASON)

    try:
      approval_obj.CheckAccess(approval_obj.token)
      self.is_valid = True
    except access_control.UnauthorizedAccess as e:
      self.is_valid = False
      self.is_valid_message = utils.SmartStr(e)

    notified_users = approval_obj.Get(approval_obj.Schema.NOTIFIED_USERS)
    if notified_users:
      self.notified_users = sorted(u.strip() for u in notified_users.split(","))

    email_cc = approval_obj.Get(approval_obj.Schema.EMAIL_CC)
    email_cc_addresses = sorted(s.strip() for s in email_cc.split(","))
    self.email_cc_addresses = set(email_cc_addresses) - set(self.notified_users)

    self.approvers = sorted(approval_obj.GetNonExpiredApprovers())

    return self


class ApiCreateUserClientApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCreateUserClientApprovalArgs


class ApiCreateUserClientApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Creates new user client approval and notifies requested approvers."""

  category = CATEGORY

  # We return a single object and have to preserve type information of all
  # the fields.
  strip_json_root_fields_types = False

  args_type = ApiCreateUserClientApprovalArgs
  result_type = ApiUserClientApproval

  def Handle(self, args, token=None):
    if not args.approval.reason:
      raise ValueError("Approval reason can't be empty.")

    flow.GRRFlow.StartFlow(
        client_id=args.client_id,
        flow_name=aff4_security.RequestClientApprovalFlow.__name__,
        reason=args.approval.reason,
        approver=",".join(args.approval.notified_users),
        email_cc_address=",".join(args.approval.email_cc_addresses),
        subject_urn=args.client_id,
        token=token)

    approval_urn = aff4.ROOT_URN.Add("ACL").Add(args.client_id.Basename()).Add(
        token.username).Add(utils.EncodeReasonString(args.approval.reason))
    approval_obj = aff4.FACTORY.Open(
        approval_urn, aff4_type=aff4_security.ClientApproval.__name__,
        age=aff4.ALL_TIMES, token=token)

    return ApiUserClientApproval().InitFromAff4Object(approval_obj)


class ApiGetUserClientApprovalArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetUserClientApprovalArgs


class ApiGetUserClientApprovalHandler(api_call_handler_base.ApiCallHandler):
  """Returns details about an approval for a given client and reason."""

  category = CATEGORY

  # We return a single object and have to preserve type information of all
  # the fields.
  strip_json_root_fields_types = False

  args_type = ApiGetUserClientApprovalArgs
  result_type = ApiUserClientApproval

  def Handle(self, args, token=None):
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(args.client_id.Basename()).Add(
        token.username).Add(utils.EncodeReasonString(args.reason))
    approval_obj = aff4.FACTORY.Open(
        approval_urn, aff4_type=aff4_security.ClientApproval.__name__,
        age=aff4.ALL_TIMES, token=token)
    return ApiUserClientApproval().InitFromAff4Object(approval_obj)


class ApiListUserApprovalsHandlerBase(api_call_handler_base.ApiCallHandler):
  """Renders list of all user approvals."""

  category = CATEGORY

  def _GetApprovals(self, approval_type, offset, count, token=None):
    approvals_base_urn = aff4.ROOT_URN.Add("users").Add(token.username).Add(
        "approvals").Add(approval_type)

    all_children = aff4.FACTORY.RecursiveMultiListChildren(
        [approvals_base_urn], token=token)

    approvals_urns = []
    for subject, children in all_children:
      # We only want to process leaf nodes.
      if children:
        continue
      approvals_urns.append(subject)

    approvals_urns.sort(key=lambda x: x.age, reverse=True)
    if count:
      right_edge = offset + count
    else:
      right_edge = len(approvals_urns)
    approvals_urns = approvals_urns[offset:right_edge]

    approvals = list(aff4.FACTORY.MultiOpen(
        approvals_urns, mode="r", aff4_type=aff4_security.Approval.__name__,
        age=aff4.ALL_TIMES, token=token))
    approvals_by_urn = {}
    for approval in approvals:
      approvals_by_urn[approval.symlink_urn
                       or approval.urn] = approval
    sorted_approvals = []
    for approval_urn in approvals_urns:
      try:
        sorted_approvals.append(approvals_by_urn[approval_urn])
      except KeyError:
        pass

    subjects_urns = [a.Get(a.Schema.SUBJECT) for a in approvals]
    subjects_by_urn = {}
    for subject in aff4.FACTORY.MultiOpen(subjects_urns, mode="r",
                                          token=token):
      subjects_by_urn[subject.urn] = subject

    return sorted_approvals, subjects_by_urn

  def _RenderApprovals(self, approvals, subjects_by_urn):
    rendered_approvals = []
    for approval in approvals:
      try:
        subject = subjects_by_urn[approval.Get(approval.Schema.SUBJECT)]
      except KeyError:
        continue

      rendered_approval = api_aff4_object_renderers.RenderAFF4Object(approval)
      rendered_approval["subject"] = api_aff4_object_renderers.RenderAFF4Object(
          subject)

      try:
        approval.CheckAccess(approval.token)
        rendered_approval["is_valid"] = True
      except access_control.UnauthorizedAccess as e:
        rendered_approval["is_valid"] = False
        rendered_approval["is_valid_message"] = utils.SmartStr(e)

      rendered_approvals.append(rendered_approval)

    return dict(items=rendered_approvals)

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


class ApiListUserClientApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserClientApprovalsArgs


class ApiListUserClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserClientApprovalsResult


class ApiListUserClientApprovalsHandler(ApiListUserApprovalsHandlerBase):
  """Returns list of user's clients approvals."""

  args_type = ApiListUserClientApprovalsArgs
  result_type = ApiListUserClientApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiUserClientApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def Handle(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "client", args.offset, args.count, token=token)
    return ApiListUserClientApprovalsResult(
        items=self._HandleApprovals(approvals, subjects_by_urn,
                                    self._ApprovalToApiApproval))


class ApiListUserHuntApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserHuntApprovalsArgs


class ApiListUserHuntApprovalsHandler(ApiListUserApprovalsHandlerBase):
  """Returns list of user's hunts approvals."""

  args_type = ApiListUserHuntApprovalsArgs

  def Render(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "hunt", args.offset, args.count, token=token)
    return self._RenderApprovals(approvals, subjects_by_urn)


class ApiListUserCronApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserCronApprovalsArgs


class ApiListUserCronApprovalsHandler(ApiListUserApprovalsHandlerBase):
  """Returns list of user's cron jobs approvals."""

  args_type = ApiListUserCronApprovalsArgs

  def Render(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "cron", args.offset, args.count, token=token)
    return self._RenderApprovals(approvals, subjects_by_urn)


class ApiGetUserSettingsHandler(api_call_handler_base.ApiCallHandler):
  """Renders current user settings."""

  category = CATEGORY

  def GetUserSettings(self, token):
    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(token.username), "GRRUser",
          token=token)

      return user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      return aff4.GRRUser.SchemaCls.GUI_SETTINGS()

  def Render(self, unused_args, token=None):
    """Fetches and renders current user's settings."""

    user_settings = self.GetUserSettings(token)
    return api_value_renderers.RenderValue(user_settings)


class ApiUpdateUserSettingsHandler(api_call_handler_base.ApiCallHandler):
  """Sets current user settings."""

  category = CATEGORY
  args_type = aff4_users.GUISettings
  privileged = True

  def Render(self, args, token=None):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type="GRRUser", mode="w",
        token=token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS(args))

    return dict(status="OK")


class ApiGetUserInfoResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetUserInfoResult


class ApiGetUserInfoHandler(api_call_handler_base.ApiCallHandler):
  """Fetches the user info."""

  category = CATEGORY
  result_type = ApiGetUserInfoResult

  def Handle(self, args, token=None):
    return ApiGetUserInfoResult(username=token.username)


class ApiGetPendingUserNotificationsCountResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetPendingUserNotificationsCountResult


class ApiGetPendingUserNotificationsCountHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  category = CATEGORY
  result_type = ApiGetPendingUserNotificationsCountResult

  def Handle(self, args, token=None):
    """Fetches the pending notification count."""

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username), aff4_type="GRRUser",
        mode="r", token=token)

    notifications = user_record.Get(user_record.Schema.PENDING_NOTIFICATIONS)

    return ApiGetPendingUserNotificationsCountResult(count=len(notifications))


class ApiGetPendingUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetPendingUserNotificationsArgs


class ApiGetPendingUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetPendingUserNotificationsResult


class ApiGetPendingUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the of pending notifications for the current user."""

  category = CATEGORY
  args_type = ApiGetPendingUserNotificationsArgs
  result_type = ApiGetPendingUserNotificationsResult

  def Handle(self, args, token=None):
    """Fetches the pending notification count."""

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username), aff4_type="GRRUser",
        mode="r", token=token)

    notifications = user_record.Get(user_record.Schema.PENDING_NOTIFICATIONS)

    result = [ApiNotification().InitFromNotification(n, is_pending=True)
              for n in notifications
              if n.timestamp > args.timestamp]

    return ApiGetPendingUserNotificationsResult(items=result)


class ApiGetAndResetUserNotificationsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetAndResetUserNotificationsArgs


class ApiGetAndResetUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetAndResetUserNotificationsResult


class ApiNotification(rdf_structs.RDFProtoStruct):
  """Represents a user notification."""

  protobuf = api_pb2.ApiNotification

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
    self._DetermineReference(self.reference, notification)
    return self

  def _DetermineReference(self, reference, notification):
    """Determine the most appropriate location for this notification."""

    reference_type_enum = ApiNotificationReference.Type

    if notification.type == "Discovery":
      components = self._GetUrnComponents(notification)
      reference.type = reference_type_enum.DISCOVERY
      reference.discovery = ApiNotificationDiscoveryReference(
          client_id=components[0])

    elif notification.type == "DownloadFile":
      components = self._GetUrnComponents(notification)
      if len(components) == 2 and components[0] == "hunts":
        # Return a specific notification reference for hunt results
        # in a future CL
        pass
      else:
        path = notification.subject
        reference.type = reference_type_enum.FILE_DOWNLOAD_READY
        reference.file_download_ready = ApiNotificationFileDownloadReference(
            path=path)

    elif notification.type == "ViewObject":
      components = self._GetUrnComponents(notification)
      if len(components) == 2 and components[0] == "hunts":
        reference.type = reference_type_enum.HUNT
        reference.hunt = ApiNotificationHuntReference(
            hunt_urn=notification.subject)
      elif len(components) == 2 and components[0] == "cron":
        reference.type = reference_type_enum.CRON
        reference.cron = ApiNotificationCronReference(
            cron_job_urn=notification.subject)
      elif len(components) == 3 and components[1] == "flows":
        reference.type = reference_type_enum.FLOW
        reference.flow = ApiNotificationFlowReference(
            flow_urn=notification.subject, client_id=components[0])
      else:
        reference.type = reference_type_enum.VFS
        reference.vfs = ApiNotificationVfsReference(
            vfs_path=notification.subject,
            client_id=components[0])

    elif notification.type == "FlowStatus":
      components = self._GetUrnComponents(notification)
      if not components or not rdf_client.ClientURN.Validate(components[0]):
        # No reference to flow errors when the client id is missing.
        return

      reference.type = reference_type_enum.FLOW_STATUS
      reference.flow_status = ApiNotificationFlowStatusReference(
          flow_urn=notification.source,
          client_id=components[0])

    elif notification.type == "GrantAccess":
      reference.type = reference_type_enum.GRANT_ACCESS
      reference.grant_access = ApiNotificationGrantAccessReference(
          acl=notification.subject)

    elif notification.type == "ArchiveGenerationFinished":
      reference.type = reference_type_enum.ARCHIVE_GENERATION_FINISHED
      reference.path = notification.subject

    elif notification.type == "Error":
      reference.type = reference_type_enum.ERROR

  def _GetUrnComponents(self, notification):
    # Still display if subject doesn't get set, this will appear in the GUI with
    # a target of "None"
    urn = "/"
    if notification.subject is not None:
      urn = notification.subject

    path = rdfvalue.RDFURN(urn)
    return path.Path().split("/")[1:]


class ApiNotificationReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationReference


class ApiNotificationDiscoveryReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationDiscoveryReference


class ApiNotificationFileDownloadReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationFileDownloadReference


class ApiNotificationArchiveGenerationFinishedReference(
    rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationArchiveGenerationFinishedReference


class ApiNotificationHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationHuntReference


class ApiNotificationCronReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationCronReference


class ApiNotificationFlowReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationFlowReference


class ApiNotificationVfsReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationVfsReference


class ApiNotificationFlowStatusReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationFlowStatusReference


class ApiNotificationGrantAccessReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationGrantAccessReference


class ApiGetAndResetUserNotificationsHandler(
    api_call_handler_base.ApiCallHandler):
  """Returns the number of pending notifications for the current user."""

  category = CATEGORY
  args_type = ApiGetAndResetUserNotificationsArgs
  result_type = ApiGetAndResetUserNotificationsResult

  def Handle(self, args, token=None):
    """Fetches the user notifications."""

    user_record = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(token.username), aff4_type="GRRUser",
        mode="rw", token=token)

    result = []

    pending_notifications = user_record.Get(
        user_record.Schema.PENDING_NOTIFICATIONS)

    # Hack for sorting. Requires retrieval of all notifications.
    notifications = list(user_record.ShowNotifications(reset=True))
    notifications = sorted(notifications,
                           key=lambda x: x.timestamp, reverse=True)

    total_count = len(notifications)

    if args.filter:
      notifications = [n for n in notifications
                       if args.filter.lower() in n.message.lower()]

    if not args.count:
      args.count = 50

    start = args.offset
    end = args.offset + args.count
    for notification in notifications[start:end]:
      item = ApiNotification().InitFromNotification(
          notification, is_pending=(notification in pending_notifications))
      result.append(item)

    return ApiGetAndResetUserNotificationsResult(
        items=result, total_count=total_count)
