#!/usr/bin/env python
"""Renderers to implement ACL control workflow."""


from grr.gui import renderers


# TODO(user): Remove as soon as code in ACLDialog javascript renderer
# is migrated.
class ACLDialog(renderers.TemplateRenderer):
  """Legacy ACLDialog renderer."""

  layout_template = renderers.Template("""
<div id="acl_dialog"></div>
""")

  def Layout(self, request, response, exception=None):
    response = super(ACLDialog, self).Layout(request, response)
    return self.CallJavascript(response, "ACLDialog.Layout")
