#!/usr/bin/env python
"""API renderers for user-related data and actions."""

from grr.gui import api_call_renderer_base
from grr.gui import api_value_renderers

from grr.lib import aff4
from grr.lib.aff4_objects import users as aff4_users


CATEGORY = "Settings"


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
