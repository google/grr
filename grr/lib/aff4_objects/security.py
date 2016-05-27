#!/usr/bin/env python
"""AFF4 Objects to enforce ACL policies."""


import email
import re
import urllib

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.authorization import client_approval_auth

from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import flows_pb2


class Error(Exception):
  """Base exception class."""


class ErrorClientDoesNotExist(Error):
  """Raised when trying to check approvals on non-existent client."""


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
    REQUESTOR = aff4.Attribute("aff4:approval/requestor", rdfvalue.RDFString,
                               "Requestor of the approval.")

    APPROVER = aff4.Attribute("aff4:approval/approver", rdfvalue.RDFString,
                              "An approver for the request.", "approver")

    SUBJECT = aff4.Attribute("aff4:approval/subject", rdfvalue.RDFURN,
                             "Subject of the approval. I.e. the resource that "
                             "requires approved access.")

    REASON = aff4.Attribute("aff4:approval/reason",
                            rdfvalue.RDFString,
                            "The reason for requesting access to this client.")

    EMAIL_MSG_ID = aff4.Attribute("aff4:approval/email_msg_id",
                                  rdfvalue.RDFString,
                                  "The email thread message ID for this"
                                  "approval. Storing this allows for "
                                  "conversation threading.")

    EMAIL_CC = aff4.Attribute("aff4:approval/email_cc", rdfvalue.RDFString,
                              "Comma separated list of email addresses to "
                              "CC on approval emails.")

    NOTIFIED_USERS = aff4.Attribute("aff4:approval/notified_users",
                                    rdfvalue.RDFString,
                                    "Comma-separated list of GRR users "
                                    "notified about this approval.")

  def CheckAccess(self, token):
    """Check that this approval applies to the given token.

    Args:
      token: User's credentials token.
    Returns:
      True if access is granted, raises access_control.UnauthorizedAccess
      otherwise.
    Raises:
      access_control.UnauthorizedAccess: if access is rejected.
    """
    _ = token
    raise NotImplementedError()

  @staticmethod
  def GetApprovalForObject(object_urn, token=None, username=""):
    """Looks for approvals for an object and returns available valid tokens.

    Args:
      object_urn: Urn of the object we want access to.

      token: The token to use to lookup the ACLs.

      username: The user to get the approval for, if "" we get it from the
        token.

    Returns:
      A token for access to the object on success, otherwise raises.

    Raises:
      UnauthorizedAccess: If there are no valid approvals available.

    """
    if token is None:
      raise access_control.UnauthorizedAccess(
          "No token given, cannot authenticate.")

    if not username:
      username = token.username

    approvals_root_urn = aff4.ROOT_URN.Add("ACL").Add(object_urn.Path()).Add(
        username)

    children_urns = list(aff4.FACTORY.ListChildren(approvals_root_urn,
                                                   token=token))
    if not children_urns:
      raise access_control.UnauthorizedAccess("No approvals found for user %s" %
                                              utils.SmartStr(username),
                                              subject=object_urn)

    last_error = None
    approvals = aff4.FACTORY.MultiOpen(children_urns,
                                       mode="r",
                                       aff4_type=Approval,
                                       age=aff4.ALL_TIMES,
                                       token=token)
    for approval in approvals:
      try:
        test_token = access_control.ACLToken(
            username=username,
            reason=approval.Get(approval.Schema.REASON))
        approval.CheckAccess(token)

        return test_token
      except access_control.UnauthorizedAccess as e:
        last_error = e

    if last_error:
      # We tried all possible approvals, but got no usable results.
      raise access_control.UnauthorizedAccess(last_error, subject=object_urn)
    else:
      # If last error is None, means that none of the URNs in children_urns
      # could be opened. This shouldn't really happen ever, but we have
      # to make sure to provide a meaningful error message.
      raise access_control.UnauthorizedAccess(
          "Couldn't open any of %d approvals "
          "for user %s" % (len(children_urns), utils.SmartStr(username)),
          subject=object_urn)


