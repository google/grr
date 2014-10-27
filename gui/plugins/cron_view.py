#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#

"""This is the interface for managing cron jobs."""


import itertools
import time

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import flow_management
from grr.gui.plugins import forms
from grr.gui.plugins import new_hunt
from grr.gui.plugins import semantic
from grr.gui.plugins import wizards
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import cronjobs


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


class CronJobStateIcon(semantic.RDFValueRenderer):
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
  class="modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="disable_cron_job_dialog_{{unique|escape}}"
  class="modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="delete_cron_job_dialog_{{unique|escape}}"
  class="modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="run_cron_job_dialog_{{unique|escape}}"
  class="modal" tabindex="-1" role="dialog" aria-hidden="true">
</div>

<div id="schedule_hunt_cron_job_dialog_{{unique|escape}}"
  class="modal wide-modal high-modal" update_on_show="true"
  tabindex="-1" role="dialog" aria-hidden="true">
</div>

<ul class="breadcrumb">
  <li>
  <div class="btn-group">
  <button id='schedule_hunt_cron_job_{{unique|escape}}' title='Schedule Hunt'
    class="btn btn-default" name="ScheduleHuntCronJob" data-toggle="modal"
    data-target="#schedule_hunt_cron_job_dialog_{{unique|escape}}"
    >
      <img src='/static/images/new.png' class='toolbar_icon'>
  </button>
  </div>

  <div class="btn-group">
  <button id='enable_cron_job_{{unique|escape}}' title='Enable Cron Job'
    class="btn btn-default" name="EnableCronJob" data-toggle="modal"
    data-target="#enable_cron_job_dialog_{{unique|escape}}"
    disabled="true"
    >
      <img src='/static/images/play_button.png' class='toolbar_icon'>
  </button>

  <button id='run_cron_job_{{unique|escape}}' title='Force Run Cron Job'
    class="btn btn-default" name="RunCronJob" data-toggle="modal"
    data-target="#run_cron_job_dialog_{{unique|escape}}"
    disabled="true"
    >
      <img src='/static/images/play_force_button.png' class='toolbar_icon'>
  </button>

  <button id='disable_cron_job_{{unique|escape}}' title='Disable Cron Job'
    class="btn btn-default" name="DisableCronJob" data-toggle="modal"
    data-target="#disable_cron_job_dialog_{{unique|escape}}"
    disabled="true"
    >
      <img src='/static/images/pause_button.png' class='toolbar_icon'>
  </button>
  </div>

  <div class="btn-group">
  <button id='delete_cron_job_{{unique|escape}}' title='Delete Cron Job'
    class="btn btn-default" name="DeleteCronJob" data-toggle="modal"
    data-target="#delete_cron_job_dialog_{{unique|escape}}"
    disabled="true"
    >
      <img src='/static/images/editdelete.png' class='toolbar_icon'>
  </button>
  </div>

  </li>
</ul>
""" + renderers.TableRenderer.layout_template

  def __init__(self, **kwargs):
    super(CronTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn(
        "State", renderer=CronJobStateIcon, width="40px"))
    self.AddColumn(semantic.RDFValueColumn(
        "Name", width="10%", renderer=semantic.SubjectRenderer))
    self.AddColumn(semantic.RDFValueColumn("Last Run", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Frequency", width="10%"))
    self.AddColumn(semantic.RDFValueColumn("Description", width="70%"))

  def Layout(self, request, response):
    response = super(CronTable, self).Layout(request, response)
    return self.CallJavascript(response, "CronTable.Layout")

  def IsCronJobFailing(self, cron_job):
    """Returns True if there are more than 1 failures during last 4 runs."""
    statuses = itertools.islice(
        cron_job.GetValuesForAttribute(cron_job.Schema.LAST_RUN_STATUS), 0, 4)

    failures_count = 0
    for status in statuses:
      if status.status != rdfvalue.CronJobRunStatus.Status.OK:
        failures_count += 1

    return failures_count >= 2

  def IsCronJobStuck(self, cron_job):
    """Returns True if more than "2 * periodicity" has passed since last run."""
    last_run_time = cron_job.Get(cron_job.Schema.LAST_RUN_TIME)
    if not last_run_time:
      return True

    periodicity = cron_job.Get(cron_job.Schema.CRON_ARGS).periodicity
    return (time.time() - last_run_time.AsSecondsFromEpoch() >
            periodicity.seconds * 2)

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    cron_jobs_urns = list(cronjobs.CRON_MANAGER.ListJobs(token=request.token))
    cron_jobs = aff4.FACTORY.MultiOpen(
        cron_jobs_urns[start_row:end_row], aff4_type="CronJob",
        token=request.token, age=aff4.ALL_TIMES)

    for i, cron_job in enumerate(sorted(cron_jobs)):
      if self.IsCronJobFailing(cron_job):
        self.SetRowClass(i + start_row, "danger")
      elif self.IsCronJobStuck(cron_job):
        self.SetRowClass(i + start_row, "warning")

      cron_args = cron_job.Get(cron_job.Schema.CRON_ARGS)
      if cron_args is not None:
        self.AddCell(i + start_row, "State",
                     cron_job.Get(cron_job.Schema.DISABLED, False))

        self.AddCell(i+start_row, "Name", cron_job.urn)
        self.AddCell(i+start_row, "Last Run",
                     cron_job.Get(cron_job.Schema.LAST_RUN_TIME))
        self.AddCell(i+start_row, "Frequency", cron_args.periodicity)
        self.AddCell(i+start_row, "Description", cron_args.description)


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
  post_parameters = ["cron_urn"]

  action_name = rdfvalue.ManageCronJobFlowArgs.Action.NOOP

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
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("cron_urn"))
    return super(CronJobManagementConfirmationDialog, self).Layout(
        request, response)

  def RenderAjax(self, request, response):
    cron_urn = rdfvalue.RDFURN(request.REQ.get("cron_urn"))

    flow.GRRFlow.StartFlow(
        flow_name="ManageCronJobFlow", action=self.action_name,
        urn=cron_urn, token=request.token)

    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique, this=self)


class DisableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to disable a cron job."""

  action_name = rdfvalue.ManageCronJobFlowArgs.Action.DISABLE


class EnableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to enable a cron job."""

  action_name = rdfvalue.ManageCronJobFlowArgs.Action.ENABLE


class DeleteCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to delete a cron job."""
  action_name = rdfvalue.ManageCronJobFlowArgs.Action.DELETE


class ForceRunCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to force a cron job run.

  This action can be run at any time regardless of whether the cronjob is
  enabled or disabled.
  """
  action_name = rdfvalue.ManageCronJobFlowArgs.Action.RUN


class CronConfigureSchedule(renderers.TemplateRenderer):
  """Renderer that allows user to configure how often the hunt will run."""
  description = "When to run?"

  layout_template = renderers.Template("""
<div id="CronHuntConfigureSchedule_{{unique|escape}}"
  class="CronHuntConfigureSchedule padded">
<div class="well well-large">
{{this.cron_form|safe}}
</div>
</div>
""")

  cron_suppressions = ["flow_runner_args", "flow_args"]

  def Validate(self, request, response):
    pass

  def Layout(self, request, response):
    cron_args = rdfvalue.CreateCronJobFlowArgs()
    cron_args.flow_runner_args.flow_name = "CreateAndRunGenericHuntFlow"

    self.cron_form = forms.SemanticProtoFormRenderer(
        cron_args, id=self.id,
        supressions=self.cron_suppressions,
        prefix="cron").RawHTML(request)

    return super(CronConfigureSchedule, self).Layout(request, response)


class CronHuntParser(new_hunt.HuntArgsParser):

  def ParseCronParameters(self):
    cron_parmeters = forms.SemanticProtoFormRenderer(
        rdfvalue.CreateCronJobFlowArgs(), prefix="cron").ParseArgs(
            self.request)

    cron_parmeters.flow_runner_args.flow_name = "CreateAndRunGenericHuntFlow"
    cron_parmeters.flow_args.hunt_runner_args = self.ParseHuntRunnerArgs()
    cron_parmeters.flow_args.hunt_args = self.ParseHuntArgs()

    return cron_parmeters


class CronReview(new_hunt.HuntInformation):
  """Shows generic hunt information plus its' cron scheduling settings."""

  ajax_template = renderers.Template("""
<h3>Hunt Periodicity</h3>
<div class="HuntPeriodicity">
  <p>Hunt will run <strong>{{this.cron_arg.periodicity|escape}}</strong>.</p>
</div>
""") + new_hunt.HuntInformation.ajax_template

  def RenderAjax(self, request, response):
    """Renders review page of a hunt cron scheduling wizard."""
    parser = CronHuntParser(request)

    self.cron_arg = parser.ParseCronParameters()

    return super(CronReview, self).RenderAjax(request, response)


class CronSchedule(new_hunt.HuntInformation):
  """Creates a cron job that runs given generic hunt."""

  ajax_template = renderers.Template("""
<div class="CronHuntSchedulingSummary padded">
  <p class="text-success">Hunt was successfully scheduled!</p>
</div>
""")

  def RenderAjax(self, request, response):
    """Attempt to schedule the new cron job."""
    parser = CronHuntParser(request)

    self.cron_arg = parser.ParseCronParameters()

    # Create the cron job through the suid flow.
    flow.GRRFlow.StartFlow(flow_name="CreateCronJobFlow",
                           token=request.token, args=self.cron_arg)

    return super(CronSchedule, self).RenderAjax(request, response)


class CronConfigureFlow(new_hunt.HuntConfigureFlow):
  right_renderer = "CronFlowForm"


class CronFlowForm(new_hunt.HuntFlowForm):
  suppressions = ["description"] + new_hunt.HuntFlowForm.suppressions


class CronConfigureOutputPlugins(new_hunt.HuntConfigureOutputPlugins):
  pass


class CronConfigureRules(new_hunt.ConfigureHuntRules):
  pass


class ScheduleHuntCronJobDialog(wizards.WizardRenderer):
  """Schedule new cron job that launches a hunt periodically."""

  wizard_name = "hunt_run"
  title = "Schedule a Periodic Hunt"
  pages = [
      CronConfigureFlow,
      CronConfigureOutputPlugins,
      CronConfigureRules,
      CronConfigureSchedule,
      CronReview,
      CronSchedule,
      ]

  def Layout(self, request, response):
    response = super(ScheduleHuntCronJobDialog, self).Layout(request, response)
    return self.CallJavascript(response, "ScheduleHuntCronJobDialog.Layout")
