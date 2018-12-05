#!/usr/bin/env python
"""This module implements User managers and Access control managers.

These are concrete implementations of the classes defined in access_control.py:

AccessControlManager Classes:
  NullAccessControlManager: Gives everyone full access to everything.
  BasicAccessControlManager: Provides basic Admin/Non-Admin distinction based on
    labels.
  FullAccessControlManager: Provides for multiparty authorization.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import fnmatch
import functools
import logging
import re


from builtins import map  # pylint: disable=redefined-builtin

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import compatibility
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import flow
from grr_response_server.aff4_objects import security
from grr_response_server.aff4_objects import users as aff4_users


class LoggedACL(object):
  """A decorator to automatically log result of the ACL check."""

  def __init__(self, access_type):
    self.access_type = access_type

  def __call__(self, func):

    @functools.wraps(func)
    def Decorated(this, token, *args, **kwargs):
      try:
        result = func(this, token, *args, **kwargs)
        if (self.access_type == "data_store_access" and token and
            token.username in aff4_users.GRRUser.SYSTEM_USERS):
          # Logging internal system database access is noisy and useless.
          return result
        if logging.getLogger().isEnabledFor(logging.DEBUG):
          logging.debug(
              u"%s GRANTED by %s to %s%s (%s, %s) with reason: %s",
              utils.SmartUnicode(self.access_type),
              compatibility.GetName(this.__class__.__name__),
              utils.SmartUnicode(token and token.username),
              utils.SmartUnicode(
                  token and token.supervisor and " (supervisor)" or ""),
              utils.SmartUnicode(args), utils.SmartUnicode(kwargs),
              utils.SmartUnicode(token and token.reason))

        return result
      except access_control.UnauthorizedAccess:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
          logging.debug(
              u"%s REJECTED by %s to %s%s (%s, %s) with reason: %s",
              utils.SmartUnicode(self.access_type),
              compatibility.GetName(this.__class__.__name__),
              utils.SmartUnicode(token and token.username),
              utils.SmartUnicode(
                  token and token.supervisor and " (supervisor)" or ""),
              utils.SmartUnicode(args), utils.SmartUnicode(kwargs),
              utils.SmartUnicode(token and token.reason))

        raise

    return Decorated


def ValidateToken(token, targets):
  """Does basic token validation.

  Args:
    token: User's credentials as access_control.ACLToken.
    targets: List of targets that were meant to be accessed by the token. This
      is used for logging purposes only.

  Returns:
    True if token is valid.

  Raises:
    access_control.UnauthorizedAccess: if token is not valid.
    ValueError: if targets list is empty.
  """

  def GetSubjectForError():
    if len(targets) == 1:
      return list(targets)[0]
    else:
      return None

  # All accesses need a token.
  if not token:
    raise access_control.UnauthorizedAccess(
        "Must give an authorization token for %s" % targets,
        subject=GetSubjectForError())

  # Token must not be expired here.
  token.CheckExpiry()

  # Token must have identity
  if not token.username:
    raise access_control.UnauthorizedAccess(
        "Must specify a username for access to %s." % targets,
        subject=GetSubjectForError())

  return True


def ValidateAccessAndSubjects(requested_access, subjects):
  """Does basic requested access validation.

  Args:
    requested_access: String consisting or 'r', 'w' and 'q' characters.
    subjects: A list of subjects that are about to be accessed with a given
      requested_access. Used for logging purposes only.

  Returns:
    True if requested_access is valid.

  Raises:
    access_control.UnauthorizedAccess: if requested_access is not valid.
    ValueError: if subjects list is empty.
  """

  if not requested_access:
    raise access_control.UnauthorizedAccess(
        "Must specify requested access type for %s" % subjects)

  for s in requested_access:
    if s not in "rwq":
      raise ValueError(
          "Invalid access requested for %s: %s" % (subjects, requested_access))

  if "q" in requested_access and "r" not in requested_access:
    raise access_control.UnauthorizedAccess(
        "Invalid access request: query permissions require read permissions "
        "for %s" % subjects,
        requested_access=requested_access)

  return True


def CheckUserForLabels(username, authorized_labels, token=None):
  """Verify that the username has all the authorized_labels set."""
  authorized_labels = set(authorized_labels)

  try:
    user = aff4.FACTORY.Open(
        "aff4:/users/%s" % username, aff4_type=aff4_users.GRRUser, token=token)

    # Only return if all the authorized_labels are found in the user's
    # label list, otherwise raise UnauthorizedAccess.
    if (authorized_labels.intersection(
        user.GetLabelsNames()) == authorized_labels):
      return True
    else:
      raise access_control.UnauthorizedAccess(
          "User %s is missing labels (required: %s)." % (username,
                                                         authorized_labels))
  except IOError:
    raise access_control.UnauthorizedAccess("User %s not found." % username)


def CheckFlowCanBeStartedOnClient(flow_name):
  """Checks if flow can be started on a particular client.

  Only flows with a category can bestarted. Having a category means that the
  flow will be accessible from the UI.

  Args:
    flow_name: Name of the flow to check access for.

  Returns:
    True if flow is externally accessible.
  Raises:
    access_control.UnauthorizedAccess: if flow is not externally accessible.
  """
  flow_cls = flow.GRRFlow.GetPlugin(flow_name)

  if flow_cls.category:
    return True
  else:
    raise access_control.UnauthorizedAccess(
        "Flow %s can't be started on a client by non-suid users." % flow_name)


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
               If this function returns True, the check is considered passed.
               If it raises, the check is considered failed, no other checks
               are made and exception is propagated.
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

      logging.debug(
          u"Datastore access granted to %s on %s by pattern: %s "
          u"with reason: %s (require=%s, require_args=%s, "
          u"require_kwargs=%s, helper_name=%s)",
          utils.SmartUnicode(token.username), utils.SmartUnicode(subject_str),
          utils.SmartUnicode(regex_text), utils.SmartUnicode(token.reason),
          require, require_args, require_kwargs, self.helper_name)
      return True

    logging.warn("Datastore access denied to %s (no matched rules)",
                 subject_str)
    raise access_control.UnauthorizedAccess(
        "Access to %s rejected: (no matched rules)." % subject, subject=subject)


class FullAccessControlManager(access_control.AccessControlManager):
  """Control read/write/query access for multi-party authorization system.

  This access control manager enforces valid identity and a scheme of
  read/write/query access that works with the GRR approval system.
  """

  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  approval_cache_time = 600

  def __init__(self):
    super(FullAccessControlManager, self).__init__()

    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=self.approval_cache_time)
    self.super_token = access_control.ACLToken(username="GRRSystem").SetUID()

    self.helpers = {
        "w": self._CreateWriteAccessHelper(),
        "r": self._CreateReadAccessHelper(),
        "q": self._CreateQueryAccessHelper()
    }

  def _HasAccessToClient(self, subject, token):
    """Checks if user has access to a client under given URN."""
    client_id, _ = rdfvalue.RDFURN(subject).Split(2)
    client_urn = rdf_client.ClientURN(client_id)

    return self.CheckClientAccess(token, client_urn)

  def _UserHasAdminLabel(self, subject, token):
    """Checks whether a user has admin label. Used by CheckAccessHelper."""
    return CheckUserForLabels(token.username, ["admin"], token=token)

  def _IsHomeDir(self, subject, token):
    """Checks user access permissions for paths under aff4:/users."""
    h = CheckAccessHelper("IsHomeDir")
    h.Allow("aff4:/users/%s" % token.username)
    h.Allow("aff4:/users/%s/*" % token.username)
    try:
      return h.CheckAccess(subject, token)
    except access_control.UnauthorizedAccess:
      raise access_control.UnauthorizedAccess(
          "User can only access their "
          "home directory.", subject=subject)

  def _CreateWriteAccessHelper(self):
    """Creates a CheckAccessHelper for controlling write access."""
    h = CheckAccessHelper("write")

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

    # User is allowed to access anything in their home dir.
    h.Allow("aff4:/users/*", self._IsHomeDir)

    # Administrators are allowed to see current set of foreman rules.
    h.Allow("aff4:/foreman", self._UserHasAdminLabel)

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

    # Keyword-based Client index.
    h.Allow("aff4:/client_index")
    h.Allow("aff4:/client_index/*")

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

    # Namespace for audit data.
    h.Allow("aff4:/audit")
    h.Allow("aff4:/audit/*")
    h.Allow("aff4:/audit/logs")
    h.Allow("aff4:/audit/logs/*")

    # Namespace for clients.
    h.Allow(self.CLIENT_URN_PATTERN)
    h.Allow(self.CLIENT_URN_PATTERN + "/*", self._HasAccessToClient)

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

    # User is allowed to do anything in their home dir.
    h.Allow("aff4:/users/*", self._IsHomeDir)

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

    # Namespace for audit data. Required to display usage statistics.
    h.Allow("aff4:/audit/logs")
    h.Allow("aff4:/audit/logs/*")

    return h

  def _CheckAccessWithHelpers(self, token, subjects, requested_access):
    for subject in subjects:
      for access in requested_access:
        try:
          self.helpers[access].CheckAccess(subject, token)
        except access_control.UnauthorizedAccess as e:
          e.requested_access = requested_access
          raise

    return True

  def _CheckApprovalsForTokenWithoutReason(self, token, target):
    approval_root_urn = aff4.ROOT_URN.Add("ACL").Add(target.Path()).Add(
        token.username)

    try:
      cached_token = self.acl_cache.Get(approval_root_urn)
      stats_collector_instance.Get().IncrementCounter(
          "approval_searches", fields=["without_reason", "cache"])

      token.is_emergency = cached_token.is_emergency
      token.reason = cached_token.reason

      return True
    except KeyError:
      stats_collector_instance.Get().IncrementCounter(
          "approval_searches", fields=["without_reason", "data_store"])

      approved_token = security.Approval.GetApprovalForObject(
          target, token=token)
      token.reason = approved_token.reason
      token.is_emergency = approved_token.is_emergency

      self.acl_cache.Put(approval_root_urn, approved_token)

      return True

  def _CheckApprovals(self, token, target):
    return self._CheckApprovalsForTokenWithoutReason(token, target)

  @LoggedACL("client_access")
  @stats_utils.Timed("acl_check_time", fields=["client_access"])
  def CheckClientAccess(self, token, client_urn):
    if not client_urn:
      raise ValueError("Client urn can't be empty.")
    client_urn = rdf_client.ClientURN(client_urn)

    return ValidateToken(
        token, [client_urn]) and (token.supervisor or
                                  self._CheckApprovals(token, client_urn))

  @LoggedACL("hunt_access")
  @stats_utils.Timed("acl_check_time", fields=["hunt_access"])
  def CheckHuntAccess(self, token, hunt_urn):
    if not hunt_urn:
      raise ValueError("Hunt urn can't be empty.")
    hunt_urn = rdfvalue.RDFURN(hunt_urn)

    return ValidateToken(token,
                         [hunt_urn]) and (token.supervisor or
                                          self._CheckApprovals(token, hunt_urn))

  @LoggedACL("cron_job_access")
  @stats_utils.Timed("acl_check_time", fields=["cron_job_access"])
  def CheckCronJobAccess(self, token, cron_job_urn):
    if not cron_job_urn:
      raise ValueError("Cron job urn can't be empty.")
    cron_job_urn = rdfvalue.RDFURN(cron_job_urn)

    return ValidateToken(
        token, [cron_job_urn]) and (token.supervisor or
                                    self._CheckApprovals(token, cron_job_urn))

  @LoggedACL("can_start_flow")
  @stats_utils.Timed("acl_check_time", fields=["can_start_flow"])
  def CheckIfCanStartFlow(self, token, flow_name):
    if not flow_name:
      raise ValueError("Flow name can't be empty.")

    return ValidateToken(
        token, [flow_name]) and (token.supervisor or
                                 CheckFlowCanBeStartedOnClient(flow_name))

  @LoggedACL("data_store_access")
  @stats_utils.Timed("acl_check_time", fields=["data_store_access"])
  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """Allow all access if token and requested access are valid."""
    if any(not x for x in subjects):
      raise ValueError("Subjects list can't contain empty URNs.")
    subjects = list(map(rdfvalue.RDFURN, subjects))

    return (ValidateAccessAndSubjects(requested_access, subjects) and
            ValidateToken(token, subjects) and
            (token.supervisor or
             self._CheckAccessWithHelpers(token, subjects, requested_access)))
