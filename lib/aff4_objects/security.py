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

"""AFF4 Objects to enforce ACL policies."""

import urllib

from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import utils


flags.DEFINE_integer("acl_approvers_required", 2,
                     "The number of approvers required for access.")
flags.DEFINE_string("ui_url", "http://localhost:8000/",
                    "The direct URL for the user interface.")

flags.DEFINE_string("grr_emergency_email_address",
                    "emergency@nowhere.com",
                    "The email address to notify in an emergency.")

FLAGS = flags.FLAGS


class Approval(aff4.AFF4Object):
  """An approval request for access to a specific client.

  This object normally lives within the namespace:
  aff4:/ACL/client_id/user/<utils.EncodeReasonString(reason)>

  Hence the client_id and user which is granted access are inferred from this
  object's URN.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object:

   - RequestApproval()
   - GrantAccess()
  """

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """The Schema for the Approval class."""
    APPROVER = aff4.Attribute("aff4:approval/approver", aff4.RDFString,
                              "An approver for the request.", "approver")

    REASON = aff4.Attribute("aff4:approval/reason", aff4.RDFString,
                            "The reason for requesting access to this client.")

    LIFETIME = aff4.Attribute(
        "aff4:approval/lifetime", aff4.RDFInteger,
        "The number of microseconds an approval is valid for.",
        default=4 * 7 * 24 * 60 * 60 * 1000000)  # 4 weeks

    BREAK_GLASS = aff4.Attribute(
        "aff4:approval/breakglass", aff4.RDFDatetime,
        "The date when this break glass approval will expire.")

  def CheckAccess(self, token):
    """Enforce a dual approver policy for access."""
    namespace, client_id, user, _ = self.urn.Split(4)
    if namespace != "ACL":
      raise data_store.UnauthorizedAccess(
          "Approval object has invalid urn %s.", self.urn,
          requested_access=token.requested_access)

    if user != token.username:
      raise data_store.UnauthorizedAccess(
          "Approval object is not for user %s." % token.username,
          requested_access=token.requested_access)

    # This approval can only apply for a client.
    if not self.classes["VFSGRRClient"].CLIENT_ID_RE.match(client_id):
      raise data_store.UnauthorizedAccess(
          "Approval can only be granted on clients, not %s" % client_id,
          requested_access=token.requested_access)

    now = aff4.RDFDatetime()

    # Is this an emergency access?
    break_glass = self.Get(self.Schema.BREAK_GLASS)
    if break_glass and now < break_glass:
      # This tags the token as an emergency token.
      token.is_emergency = True
      return True

    # Check that there are enough approvers.
    lifetime = self.Get(self.Schema.LIFETIME)
    approvers = set()
    for approver in self.GetValuesForAttribute(self.Schema.APPROVER):
      if approver.age + lifetime > now:
        approvers.add(utils.SmartStr(approver))

    if len(approvers) < FLAGS.acl_approvers_required:
      raise data_store.UnauthorizedAccess(
          "Requires %s approvers for access." % FLAGS.acl_approvers_required,
          requested_access=token.requested_access)

    return True


