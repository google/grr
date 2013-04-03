#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""AFF4 Objects to enforce ACL policies."""

import urllib

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils

config_lib.DEFINE_integer("ACL.approvers_required", 2,
                          "The number of approvers required for access.")

config_lib.DEFINE_string("AdminUI.url", "http://localhost:8000/",
                         "The direct URL for the user interface.")

config_lib.DEFINE_string("Monitoring.emergency_access_email",
                         "emergency@nowhere.com",
                         "The email address to notify in an emergency.")


class Approval(aff4.AFF4Object):
  """An abstract approval request object.

  This object normally lives within the namespace:
  aff4:/ACL/...

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object.
  """

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    """The Schema for the Approval class."""
    APPROVER = aff4.Attribute("aff4:approval/approver", rdfvalue.RDFString,
                              "An approver for the request.", "approver")

    REASON = aff4.Attribute("aff4:approval/reason",
                            rdfvalue.RDFString,
                            "The reason for requesting access to this client.")

  def CheckAccess(self, token):
    """Check that this approval applies to the given token."""
    _ = token
    raise RuntimeError("Not implemented.")

  @staticmethod
  def GetApprovalForObject(object_urn, token, username=""):
    """Looks for approvals for an object and returns available valid tokens.

    Args:
      object_urn: Urn of the object we want access to.

      token: The token to use to lookup the ACLs.

      username: The user to get the approval for, if "" we get it from the
        token.

    Returns:
      A token for access to the object on success, otherwise raises.

    Raises:
      UnauthorizedAccess: If there are no valid tokens available.

    """
    if not username:
      username = token.username
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(object_urn.Path()).Add(
        username)

    error = "No approvals available"
    fd = aff4.FACTORY.Open(approval_urn, mode="r", token=token)
    for auth_request in fd.OpenChildren():
      try:
        reason = utils.DecodeReasonString(auth_request.urn.Basename())
      except TypeError:
        continue

      # Check authorization using the data_store for an authoritative source.
      test_token = access_control.ACLToken(username, reason)
      try:
        # TODO(user): making assumptions about URNs, no easy way to check
        # for "x" access.
        if object_urn.Split()[0] == "hunts":
          # Hunts are special as they require execute permissions. These aren't
          # in the ACL model for objects yet, so we work around by scheduling a
          # fake flow to do the check for us.
          flow.FACTORY.StartFlow(None, "CheckHuntAccessFlow", token=test_token,
                                 hunt_urn=object_urn)
        else:
          # Check if we can access a non-existent path under this one.
          aff4.FACTORY.Open(rdfvalue.RDFURN(object_urn).Add("acl_chk"),
                            mode="r", token=test_token)
        return test_token
      except access_control.UnauthorizedAccess as e:
        error = e

    # We tried all auth_requests, but got no usable results.
    raise access_control.UnauthorizedAccess(
        error, subject=object_urn)


class ClientApproval(Approval):
  """An approval request for access to a specific client.

  This object normally lives within the namespace:
  aff4:/ACL/client_id/user/<utils.EncodeReasonString(reason)>

  Hence the client_id and user which is granted access are inferred from this
  object's URN.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object:

   - RequestClientApprovalFlow()
   - GrantClientApprovalFlow()
  """

  class SchemaCls(Approval.SchemaCls):
    """The Schema for the ClientAccessApproval class."""
    LIFETIME = aff4.Attribute(
        "aff4:approval/lifetime", rdfvalue.RDFInteger,
        "The number of microseconds an approval is valid for.",
        default=4 * 7 * 24 * 60 * 60 * 1000000)  # 4 weeks

    BREAK_GLASS = aff4.Attribute(
        "aff4:approval/breakglass", rdfvalue.RDFDatetime,
        "The date when this break glass approval will expire.")

  def CheckAccess(self, token):
    """Enforce a dual approver policy for access."""
    namespace, client_id, user, _ = self.urn.Split(4)

    if namespace != "ACL":
      raise access_control.UnauthorizedAccess(
          "Approval object has invalid urn %s.", subject=self.urn,
          requested_access=token.requested_access)

    if user != token.username:
      raise access_control.UnauthorizedAccess(
          "Approval object is not for user %s." % token.username,
          subject=self.urn, requested_access=token.requested_access)

    # This approval can only apply for a client.
    if not self.classes["VFSGRRClient"].CLIENT_ID_RE.match(client_id):
      raise access_control.UnauthorizedAccess(
          "Approval can only be granted on clients, not %s" % client_id,
          subject=self.urn, requested_access=token.requested_access)

    now = rdfvalue.RDFDatetime()

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

    if len(approvers) < config_lib.CONFIG["ACL.approvers_required"]:
      raise access_control.UnauthorizedAccess(
          ("Requires %s approvers for access." %
           config_lib.CONFIG["ACL.approvers_required"]),
          subject=rdfvalue.RDFURN(client_id),
          requested_access=token.requested_access)

    return True


