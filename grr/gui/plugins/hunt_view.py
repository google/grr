#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
"""This is the interface for managing hunts."""


import collections as py_collections
import urllib


import logging

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import foreman
from grr.gui.plugins import forms
from grr.gui.plugins import searchclient
from grr.gui.plugins import semantic
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr
from grr.lib.hunts import implementation
from grr.lib.hunts import standard as hunts_standard
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


class ManageHunts(renderers.AngularDirectiveRenderer):
  description = "Hunt Manager"
  behaviours = frozenset(["General"])

  directive = "grr-hunts-view"


class RunHuntConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks confirmation to run a hunt and actually runs it."""
  post_parameters = ["hunt_id"]

  inner_dialog_only = True
  header = "Run a hunt?"

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>run</strong> this hunt?</p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt started successfully!</p>
""")

  def Layout(self, request, response):
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    return super(RunHuntConfirmationDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    flow.GRRFlow.StartFlow(flow_name="StartHuntFlow",
                           token=request.token,
                           hunt_urn=rdfvalue.RDFURN(request.REQ.get("hunt_id")))
    return self.RenderFromTemplate(self.ajax_template,
                                   response,
                                   unique=self.unique)


class StopHuntConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks confirmation to stop a hunt."""
  post_parameters = ["hunt_id"]

  inner_dialog_only = True
  header = "Stop a hunt?"

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>stop</strong> this hunt? Once a hunt is
stopped, restarting it will run it on all clients again.</p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt stopped successfully!</p>
""")

  def Layout(self, request, response):
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    return super(StopHuntConfirmationDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    flow.GRRFlow.StartFlow(flow_name="StopHuntFlow",
                           token=request.token,
                           hunt_urn=rdfvalue.RDFURN(request.REQ.get("hunt_id")))
    return self.RenderFromTemplate(self.ajax_template,
                                   response,
                                   unique=self.unique)


class ModifyHuntDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that allows user to modify certain hunt parameters."""
  post_parameters = ["hunt_id"]

  inner_dialog_only = True
  header = "Modify a hunt"
  proceed_button_title = "Modify!"

  expiry_time_dividers = ((60 * 60 * 24, "d"), (60 * 60, "h"), (60, "m"),
                          (1, "s"))

  content_template = renderers.Template("""
{{this.hunt_params_form|safe}}
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt modified successfully!</p>
""")

  def Layout(self, request, response):
    """Layout handler."""
    hunt_urn = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    with aff4.FACTORY.Open(hunt_urn,
                           aff4_type=implementation.GRRHunt,
                           token=request.token) as hunt:

      runner = hunt.GetRunner()

      hunt_args = hunts_standard.ModifyHuntFlowArgs(
          client_limit=runner.args.client_limit,
          expiry_time=runner.context.expires,)

      self.hunt_params_form = forms.SemanticProtoFormRenderer(
          hunt_args, supressions=["hunt_urn"]).RawHTML(request)

      self.check_access_subject = hunt_urn

      return super(ModifyHuntDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Starts ModifyHuntFlow that actually modifies a hunt."""
    hunt_urn = rdfvalue.RDFURN(request.REQ.get("hunt_id"))

    args = forms.SemanticProtoFormRenderer(hunts_standard.ModifyHuntFlowArgs(
    )).ParseArgs(request)

    flow.GRRFlow.StartFlow(flow_name="ModifyHuntFlow",
                           token=request.token,
                           hunt_urn=hunt_urn,
                           args=args)

    return self.RenderFromTemplate(self.ajax_template,
                                   response,
                                   unique=self.unique)


class DeleteHuntDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that confirms deletion of a hunt."""
  post_parameters = ["hunt_id"]

  inner_dialog_only = True
  header = "Delete a hunt"
  proceed_button_title = "Delete!"

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>delete</strong> this hunt? Note that
hunts can only be deleted if there are no results. </p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt Deleted!</p>
""")

  def Layout(self, request, response):
    """Layout handler."""
    # TODO(user) Switch from requiring approval to requiring ownership.
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    return super(DeleteHuntDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Starts DeleteHuntFlow that actually modifies a hunt."""
    flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                           token=request.token,
                           hunt_urn=rdfvalue.RDFURN(request.REQ.get("hunt_id")))
    return self.RenderFromTemplate(self.ajax_template,
                                   response,
                                   unique=self.unique)


class ManageHuntsClientView(renderers.Splitter2Way):
  """Manages the clients involved in a hunt."""
  description = "Hunt Client View"
  top_renderer = "HuntClientTableRenderer"
  bottom_renderer = "HuntClientViewTabs"


class ResourceRenderer(semantic.RDFValueRenderer):
  """Renders resource usage as meters."""

  cls = "vertical_aligned"

  layout_template = renderers.Template(
      "<div>"
      "<meter value=\"{{this.proxy|escape}}\"></meter>"
      "</div>")


class FloatRenderer(semantic.RDFValueRenderer):

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
<span class='pull-right'> Filter by State
<select id='{{unique|escape}}_select'>
  <option>ALL</option>
  <option>OUTSTANDING</option>
  <option>COMPLETED</option>
  <option>BAD</option>
</select>
</span>
""" + fileview.AbstractFileTable.layout_template

  post_parameters = ["hunt_id"]

  def __init__(self, **kwargs):
    super(HuntClientTableRenderer, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Client ID",
                                           width="20%",
                                           renderer=semantic.SubjectRenderer))
    self.AddColumn(semantic.RDFValueColumn("Hostname", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Status", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("User CPU seconds",
                                           width="10%",
                                           renderer=FloatRenderer))
    self.AddColumn(semantic.RDFValueColumn("System CPU seconds",
                                           width="10%",
                                           renderer=FloatRenderer))
    self.AddColumn(semantic.RDFValueColumn("CPU",
                                           renderer=ResourceRenderer,
                                           width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Network bytes sent", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Network",
                                           renderer=ResourceRenderer,
                                           width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Last Checkin", width="10%"))

  def Layout(self, request, response):
    """Ensure our hunt is in our state for HTML layout."""
    hunt_id = request.REQ.get("hunt_id")
    self.title = "Viewing Hunt %s" % hunt_id
    h = dict(main="ManageHunts", hunt_id=hunt_id)
    self.hunt_hash = urllib.urlencode(sorted(h.items()))

    response = super(HuntClientTableRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "HuntClientTableRenderer.Layout",
                               hunt_hash=self.hunt_hash)

  def BuildTable(self, start_row, end_row, request):
    """Called to fill in the data in the table."""
    hunt_id = request.REQ.get("hunt_id")
    completion_status_filter = request.REQ.get("completion_status", "ALL")
    if hunt_id is None:
      return
    try:
      self.hunt = aff4.FACTORY.Open(hunt_id,
                                    token=request.token,
                                    aff4_type=implementation.GRRHunt)
    except IOError:
      logging.error("Invalid hunt %s", hunt_id)
      return

    # TODO(user): enable per-client resource usage display.
    resource_usage = {}

    resource_max = [0, 0, 0]
    for resource in resource_usage.values():
      for i in range(3):
        if resource_max[i] < resource[i]:
          resource_max[i] = resource[i]

    results = {}
    for status, client_list in self.hunt.GetClientsByStatus().items():
      if (completion_status_filter == "ALL" or
          status == completion_status_filter):
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
             "Last Checkin": searchclient.FormatLastSeenTime(cdict.get("age") or
                                                             0)}

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


class AbstractLogRenderer(renderers.TemplateRenderer):
  """Render a page for view a Log file.

  Implements a very simple view. That will be extended with filtering
  capabilities.

  Implementations should implement the GetLog function.
  """
  show_total_count = False
  layout_template = renderers.Template("""
<table class="proto_table">
{% if this.log|length > 0 %}
  {% if this.show_total_count %}
    <h5>{{this.log|length}} Entries</h5>
  {% endif %}
{% endif %}
{% for line in this.log %}
  <tr>
  {% for val in line %}
    <td class="proto_key">{{ val|safe }}</td>
  {% endfor %}
  </tr>
{% empty %}
<tr><td>No entries</tr></td>
{% endfor %}
<table>
""")

  def GetLog(self, request):
    """Take a request and return a list of tuples for a log."""
    _ = request
    return []

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    self.log = []
    for row in self.GetLog(request):
      rendered_row = []
      for item in row:
        item_renderer = semantic.FindRendererForObject(item)
        rendered_row.append(item_renderer.RawHTML(request))

      self.log.append(rendered_row)

    return super(AbstractLogRenderer, self).Layout(request, response)


class HuntOverviewRenderer(AbstractLogRenderer):
  """Renders the overview tab."""

  # Will be retrieved from request.REQ if not set.
  hunt_id = None

  layout_template = renderers.Template("""

<a id="ViewHuntDetails_{{unique}}" href='#{{this.hash|escape}}'
    onclick='grr.loadFromHash("{{this.hash|escape}}");'
    class="btn btn-info">
  View hunt details
</a>
<br/>
<dl class="dl-horizontal dl-hunt">
  <dt>Name</dt><dd>{{ this.hunt_name|escape }}</dd>
  <dt>Hunt ID</dt>
  <dd>{{ this.hunt.urn.Basename|escape }}</dd>

  <dt>Hunt URN</dt>
  <dd>{{ this.hunt.urn|escape }}</dd>

  <dt>Creator</dt>
  <dd>{{ this.hunt_creator|escape }}</dd>

  <dt>Client Limit</dt>
  {% if this.client_limit == 0 %}
    <dd>None</dd>
  {% else %}
    <dd>{{ this.client_limit|escape }}</dd>
  {% endif %}

  <dt>Client Rate (clients/min)</dt>
  {% if this.client_rate == 0.0 %}
    <dd>No rate limit</dd>
  {% else %}
    <dd>{{ this.client_rate|escape }}</dd>
  {% endif %}

  <dt>Clients Scheduled</dt>
  <dd>{{ this.all_clients_count|escape }}</dd>

  <dt>Outstanding</dt>
  <dd>{{ this.outstanding_clients_count|escape }}</dd>

  <dt>Completed</dt>
  <dd>{{ this.completed_clients_count|escape }}</dd>

  <dt>Total CPU seconds used</dt>
  <dd>{{ this.cpu_sum|escape }}</dd>

  <dt>Total network traffic</dt>
  <dd>{{ this.net_sum|filesizeformat }}</dd>

  <dt>Client rule set</dt>
  <dd>{{ this.client_rule_set|safe }}</dd>

  <dt>Arguments</dt><dd>{{ this.args_str|safe }}</dd>

{% for key, val in this.data.items %}
  <dt>{{ key|escape }}</dt><dd>{{ val|escape }}</dd>
{% endfor %}

</dl>
""")

  error_template = renderers.Template("No information available for this Hunt.")

  ajax_template = renderers.Template("""
<div id="RunHuntResult_{{unique|escape}}"></div>
""")

  def RenderAjax(self, request, response):
    self.hunt_id = request.REQ.get("hunt_id")
    self.subject = rdfvalue.RDFURN(self.hunt_id)

    response = renderers.TemplateRenderer.Layout(
        self, request,
        response, apply_template=self.ajax_template)
    return self.CallJavascript(response,
                               "HuntOverviewRenderer.RenderAjax",
                               subject=self.subject,
                               hunt_id=self.hunt_id)

  def Layout(self, request, response):
    """Display the overview."""
    if not self.hunt_id:
      self.hunt_id = request.REQ.get("hunt_id")

    h = dict(main="ManageHuntsClientView", hunt_id=self.hunt_id)
    self.hash = urllib.urlencode(sorted(h.items()))
    self.data = {}
    self.args_str = ""

    if self.hunt_id:
      try:
        self.hunt = aff4.FACTORY.Open(self.hunt_id,
                                      aff4_type=implementation.GRRHunt,
                                      token=request.token)

        if self.hunt.state.Empty():
          raise IOError("No valid state could be found.")

        hunt_stats = self.hunt.state.context.usage_stats
        self.cpu_sum = "%.2f" % hunt_stats.user_cpu_stats.sum
        self.net_sum = hunt_stats.network_bytes_sent_stats.sum

        (self.all_clients_count, self.completed_clients_count,
         _) = self.hunt.GetClientsCounts()
        self.outstanding_clients_count = (
            self.all_clients_count - self.completed_clients_count)

        runner = self.hunt.GetRunner()
        self.hunt_name = runner.args.hunt_name
        self.hunt_creator = runner.context.creator

        self.data = py_collections.OrderedDict()
        self.data["Start Time"] = runner.context.start_time
        self.data["Expiry Time"] = runner.context.expires
        self.data["Status"] = self.hunt.Get(self.hunt.Schema.STATE)

        self.client_limit = runner.args.client_limit
        self.client_rate = runner.args.client_rate

        self.args_str = renderers.DictRenderer(
            self.hunt.state, filter_keys=["context"]).RawHTML(request)

        if runner.args.client_rule_set:
          self.client_rule_set = foreman.RuleArray(
              runner.args.client_rule_set).RawHTML(request)
        else:
          self.client_rule_set = "None"

      except IOError:
        self.layout_template = self.error_template

    return super(AbstractLogRenderer, self).Layout(request, response)


class HuntContextView(renderers.TemplateRenderer):
  """Render a the hunt context."""

  layout_template = renderers.Template("""
{{this.args_str|safe}}
""")

  def Layout(self, request, response):
    """Display hunt's context presented as dict."""
    if not hasattr(self, "hunt_id"):
      self.hunt_id = request.REQ.get("hunt_id")
    self.hunt = aff4.FACTORY.Open(self.hunt_id,
                                  aff4_type=implementation.GRRHunt,
                                  token=request.token)
    if self.hunt.state.Empty():
      raise IOError("No valid state could be found.")

    self.args_str = renderers.DictRenderer(self.hunt.state.context).RawHTML(
        request)

    return super(HuntContextView, self).Layout(request, response)


class HuntLogRenderer(renderers.AngularDirectiveRenderer):
  directive = "grr-hunt-log"

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["hunt-urn"] = request.REQ.get("hunt_id")
    return super(HuntLogRenderer, self).Layout(request, response)


class HuntErrorRenderer(renderers.AngularDirectiveRenderer):
  directive = "grr-hunt-errors"

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["hunt-urn"] = request.REQ.get("hunt_id")
    return super(HuntErrorRenderer, self).Layout(request, response)


class HuntClientViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected client of the selected hunt."""

  names = ["Status", "Hunt Log", "Hunt Errors", "Client Detail"]
  delegated_renderers = ["HuntClientOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntHostInformationRenderer"]

  post_parameters = ["hunt_id", "hunt_client"]

  def Layout(self, request, response):
    response = super(HuntClientViewTabs, self).Layout(request, response)
    return self.CallJavascript(response,
                               "HuntClientViewTabs.Layout",
                               hunt_id=self.state["hunt_id"])


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
    if hunt_id is not None and hunt_client is not None:
      try:
        self.client = aff4.FACTORY.Open(hunt_client,
                                        token=request.token,
                                        aff4_type=aff4_grr.VFSGRRClient)
        self.last_checkin = rdfvalue.RDFDatetime(self.client.Get(
            self.client.Schema.PING))

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
{% else %}
No data to graph yet.
{% endif %}
""")

  def Layout(self, request, response):
    self.hunt_id = request.REQ.get("hunt_id")

    hunt = aff4.FACTORY.Open(self.hunt_id, token=request.token)
    all_count, _, _ = hunt.GetClientsCounts()
    self.clients = bool(all_count)

    response = super(HuntClientGraphRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "HuntClientGraphRenderer.Layout",
                               hunt_id=self.hunt_id)


