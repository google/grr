#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2012 Google Inc.
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


"""This is the interface for managing hunts."""


import operator
import StringIO
import sys
import urllib


from django import http
import matplotlib.pyplot as plt

import logging

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import foreman
from grr.gui.plugins import searchclient
from grr.lib import aff4
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections

# TODO(user): This is needed to load existing hunts into the gui. When
# unpickling stored hunts, python issues an import command for the module
# the pickled class is located. We moved some of the files during the last
# refactor so we make this work again using this hack. Hunts expire after
# three months anyways so we can remove this soon.
sys.modules["grr.lib.flows.general.hunts"] = hunts
collections.GRRRDFValueCollection = collections.RDFValueCollection


class ManageHunts(renderers.Splitter2Way):
  """Manages Hunts GUI Screen."""
  description = "Hunt Viewer"
  behaviours = frozenset(["General"])
  top_renderer = "HuntTable"
  bottom_renderer = "HuntViewTabs"


class HuntStateIcon(renderers.RDFValueRenderer):
  """Render the hunt state by using an icon.

  This class is similar to FlowStateIcon, but it also adds STATE_STOPPED
  state for hunts that were created but not yet started (because of lack of
  approval, for example).
  """

  layout_template = renderers.Template("""
<img class='grr-icon grr-flow-icon' src='/static/images/{{icon|escape}}' />
""")

  # Maps the flow states to icons we can show
  state_map = {rdfvalue.Flow.Enum("TERMINATED"): "stock_yes.png",
               rdfvalue.Flow.Enum("RUNNING"): "clock.png",
               rdfvalue.Flow.Enum("ERROR"): "nuke.png",
               aff4.AFF4Object.VFSHunt.STATE_STOPPED: "pause.png"}

  def Layout(self, _, response):
    return self.RenderFromTemplate(
        self.layout_template, response,
        icon=self.state_map.get(self.proxy, "question-red.png"))


