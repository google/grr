#!/usr/bin/env python
"""This plugin renders the client search page."""
import urllib

from grr.gui import renderers
from grr.gui.plugins import forms
from grr.gui.plugins import semantic

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

from grr.lib.aff4_objects import users as aff4_users


class NotificationCount(renderers.TemplateRenderer):
  """Display the number of outstanding notifications."""

  def RenderAjax(self, request, response):
    """Return the count on unseen notifications."""
    response = super(NotificationCount, self).RenderAjax(request, response)
    number = 0

    try:
      user_fd = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(request.user),
          token=request.token)
      notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)
      if notifications:
        number = len(notifications)
    except IOError:
      pass

    return renderers.JsonResponse(dict(number=number))


class NotificationBar(renderers.TemplateRenderer):
  """Render a notification bar for the user."""

  layout_template = renderers.Template("""
<div id="notification_dialog" class="modal wide-modal" tabindex="-1"
  role="dialog" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal"
          aria-hidden="true">x</button>
        <h3>Notifications for {{this.user|escape}}</h3>
      </div>
      <div class="modal-body" id="notification_dialog_body">
      </div>
      <div class="modal-footer">
        <button class="btn btn-default" data-dismiss="modal" aria-hidden="true">
          Close
        </button>
      </div>
    </div>
  </div>
</div>

<div id="user_settings_dialog" class="modal" tabindex="-1"
  role="dialog" aria-hidden="true">
</div>

<ul class="nav pull-left">
  <li><p class="navbar-text">User: {{this.user|escape}}</p></li>
</ul>

<div id="notifications_and_settings" class="pull-right navbar-form">
  <button id="notification_button" class="btn btn-info"
         data-toggle="modal" data-target="#notification_dialog"
         style="margin-right: 10px" />
</div>
""")

  def Layout(self, request, response):
    """Show the number of notifications outstanding for the user."""
    self.user = request.user
    response = super(NotificationBar, self).Layout(request, response)
    return self.CallJavascript(response, "Layout")


class UpdateSettingsFlow(flow.GRRFlow):
  """Update the User's GUI settings."""
  # This flow can run without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  args_type = aff4_users.GUISettings

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type=aff4_users.GRRUser,
        mode="w",
        token=self.token) as user_fd:
      user_fd.Set(user_fd.Schema.GUI_SETTINGS(self.args))


class UserSettingsDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that allows user to change his settings."""

  header = "Settings"
  proceed_button_title = "Apply"

  content_template = renderers.Template("""
{{this.user_settings_form|safe}}
""")

  ajax_template = renderers.Template("""
Settings were successfully updated. Reloading...
""")

  def GetUserSettings(self, request):
    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(request.user),
          aff4_users.GRRUser,
          token=request.token)

      return user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      return aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

  def Layout(self, request, response):
    user_settings = self.GetUserSettings(request)
    self.user_settings_form = forms.SemanticProtoFormRenderer(
        proto_obj=user_settings, prefix="settings").RawHTML(request)

    return super(UserSettingsDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Ajax hanlder for this renderer."""
    settings = forms.SemanticProtoFormRenderer(
        proto_obj=aff4_users.GUISettings(),
        prefix="settings").ParseArgs(request)

    flow.GRRFlow.StartFlow(flow_name="UpdateSettingsFlow",
                           args=settings,
                           token=request.token)

    response = self.RenderFromTemplate(self.ajax_template,
                                       response,
                                       unique=self.unique)
    return self.CallJavascript(response, "RenderAjax")


class ResetUserNotifications(flow.GRRFlow):
  """A flow to reset user's notifications."""

  # This flow can run without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  @flow.StateHandler()
  def Start(self):
    user_fd = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=self.token)
    user_fd.ShowNotifications(reset=True)


class ViewNotifications(renderers.TableRenderer):
  """Render the notifications for the user."""

  target_template = renderers.Template("""
<a href="/#{{hash|escape}}" target_hash="{{hash|escape}}"
   notification_type="{{notification_type|escape}}">{{target}}</span>""")

  layout_template = renderers.TableRenderer.layout_template

  def __init__(self, **kwargs):
    renderers.TableRenderer.__init__(self, **kwargs)

    self.AddColumn(semantic.RDFValueColumn("Timestamp"))
    self.AddColumn(semantic.RDFValueColumn("Message", width="100%"))
    self.AddColumn(semantic.RDFValueColumn("Target"))

  def Layout(self, request, response):
    response = super(ViewNotifications, self).Layout(request, response)
    return self.CallJavascript(response, "ViewNotifications.Layout")

  def BuildTable(self, start_row, end_row, request):
    """Add all the notifications to this table."""
    row_index = 0
    search_term = request.REQ.get("sSearch")

    # We modify this object by changing the notification from pending to
    # shown.
    try:
      user_fd = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(request.user),
          aff4_type=aff4_users.GRRUser,
          token=request.token)
    except IOError:
      return

    # Hack for sorting. Requires retrieval of all notifications.
    notifications = list(user_fd.ShowNotifications(reset=False))
    for notification in sorted(notifications,
                               key=lambda x: x.timestamp,
                               reverse=True):
      if row_index < start_row:
        continue
      if row_index > end_row:
        break

      if (search_term and
          search_term.lower() not in notification.message.lower()):
        continue

      row = {"Message": notification.message,
             "Target": self.FormatFromTemplate(
                 self.target_template,
                 hash=self.BuildHashFromNotification(notification),
                 notification_type=notification.type,
                 target=notification.subject),
             "Timestamp": rdfvalue.RDFDatetime(notification.timestamp)}
      self.AddRow(row, row_index)
      row_index += 1

    flow.GRRFlow.StartFlow(flow_name="ResetUserNotifications",
                           token=request.token)

  @staticmethod
  def BuildHashFromNotification(notification):
    """Navigate to the most appropriate location for this navigation."""
    h = {}

    # Still display if subject doesn't get set, this will appear in the GUI with
    # a target of "None"
    urn = "/"
    if notification.subject is not None:
      urn = notification.subject

    # General Host information
    if notification.type == "Discovery":
      path = rdfvalue.RDFURN(urn)
      components = path.Path().split("/")[1:]
      h["c"] = components[0]
      h["main"] = "HostInformation"

    elif notification.type == "DownloadFile":
      h["aff4_path"] = notification.subject
      h["main"] = "DownloadFile"

    elif notification.type == "ViewObject":
      path = rdfvalue.RDFURN(urn)
      components = path.Path().split("/")[1:]
      if len(components) == 2 and components[0] == "hunts":
        h["hunt_id"] = notification.subject
        h["main"] = "ManageHunts"
      elif len(components) == 2 and components[0] == "cron":
        h["cron_job_urn"] = notification.subject
        h["main"] = "ManageCron"
      elif len(components) == 3 and components[1] == "flows":
        h["flow"] = notification.subject
        h["c"] = components[0]
        h["main"] = "ManageFlows"
      else:
        h["c"] = components[0]
        h["aff4_path"] = notification.subject
        h["t"] = renderers.DeriveIDFromPath("/".join(components[1:-1]))
        h["main"] = "VirtualFileSystemView"

    # Error with a flow
    elif notification.type == "FlowStatus":
      path = rdfvalue.RDFURN(urn)
      components = path.Path().split("/")[1:]
      h["flow"] = notification.source
      h["c"] = components[0]
      h["main"] = "ManageFlows"

    elif notification.type == "GrantAccess":
      h["main"] = "GrantAccess"
      h["acl"] = notification.subject

    return urllib.urlencode(dict([(x, utils.SmartStr(y)) for x, y in h.items()
                                 ]))
