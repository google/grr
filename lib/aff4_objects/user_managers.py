#!/usr/bin/env python
"""This module implements User managers and Access control managers.

These are concrete implementations of the classes defined in access_control.py:

AccessControlManager Classes:
  NullAccessControlManager: Gives everyone full access to everything.
  TestAccessControlManager: In memory, very basic functionality for tests.
  FullAccessControlManager: Provides for multiparty authorization.
  BasicAccessControlManager: Provides basic Admin/Non-Admin distinction based on
    labels.
"""


import fnmatch
import re

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr


class BaseAccessControlManager(access_control.AccessControlManager):

  def CheckUserLabels(self, username, authorized_labels, token=None):
    """Verify that the username has all the authorized_labels set."""
    authorized_labels = set(authorized_labels)

    try:
      user = aff4.FACTORY.Open("aff4:/users/%s" % username, aff4_type="GRRUser",
                               token=token)

      # Only return if all the authorized_labels are found in the user's
      # label list, otherwise raise UnauthorizedAccess.
      if (authorized_labels.intersection(user.GetLabelsNames()) ==
          authorized_labels):
        return
      raise access_control.UnauthorizedAccess(
          "User %s is missing labels (required: %s)." % (username,
                                                         authorized_labels))
    except IOError:
      raise access_control.UnauthorizedAccess("User %s not found." % username)


class BasicAccessControlManager(BaseAccessControlManager):
  """Basic ACL manager that uses the config file for user management."""

  # pylint: disable=unused-argument
  def CheckHuntAccess(self, token, hunt_urn):
    """Allow all access."""
    return True

  def CheckFlowAccess(self, token, flow_name, client_id=None):
    """Allow all access."""
    return True

  def CheckCronJobAccess(self, token, cron_job_urn):
    """Allow all access."""
    return True

  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """Allow all access."""
    return True
  # pylint: enable=unused-argument


class NullAccessControlManager(BasicAccessControlManager):
  """An ACL manager which does not enforce any ACLs."""

  # pylint: disable=unused-argument
  def CheckUserLabels(self, username, authorized_labels, token=None):
    """Allow all access."""
    return True
  # pylint: enable=unused-argument


