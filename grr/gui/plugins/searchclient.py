#!/usr/bin/env python
"""This plugin renders the client search page."""

import time

from django.utils import datastructures

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import ip_resolver
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.rdfvalues import client as rdf_client


class SearchHostInit(registry.InitHook):

  def RunOnce(self):
    # Counters used here
    stats.STATS.RegisterEventMetric("grr_gui_search_host_time")


class ContentView(renderers.Splitter2WayVertical):
  """The content view has a navigator and the main panel."""
  left_renderer = "Navigator"
  right_renderer = "FrontPage"

  min_left_pane_width = 210
  max_left_pane_width = 210

  layout_template = ("""<div id="global-notification"></div>""" +
                     renderers.Splitter2WayVertical.layout_template)

  def Layout(self, request, response):
    canary_mode = False

    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(request.user),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=request.token)
    canary_mode = user_record.Get(user_record.Schema.GUI_SETTINGS).canary_mode

    if canary_mode:
      response.set_cookie("canary_mode", "true")
    else:
      response.delete_cookie("canary_mode")

    # Ensure that Javascript will be executed before the rest of the template
    # gets processed.
    response = self.CallJavascript(
        response,
        "ContentView.Layout",
        global_notification_poll_time=GlobalNotificationBar.POLL_TIME,
        canary=int(canary_mode))
    response = super(ContentView, self).Layout(request, response)
    return response


class SetGlobalNotification(flow.GRRGlobalFlow):
  """Updates user's global notification timestamp."""

  # This is an administrative flow.
  category = "/Administrative/"

  # Only admins can run this flow.
  AUTHORIZED_LABELS = ["admin"]

  # This flow is a SUID flow.
  ACL_ENFORCED = False

  args_type = aff4_users.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(aff4_users.GlobalNotificationStorage.DEFAULT_PATH,
                             aff4_type=aff4_users.GlobalNotificationStorage,
                             mode="rw",
                             token=self.token) as storage:
      storage.AddNotification(self.args)


class MarkGlobalNotificationAsShown(flow.GRRFlow):
  """Updates user's global notification timestamp."""

  # This flow is a SUID flow.
  ACL_ENFORCED = False

  args_type = aff4_users.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_users.GRRUser,
        token=self.token,
        mode="rw") as user_record:
      user_record.MarkGlobalNotificationAsShown(self.args)


class GlobalNotificationBar(renderers.TemplateRenderer):
  """Renders global notification bar on top of the admin UI."""

  POLL_TIME = 5 * 60 * 1000

  layout_template = renderers.Template("""
{% for notification in this.notifications %}
<div class="alert alert-block alert-{{notification.type_name|lower|escape}}">
  <button type="button" notification-hash="{{notification.hash|escape}}"
    class="close">&times;</button>
  <h4>{{notification.header|escape}}</h4>
  <p>{{notification.content|escape}}</h4>
  {% if notification.link %}
    <p><a href="{{notification.link|escape}}" target="_blank">More...</a></p>
  {% endif %}
</div>
{% endfor %}
""")

  def Layout(self, request, response):
    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(request.user),
          aff4_users.GRRUser,
          token=request.token)

      self.notifications = user_record.GetPendingGlobalNotifications()
    except IOError:
      self.notifications = []

    return super(GlobalNotificationBar, self).Layout(request, response)

  def RenderAjax(self, request, response):
    # If notification_hash is part of request, remove notification with a
    # given hash, otherwise just render list of notifications as usual.
    if "notification_hash" in request.REQ:
      hash_to_remove = int(request.REQ["notification_hash"])

      user_record = aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(request.user),
          aff4_users.GRRUser,
          mode="r",
          token=request.token)

      notifications = user_record.GetPendingGlobalNotifications()
      for notification in notifications:
        if notification.hash == hash_to_remove:
          flow.GRRFlow.StartFlow(flow_name="MarkGlobalNotificationAsShown",
                                 args=notification,
                                 token=request.token)
          break
    else:
      return self.Layout(request, response)