class ApprovalWithApproversAndReason(Approval):
  """Generic all-purpose base approval class.

  This object normally lives within the aff4:/ACL namespace. Reason and username
  are encoded into this object's urn. Subject's urn (i.e. urn of the object
  which this approval corresponds for) can also be inferred from this approval's
  urn.
  This class provides following functionality:
  * Number of approvers configured by ACL.approvers_required configuration
    parameter is required for this approval's CheckAccess() to succeed.
  * Optional checked_approvers_label attribute may be specified. Then
    at least min_approvers_with_label number of approvers will have to
    have checked_approvers_label label in order for CheckAccess to
    succeed.
  * Break-glass functionality. If this approval's BREAK_GLASS attribute is
    set, user's token is marked as emergency token and CheckAccess() returns
    True.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows.
  """

  checked_approvers_label = None
  min_approvers_with_label = 1

  class SchemaCls(Approval.SchemaCls):
    """The Schema for the ClientAccessApproval class."""

    LIFETIME = aff4.Attribute("aff4:approval/lifetime",
                              rdfvalue.RDFInteger,
                              "The number of seconds an approval is valid for.",
                              default=0)
    BREAK_GLASS = aff4.Attribute(
        "aff4:approval/breakglass", rdfvalue.RDFDatetime,
        "The date when this break glass approval will expire.")

  def InferUserAndSubjectFromUrn(self):
    """Infers user name and subject urn from self.urn.

    Returns:
      (username, subject_urn) tuple.
    """
    raise NotImplementedError()

  def GetApprovers(self, now):
    lifetime = rdfvalue.Duration(self.Get(self.Schema.LIFETIME) or
                                 config_lib.CONFIG["ACL.token_expiry"])

    # Check that there are enough approvers.
    approvers = set()
    for approver in self.GetValuesForAttribute(self.Schema.APPROVER):
      if approver.age + lifetime > now:
        approvers.add(utils.SmartStr(approver))
    return approvers

  def CheckAccess(self, token):
    """Enforce a dual approver policy for access."""
    namespace, _ = self.urn.Split(2)

    if namespace != "ACL":
      raise access_control.UnauthorizedAccess(
          "Approval object has invalid urn %s." % self.urn,
          subject=self.urn,
          requested_access=token.requested_access)

    user, subject_urn = self.InferUserAndSubjectFromUrn()
    if user != token.username:
      raise access_control.UnauthorizedAccess(
          "Approval object is not for user %s." % token.username,
          subject=self.urn,
          requested_access=token.requested_access)

    now = rdfvalue.RDFDatetime().Now()

    # Is this an emergency access?
    break_glass = self.Get(self.Schema.BREAK_GLASS)
    if break_glass and now < break_glass:
      # This tags the token as an emergency token.
      token.is_emergency = True
      return True

    # Check that there are enough approvers.
    approvers = self.GetNonExpiredApprovers()
    if len(approvers) < config_lib.CONFIG["ACL.approvers_required"]:
      msg = ("Requires %s approvers for access." %
             config_lib.CONFIG["ACL.approvers_required"])
      raise access_control.UnauthorizedAccess(
          msg, subject=subject_urn,
          requested_access=token.requested_access)

    # Check User labels
    if self.checked_approvers_label:
      approvers_with_label = []

      # We need to check labels with high privilege since normal users can
      # inspect other user's labels.
      for approver in approvers:
        try:
          user = aff4.FACTORY.Open("aff4:/users/%s" % approver,
                                   aff4_type=aff4_users.GRRUser,
                                   token=token.SetUID())
          if self.checked_approvers_label in user.GetLabelsNames():
            approvers_with_label.append(approver)
        except IOError:
          pass

      if len(approvers_with_label) < self.min_approvers_with_label:
        raise access_control.UnauthorizedAccess(
            "At least %d approver(s) should have '%s' label." %
            (self.min_approvers_with_label, self.checked_approvers_label),
            subject=subject_urn,
            requested_access=token.requested_access)

    return True

  def GetNonExpiredApprovers(self):
    """Returns a list of usernames of approvers who approved this approval."""

    lifetime = rdfvalue.Duration(self.Get(self.Schema.LIFETIME) or
                                 config_lib.CONFIG["ACL.token_expiry"])

    # Check that there are enough approvers.
    #
    # TODO(user): approvals have to be opened with
    # age=aff4.ALL_TIMES because versioning is used to store lists
    # of approvers. This doesn't seem right and has to be fixed.
    approvers = set()
    now = rdfvalue.RDFDatetime().Now()
    for approver in self.GetValuesForAttribute(self.Schema.APPROVER):
      if approver.age + lifetime > now:
        approvers.add(utils.SmartStr(approver))

    return list(approvers)


