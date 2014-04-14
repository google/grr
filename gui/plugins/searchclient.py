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
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import search
from grr.lib import stats
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr


class SearchHostInit(registry.InitHook):

  pre = ["StatsInit"]

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
        aff4.ROOT_URN.Add("users").Add(request.user), aff4_type="GRRUser",
        mode="r", token=request.token)
    canary_mode = user_record.Get(
        user_record.Schema.GUI_SETTINGS).canary_mode

    if canary_mode:
      response.set_cookie("canary_mode", "true")
    else:
      response.delete_cookie("canary_mode")

    # Ensure that Javascript will be executed before the rest of the template
    # gets processed.
    response = self.CallJavascript(
        response, "ContentView.Layout",
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

  args_type = rdfvalue.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(aff4.GlobalNotificationStorage.DEFAULT_PATH,
                             aff4_type="GlobalNotificationStorage",
                             mode="rw", token=self.token) as storage:
      storage.AddNotification(self.args)


class MarkGlobalNotificationAsShown(flow.GRRFlow):
  """Updates user's global notification timestamp."""

  # This flow is a SUID flow.
  ACL_ENFORCED = False

  args_type = rdfvalue.GlobalNotification

  @flow.StateHandler()
  def Start(self):
    with aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username), "GRRUser",
        token=self.token, mode="rw") as user_record:
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
          aff4.ROOT_URN.Add("users").Add(request.user), "GRRUser",
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
          aff4.ROOT_URN.Add("users").Add(request.user), "GRRUser",
          mode="r", token=request.token)

      notifications = user_record.GetPendingGlobalNotifications()
      for notification in notifications:
        if notification.hash == hash_to_remove:
          flow.GRRFlow.StartFlow(flow_name="MarkGlobalNotificationAsShown",
                                 args=notification, token=request.token)
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
<br>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""

    client_id = request.REQ.get("client_id")
    if client_id:
      client_id = rdfvalue.ClientURN(client_id)
      client = aff4.FACTORY.Open(client_id, token=request.token)

      self.last_crash = None
      crash = client.Get(client.Schema.LAST_CRASH)
      if crash:
        time_since_crash = rdfvalue.RDFDatetime().Now() - crash.timestamp
        if time_since_crash < self.MAX_TIME_SINCE_CRASH:
          self.last_crash = FormatLastSeenTime(crash.timestamp)

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
      (status, description) = utils.RetrieveIPInfo(ip)
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
        ("General", ("Management", [], [])),
        ("Configuration", ("Configuration", [], []))
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
                        getattr(x[0], "description", ""))
      self.general_headings[heading][1].sort(key=lkey)
    self.host_headings.sort(key=lambda x: getattr(x[0], "order", 10))

    self.hosts = []
    self.unauthorized = False
    self.client_id = request.REQ.get("client_id")
    if self.client_id:
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
      renderers.Renderer.GetPlugin("UnauthorizedRenderer")().Layout(
          request, response, exception=e)

    return self.CallJavascript(response, "Navigator.Layout",
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

  icons = {utils.IPInfo.UNKNOWN: "ip_unknown.png",
           utils.IPInfo.INTERNAL: "ip_internal.png",
           utils.IPInfo.EXTERNAL: "ip_external.png",
           utils.IPInfo.VPN: "ip_unknown.png"}

  def Layout(self, request, response):
    self.ip_icon = self.icons.setdefault(int(self.proxy), "ip_unknown.png")
    return super(IPStatusIcon, self).Layout(request, response)


class ClientStatusIconsRenderer(semantic.RDFValueRenderer):
  """Render the online state by using a centered icon."""

  MAX_TIME_SINCE_CRASH = rdfvalue.Duration("1d")

  layout_template = renderers.Template("""<div class="centered">
{{this.online_icon_code|safe}}
{% if this.show_crash_icon %}
  <img class='grr-icon' src='/static/images/skull-icon.png'
    title="{{this.crash_time|escape}}" />
{% endif %}
</div>""")

  def Layout(self, request, response):
    last_ping = self.proxy.Get(self.proxy.Schema.PING, 0)
    self.online_icon_code = OnlineStateIcon(last_ping).RawHTML(request)

    last_crash = self.proxy.Get(self.proxy.Schema.LAST_CRASH)
    if (last_crash and
        (rdfvalue.RDFDatetime().Now() - last_crash.timestamp) <
        self.MAX_TIME_SINCE_CRASH):
      self.crash_time = "%s (%s)" % (str(last_crash.timestamp),
                                     FormatLastSeenTime(last_crash.timestamp))
      self.show_crash_icon = True

    return super(ClientStatusIconsRenderer, self).Layout(request, response)


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

    for i, (_, value, timestamp) in enumerate(data_store.DB.ResolveRegex(
        hash_urn, "index:.*", token=request.token)):

      if i > end:
        break

      self.AddRow(row_index=i, File=value,
                  Client=aff4_grr.VFSGRRClient.ClientURNFromURN(value),
                  Timestamp=rdfvalue.RDFDatetime(timestamp))

    # We only display 50 entries.
    return False


class HostTable(renderers.TableRenderer):
  """Render a table for searching hosts."""

  fixed_columns = False

  def __init__(self, **kwargs):
    super(HostTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Online", width="40px",
                                           renderer=ClientStatusIconsRenderer))
    self.AddColumn(semantic.AttributeColumn("subject", width="13em"))
    self.AddColumn(semantic.AttributeColumn("Host", width="13em"))
    self.AddColumn(semantic.AttributeColumn("Version", width="20%"))
    self.AddColumn(semantic.AttributeColumn("MAC", width="10%"))
    self.AddColumn(semantic.AttributeColumn("Usernames", width="20%"))
    self.AddColumn(semantic.AttributeColumn("FirstSeen", width="15%",
                                            header="First Seen"))
    self.AddColumn(semantic.AttributeColumn("Install", width="15%",
                                            header="OS Install Date"))
    self.AddColumn(semantic.AttributeColumn("Labels", width="8%"))
    self.AddColumn(semantic.AttributeColumn("Clock", width="15%",
                                            header="Last Checkin"))

  @renderers.ErrorHandler()
  def Layout(self, request, response):
    response = super(HostTable, self).Layout(request, response)
    return self.CallJavascript(response, "HostTable.Layout")

  @stats.Timed("grr_gui_search_host_time")
  def BuildTable(self, start, end, request):
    """Draw table cells."""
    row_count = 0

    query_string = request.REQ.get("q", "")
    if not query_string:
      raise RuntimeError("A query string must be provided.")

    result_urns = search.SearchClients(query_string, start=start,
                                       max_results=end-start,
                                       token=request.token)
    result_set = aff4.FACTORY.MultiOpen(result_urns, token=request.token)

    self.message = "Searched for %s" % query_string

    for child in result_set:
      # Add the fd to all the columns
      self.AddRowFromFd(row_count + start, child)

      # Also update the online and crash status.
      self.columns[0].AddElement(row_count + start, child)

      row_count += 1

    # We only show 50 hits here.
    return False


