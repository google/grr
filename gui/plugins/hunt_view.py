#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2012 Google Inc. All Rights Reserved.

"""This is the interface for managing hunts."""


import collections as py_collections
import json
import operator
import StringIO
import urllib


from django import http
import matplotlib.pyplot as plt

import logging

from grr.gui import renderers
from grr.gui.plugins import crash_view
from grr.gui.plugins import fileview
from grr.gui.plugins import foreman
from grr.gui.plugins import searchclient
from grr.lib import aff4
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib.hunts import output_plugins


class ManageHunts(renderers.Splitter2Way):
  """Manages Hunts GUI Screen."""
  description = "Hunt Manager"
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
<div class="centered hunt-state-icon" state="{{state_str|escape}}">
<img class='grr-icon grr-flow-icon' src='/static/images/{{icon|escape}}' />
</div>
""")

  # Maps the flow states to icons we can show
  state_map = {rdfvalue.Flow.State.TERMINATED: "stock_yes.png",
               rdfvalue.Flow.State.RUNNING: "clock.png",
               rdfvalue.Flow.State.ERROR: "nuke.png",
               hunts.GRRHunt.STATE_STOPPED: "pause.png"}

  def Layout(self, _, response):
    self.state_str = str(self.proxy)
    return self.RenderFromTemplate(
        self.layout_template, response,
        state_str=str(self.proxy),
        icon=self.state_map.get(self.proxy, "question-red.png"))


class RunHuntConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks confirmation to run a hunt and actually runs it."""
  post_parameters = ["hunt_id"]

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
    flow.GRRFlow.StartFlow(None, "RunHuntFlow", token=request.token,
                           hunt_urn=rdfvalue.RDFURN(request.REQ.get("hunt_id")))
    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique)


class PauseHuntConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks confirmation to pause a hunt and actually runs it."""
  post_parameters = ["hunt_id"]

  header = "Pause a hunt?"

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>pause</strong> this hunt?</p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt paused successfully!</p>
""")

  def Layout(self, request, response):
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    return super(PauseHuntConfirmationDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    flow.GRRFlow.StartFlow(None, "PauseHuntFlow", token=request.token,
                           hunt_urn=rdfvalue.RDFURN(request.REQ.get("hunt_id")))
    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique)


class ModifyHuntDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that allows user to modify certain hunt parameters."""
  post_parameters = ["hunt_id"]

  header = "Modify a hunt"
  proceed_button_title = "Modify!"

  expiry_time_dividers = ((60*60*24, "d"), (60*60, "h"), (60, "m"), (1, "s"))

  content_template = renderers.Template("""
{{this.hunt_params_form|safe}}
""")

  ajax_template = renderers.Template("""
<p class="text-info">Hunt modified successfully!</p>
""")

  def Layout(self, request, response):
    """Layout handler."""
    hunt_urn = rdfvalue.RDFURN(request.REQ.get("hunt_id"))
    hunt_obj = aff4.FACTORY.Open(hunt_urn, aff4_type="GRRHunt",
                                 token=request.token)

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    req = dict()
    req["client_limit"] = hunt_obj.state.context.client_limit
    req["expiry_time"] = hunt_obj.state.context.expiry_time

    self.hunt_params_form = type_descriptor_renderer.Form(
        hunts.GRRHunt.hunt_typeinfo, req, prefix="")
    self.check_access_subject = hunt_urn

    return super(ModifyHuntDialog, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Starts ModifyHuntFlow that actually modifies a hunt."""
    hunt_urn = request.REQ.get("hunt_id")

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    hunt_args = dict(type_descriptor_renderer.ParseArgs(
        hunts.GRRHunt.hunt_typeinfo, request, prefix=""))

    flow.GRRFlow.StartFlow(None, "ModifyHuntFlow", token=request.token,
                           hunt_urn=rdfvalue.RDFURN(hunt_urn),
                           expiry_time=hunt_args["expiry_time"],
                           client_limit=hunt_args["client_limit"])

    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique)