class HuntTable(fileview.AbstractFileTable):
  """Show all hunts."""
  selection_publish_queue = "hunt_select"

  layout_template = """
<div id="toolbar_{{unique|escape}}" class="toolbar">
  <button id='launch_hunt_{{unique|escape}}' title='Launch Hunt'
    name="LaunchHunt">
    <img src='/static/images/new.png' class='toolbar_icon'>
  </button>
  <div class="new_hunt_dialog" id="new_hunt_dialog_{{unique|escape}}" />
</div>
""" + fileview.AbstractFileTable.layout_template + """
<script>
  $(".new_hunt_dialog[id!='new_hunt_dialog_{{unique|escape}}'").remove();

  grr.dialog("LaunchHunts", "new_hunt_dialog_{{unique|escape}}",
    "launch_hunt_{{unique|escape}}",
    { modal: true,
      width: Math.min(parseInt($('body').css('width')) * 0.9, 1000),
      height: Math.min(parseInt($('body').css('height')) * 0.9, 700),
      title: "Launch New Hunt",
      open: function() {
        grr.layout("LaunchHunts", "new_hunt_dialog_{{unique|escape}}");
      },
      close: function() {
        $("#new_hunt_dialog_{{unique|escape}}").remove();
      }
    });
  grr.subscribe("WizardComplete", function(wizardStateName) {
    $("#new_hunt_dialog_{{unique|escape}}").dialog("close");
  }, "new_hunt_dialog_{{unique|escape}}");

  // If hunt_id in hash, click that row.
  if (grr.hash.hunt_id) {
    $("#{{this.id}}").find("td:contains('" + grr.hash.hunt_id + "')").click();
  };
</script>
"""

  root_path = "aff4:/hunts"

  def __init__(self, **kwargs):
    super(HuntTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Status", renderer=HuntStateIcon, width=0))

    # The hunt id is the AFF4 URN for the hunt object.
    self.AddColumn(renderers.RDFValueColumn(
        "Hunt ID", renderer=renderers.SubjectRenderer, width=10))
    self.AddColumn(renderers.RDFValueColumn("Name", width=10))
    self.AddColumn(renderers.RDFValueColumn("Start Time", width=10))
    self.AddColumn(renderers.RDFValueColumn("Expires", width=10))
    self.AddColumn(renderers.RDFValueColumn("Client Limit", width=5))
    self.AddColumn(renderers.RDFValueColumn("Creator", width=10))
    self.AddColumn(renderers.RDFValueColumn("Description", width=60))

  def BuildTable(self, start_row, end_row, request):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=request.token)
    try:
      children = list(fd.ListChildren())
      total_size = len(children)

      children.sort(key=operator.attrgetter("age"), reverse=True)
      children = children[start_row:end_row]

      hunt_list = list(fd.OpenChildren(children=children))
      hunt_list.sort(key=lambda x: x.create_time, reverse=True)

      row_index = start_row
      for aff4_hunt in hunt_list:
        hunt_obj = aff4_hunt.flow_obj

        if not hunt_obj:
          continue

        expire_time = (hunt_obj.start_time +
                       hunt_obj.expiry_time) * 1e6

        description = (aff4_hunt.Get(aff4_hunt.Schema.DESCRIPTION) or
                       hunt_obj.__class__.__doc__.split("\n", 1)[0])

        if aff4_hunt.Get(aff4_hunt.Schema.STATE) == aff4_hunt.STATE_STOPPED:
          hunt_state = aff4_hunt.STATE_STOPPED
        else:
          hunt_state = aff4_hunt.flow_pb.state

        self.AddRow({"Hunt ID": aff4_hunt.urn,
                     "Name": hunt_obj.__class__.__name__,
                     "Status": hunt_state,
                     "Start Time": rdfvalue.RDFDatetime(
                         hunt_obj.start_time * 1e6),
                     "Expires": rdfvalue.RDFDatetime(expire_time),
                     "Client Limit": hunt_obj.client_limit,
                     "Creator": hunt_obj.user,
                     "Description": description},
                    row_index=row_index)
        row_index += 1

      for aff4_hunt in hunt_list:
        if not aff4_hunt.flow_obj:
          self.AddRow({"Hunt ID": aff4_hunt.urn,
                       "Description": "Hunt too old, no information available"},
                      row_index=row_index)
          row_index += 1

      self.size = total_size

    except IOError as e:
      logging.error("Bad hunt %s", e)


class HuntViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected hunt.

  Listening Javascript Events:
    - file_select(aff4_path, age) - A selection event on the hunt table
      informing us of a new hunt to show. We redraw the entire bottom right
      side using a new renderer.

  """

  names = ["Overview", "Log", "Errors", "Rules", "Graph"]
  # TODO(user): Add Renderer for Hunt Resource Usage (CPU/IO etc).
  delegated_renderers = ["HuntOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntRuleRenderer",
                         "HuntClientGraphRenderer"]

  layout_template = renderers.TabLayout.layout_template + """
<script>
  // When the hunt id is selected, redraw the tabs below.
  grr.subscribe("file_select", function(hunt_id) {
    grr.layout("HuntViewTabs", "main_bottomPane", {hunt_id: hunt_id});
  }, "{{unique|escapejs}}");
