#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2012 Google Inc. All Rights Reserved.

"""This is the interface for managing cron jobs."""


from grr.gui import renderers
from grr.gui.plugins import flow_management

from grr.lib import aff4
from grr.lib import cron


class ManageCron(renderers.Splitter2Way):
  """Manages Cron jobs."""
  description = "Cron Job Viewer"
  behaviours = frozenset(["General"])
  top_renderer = "CronTable"
  bottom_renderer = "CronJobView"

  layout_template = renderers.Splitter2Way.layout_template + """
<script>
grr.subscribe("cron_select", function(cron_urn) {
  grr.layout("CronJobView", "{{id|escapejs}}_bottomPane", {value: cron_urn});
}, "{{id|escapejs}}_bottomPane");
</script>
"""


class CronTable(renderers.TableRenderer):
  """Show all existing rules."""
  selection_publish_queue = "cron_select"

  layout_template = renderers.TableRenderer.layout_template + """
<script>
  //Receive the selection event and emit the detail.
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var cron_urn = $(node).find("span[aff4_path]").attr("aff4_path");
      grr.publish("cron_select", cron_urn);
    };
  }, '{{ unique|escapejs }}');

</script>
"""

  def __init__(self, **kwargs):
    super(CronTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Name", width="10%", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Last Run", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Frequency", width="10%"))
    self.AddColumn(renderers.RDFValueColumn("Description", width="70%"))

  def RenderAjax(self, request, response):
    """Renders the table."""
    cron_jobs_urns = cron.CRON_MANAGER.ListJobs(token=request.token)
    cron_jobs = aff4.FACTORY.MultiOpen(
        cron_jobs_urns, mode="r", aff4_type="CronJob", token=request.token)
    for cron_job in cron_jobs:
      self.AddRow({"Name": cron_job.urn,
                   "Last Run": cron_job.Get(cron_job.Schema.LAST_RUN_TIME),
                   "Frequency": cron_job.Get(cron_job.Schema.FREQUENCY),
                   "Description": cron_job.Get(cron_job.Schema.DESCRIPTION)})

    # Call our baseclass to actually do the rendering
    return super(CronTable, self).RenderAjax(request, response)


class CronJobView(flow_management.ManageFlows):
  """Render a customized form for a foreman action."""

  # Don't show the link to this view in the sidebar,
  behaviours = frozenset()

  empty_template = renderers.Template("""
<div class="padded">Please select a cron job to see the details.</div>
""")

  def Layout(self, request, response):
    if not request.REQ.get("value"):
      return self.RenderFromTemplate(self.empty_template, response)
    else:
      super(CronJobView, self).Layout(request, response)