class SearchHostView(renderers.Renderer):
  """Show a search screen for the host."""

  title = "Search Client"

  template = renderers.Template("""
  <form id="search_host" class="navbar-form form-search pull-right">
    <div class="input-append">
      <input type="text" id="client_query" name="q" class="span4 search-query" placeholder="Search Box"/>
      <button type="submit" id="client_query_submit" class="btn search-query">Search</button>
    </div>
  </form>
""")

  def Layout(self, request, response):
    """Display a search screen for the host."""
    response = super(SearchHostView, self).Layout(request, response)

    response = self.RenderFromTemplate(
        self.template, response, title=self.title,
        id=self.id)

    return self.CallJavascript(response, "SearchHostView.Layout")


class FrontPage(renderers.TemplateRenderer):
  """The front page of the GRR application."""

  layout_template = renderers.Template("""
  <div id="main">

   <div class="container-fluid">
     <div class="row-fluid">
  <div id='front'><h2>Welcome to GRR</h2></div>
  Query for a system to view in the search box above.

  <p>
  Type a search term to search for a machine using either a hostname,
  mac address or username.
  </p>
     </div>  <!-- row -->
   </div>  <!-- container -->

  </div>
""")

  def Layout(self, request, response):
    response = super(FrontPage, self).Layout(request, response)
    return self.CallJavascript(response, "FrontPage.Layout")