class RequestApproval(flow.GRRFlow):
  """A flow to request approval to access a client."""

  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  def __init__(self, reason="Unspecified", approver="", **kwargs):
    self.reason = reason
    self.approver = approver
    super(RequestApproval, self).__init__(**kwargs)

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # Make a supervisor token
    token = data_store.ACLToken()
    token.supervisor = True

    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id).Add(
        self.token.username).Add(utils.EncodeReasonString(self.reason))

    approval_request = aff4.FACTORY.Create(approval_urn, "Approval",
                                           mode="rw", token=token)
    approval_request.Set(approval_request.Schema.REASON(self.reason))

    # We add ourselves as an approver as well (The requirement is that we have 2
    # approvers, so the requester is automatically an approver).
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))

    approval_request.Close()

    # Notify to the users.
    for user in self.approver.split(","):
      user = user.strip()
      fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(user),
                               "GRRUser", mode="rw", token=token)

      fd.Notify("GrantAccess", approval_urn, "Please grant access to a machine",
                self.session_id)
      fd.Close()

      template = """
<html><body><h1>GRR machine access requested.</h1>

The user "%(username)s" has requested access to a GRR machine "%(hostname)s"
for the purpose of "%(reason)s".

Please click <a href='%(admin_ui)s#%(approval_urn)s'>
  here
</a> to review this host and then grant access.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

      client = aff4.FACTORY.Open(self.client_id, token=self.token)
      hostname = client.Get(client.Schema.HOSTNAME)

      url = urllib.urlencode((("acl", str(approval_urn)),
                              ("main", "GrantAccess")))

      email_alerts.SendEmail(user, self.token.username,
                             "Please grant %s access." % self.token.username,
                             template % dict(
                                 username=self.token.username,
                                 hostname=hostname,
                                 reason=utils.SmartStr(self.reason),
                                 admin_ui=FLAGS.ui_url,
                                 approval_urn=url),
                             is_html=True)


class GrantAccessFlow(flow.GRRFlow):
  """Grant the approval requested."""
    # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  def __init__(self, reason="Unspecified", delegate="", **kwargs):
    self.reason = reason
    self.delegate = delegate
    super(GrantAccessFlow, self).__init__(**kwargs)

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # TODO(user): Right now anyone can approve anything. We may want to
    # refine this policy in future.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id).Add(
        self.delegate).Add(utils.EncodeReasonString(self.reason))

    # This object must already exist.
    approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                         token=self.token)
    if not isinstance(approval_request, Approval):
      raise data_store.UnauthorizedAccess("Approval object does not exist.",
                                          requested_access="rw")

    # We are now an approver for this request.
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))
    approval_request.Close(sync=True)

    # Notify to the user.
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(self.delegate),
                             "GRRUser", mode="rw", token=self.token)

    fd.Notify("ViewObject", aff4.RDFURN(self.client_id),
              "%s has approved your request to this "
              "machine" % self.token.username, self.session_id)
    fd.Close()

    template = """
<html><body><h1>GRR machine access granted.</h1>

The user %(username)s has granted access to a GRR machine for the
purpose of: "%(reason)s".

Please click <a href='%(admin_ui)s#%(urn)s'>
  here
</a> to get access to this machine.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

    url = urllib.urlencode((("c", self.client_id),
                            ("main", "HostInformation")))

    email_alerts.SendEmail(self.delegate, self.token.username,
                           "Access granted for machine.",
                           template % dict(
                               username=self.token.username,
                               reason=utils.SmartStr(self.reason),
                               admin_ui=FLAGS.ui_url,
                               urn=url),
                           is_html=True)


class BreakGlassGrantAccessFlow(GrantAccessFlow):
  """Grant an approval in an emergency."""

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id).Add(
        self.token.username).Add(utils.EncodeReasonString(self.reason))

    # Create a new Approval object.
    approval_request = aff4.FACTORY.Create(approval_urn, "Approval",
                                           token=self.token)

    approval_request.Set(approval_request.Schema.REASON(self.reason))
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))

    # This is a break glass approval.
    break_glass = approval_request.Schema.BREAK_GLASS()

    # By default a break_glass approval only lasts 24 hours.
    break_glass += 60 * 60 * 24 * 1e6
    approval_request.Set(break_glass)
    approval_request.Close(sync=True)

    # Notify to the user.
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(
        self.token.username), "GRRUser", mode="rw", token=self.token)

    fd.Notify("ViewObject", aff4.RDFURN(self.client_id),
              "An Emergency Approval has been granted to this "
              "machine", self.session_id)
    fd.Close()

    template = """
<html><body><h1>Emergency Approval Granted.</h1>

The user %(username)s has requested emergency access to host %(hostname)s
(client id %(client_id)s) for the purpose of: "%(reason)s".

This access has been logged and granted for 24 hours.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    email_alerts.SendEmail(FLAGS.grr_emergency_email_address,
                           self.token.username,
                           "Emergency Access Required for machine.",
                           template % dict(
                               client_id=self.client_id,
                               hostname=client.Get(client.Schema.HOSTNAME,
                                                   "Unknown"),
                               username=self.token.username,
                               reason=utils.SmartStr(self.reason)),
                           is_html=True)