class HuntApproval(Approval):
  """An approval request for running a specific hunt.

  This object normally lives within the namespace:
  aff4:/ACL/hunts/hunt_id/user_id/<utils.EncodeReasonString(reason)>

  Hence the hunt_id and user_id are inferred from this object's URN.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object:

   - RequestHuntApprovalFlow()
   - GrantHuntApprovalFlow()
  """

  class SchemaCls(Approval.SchemaCls):
    """The Schema for the ClientAccessApproval class."""
    LIFETIME = aff4.Attribute(
        "aff4:approval/lifetime", rdfvalue.RDFInteger,
        "The number of microseconds an approval is valid for.",
        default=4 * 7 * 24 * 60 * 60 * 1000000)  # 4 weeks

  def CheckAccess(self, token):
    """Enforce that there are 2 approvers and one of them has "admin" label."""
    namespace, hunts_str, hunt_id, user, _ = self.urn.Split(5)
    if namespace != "ACL" or hunts_str != "hunts":
      raise access_control.UnauthorizedAccess(
          "Approval object has invalid urn %s." % self.urn,
          requested_access=token.requested_access)

    hunt_urn = aff4.ROOT_URN.Add("hunts").Add(hunt_id)

    if user != token.username:
      raise access_control.UnauthorizedAccess(
          "Approval object is not for user %s." % token.username,
          subject=hunt_urn, requested_access=token.requested_access)

    now = rdfvalue.RDFDatetime()

    # Check that there are enough approvers.
    lifetime = self.Get(self.Schema.LIFETIME)
    approvers = set()
    for approver in self.GetValuesForAttribute(self.Schema.APPROVER):
      if approver.age + lifetime > now:
        approvers.add(utils.SmartStr(approver))

    if len(approvers) < config_lib.CONFIG["ACL.approvers_required"]:
      raise access_control.UnauthorizedAccess(
          ("Requires %s approvers for access." %
           config_lib.CONFIG["ACL.approvers_required"]),
          subject=hunt_urn, requested_access=token.requested_access)

    # Check that at least one approver has admin label
    admins = [approver for approver in approvers
              if data_store.DB.security_manager.CheckUserLabels(
                  approver, ["admin"])]

    if not admins:
      raise access_control.UnauthorizedAccess(
          "At least one approver should have 'admin' label.",
          subject=hunt_urn, requested_access=token.requested_access)

    return True


class RequestClientApprovalFlow(flow.GRRFlow):
  """A flow to request approval to access a client."""

  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="Reason for approval",
          name="reason",
          default="Unspecified"),
      type_info.String(
          description="Approver username",
          name="approver",
          default=""),
      )

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # Make a supervisor token
    token = access_control.ACLToken()
    token.supervisor = True

    # TODO(user): remove explicit conversion to RDFURN when all cient_ids
    # are RDFURNs by default
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(
        rdfvalue.RDFURN(self.client_id).Path()).Add(
            self.token.username).Add(utils.EncodeReasonString(self.reason))

    approval_request = aff4.FACTORY.Create(approval_urn, "ClientApproval",
                                           mode="w", token=token)
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

      url = urllib.urlencode((("acl", utils.SmartStr(approval_urn)),
                              ("main", "GrantAccess")))

      email_alerts.SendEmail(user, self.token.username,
                             "Please grant %s access." % self.token.username,
                             template % dict(
                                 username=self.token.username,
                                 hostname=hostname,
                                 reason=utils.SmartStr(self.reason),
                                 admin_ui=config_lib.CONFIG["AdminUI.url"],
                                 approval_urn=url),
                             is_html=True)


