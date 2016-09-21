#!/usr/bin/env python
"""API handlers for user-related data and actions."""

import functools
import os

from grr.gui import api_call_handler_base

from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import cron as api_cron
from grr.gui.api_plugins import hunt as api_hunt

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import cronjobs as aff4_cronjobs
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.flows.general import administrative

from grr.lib.hunts import implementation

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class GlobalNotificationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raised when a specific global notification could not be found."""


class ApiGrrUserInterfaceTraits(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGrrUserInterfaceTraits

  def EnableAll(self):
    for type_descriptor in self.type_infos:
      self.Set(type_descriptor.name, True)

    return self


class ApiGrrUser(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGrrUser


def _InitApiApprovalFromAff4Object(api_approval, approval_obj):
  """Initializes Api(Client|Hunt|CronJob)Approval from an AFF4 object."""

  api_approval.id = approval_obj.urn.Basename()
  api_approval.reason = approval_obj.Get(approval_obj.Schema.REASON)

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
    api_approval.notified_users = sorted(u.strip()
                                         for u in notified_users.split(","))

  email_cc = approval_obj.Get(approval_obj.Schema.EMAIL_CC)
  email_cc_addresses = sorted(s.strip() for s in email_cc.split(","))
  api_approval.email_cc_addresses = (
      set(email_cc_addresses) - set(api_approval.notified_users))

  api_approval.approvers = sorted(approval_obj.GetNonExpiredApprovers())
  return api_approval


class ApiClientApproval(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientApproval

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          approval_obj.Get(approval_obj.Schema.SUBJECT),
          aff4_type=aff4_grr.VFSGRRClient,
          token=approval_obj.token)
    self.subject = api_client.ApiClient().InitFromAff4Object(
        approval_subject_obj)

    return _InitApiApprovalFromAff4Object(self, approval_obj)


class ApiHuntApproval(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntApproval

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          approval_obj.Get(approval_obj.Schema.SUBJECT),
          aff4_type=implementation.GRRHunt,
          token=approval_obj.token)
    self.subject = api_hunt.ApiHunt().InitFromAff4Object(approval_subject_obj)

    return _InitApiApprovalFromAff4Object(self, approval_obj)


class ApiCronJobApproval(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCronJobApproval

  def InitFromAff4Object(self, approval_obj, approval_subject_obj=None):
    if not approval_subject_obj:
      approval_subject_obj = aff4.FACTORY.Open(
          approval_obj.Get(approval_obj.Schema.SUBJECT),
          aff4_type=aff4_cronjobs.CronJob,
          token=approval_obj.token)
    self.subject = api_cron.ApiCronJob().InitFromAff4Object(
        approval_subject_obj)

    return _InitApiApprovalFromAff4Object(self, approval_obj)


class ApiCreateApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class for all Crate*Approval handlers."""

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  # Flow to be used to grant the approval. Flow class is expected. Should be set
  # by a subclass.
  approval_create_flow = None

  def Handle(self, args, token=None):
    if not args.approval.reason:
      raise ValueError("Approval reason can't be empty.")

    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=self.__class__.approval_create_flow.__name__,
        reason=args.approval.reason,
        approver=",".join(args.approval.notified_users),
        email_cc_address=",".join(args.approval.email_cc_addresses),
        subject_urn=args.BuildSubjectUrn(),
        token=token)

    flow_fd = aff4.FACTORY.Open(flow_urn, aff4_type=flow.GRRFlow, token=token)
    approval_urn = flow_fd.state.approval_urn

    approval_obj = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.__class__.approval_aff4_type,
        age=aff4.ALL_TIMES,
        token=token)

    return self.__class__.result_type().InitFromAff4Object(approval_obj)


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
      if cur_offset < offset:
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


class ApiGetApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class for all Get*Approval handlers."""

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  def Handle(self, args, token=None):
    approval_urn = args.BuildApprovalObjUrn()
    approval_obj = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.__class__.approval_aff4_type,
        age=aff4.ALL_TIMES,
        token=token)
    return self.__class__.result_type().InitFromAff4Object(approval_obj)


class ApiGrantApprovalHandlerBase(api_call_handler_base.ApiCallHandler):
  """Base class reused by all client approval handlers."""

  # AFF4 type of the approval object to be checked. Should be set by a subclass.
  approval_aff4_type = None

  # Flow to be used to grant the approval. Flow class is expected. Should be set
  # by a subclass.
  approval_grant_flow = None

  def Handle(self, args, token=None):
    subject_urn = args.BuildSubjectUrn()
    approval_urn = args.BuildApprovalObjUrn()

    approval_request = aff4.FACTORY.Open(
        approval_urn, aff4_type=self.__class__.approval_aff4_type, token=token)
    reason = approval_request.Get(approval_request.Schema.REASON)

    flow.GRRFlow.StartFlow(
        flow_name=self.__class__.approval_grant_flow.__name__,
        reason=reason,
        delegate=args.username,
        subject_urn=subject_urn,
        token=token)

    approval_request = aff4.FACTORY.Open(
        approval_urn,
        aff4_type=self.__class__.approval_aff4_type,
        age=aff4.ALL_TIMES,
        token=token)
    return self.__class__.result_type().InitFromAff4Object(approval_request)


class ApiClientApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return self.client_id

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.client_id.Basename()).Add(
        self.username).Add(self.approval_id)


class ApiCreateClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_pb2.ApiCreateClientApprovalArgs


class ApiCreateClientApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user client approval and notifies requested approvers."""

  args_type = ApiCreateClientApprovalArgs
  result_type = ApiClientApproval

  approval_obj_type = aff4_security.ClientApproval
  approval_create_flow = aff4_security.RequestClientApprovalFlow

  def Handle(self, args, token=None):
    result = super(ApiCreateClientApprovalHandler, self).Handle(
        args, token=token)

    if args.keep_client_alive:
      flow.GRRFlow.StartFlow(
          client_id=args.client_id,
          flow_name=administrative.KeepAlive.__name__,
          duration=3600,
          token=token)

    return result


class ApiGetClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_pb2.ApiGetClientApprovalArgs


class ApiGetClientApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about an approval for a given client and reason."""

  args_type = ApiGetClientApprovalArgs
  result_type = ApiClientApproval

  approval_obj_type = aff4_security.ClientApproval


class ApiGrantClientApprovalArgs(ApiClientApprovalArgsBase):
  protobuf = api_pb2.ApiGrantClientApprovalArgs


class ApiGrantClientApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantClientApprovalArgs
  result_type = ApiClientApproval

  approval_aff4_type = aff4_security.ClientApproval
  approval_grant_flow = aff4_security.GrantClientApprovalFlow


class ApiListClientApprovalsArgs(ApiClientApprovalArgsBase):
  protobuf = api_pb2.ApiListClientApprovalsArgs


class ApiListClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListClientApprovalsResult


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

  def Handle(self, args, token=None):
    filter_func = self._BuildFilter(args)

    approvals, subjects_by_urn = self._GetApprovals(
        "client", args.offset, args.count, filter_func=filter_func, token=token)
    return ApiListClientApprovalsResult(items=self._HandleApprovals(
        approvals, subjects_by_urn, self._ApprovalToApiApproval))


class ApiHuntApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return aff4.ROOT_URN.Add("hunts").Add(self.hunt_id)

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.BuildSubjectUrn().Path()).Add(
        self.username).Add(self.approval_id)


class ApiCreateHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_pb2.ApiCreateHuntApprovalArgs


class ApiCreateHuntApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user hunt approval and notifies requested approvers."""

  args_type = ApiCreateHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_obj_type = aff4_security.HuntApproval
  approval_create_flow = aff4_security.RequestHuntApprovalFlow


class ApiGetHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_pb2.ApiGetHuntApprovalArgs


class ApiGetHuntApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given hunt, user and approval id."""

  args_type = ApiGetHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_obj_type = aff4_security.HuntApproval


class ApiGrantHuntApprovalArgs(ApiHuntApprovalArgsBase):
  protobuf = api_pb2.ApiGrantHuntApprovalArgs


class ApiGrantHuntApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantHuntApprovalArgs
  result_type = ApiHuntApproval

  approval_aff4_type = aff4_security.HuntApproval
  approval_grant_flow = aff4_security.GrantHuntApprovalFlow


class ApiListHuntApprovalsArgs(ApiHuntApprovalArgsBase):
  protobuf = api_pb2.ApiListHuntApprovalsArgs


class ApiListHuntApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntApprovalsResult


class ApiListHuntApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's hunts approvals."""

  args_type = ApiListHuntApprovalsArgs
  result_type = ApiListHuntApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiHuntApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def Handle(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "hunt", args.offset, args.count, token=token)
    return ApiListHuntApprovalsResult(items=self._HandleApprovals(
        approvals, subjects_by_urn, self._ApprovalToApiApproval))


class ApiCronJobApprovalArgsBase(rdf_structs.RDFProtoStruct):

  __abstract = True  # pylint: disable=g-bad-name

  def BuildSubjectUrn(self):
    return aff4.ROOT_URN.Add("cron").Add(self.cron_job_id)

  def BuildApprovalObjUrn(self):
    return aff4.ROOT_URN.Add("ACL").Add(self.BuildSubjectUrn().Path()).Add(
        self.username).Add(self.approval_id)


class ApiCreateCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_pb2.ApiCreateCronJobApprovalArgs


class ApiCreateCronJobApprovalHandler(ApiCreateApprovalHandlerBase):
  """Creates new user cron approval and notifies requested approvers."""

  args_type = ApiCreateCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_aff4_type = aff4_security.CronJobApproval
  approval_create_flow = aff4_security.RequestCronJobApprovalFlow


class ApiGetCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_pb2.ApiGetCronJobApprovalArgs


class ApiGetCronJobApprovalHandler(ApiGetApprovalHandlerBase):
  """Returns details about approval for a given cron, user and approval id."""

  args_type = ApiGetCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_aff4_type = aff4_security.CronJobApproval


class ApiGrantCronJobApprovalArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_pb2.ApiGrantCronJobApprovalArgs


class ApiGrantCronJobApprovalHandler(ApiGrantApprovalHandlerBase):

  args_type = ApiGrantCronJobApprovalArgs
  result_type = ApiCronJobApproval

  approval_aff4_type = aff4_security.CronJobApproval
  approval_grant_flow = aff4_security.GrantCronJobApprovalFlow


class ApiListCronJobApprovalsArgs(ApiCronJobApprovalArgsBase):
  protobuf = api_pb2.ApiListCronJobApprovalsArgs


class ApiListCronJobApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListCronJobApprovalsResult


class ApiListCronJobApprovalsHandler(ApiListApprovalsHandlerBase):
  """Returns list of user's cron jobs approvals."""

  args_type = ApiListCronJobApprovalsArgs
  result_type = ApiListCronJobApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    return ApiCronJobApproval().InitFromAff4Object(
        approval_obj, approval_subject_obj=subject)

  def Handle(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "cron", args.offset, args.count, token=token)
    return ApiListCronJobApprovalsResult(items=self._HandleApprovals(
        approvals, subjects_by_urn, self._ApprovalToApiApproval))


class ApiGetGrrUserHandler(api_call_handler_base.ApiCallHandler):
  """Renders current user settings."""

  result_type = ApiGrrUser

  def __init__(self, interface_traits=None):
    super(ApiGetGrrUserHandler, self).__init__()
    self.interface_traits = interface_traits

  def Handle(self, unused_args, token=None):
    """Fetches and renders current user's settings."""

    result = ApiGrrUser(username=token.username)

    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(token.username),
          aff4_users.GRRUser,
          token=token)

      result.settings = user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      result.settings = aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

    result.interface_traits = (self.interface_traits or
                               ApiGrrUserInterfaceTraits())

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


class ApiGetPendingUserNotificationsCountResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetPendingUserNotificationsCountResult


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
  protobuf = api_pb2.ApiListPendingUserNotificationsArgs


class ApiListPendingUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListPendingUserNotificationsResult


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

    result = [ApiNotification().InitFromNotification(
        n, is_pending=True) for n in notifications
              if n.timestamp > args.timestamp]

    return ApiListPendingUserNotificationsResult(items=result)


class ApiDeletePendingUserNotificationArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiDeletePendingUserNotificationArgs


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
  protobuf = api_pb2.ApiListAndResetUserNotificationsArgs


class ApiListAndResetUserNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListAndResetUserNotificationsResult


class ApiNotification(rdf_structs.RDFProtoStruct):
  """Represents a user notification."""

  protobuf = api_pb2.ApiNotification

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
      elif len(components) == 1 and rdf_client.ClientURN.Validate(components[
          0]):
        self.reference.type = reference_type_enum.DISCOVERY
        self.reference.discovery.client_id = components[0]
      else:
        path = notification.subject.Path()
        for prefix in aff4_grr.VFSGRRClient.AFF4_PREFIXES.values():
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


class ApiNotificationReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationReference


class ApiNotificationDiscoveryReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationDiscoveryReference


class ApiNotificationHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationHuntReference


class ApiNotificationCronReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationCronReference


class ApiNotificationFlowReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationFlowReference


class ApiNotificationVfsReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationVfsReference


class ApiNotificationClientApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationClientApprovalReference


class ApiNotificationHuntApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationHuntApprovalReference


class ApiNotificationCronJobApprovalReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationCronJobApprovalReference


class ApiNotificationUnknownReference(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiNotificationUnknownReference


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

    return ApiListAndResetUserNotificationsResult(
        items=result, total_count=total_count)


class ApiListPendingGlobalNotificationsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListPendingGlobalNotificationsResult


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
  protobuf = api_pb2.ApiDeletePendingGlobalNotificationArgs


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
