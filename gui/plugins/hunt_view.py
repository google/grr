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
import urllib


from django import http
import matplotlib.pyplot as plt

import logging

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import flow_management
from grr.gui.plugins import foreman
from grr.gui.plugins import searchclient
from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils


class ManageHunts(renderers.Splitter2Way):
  """Manages Hunts."""
  description = "Hunt Viewer"
  behaviours = frozenset(["General"])
  top_renderer = "HuntTable"
  bottom_renderer = "EmptyRenderer"


class HuntTable(renderers.TableRenderer):
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
""" + renderers.TableRenderer.layout_template + """
<script>
  $(".new_hunt_dialog[id!='new_hunt_dialog_{{unique|escape}}'").remove();

  $("#new_hunt_dialog_{{unique|escape}}").bind('resize', function() {
    grr.publish("GeometryChange", "new_hunt_dialog_{{unique|escape}}");
  });
  grr.dialog("LaunchHunts", "new_hunt_dialog_{{unique|escape}}",
    "launch_hunt_{{unique|escape}}",
    { modal: true,
      width: Math.min(parseInt($('body').css('width')) * 0.9, 1000),
      height: Math.min(parseInt($('body').css('height')) * 0.9, 700),
      title: "Launch New Hunt",
      open: function() {
        grr.layout("LaunchHunts", "new_hunt_dialog_{{unique|escape}}");
      }
    });
  grr.subscribe("WizardComplete", function(wizardStateName) {
    $("#new_hunt_dialog_{{unique|escape}}").dialog("close");
  }, "new_hunt_dialog_{{unique|escape}}");

  //Receive the selection event and emit the detail.
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      //ID is the second column.
      var hunt_id = $(node).find("td")[1].textContent;
      grr.state.hunt_id = hunt_id;
      grr.layout("HuntViewTabs", "main_bottomPane", {hunt_id: hunt_id});
      grr.publish("{{ this.selection_publish_queue|escapejs }}", hunt_id);
    };
  }, '{{ unique|escapejs }}');

  // If hunt_id in hash, click that row.
  // TODO: This doesn't work because the table isn't rendered yet.
  //       Need to hook the completion of ajax render of table.
  if (grr.hash.hunt_id) {
    $("#{{this.id}}").find("td:contains('" + grr.hash.hunt_id + "')").click();
  };
</script>
"""

  def __init__(self):
    super(HuntTable, self).__init__()
    status = renderers.RDFValueColumn("Status",
                                      renderer=flow_management.FlowStateIcon,
                                      width=0)
    self.AddColumn(status)
    self.AddColumn(renderers.RDFValueColumn("Hunt ID", width=10))
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

      hunts = list(fd.OpenChildren(children=children))

      hunts_by_session_ids = dict([(h.urn.Basename(), h) for h in hunts])
      hunt_objs = list(flow.FACTORY.GetFlowObjs(hunts_by_session_ids.keys(),
                                                token=request.token))
      hunt_objs.sort(key=lambda obj: obj.start_time, reverse=True)
      for hunt in hunt_objs:
        expire_time = (hunt.start_time + hunt.expiry_time) * 1e6
        vfshunt = hunts_by_session_ids[hunt.session_id]
        description = (vfshunt.Get(vfshunt.Schema.DESCRIPTION) or
                       hunt.__class__.__doc__.split("\n", 1)[0])
        self.AddRow({"Hunt ID": hunt.session_id,
                     "Name": hunt.__class__.__name__,
                     "Status": hunt.flow_pb.state,
                     "Start Time": aff4.RDFDatetime(hunt.start_time * 1e6),
                     "Expires": aff4.RDFDatetime(expire_time),
                     "Client Limit": hunt.client_limit,
                     "Creator": hunt.user,
                     "Description": description})
      displayed_ok = set([h.session_id for h in hunt_objs])
      for hunt in hunts:
        session_id = hunt.urn.Split()[-1]
        if session_id not in displayed_ok:
          self.AddRow({"Hunt ID": session_id,
                       "Start Time": hunt.urn.age,
                       "Description": "Hunt too old, no information available"})
      self.size = total_size

    except IOError as e:
      logging.error("Bad hunt %s", e)


class HuntViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected hunt."""

  names = ["Overview", "Log", "Errors", "Rules", "Graph"]
  # TODO(user): Add Renderer for Hunt Resource Usage (CPU/IO etc).
  delegated_renderers = ["HuntOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntRuleRenderer",
                         "HuntClientGraphRenderer"]

  def Layout(self, request, response):
    """Add hunt_id to the state of the tabs."""
    hunt_id = request.REQ.get("hunt_id")
    self.state = dict(hunt_id=hunt_id)

    return super(HuntViewTabs, self).Layout(request, response)