class HuntHostInformationRenderer(fileview.AFF4Stats):
  """Modified HostInformation that reads from hunt_client variable."""

  description = "Hunt Client Host Information"
  css_class = "TableBody"
  attributes_to_show = ["USERNAMES", "HOSTNAME", "MAC_ADDRESS", "INSTALL_DATE",
                        "SYSTEM", "CLOCK", "CLIENT_INFO"]

  def Layout(self, request, response):
    """Produce a summary of the client information."""
    client_id = request.REQ.get("hunt_client")
    if client_id:
      super(HuntHostInformationRenderer, self).Layout(
          request,
          response,
          client_id=client_id,
          aff4_path=rdf_client.ClientURN(client_id),
          age=aff4.ALL_TIMES)


class HuntStatsRenderer(renderers.TemplateRenderer):
  """Display hunt's resources usage stats."""

  layout_template = renderers.Template("""
<h3>Total number of clients: {{this.stats.user_cpu_stats.num|escape}}</h3>

<h3>User CPU</h3>
<dl class="dl-horizontal">
  <dt>User CPU mean</dt>
  <dd>{{this.stats.user_cpu_stats.mean|floatformat}}</dd>

  <dt>User CPU stdev</dt>
  <dd>{{this.stats.user_cpu_stats.std|floatformat}}</dd>

  <dt>Clients Histogram</dt>
  <dd class="histogram">
    <div id="user_cpu_{{unique|escape}}"></div>
  </dd>
</dl>

<h3>System CPU</h3>
<dl class="dl-horizontal">
  <dt>System CPU mean</dt>
  <dd>{{this.stats.system_cpu_stats.mean|floatformat}}</dd>

  <dt>System CPU stdev</dt>
  <dd>{{this.stats.system_cpu_stats.std|floatformat}}</dd>

  <dt>Clients Histogram</dt>
  <dd class="histogram">
    <div id="system_cpu_{{unique|escape}}"></div>
  </dd>
</dl>

<h3>Network bytes sent</h3>
<dl class="dl-horizontal">
  <dt>Network bytes sent mean</dt>
  <dd>{{this.stats.network_bytes_sent_stats.mean|floatformat}}</dd>

  <dt>Network bytes sent stdev</dt>
  <dd>{{this.stats.network_bytes_sent_stats.std|floatformat}}</dd>

  <dt>Clients Histogram</dt>
  <dd class="histogram">
    <div id="network_bytes_sent_{{unique|escape}}"></div>
  </dd>
</dl>

<h3>Worst performers</h3>
<div class="row">
<div class="col-md-8">
<table id="performers_{{unique|escape}}"
  class="table table-condensed table-striped table-bordered">
  <thead>
    <th>Client Id</th>
    <th>User CPU</th>
    <th>System CPU</th>
    <th>Network bytes sent</th>
  </thead>
  <tbody>
  {% for r in this.stats.worst_performers %}
    <tr>
      <td><a client_id="{{r.client_id|escape}}">{{r.client_id|escape}}</a></td>
      <td>{{r.cpu_usage.user_cpu_time|floatformat}}</td>
      <td>{{r.cpu_usage.system_cpu_time|floatformat}}</td>
      <td>{{r.network_bytes_sent|escape}}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</div>
</div>
""")
  error_template = renderers.Template("No information available for this Hunt.")

  def _HistogramToJSON(self, histogram):
    hist_data = [(b.range_max_value, b.num) for b in histogram.bins]
    return renderers.JsonDumpForScriptContext(hist_data)

  def Layout(self, request, response):
    """Layout the HuntStatsRenderer data."""
    hunt_id = request.REQ.get("hunt_id")

    if hunt_id:
      try:
        hunt = aff4.FACTORY.Open(hunt_id,
                                 aff4_type=implementation.GRRHunt,
                                 token=request.token)
        if hunt.state.Empty():
          raise IOError("No valid state could be found.")

        self.stats = hunt.state.context.usage_stats

        self.user_cpu_json_data = self._HistogramToJSON(
            self.stats.user_cpu_stats.histogram)
        self.system_cpu_json_data = self._HistogramToJSON(
            self.stats.system_cpu_stats.histogram)
        self.network_bytes_sent_json_data = self._HistogramToJSON(
            self.stats.network_bytes_sent_stats.histogram)

        response = super(HuntStatsRenderer, self).Layout(request, response)
        return self.CallJavascript(
            response,
            "HuntStatsRenderer.Layout",
            user_cpu_json_data=self.user_cpu_json_data,
            system_cpu_json_data=self.system_cpu_json_data,
            network_bytes_sent_json_data=self.network_bytes_sent_json_data)
      except IOError:
        self.layout_template = self.error_template
        return super(HuntStatsRenderer, self).Layout(request, response)