</script>
"""

  post_parameters = ["hunt_id"]


class ManageHuntsClientView(renderers.Splitter2Way):
  """Manages the clients involved in a hunt."""
  description = "Hunt Client View"
  top_renderer = "HuntClientTableRenderer"
  bottom_renderer = "HuntClientViewTabs"


class ResourceRenderer(renderers.RDFValueRenderer):
  """Renders resource usage as meters."""

  cls = "vertical_aligned"

  layout_template = renderers.Template(
      "<div>"
      "<meter value=\"{{this.proxy|escape}}\"></meter>"
      "</div>")


class FloatRenderer(renderers.RDFValueRenderer):

  layout_template = renderers.Template("{{this.value|escape}}")

  def Layout(self, request, response):

    if self.proxy is None:
      self.value = "0.0"
    else:
      self.value = "%.2f" % self.proxy

    super(FloatRenderer, self).Layout(request, response)


class HuntClientTableRenderer(fileview.AbstractFileTable):
  """Displays the clients."""

  selection_publish_queue = "hunt_client_select"

  layout_template = """
{{this.title|escape}}
<a id="backlink_{{unique|escape}}" href='#{{this.hash|escape}}'>
back to hunt view</a>
""" + fileview.AbstractFileTable.layout_template + """
<script>
  if (!grr.state.hunt_id) {
    // Refresh the page with the hunt_id from the hash.
    grr.state.hunt_id = grr.hash.hunt_id;
    grr.layout('ContentView', 'content', grr.state);
  }

  // Add click handler to the backlink.
  $("#" + "backlink_{{unique|escape}}").click(function () {
    // clean up our state before we jump back to the hunt.
    delete grr.state.client_id;
    grr.loadFromHash("{{this.hunt_hash}}");
  });

</script>
"""

  post_parameters = ["hunt_id"]

  def __init__(self, **kwargs):
    super(HuntClientTableRenderer, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Client ID", width=10, renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Hostname", width=10))
    self.AddColumn(renderers.RDFValueColumn("Status", width=10))
    self.AddColumn(renderers.RDFValueColumn("User CPU seconds", width=10,
                                            renderer=FloatRenderer))
    self.AddColumn(renderers.RDFValueColumn("System CPU seconds", width=10,
                                            renderer=FloatRenderer))
    self.AddColumn(renderers.RDFValueColumn("CPU",
                                            renderer=ResourceRenderer))
    self.AddColumn(renderers.RDFValueColumn("Network bytes sent", width=10))
    self.AddColumn(renderers.RDFValueColumn("Network",
                                            renderer=ResourceRenderer))
    self.AddColumn(renderers.RDFValueColumn("Last Checkin", width=10))

  def Layout(self, request, response):
    """Ensure our hunt is in our state for HTML layout."""
    hunt_id = request.REQ.get("hunt_id")
    self.title = "Viewing Hunt %s" % hunt_id
    h = dict(main="ManageHunts", hunt_id=hunt_id)
    self.hunt_hash = urllib.urlencode(sorted(h.items()))
    super(HuntClientTableRenderer, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Called to fill in the data in the table."""
    hunt_id = request.REQ.get("hunt_id")
    if hunt_id is None:
      return
    try:
      self.hunt = aff4.FACTORY.Open(hunt_id,
                                    required_type="VFSHunt",
                                    token=request.token, age=aff4.ALL_TIMES)
    except IOError:
      logging.error("Invalid hunt %s", hunt_id)
      return

    resources = self.hunt.GetValuesForAttribute(self.hunt.Schema.RESOURCES)
    resource_usage = {}
    for resource in resources:
      usage = resource_usage.setdefault(resource.client_id, [0, 0, 0])
      usage[0] += resource.cpu_usage.user_cpu_time
      usage[1] += resource.cpu_usage.system_cpu_time
      usage[2] += resource.network_bytes_sent
      resource_usage[resource.client_id] = usage

    resource_max = [0, 0, 0]
    for resource in resource_usage.values():
      for i in range(3):
        if resource_max[i] < resource[i]:
          resource_max[i] = resource[i]

    # TODO(user): Allow table to be filtered by client status.
    results = {}
    for status, client_list in self.hunt.GetClientsByStatus().items():
      for client in client_list:
        results[client] = status

    # Get the list of clients and sort so that we can page accurately.
    client_list = results.keys()
    client_list.sort()
    client_list = client_list[start_row:end_row]

    row_index = start_row
    for c_urn, cdict in self.hunt.GetClientStates(client_list):
      row = {"Client ID": c_urn,
             "Hostname": cdict.get("hostname"),
             "Status": results[c_urn],
             "Last Checkin": searchclient.FormatLastSeenTime(
                 cdict.get("age") or 0),
            }

      client_id = c_urn.Basename()
      if client_id in resource_usage:
        usage = resource_usage[client_id]
        row["User CPU seconds"] = usage[0]
        row["System CPU seconds"] = usage[1]
        row["Network bytes sent"] = usage[2]
        usage_percent = []
        for i in range(3):
          if resource_max[i]:
            usage_percent.append(round(usage[i], 2) / resource_max[i])
          else:
            usage_percent.append(0.0)
        row["CPU"] = usage_percent[0]
        row["Network"] = usage_percent[2]
      else:
        row["User CPU seconds"] = 0
        row["System CPU seconds"] = 0
        row["Network bytes sent"] = 0
        row["CPU"] = 0
        row["Network"] = 0

      self.AddRow(row, row_index)
      row_index += 1
    self.size = len(results)


