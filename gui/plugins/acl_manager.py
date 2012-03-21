#!/usr/bin/env python

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

"""Renderers to implement ACL control workflow."""


from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow


class ACLDialog(renderers.TemplateRenderer):
  """Render the ACL dialogbox."""

  layout_template = renderers.Template("""
<div id="acl_dialog" title="Authorization Required">
 <h1>Authorization Required</h1>

 The server requires authorization to access this resource.
 <div id="acl_server_message"></div>
 <div id="acl_form"></div>
</div>

<script>
$( "#acl_dialog" ).dialog({
  modal: true
}).dialog('close');

grr.subscribe("unauthorized", function(subject, message) {
 $("#acl_server_message").text(message);
 grr.layout("CheckAccess", "acl_form", grr.state);
}, "acl_dialog");

</script>
""")


class ApprovalRequestRenderer(renderers.TemplateRenderer):
  """Make a new approval request."""

  layout_template = renderers.Template("""
Access Request created. Please try again once an approval is granted.
""")

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    client_id = request.REQ.get("client_id")
    reason = request.REQ.get("reason")
    approver = request.REQ.get("approver")

    if approver and reason:
      # Request approval for this client
      flow.FACTORY.StartFlow(client_id, "RequestApproval", reason=reason,
                             approver=approver, token=request.token)

    super(ApprovalRequestRenderer, self).Layout(request, response)


class GrantAccess(fileview.HostInformation):
  """Grant Access to a user.

  Post Parameters:
    - acl: The aff4 urn of the ACL we should be granting.
  """
  # Do not show in the navigation menu.
  behaviours = frozenset([])

  layout_template = renderers.Template("""
<div id="{{unique|escape}}_container" class="TableBody">
 <h1> Grant Access for GRR Use.</h1>

 The user {{this.user|escape}} has requested you to grant them access based on:
 <div class="proto_value">
  {{this.reason|escape}}
 </div>

<button id="{{unique|escape}}_approve" class="grr-button grr-button-red">
  Approve
</button>
<p>
You are about to grant access to the following machine:

<div>""") + fileview.AFF4Stats.layout_template + """</div>
</div>
<script>
  $("#{{unique|escapejs}}_approve").click(function () {
    grr.update("{{renderer|escapejs}}", "{{unique|escapejs}}_container", {
      acl: "{{this.acl|escapejs}}",
    });
  });
</script>
"""

  ajax_template = renderers.Template("""
You have granted access for {{this.client_id|escape}} to {{this.user|escape}}
""")

  refresh_from_hash_template = renderers.Template("""
<script>
  var state = grr.parseHashState();
  state.source = 'hash';
  grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", state);
</script>
""")

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    self.acl = request.REQ.get("acl")
    source = request.REQ.get("source")

    if self.acl is None and source != "hash":
      return renderers.TemplateRenderer.Layout(
          self, request, response,
          apply_template=self.refresh_from_hash_template)

    approval_urn = aff4.RDFURN(self.acl or "/")
    try:
      _, self.client_id, self.user, _ = approval_urn.Split()
    except ValueError:
      raise data_store.UnauthorizedAccess("Approval object is not well formed.")

    approval_request = aff4.FACTORY.Open(approval_urn, mode="r",
                                         token=request.token)

    self.reason = approval_request.Get(approval_request.Schema.REASON)
    self.fd = aff4.FACTORY.Open(self.client_id, token=request.token,
                                age=aff4.ALL_TIMES)
    self.classes = self.RenderAFF4Attributes(self.fd, request)
    self.path = self.client_id

    return renderers.TemplateRenderer.Layout(self, request, response)

  def RenderAjax(self, request, response):
    """Run the flow for granting access."""
    approval_urn = aff4.RDFURN(request.REQ.get("acl", "/"))
    try:
      _, self.client_id, self.user, self.reason = approval_urn.Split()
    except ValueError:
      raise data_store.UnauthorizedAccess("Approval object is not well formed.")

    flow.FACTORY.StartFlow(self.client_id, "GrantAccessFlow",
                           reason=self.reason, delegate=self.user,
                           token=request.token)

    return renderers.TemplateRenderer.Layout(self, request, response,
                                             apply_template=self.ajax_template)


class CheckAccess(renderers.TemplateRenderer):
  """Check the level of access the user has for a specified client."""

  # Allow the user to request access to the client.
  layout_template = renderers.Template("""
{% if this.error %}
Existing authorization request ({{this.reason|escape}}) failed:
<p>
{{this.error|escape}}
<p>
{% endif %}
<h3>Create a new approval request.</h3>
<form id="acl_form_{{unique|escape}}" class="acl_form">
 <table>
  <tr>
   <td>
    Approvers (comma separated)</td><td><input type=text id="acl_approver" />
   </td>
  </tr>
  <tr>
   <td>Reason</td><td><input type=text id="acl_reason" /></td>
  </tr>
 </table>
 <input type=submit>
</form>

<script>
$("#acl_form_{{unique|escapejs}}").submit(function (event) {
  var state = {
    client_id: grr.state.client_id,
    approver: $("#acl_approver").val(),
    reason: $("#acl_reason").val()
  };

  // When we complete the request refresh to the main screen.
  grr.layout("ApprovalRequestRenderer", "acl_server_message", state,
    function () {
      window.location = "/";
    });

  event.preventDefault();
});

// Allow the user to request access through the dialog.
$("#acl_dialog").dialog('open');
</script>
""")

  # This will be shown when the user already has access.
  access_ok_template = renderers.Template("""
<script>
  grr.publish("hash_state", "reason", "{{this.reason|escapejs}}");
  grr.state.reason = "{{this.reason|escapejs}}";
  grr.publish("client_selection", grr.state.client_id);
</script>
""")

  def Layout(self, request, response):
    """Checks the level of access the user has to this client."""
    client_id = request.REQ.get("client_id", "")
    token = request.token
    username = token.username

    # Now we try to find any reason which will allow the user to access this
    # client right now.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        username)

    fd = aff4.FACTORY.Open(approval_urn, mode="r", token=token)
    for auth_request in fd.OpenChildren():
      reason = auth_request.urn.Basename()
      # Check authorization using the data_store for an authoritative source.
      test_token = data_store.ACLToken(username, reason)
      try:
        fd = aff4.FACTORY.Open(aff4.RDFURN(client_id).Add("acl_check"),
                               mode="r", token=test_token)
        self.reason = reason
        # User is authorized.
        self.layout_template = self.access_ok_template
      except data_store.UnauthorizedAccess, e:
        self.error = str(e)

    return super(CheckAccess, self).Layout(request, response)