class ManageHuntsClientView(renderers.Splitter2Way):
  """Manages the clients involved in a hunt."""
  description = "Hunt Client View"
  top_renderer = "HuntClientTableRenderer"
  bottom_renderer = "EmptyRenderer"


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


class HuntClientTableRenderer(renderers.TableRenderer):
  """Displays the clients."""

  selection_publish_queue = "hunt_client_select"

  layout_template = """
{{this.title|escape}}
<a id="backlink_{{unique|escape}}" href='#{{this.hash|escape}}'>
back to hunt view</a>
""" + renderers.TableRenderer.layout_template + """
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

  //Receive the selection event and emit the detail.
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      // ID is the first column.
      var hunt_client = $(node).find("td")[0].textContent;
      var state = grr.state;
      state.hunt_client = hunt_client
      grr.layout("HuntClientViewTabs", "main_bottomPane", state);
      grr.publish("{{ this.selection_publish_queue|escapejs }}", hunt_client);
    };
  }, '{{ unique|escapejs }}');

</script>
"""

  def __init__(self):
    super(HuntClientTableRenderer, self).__init__()
    self.AddColumn(renderers.RDFValueColumn("Client ID", width=10))
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
    self.state = {"hunt_id": hunt_id}
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
      self.hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt_id,
                                    required_type="VFSHunt",
                                    token=request.token, age=aff4.ALL_TIMES)
    except IOError:
      logging.error("Invalid hunt %s", "aff4:/hunts/%s" % hunt_id)
      return

    resources = self.hunt.GetValuesForAttribute(self.hunt.Schema.RESOURCES)
    resource_usage = {}
    for resource in resources:
      usage = resource_usage.setdefault(resource.data.client_id, [0, 0, 0])
      usage[0] += resource.data.cpu_usage.user_cpu_time
      usage[1] += resource.data.cpu_usage.system_cpu_time
      usage[2] += resource.data.network_bytes_sent
      resource_usage[resource.data.client_id] = usage

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
      client_id = c_urn.Basename()
      row = {"Client ID": client_id,
             "Hostname": cdict.get("hostname"),
             "Status": results[c_urn],
             "Last Checkin": searchclient.FormatLastSeenTime(
                 cdict.get("age") or 0),
            }
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


class HuntOverviewRenderer(renderers.AbstractLogRenderer):
  """Renders the overview tab."""

  layout_template = renderers.Template("""

<a id="ViewHuntDetails_{{unique}}" href='#{{this.hash|escape}}'
    onclick='grr.loadFromHash("{{this.hash|escape}}");'
    class="grr-button grr-button-red">
  View hunt details
</a>
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

</table>
""")

  error_template = renderers.Template(
      "No information available for this Hunt.")

  def Layout(self, request, response):
    """Display the overview."""
    hunt_id = request.REQ.get("hunt_id")
    h = dict(main="ManageHuntsClientView", hunt_id=hunt_id)
    self.hash = urllib.urlencode(sorted(h.items()))
    self.data = {}
    if hunt_id is not None:
      try:
        self.hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt_id,
                                      required_type="VFSHunt",
                                      token=request.token, age=aff4.ALL_TIMES)
        resources = self.hunt.GetValuesForAttribute(self.hunt.Schema.RESOURCES)
        self.cpu_sum, self.net_sum = 0, 0
        for resource in resources:
          self.cpu_sum += resource.data.cpu_usage.user_cpu_time
          self.net_sum += resource.data.network_bytes_sent

        self.cpu_sum = "%.2f" % self.cpu_sum

        self.hunt_name = self.hunt.Get(self.hunt.Schema.HUNT_NAME)
        self.hunt_creator = self.hunt.Get(self.hunt.Schema.CREATOR)
        self.flow = self.hunt.GetFlowObj()
        if self.flow:
          fpb = self.flow.flow_pb

          enum_types = fpb.DESCRIPTOR.enum_types_by_name["FlowState"]
          self.data = {
              "Start Time": aff4.RDFDatetime(self.flow.start_time * 1e6),
              "Status": enum_types.values[fpb.state].name}

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

    fd = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt_id, token=request.token,
                           age=aff4.ALL_TIMES)
    log_vals = fd.GetValuesForAttribute(fd.Schema.LOG)
    log = []
    for l in log_vals:
      if not hunt_client or hunt_client == l.data.client_id:
        log.append((l.age, l.data.client_id, l.data.log_message))
    return log