class HuntViewRunHunt(renderers.TemplateRenderer):
  """Runs a hunt when "Run Hunt" button is pressed and permissions checked."""

  layout_template = renderers.Template("""
  Hunt was started!
""")

  def Layout(self, request, response):
    hunt_urn = request.REQ.get("hunt_id")
    flow.FACTORY.StartFlow(None, "RunHuntFlow", token=request.token,
                           hunt_urn=hunt_urn)

    return super(HuntViewRunHunt, self).Layout(request, response)


class HuntOverviewRenderer(renderers.AbstractLogRenderer):
  """Renders the overview tab."""

  layout_template = renderers.Template("""

<a id="ViewHuntDetails_{{unique}}" href='#{{this.hash|escape}}'
    onclick='grr.loadFromHash("{{this.hash|escape}}");'
    class="grr-button grr-button-red">
  View hunt details
</a>
{% if this.allow_run %}
<br/><br/>
<div id="RunHunt_{{unique|escape}}">
<a id="RunHuntButton_{{unique|escape}}" name="RunHunt"
    href='#{{this.hash|escape}}' class="grr-button grr-button-red">
  Run Hunt
</a>
</div>
{% endif %}
<br/><br/>
<table class="proto_table">
{% for key, val in this.data.items %}
  <tr><td class="proto_key">{{ key|escape }}</td><td>{{ val|escape }}</td>
{% endfor %}

  <tr><td class="proto_key">Name</td>
      <td>{{ this.hunt_name|escape }}</td>
  <tr><td class="proto_key">Hunt ID</td>
      <td>{{ this.hunt.urn.Basename|escape }}</td>
  <tr><td class="proto_key">Hunt URN</td>
      <td>{{ this.hunt.urn|escape }}</td>
  <tr><td class="proto_key">Creator</td>
      <td>{{ this.hunt_creator|escape }}</td>
  <tr><td class="proto_key">Client Limit</td>
      <td>{{ this.client_limit|escape }}</td>
  <tr><td class="proto_key">Client Count</td>
      <td>{{ this.hunt.NumClients|escape }}</td>
  <tr><td class="proto_key">Outstanding</td>
      <td>{{ this.hunt.NumOutstanding|escape }}</td>
  <tr><td class="proto_key">Completed</td>
      <td>{{ this.hunt.NumCompleted|escape }}</td>
  <tr><td class="proto_key">Findings</td>
      <td>{{ this.hunt.NumResults|escape }}</td>
  <tr><td class="proto_key">Total CPU seconds used</td>
      <td>{{ this.cpu_sum|escape }}</td>
  <tr><td class="proto_key">Total network traffic</td>
      <td>{{ this.net_sum|filesizeformat }}</td>
  <tr><td class="proto_key">Arguments</td>
      <td><pre>{{ this.args_str|safe }}</pre></td>

</table>

<script>
(function() {

$("#RunHuntButton_{{unique|escapejs}}").click(function() {
  grr.update("HuntOverviewRenderer", "RunHunt_{{unique|escapejs}}",
    { hunt_id: "{{this.hunt_id|escapejs}}" });
});

})();
</script>
""")

  error_template = renderers.Template(
      "No information available for this Hunt.")

  ajax_template = renderers.Template("""
<div id="RunHuntResult_{{unique|escape}}"></div>
<script>
  // We execute CheckAccess renderer with silent=true. Therefore it searches
  // for an approval and sets correct reason if approval is found. When
  // CheckAccess completes, we execute HuntViewRunHunt renderer, which
  // tries to run an actual hunt. If the approval wasn't found on CheckAccess
  // stage, it will fail due to unauthorized access and proper ACLDialog will
  // be displayed.
  grr.layout("CheckAccess", "RunHuntResult_{{unique|escapejs}}",
    {silent: true, subject: "{{this.subject|escapejs}}" },
    function() {
      grr.layout("HuntViewRunHunt", "RunHuntResult_{{unique|escapejs}}",
        { hunt_id: "{{this.hunt_id|escapejs}}" });
    });
</script>
""")

  def RenderAjax(self, request, response):
    self.hunt_id = request.REQ.get("hunt_id")
    self.subject = rdfvalue.RDFURN(self.hunt_id)

    return renderers.TemplateRenderer.Layout(self, request, response,
                                             apply_template=self.ajax_template)

  def Layout(self, request, response):
    """Display the overview."""
    # If hunt_id is set by a subclass, don't look for it in request.REQ
    if not hasattr(self, "hunt_id"):
      self.hunt_id = request.REQ.get("hunt_id")

    h = dict(main="ManageHuntsClientView", hunt_id=self.hunt_id)
    self.hash = urllib.urlencode(sorted(h.items()))
    self.data = {}
    self.args_str = ""
    self.client_limit = None

    if self.hunt_id:
      try:
        self.hunt = aff4.FACTORY.Open(self.hunt_id,
                                      required_type="VFSHunt",
                                      token=request.token, age=aff4.ALL_TIMES)
        resources = self.hunt.GetValuesForAttribute(self.hunt.Schema.RESOURCES)
        self.cpu_sum, self.net_sum = 0, 0
        for resource in resources:
          self.cpu_sum += resource.cpu_usage.user_cpu_time
          self.net_sum += resource.network_bytes_sent

        self.cpu_sum = "%.2f" % self.cpu_sum

        self.hunt_name = self.hunt.Get(self.hunt.Schema.HUNT_NAME)
        self.hunt_creator = self.hunt.Get(self.hunt.Schema.CREATOR)
        self.flow = self.hunt.GetFlowObj()
        if self.flow:
          fpb = self.flow.flow_pb

          enum_types = fpb.DESCRIPTOR.enum_types_by_name["FlowState"]
          self.data = {
              "Start Time": rdfvalue.RDFDatetime(self.flow.start_time * 1e6),
              "Status": enum_types.values[fpb.state].name}

          self.client_limit = self.flow.client_limit
          self.args_str = renderers.RDFProtoDictRenderer(fpb.args).RawHTML()

        # The hunt is allowed to run if it's stopped. Also, if allow_run
        # is set by the subclass, we don't override it
        if not hasattr(self, "allow_run"):
          self.allow_run = (self.hunt.Get(self.hunt.Schema.STATE) ==
                            self.hunt.STATE_STOPPED)

      except IOError:
        self.layout_template = self.error_template

    return super(HuntOverviewRenderer, self).Layout(request, response)


