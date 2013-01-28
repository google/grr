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


"""This is the interface for managing cron jobs."""


import logging

from grr.gui import renderers
from grr.lib import aff4
from grr.lib import data_store
from grr.lib.aff4_objects import cronjobs


class ManageCron(renderers.Splitter2Way):
  """Manages Cron jobs."""
  description = "Cron Job Viewer"
  behaviours = frozenset(["General"])
  top_renderer = "CronTable"
  bottom_renderer = "ViewCronDetail"


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
        "Name", width=10, renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.RDFValueColumn("Last Run", width=10))
    self.AddColumn(renderers.RDFValueColumn("Frequency", width=10))
    self.AddColumn(renderers.RDFValueColumn("Description", width=60))

  def RenderAjax(self, request, response):
    """Renders the table."""
    for cls_name, cls in aff4.AFF4Object.classes.iteritems():
      if (issubclass(cls, cronjobs.AbstractScheduledCronJob) or
          issubclass(cls, cronjobs.AbstractCronTask)):
        try:
          fd = aff4.FACTORY.Open("cron:/%s" % cls_name, required_type=cls_name,
                                 mode="r", token=request.token)
          last_run_time = fd.Get(fd.Schema.LAST_RUN_TIME)

          self.AddRow({"Name": fd.urn,
                       "Last Run": last_run_time,
                       "Frequency": "%sH" % int(fd.frequency),
                       "Description": cls.__doc__})
        except IOError:
          logging.error("Bad cron %s", cls)
        except data_store.UnauthorizedAccess:
          pass

    # Call our baseclass to actually do the rendering
    return super(CronTable, self).RenderAjax(request, response)


class ViewCronDetail(renderers.TemplateRenderer):
  """Render a customized form for a foreman action."""

  layout_template = renderers.Template("""
<div id="{{unique}}">
  <h3>Cron Log</h3>
  <table class="proto_table">
  {% for val in this.log %}
    <tr><td class="proto_key">{{ val.age }}</td><td>{{ val|escape }}</td>
  {% empty %}
    <tr><td>No logs</td></tr>
  {% endfor %}
  <table>
</div>
<script>
grr.subscribe("cron_select", function(cron_urn) {
  $("#{{unique|escapejs}}").html("<em>Loading&#8230;</em>");
  grr.layout("ViewCronDetail", "{{unique|escapejs}}", {cron_urn: cron_urn});
}, "{{unique}}");
</script>
""")

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    cron_urn = request.REQ.get("cron_urn")
    if cron_urn:
      fd = aff4.FACTORY.Open(cron_urn, token=request.token,
                             age=aff4.ALL_TIMES)
      self.log = fd.GetValuesForAttribute(fd.Schema.LOG)
    return super(ViewCronDetail, self).Layout(request, response)
