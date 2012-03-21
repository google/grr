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
from grr.lib import flow
from grr.lib import utils


flags.DEFINE_integer("acl_approvers_required", 2,
                     "The number of approvers required for access.")
flags.DEFINE_string("admin_ui_url", "https://localhost/",
                    "The direct URL for the admin UI.")

FLAGS = flags.FLAGS


class Approval(aff4.AFF4Object):
  """An approval request for access to a specific client.

  This object normally lives within the namespace:
  aff4:/ACL/client_id/user/reason

  Hence the client_id and user which is granted access are inferred from this
  object's URN.

  The aff4:/ACL namespace is not writable by users, hence all manipulation of
  this object must be done via dedicated flows. These flows use the server's
  access credentials for manipulating this object:

   - RequestApproval()
   - GrantAccess()
  """

  class SchemaCls(aff4.AFF4Object.SchemaCls):
    APPROVER = aff4.Attribute("aff4:approval/approver", aff4.RDFString,
                              "An approver for the request.", "approver")

    REASON = aff4.Attribute("aff4:approval/reason", aff4.RDFString,
                            "The reason for requesting access to this client.")

    LIFETIME = aff4.Attribute(
        "aff4:approval/lifetime", aff4.RDFInteger,
        "The number of microseconds an approval is valid for.",
        default=60 * 60 * 24 * 7 * 1000000)  # 1 Week

  def CheckAccess(self, token):
    """Enforce a dual approver policy for access."""
    namespace, _, user, _ = self.urn.Split(4)
    if namespace != "ACL":
      raise data_store.UnauthorizedAccess(
          "Approval object has invalid urn %s.", self.urn)

    if user != token.username:
      raise data_store.UnauthorizedAccess("Approval object is not for user "
                                          "%s." % token.username)

    # Check that there are enough approvers.
    lifetime = self.Get(self.Schema.LIFETIME)
    now = aff4.RDFDatetime()
    approvers = set()
    for approver in self.GetValuesForAttribute(self.Schema.APPROVER):
      if approver.age + lifetime > now:
        approvers.add(utils.SmartStr(approver))

    if len(approvers) < FLAGS.acl_approvers_required:
      raise data_store.UnauthorizedAccess("Requires %s approvers for access." %
                                          FLAGS.acl_approvers_required)

    return True


class RequestApproval(flow.GRRFlow):
  """A flow to request approval to access a client."""

  # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  def __init__(self, reason="Unspecified", approver="", **kwargs):
    self.reason = reason
    self.approver = approver
    super(RequestApproval, self).__init__(**kwargs)

  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # Make a supervisor token
    token = data_store.ACLToken()
    token.supervisor = True

    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id).Add(
        self.token.username).Add(self.reason)

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



class GrantAccessFlow(flow.GRRFlow):
  """Grant the approval requested."""
    # This flow can run on any client without ACL enforcement (an SUID flow).
  ACL_ENFORCED = False

  def __init__(self, reason="Unspecified", delegate="", **kwargs):
    self.reason = reason
    self.delegate = delegate
    super(GrantAccessFlow, self).__init__(**kwargs)

  def Start(self):
    """Create the Approval object and notify the Approval Granter."""
    # TODO(user): Right now anyone can approve anything. We may want to
    # refine this policy in future.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(self.client_id).Add(
        self.delegate).Add(self.reason)

    # This object must already exist.
    approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                         token=self.token)
    if not isinstance(approval_request, Approval):
      raise data_store.UnauthorizedAccess("Approval object does not exist.")

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