class HuntLogRenderer(renderers.AbstractLogRenderer):
  """Render the hunt log."""

  def GetLog(self, request):
    """Retrieve the log data."""
    hunt_id = request.REQ.get("hunt_id")
    hunt_client = request.REQ.get("hunt_client")
    if hunt_id is None:
      return []

    fd = aff4.FACTORY.Open(hunt_id, token=request.token,
                           age=aff4.ALL_TIMES)
    log_vals = fd.GetValuesForAttribute(fd.Schema.LOG)
    log = []
    for l in log_vals:
      if not hunt_client or hunt_client == l.client_id:
        log.append((l.age, l.client_id, l.log_message))

    return log


class HuntErrorRenderer(renderers.AbstractLogRenderer):
  """Render the hunt errors."""

  def GetLog(self, request):
    """Retrieve the log data."""
    hunt_id = request.REQ.get("hunt_id")
    hunt_client = request.REQ.get("hunt_client")
    if hunt_id is None:
      return []

    fd = aff4.FACTORY.Open(hunt_id, token=request.token,
                           age=aff4.ALL_TIMES)
    err_vals = fd.GetValuesForAttribute(fd.Schema.ERRORS)
    log = []
    for l in err_vals:
      if not hunt_client or hunt_client == rdfvalue.RDFURN(l.client_id):
        log.append((l.age, l.client_id, l.backtrace,
                    l.log_message))
    return log