def FormatLastSeenTime(age):

  age = rdfvalue.RDFDatetime(age)
  if int(age) == 0:
    return "Never"

  time_last_seen = int(rdfvalue.RDFDatetime().Now() - age)

  if time_last_seen < 60:
    return "%d seconds ago" % int(time_last_seen)
  elif time_last_seen < 60 * 60:
    return "%d minutes ago" % int(time_last_seen // 60)
  elif time_last_seen < 60 * 60 * 24:
    return "%d hours ago" % int(time_last_seen // (60 * 60))
  else:
    return "%d days ago" % int(time_last_seen // (60 * 60 * 24))


def GetLowDiskWarnings(client):
  """Check disk free space for a client.

  Args:
    client: client object open for reading
  Returns:
    array of warning strings, empty if no warnings
  """
  warnings = []
  volumes = client.Get(client.Schema.VOLUMES)

  # Avoid showing warnings for the CDROM.  This is isn't a problem for linux and
  # OS X since we only check usage on the disk mounted at "/".
  exclude_windows_types = [
      rdf_client.WindowsVolume.WindowsDriveTypeEnum.DRIVE_CDROM
  ]

  if volumes:
    for volume in volumes:
      if volume.windowsvolume.drive_type not in exclude_windows_types:
        freespace = volume.FreeSpacePercent()
        if freespace < 5.0:
          warnings.append("{0} {1:.0f}% free".format(volume.Name(), freespace))
  return warnings


class StatusRenderer(renderers.TemplateRenderer):
  """A renderer for the online status line."""

  MAX_TIME_SINCE_CRASH = rdfvalue.Duration("1w")

  layout_template = renderers.Template("""
Status: {{this.icon|safe}}
{{this.last_seen_msg|escape}}.
{% if this.ip_description %}
  <br>
  {{this.ip_icon|safe}} {{this.ip_description|escape}}
{% endif %}
{% if this.last_crash %}
  <br>
  <strong>Last crash:</strong><br>
  <img class='grr-icon' src='/static/images/skull-icon.png'> {{this.last_crash}}<br/>
{% endif %}
{% if this.disk_full %}
  <br>
  <img class='grr-icon' src='/static/images/hdd-bang-icon.png'>
  <strong>Disk free space low:</strong><br>
  {% for message in this.disk_full %}
    {{message|escape}}<br/>
  {% endfor %}
{% endif %}
<br>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""

    client_id = request.REQ.get("client_id")
    if client_id:
      client_id = rdf_client.ClientURN(client_id)
      client = aff4.FACTORY.Open(client_id, token=request.token)

      self.last_crash = None
      crash = client.Get(client.Schema.LAST_CRASH)
      if crash:
        time_since_crash = rdfvalue.RDFDatetime().Now() - crash.timestamp
        if time_since_crash < self.MAX_TIME_SINCE_CRASH:
          self.last_crash = FormatLastSeenTime(crash.timestamp)

      self.disk_full = GetLowDiskWarnings(client)

      ping = client.Get(client.Schema.PING)
      if ping:
        age = ping
      else:
        age = 0

      # Also check for proper access.
      aff4.FACTORY.Open(client.urn.Add("fs"), token=request.token)

      self.icon = OnlineStateIcon(age).RawHTML(request)
      self.last_seen_msg = FormatLastSeenTime(age)

      ip = client.Get(client.Schema.CLIENT_IP)
      (status, description) = ip_resolver.IP_RESOLVER.RetrieveIPInfo(ip)
      self.ip_icon = IPStatusIcon(status).RawHTML(request)
      self.ip_description = description

    return super(StatusRenderer, self).Layout(request, response)

  def RenderAjax(self, request, response):
    return self.Layout(request, response)


class Navigator(renderers.TemplateRenderer):
  """A Renderer to show all menu options."""

  # Status update interval in ms.
  poll_time = 30000

  layout_template = renderers.Template("""
<div id="{{unique|escape}}"></div>
<div id="navigator">
  <ul class="nav nav-list">

{% for client_id, host in this.hosts %}
  <div class="text-success">{{host|escape}}</div>
  {% if this.unauthorized %}
  <div class="ACL_reason">
   Searching for authorization...
  </div>
  {% else %}
  {% if this.reason %}
  <div class="ACL_reason">
     Access reason: {{this.reason|escape|urlize}}
  </div>
  {% endif %}
  <div class="infoline" id="infoline_{{unique|escape}}"></div>

  {% for renderer, name in this.host_headings %}
   <li>
     <a grrtarget="{{name|escape}}"
        href="#c={{client_id|escape}}&main={{name|escape}}">
       {{ renderer.description|escape }}</a>
   </li>
  {% endfor %}

  <li>
    <a class="dropdown-toggle" data-toggle="collapse"
      href="#HostAdvanced">Advanced <b class="caret"></b></a>
  </li>
  <div id="HostAdvanced" class="collapse out">
    <ul class="nav nav-list">
      {% for renderer, name in this.host_advanced_headings %}
      <li>
        <a tabindex="-1" grrtarget="{{name|escape}}"
          href="#"> {{ renderer.description|escape }}</a>
      </li>
      {% endfor %}
    </ul>
  </div>

  {% endif %}
{% endfor %}

  {% for heading, data in this.general_headings.items %}
  <li class="nav-header">{{ data.0|escape }}</li>
  {% for renderer, name in data.1 %}
   <li>
     <a grrtarget="{{name|escape}}"
        href="#c={{client_id|escape}}&main={{name|escape}}">
       {{ renderer.description|escape }}</a>
   </li>
  {% endfor %}

  {% if data.2 %}
  <li>
    <a class="dropdown-toggle" data-toggle="collapse"
      href="#{{ data.0|escape }}Advanced">Advanced <b class="caret"></b></a>
  </li>
  <div id="{{ data.0|escape }}Advanced" class="collapse out">
    <ul class="nav nav-list">
      {% for renderer, name in data.2 %}
      <li>
        <a tabindex="-1" grrtarget="{{name|escape}}"
          href="#"> {{ renderer.description|escape }}</a>
      </li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

{% endfor %}
  </ul>
</div>

</div>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""
    self.reason = request.REQ.get("reason", "")
    if "/" in self.reason and not self.reason.startswith("http"):
      self.reason = "http://%s" % self.reason

    self.host_advanced_headings = []
    self.host_headings = []
    self.general_headings = datastructures.SortedDict([
        ("General", ("Management", [], [])), ("Configuration", ("Configuration",
                                                                [], []))
    ])

    # Introspect all the categories
    for cls in self.classes.values():
      try:
        if not aff4.issubclass(cls, renderers.Renderer):
          continue

        cls.CheckAccess(request)
      except access_control.UnauthorizedAccess:
        continue

      for behaviour in self.general_headings:
        if behaviour in cls.behaviours:
          self.general_headings[behaviour][1].append((cls, cls.__name__))
        if behaviour + "Advanced" in cls.behaviours:
          self.general_headings[behaviour][2].append((cls, cls.__name__))

      if "Host" in cls.behaviours:
        self.host_headings.append((cls, cls.__name__))
      if "HostAdvanced" in cls.behaviours:
        self.host_advanced_headings.append((cls, cls.__name__))

    # Sort the output so they are in order.
    for heading in self.general_headings:
      # pylint: disable=g-long-lambda
      lkey = lambda x: (getattr(x[0], "order", 10),
                        getattr(x[0], "description", ""))  # pyformat: disable
      # pylint: enable=g-long-lambda
      self.general_headings[heading][1].sort(key=lkey)
    self.host_headings.sort(key=lambda x: getattr(x[0], "order", 10))

    self.hosts = []
    self.unauthorized = False
    self.client_id = request.REQ.get("client_id")
    if self.client_id:
      # If there was an approval with a reason for this client, find it and
      # and show the reason.
      try:
        approved_token = aff4_security.Approval.GetApprovalForObject(
            rdf_client.ClientURN(self.client_id),
            token=request.token)
        self.reason = approved_token.reason
      except access_control.UnauthorizedAccess as e:
        pass

      client = aff4.FACTORY.Open(self.client_id, token=request.token)

      self.hosts.append((self.client_id, client.Get(client.Schema.HOSTNAME)))

      try:
        # Also check for proper access.
        aff4.FACTORY.Open(client.urn.Add("acl_check"), token=request.token)
      except access_control.UnauthorizedAccess as e:
        self.unauthorized = True
        self.unauthorized_exception = e

    super(Navigator, self).Layout(request, response)
    if self.unauthorized:
      renderers.Renderer.GetPlugin("UnauthorizedRenderer")().Layout(request,
                                                                    response,
                                                                    exception=e)

    return self.CallJavascript(response,
                               "Navigator.Layout",
                               renderer=self.__class__.__name__,
                               client_id=self.client_id,
                               poll_time=self.poll_time)


class OnlineStateIcon(semantic.RDFValueRenderer):
  """Render the online state by using an icon."""

  cls = "vertical_aligned"

  layout_template = renderers.Template("""
<img class="grr-icon-small {{this.cls|escape}}"
     src="/static/images/{{this.icon|escape}}"
     title="{{this.last_seen_str|escape}}"/>""")

  # Maps the flow states to icons we can show
  state_map = {"15m": "online.png",
               "1d": "online-1d.png",
               "offline": "offline.png"}

  def Layout(self, request, response):
    """Render the state icon."""
    time_last_seen = time.time() - (self.proxy / 1e6)
    self.last_seen_str = FormatLastSeenTime(self.proxy)
    if time_last_seen < 60 * 15:
      self.icon = self.state_map["15m"]
    elif time_last_seen < 60 * 60 * 24:
      self.icon = self.state_map["1d"]
    else:
      self.icon = self.state_map["offline"]

    return super(OnlineStateIcon, self).Layout(request, response)


class IPStatusIcon(semantic.RDFValueRenderer):
  """Renders the ip status (internal, external) icon."""

  cls = "vertical_aligned"

  layout_template = renderers.Template("""
<img class="grr-icon-small {{this.cls|escape}}"
     src="/static/images/{{this.ip_icon|escape}}"/>""")

  icons = {ip_resolver.IPInfo.UNKNOWN: "ip_unknown.png",
           ip_resolver.IPInfo.INTERNAL: "ip_internal.png",
           ip_resolver.IPInfo.EXTERNAL: "ip_external.png",
           ip_resolver.IPInfo.VPN: "ip_unknown.png"}

  def Layout(self, request, response):
    self.ip_icon = self.icons.setdefault(int(self.proxy), "ip_unknown.png")
    return super(IPStatusIcon, self).Layout(request, response)


class FilestoreTable(renderers.TableRenderer):
  """Render filestore hits."""

  def __init__(self, **kwargs):
    super(FilestoreTable, self).__init__(**kwargs)

    self.AddColumn(semantic.RDFValueColumn("Client"))
    self.AddColumn(semantic.RDFValueColumn("File"))
    self.AddColumn(semantic.RDFValueColumn("Timestamp"))

  def BuildTable(self, start, end, request):
    query_string = request.REQ.get("q", "")
    if not query_string:
      raise RuntimeError("A query string must be provided.")

    hash_urn = rdfvalue.RDFURN("aff4:/files/hash/generic/sha256/").Add(
        query_string)

    for i, (_, value, timestamp) in enumerate(data_store.DB.ResolvePrefix(
        hash_urn, "index:", token=request.token)):

      if i > end:
        break

      self.AddRow(row_index=i,
                  File=value,
                  Client=aff4_grr.VFSGRRClient.ClientURNFromURN(value),
                  Timestamp=rdfvalue.RDFDatetime(timestamp))

    # We only display 50 entries.
    return False


class ClientLabelsRenderer(semantic.RDFValueRenderer):
  """Renders client labels."""

  layout_template = renderers.Template("""
{% for label in this.labels %}

{% if label.owner == 'GRR' %}
<span class="label label-default">{{label.name|escape}}</span>
{% else %}
<span class="label label-success">{{label.name|escape}}</span>
{% endif %}

{% endfor %}
""")

  def Layout(self, request, response):
    labels_list = self.proxy.Get(self.proxy.Schema.LABELS)
    if labels_list:
      self.labels = labels_list.labels
    else:
      self.labels = []

    return super(ClientLabelsRenderer, self).Layout(request, response)


class HostTable(renderers.AngularDirectiveRenderer):
  directive = "grr-clients-list"

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["query"] = request.REQ.get("q")
    return super(HostTable, self).Layout(request, response)


class SearchHostView(renderers.AngularDirectiveRenderer):
  directive = "grr-client-search-box"


class FrontPage(renderers.TemplateRenderer):
  """The front page of the GRR application."""

  layout_template = renderers.Template("""
  <div id="main"></div>
""")

  def Layout(self, request, response):
    response = super(FrontPage, self).Layout(request, response)
    return self.CallJavascript(response, "FrontPage.Layout")


class UserDashboard(renderers.AngularDirectiveRenderer):
  directive = "grr-user-dashboard"
