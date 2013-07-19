#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.

"""This plugin renders the client search page."""
import json
import urllib

from django import http

from grr.gui import renderers
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils


class NotificationCount(renderers.TemplateRenderer):
  """Display the number of outstanding notifications."""

  def RenderAjax(self, request, response):
    """Return the count on unseen notifications."""
    response = super(NotificationCount, self).RenderAjax(request, response)
    number = 0

    try:
      user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(
          request.user), token=request.token)
      notifications = user_fd.Get(user_fd.Schema.PENDING_NOTIFICATIONS)
      if notifications:
        number = len(notifications)
    except IOError:
      pass

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(dict(number=number)),
                             mimetype="text/json")


class NotificationBar(renderers.TemplateRenderer):
  """Render a notification bar for the user."""

  layout_template = renderers.Template("""
<div id="notification_dialog" class="modal wide-modal hide" tabindex="-1"
  role="dialog" aria-hidden="true">
  <div class="modal-header">
    <button type="button" class="close" data-dismiss="modal"
      aria-hidden="true">x</button>
    <h3>Notifications for {{this.user|escape}}</h3>
  </div>
  <div class="modal-body" id="notification_dialog_body">
  </div>
  <div class="modal-footer">
    <button class="btn" data-dismiss="modal" aria-hidden="true">Close</button>
  </div>
</div>

<ul class="nav pull-left">
  <li><p class="navbar-text">User: {{this.user|escape}}</p></li>
</ul>

<ul class="nav pull-right">
  <li><button id="notification_button" class="nav-btn btn btn-info span1"
         data-toggle="modal" data-target="#notification_dialog"/></li>
</ul>
""")

  def Layout(self, request, response):
    """Show the number of notifications outstanding for the user."""
    self.user = request.user

    response = super(NotificationBar, self).Layout(request, response)
    return self.CallJavascript(response, "NotificationBar.Layout")


class ResetUserNotifications(flow.GRRFlow):
  """A flow to reset user's notifications."""

  # This flow can run without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  @flow.StateHandler()
  def Start(self):
    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(
        self.token.username), aff4_type="GRRUser", mode="rw", token=self.token)
    user_fd.ShowNotifications(reset=True)


class ViewNotifications(renderers.TableRenderer):
  """Render the notifications for the user."""

  target_template = renderers.Template("""
<a href="/#{{hash|escape}}" target_hash="{{hash|escape}}">{{target}}</span>""")

  layout_template = renderers.TableRenderer.layout_template

  def __init__(self, **kwargs):
    renderers.TableRenderer.__init__(self, **kwargs)

    self.AddColumn(renderers.RDFValueColumn("Timestamp"))
    self.AddColumn(renderers.RDFValueColumn("Message", width="100%"))
    self.AddColumn(renderers.RDFValueColumn("Target"))

  def Layout(self, request, response):
    response = super(ViewNotifications, self).Layout(request, response)
    return self.CallJavascript(response, "ViewNotifications.Layout")

  def BuildTable(self, start_row, end_row, request):
    """Add all the notifications to this table."""
    row_index = 0
    search_term = request.REQ.get("sSearch")

    # We modify this object by changing the notification from pending to
    # shown.
    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(
        request.user), aff4_type="GRRUser", token=request.token)

    # Hack for sorting. Requires retrieval of all notifications.
    notifications = list(user_fd.ShowNotifications(reset=False))
    for notification in sorted(notifications, key=lambda x: x.timestamp,
                               reverse=True):
      if row_index < start_row: continue
      if row_index > end_row: break

      if (search_term and
          search_term.lower() not in notification.message.lower()):
        continue

      row = {"Message": notification.message,
             "Target": self.FormatFromTemplate(
                 self.target_template,
                 hash=self.BuildHashFromNotification(notification),
                 target=notification.subject),
             "Timestamp": rdfvalue.RDFDatetime(notification.timestamp),
            }
      self.AddRow(row, row_index)
      row_index += 1

    flow.GRRFlow.StartFlow(None, "ResetUserNotifications",
                           token=request.token)

  def BuildHashFromNotification(self, notification):
    """Navigate to the most appropriate location for this navigation."""
    h = {}

    # General Host information
    if notification.type == "Discovery":
      path = rdfvalue.RDFURN(notification.subject)
      components = path.Path().split("/")[1:]
      h["c"] = components[0]
      h["main"] = "HostInformation"

    # Downloading a file
    elif notification.type == "ViewObject":
      path = rdfvalue.RDFURN(notification.subject)
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
      path = rdfvalue.RDFURN(notification.subject)
      components = path.Path().split("/")[1:]
      h["flow"] = notification.source
      h["c"] = components[0]
      h["main"] = "ManageFlows"

    elif notification.type == "GrantAccess":
      h["main"] = "GrantAccess"
      h["acl"] = notification.subject

    return urllib.urlencode(
        dict([(x, utils.SmartStr(y)) for x, y in h.items()]))