class HuntRuleRenderer(foreman.ReadOnlyForemanRuleTable):
  """Rule renderer that only shows our hunts rules."""

  def RenderAjax(self, request, response):
    """Renders the table."""
    hunt_id = request.REQ.get("hunt_id")
    if hunt_id is not None:
      hunt = aff4.FACTORY.Open(hunt_id, required_type="VFSHunt",
                               age=aff4.ALL_TIMES, token=request.token)

      # Getting list of rules from hunt object: this doesn't require us to
      # have admin privileges (which we need to go through foreman rules).
      hunt_obj = hunt.GetFlowObj()

      for rule in hunt_obj.rules:
        self.AddRow(Created=rule.created,
                    Expires=rule.expires,
                    Description=rule.description)

        self.AddRow(Created=rule.created,
                    Expires=rule.expires,
                    Description=rule.description,
                    Rules=rule,
                    Actions=rule)

    # Call our raw TableRenderer to actually do the rendering
    return renderers.TableRenderer.RenderAjax(self, request, response)


class HuntClientViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected client of the selected hunt."""

  names = ["Status", "Hunt Log", "Hunt Errors", "Client Detail"]
  delegated_renderers = ["HuntClientOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntHostInformationRenderer"]

  layout_template = renderers.TabLayout.layout_template + """
<script>
  // When the hunt id is selected, redraw the tabs below.
  grr.subscribe("file_select", function(client_id) {
    grr.layout("HuntClientViewTabs", "main_bottomPane", {
                 hunt_client: client_id,
                 hunt_id: '{{this.state.hunt_id|escapejs}}'
               });
  }, "{{unique|escapejs}}");
</script>
"""

  post_parameters = ["hunt_id", "hunt_client"]


class HuntClientOverviewRenderer(renderers.TemplateRenderer):
  """Renders the Client Hunt Overview tab."""

  layout_template = renderers.Template("""
<a href='#{{this.hash|escape}}' onclick='grr.loadFromHash(
    "{{this.hash|escape}}");' ">
  Go to client {{ this.client.urn|escape }}
</a>
<table class="proto_table">
  <tr><td class="proto_key">Last Checkin</td>
      <td>{{ this.last_checkin|escape }}</td>
</table>
""")

  def Layout(self, request, response):
    """Display the overview."""
    hunt_id = request.REQ.get("hunt_id")
    hunt_client = request.REQ.get("hunt_client")
    if hunt_id is not None:
      try:
        self.client = aff4.FACTORY.Open(hunt_client, token=request.token,
                                        required_type="VFSGRRClient")
        self.last_checkin = rdfvalue.RDFDatetime(
            self.client.Get(self.client.Schema.PING))

        h = dict(main="HostInformation", c=self.client.client_id)
        self.hash = urllib.urlencode(sorted(h.items()))
      except IOError as e:
        logging.error("Attempt to open client %s. Err %s", hunt_client, e)

    return super(HuntClientOverviewRenderer, self).Layout(request, response)


class HuntClientGraphRenderer(renderers.TemplateRenderer):
  """Renders the button to download a hunt graph."""

  layout_template = renderers.Template("""
{% if this.clients %}
<button id="{{ unique|escape }}">
 Generate