class CheckAccessHelper(object):
  """Helps with access checks (See FullAccessControlManager for details)."""

  def __init__(self, helper_name):
    """Constructor for CheckAccessHelper.

    Args:
      helper_name: String identifier of this helper (used for logging).
    """
    self.helper_name = helper_name
    self.checks = []

  def Allow(self, path, require=None, *args, **kwargs):
    """Checks if given path pattern fits the subject passed in constructor.

    Registers "allow" check in this helper. "Allow" check consists of
    fnmatch path pattern and optional "require" check. *args and *kwargs will
    be passed to the optional "require" check function.

    All registered "allow" checks are executed in CheckAccess() call. The
    following is done for every check:
    * If fnmatch path pattern does not match the check is skipped.
    * If fnmatch path pattern matches and the require parameter is None (does
      not specify an additiona check) then match is successful.
      No other checks are executed.
    * If fnmatch path pattern matches and the require parameter specifies an
      additional check, which is a function, and this function returns True,
      then match is successful. No other checks are executed.
    * If fnmatch path pattern matches but additional check raises,
      match is unsuccessful, no other checks are executed, and exception
      is propagated.

    Args:
      path: A string, which is a fnmatch pattern.
      require: Function that will be called to perform additional checks.
               None by default. It will be called like this:
               require(subject_urn, *args, **kwargs).
               If this function returns True, the check is considered
               passed. If it raises, the check is considered failed, no
               other checks are made and exception is propagated.
      *args: Positional arguments that will be passed to "require" function.
      **kwargs: Keyword arguments that will be passed to "require" function.
    """
    regex_text = fnmatch.translate(path)
    regex = re.compile(regex_text)
    self.checks.append((regex_text, regex, require, args, kwargs))

  def CheckAccess(self, subject, token):
    """Checks for access to given subject with a given token.

    CheckAccess runs given subject through all "allow" clauses that
    were previously registered with Allow() calls. It returns True on
    first match and raises access_control.UnauthorizedAccess if there
    are no matches or if any of the additional checks fails.

    Args:
      subject: RDFURN of the subject that will be checked for access.
      token: User credentials token.

    Returns:
      True if access is granted.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    subject = rdfvalue.RDFURN(subject)
    subject_str = subject.SerializeToString()

    for check_tuple in self.checks:
      regex_text, regex, require, require_args, require_kwargs = check_tuple

      match = regex.match(subject_str)
      if not match:
        continue

      if require:
        # If require() fails, it raises access_control.UnauthorizedAccess.
        require(subject, token, *require_args, **require_kwargs)

      logging.debug("Allowing access to %s by pattern: %s "
                    "(require=%s, require_args=%s, require_kwargs=%s, "
                    "helper_name=%s)",
                    subject_str, regex_text, require, require_args,
                    require_kwargs, self.helper_name)
      return True

    logging.debug("Rejecting access to %s (no matched rules)", subject_str)
    raise access_control.UnauthorizedAccess(
        "Access to %s rejected: (no matched rules)." % subject, subject=subject)


class FullAccessControlManager(BaseAccessControlManager):
  """An access control manager that handles multi-party authorization.

  Write access to the data store is forbidden. Data store read- and query-access
  policies are defined in _CreateReadAccessHelper and _CreateQueryAccessHelper
  functions. Please refer to these functions to review or modify GRR's data
  store access policies.
  """

  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  def __init__(self):
    self.client_id_re = aff4_grr.VFSGRRClient.CLIENT_ID_RE
    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=config_lib.CONFIG["ACL.cache_age"])

    self.flow_cache = utils.FastStore(max_size=10000)
    self.super_token = access_control.ACLToken(username="test").SetUID()

    self.write_access_helper = self._CreateWriteAccessHelper()
    self.read_access_helper = self._CreateReadAccessHelper()
    self.query_access_helper = self._CreateQueryAccessHelper()

    super(FullAccessControlManager, self).__init__()

  def _CreateWriteAccessHelper(self):
    """Creates a CheckAccessHelper for controlling write access."""
    h = CheckAccessHelper("write")

    # Namespace for temporary scratch space. Note that Querying this area is not
    # allowed. Users should create files with random names if they want to
    # prevent other users from reading or modifying them.
    h.Allow("aff4:/tmp")
    h.Allow("aff4:/tmp/*")

    # Users are allowed to modify artifacts live.
    h.Allow("aff4:/artifact_store")
    h.Allow("aff4:/artifact_store/*")

    return h

  def _CreateReadAccessHelper(self):
    """Creates a CheckAccessHelper for controlling read access.

    This function and _CreateQueryAccessHelper essentially define GRR's ACL
    policy. Please refer to these 2 functions to either review or modify
    GRR's ACLs.

    Read access gives you the ability to open and read aff4 objects for which
    you already have the URN.

    Returns:
      CheckAccessHelper for controlling read access.
    """
    h = CheckAccessHelper("read")

    h.Allow("aff4:/")

    # In order to open directories below aff4:/users, we have to have access to
    # aff4:/users directory itself.
    h.Allow("aff4:/users")

    # User is allowed to access anything in his home dir.
    h.Allow("aff4:/users/*", self.IsHomeDir)

    # Administrators are allowed to see current set of foreman rules.
    h.Allow("aff4:/foreman", self.UserHasAdminLabel)

    # Querying is not allowed for the blob namespace. Blobs are stored by hashes
    # as filename. If the user already knows the hash, they can access the blob,
    # however they must not be allowed to query for hashes.
    h.Allow("aff4:/blobs")
    h.Allow("aff4:/blobs/*")

    # The fingerprint namespace typically points to blobs. As such, it follows
    # the same rules.
    h.Allow("aff4:/FP")
    h.Allow("aff4:/FP/*")

    # The files namespace contains hash references to all files downloaded with
    # GRR, and is extensible via Filestore objects. Users can access files for
    # which they know the hash.
    # See lib/aff4_objects/filestore.py
    h.Allow("aff4:/files")
    h.Allow("aff4:/files/*")

    # Namespace for indexes. Client index is stored there.
    h.Allow("aff4:/index")
    h.Allow("aff4:/index/*")

    # ACL namespace contains approval objects for accessing clients and hunts.
    h.Allow("aff4:/ACL")
    h.Allow("aff4:/ACL/*")

    # stats namespace is for different statistics. For example, ClientFleetStats
    # object is stored there.
    h.Allow("aff4:/stats")
    h.Allow("aff4:/stats/*")
    h.Allow("aff4:/stats/FileStoreStats")
    h.Allow("aff4:/stats/FileStoreStats/*")

    # Configuration namespace used for reading drivers, python hacks etc.
    h.Allow("aff4:/config")
    h.Allow("aff4:/config/*")

    # Namespace for flows that run without a client. A lot of internal utilitiy
    # flows and cron jobs' flows will end up here.
    h.Allow("aff4:/flows")
    h.Allow("aff4:/flows/*")

    # Namespace for hunts.
    h.Allow("aff4:/hunts")
    h.Allow("aff4:/hunts/*")

    # Namespace for cron jobs.
    h.Allow("aff4:/cron")
    h.Allow("aff4:/cron/*")

    # Namespace for crashes data.
    h.Allow("aff4:/crashes")
    h.Allow("aff4:/crashes/*")

    # Namespace for audit data.
    h.Allow("aff4:/audit")
    h.Allow("aff4:/audit/*")

    # Namespace for clients.
    h.Allow(self.CLIENT_URN_PATTERN)
    h.Allow(self.CLIENT_URN_PATTERN + "/*", self.UserHasClientApproval)

    # Namespace for temporary scratch space. Note that Querying this area is not
    # allowed. Users should create files with random names if they want to
    # prevent other users from reading or modifying them.
    h.Allow("aff4:/tmp")
    h.Allow("aff4:/tmp/*")

    # Allow everyone to read the artifact store.
    h.Allow("aff4:/artifact_store")
    h.Allow("aff4:/artifact_store/*")

    # Allow everyone to read monitoring data from stats store.
    h.Allow("aff4:/stats_store")
    h.Allow("aff4:/stats_store/*")

    return h

  def _CreateQueryAccessHelper(self):
    """Creates a CheckAccessHelper for controlling query access.

    This function and _CreateReadAccessHelper essentially define GRR's ACL
    policy. Please refer to these 2 functions to either review or modify
    GRR's ACLs.

    Query access gives you the ability to find objects in the tree without
    knowing their URN, using ListChildren.  If you grant query access,
    you will also need read access.

    Returns:
      CheckAccessHelper for controlling query access.
    """
    h = CheckAccessHelper("query")

    # Querying is allowed for aff4:/cron/*, as GUI renders list of current
    # cron jobs. Also, links to flows executed by every cron job are stored
    # below cron job object,
    h.Allow("aff4:/cron")
    h.Allow("aff4:/cron/*")

    # Hunts and data collected by hunts are publicly available and thus can
    # be queried.
    h.Allow("aff4:/hunts")
    h.Allow("aff4:/hunts/*")

    # ACLs have to be queried to search for proper approvals. As a consequence,
    # any user can query for all approval objects and get a list of all
    # possible reasons. At the moment we assume that it's ok.
    h.Allow("aff4:/ACL")
    h.Allow("aff4:/ACL/*")

    # Querying contents of the client is allowed, as we have to browse VFS
    # filesystem.
    h.Allow(self.CLIENT_URN_PATTERN)
    h.Allow(self.CLIENT_URN_PATTERN + "/*")

    # Namespace for indexes. Client index is stored there and users need to
    # query the index for searching clients.
    h.Allow("aff4:/index")
    h.Allow("aff4:/index/*")

    # Configuration namespace used for reading drivers, python hacks etc. The
    # GUI needs to be able to list these paths.
    h.Allow("aff4:/config")
    h.Allow("aff4:/config/*")

    # We do not allow querying for all flows with empty client id, but we do
    # allow querying for particular flow's children. This is needed, in
    # particular, for cron jobs, whose flows end up in aff4:/flows and we
    # have to query them for children flows.
    # NOTE: Allow(aff4:/flows/*) does not allow querying of aff4:/flows
    #       children. But, on the other hand, it will allow querying for
    #       anything under aff4:/flows/W:SOMEFLOW, for example.
    h.Allow("aff4:/flows/*")

    # Querying the index of filestore objects is allowed since it reveals the
    # clients which have this file.
    h.Allow("aff4:/files/hash/generic/sha256/" + "[a-z0-9]" * 64)

    # Allow everyone to query monitoring data from stats store.
    h.Allow("aff4:/stats_store")
    h.Allow("aff4:/stats_store/*")

    return h

  def RejectWriteAccess(self, unused_subject, unused_token):
    """Write access to data store is forbidden. Use flows instead."""
    raise access_control.UnauthorizedAccess("Write access to data store is "
                                            "forbidden.")

  @stats.Timed("acl_check_time")
  def CheckFlowAccess(self, token, flow_name, client_id=None):
    """Checks access to the given flow.

    Args:
      token: User credentials token.
      flow_name: Name of the flow to check.
      client_id: Client id of the client where the flow is going to be
                 started. Defaults to None.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    client_urn = None
    if client_id:
      client_urn = rdfvalue.ClientURN(client_id)

    if not token:
      raise access_control.UnauthorizedAccess(
          "Must give an authorization token for flow %s" % flow_name)

    # Token must not be expired here.
    token.CheckExpiry()

    # The supervisor may bypass all ACL checks.
    if token.supervisor:
      return True

    flow_cls = flow.GRRFlow.GetPlugin(flow_name)

    # Flows which are not enforced can run all the time.
    if not flow_cls.ACL_ENFORCED:
      return True

    if not client_urn:
      raise access_control.UnauthorizedAccess(
          "Mortals are only allowed to run flows on the client.")

    # This should raise in case of failure.
    return self.UserHasClientApproval(client_urn, token)

  @stats.Timed("acl_check_time")
  def CheckHuntAccess(self, token, hunt_urn):
    """Checks access to the given hunt.

    Args:
      token: User credentials token.
      hunt_urn: URN of the hunt to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking approval for hunt %s, %s", hunt_urn, token)
    if token.supervisor:
      return True

    if not token.username:
      raise access_control.UnauthorizedAccess(
          "Must specify a username for access.",
          subject=hunt_urn)

    if not token.reason:
      raise access_control.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=hunt_urn)

     # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(hunt_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      approval_request = aff4.FACTORY.Open(
          approval_urn, aff4_type="Approval", mode="r",
          token=token, age=aff4.ALL_TIMES)
    except IOError:
      # No Approval found, reject this request.
      raise access_control.UnauthorizedAccess(
          "No approval found for hunt %s." % hunt_urn, subject=hunt_urn)

    if approval_request.CheckAccess(token):
      return True
    else:
      raise access_control.UnauthorizedAccess(
          "Approval %s was rejected." % approval_urn, subject=hunt_urn)

  @stats.Timed("acl_check_time")
  def CheckCronJobAccess(self, token, cron_job_urn):
    """Checks access to a given cron job.

    Args:
      token: User credentials token.
      cron_job_urn: URN of cron job to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking approval for cron job %s, %s", cron_job_urn, token)

    if not token.username:
      raise access_control.UnauthorizedAccess(
          "Must specify a username for access.", subject=cron_job_urn)

    if not token.reason:
      raise access_control.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=cron_job_urn)

     # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(cron_job_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      approval_request = aff4.FACTORY.Open(approval_urn, aff4_type="Approval",
                                           mode="r", token=token,
                                           age=aff4.ALL_TIMES)
    except IOError:
      # No Approval found, reject this request.
      raise access_control.UnauthorizedAccess(
          "No approval found for cron job %s." % cron_job_urn,
          subject=cron_job_urn)

    if approval_request.CheckAccess(token):
      return True
    else:
      raise access_control.UnauthorizedAccess(
          "Approval %s was rejected." % approval_urn, subject=cron_job_urn)

  @stats.Timed("acl_check_time")
  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """The main entry point for checking access to data store resources.

    Args:
      token: An instance of ACLToken security token.

      subjects: The list of subject URNs which the user is requesting access
         to. If any of these fail, the whole request is denied.

      requested_access: A string specifying the desired level of access ("r" for
         read and "w" for write, "q" for query).

    Returns:
       True: If the access is allowed.

    Raises:
       UnauthorizedAccess: If the user is not authorized to perform
       the action on any of the subject URNs.

       ExpiryError: If the token is expired.
    """
    # All accesses need a token.
    if not token:
      raise access_control.UnauthorizedAccess(
          "Must give an authorization token for %s" % subjects,
          requested_access=requested_access)

    if not requested_access:
      raise access_control.UnauthorizedAccess(
          "Must specify requested access type for %s" % subjects)

    if "q" in requested_access and "r" not in requested_access:
      raise access_control.UnauthorizedAccess(
          "Invalid access request: query permissions require read permissions "
          "for %s" % subjects, requested_access=requested_access)

    # Token must not be expired here.
    token.CheckExpiry()

    # The supervisor may bypass all ACL checks.
    if token.supervisor:
      return True

    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)

    # Direct writes are not allowed. Specialised flows (with ACL_ENFORCED=False)
    # have to be used instead.
    access_checkers = {"w": self.write_access_helper.CheckAccess,
                       "r": self.read_access_helper.CheckAccess,
                       "q": self.query_access_helper.CheckAccess}

    for subject in subjects:
      for access in requested_access:
        try:
          access_checkers[access](subject, token)

        except KeyError:
          raise access_control.UnauthorizedAccess(
              "Invalid access requested for %s" % subject, subject=subject,
              requested_access=requested_access)
        except access_control.UnauthorizedAccess as e:
          logging.info("%s access rejected for %s: %s", requested_access,
                       subject, e)
          e.requested_access = requested_access
          raise

    return True

  def UserHasAdminLabel(self, subject, token):
    """Checks whether a user has admin label. Used by CheckAccessHelper."""
    self.CheckUserLabels(token.username, ["admin"], token=token)

  def IsHomeDir(self, subject, token):
    """Checks user access permissions for paths under aff4:/users."""
    h = CheckAccessHelper("IsHomeDir")
    h.Allow("aff4:/users/%s" % token.username)
    h.Allow("aff4:/users/%s/*" % token.username)
    try:
      return h.CheckAccess(subject, token)
    except access_control.UnauthorizedAccess:
      raise access_control.UnauthorizedAccess("User can only access his "
                                              "home directory.",
                                              subject=subject)

  def UserHasClientApproval(self, subject, token):
    """Checks if read access for this client is allowed using the given token.

    Args:
      subject: Subject below the client level which triggered the check.
      token: The token to check with.

    Returns:
      True if the access is allowed.

    Raises:
      UnauthorizedAccess: if the access is rejected.
    """
    client_id, _ = rdfvalue.RDFURN(subject).Split(2)
    client_urn = rdfvalue.ClientURN(client_id)

    logging.debug("Checking client approval for %s, %s", client_urn, token)

    if not token.reason:
      raise access_control.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=client_urn)

    # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_urn.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      token.is_emergency = self.acl_cache.Get(approval_urn)
      return True
    except KeyError:
      try:
        # Retrieve the approval object with superuser privileges so we can check
        # it.
        approval_request = aff4.FACTORY.Open(
            approval_urn, aff4_type="Approval", mode="r",
            token=self.super_token, age=aff4.ALL_TIMES)

        if approval_request.CheckAccess(token):
          # Cache this approval for fast path checking.
          self.acl_cache.Put(approval_urn, token.is_emergency)
          return True

        raise access_control.UnauthorizedAccess(
            "Approval %s was rejected." % approval_urn,
            subject=client_urn)

      except IOError:
        # No Approval found, reject this request.
        raise access_control.UnauthorizedAccess(
            "No approval found for client %s." % client_urn,
            subject=client_urn)
