#!/usr/bin/env python
#
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

"""The access control classes for the data_store."""



import logging
import re


from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import stats
from grr.lib import utils

flags.DEFINE_integer("acl_cache_age", 600, "The number of seconds "
                     "approval objects live in the cache.")

flags.DEFINE_string("security_manager", "NullACLManager",
                    "The ACL manager for controlling access to data.")

FLAGS = flags.FLAGS


class NullACLManager(data_store.BaseAccessControlManager):
  """An ACL manager which does not enforce any ACLs."""

  def CheckAccess(self, token, subjects, requested_access="r"):
    """Allow all access."""
    return True


class AccessControlManager(data_store.BaseAccessControlManager):
  """A class managing access to data resources."""

  def __init__(self):
    self.client_id_re = re.compile(r"^C\.[0-9a-fA-F]{16}$")
    self.blob_re = re.compile(r"^[0-9a-f]{64}$")
    self.acl_cache = utils.AgeBasedCache(max_size=10000,
                                         max_age=FLAGS.acl_cache_age)
    self.flow_cache = utils.FastStore(max_size=10000)
    self.super_token = data_store.ACLToken()
    self.super_token.supervisor = True
    self.flow_switch = aff4.FACTORY.Create("aff4:/flows", "GRRFlowSwitch",
                                           mode="r", token=self.super_token)

    super(AccessControlManager, self).__init__()

  def AccessLowerThan(self, requested_access, mask):
    """Checks that requested_access has lower permissions than mask.

    Args:
      requested_access: The access the user requested, a sequence of 'rwqx'.
      mask: The maximum level of access allowed.

    Returns:
      True if requested_access is lower then the required access, False
      otherwise.
    """
    requested_access = set(requested_access)
    for c in mask:
      if c in requested_access:
        requested_access.remove(c)

    return not requested_access

  @stats.Timed("acl_check_time")
  def CheckAccess(self, token, subjects, requested_access="r"):
    """The main entry point for checking access to resources.

    Args:
      token: An instance of data_store.ACLToken security token.

      subjects: The list of subject URNs which the user is requesting access
         to. If any of these fail, the whole request is denied.

      requested_access: A string specifying the desired level of access ("r" for
         read and "w" for write).

    Returns:
       True: If the access is allowed.

    Raises:
       data_store.UnauthorizedAccess: If the user is not authorized to perform
       the action on any of the subject URNs.
    """
    # The supervisor may bypass all ACL checks.
    if token and token.supervisor:
      return True

    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)

    # Execute access applies to flows only.
    if "x" in requested_access:
      for subject in subjects:
        if not self.CheckFlowAccess(subject, token):
          raise data_store.UnauthorizedAccess(
              "Execution of flow %s rejected." % subject, subject=subject)

    else:
      # Check each subject in turn. If any subject is reject the entire request
      # is rejected.
      for subject in subjects:
        if not self.CheckSubject(subject, token, requested_access):
          raise data_store.UnauthorizedAccess(
              "Must specify authorization for %s" % subject, subject=subject)

    return True

  def CheckSubject(self, subject, token, requested_access):
    """Checks access for just one subject.

    Args:
      subject: The subject to check - Can be an RDFURN or string.
      token: The token to check with.
      requested_access: The type of access requested (can be "r", "w", "x")

    Returns:
      True if the access is allowed.

    Raises:
      UnauthorizedAccess: if the access is rejected.
    """
    # The supervisor may bypass all ACL checks.
    if token and token.supervisor:
      return True

    subject = aff4.RDFURN(subject)
    namespace, path = subject.Split(2)
    # Check for default namespaces.
    if self.CheckWhiteList(namespace, path, requested_access):
      return True

    # Starting from here, all accesses need a token.
    if not token:
      raise data_store.UnauthorizedAccess(
          "Must give an authorization token for %s" % subject,
          subject=namespace)

    # This is a request into a client namespace, requires approval.
    if self.client_id_re.match(namespace):
      return self.CheckApproval(namespace, token)

    # Anyone should be able to read their own user record.
    if namespace == "users" and path == token.username:
      return True

    # Tasks live in their own URN scheme
    if subject.scheme == "task":
      session_id = namespace

      # This allows access to queued tasks for approved clients.
      if self.client_id_re.match(session_id):
        return self.CheckApproval(session_id, token)

      # This provides access to flow objects for approved clients.
      flow_urn = aff4.ROOT_URN.Add("flows").Add(session_id)
      try:
        client_id = self.flow_cache.Get(flow_urn)

        # Check for write access to the client id itself.
        return self.CheckApproval(client_id, token)

      except KeyError:
        try:
          aff4_flow = self.flow_switch.OpenMember(flow_urn)
        except (IOError, flow.FlowError):
          # The flow was not loadable so we allow access to the urn here. This
          # is a race condition but if someone can access a flow it's not a
          # big deal, so we just allow access.
          return True

        try:
          flow_obj = aff4_flow.GetFlowObj()
        except flow.FlowError:
          # This happens because we fail to unpickle the flow - this is not
          # going to change in future, so we just mark it as invalid and cache
          # that.
          self.flow_cache.Put(session_id, "Invalid")
          return True

        client_id = flow_obj.client_id
        self.flow_cache.Put(session_id, client_id)

        # Check access to the client id itself.
        if self.CheckApproval(client_id, token):
          # The user has access to the client, pre-populate the flow cache. Even
          # though this is one more roundtrip we can save a lot of round trips
          # by having the cache pre-populated here.
          fd = aff4.FACTORY.Open(client_id, mode="r", token=self.super_token,
                                 age=aff4.ALL_TIMES)
          for client_flow_urn in fd.GetValuesForAttribute(fd.Schema.FLOW):
            self.flow_cache.Put(client_flow_urn, client_id)

          # We have write access to this client.
          return True

    return False

  def CheckWhiteList(self, namespace, path, requested_access):
    """Checks for access against whitelisted namespaces.

    This check is for predetermined part of the namespace with the same access
    controls for everyone.

    Args:
      namespace: The namespace to check, this is a string.
      path: path following the namespace
      requested_access: The type of access requested (can be "r", "w", "x")

    Returns:
      True if the access is allowed, False otherwise.
    """
    # The ROOT_URN is always allowed.
    if not namespace:
      return True

    # Not sure about this, supervisor token might be better.
    if namespace == "foreman":
      return True

    if namespace == "flows":
      return True

    # Querying is not allowed for the blob namespace. Blobs are stored by hashes
    # as filename. If the user already knows the hash, they can access the blob,
    # however they must not be allowed to query for hashes. Users are not
    # allowed to write to blobs either - so they must only use "r".
    if namespace == "blobs" and self.AccessLowerThan(requested_access, "r"):
      return True

    if namespace == "users" and not path:
      return True

    # Anyone can read the ACL data base.
    if namespace == "ACL" and self.AccessLowerThan(requested_access, "rq"):
      return True

    # Anyone can read stats.
    if namespace == "OSBreakDown" and self.AccessLowerThan(
        requested_access, "r"):
      return True

    # Anyone can read and write indexes.
    if namespace == "index":
      return True

    # Anyone can read cron.
    if namespace == "cron:" and self.AccessLowerThan(requested_access, "r"):
      return True

    if self.client_id_re.match(namespace):
      # Direct reading of clients is allowed for anyone for any reason.
      if not path and "r" in requested_access:
        return True

    # Check access to the flow object.
    if namespace == "flows":
      if not path:
        return True

    if namespace == "config" and "r" in requested_access:
      return True

    return False

  def CheckApproval(self, client_id, token):
    """Checks if access for this client is allowed using the given token.

    Args:
      client_id: The client to check - Can be an RDFURN or string.
      token: The token to check with.

    Returns:
      True if the access is allowed.

    Raises:
      UnauthorizedAccess: if the access is rejected.
    """
    logging.debug("Checking approval for %s, %s", client_id, token)

    if not token.username:
      raise data_store.UnauthorizedAccess(
          "Must specify a username for access.", subject=client_id)

    if not token.reason:
      raise data_store.UnauthorizedAccess(
          "Must specify a reason for access.", subject=client_id)

    # Accept either a client_id or a URN.
    client_id, _ = aff4.RDFURN(client_id).Split(2)

    # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(token.reason)

    try:
      self.acl_cache.Get(approval_urn)
      return True
    except KeyError:
      try:
        # Retrieve the approval object with superuser privileges so we can check
        # it.
        approval_request = aff4.FACTORY.Create(
            approval_urn, "Approval", mode="r", token=self.super_token,
            age=aff4.ALL_TIMES)

        if approval_request.CheckAccess(token):
          # Cache this approval for fast path checking.
          self.acl_cache.Put(approval_urn, True)
          return True

        raise data_store.UnauthorizedAccess(
            "Approval %s was rejected." % approval_urn, subject=client_id)

      except IOError:
        # No Approval found, reject this request.
        raise data_store.UnauthorizedAccess(
            "No approval found for client %s." % client_id, subject=client_id)

  def CheckFlowAccess(self, subject, token):
    """This is called when the user wishes to execute a flow against a client.

    Args:
      subject: The flow must be encoded as aff4:/client_id/flow_name.
      token: The access token.

    Returns:
      True is access if allowed, False otherwise.
    """
    client_id, flow_name = aff4.RDFURN(subject).Split(2)
    flow_cls = flow.GRRFlow.NewPlugin(flow_name)

    # Flows which are not enforced can run all the time.
    if not flow_cls.ACL_ENFORCED:
      return True

    if not self.client_id_re.match(client_id):
      raise data_store.UnauthorizedAccess(
          "Malformed subject for mode 'x': %s." % subject,
          subject=client_id)

    return self.CheckApproval(client_id, token)


class ACLInit(aff4.AFF4InitHook):
  """Install the selected security manager.

  Since many security managers depend on AFF4, we must run after the AFF4
  subsystem is ready.
  """

  def __init__(self):
    stats.STATS.RegisterMap("acl_check_time", "times", precision=0)

    security_manager = data_store.BaseAccessControlManager.NewPlugin(
        FLAGS.security_manager)()
    data_store.DB.security_manager = security_manager
    logging.info("Using security manager %s", security_manager)