class ClientApproval(ApprovalWithApproversAndReason):
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
   - BreakGlassGrantClientApprovalFlow()
  """

  def InferUserAndSubjectFromUrn(self):
    """Infers user name and subject urn from self.urn."""
    _, client_id, user, _ = self.urn.Split(4)
    return (user, rdf_client.ClientURN(client_id))

  def CheckAccess(self, token):
    super(ClientApproval, self).CheckAccess(token)
    # If approvers isn't set and super-class checking passed, we're done.
    if not client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.IsActive():
      return True

    now = rdfvalue.RDFDatetime().Now()
    approvers = self.GetApprovers(now)
    requester, client_urn = self.InferUserAndSubjectFromUrn()
    # Open the client object with superuser privs so we can get the list of
    # labels
    try:
      client_object = aff4.FACTORY.Open(client_urn,
                                        mode="r",
                                        aff4_type=aff4_grr.VFSGRRClient,
                                        token=token.SetUID())
    except aff4.InstantiationError:
      raise ErrorClientDoesNotExist("Can't check label approvals on client %s "
                                    "that doesn't exist" % client_urn)

    client_labels = client_object.Get(client_object.Schema.LABELS, [])

    for label in client_labels:
      client_approval_auth.CLIENT_APPROVAL_AUTH_MGR.CheckApproversForLabel(
          token, client_urn, requester, approvers, label.name)

    return True


class HuntApproval(ApprovalWithApproversAndReason):
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

  checked_approvers_label = "admin"

  def InferUserAndSubjectFromUrn(self):
    """Infers user name and subject urn from self.urn."""
    _, hunts_str, hunt_id, user, _ = self.urn.Split(5)

    if hunts_str != "hunts":
      raise access_control.UnauthorizedAccess(
          "Approval object has invalid urn %s." % self.urn,
          requested_access=self.token.requested_access)

    return (user, aff4.ROOT_URN.Add("hunts").Add(hunt_id))


class CronJobApproval(ApprovalWithApproversAndReason):
  """An approval request for managing a specific cron job.

  This object normally lives within the namespace:
  aff4:/ACL/cron/cron_job_id/user_id/<utils.EncodeReasonString(reason)>

  Hence the hunt_id and user_id are inferred from this object's URN.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object:

   - RequestCronJobApprovalFlow()
   - GrantCronJobApprovalFlow()
  """

  checked_approvers_label = "admin"

  def InferUserAndSubjectFromUrn(self):
    """Infers user name and subject urn from self.urn."""
    _, cron_str, cron_job_name, user, _ = self.urn.Split(5)

    if cron_str != "cron":
      raise access_control.UnauthorizedAccess(
          "Approval object has invalid urn %s." % self.urn,
          requested_access=self.token.requested_access)

    return (user, aff4.ROOT_URN.Add("cron").Add(cron_job_name))


class AbstractApprovalWithReason(object):
  """Abstract class for approval requests/grants."""
  approval_type = None

  def BuildApprovalUrn(self):
    """Builds approval object urn."""
    raise NotImplementedError()

  def BuildApprovalSymlinksUrns(self):
    """Builds a list of symlinks to the approval object."""
    return []

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    raise NotImplementedError()

  def BuildAccessUrl(self):
    """Builds the urn to access this object."""
    raise NotImplementedError()

  def CreateReasonHTML(self, reason):
    """Creates clickable links in the reason where appropriate.

    Args:
      reason: reason string
    Returns:
      Reason string with HTML hrefs as appropriate.

    Use a regex named group of "link":
      (?P<link>sometext)

    for things that should be turned into links.
    """
    for link_re in config_lib.CONFIG.Get("Email.link_regex_list"):
      reason = re.sub(link_re, r"""<a href="\g<link>">\g<link></a>""", reason)
    return reason

  @staticmethod
  def ApprovalUrnBuilder(subject, user, reason):
    """Encode an approval URN."""
    return aff4.ROOT_URN.Add("ACL").Add(subject).Add(user).Add(
        utils.EncodeReasonString(reason))

  @staticmethod
  def ApprovalSymlinkUrnBuilder(approval_type, unique_id, user, reason):
    """Build an approval symlink URN."""
    return aff4.ROOT_URN.Add("users").Add(user).Add("approvals").Add(
        approval_type).Add(unique_id).Add(utils.EncodeReasonString(reason))


class RequestApprovalWithReasonFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.RequestApprovalWithReasonFlowArgs


class RequestApprovalWithReasonFlow(AbstractApprovalWithReason, flow.GRRFlow):
  """Base flow class for flows that request approval of a certain type."""
  args_type = RequestApprovalWithReasonFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    approval_urn = self.BuildApprovalUrn()
    subject_title = self.BuildSubjectTitle()
    email_msg_id = email.utils.make_msgid()

    with aff4.FACTORY.Create(approval_urn,
                             self.approval_type,
                             mode="w",
                             token=self.token) as approval_request:
      approval_request.Set(approval_request.Schema.SUBJECT(
          self.args.subject_urn))
      approval_request.Set(approval_request.Schema.REQUESTOR(
          self.token.username))
      approval_request.Set(approval_request.Schema.REASON(self.args.reason))
      approval_request.Set(approval_request.Schema.EMAIL_MSG_ID(email_msg_id))

      cc_addresses = (self.args.email_cc_address,
                      config_lib.CONFIG.Get("Email.approval_cc_address"))
      email_cc = ",".join(filter(None, cc_addresses))

      # When we reply with the approval we want to cc all the people to whom the
      # original approval was sent, to avoid people approving stuff that was
      # already approved.
      if email_cc:
        reply_cc = ",".join((self.args.approver, email_cc))
      else:
        reply_cc = self.args.approver

      approval_request.Set(approval_request.Schema.EMAIL_CC(reply_cc))

      approval_request.Set(approval_request.Schema.NOTIFIED_USERS(
          self.args.approver))

      # We add ourselves as an approver as well (The requirement is that we have
      # 2 approvers, so the requester is automatically an approver).
      approval_request.AddAttribute(approval_request.Schema.APPROVER(
          self.token.username))

    approval_link_urns = self.BuildApprovalSymlinksUrns()
    for link_urn in approval_link_urns:
      with aff4.FACTORY.Create(link_urn,
                               aff4.AFF4Symlink,
                               mode="w",
                               token=self.token) as link:
        link.Set(link.Schema.SYMLINK_TARGET(approval_urn))

    # Notify to the users.
    for user in self.args.approver.split(","):
      user = user.strip()
      fd = aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("users").Add(user),
          aff4_users.GRRUser,
          mode="rw",
          token=self.token)

      fd.Notify("GrantAccess", approval_urn,
                "Please grant access to %s" % subject_title, self.session_id)
      fd.Close()

    if not config_lib.CONFIG.Get("Email.send_approval_emails"):
      return

    reason = self.CreateReasonHTML(self.args.reason)

    template = u"""
