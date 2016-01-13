#!/usr/bin/env python
"""API handlers for user-related data and actions."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers

from grr.gui.api_plugins import client as api_client

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import utils
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "User"


class ApiUserClientApproval(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiUserClientApproval


class ApiListUserClientApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserClientApprovalsArgs


class ApiListUserClientApprovalsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserClientApprovalsResult


class ApiListUserHuntApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserHuntApprovalsArgs


class ApiListUserCronApprovalsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListUserCronApprovalsArgs


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


class ApiListUserClientApprovalsHandler(ApiListUserApprovalsHandlerBase):
  """Returns list of user's clients approvals."""

  args_type = ApiListUserClientApprovalsArgs
  result_type = ApiListUserClientApprovalsResult

  def _ApprovalToApiApproval(self, approval_obj, subject):
    result = ApiUserClientApproval(
        subject=api_client.ApiGetClientHandler.VFSGRRClientToApiClient(subject),
        reason=approval_obj.Get(approval_obj.Schema.REASON))

    try:
      approval_obj.CheckAccess(approval_obj.token)
      result.is_valid = True
    except access_control.UnauthorizedAccess as e:
      result.is_valid = False
      result.is_valid_message = utils.SmartStr(e)

    return result

  def Handle(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "client", args.offset, args.count, token=token)
    return ApiListUserClientApprovalsResult(
        items=self._HandleApprovals(approvals, subjects_by_urn,
                                    self._ApprovalToApiApproval))


class ApiListUserHuntApprovalsHandler(ApiListUserApprovalsHandlerBase):
  """Returns list of user's hunts approvals."""

  args_type = ApiListUserHuntApprovalsArgs

  def Render(self, args, token=None):
    approvals, subjects_by_urn = self._GetApprovals(
        "hunt", args.offset, args.count, token=token)
    return self._RenderApprovals(approvals, subjects_by_urn)


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
