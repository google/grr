#!/usr/bin/env python
"""API renderers for user-related data and actions."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderer_base
from grr.gui import api_value_renderers

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import utils
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "User"


class ApiUserApprovalsListRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiUserApprovalsListRendererArgs


class ApiUserApprovalsListRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders list of all user approvals."""

  category = CATEGORY
  args_type = ApiUserApprovalsListRendererArgs

  def Render(self, args, token=None):
    approvals_base_urn = aff4.ROOT_URN.Add("users").Add(token.username).Add(
        "approvals").Add(args.approval_type.name.lower())

    all_children = aff4.FACTORY.RecursiveMultiListChildren(
        [approvals_base_urn], token=token)

    approvals_urns = []
    for subject, children in all_children:
      # We only want to process leaf nodes.
      if children:
        continue
      approvals_urns.append(subject)

    approvals_urns.sort(key=lambda x: x.age, reverse=True)
    if args.count:
      right_edge = args.offset + args.count
    else:
      right_edge = len(approvals_urns)
    approvals_urns = approvals_urns[args.offset:right_edge]

    approvals = list(aff4.FACTORY.MultiOpen(
        approvals_urns, mode="r", aff4_type=aff4_security.Approval.__name__,
        age=aff4.ALL_TIMES, token=token))
    subjects_urns = [a.Get(a.Schema.SUBJECT) for a in approvals]
    subjects_by_urn = {}
    for subject in aff4.FACTORY.MultiOpen(subjects_urns, mode="r",
                                          token=token):
      subjects_by_urn[subject.urn] = subject

    rendered_approvals_by_urn = {}
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

      rendered_approvals_by_urn[approval.symlink_urn
                                or approval.urn] = rendered_approval

    items = []
    for urn in approvals_urns:
      try:
        items.append(rendered_approvals_by_urn[urn])
      except KeyError:
        pass

    return dict(items=items, offset=args.offset, count=len(items))


class ApiUserSettingsRenderer(api_call_renderer_base.ApiCallRenderer):
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


class ApiSetUserSettingsRenderer(api_call_renderer_base.ApiCallRenderer):
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