<html><body><h1>Approval to access
<a href='%(admin_ui)s#%(approval_urn)s'>%(subject_title)s</a> requested.</h1>

The user "%(username)s" has requested access to
<a href='%(admin_ui)s#%(approval_urn)s'>%(subject_title)s</a>
for the purpose of "%(reason)s".

Please click <a href='%(admin_ui)s#%(approval_urn)s'>
here
</a> to review this request and then grant access.

<p>Thanks,</p>
<p>%(signature)s</p>
<p>%(image)s</p>
</body></html>"""

    # If you feel like it, add a funny cat picture here :)
    image = config_lib.CONFIG["Email.approval_signature"]

    url = urllib.urlencode((("acl", utils.SmartStr(approval_urn)), (
        "main", "GrantAccess")))

    body = template % dict(username=self.token.username,
                           reason=reason,
                           admin_ui=config_lib.CONFIG["AdminUI.url"],
                           subject_title=subject_title,
                           approval_urn=url,
                           image=image,
                           signature=config_lib.CONFIG["Email.signature"])

    email_alerts.EMAIL_ALERTER.SendEmail(self.args.approver,
                                         utils.SmartStr(self.token.username),
                                         u"Approval for %s to access %s." %
                                         (self.token.username, subject_title),
                                         utils.SmartStr(body),
                                         is_html=True,
                                         cc_addresses=email_cc,
                                         message_id=email_msg_id)


class GrantApprovalWithReasonFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.GrantApprovalWithReasonFlowArgs


class GrantApprovalWithReasonFlow(AbstractApprovalWithReason, flow.GRRFlow):
  """Base flows class for flows that grant approval of a certain type."""
  args_type = GrantApprovalWithReasonFlowArgs

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    approval_urn = self.BuildApprovalUrn()
    subject_title = self.BuildSubjectTitle()
    access_urn = self.BuildAccessUrl()

    # This object must already exist.
    try:
      approval_request = aff4.FACTORY.Open(approval_urn,
                                           mode="rw",
                                           aff4_type=self.approval_type,
                                           token=self.token)
    except IOError:
      raise access_control.UnauthorizedAccess("Approval object does not exist.",
                                              requested_access="rw")

    # We are now an approver for this request.
    approval_request.AddAttribute(approval_request.Schema.APPROVER(
        self.token.username))
    email_msg_id = utils.SmartStr(approval_request.Get(
        approval_request.Schema.EMAIL_MSG_ID))
    email_cc = utils.SmartStr(approval_request.Get(
        approval_request.Schema.EMAIL_CC))

    approval_request.Close(sync=True)

    # Notify to the user.
    fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.args.delegate),
        aff4_users.GRRUser,
        mode="rw",
        token=self.token)

    fd.Notify("ViewObject", self.args.subject_urn,
              "%s has granted you access to %s." %
              (self.token.username, subject_title), self.session_id)
    fd.Close()

    if not config_lib.CONFIG.Get("Email.send_approval_emails"):
      return

    reason = self.CreateReasonHTML(self.args.reason)

    template = u"""
