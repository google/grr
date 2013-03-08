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
from grr.gui.plugins import hunt_view

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils


class ACLDialog(renderers.TemplateRenderer):
  """Render the ACL dialogbox."""

  layout_template = renderers.Template("""
<div id="acl_dialog" class="modal hide fade" tabindex="-1" role="dialog"
  aria-hidden="true">

  <div class="modal-header">
    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">
      x
    </button>
    <h3>Authorization Required</h3>
  </div>
  <div class="modal-body">
    <p class="text-info">The server requires authorization to access this
      resource.</p>
    <blockquote id="acl_server_message"></blockquote>
    <div id="acl_form"></div>
  </div>
  <div class="modal-footer">
    <button id="acl_dialog_submit" name="Submit" class="btn btn-success">
      Submit</button>
    <button class="btn" data-dismiss="modal" name="Close" aria-hidden="true">
      Close</button>
  </div>

</div>

<script>
$("#acl_dialog_submit").click(function (event) {
  $("#acl_form form").submit();
});

grr.subscribe("unauthorized", function(subject, message) {
  $("#acl_server_message").text(message);
  grr.layout("CheckAccess", "acl_form", {subject: subject});
}, "acl_dialog");

</script>
""")


class ClientApprovalRequestRenderer(renderers.TemplateRenderer):
  """Make a new client authorization approval request."""

  layout_template = renderers.Template("""
Client Access Request created. Please try again once an approval is granted.
""")

  def Layout(self, request, response):
    """Launch the RequestClientApproval flow on the backend."""
    subject = request.REQ.get("subject")
    reason = request.REQ.get("reason")
    approver = request.REQ.get("approver")

    client_id, _ = rdfvalue.RDFURN(subject).Split(2)

    if approver and reason:
      # Request approval for this client
      flow.FACTORY.StartFlow(client_id, "RequestClientApprovalFlow",
                             reason=reason, approver=approver,
                             token=request.token)

    super(ClientApprovalRequestRenderer, self).Layout(request, response)


class HuntApprovalRequestRenderer(renderers.TemplateRenderer):
  """Make a new hunt authorization approval request."""

  layout_template = renderers.Template("""
Hunt Access Request created. Please try again once an approval is granted.
""")

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    subject = request.REQ.get("subject")
    reason = request.REQ.get("reason")
    approver = request.REQ.get("approver")

    _, hunt_id, _ = rdfvalue.RDFURN(subject).Split(3)

    if approver and reason:
      # Request approval for this client
      flow.FACTORY.StartFlow(None, "RequestHuntApprovalFlow",
                             reason=reason, approver=approver,
                             token=request.token,
                             hunt_id=hunt_id)

    super(HuntApprovalRequestRenderer, self).Layout(request, response)


class ClientApprovalDetailsRenderer(fileview.HostInformation):
  """Renders details of the client approval."""

  # Do not show in the navigation menu.
  behaviours = frozenset([])

  def Layout(self, request, response):
    acl = request.REQ.get("acl", "")
    _, client_id, _ = rdfvalue.RDFURN(acl).Split(3)

    # We skip the direct super class to avoid the access control check.
    super(fileview.HostInformation, self).Layout(
        request, response, client_id=client_id,
        aff4_path=rdfvalue.RDFURN(client_id))


class HuntApprovalDetailsRenderer(hunt_view.HuntOverviewRenderer):
  """Renders details of the hunt approval."""

  def Layout(self, request, response):
    acl = request.REQ.get("acl", "")
    _, _, hunt_id, _ = rdfvalue.RDFURN(acl).Split(4)
    self.hunt_id = aff4.ROOT_URN.Add("hunts").Add(hunt_id)
    return super(HuntApprovalDetailsRenderer, self).Layout(request, response)


