#!/usr/bin/env python
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This plugin renders the client search page."""
import json
import urllib

from django import http
from grr.gui import renderers
from grr.lib import aff4
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
<div id="notification_dialog" class="modal wide-modal hide fade" tabindex="-1"
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

<script>
  grr.subscribe("NotificationCount", function (number) {
    var button;

    if(parseInt(number) > 0) {
      button = $('#notification_button').removeClass("btn-info");
      button = $('#notification_button').addClass("btn-danger");
    } else {
      button = $('#notification_button').addClass("btn-info");
      button = $('#notification_button').removeClass("btn-danger");
    };
    button.text(number);
  }, "notification_button");

  grr.poll("NotificationCount", "notification_button", function (data) {
    if(data) {
      grr.publish("NotificationCount", data.number);
    };

    return true;
  }, 60000, grr.state, 'json');

  $("#notification_dialog").detach().appendTo("body");
  $("#notification_dialog").on("show", function () {
    grr.layout("ViewNotifications", "notification_dialog_body");
    grr.publish("NotificationCount", 0);
  });
</script>
""")

  def Layout(self, request, response):
    """Show the number of notifications outstanding for the user."""
    self.user = request.user

    return super(NotificationBar, self).Layout(request, response)


class ViewNotifications(renderers.TableRenderer):
  """Render the notifications for the user."""

  target_template = renderers.Template("""
<a href="/#{{hash|escape}}" target_hash="{{hash|escape}}">{{target}}</span>""")

  layout_template = renderers.TableRenderer.layout_template + """
<script>
  //Receive the selection event and emit a path
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
    var element = node.find("a");
      if(element) {
        grr.loadFromHash(element.attr("target_hash"));
      };
    };
  }, '{{ unique|escapejs }}');
</script>
  """

  def __init__(self, **kwargs):
    renderers.TableRenderer.__init__(self, **kwargs)

    self.AddColumn(renderers.RDFValueColumn("Timestamp"))
    self.AddColumn(renderers.RDFValueColumn("Message", width="100%"))
    self.AddColumn(renderers.RDFValueColumn("Target"))

  def BuildTable(self, start_row, end_row, request):
    """Add all the notifications to this table."""
    try:
      row_index = 0
      search_term = request.REQ.get("sSearch")

      # We modify this object by changing the notification from pending to
      # shown.
      user_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(
          request.user), "GRRUser", mode="rw", token=request.token)

      # Hack for sorting. Requires retrieval of all notifications.
      notifications = list(user_fd.ShowNotifications(reset=True))
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

    except IOError:
      pass

  def BuildHashFromNotification(self, notification):
    """Navigate to the most appropriate location for this navigation."""
    h = {}

    # General Host information
    if notification.type == "Discovery":
      h["c"] = notification.subject
      h["main"] = "HostInformation"

    # Downloading a file
    elif notification.type == "ViewObject":
      path = rdfvalue.RDFURN(notification.subject)
      components = path.Path().split("/")[1:]
      if len(components) == 2 and components[0] == "hunts":
        h["hunt_id"] = notification.subject
        h["main"] = "ManageHunts"
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
      h["flow"] = notification.source
      h["c"] = notification.subject
      h["main"] = "ManageFlows"

    elif notification.type == "GrantAccess":
      h["main"] = "GrantAccess"
      h["acl"] = notification.subject

    return urllib.urlencode(
        dict([(x, utils.SmartStr(y)) for x, y in h.items()]))