class HuntOutstandingRenderer(renderers.TableRenderer):
  """A renderer that shows debug information for outstanding clients."""

  post_parameters = ["hunt_id"]

  def __init__(self, **kwargs):
    super(HuntOutstandingRenderer, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Client"))
    self.AddColumn(semantic.RDFValueColumn("Flow"))
    self.AddColumn(semantic.RDFValueColumn("Incomplete Request #"))
    self.AddColumn(semantic.RDFValueColumn("State"))
    self.AddColumn(semantic.RDFValueColumn("Args Expected"))
    self.AddColumn(semantic.RDFValueColumn("Available Responses"))
    self.AddColumn(semantic.RDFValueColumn("Status"))
    self.AddColumn(semantic.RDFValueColumn("Expected Responses"))
    self.AddColumn(semantic.RDFValueColumn("Client Requests Pending"))

  def GetClientRequests(self, client_urns, token):
    """Returns all client requests for the given client urns."""
    task_urns = [urn.Add("tasks") for urn in client_urns]

    client_requests_raw = data_store.DB.MultiResolvePrefix(task_urns,
                                                           "task:",
                                                           token=token)

    client_requests = {}
    for client_urn, requests in client_requests_raw:
      client_id = str(client_urn)[6:6 + 18]

      client_requests.setdefault(client_id, [])

      for _, serialized, _ in requests:
        client_requests[client_id].append(rdf_flows.GrrMessage(serialized))

    return client_requests

  def GetAllSubflows(self, hunt_urn, client_urns, token):
    """Lists all subflows for a given hunt for all clients in client_urns."""
    client_ids = [urn.Split()[0] for urn in client_urns]
    client_bases = [hunt_urn.Add(client_id) for client_id in client_ids]

    all_flows = []
    act_flows = client_bases

    while act_flows:
      next_flows = []
      for _, children in aff4.FACTORY.MultiListChildren(act_flows, token=token):
        for flow_urn in children:
          next_flows.append(flow_urn)
      all_flows.extend(next_flows)
      act_flows = next_flows

    return all_flows

  def GetFlowRequests(self, flow_urns, token):
    """Returns all outstanding requests for the flows in flow_urns."""
    flow_requests = {}
    flow_request_urns = [flow_urn.Add("state") for flow_urn in flow_urns]

    for flow_urn, values in data_store.DB.MultiResolvePrefix(flow_request_urns,
                                                             "flow:",
                                                             token=token):
      for subject, serialized, _ in values:
        try:
          if "status" in subject:
            msg = rdf_flows.GrrMessage(serialized)
          else:
            msg = rdf_flows.RequestState(serialized)
        except Exception as e:  # pylint: disable=broad-except
          logging.warn("Error while parsing: %s", e)
          continue

        flow_requests.setdefault(flow_urn, []).append(msg)
    return flow_requests

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    hunt_id = request.REQ.get("hunt_id")
    token = request.token

    if hunt_id is None:
      return

    hunt_id = rdfvalue.RDFURN(hunt_id)
    hunt = aff4.FACTORY.Open(hunt_id,
                             aff4_type=implementation.GRRHunt,
                             age=aff4.ALL_TIMES,
                             token=token)

    clients_by_status = hunt.GetClientsByStatus()
    outstanding = clients_by_status["OUTSTANDING"]

    self.size = len(outstanding)

    outstanding = sorted(outstanding)[start_row:end_row]

    all_flow_urns = self.GetAllSubflows(hunt_id, outstanding, token)

    flow_requests = self.GetFlowRequests(all_flow_urns, token)

    try:
      client_requests = self.GetClientRequests(outstanding, token)
    except access_control.UnauthorizedAccess:
      client_requests = None

    waitingfor = {}
    status_by_request = {}

    for flow_urn in flow_requests:
      for obj in flow_requests[flow_urn]:
        if isinstance(obj, rdf_flows.RequestState):
          waitingfor.setdefault(flow_urn, obj)
          if waitingfor[flow_urn].id > obj.id:
            waitingfor[flow_urn] = obj
        elif isinstance(obj, rdf_flows.GrrMessage):
          status_by_request.setdefault(flow_urn, {})[obj.request_id] = obj

    response_urns = []

    for request_base_urn, request in waitingfor.iteritems():
      response_urns.append(rdfvalue.RDFURN(request_base_urn).Add("request:%08X"
                                                                 % request.id))

    response_dict = dict(data_store.DB.MultiResolvePrefix(
        response_urns, "flow:", token=token))

    row_index = start_row

    for flow_urn in sorted(all_flow_urns):
      request_urn = flow_urn.Add("state")
      client_id = flow_urn.Split()[2]
      try:
        request_obj = waitingfor[request_urn]
        response_urn = rdfvalue.RDFURN(request_urn).Add("request:%08X" %
                                                        request_obj.id)
        responses_available = len(response_dict.setdefault(response_urn, []))
        status_available = "No"
        responses_expected = "Unknown"
        if request_obj.id in status_by_request.setdefault(request_urn, {}):
          status_available = "Yes"
          status = status_by_request[request_urn][request_obj.id]
          responses_expected = status.response_id

        if client_requests is None:
          client_requests_available = "Must use raw access."
        else:
          client_requests_available = 0
          for client_req in client_requests.setdefault(client_id, []):
            if request_obj.request.session_id == client_req.session_id:
              client_requests_available += 1

        row_data = {
            "Client": client_id,
            "Flow": flow_urn,
            "Incomplete Request #": request_obj.id,
            "State": request_obj.next_state,
            "Args Expected": request_obj.request.args_rdf_name,
            "Available Responses": responses_available,
            "Status": status_available,
            "Expected Responses": responses_expected,
            "Client Requests Pending": client_requests_available
        }
      except KeyError:
        row_data = {
            "Client": client_id,
            "Flow": flow_urn,
            "Incomplete Request #": "No request found"
        }

      self.AddRow(row_data, row_index=row_index)
      row_index += 1