class GrantAccess(fileview.HostInformation):
  """Grant Access to a user.

  Post Parameters:
    - acl: The aff4 urn of the ACL we should be granting.
  """
  # Do not show in the navigation menu.
  behaviours = frozenset([])

  layout_template = renderers.Template("""
<div id="{{unique|escape}}_container" class="fill-parent">
  <h2> Grant Access for GRR Use.</h2>

  <p>The user <strong>{{this.user|escape}}</strong> has requested you to grant
    them access based on:</p>
  <blockquote>
    {{this.reason|escape}}
  </blockquote>
  <p>Details:</p>
  <div id="details_{{unique|escape}}" class="well"></div>

  <button id="{{unique|escape}}_approve" class="btn btn-success">
    Approve
  </button>
</div>

<script>
  $("#{{unique|escapejs}}_approve").click(function () {
    grr.update("{{renderer|escapejs}}", "{{unique|escapejs}}_container", {
      acl: "{{this.acl|escapejs}}",
    });
  });
  grr.layout("{{this.details_renderer|escapejs}}",
    "details_{{unique|escapejs}}",
    { acl: "{{this.acl|escapejs}}" });
</script>
""")

  ajax_template = renderers.Template("""
You have granted access for {{this.subject|escape}} to {{this.user|escape}}
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

    # There is a bug in Firefox that strips trailing "="s from get parameters
    # which is a problem with the base64 padding. To pass the selenium tests,
    # we have to restore the original string.
    while len(self.acl.split("/")[-1]) % 4 != 0:
      self.acl += "="

    # TODO(user): This makes assumptions about the approval URL.
    approval_urn = rdfvalue.RDFURN(self.acl or "/")
    _, namespace, _ = approval_urn.Split(3)

    if namespace == "hunts":
      self.details_renderer = "HuntApprovalDetailsRenderer"
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      self.details_renderer = "ClientApprovalDetailsRenderer"
    else:
      raise access_control.UnauthorizedAccess(
          "Approval object is not well formed.")

    approval_request = aff4.FACTORY.Open(approval_urn, mode="r",
                                         token=request.token)

    self.user = request.token.username
    self.reason = approval_request.Get(approval_request.Schema.REASON)
    return renderers.TemplateRenderer.Layout(self, request, response)

  def RenderAjax(self, request, response):
    """Run the flow for granting access."""
    approval_urn = rdfvalue.RDFURN(request.REQ.get("acl", "/"))
    _, namespace, _ = approval_urn.Split(3)

    if namespace == "hunts":
      try:
        _, _, hunt_id, user, reason = approval_urn.Split()
        self.subject = rdfvalue.RDFURN(namespace).Add(hunt_id)
        self.user = user
        self.reason = utils.DecodeReasonString(reason)
      except (ValueError, TypeError):
        raise data_store.UnauthorizedAccess(
            "Approval object is not well formed.")

      flow.FACTORY.StartFlow(None, "GrantHuntApprovalFlow",
                             hunt_urn=self.subject, reason=self.reason,
                             delegate=self.user, token=request.token)

    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      try:
        _, client_id, user, reason = approval_urn.Split()
        self.subject = client_id
        self.user = user
        self.reason = utils.DecodeReasonString(reason)
      except (ValueError, TypeError):
        raise access_control.UnauthorizedAccess(
            "Approval object is not well formed.")

      flow.FACTORY.StartFlow(client_id, "GrantClientApprovalFlow",
                             reason=self.reason, delegate=self.user,
                             token=request.token)
    else:
      raise access_control.UnauthorizedAccess(
          "Approval object is not well formed.")

    return renderers.TemplateRenderer.Layout(self, request, response,
                                             apply_template=self.ajax_template)


class CheckAccess(renderers.TemplateRenderer):
  """Check the level of access the user has for a specified client."""

  # Allow the user to request access to the client.
  layout_template = renderers.Template("""
{% if this.error %}
<p class="text-info">Existing authorization request ({{this.reason|escape}})
  failed:</p>
<blockquote>
{{this.error|escape}}
</blockquote>
{% endif %}
<h3>Create a new approval request.</h3>
<form id="acl_form_{{unique|escape}}" class="form-horizontal acl-form">
  <div class="control-group">
    <label class="control-label" for="acl_approver">Approvers</label>
    <div class="controls">
      <input type="text" id="acl_approver"
        placeholder="approver1,approver2,approver3" />
    </div>
  </div>
  <div class="control-group">
    <label class="control-label" for="acl_reason">Reason</label>
    <div class="controls">
      <input type=text id="acl_reason" />
    </div>
  </div>
</form>

<script>
(function() {

$("#acl_form_{{unique|escapejs}}").submit(function (event) {
  var state = {
    subject: "{{this.subject|escapejs}}",
    approver: $("#acl_approver").val(),
    reason: $("#acl_reason").val()
  };

  // When we complete the request refresh to the main screen.
  grr.layout("{{this.approval_renderer|escapejs}}", "acl_server_message", state,
    function () {
      window.location = "/";
    });

  event.preventDefault();
});

if ($("#acl_dialog[aria-hidden=false]").size() == 0) {

$("#acl_dialog").detach().appendTo('body');

// TODO(mbushkov): cleanup a bit. We use update_on_show attribute in
// LaunchHunts wizard to avoid reloading the modal when it's hidden and shown
// again because ACL dialog interrupted the UI flow.
var openedModal = $(".modal[aria-hidden=false]");
openedModal.attr("update_on_show", "false");
openedModal.modal("hide");

var returnModalHandler = function () {
  if (openedModal.attr("restore_after_acl") != "false") {
    openedModal.modal("show");
  }
  $("#acl_dialog").off("hidden", returnModalHandler);
};
$("#acl_dialog").on("hidden", returnModalHandler);

// Allow the user to request access through the dialog.
$("#acl_dialog").modal('toggle');
}

})();
</script>
""")

  silent_template = renderers.Template("""
{% if this.error %}
Authorization request ({{this.reason|escape}}) failed:
<p>
{{this.error|escape}}
</p>
{% endif %}
""")

  # This will be shown when the user already has access.
  access_ok_template = renderers.Template("""
<script>
  grr.publish("hash_state", "reason", "{{this.reason|escapejs}}");
  grr.state.reason = "{{this.reason|escapejs}}";
  {% if not this.silent %}
    grr.publish("client_selection", grr.state.client_id);
  {% endif %}
</script>
""")

  def CheckObjectAccess(self, namespace, object_name, token):
    """Check if the user has access to the specified hunt."""
    try:
      approved_token = aff4.Approval.GetApprovalForObject(
          namespace, object_name, token=token)
    except access_control.UnauthorizedAccess as e:
      self.error = e
      approved_token = None

    if approved_token:
      self.reason = approved_token.reason
      self.layout_template = self.access_ok_template

  def Layout(self, request, response):
    """Checks the level of access the user has to this client."""
    self.subject = request.REQ.get("subject", "")
    self.silent = request.REQ.get("silent", "")
    namespace, path_part, _ = rdfvalue.RDFURN(self.subject).Split(3)

    token = request.token

    # When silent=True, we don't show ACLDialog in case of failure.
    # This is useful when we just want to make an access check and set
    # the correct reason (if found) without asking for a missing approval.
    if self.silent:
      self.layout_template = self.silent_template

    if namespace == "hunts":
      self.approval_renderer = "HuntApprovalRequestRenderer"
      self.CheckObjectAccess(namespace, path_part, token)
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      self.CheckObjectAccess("clients", namespace, token)
      self.approval_renderer = "ClientApprovalRequestRenderer"
    else:
      raise RuntimeError("Unexpected namespace for access check: %s." %
                         namespace)

    return super(CheckAccess, self).Layout(request, response)