class HuntTable(fileview.AbstractFileTable):
  """Show all hunts."""
  selection_publish_queue = "hunt_select"

  layout_template = """
<div id="new_hunt_dialog_{{unique|escape}}"
  class="modal wide-modal high-modal hide" update_on_show="true"
  tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="run_hunt_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="pause_hunt_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="modify_hunt_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<ul class="breadcrumb">
  <li>
  <button id='new_hunt_{{unique|escape}}' title='New Hunt'
    class="btn" name="NewHunt" data-toggle="modal"
    data-target="#new_hunt_dialog_{{unique|escape}}">
    <img src='/static/images/new.png' class='toolbar_icon'>
  </button>

  <div class="btn-group">
  <button id='run_hunt_{{unique|escape}}' title='Run Hunt'
    class="btn" disabled="yes" name="RunHunt" data-toggle="modal"
    data-target="#run_hunt_dialog_{{unique|escape}}">
    <img src='/static/images/play_button.png' class='toolbar_icon'>
  </button>
  <button id='pause_hunt_{{unique|escape}}' title='Pause Hunt'
    class="btn" disabled="yes" name="PauseHunt" data-toggle="modal"
    data-target="#pause_hunt_dialog_{{unique|escape}}">
    <img src='/static/images/pause_button.png' class='toolbar_icon'>
  </button>
  <button id='modify_hunt_{{unique|escape}}' title='Modify Hunt'
    class="btn" disabled="yes" name="ModifyHunt" data-toggle="modal"
    data-target="#modify_hunt_dialog_{{unique|escape}}">
    <img src='/static/images/modify.png' class='toolbar_icon'>
  </button>
  </div>

  <div class="new_hunt_dialog" id="new_hunt_dialog_{{unique|escape}}"
    class="hide" />
  </li>
</ul>
""" + fileview.AbstractFileTable.layout_template + """
<script>
(function() {
  // Store currently selected hunt_id in this variable. Event listeners
  // will use it (see grr.subscribe("file_select"), for example).
  var hunt_id;

  $("#new_hunt_dialog_{{unique|escapejs}}").on("shown", function () {
    grr.layout("NewHunt", "new_hunt_dialog_{{unique|escapejs}}");
  }).on("hidden", function () {
    $("#{{unique|escapejs}}").trigger("refresh");
    $(this).html("");
  });

  $("#run_hunt_dialog_{{unique|escape}}").on("show", function() {
    grr.layout("RunHuntConfirmationDialog",
      "run_hunt_dialog_{{unique|escape}}", {hunt_id: hunt_id});
  }).on("hidden", function () {
    $("#{{unique|escapejs}}").trigger("refresh");
    $(this).html("");
  });

  $("#pause_hunt_dialog_{{unique|escape}}").on("show", function() {
    grr.layout("PauseHuntConfirmationDialog",
      "pause_hunt_dialog_{{unique|escape}}", {hunt_id: hunt_id});
  }).on("hidden", function () {
    $("#{{unique|escapejs}}").trigger("refresh");
    $(this).html("");
  });

  $("#modify_hunt_dialog_{{unique|escape}}").on("show", function() {
    grr.layout("ModifyHuntDialog", "modify_hunt_dialog_{{unique|escape}}",
      {hunt_id: hunt_id});
  }).on("hidden", function () {
    $("#{{unique|escapejs}}").trigger("refresh");
    $(this).html("");
  });

  grr.subscribe("WizardComplete", function(wizardStateName) {
    $("#new_hunt_dialog_{{unique|escape}}").modal("hide");
  }, "new_hunt_dialog_{{unique|escape}}");

  grr.subscribe("file_select", function(_hunt_id) {
    hunt_id = _hunt_id;

    var row = $("span[aff4_path='" + hunt_id + "']",
      "#{{this.id|escapejs}}").closest("tr");
    $(".hunt-state-icon", row).each(function() {
      var state = $(this).attr("state");
      if (state == "RUNNING") {
        $("#run_hunt_{{unique|escape}}").attr("disabled", "true");
        $("#modify_hunt_{{unique|escape}}").attr("disabled", "true");
        $("#pause_hunt_{{unique|escape}}").removeAttr("disabled");
      } else if (state == "stopped") {
        $("#run_hunt_{{unique|escape}}").removeAttr("disabled");
        $("#modify_hunt_{{unique|escape}}").removeAttr("disabled");
        $("#pause_hunt_{{unique|escape}}").attr("disabled", "true");
      }
    });
  }, "run_hunt_{{unique|escapejs}}");

  // If hunt_id in hash, click that row.
  if (grr.hash.hunt_id) {
    $("#{{this.id|escapejs}}").find("td:contains('" +
      grr.hash.hunt_id.split("/").reverse()[0] +
      "')").click();
  }
})();
</script>
"""

  root_path = "aff4:/hunts"

  def __init__(self, **kwargs):
    super(HuntTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Status", renderer=HuntStateIcon, width="40px"))

    # The hunt id is the AFF4 URN for the hunt object.
    self.AddColumn(renderers.RDFValueColumn(
        "Hunt ID", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Name"))
    self.AddColumn(renderers.RDFValueColumn("Start Time", width="16em"))
    self.AddColumn(renderers.RDFValueColumn("Expires", width="16em"))
    self.AddColumn(renderers.RDFValueColumn("Client Limit"))
    self.AddColumn(renderers.RDFValueColumn("Creator"))
    self.AddColumn(renderers.RDFValueColumn("Description", width="100%"))

  def BuildTable(self, start_row, end_row, request):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=request.token)
    try:
      children = list(fd.ListChildren())

      children.sort(key=operator.attrgetter("age"), reverse=True)
      children = children[start_row:end_row]

      hunt_list = [x for x in fd.OpenChildren(children=children)
                   if isinstance(x, hunts.GRRHunt)]
      total_size = len(hunt_list)

      hunt_list.sort(key=lambda x: x.state.context.get("create_time", 0),
                     reverse=True)

      could_not_display = []
      row_index = start_row
      for hunt_obj in hunt_list:
        if not isinstance(hunt_obj, hunts.GRRHunt):
          could_not_display.append((hunt_obj, "Object is not a valid hunt."))
          continue
        if hunt_obj.state.Empty():
          logging.error("Hunt without a valid state found: %s", hunt_obj)
          could_not_display.append((hunt_obj,
                                    "Hunt doesn't have a valid state."))
          continue

        context = hunt_obj.state.context
        expire_time = (context.start_time +
                       context.expiry_time.seconds) * 1e6

        description = (context.description or
                       hunt_obj.__class__.__doc__.split("\n", 1)[0])

        if context.hunt_state == hunts.GRRHunt.STATE_STOPPED:
          hunt_state = hunts.GRRHunt.STATE_STOPPED
        else:
          hunt_state = context.state

        self.AddRow({"Hunt ID": hunt_obj.urn,
                     "Name": hunt_obj.__class__.__name__,
                     "Status": hunt_state,
                     "Start Time": rdfvalue.RDFDatetime(
                         context.start_time * 1e6),
                     "Expires": rdfvalue.RDFDatetime(expire_time),
                     "Client Limit": context.client_limit,
                     "Creator": context.user,
                     "Description": description},
                    row_index=row_index)
        row_index += 1

      for hunt_obj, reason in could_not_display:
        self.AddRow({"Hunt ID": hunt_obj.urn,
                     "Description": reason},
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

  names = ["Overview", "Log", "Errors", "Rules", "Graph", "Results", "Stats",
           "Crashes"]
  # TODO(user): Add Renderer for Hunt Resource Usage (CPU/IO etc).
  delegated_renderers = ["HuntOverviewRenderer", "HuntLogRenderer",
                         "HuntErrorRenderer", "HuntRuleRenderer",
                         "HuntClientGraphRenderer", "HuntResultsRenderer",
                         "HuntStatsRenderer", "HuntCrashesRenderer"]

  subscribe_script_template = renderers.Template("""
<script>
  // When the hunt id is selected, redraw the tabs below.
  grr.subscribe("file_select", function(hunt_id) {
    grr.layout("HuntViewTabs", "main_bottomPane", {hunt_id: hunt_id});
  }, "{{unique|escapejs}}");
</script>
""")

  empty_template = renderers.Template("""
<div class="padded" id="{{unique|escape}}">
<p>Please select a hunt to see its details here.</p>
</div>
""") + subscribe_script_template
  layout_template = (renderers.TabLayout.layout_template +
                     subscribe_script_template)

  post_parameters = ["hunt_id"]

  def Layout(self, request, response):
    hunt_id = request.REQ.get("hunt_id")
    if hunt_id:
      super(HuntViewTabs, self).Layout(request, response)
    else:
      super(HuntViewTabs, self).Layout(request, response,
                                       apply_template=self.empty_template)


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
<span class='pull-right'> Filter by State
<select id='{{unique|escape}}_select'>
  <option>ALL</option>
  <option>OUTSTANDING</option>
  <option>COMPLETED</option>
  <option>BAD</option>
</select>
</span>
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

  $("#" + "{{unique|escape}}_select").change(function () {
    grr.state.completion_status = $("#{{unique|escape}}_select").val();
    grr.layout('HuntClientTableRenderer', 'main_topPane', grr.state);
  });

</script>
"""

  post_parameters = ["hunt_id"]

  def __init__(self, **kwargs):
    super(HuntClientTableRenderer, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Client ID", width="20%", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Hostname", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Status", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("User CPU seconds", width="10%",
                                            renderer=FloatRenderer))
    self.AddColumn(renderers.RDFValueColumn("System CPU seconds", width="10%",
                                            renderer=FloatRenderer))
    self.AddColumn(renderers.RDFValueColumn("CPU",
                                            renderer=ResourceRenderer,
                                            width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Network bytes sent", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Network",
                                            renderer=ResourceRenderer,
                                            width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Last Checkin", width="10%"))

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
    completion_status_filter = request.REQ.get("completion_status", "ALL")
    if hunt_id is None:
      return
    try:
      self.hunt = aff4.FACTORY.Open(hunt_id, token=request.token,
                                    aff4_type="GRRHunt", age=aff4.ALL_TIMES)
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


class HuntOverviewRenderer(renderers.AbstractLogRenderer):
  """Renders the overview tab."""

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

  <dt>Hunt Results URN</dt>
  <dd>{{ this.hunt.urn|escape }}/Results</dd>

  <dt>Creator</dt>
  <dd>{{ this.hunt_creator|escape }}</dd>

  <dt>Client Limit</dt>
  <dd>{{ this.client_limit|escape }}</dd>

  <dt>Client Count</dt>
  <dd>{{ this.hunt.NumClients|escape }}</dd>

  <dt>Outstanding</dt>
  <dd>{{ this.hunt.NumOutstanding|escape }}</dd>

  <dt>Completed</dt>
  <dd>{{ this.hunt.NumCompleted|escape }}</dd>

  <dt>Total CPU seconds used</dt>
  <dd>{{ this.cpu_sum|escape }}</dd>

  <dt>Total network traffic</dt>
  <dd>{{ this.net_sum|filesizeformat }}</dd>

  <dt>Arguments</dt><dd>{{ this.args_str|safe }}</dd>

{% for key, val in this.data.items %}
  <dt>{{ key|escape }}</dt><dd>{{ val|escape }}</dd>
{% endfor %}

</dl>
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
        self.hunt = aff4.FACTORY.Open(self.hunt_id, aff4_type="GRRHunt",
                                      token=request.token, age=aff4.ALL_TIMES)
        if self.hunt.state.Empty():
          raise IOError("No valid state could be found.")

        resources = self.hunt.GetValuesForAttribute(
            self.hunt.Schema.RESOURCES)
        self.cpu_sum, self.net_sum = 0, 0
        for resource in resources:
          self.cpu_sum += resource.cpu_usage.user_cpu_time
          self.net_sum += resource.network_bytes_sent

        self.cpu_sum = "%.2f" % self.cpu_sum

        self.hunt_name = self.hunt.state.context.hunt_name
        self.hunt_creator = self.hunt.state.context.creator

        self.data = py_collections.OrderedDict()
        self.data["Start Time"] = rdfvalue.RDFDatetime(
            self.hunt.state.context.start_time * 1e6)
        self.data["Expiry Time"] = rdfvalue.RDFDatetime(
            (self.hunt.state.context.start_time +
             self.hunt.state.context.expiry_time.seconds) * 1e6)

        if self.hunt.state.context.hunt_state == self.hunt.STATE_STOPPED:
          self.data["Status"] = self.hunt.STATE_STOPPED
        else:
          self.data["Status"] = self.hunt.state.context.state

        self.client_limit = self.hunt.state.context.client_limit
        args_dict = self.hunt.state.Copy()

        self.args_str = renderers.DictRenderer(args_dict).RawHTML()
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

  error_template = renderers.Template(
      "No information available for this Hunt.")

  def RenderAjax(self, request, response):
    """Renders the table."""
    hunt_id = request.REQ.get("hunt_id")
    if hunt_id is not None:
      hunt = aff4.FACTORY.Open(hunt_id, aff4_type="GRRHunt",
                               age=aff4.ALL_TIMES, token=request.token)

      if not hunt.state.Empty():
        # Getting list of rules from hunt object: this doesn't require us to
        # have admin privileges (which we need to go through foreman rules).
        for rule in hunt.state.context.rules:
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
    if hunt_id is not None and hunt_client is not None:
      try:
        self.client = aff4.FACTORY.Open(hunt_client, token=request.token,
                                        aff4_type="VFSGRRClient")
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


class HuntResultsRenderer(renderers.RDFValueCollectionRenderer):
  """Displays a collection of hunt's results."""

  error_template = renderers.Template("""
<p>This hunt hasn't stored any results yet.</p>
""")

  no_plugin_template = renderers.Template("""
<p>This hunt is not configured to store results in a collection.</p>
""")

  def Layout(self, request, response):
    """Layout the hunt results."""
    hunt_id = request.REQ.get("hunt_id")
    hunt = aff4.FACTORY.Open(hunt_id, age=aff4.ALL_TIMES, token=request.token)

    # TODO(user): In theory a hunt might choose to store the results in
    # multiple collections. We only show the first one here.
    output_objects = hunt.GetOutputObjects(
        output_cls=output_plugins.CollectionPlugin)
    if not output_objects:
      return self.RenderFromTemplate(self.no_plugin_template, response)
    collection = output_objects[0].GetCollection()
    if collection:
      return super(HuntResultsRenderer, self).Layout(
          request, response, aff4_path=collection.urn)
    else:
      return self.RenderFromTemplate(self.error_template, response)


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

  <dt>Clients Hisogram</dt>
  <dd class="histogram">
    <div id="network_bytes_sent_{{unique|escape}}"></div>
  </dd>
</dl>

<h3>Worst performers</h3>
<div class="row">
<div class="span8">
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

<script>
(function() {
  $("#performers_{{unique|escapejs}} a[client_id!='']").click(function () {
    client_id = $(this).attr("client_id");
    grr.state.client_id = client_id;
    grr.publish("hash_state", "c", client_id);

    // Clear the authorization for new clients.
    grr.publish("hash_state", "reason", "");
    grr.state.reason = "";

    grr.publish("hash_state", "main", null);
    grr.publish("client_selection", client_id);
  });

  function formatTimeTick(tick) {
    if (Math.abs(Math.floor(tick) - tick) > 1e-7) {
      return tick.toFixed(1);
    } else {
      return Math.floor(tick);
    }
  }

  function formatBytesTick(tick) {
    if (tick < 1024) {
      return tick + "B";
    } else {
      return Math.round(tick / 1024) + "K";
    }
  }

  function plotStats(statName, jsonString, formatTickFn) {
    var srcData = $.parseJSON(jsonString);
    var data = [];
    var ticks = [];
    for (var i = 0; i < srcData.length; ++i) {
      data.push([i, srcData[i][1]]);
      ticks.push([i + 0.5, formatTickFn(srcData[i][0])]);
    }

    $.plot("#" + statName + "_{{unique|escapejs}}", [data], {
      series: {
        bars: {
          show: true,
          lineWidth: 1
        }
      },
      xaxis: {
        tickLength: 0,
        ticks: ticks,
      },
      yaxis: {
        minTickSize: 1,
        tickDecimals: 0,
      }
    });
  }

  plotStats("user_cpu",
    "{{this.user_cpu_json_data|escapejs}}", formatTimeTick);
  plotStats("system_cpu",
    "{{this.system_cpu_json_data|escapejs}}", formatTimeTick);
  plotStats("network_bytes_sent",
    "{{this.network_bytes_sent_json_data|escapejs}}", formatBytesTick);
})();
</script>
""")
  error_template = renderers.Template(
      "No information available for this Hunt.")

  def _HistogramToJSON(self, histogram):
    return json.dumps([(b.range_max_value, b.num) for b in histogram.bins])

  def Layout(self, request, response):
    """Layout the HuntStatsRenderer data."""
    hunt_id = request.REQ.get("hunt_id")

    if hunt_id:
      try:
        hunt = aff4.FACTORY.Open(hunt_id,
                                 aff4_type="GRRHunt",
                                 token=request.token, age=aff4.ALL_TIMES)
        if hunt.state.Empty():
          raise IOError("No valid state could be found.")

        self.stats = hunt.state.context.usage_stats

        self.user_cpu_json_data = self._HistogramToJSON(
            self.stats.user_cpu_stats.histogram)
        self.system_cpu_json_data = self._HistogramToJSON(
            self.stats.user_cpu_stats.histogram)
        self.network_bytes_sent_json_data = self._HistogramToJSON(
            self.stats.network_bytes_sent_stats.histogram)
      except IOError:
        self.layout_template = self.error_template

    return super(HuntStatsRenderer, self).Layout(request, response)


class HuntCrashesRenderer(crash_view.ClientCrashCollectionRenderer):
  """View launched flows in a tree."""

  def Layout(self, request, response):
    hunt_id = request.REQ.get("hunt_id")
    self.crashes_urn = rdfvalue.RDFURN(hunt_id).Add("crashes")
    super(HuntCrashesRenderer, self).Layout(request, response)