class HuntErrorRenderer(renderers.AbstractLogRenderer):
  """Render the hunt errors."""

  def GetLog(self, request):
    """Retrieve the log data."""
    hunt_id = request.REQ.get("hunt_id")
    hunt_client = request.REQ.get("hunt_client")
    if hunt_id is None:
      return []

    fd = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt_id, token=request.token,
                           age=aff4.ALL_TIMES)
    err_vals = fd.GetValuesForAttribute(fd.Schema.ERRORS)
    log = []
    for l in err_vals:
      if not hunt_client or hunt_client == l.data.client_id:
        log.append((l.age, l.data.client_id, l.data.backtrace,
                    l.data.log_message))
    return log


class HuntRuleRenderer(foreman.ReadOnlyForemanRuleTable):
  """Rule renderer that only shows our hunts rules."""

  def RenderAjax(self, request, response):
    """Renders the table."""
    hunt_id = request.REQ.get("hunt_id")
    if hunt_id is not None:
      fman = aff4.FACTORY.Open("aff4:/foreman", mode="r", token=request.token)
      hunt_rules = []
      rules = fman.Get(fman.Schema.RULES, [])
      for rule in rules:
        for action in rule.actions:
          if action.hunt_id == hunt_id:
            hunt_rules.append(rule)
            break  # move to next rule

      for rule in hunt_rules:
        self.AddRow(dict(Created=aff4.RDFDatetime(rule.created),
                         Expires=aff4.RDFDatetime(rule.expires),
                         Description=rule.description,
                         Rules=rule,
                         Actions=rule))

    # Call our raw TableRenderer to actually do the rendering
    return renderers.TableRenderer.RenderAjax(self, request, response)


class HuntClientViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected client of the selected hunt."""

  names = ["Status", "Hunt Log", "Hunt Errors", "Client Detail"]
  delegated_renderers = ["HuntClientOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntHostInformationRenderer"]

  def Layout(self, request, response):
    """Populate the hunt_id and client in the tab."""
    hunt_id = request.REQ.get("hunt_id")
    hunt_client = request.REQ.get("hunt_client")
    self.state = dict(hunt_id=hunt_id, hunt_client=hunt_client)
    return super(HuntClientViewTabs, self).Layout(request, response)


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
        self.last_checkin = aff4.RDFDatetime(
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
    hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % self.hunt_id)
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
    hunt = aff4.FACTORY.Open("aff4:/hunts/%s" % hunt_id, age=aff4.ALL_TIMES)
    cl = hunt.GetValuesForAttribute(hunt.Schema.CLIENTS)
    fi = hunt.GetValuesForAttribute(hunt.Schema.FINISHED)

    cl_age = sorted([int(c.age/1e6) for c in cl])
    fi_age = sorted([int(c.age/1e6) for c in fi])

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
    self.client_id = request.REQ.get("hunt_client")
    self.urn = aff4.RDFURN(self.client_id)

    try:
      # Get all the versions of this file.
      self.fd = aff4.FACTORY.Open(self.client_id, token=request.token,
                                  age=aff4.ALL_TIMES)
      self.classes = self.RenderAFF4Attributes(self.fd, request)
      self.state["path"] = self.path = utils.SmartStr(self.fd.urn)
    except IOError:
      self.path = "Unable to open %s" % self.urn
      self.classes = []

    # Skip our direct parent and call up.
    return super(fileview.AFF4Stats, self).Layout(request, response)
