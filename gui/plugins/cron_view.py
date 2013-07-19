#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2012 Google Inc. All Rights Reserved.

"""This is the interface for managing cron jobs."""


import json

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import flow_management
from grr.gui.plugins import new_hunt
from grr.lib import aff4
from grr.lib import cron
from grr.lib import flow
from grr.lib import rdfvalue


class ManageCron(renderers.Splitter2Way):
  """Manages Cron jobs."""
  description = "Cron Job Viewer"
  behaviours = frozenset(["General"])
  top_renderer = "CronTable"
  bottom_renderer = "CronJobManagementTabs"

  def Layout(self, request, response):
    response = super(ManageCron, self).Layout(request, response)
    return self.CallJavascript(response, "ManageCron.Layout")


class CronJobInformation(fileview.AFF4Stats):
  """Renderer displaying information about a cron job."""

  def Layout(self, request, response):
    """Introspect the Schema for flow objects."""
    if not hasattr(self, "cron_job_urn"):
      self.cron_job_urn = rdfvalue.RDFURN(request.REQ.get("cron_job_urn"))

    return super(CronJobInformation, self).Layout(request, response,
                                                  aff4_path=self.cron_job_urn)


class CronJobStateIcon(renderers.RDFValueRenderer):
  """Render the flow state by using an icon."""

  layout_template = renderers.Template("""
<div class="centered cron-job-state-icon" state="{{this.state|escape}}">
  <img class='grr-icon grr-flow-icon'
    src='/static/images/{{this.icon|escape}}' />
</div>""")

  def Layout(self, request, response):
    # self.proxy will contain an RDFValue that we're about to render. In
    # CronJobStateIcon's case, it will be CronJob.Schema.DISABLED AFF4
    # attribute, which is an RDFBool. Therefore we treat self.proxy as
    # a boolean value.
    if self.proxy:
      self.icon = "pause.png"
      self.state = "disabled"
    else:
      self.icon = "clock.png"
      self.state = "enabled"

    super(CronJobStateIcon, self).Layout(request, response)


