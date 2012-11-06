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
        number = len(notifications.data)
    except IOError:
      pass

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(dict(number=number)),
                             mimetype="text/json")


class NotificationBar(renderers.TemplateRenderer):
  """Render a notification bar for the user."""

  bug_url = "http://code.google.com/p/grr/issues/list"
  code_url = "http://code.google.com/p/grr"

  layout_template = renderers.Template("""
<div class="grr-topbar-username">{{user|escape}}</div>
<span class="grr-topbar-divider">
 <span class="grr-topbar-divider-img"></span>
</span>
<button id="notification_button" class="grr-button">
</button>
<div id="notification_dialog"></div>

<span class="grr-topbar-divider">
 <span class="grr-topbar-divider-img"></span>
</span>

<a class="grr-topbar-entry" href="{{this.code_url|escape}}"
  target="_blank">Help</a>

<span class="grr-topbar-divider">
 <span class="grr-topbar-divider-img"></span>
</span>

<a class="grr-topbar-entry" href="{{this.bug_url|escape}}"
  target="_blank">Report a problem</a>

<script>
  grr.subscribe("NotificationCount", function (number) {
    var button;

    if(parseInt(number) > 0) {
      button = $('#notification_button').addClass("grr-button-red");
    } else {
      button = $('#notification_button').removeClass("grr-button-red");
    };
    button.text(number);
  }, "notification_button");

  grr.poll("NotificationCount", "notification_button", function (data) {
    if(data) {
      grr.publish("NotificationCount", data.number);
    };

    return true;
  }, 60000, grr.state, 'json');

  grr.dialog("ViewNotifications", "notification_dialog", "notification_button",
    {open: function() {grr.publish("NotificationCount", 0);},
     title: "Notifications for {{this.user|escapejs}}"});
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

  def __init__(self):
    renderers.TableRenderer.__init__(self)

    self.AddColumn(renderers.RDFValueColumn("Timestamp", width=10))
    self.AddColumn(renderers.RDFValueColumn("Message"))
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
               "Timestamp": aff4.RDFDatetime(notification.timestamp),
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
      path = aff4.RDFURN(notification.subject)
      components = path.Path().split("/")[1:]
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
