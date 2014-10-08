#!/usr/bin/env python
"""Test renderers for angular_components_test.py."""

from grr.gui import renderers


class AngularTestRenderer(renderers.TemplateRenderer):
  """Renderers specified Angular directive with given parameters."""

  angular_template = None
  layout_template = renderers.Template("""
<div id="{{unique|escape}}">{{this.angular_template|safe}}</div>
""")

  def Layout(self, request, response, **kwargs):
    response = super(AngularTestRenderer, self).Layout(
        request, response, **kwargs)
    return self.CallJavascript(response, "AngularDirectiveRenderer.Compile")


class CollectionTableTestRenderer(renderers.AngularTestRenderer):

  angular_template = renderers.Template("""
<grr-collection-table collection-urn="aff4:/tmp/collection" page-size="5">
  <div class="table-cell">{$ item.log_message $}</div>
</grr-collection-table>
""")