<html><body><h1>Access to
<a href='%(admin_ui)s#%(subject_urn)s'>%(subject_title)s</a> granted.</h1>

The user %(username)s has granted access to
<a href='%(admin_ui)s#%(subject_urn)s'>%(subject_title)s</a> for the
purpose of "%(reason)s".

Please click <a href='%(admin_ui)s#%(subject_urn)s'>here</a> to access it.

<p>Thanks,</p>
<p>%(signature)s</p>
</body></html>"""

    body = template % dict(subject_title=subject_title,
                           username=self.token.username,
                           reason=reason,
                           admin_ui=config_lib.CONFIG["AdminUI.url"],
                           subject_urn=access_urn,
                           signature=config_lib.CONFIG["Email.signature"])

    # Email subject should match approval request, and we add message id
    # references so they are grouped together in a thread by gmail.
    subject = u"Approval for %s to access %s." % (
        utils.SmartStr(self.args.delegate), subject_title)
    headers = {"In-Reply-To": email_msg_id, "References": email_msg_id}
    email_alerts.EMAIL_ALERTER.SendEmail(
        utils.SmartStr(self.args.delegate),
        utils.SmartStr(self.token.username),
        subject,
        utils.SmartStr(body),
        is_html=True,
        cc_addresses=email_cc,
        headers=headers)


class BreakGlassGrantApprovalWithReasonFlow(GrantApprovalWithReasonFlow):
  """Grant an approval in an emergency."""

  @flow.StateHandler()
  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    approval_urn = self.BuildApprovalUrn()
    subject_title = self.BuildSubjectTitle()

    # Create a new Approval object.
    approval_request = aff4.FACTORY.Create(approval_urn,
                                           aff4_type=self.approval_type,
                                           token=self.token)

    approval_request.Set(approval_request.Schema.REASON(self.args.reason))
    approval_request.AddAttribute(approval_request.Schema.APPROVER(
        self.token.username))

    # This is a break glass approval.
    break_glass = approval_request.Schema.BREAK_GLASS().Now()

    # By default a break_glass approval only lasts 24 hours.
    break_glass += 60 * 60 * 24 * 1e6
    approval_request.Set(break_glass)
    approval_request.Close(sync=True)

    # Notify the user.
    fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(self.token.username),
        aff4_users.GRRUser,
        mode="rw",
        token=self.token)

    fd.Notify("ViewObject", self.args.subject_urn,
              "An Emergency Approval has been granted to access "
              "%s." % subject_title, self.session_id)
    fd.Close()

    template = u"""
