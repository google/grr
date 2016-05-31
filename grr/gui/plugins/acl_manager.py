#!/usr/bin/env python
"""Renderers to implement ACL control workflow."""


from grr.gui import renderers
from grr.gui.api_plugins import user as api_user
from grr.gui.plugins import cron_view
from grr.gui.plugins import fileview
from grr.gui.plugins import hunt_view

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

from grr.lib.aff4_objects import security as aff4_security

from grr.lib.rdfvalues import client as rdf_client


class UnauthorizedRenderer(renderers.TemplateRenderer):
  """Send UnauthorizedAccess Exceptions to the queue."""

  def Layout(self, request, response, exception=None):
    subject = message = ""

    exception = exception or request.REQ.get("e", "")
    if exception:
      subject = str(exception.subject)
      message = str(exception)

    response = super(UnauthorizedRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "UnauthorizedRenderer.Layout",
                               subject=subject,
                               message=message)


class ACLDialog(renderers.TemplateRenderer):
  """Render the ACL dialogbox."""

  layout_template = renderers.Template("""
<div id="acl_dialog" class="modal" tabindex="-1" role="dialog"
  aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal"
          aria-hidden="true">
          x
        </button>
        <h3>Authorization Required</h3>
      </div>
      <div class="modal-body">
        <p class="text-info">The server requires authorization to access this
          resource
        <div id="acl_form"></div>
      </div>
      <div class="modal-footer">
        <button id="acl_dialog_submit" name="Submit" class="btn btn-success">
          Submit</button>
        <button class="btn btn-default" data-dismiss="modal" name="Close"
          aria-hidden="true">
          Close
        </button>
      </div>
    </div>
  </div>
</div>
""")

  def Layout(self, request, response, exception=None):
    response = super(ACLDialog, self).Layout(request, response)
    return self.CallJavascript(response, "ACLDialog.Layout")


def _GetEmailCCAddress(request):
  if request.REQ.get("cc_approval"):
    return config_lib.CONFIG.Get("Email.approval_optional_cc_address")
  else:
    return None


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
    keepalive = bool(request.REQ.get("keepalive"))

    client_id, _ = rdfvalue.RDFURN(subject).Split(2)

    # TODO(user): If something goes wrong here (or in similar renderers below)
    # we should really provide some feedback for the user.
    if approver and reason:
      # Request approval for this client
      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="RequestClientApprovalFlow",
                             reason=reason,
                             approver=approver,
                             token=request.token,
                             email_cc_address=_GetEmailCCAddress(request),
                             subject_urn=rdf_client.ClientURN(client_id))

    if keepalive:
      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="KeepAlive",
                             duration=3600,
                             token=request.token)

    super(ClientApprovalRequestRenderer, self).Layout(request, response)


class HuntApprovalRequestRenderer(renderers.TemplateRenderer):
  """Make a new hunt authorization approval request."""

  layout_template = renderers.Template("""
Hunt Access Request created. Please try again once an approval is granted.
""")

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    subject = rdfvalue.RDFURN(request.REQ.get("subject"))
    reason = request.REQ.get("reason")
    approver = request.REQ.get("approver")

    if approver and reason:
      # Request approval for this hunt
      flow.GRRFlow.StartFlow(flow_name="RequestHuntApprovalFlow",
                             reason=reason,
                             approver=approver,
                             token=request.token,
                             email_cc_address=_GetEmailCCAddress(request),
                             subject_urn=rdfvalue.RDFURN(subject))
    super(HuntApprovalRequestRenderer, self).Layout(request, response)


class CronJobApprovalRequestRenderer(renderers.TemplateRenderer):
  """Make a new cron job authorization approval request."""

  layout_template = renderers.Template("""
Cron Job Access Request created. Please try again once an approval is granted.
""")

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    subject = rdfvalue.RDFURN(request.REQ.get("subject"))
    reason = request.REQ.get("reason")
    approver = request.REQ.get("approver")

    if approver and reason:
      # Request approval for this cron job
      flow.GRRFlow.StartFlow(flow_name="RequestCronJobApprovalFlow",
                             reason=reason,
                             approver=approver,
                             token=request.token,
                             email_cc_address=_GetEmailCCAddress(request),
                             subject_urn=rdfvalue.RDFURN(subject))
    super(CronJobApprovalRequestRenderer, self).Layout(request, response)


class ClientApprovalDetailsRenderer(fileview.AFF4Stats):
  """Renders details of the client approval."""

  # Do not show in the navigation menu.
  behaviours = frozenset([])
  css_class = "TableBody"

  def Layout(self, request, response, client_id=None):
    acl = request.REQ.get("acl", "")
    _, client_id, _ = rdfvalue.RDFURN(acl).Split(3)
    urn = rdf_client.ClientURN(client_id)

    return super(ClientApprovalDetailsRenderer, self).Layout(
        request, response, client_id=client_id,
        aff4_path=urn)


