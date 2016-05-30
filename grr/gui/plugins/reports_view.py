#!/usr/bin/env python
"""This plugin adds reporting functionality."""

from grr.gui.plugins import forms
from grr.lib.aff4_objects import reports


class ReportNameRenderer(forms.StringTypeFormRenderer):
  """Renderer for listing the available reports."""

  type_descriptor = reports.ReportName
  default = "ClientListReport"

  layout_template = ("""<div class="form-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <select id='{{this.prefix}}' onchange="grr.forms.inputOnChange(this)"
    class="unset">
      {% for report_name in this.reports %}
        <option {% ifequal report_name this.default %}selected{% endifequal %}
        value='{{report_name|escape}}'>{{report_name|escape}}</option>
      {% endfor %}
    </select>
  </div>
</div>
""")

  def Layout(self, request, response):
    self.reports = [r.__name__ for r in reports.Report.class_list
                    if r is not reports.Report.top_level_class]
    response = super(ReportNameRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "ReportNameRenderer.Layout",
                               prefix=self.prefix)