</button>
<script>
  var button = $("#{{ unique|escapejs }}").button();

  var state = {hunt_id: '{{this.hunt_id|escapejs}}'};
  grr.downloadHandler(button, state, false,
                      '/render/Download/HuntClientCompletionGraphRenderer');
</script>
{% else %}
No data to graph yet.
{% endif %}
""")

  def Layout(self, request, response):
    self.hunt_id = request.REQ.get("hunt_id")
    hunt = aff4.FACTORY.Open(self.hunt_id, token=request.token)

    self.clients = bool(hunt.Get(hunt.Schema.CLIENTS))
    super(HuntClientGraphRenderer, self).Layout(request, response)


class ImageDownloadRenderer(renderers.TemplateRenderer):

  mimetype = "image/png"

  def Content(self, request, response):
    _ = request, response
    return ""

  def Download(self, request, response):

    response = http.HttpResponse(content=self.Content(request, response),
                                 mimetype=self.mimetype)

    return response


class HuntClientCompletionGraphRenderer(ImageDownloadRenderer):

  def Content(self, request, _):
    """Generates the actual image to display."""
    hunt_id = request.REQ.get("hunt_id")
    hunt = aff4.FACTORY.Open(hunt_id, age=aff4.ALL_TIMES)
    cl = hunt.GetValuesForAttribute(hunt.Schema.CLIENTS)
    fi = hunt.GetValuesForAttribute(hunt.Schema.FINISHED)

    cdict = {}
    for c in cl:
      cdict.setdefault(c, []).append(c.age)

    fdict = {}
    for c in fi:
      fdict.setdefault(c, []).append(c.age)

    cl_age = [int(min(x)/1e6) for x in cdict.values()]
    fi_age = [int(min(x)/1e6) for x in fdict.values()]

    cl_hist = {}
    fi_hist = {}

    for age in cl_age:
      cl_hist.setdefault(age, 0)
      cl_hist[age] += 1

    for age in fi_age:
      fi_hist.setdefault(age, 0)
      fi_hist[age] += 1

    t0 = min(cl_age) - 1
    times = [t0]
    cl = [0]
    fi = [0]

    all_times = set(cl_age) | set(fi_age)
    cl_count = 0
    fi_count = 0

    for time in sorted(all_times):
      # Check if there is a datapoint one second earlier, add one if not.
      if times[-1] != time-1:
        times.append(time)
        cl.append(cl_count)
        fi.append(fi_count)

      cl_count += cl_hist.get(time, 0)
      fi_count += fi_hist.get(time, 0)

      times.append(time)
      cl.append(cl_count)
      fi.append(fi_count)

    # Convert to hours, starting from 0.
    times = [(t-t0)/3600.0 for t in times]

    params = {"backend": "png"}

    plt.rcParams.update(params)
    plt.figure(1)
    plt.clf()

    plt.plot(times, cl, label="Agents issued.")
    plt.plot(times, fi, label="Agents completed.")
    plt.title("Agent Coverage")
    plt.xlabel("Time (h)")
    plt.ylabel(r"Agents")
    plt.grid(True)
    plt.legend(loc=4)
    buf = StringIO.StringIO()
    plt.savefig(buf)
    buf.seek(0)

    return buf.read()


class HuntHostInformationRenderer(fileview.AFF4Stats):
  """Modified HostInformation that reads from hunt_client variable."""

  description = "Hunt Client Host Information"
  css_class = "TableBody"
  filtered_attributes = ["USERNAMES", "HOSTNAME", "MAC_ADDRESS", "INSTALL_DATE",
                         "SYSTEM", "CLOCK", "CLIENT_INFO"]

  def Layout(self, request, response):
    """Produce a summary of the client information."""
    client_id = request.REQ.get("hunt_client")
    super(HuntHostInformationRenderer, self).Layout(
        request, response, client_id=client_id,
        aff4_path=rdfvalue.RDFURN(client_id),
        age=aff4.ALL_TIMES)