class HuntApprovalDetailsRenderer(hunt_view.HuntOverviewRenderer):
  """Renders details of the hunt approval."""

  def Layout(self, request, response):
    acl = request.REQ.get("acl", "")
    _, _, hunt_id, _ = rdfvalue.RDFURN(acl).Split(4)
    self.hunt_id = aff4.ROOT_URN.Add("hunts").Add(hunt_id)
    return super(HuntApprovalDetailsRenderer, self).Layout(request, response)


class CronJobApprovalDetailsRenderer(cron_view.CronJobInformation):
  """Renders details of the hunt approval."""

  def Layout(self, request, response):
    acl = request.REQ.get("acl", "")
    _, _, cron_job_name, _ = rdfvalue.RDFURN(acl).Split(4)
    self.cron_job_urn = aff4.ROOT_URN.Add("cron").Add(cron_job_name)
    return super(CronJobApprovalDetailsRenderer, self).Layout(request, response)


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
  <button id="{{unique|escape}}_approve" class="{{this.btn_cls|escape}}">
    Approve
  </button>
  {{this.already_approved_text|escape}}
  <h3>{{this.detail_header|escape}}</h3>
  <div id="details_{{unique|escape}}" class="well"></div>
</div>
""")

  ajax_template = renderers.Template("""
You have granted access for {{this.subject|escape}} to {{this.user|escape}}
""")

  detail_header = "Details"

  def Layout(self, request, response):
    """Launch the RequestApproval flow on the backend."""
    self.acl = request.REQ.get("acl")

    source = request.REQ.get("source")

    if self.acl is None and source != "hash":
      # NOTE: we have to pass id explicitly because super().Layout() wasn't
      # called yet, and therefore self.id is None.
      return self.CallJavascript(response,
                                 "GrantAccess.RefreshFromHash",
                                 renderer=self.__class__.__name__,
                                 id=request.REQ.get("id", hash(self)))

    # There is a bug in Firefox that strips trailing "="s from get parameters
    # which is a problem with the base64 padding. To pass the selenium tests,
    # we have to restore the original string.
    while len(self.acl.split("/")[-1]) % 4 != 0:
      self.acl += "="

    # TODO(user): This makes assumptions about the approval URL.
    approval_urn = rdfvalue.RDFURN(self.acl or "/")
    components = approval_urn.Split()
    username = components[-2]
    namespace = components[1]

    _, namespace, _ = approval_urn.Split(3)
    if namespace == "hunts":
      self.details_renderer = "HuntApprovalDetailsRenderer"
      self.user = components[3]
      self.detail_header = "Hunt Information"
    elif namespace == "cron":
      self.details_renderer = "CronJobApprovalDetailsRenderer"
      self.user = components[3]
      self.detail_header = "Cronjob Information"
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      self.details_renderer = "ClientApprovalDetailsRenderer"
      self.user = components[2]
      self.detail_header = "Client Information"
    else:
      raise access_control.UnauthorizedAccess(
          "Approval object is not well formed.")

    approval_request = aff4.FACTORY.Open(approval_urn,
                                         mode="r",
                                         age=aff4.ALL_TIMES,
                                         token=request.token)
    self.user = username
    self.reason = approval_request.Get(approval_request.Schema.REASON)

    user_token = access_control.ACLToken(username=self.user, reason=self.reason)
    self.already_approved_text = ""
    self.btn_cls = "btn btn-success"
    try:
      if approval_request.CheckAccess(user_token):
        self.already_approved_text = "This approval has already been granted!"
        self.btn_cls = "btn btn-warning"
    except access_control.UnauthorizedAccess:
      pass

    response = renderers.TemplateRenderer.Layout(self, request, response)
    return self.CallJavascript(response,
                               "GrantAccess.Layout",
                               renderer=self.__class__.__name__,
                               acl=self.acl,
                               details_renderer=self.details_renderer)

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
        raise access_control.UnauthorizedAccess(
            "Approval object is not well formed.")

      flow.GRRFlow.StartFlow(flow_name="GrantHuntApprovalFlow",
                             subject_urn=self.subject,
                             reason=self.reason,
                             delegate=self.user,
                             token=request.token)
    elif namespace == "cron":
      try:
        _, _, cron_job_name, user, reason = approval_urn.Split()
        self.subject = rdfvalue.RDFURN(namespace).Add(cron_job_name)
        self.user = user
        self.reason = utils.DecodeReasonString(reason)
      except (ValueError, TypeError):
        raise access_control.UnauthorizedAccess(
            "Approval object is not well formed.")

      flow.GRRFlow.StartFlow(flow_name="GrantCronJobApprovalFlow",
                             subject_urn=self.subject,
                             reason=self.reason,
                             delegate=self.user,
                             token=request.token)
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      try:
        _, client_id, user, reason = approval_urn.Split()
        self.subject = client_id
        self.user = user
        self.reason = utils.DecodeReasonString(reason)
      except (ValueError, TypeError):
        raise access_control.UnauthorizedAccess(
            "Approval object is not well formed.")

      flow.GRRFlow.StartFlow(client_id=client_id,
                             flow_name="GrantClientApprovalFlow",
                             reason=self.reason,
                             delegate=self.user,
                             subject_urn=rdf_client.ClientURN(self.subject),
                             token=request.token)
    else:
      raise access_control.UnauthorizedAccess(
          "Approval object is not well formed.")

    return renderers.TemplateRenderer.Layout(self,
                                             request,
                                             response,
                                             apply_template=self.ajax_template)


class CheckAccess(renderers.TemplateRenderer):
  """Check the level of access the user has for a specified client."""

  show_keepalive_option = False

  # Allow the user to request access to the client.
  layout_template = renderers.Template("""
{% if this.error %}
<p class="text-info">Existing authorization request
  {% if this.reason %}(reason: <em>{{this.reason|escape}}</em>){% endif %}
  failed:</p>