class CronTable(renderers.TableRenderer):
  """Show all existing rules."""
  selection_publish_queue = "cron_select"

  layout_template = """
<div id="enable_cron_job_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="disable_cron_job_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="delete_cron_job_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="schedule_hunt_cron_job_dialog_{{unique|escape}}"
  class="modal wide-modal high-modal hide" update_on_show="true"
  tabindex="-1" role="dialog" aria-hidden="true">
</div>

<ul class="breadcrumb">
  <li>
  <div class="btn-group">
  <button id='schedule_hunt_cron_job_{{unique|escape}}' title='Schedule Hunt'
    class="btn" name="ScheduleHuntCronJob" data-toggle="modal"
    data-target="#schedule_hunt_cron_job_dialog_{{unique|escape}}">
    <img src='/static/images/new.png' class='toolbar_icon'>
  </button>
  </div>

  <div class="btn-group">
  <button id='enable_cron_job_{{unique|escape}}' title='Enable Cron Job'
    class="btn" name="EnableCronJob" data-toggle="modal"
    data-target="#enable_cron_job_dialog_{{unique|escape}}"
    disabled="true">
    <img src='/static/images/play_button.png' class='toolbar_icon'>
  </button>

  <button id='disable_cron_job_{{unique|escape}}' title='Disable Cron Job'
    class="btn" name="DisableCronJob" data-toggle="modal"
    data-target="#disable_cron_job_dialog_{{unique|escape}}"
    disabled="true">
    <img src='/static/images/pause_button.png' class='toolbar_icon'>
  </button>
  </div>

  <div class="btn-group">
  <button id='delete_cron_job_{{unique|escape}}' title='Delete Cron Job'
    class="btn" name="DeleteCronJob" data-toggle="modal"
    data-target="#delete_cron_job_dialog_{{unique|escape}}"
    disabled="true">
    <img src='/static/images/editdelete.png' class='toolbar_icon'>
  </button>
  </div>

  </li>
</ul>
""" + renderers.TableRenderer.layout_template

  def __init__(self, **kwargs):
    super(CronTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "State", renderer=CronJobStateIcon, width="40px"))
    self.AddColumn(renderers.RDFValueColumn(
        "Name", width="10%", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Last Run", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Frequency", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Description", width="70%"))

  def Layout(self, request, response):
    response = super(CronTable, self).Layout(request, response)
    return self.CallJavascript(response, "CronTable.Layout")

  def RenderAjax(self, request, response):
    """Renders the table."""
    cron_jobs_urns = cron.CRON_MANAGER.ListJobs(token=request.token)
    cron_jobs = aff4.FACTORY.MultiOpen(
        cron_jobs_urns, mode="r", aff4_type="CronJob", token=request.token)
    for cron_job in cron_jobs:
      self.AddRow({"State": cron_job.Get(cron_job.Schema.DISABLED, False),
                   "Name": cron_job.urn,
                   "Last Run": cron_job.Get(cron_job.Schema.LAST_RUN_TIME),
                   "Frequency": cron_job.Get(cron_job.Schema.FREQUENCY),
                   "Description": cron_job.Get(cron_job.Schema.DESCRIPTION)})

    # Call our baseclass to actually do the rendering
    return super(CronTable, self).RenderAjax(request, response)


class CronJobManagementTabs(renderers.TabLayout):
  """Tab renderer for cron job management."""
  names = ["Details", "Flows"]
  delegated_renderers = ["CronJobInformation", "CronJobView"]

  tab_hash = "cjt"

  empty_template = renderers.Template("""
<div class="padded">Please select a cron job to see the details.</div>
""")

  def Layout(self, request, response):
    if not request.REQ.get("cron_job_urn"):
      return self.RenderFromTemplate(self.empty_template, response)
    else:
      self.state = dict(cron_job_urn=request.REQ.get("cron_job_urn"))
      return super(CronJobManagementTabs, self).Layout(request, response)


class CronJobView(flow_management.ListFlowsTable):
  """Render a customized form for a foreman action."""

  with_toolbar = False

  layout_template = """
<div id="CronJobView_{{unique|escape}}" style="position: absolute; top: 45px;
  right: 0; left: 0">
""" + flow_management.ListFlowsTable.layout_template + """
</div>
<div id="FlowDetails_{{unique|escape}}" class="panel details-right-panel hide">
  <div class="padded">
    <button id="FlowDetailsClose_{{unique|escape}}" class="close">
      &times;
    </button>
  </div>
  <div id="FlowDetailsContent_{{unique|escape}}"></div>
</div>
"""

  def Layout(self, request, response):
    self.state["value"] = request.REQ.get("cron_job_urn")
    response = super(CronJobView, self).Layout(request, response)
    return self.CallJavascript(response, "CronJobView.Layout")


class CronJobManagementConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks confirmation to manage a cron job."""
  post_parameters = ["cron_job_urn"]

  flow_name = None
  action_name = None

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>{{this.action_name|escape}}</strong>
this cron job?</p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Cron job was {{this.action_name|escape}}d
successfully!</p>
""")

  @property
  def header(self):
    return self.action_name.title() + " a cron job?"

  def Layout(self, request, response):
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("cron_job_urn"))
    return super(CronJobManagementConfirmationDialog, self).Layout(
        request, response)

  def RenderAjax(self, request, response):
    flow.GRRFlow.StartFlow(
        None, self.flow_name, token=request.token,
        cron_job_urn=rdfvalue.RDFURN(request.REQ.get("cron_job_urn")))
    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique, this=self)


class DisableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks confirmation to disable a cron job."""

  flow_name = "DisableCronJobFlow"
  action_name = "disable"


class EnableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks confirmation to enable a cron job."""

  flow_name = "EnableCronJobFlow"
  action_name = "enable"


class DeleteCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks confirmation to delete a cron job."""

  flow_name = "DeleteCronJobFlow"
  action_name = "delete"


class ScheduleHuntCronJobDialog(renderers.WizardRenderer):
  """Schedule new cron job that launches a hunt periodically."""

  wizard_name = "hunt_run"
  title = "Schedule a Periodic Hunt"
  pages = [
      renderers.WizardPage(
          name="ConfigureFlow",
          description="What to run?",
          renderer="HuntConfigureFlow"),
      renderers.WizardPage(
          name="ConfigureOutput",
          description="Output Processing",
          renderer="HuntConfigureOutputPlugins"),
      renderers.WizardPage(
          name="ConfigureRules",
          description="Where to run?",
          renderer="HuntConfigureRules"),
      renderers.WizardPage(
          name="ConfigureTime",
          description="When to run?",
          renderer="CronHuntConfigureSchedule"),
      renderers.WizardPage(
          name="ReviewAndTest",
          description="Review",
          renderer="CronHuntReview",
          next_button_label="Schedule"),
      renderers.WizardPage(
          name="Done",
          description="Hunt cron job was created.",
          renderer="CronHuntSchedule",
          next_button_label="Ok!",
          show_back_button=False)
      ]

  def Layout(self, request, response):
    response = super(ScheduleHuntCronJobDialog, self).Layout(request, response)
    return self.CallJavascript(response, "ScheduleHuntCronJobDialog.Layout")


class CronHuntConfigureSchedule(renderers.TemplateRenderer):
  """Renderer that allows user to configure how often the hunt will run."""

  layout_template = renderers.Template("""
<div id="CronHuntConfigureSchedule_{{unique|escape}}"
  class="CronHuntConfigureSchedule padded">
<div class="well well-large">

<form class="form-horizontal">
  <div class="control-group">
    <label class="control-label">Periodicity</label>
    <div class="controls">
      <select name="periodicity">
        <option value="1">Daily</option>
        <option value="7">Weekly</option>
        <option value="14">Every 2 weeks</option>
      </select>
    </div>
  </div>
</form>

</div>
</div>
""")

  def Layout(self, request, response):
    response = super(CronHuntConfigureSchedule, self).Layout(request, response)
    return self.CallJavascript(response, "CronHuntConfigureSchedule.Layout")


class CronHuntReview(new_hunt.HuntInformation):
  """Shows generic hunt information plus its' cron scheduling settings."""

  hunt_details_template = new_hunt.HuntInformation.hunt_details_template + """
<h3>Hunt Periodicity</h3>
<div class="HuntPeriodicity">
  <p>Hunt will run <strong>{{this.periodicity_label|escape}}</strong>.</p>
</div>
"""

  def Layout(self, request, response):
    """Renders review page of a hunt cron scheduling wizard."""
    hunt_config_json = request.REQ.get("hunt_run")
    hunt_config = json.loads(hunt_config_json)

    periodicity = int(hunt_config["hunt_periodicity"])
    periodicity_labels = {1: "daily",
                          7: "weekly",
                          14: "every 2 weeks"}

    self.periodicity_label = periodicity_labels.get(
        periodicity, "every %d days" % periodicity)

    return super(CronHuntReview, self).Layout(request, response)


class CronHuntSchedule(renderers.TemplateRenderer,
                       new_hunt.HuntRequestParsingMixin):
  """Creates a cron job that runs given generic hunt."""

  layout_template = renderers.Template("""
<div class="CronHuntSchedulingSummary padded">
  <p class="text-success">Hunt was successfully scheduled!</p>
</div>
""")

  def Layout(self, request, response):
    """Attempt to run ScheduleGenericHuntFlow."""
    hunt_config_json = request.REQ.get("hunt_run")
    hunt_config = json.loads(hunt_config_json)
    periodicity = int(hunt_config["hunt_periodicity"])

    hunt_args = self.GetHuntArgsFromRequest(request)

    try:
      flow.GRRFlow.StartFlow(
          None, "ScheduleGenericHuntFlow",
          token=request.token,
          expiry_time=hunt_args["hunt_args"]["expiry_time"],
          client_limit=hunt_args["hunt_args"]["client_limit"],
          hunt_flow_name=hunt_args["flow_name"],
          hunt_flow_args=hunt_args["flow_args"],
          hunt_rules=hunt_args["rules"],
          output_plugins=hunt_args["output"],
          hunt_periodicity=periodicity)
    except RuntimeError as e:
      return self.Fail(e, request, response)

    return super(CronHuntSchedule, self).Layout(request, response)
