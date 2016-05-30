#!/usr/bin/env python
# -*- Mode: python; encoding: utf-8 -*-
#
"""This is the interface for managing cron jobs."""


from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import flow_management
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import cronjobs


class ManageCron(renderers.AngularDirectiveRenderer):
  """Manages Cron jobs."""

  directive = "grr-cron-view"

  description = "Cron Job Viewer"
  behaviours = frozenset(["General"])


class CronJobInformation(fileview.AFF4Stats):
  """Renderer displaying information about a cron job."""

  def Layout(self, request, response):
    """Introspect the Schema for flow objects."""
    if not hasattr(self, "cron_job_urn"):
      self.cron_job_urn = rdfvalue.RDFURN(request.REQ.get("cron_job_urn"))

    return super(CronJobInformation, self).Layout(request,
                                                  response,
                                                  aff4_path=self.cron_job_urn)


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

  action_name = cronjobs.ManageCronJobFlowArgs.Action.NOOP

  inner_dialog_only = True

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
    return self.action_name.name.title() + " cron job"

  def Layout(self, request, response):
    self.check_access_subject = rdfvalue.RDFURN(request.REQ.get("cron_urn"))
    return super(CronJobManagementConfirmationDialog, self).Layout(request,
                                                                   response)

  def RenderAjax(self, request, response):
    cron_urn = rdfvalue.RDFURN(request.REQ.get("cron_urn"))

    flow.GRRFlow.StartFlow(flow_name="ManageCronJobFlow",
                           action=self.action_name,
                           urn=cron_urn,
                           token=request.token)

    return self.RenderFromTemplate(self.ajax_template,
                                   response,
                                   unique=self.unique,
                                   this=self)


class DisableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to disable a cron job."""

  action_name = cronjobs.ManageCronJobFlowArgs.Action.DISABLE


class EnableCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to enable a cron job."""

  action_name = cronjobs.ManageCronJobFlowArgs.Action.ENABLE


class DeleteCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to delete a cron job."""
  action_name = cronjobs.ManageCronJobFlowArgs.Action.DELETE


class ForceRunCronJobConfirmationDialog(CronJobManagementConfirmationDialog):
  """Dialog that asks for confirmation to force a cron job run.

  This action can be run at any time regardless of whether the cronjob is
  enabled or disabled.
  """
  action_name = cronjobs.ManageCronJobFlowArgs.Action.RUN
