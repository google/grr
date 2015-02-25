#!/usr/bin/env python
"""This module implements User managers and Access control managers.

These are concrete implementations of the classes defined in access_control.py:

AccessControlManager Classes:
  NullAccessControlManager: Gives everyone full access to everything.
  BasicAccessControlManager: Provides basic Admin/Non-Admin distinction based on
    labels.
  FullAccessControlManager: Provides for multiparty authorization.
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

      logging.debug("Datastore access granted to %s on %s by pattern: %s "
                    "(require=%s, require_args=%s, require_kwargs=%s, "
                    "helper_name=%s)",
                    utils.SmartStr(token.username), subject_str, regex_text,
                    require, require_args, require_kwargs, self.helper_name)
      return True

    logging.warn("Datastore access denied to %s (no matched rules)",
                 subject_str)
    raise access_control.UnauthorizedAccess(
        "Access to %s rejected: (no matched rules)." % subject, subject=subject)


class NullAccessControlManager(access_control.AccessControlManager):
  """An ACL manager which does not enforce any ACLs or check user privilege."""

  # pylint: disable=unused-argument
  def CheckUserLabels(self, username, authorized_labels, token=None):
    """Allow all access."""
    return True

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


class BasicAccessControlManager(NullAccessControlManager):
  """Basic ACL manager that uses the config file for user management.

  This access control manager enforces valid identity but that is all.  Users
  are allowed to read/write/query everywhere.
  """

  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  def __init__(self):
    self.client_id_re = aff4_grr.VFSGRRClient.CLIENT_ID_RE
    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=config_lib.CONFIG["ACL.cache_age"])

    self.flow_cache = utils.FastStore(max_size=10000)
    self.super_token = access_control.ACLToken(username="GRRSystem").SetUID()

    self.write_access_helper = self._CreateWriteAccessHelper()
    self.read_access_helper = self._CreateReadAccessHelper()
    self.query_access_helper = self._CreateQueryAccessHelper()

    super(BasicAccessControlManager, self).__init__()

  def CheckUserLabels(self, username, authorized_labels, token=None):
    """Verify that the username has all the authorized_labels set."""
    authorized_labels = set(authorized_labels)

    try:
      user = aff4.FACTORY.Open("aff4:/users/%s" % username, aff4_type="GRRUser",
                               token=token)

      # Only return if all the authorized_labels are found in the user's
      # label list, otherwise raise UnauthorizedAccess.
      if (authorized_labels.intersection(
          user.GetLabelsNames()) == authorized_labels):
        return
      raise access_control.UnauthorizedAccess(
          "User %s is missing labels (required: %s)." % (username,
                                                         authorized_labels))
    except IOError:
      raise access_control.UnauthorizedAccess("User %s not found." % username)

  @stats.Timed("acl_check_time")
  def CheckFlowAccess(self, token, flow_name, client_id=None):
    client_urn = None
    if client_id:
      client_urn = rdfvalue.ClientURN(client_id)

    self.ValidateToken(token, client_urn)

    flow_cls = flow.GRRFlow.GetPlugin(flow_name)

    # Flows which are not enforced can run all the time.
    if not flow_cls.ACL_ENFORCED:
      logging.debug("ACL access granted by ACL_ENFORCED bypass for %s.",
                    flow_name)
      return True

    return self.CheckACL(token, client_urn)

  @stats.Timed("acl_check_time")
  def CheckHuntAccess(self, token, hunt_urn):
    self.ValidateToken(token, hunt_urn)
    return self.CheckACL(token, hunt_urn)

  @stats.Timed("acl_check_time")
  def CheckCronJobAccess(self, token, cron_job_urn):
    self.ValidateToken(token, cron_job_urn)
    return self.CheckACL(token, cron_job_urn)

  def CheckClientAccess(self, subject, token):
    client_id, _ = rdfvalue.RDFURN(subject).Split(2)
    client_urn = rdfvalue.ClientURN(client_id)
    return self.CheckACL(token, client_urn)

  @stats.Timed("acl_check_time")
  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """Allow all access."""

    self.ValidateToken(token, subjects)
    self.ValidateRequestedAccess(requested_access, subjects)

    # The supervisor may bypass all ACL checks.
    if token.supervisor:
      logging.debug("Datastore access granted to %s on %s. Mode: %s "
                    "Supervisor: %s", utils.SmartStr(token.username), subjects,
                    requested_access, token.supervisor)
      return True

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
          logging.warn("Datastore access denied to %s on %s. Mode: %s "
                       "Error: %s", utils.SmartStr(token.username), subjects,
                       requested_access, e)
          e.requested_access = requested_access
          raise

    return True

  def ValidateToken(self, token, target):
    """Validate Basic Token Issues."""
    # All accesses need a token.
    if not token:
      raise access_control.UnauthorizedAccess(
          "Must give an authorization token for %s" % target, subject=target
          )

    # Token must not be expired here.
    token.CheckExpiry()

    # Token must have identity
    if not token.username:
      raise access_control.UnauthorizedAccess(
          "Must specify a username for access to %s." % target, subject=target
          )

  def ValidateRequestedAccess(self, requested_access, subjects):
    if not requested_access:
      raise access_control.UnauthorizedAccess(
          "Must specify requested access type for %s" % subjects)

    if "q" in requested_access and "r" not in requested_access:
      raise access_control.UnauthorizedAccess(
          "Invalid access request: query permissions require read permissions "
          "for %s" % subjects, requested_access=requested_access)

  def _CreateWriteAccessHelper(self):
    """Creates a CheckAccessHelper for controlling write access."""
    h = CheckAccessHelper("write")

    h.Allow("*")

    return h

  def _CreateReadAccessHelper(self):
    """Creates a CheckAccessHelper for controlling read access.

    This function and _CreateQueryAccessHelper essentially define GRR's ACL
    policy. Please refer to these 2 functions to either review or modify
    GRR's ACLs.

    Returns:
      CheckAccessHelper for controlling read access.
    """
    h = CheckAccessHelper("read")

    h.Allow("*")

    return h

  def _CreateQueryAccessHelper(self):
    """Creates a CheckAccessHelper for controlling query access.

    This function and _CreateReadAccessHelper essentially define GRR's ACL
    policy. Please refer to these 2 functions to either review or modify
    GRR's ACLs.

    Returns:
      CheckAccessHelper for controlling query access.
    """
    h = CheckAccessHelper("query")

    h.Allow("*")

    return h

  def CheckACL(self, token, target):
    logging.debug("ACL access granted to %s on %s. Supervisor: %s",
                  utils.SmartStr(token.username), target, token.supervisor)
    return True


class FullAccessControlManager(BasicAccessControlManager):
  """Control read/write/query access for multi-party authorization system.

  This access control manager enforces valid identity and a scheme of
  read/write/query access that works with the GRR approval system.
  """

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
    h.Allow(self.CLIENT_URN_PATTERN + "/*", self.CheckClientAccess)

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

    # Allow everyone to query the artifact store.
    h.Allow("aff4:/artifact_store")
    h.Allow("aff4:/artifact_store/*")

    # Allow everyone to query monitoring data from stats store.
    h.Allow("aff4:/stats_store")
    h.Allow("aff4:/stats_store/*")

    # Users are allowed to query the artifact store.
    h.Allow("aff4:/artifact_store")
    h.Allow("aff4:/artifact_store/*")

    return h

  def CheckACL(self, token, target):
    # The supervisor may bypass all ACL checks.
    if token.supervisor:
      logging.debug("ACL access granted to %s on %s. Supervisor: %s",
                    utils.SmartStr(token.username), target, token.supervisor)
      return True

    # Target may be None for flows not specifying a client.
    # Only aff4.GRRUser.SYSTEM_USERS can run these flows.
    if not target:
      if token.username not in aff4.GRRUser.SYSTEM_USERS:
        raise access_control.UnauthorizedAccess(
            "ACL access denied for flow without client_urn for %s",
            token.username)
      return True

    if not token.reason:
      raise access_control.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=target)

    # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(target.Path()).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      token.is_emergency = self.acl_cache.Get(approval_urn)
      logging.debug("ACL access granted to %s on %s. Supervisor: %s",
                    utils.SmartStr(token.username), target, token.supervisor)
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
          logging.debug(
              "ACL access granted to %s on %s. Supervisor: %s",
              utils.SmartStr(token.username), target, token.supervisor)
          return True

        raise access_control.UnauthorizedAccess(
            "Approval %s was rejected." % approval_urn,
            subject=target)

      except IOError:
        # No Approval found, reject this request.
        raise access_control.UnauthorizedAccess(
            "No approval found for %s." % target,
            subject=target)