<blockquote>
{{this.error|escape}}
</blockquote>
{% endif %}
<h3>Create a new approval request.</h3>
<form id="acl_form_{{unique|escape}}" class="form-horizontal acl-form">
  <div class="form-group">
    <label class="control-label" for="acl_approver">Approvers</label>
    <div class="controls">
      <input type="text" id="acl_approver" class="form-control"
        placeholder="approver1,approver2,approver3" />
    </div>
  </div>
  {% if this.cc_address %}
  <div class="form-group">
    <div class="controls">
      <input id="acl_cc_approval" type=checkbox class="unset"
       name="cc_approval" value="yesplease" class="form-control" checked />
      <label for="acl_cc_approval">CC {{this.cc_address|escape}}</label>
    </div>
  </div>
  {% endif %}
  <div class="form-group">
    <label class="control-label" for="acl_recent_reasons">Reason</label>
    <div class="controls">
      <select id="acl_recent_reasons" class="form-control">
        <option value="new_reason">Enter New Reason...</option>
        {% for recent_reason in this.recent_reasons %}
          <option value="{{recent_reason|escape}}">{{recent_reason|escape}}</option>
        {% endfor %}
      </select>
    </div>
  </div>
  <div class="form-group">
    <label class="control-label" for="acl_reason"></label>
    <div class="controls">
      <input type="text" id="acl_reason" class="form-control" />
    </div>
  </div>
  <div id="acl_reason_warning" class="alert alert-danger hide">
    Please enter the reason.
  </div>
  {% if this.show_keepalive_option %}
  <div class="form-group">
    <div class="controls">
      <input id="acl_keepalive" type=checkbox class="unset"
       name="keepalive" value="yesplease" class="form-control" />
      <label for="acl_keepalive">Keep this client alive as soon as it comes online.</label>
    </div>
  </div>
  {% endif %}
</form>
""")

  silent_template = renderers.Template("""
{% if this.error %}
Authorization request ({{this.reason|escape}}) failed:
<p>
{{this.error|escape}}
</p>
{% endif %}
""")

  def CheckObjectAccess(self, object_urn, token):
    """Check if the user has access to the specified hunt."""
    try:
      approved_token = aff4_security.Approval.GetApprovalForObject(object_urn,
                                                                   token=token)
    except access_control.UnauthorizedAccess as e:
      self.error = e
      approved_token = None

    if approved_token:
      self.reason = approved_token.reason
      return True
    else:
      return False

  def Layout(self, request, response):
    """Checks the level of access the user has to this client."""
    self.subject = request.REQ.get("subject", "")
    self.silent = request.REQ.get("silent", "")

    token = request.token

    # When silent=True, we don't show ACLDialog in case of failure.
    # This is useful when we just want to make an access check and set
    # the correct reason (if found) without asking for a missing approval.
    if self.silent:
      self.layout_template = self.silent_template

    self.refresh_after_form_submit = True

    subject_urn = rdfvalue.RDFURN(self.subject)
    namespace, _ = subject_urn.Split(2)
    if self.CheckObjectAccess(subject_urn, token):
      return self.CallJavascript(response,
                                 "CheckAccess.AccessOk",
                                 reason=self.reason,
                                 silent=self.silent)

    self.cc_address = config_lib.CONFIG["Email.approval_optional_cc_address"]

    recent_reasons_list = api_user.ApiListUserClientApprovalsHandler().Handle(
        api_user.ApiListUserClientApprovalsArgs(count=5),
        token=request.token)
    self.recent_reasons = [x.reason for x in recent_reasons_list.items]

    if namespace == "hunts":
      self.approval_renderer = "HuntApprovalRequestRenderer"
      self.refresh_after_form_submit = False
    elif namespace == "cron":
      self.approval_renderer = "CronJobApprovalRequestRenderer"
      self.refresh_after_form_submit = False
    elif aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(namespace):
      self.approval_renderer = "ClientApprovalRequestRenderer"
      self.show_keepalive_option = True
    else:
      raise RuntimeError(
          "Unexpected namespace for access check: %s (subject=%s)." %
          (namespace, self.subject))

    response = super(CheckAccess, self).Layout(request, response)
    if not self.silent:
      return self.CallJavascript(
          response,
          "CheckAccess.Layout",
          subject=self.subject,
          refresh_after_form_submit=self.refresh_after_form_submit,
          approval_renderer=self.approval_renderer)
    else:
      return response