<html><body><h1>Emergency Access Granted.</h1>

The user %(username)s has requested emergency access to %(subject_title)s.
for the purpose of: "%(reason)s".

This access has been logged and granted for 24 hours.

<p>Thanks,</p>
<p>%(signature)s</p>
</body></html>"""

    body = template % dict(client_id=self.client_id,
                           username=self.token.username,
                           subject_title=subject_title,
                           reason=self.args.reason,
                           signature=config_lib.CONFIG["Email.signature"]),

    email_alerts.EMAIL_ALERTER.SendEmail(
        config_lib.CONFIG["Monitoring.emergency_access_email"],
        self.token.username,
        u"Emergency approval granted for %s." % subject_title,
        utils.SmartStr(body),
        is_html=True,
        cc_addresses=config_lib.CONFIG["Email.approval_cc_address"])


class RequestClientApprovalFlow(RequestApprovalWithReasonFlow):
  """A flow to request approval to access a client."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = ClientApproval

  def BuildApprovalUrn(self):
    """Builds approval object urn."""
    event = flow.AuditEvent(user=self.token.username,
                            action="CLIENT_APPROVAL_REQUEST",
                            client=self.client_id,
                            description=self.args.reason)
    flow.Events.PublishEvent("Audit", event, token=self.token)

    return self.ApprovalUrnBuilder(self.client_id.Path(), self.token.username,
                                   self.args.reason)

  def BuildApprovalSymlinksUrns(self):
    """Builds list of symlinks URNs for the approval object."""
    return [self.ApprovalSymlinkUrnBuilder("client", self.client_id.Basename(),
                                           self.token.username,
                                           self.args.reason)]

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME)
    return u"GRR client %s (%s)" % (self.client_id.Basename(), hostname)


class GrantClientApprovalFlow(GrantApprovalWithReasonFlow):
  """Grant the approval requested."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = ClientApproval

  def BuildApprovalUrn(self):
    """Builds approval object urn."""
    flow.Events.PublishEvent("Audit",
                             flow.AuditEvent(user=self.token.username,
                                             action="CLIENT_APPROVAL_GRANT",
                                             client=self.client_id,
                                             description=self.args.reason),
                             token=self.token)

    return self.ApprovalUrnBuilder(self.client_id.Path(), self.args.delegate,
                                   self.args.reason)

  def BuildAccessUrl(self):
    """Builds the urn to access this object."""
    return urllib.urlencode((("c", self.client_id), ("main", "HostInformation")
                            ))

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME)
    return u"GRR client %s (%s)" % (self.client_id.Basename(), hostname)


class BreakGlassGrantClientApprovalFlow(BreakGlassGrantApprovalWithReasonFlow):
  """Grant an approval in an emergency."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = ClientApproval

  def BuildApprovalUrn(self):
    """Builds approval object urn."""
    event = flow.AuditEvent(user=self.token.username,
                            action="CLIENT_APPROVAL_BREAK_GLASS_REQUEST",
                            client=self.client_id,
                            description=self.args.reason)
    flow.Events.PublishEvent("Audit", event, token=self.token)

    return self.ApprovalUrnBuilder(self.client_id.Path(), self.token.username,
                                   self.args.reason)

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    client = aff4.FACTORY.Open(self.client_id, token=self.token)
    hostname = client.Get(client.Schema.HOSTNAME)
    return u"GRR client %s (%s)" % (self.client_id.Basename(), hostname)


