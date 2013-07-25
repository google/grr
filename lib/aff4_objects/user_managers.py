#!/usr/bin/env python
"""This module implements User managers and Access control managers.

These are concrete implementations of the classes defined in access_control.py:

AccessControlManager Classes:
  NullAccessControlManager: Gives everyone full access to everything.
  TestAccessControlManager: In memory, very basic functionality for tests.
  FullAccessControlManager: Provides for multiparty authorization.
  BasicAccessControlManager: Provides basic Admin/Non-Admin funcionality.

UserManager Classes:
  DatastoreUserManager: Labels are managed inside aff4:/users/<user>/labels
    inside the datstore.
  ConfigBasedUserManager: Users and labels are managed in the User section of
    the config file.
"""


import crypt
import fnmatch
import logging
import random
import re
import string

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr


class DataStoreUserManager(access_control.BaseUserManager):
  """DataStore based user manager.

  This only implements the bare minimum to support the datastore labels. It is
  assumed that the actual users are managed outside of this mechanism.

  Storage is done via the LABELS attribute of the GRRUser object at:
    aff4:/users/<username>/labels
  """

  def __init__(self, *args, **kwargs):
    super(DataStoreUserManager, self).__init__(*args, **kwargs)
    self.user_label_cache = utils.AgeBasedCache(
        max_size=1000, max_age=config_lib.CONFIG["ACL.cache_age"])
    self.super_token = access_control.ACLToken()
    self.super_token.supervisor = True

  def GetUserLabels(self, username):
    """Verify that the username has the authorized_labels set.

    Args:
       username: The name of the user.

    Returns:
      True if the user has one of the authorized_labels set.
    """
    try:
      # Labels are kept at a different location than the main user object so the
      # user can not modify them themselves.
      label_urn = rdfvalue.RDFURN("aff4:/users/").Add(username).Add("labels")
      labels = self.user_label_cache.Get(label_urn)
    except KeyError:
      fd = aff4.FACTORY.Open(label_urn, mode="r", token=self.super_token)
      labels = fd.Get(fd.Schema.LABEL, [])

      # Cache labels for a short time.
      if labels:
        self.user_label_cache.Put(label_urn, labels)
    return labels

  def SetUserLabels(self, username, labels):
    """Overwrite the current set of labels with a list of labels.

    Args:
      username: User to add the labels to.
      labels: List of additional labels to add to the user.
    """
    labels = set(l.lower() for l in labels)
    label_urn = rdfvalue.RDFURN("aff4:/users/").Add(username).Add("labels")
    u = aff4.FACTORY.Open(label_urn, mode="rw", token=self.super_token)
    label_obj = u.Schema.LABEL()
    for label in labels:
      label_obj.Append(label)
    u.Set(label_obj)
    u.Close()
    self.user_label_cache.Put(label_urn, labels)


class ConfigBasedUserManager(access_control.BaseUserManager):
  """User manager that uses the Users.authentication entry of the config file.

  This reads all user labels out of the configuration file which are in the
  Users.authentication entry. Each user has a set of labels associated with it.

  e.g.
  Users.authentication = |
    admin:GfiE1JZd9GJVs:admin,label2
    joe:Up9jbksBgt/W.:label1,label2

  """

  def __init__(self, *args, **kwargs):
    super(ConfigBasedUserManager, self).__init__(*args, **kwargs)
    self.UpdateCache()

  def UpdateCache(self):
    self._user_cache = self.ReadUsersFromConfig()

  def ReadUsersFromConfig(self):
    """Return the users from the config file as a dict."""
    results = {}
    users = config_lib.CONFIG.Get("Users.authentication", default="")
    entries = [user for user in users.split("\n") if user]
    for entry in entries:
      try:
        username, hash_val, labels = entry.split(":")
      except ValueError:
        username, hash_val = entry.rstrip(":").split(":")
        labels = ""
      labels = [l.strip().lower() for l in labels.strip().split(",")]
      results[username] = {"hash": hash_val, "labels": labels}
    return results

  def CheckUserAuth(self, username, auth_obj):
    """Check a hash against the user database."""
    crypt_hash = self._user_cache[username]["hash"]
    salt = crypt_hash[:2]
    return crypt.crypt(auth_obj.user_provided_hash, salt) == crypt_hash

  def FlushCache(self):
    user_strings = []
    for user in self._user_cache:
      hash_str = self._user_cache[user]["hash"]
      labels = ",".join(self._user_cache[user]["labels"])
      user_strings.append("%s:%s:%s" % (user, hash_str, labels))

    config_lib.CONFIG.Set("Users.authentication", "\n".join(user_strings))
    config_lib.CONFIG.Write()

  def AddUser(self, username, password=None, admin=True, labels=None):
    """Add a user.

    Args:
      username: User name to create.
      password: Password to set.
      admin: Should the user be made an admin.
      labels: List of additional labels to add to the user.

    Raises:
      RuntimeError: On invalid arguments.
    """
    self.UpdateCache()

    pwhash = None
    if password:
      # Note: As of python 3.3. there is a function to do this, but we do our
      # own for backwards compatibility.
      valid_salt_chars = string.ascii_letters + string.digits + "./"
      salt = "".join(random.choice(valid_salt_chars) for i in range(2))
      pwhash = crypt.crypt(password, salt)
    elif username not in self._user_cache:
      raise RuntimeError("Can't create user without password")

    if labels or admin:
      # Labels will be added to config. On load of the Users section when the
      # Admin UI starts, these labels will be set on the users.
      labels = set(labels or [])
      if admin:
        labels.add("admin")
      labels = sorted(list(labels))

    user_dict = self._user_cache.setdefault(username, {})
    if pwhash:
      user_dict["hash"] = pwhash
    if labels:
      user_dict["labels"] = labels
    self.FlushCache()

  def GetUserLabels(self, username):
    """Get a list of labels for a user."""
    try:
      labels = self._user_cache[username]["labels"]
      return labels
    except KeyError:
      raise access_control.InvalidUserError("No such user %s" % username)

  def SetRaw(self, username, hash_str, labels):
    d = self._user_cache.setdefault(username, {})
    d["hash"] = hash_str
    d["labels"] = labels