class RequestHuntApprovalFlow(flow.GRRFlow):
  """A flow to request approval to access a client."""

  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="Reason for approval",
          name="reason",
          default="Unspecified"),
      type_info.String(
          description="Approver username",
          name="approver",
          default=""),
      type_info.RDFURNType(
          description="Hunt id.",
          name="hunt_id"),
      )

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # Make a supervisor token
    token = access_control.ACLToken()
    token.supervisor = True

    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.hunt_id.Path()).Add(
        self.token.username).Add(utils.EncodeReasonString(self.reason))
    approval_request = aff4.FACTORY.Create(approval_urn, "HuntApproval",
                                           mode="rw", token=token)
    approval_request.Set(approval_request.Schema.REASON(self.reason))

    # We add ourselves as an approver as well (The requirement is that we have 2
    # approvers, so the requester is automatically an approver). For hunts also,
    # one of the approvers must have an "admin" label.
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))

    approval_request.Close()

    # Notify to the users.
    for user in self.approver.split(","):
      user = user.strip()
      fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(user),
                               "GRRUser", mode="rw", token=token)

      fd.Notify("GrantAccess", approval_urn,
                "Please grant permission to run a hunt",
                self.session_id)
      fd.Close()

      template = """
<html><body><h1>GRR hunt run permission requested.</h1>

The user "%(username)s" has requested a permission to run a hunt
for the purpose of "%(reason)s".

Please click <a href='%(admin_ui)s#%(approval_urn)s'>
  here
</a> to review this hunt and then grant access.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

      url = urllib.urlencode((("main", "GrantAccess"),
                              ("acl", utils.SmartStr(approval_urn))))

      email_alerts.SendEmail(user, self.token.username,
                             "Please grant %s access." % self.token.username,
                             template % dict(
                                 username=self.token.username,
                                 reason=utils.SmartStr(self.reason),
                                 admin_ui=config_lib.CONFIG["AdminUI.url"],
                                 approval_urn=url),
                             is_html=True)


class GrantClientApprovalFlow(flow.GRRFlow):
  """Grant the approval requested."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          description="Reason for approval",
          name="reason",
          default="Unspecified"),
      type_info.String(
          description="Delegate username",
          name="delegate",
          default=""),
      )

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # TODO(user): Right now anyone can approve anything. We may want to
    # refine this policy in future.
    # TODO(user): remove explicit conversion to RDFURN when all cient_ids
    # are RDFURNs by default
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(
        rdfvalue.RDFURN(self.client_id).Path()).Add(
            self.delegate).Add(utils.EncodeReasonString(self.reason))

    # This object must already exist.
    try:
      approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                           required_type="Approval",
                                           token=self.token)
    except IOError:
      raise access_control.UnauthorizedAccess("Approval object does not exist.",
                                              requested_access="rw")

    # We are now an approver for this request.
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))
    approval_request.Close(sync=True)

    # Notify to the user.
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(self.delegate),
                             "GRRUser", mode="rw", token=self.token)

    fd.Notify("ViewObject", rdfvalue.RDFURN(self.client_id),
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
                               admin_ui=config_lib.CONFIG["AdminUI.url"],
                               urn=url),
                           is_html=True)


class BreakGlassGrantClientApprovalFlow(GrantClientApprovalFlow):
  """Grant an approval in an emergency."""

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # TODO(user): remove explicit conversion to RDFURN when all cient_ids
    # are RDFURNs by default
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(
        rdfvalue.RDFURN(self.client_id).Path()).Add(
            self.token.username).Add(utils.EncodeReasonString(self.reason))

    # Create a new Approval object.
    approval_request = aff4.FACTORY.Create(approval_urn, "ClientApproval",
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

    fd.Notify("ViewObject", rdfvalue.RDFURN(self.client_id),
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
    email_alerts.SendEmail(
        config_lib.CONFIG["Monitoring.emergency_access_email"],
        self.token.username,
        "Emergency Access Required for machine.",
        template % dict(
            client_id=self.client_id,
            hostname=client.Get(client.Schema.HOSTNAME,
                                "Unknown"),
            username=self.token.username,
            reason=utils.SmartStr(self.reason)),
        is_html=True)


class GrantHuntApprovalFlow(flow.GRRFlow):
  """Grant the approval requested."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFURNType(
          description="The URN of the hunt to execute.",
          name="hunt_urn"),
      type_info.String(
          description="The reason for access.",
          name="reason"),
      type_info.String(
          description="The username to grant approval.",
          name="delegate"),
      )

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.hunt_urn.Path()).Add(
        self.delegate).Add(utils.EncodeReasonString(self.reason))

    # This object must already exist.
    try:
      approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                           required_type="Approval",
                                           token=self.token)
    except IOError:
      raise access_control.UnauthorizedAccess("Approval object does not exist.",
                                              requested_access="rw")

    # We are now an approver for this request.
    approval_request.AddAttribute(
        approval_request.Schema.APPROVER(self.token.username))
    approval_request.Close(sync=True)

    # Notify to the user.
    fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("users").Add(self.delegate),
                             "GRRUser", mode="rw", token=self.token)

    fd.Notify("ViewObject", self.hunt_urn,
              "%s has approved your permission to this hunt" %
              self.token.username, self.session_id)
    fd.Close()

    template = """
<html><body><h1>GRR hunt running permission granted.</h1>

The user %(username)s has granted you permission to run a hunt for the
purpose of: "%(reason)s".

Please click <a href='%(admin_ui)s#%(urn)s'>
  here
</a> to get access to the hunt.

<p>Thanks,</p>
<p>The GRR team.
</body></html>"""

    url = urllib.urlencode((("main", "ManageHunts"),
                            ("hunt", utils.SmartStr(self.hunt_urn))))

    email_alerts.SendEmail(self.delegate, self.token.username,
                           "Running permission granted for hunt.",
                           template % dict(
                               username=self.token.username,
                               reason=utils.SmartStr(self.reason),
                               admin_ui=config_lib.CONFIG["AdminUI.url"],
                               urn=url),
                           is_html=True)