class RequestHuntApprovalFlow(RequestApprovalWithReasonFlow):
  """A flow to request approval to access a client."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = HuntApproval

  def BuildApprovalUrn(self):
    """Builds approval object URN."""
    # In this case subject_urn is hunt's URN.
    flow.Events.PublishEvent("Audit",
                             flow.AuditEvent(user=self.token.username,
                                             action="HUNT_APPROVAL_REQUEST",
                                             urn=self.args.subject_urn,
                                             description=self.args.reason),
                             token=self.token)

    return self.ApprovalUrnBuilder(self.args.subject_urn.Path(),
                                   self.token.username, self.args.reason)

  def BuildApprovalSymlinksUrns(self):
    """Builds list of symlinks URNs for the approval object."""
    return [self.ApprovalSymlinkUrnBuilder("hunt",
                                           self.args.subject_urn.Basename(),
                                           self.token.username,
                                           self.args.reason)]

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    return u"hunt %s" % self.args.subject_urn.Basename()


class GrantHuntApprovalFlow(GrantApprovalWithReasonFlow):
  """Grant the approval requested."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = HuntApproval

  def BuildApprovalUrn(self):
    """Builds approval object URN."""
    # In this case subject_urn is hunt's URN.
    flow.Events.PublishEvent("Audit",
                             flow.AuditEvent(user=self.token.username,
                                             action="HUNT_APPROVAL_GRANT",
                                             urn=self.args.subject_urn,
                                             description=self.args.reason),
                             token=self.token)

    return self.ApprovalUrnBuilder(self.args.subject_urn.Path(),
                                   self.args.delegate, self.args.reason)

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    return u"hunt %s" % self.args.subject_urn.Basename()

  def BuildAccessUrl(self):
    """Builds the urn to access this object."""
    return urllib.urlencode((("main", "ManageHunts"), ("hunt",
                                                       self.args.subject_urn)))


class RequestCronJobApprovalFlow(RequestApprovalWithReasonFlow):
  """A flow to request approval to manage a cron job."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = CronJobApproval

  def BuildApprovalUrn(self):
    """Builds approval object URN."""
    # In this case subject_urn is hunt's URN.
    flow.Events.PublishEvent("Audit",
                             flow.AuditEvent(user=self.token.username,
                                             action="CRON_APPROVAL_REQUEST",
                                             urn=self.args.subject_urn,
                                             description=self.args.reason),
                             token=self.token)

    return self.ApprovalUrnBuilder(self.args.subject_urn.Path(),
                                   self.token.username, self.args.reason)

  def BuildApprovalSymlinksUrns(self):
    """Builds list of symlinks URNs for the approval object."""
    return [self.ApprovalSymlinkUrnBuilder("cron",
                                           self.args.subject_urn.Basename(),
                                           self.token.username,
                                           self.args.reason)]

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    return u"a cron job"


class GrantCronJobApprovalFlow(GrantApprovalWithReasonFlow):
  """Grant approval to manage a cron job."""
  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  approval_type = CronJobApproval

  def BuildApprovalUrn(self):
    """Builds approval object URN."""
    # In this case subject_urn is hunt's URN.
    flow.Events.PublishEvent("Audit",
                             flow.AuditEvent(user=self.token.username,
                                             action="CRON_APPROVAL_GRANT",
                                             urn=self.args.subject_urn,
                                             description=self.args.reason),
                             token=self.token)

    return self.ApprovalUrnBuilder(self.args.subject_urn.Path(),
                                   self.args.delegate, self.args.reason)

  def BuildSubjectTitle(self):
    """Returns the string with subject's title."""
    return u"a cron job"

  def BuildAccessUrl(self):
    """Builds the urn to access this object."""
    return urllib.urlencode({"main": "ManageCron"})
