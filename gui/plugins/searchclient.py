#!/usr/bin/env python
# Copyright 2010 Google Inc. All Rights Reserved.

"""This plugin renders the client search page."""
import time

from django.utils import datastructures

from grr.gui import renderers

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import search
from grr.lib import stats
from grr.lib import utils


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

  layout_template = """
<script>
  if (grr.hash.c) {
    grr.state.client_id = grr.hash.c;
  };
</script>
""" + renderers.Splitter2WayVertical.layout_template


def FormatLastSeenTime(age):

  if int(age) == 0:
    return "Never"

  time_last_seen = (rdfvalue.RDFDatetime().Now() - int(age)) / 1e6

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

  layout_template = renderers.Template("""
Status: {{this.icon|safe}}
{{this.last_seen_msg|escape}}.
{% if this.ip_description %}
<br>
{{this.ip_icon|safe}} {{this.ip_description|escape}}
{% endif %}
<br>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""

    client_id = request.REQ.get("client_id")
    if client_id:
      client = aff4.FACTORY.Open(client_id, token=request.token)
      ping = client.Get(client.Schema.PING)
      if ping:
        age = ping
      else:
        age = 0

      # Also check for proper access.
      aff4.FACTORY.Open(client.urn.Add("fs"), token=request.token)

      self.icon = OnlineStateIcon(age).RawHTML()
      self.last_seen_msg = FormatLastSeenTime(age)

      ip = client.Get(client.Schema.CLIENT_IP)
      (status, description) = utils.RetrieveIPInfo(ip)
      self.ip_icon = IPStatusIcon(status).RawHTML()
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
<script>

 grr.installNavigationActions("nav_{{unique|escapejs}}");
 if(!grr.hash.main) {
   $('a[grrtarget=HostInformation]').click();
 } else {
   $('a[grrtarget=' + grr.hash.main + ']').click();
 };

 grr.poll("StatusRenderer", "infoline_{{unique|escapejs}}",
   function(data) {
     $("#infoline_{{unique|escapejs}}").html(data);
     return true;
   }, {{this.poll_time|escapejs}}, grr.state, null,
   function() {
      $("#infoline_{{unique|escapejs}}").html("Client status not available.");
   });

  // Reload the navigator when a new client is selected.
  grr.subscribe("client_selection", function () {
    grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}");
  }, "{{unique|escapejs}}");

  if(grr.hash.c && grr.hash.c != "{{this.client_id|escapejs}}") {
    grr.publish("client_selection", grr.hash.c);
  };

</script>
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
      renderers.Renderer.NewPlugin("UnauthorizedRenderer")().Layout(
          request, response, exception=e)

    return response


class OnlineStateIcon(renderers.RDFValueRenderer):
  """Render the online state by using an icon."""

  cls = "vertical_aligned"

  layout_template = renderers.Template("""
<img class="grr-icon-small {{this.cls|escape}}"
     src="/static/images/{{this.icon|escape}}"/>""")

  # Maps the flow states to icons we can show
  state_map = {"15m": "online.png",
               "1d": "online-1d.png",
               "offline": "offline.png"}

  def Layout(self, request, response):
    time_last_seen = time.time() - (self.proxy / 1e6)
    if time_last_seen < 60 * 15:
      self.icon = self.state_map["15m"]
    elif time_last_seen < 60 * 60 * 24:
      self.icon = self.state_map["1d"]
    else:
      self.icon = self.state_map["offline"]

    return super(OnlineStateIcon, self).Layout(request, response)


class IPStatusIcon(renderers.RDFValueRenderer):
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


class CenteredOnlineStateIcon(OnlineStateIcon):
  """Render the online state by using a centered icon."""

  layout_template = ("<div class=\"centered\">" +
                     OnlineStateIcon.layout_template +
                     "</div>")


class HostTable(renderers.TableRenderer):
  """Render a table for searching hosts."""

  fixed_columns = False

  # Update the table if any messages appear in these queues:
  vfs_table_template = renderers.Template("""<script>
     //Receive the selection event and emit a client_id
     grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
          var aff4_path = $("span[aff4_path]", node).attr("aff4_path");
          var cn = aff4_path.replace("aff4:/", "");
          grr.state.client_id = cn;
          grr.publish("hash_state", "c", cn);

          // Clear the authorization for new clients.
          grr.publish("hash_state", "reason", "");
          grr.state.reason = "";

          grr.publish("hash_state", "main", null);
          grr.publish("client_selection", cn);
     }, "{{ unique|escapejs }}");
 </script>""")

  def __init__(self, **kwargs):
    renderers.TableRenderer.__init__(self, **kwargs)
    self.AddColumn(renderers.RDFValueColumn("Online", width="40px",
                                            renderer=CenteredOnlineStateIcon))
    self.AddColumn(renderers.AttributeColumn("subject", width="13em"))
    self.AddColumn(renderers.AttributeColumn("Host", width="13em"))
    self.AddColumn(renderers.AttributeColumn("Version", width="20%"))
    self.AddColumn(renderers.AttributeColumn("MAC", width="10%"))
    self.AddColumn(renderers.AttributeColumn("Usernames", width="20%"))
    self.AddColumn(renderers.AttributeColumn("Install", width="15%"))
    self.AddColumn(renderers.AttributeColumn("Clock", width="15%"))

  @renderers.ErrorHandler()
  def Layout(self, request, response):
    response = super(HostTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.vfs_table_template,
        response,
        event_queue=self.event_queue,
        unique=self.unique, id=self.id)

  @stats.Timed("grr_gui_search_host_time")
  def BuildTable(self, start, end, request):
    """Draw table cells."""
    row_count = 0

    query_string = request.REQ.get("q", "")
    if not query_string:
      raise RuntimeError("A query string must be provided.")

    result_set = search.SearchClients(query_string, start=start,
                                      max_results=end-start,
                                      token=request.token)
    self.message = "Searched for %s" % query_string

    for child in result_set:
      # Add the fd to all the columns
      for column in self.columns:
        try:
          column.AddRowFromFd(row_count + start, child)
        except AttributeError:
          pass

      # Also update the online status.
      ping = child.Get(child.Schema.PING) or 0
      self.columns[0].AddElement(row_count + start, long(ping))

      row_count += 1

    return row_count


class SearchHostView(renderers.Renderer):
  """Show a search screen for the host."""

  title = "Search Client"

  template = renderers.Template("""
<form id="search_host" class="navbar-search pull-left">
  <input type="text" name="q" class="search-query" placeholder="Search">
</form>

<script>
 $("#search_host").submit(function () {
   grr.layout("HostTable", "main", {q: $('input[name="q"]').val()});
   return false;
 }).find("input[name=q]").focus();
</script>
""")

  def Layout(self, request, response):
    """Display a search screen for the host."""
    response = super(SearchHostView, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.template, response, title=self.title,
        id=self.id)


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

<script>
 // Update main's state from the hash
 if (grr.hash.main) {
   grr.layout(grr.hash.main, "main");
 };

</script>
""")