class BasicAccessControlManager(access_control.BaseAccessControlManager):
  """Basic ACL manager that uses the config file for user management."""
  user_manager_cls = ConfigBasedUserManager

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


class NullAccessControlManager(access_control.BaseAccessControlManager):
  """An ACL manager which does not enforce any ACLs."""

  user_manager_cls = DataStoreUserManager

  # pylint: disable=unused-argument
  def CheckHuntAccess(self, token, hunt_urn):
    """Allow all access."""
    return True

  def CheckFlowAccess(self, token, flow_name, client_id=None):
    """Allow all access."""
    return True

  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """Allow all access."""
    return True

  def CheckUserLabels(self, username, authorized_labels):
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
      _, regex, require, require_args, require_kwargs = check_tuple

      match = regex.match(subject_str)
      if not match:
        continue

      if require:
        # If require() fails, it raises access_control.UnauthorizedAccess.
        require(subject, token, *require_args, **require_kwargs)

      logging.debug("Allowing access to %s by pattern: %s "
                    "(require=%s, require_args=%s, require_kwargs=%s, "
                    "helper_name=%s)",
                    subject_str, regex, require, require_args, require_kwargs,
                    self.helper_name)
      return True

    logging.debug("Rejecting access to %s (no matched rules)", subject_str)
    raise access_control.UnauthorizedAccess(
        "Access to %s rejected: (no matched rules)." % subject, subject=subject)


class FullAccessControlManager(access_control.BaseAccessControlManager):
  """An access control manager that handles multi-party authorization.

  Write access to the data store is forbidden. Data store read- and query-access
  policies are defined in _CreateReadAccessHelper and _CreateQueryAccessHelper
  functions. Please refer to these functions to review or modify GRR's data
  store access policies.
  """

  user_manager_cls = DataStoreUserManager

  CLIENT_URN_PATTERN = "aff4:/C." + "[0-9a-fA-F]" * 16

  def __init__(self):
    self.client_id_re = aff4_grr.VFSGRRClient.CLIENT_ID_RE
    self.acl_cache = utils.AgeBasedCache(
        max_size=10000, max_age=config_lib.CONFIG["ACL.cache_age"])

    self.flow_cache = utils.FastStore(max_size=10000)
    self.super_token = access_control.ACLToken()
    self.super_token.supervisor = True

    self.read_access_helper = self._CreateReadAccessHelper()
    self.query_access_helper = self._CreateQueryAccessHelper()

    super(FullAccessControlManager, self).__init__()

  def _CreateReadAccessHelper(self):
    """Creates a CheckAccessHelper for controlling read access.

    This function and _CreateQueryAccessHelper essentially define GRR's ACL
    policy. Please refer to these 2 functions to either review or modify
    GRR's ACLs.

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

    # Namespace for clients.
    h.Allow(self.CLIENT_URN_PATTERN)
    h.Allow(self.CLIENT_URN_PATTERN + "/*", self.UserHasClientApproval)

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

    flow_cls = flow.GRRFlow.NewPlugin(flow_name)

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
    access_checkers = {"w": self.RejectWriteAccess,
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
                       subject, e.message)
          e.requested_access = requested_access
          raise

    return True

  def UserHasAdminLabel(self, subject, token):
    """Checks whether a user has admin label. Used by CheckAccessHelper."""
    if not self.CheckUserLabels(token.username, ["admin"]):
      raise access_control.UnauthorizedAccess("User has to have 'admin' label.",
                                              subject=subject)

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
