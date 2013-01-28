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

"""The access control classes and user management classes for the data_store.

An AccessControlManager has the following responsibilities:
  - Authorize users access to resources based on a set of internal rules

A UserManager class has the following responsibilities :
  - Check if a user has a particular label
  - Manage add/update/set password for users (optional)
  - Validate a user authentication event (optional)


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



import ConfigParser
import crypt
import logging
import random
import re
import string


from grr.client import conf as flags

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils

from grr.lib.aff4_objects import aff4_grr

flags.DEFINE_integer("acl_cache_age", 600, "The number of seconds "
                     "approval objects live in the cache.")

flags.DEFINE_string("security_manager", "NullAccessControlManager",
                    "The ACL manager for controlling access to data.")

FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG


class Error(Exception):
  """Access control errors."""


class NotSupportedError(Error):
  """Used when a function isn't supported by a given Access Control Mananger."""


class InvalidUserError(Error):
  """Used when an action is attempted on an invalid user."""


class BaseUserManager(object):
  """User management class.

  Provides basic functionality for managing users.

  Note: This class is only meant for simple implementations. In a significant
    GRR implementation it is expected that user management will be
    handled outside of GRR using an SSO or directory service implementation.
  """

  __metaclass__ = registry.MetaclassRegistry

  def CheckUserLabels(self, username, authorized_labels):
    """Verify that the username has one of the authorized_labels set.

    Args:
       username: The name of the user.
       authorized_labels: A list of string labels.

    Returns:
      True if the user has one of the authorized_labels set.

    Raises:
      RuntimeError: On bad parameters.
    """
    if not username or not authorized_labels:
      raise RuntimeError("Bad CheckUserLabels call.")
    for label in self.GetUserLabels(username):
      if label in authorized_labels:
        return True
    return False

  def GetUserLabels(self, username):
    """Get a list of the labels assigned to user."""

  def AddUserLabels(self, username, labels):
    """Add the labels to the specified user."""
    self.SetUserLabels(username, self.GetUserLabels(username) + labels)

  def SetUserLabels(self, username, labels):
    """Overwrite the current set of labels with a list of labels."""

  def MakeUserAdmin(self, username):
    """Shortcut to add the Admin label to a specific user."""
    self.AddUserLabels(username, ["admin"])

  # pylint: disable=unused-argument
  def AddUser(self, username, password=None, admin=True, labels=None,
              update=False):
    """Add a user.

    Args:
      username: User name to create.
      password: Password to set.
      admin: Should the user be made an admin.
      labels: List of additional labels to add to the user.
      update: Are we creating a new user (overwrite if exists) or updating one.

    Raises:
      RuntimeError: On invalid arguments.
      NotSupportedError: If unimplemented.
    """
    raise NotSupportedError("AddUser not supported by %s" %
                            self.__class__.__name__)

  def UpdateUser(self, username, password=None, admin=True, labels=None):
    """Update the properties of an existing user."""
    self.AddUser(username, password=password, admin=admin, labels=labels,
                 update=True)

  def CheckUserAuth(self, username, auth_obj):
    """Update the properties of an existing user."""
    raise NotSupportedError("UpdateUser not supported by %s" %
                            self.__class__.__name__)

  # pylint: enable=unused-argument


class DataStoreUserManager(BaseUserManager):
  """DataStore based user manager.

  This only implements the bare minimum to support the datastore labels. It is
  assumed that the actual users are managed outside of this mechanism.

  Storage is done via the LABELS attribute of the GRRUser object at:
    aff4:/users/<username>/labels
  """

  def __init__(self, *args, **kwargs):
    super(DataStoreUserManager, self).__init__(*args, **kwargs)
    self.user_label_cache = utils.AgeBasedCache(max_size=1000,
                                                max_age=FLAGS.acl_cache_age)
    self.super_token = data_store.ACLToken()
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


class ConfigBasedUserManager(BaseUserManager):
  """User manager that uses the [Users] section of the config file.

  This reads all user labels out of the configuration file which has a section
  [Users]. Each user has a set of labels associated with it.

  e.g.
  [Users]
  admin = GfiE1JZd9GJVs:admin,label2
  joe = Up9jbksBgt/W.:label1,label2
  """

  def __init__(self, *args, **kwargs):
    super(ConfigBasedUserManager, self).__init__(*args, **kwargs)
    self._user_cache = self.ReadUsersFromConfig()

  def ReadUsersFromConfig(self):
    """Return the users from the config file as a dict."""
    results = {}
    if not CONFIG.has_section("Users"):
      return {}
    for username, data_str in CONFIG.items("Users"):
      try:
        hash_val, labels = data_str.strip().split(":", 1)
      except ValueError:
        hash_val = data_str.rstrip(":")
        labels = ""
      labels = [l.strip().lower() for l in labels.strip().split(",")]
      results[username] = {"hash": hash_val, "labels": labels}
    return results

  def CheckUserAuth(self, username, auth_obj):
    """Check a hash against the user database."""
    crypt_hash = self._user_cache[username]["hash"]
    salt = crypt_hash[:2]
    return crypt.crypt(auth_obj.user_provided_hash, salt) == crypt_hash

  def AddUser(self, username, password=None, admin=True, labels=None,
              update=False):
    """Add a user.

    Args:
      username: User name to create.
      password: Password to set.
      admin: Should the user be made an admin.
      labels: List of additional labels to add to the user.
      update: Are we creating a new user (overwrite if exists) or updating one.

    Raises:
      RuntimeError: On invalid arguments.
    """
    if not CONFIG.has_section("Users"):
      CONFIG.add_section("Users")

    pwhash, label_str = None, ""
    if update:
      # Get the current values.
      try:
        pwhash, label_str = CONFIG.get("Users", username).split(":", 1)
      except ConfigParser.NoOptionError:
        pass

    if password:
      # Note: As of python 3.3. there is a function to do this, but we do our
      # own for backwards compatibility.
      valid_salt_chars = string.ascii_letters + string.digits + "./"
      salt = "".join(random.choice(valid_salt_chars) for i in range(2))
      pwhash = crypt.crypt(password, salt)
    elif not update:
      raise RuntimeError("Can't create user without password")

    if labels:
      # Labels will be added to config. On load of the Users section when the
      # Admin UI starts, these labels will be set on the users.
      labels = labels or []
      labels = set(labels)
      if admin:
        labels.add("admin")
      label_str = ",".join(labels)

    CONFIG.set("Users", username, "%s:%s" % (pwhash, label_str))
    CONFIG.WriteConfig()

  def GetUserLabels(self, username):
    """Get a list of labels for a user."""
    try:
      labels = self._user_cache[username]["labels"]
      return labels
    except KeyError:
      raise InvalidUserError("No such user %s" % username)


class BaseAccessControlManager(object):
  """A class for managing access to data resources.

  This class is responsible for determining which users have access to each
  resource.

  By default it delegates some of this functionality to a UserManager class
  which takes care of label management and user management components.
  """

  __metaclass__ = registry.MetaclassRegistry

  user_manager_cls = BaseUserManager

  def __init__(self, user_manager_cls=None):
    """Init.

    Args:
      user_manager_cls: Class to use for managing users.
    """
    if user_manager_cls is None and self.user_manager_cls:
      self.user_manager = self.user_manager_cls()
    elif user_manager_cls:
      self.user_manager = user_manager_cls()

  def CheckAccess(self, token, subjects, requested_access="r"):
    """The main entry point for checking access to resources.

    Args:
      token: An instance of data_store.ACLToken security token.

      subjects: The list of subject URNs which the user is requesting access
         to. If any of these fail, the whole request is denied.

      requested_access: A string specifying the desired level of access ("r" for
         read and "w" for write).

    Raises:
       UnauthorizedAccess: If the user is not authorized to perform the action
       on any of the subject URNs.
    """
    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)

  def CheckUserLabels(self, username, authorized_labels):
    """Verify that the username has the authorized_labels set."""
    return self.user_manager.CheckUserLabels(username, authorized_labels)


class BasicAccessControlManager(BaseAccessControlManager):
  """Basic ACL manager that uses the config file for user management."""
  user_manager_cls = ConfigBasedUserManager


class NullAccessControlManager(BaseAccessControlManager):
  """An ACL manager which does not enforce any ACLs."""

  user_manager_cls = DataStoreUserManager

  # pylint: disable=unused-argument
  def CheckAccess(self, token, subjects, requested_access="r"):
    """Allow all access."""
    return True

  def CheckUserLabels(self, username, authorized_labels):
    """Allow all access."""
    return True
  # pylint: enable=unused-argument


class FullAccessControlManager(BaseAccessControlManager):
  """An access control manager that handles multi-party authorization."""

  user_manager_cls = DataStoreUserManager

  def __init__(self):
    self.client_id_re = aff4_grr.VFSGRRClient.CLIENT_ID_RE
    self.blob_re = re.compile(r"^[0-9a-f]{64}$")
    self.acl_cache = utils.AgeBasedCache(max_size=10000,
                                         max_age=FLAGS.acl_cache_age)
    self.flow_cache = utils.FastStore(max_size=10000)
    self.super_token = data_store.ACLToken()
    self.super_token.supervisor = True

    super(FullAccessControlManager, self).__init__()

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

       data_store.ExpiryError: If the token is expired.
    """
    # Token must not be expired here.
    if token:
      token.CheckExpiry()

    # The supervisor may bypass all ACL checks.
    if token and token.supervisor:
      return True

    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)

    # Execute access applies to flows only.
    if "x" in requested_access:
      for subject in subjects:
        namespace, _ = subject.Split(2)
        if namespace == "hunts":
          check_result = self.CheckHuntAccess(
              subject, token, requested_access)
        else:
          check_result = self.CheckFlowAccess(
              subject, token, requested_access)

        if not check_result:
          raise data_store.UnauthorizedAccess(
              "Execution of flow %s rejected." % subject,
              subject=subject, requested_access=requested_access)

    else:
      # Check each subject in turn. If any subject is rejected the entire
      # request is rejected.
      for subject in subjects:
        check_result = self.CheckSubject(subject, token, requested_access)
        if not check_result:
          raise data_store.UnauthorizedAccess(
              "Access denied for %s (%s)" % (subject, requested_access),
              subject=subject, requested_access=requested_access)

    return True

  def CheckSubject(self, subject, token, requested_access):
    """Checks access for just one subject.

    Args:
      subject: The subject to check - Can be an RDFURN or string.
      token: The token to check with.
      requested_access: The type of access requested (can be "r", "w", "x", "q")

    Returns:
      True if the access is allowed.

    Raises:
      UnauthorizedAccess: if the access is rejected.
    """
    # The supervisor may bypass all ACL checks.
    if token and token.supervisor:
      return True

    subject = rdfvalue.RDFURN(subject)
    namespace, path = subject.Split(2)
    # Check for default namespaces.
    if self.CheckWhiteList(namespace, path, requested_access):
      return True

    # Starting from here, all accesses need a token.
    if not token:
      raise data_store.UnauthorizedAccess(
          "Must give an authorization token for %s" % subject,
          subject=namespace, requested_access=requested_access)

    # This is a request into a client namespace, requires approval.
    if self.client_id_re.match(namespace):
      # User has no approval to the client name space - Reject.
      if not self.CheckClientApproval(namespace, token, requested_access):
        return False

      # Users are not allowed to write into the flows of a client - This can
      # lead to arbitrary code exec (since flow pickles run on workers).
      if path.startswith("flows/") and "w" in requested_access:
        return False
      else:
        # User has approval for the client and does not want to modify flows.
        return True

    # This is a request into hunt object, check it accordingly
    if namespace == "hunts":
      return self.CheckHuntAccess(subject, token, requested_access)

    # Foreman is only accessible by admins.
    if namespace == "foreman":
      return self.CheckUserLabels(token.username, ["admin"])

    # Anyone should be able to access their own user record.
    if namespace == "users" and path == token.username:
      return True

    # Anyone should be able to read their own labels but not write to them.
    if (namespace == "users" and
        path == token.username + "/labels" and
        requested_access == "r"):
      return True

    # Tasks live in their own URN scheme
    if subject.scheme == "task":
      session_id = namespace

      # This allows access to queued tasks for approved clients.
      if self.client_id_re.match(session_id):
        return self.CheckClientApproval(session_id, token, requested_access)

      # This provides access to flow objects for approved clients.
      try:
        client_id = self.flow_cache.Get(session_id)

        if client_id in ["Invalid", "Hunt"]:
          return True

        # Check for write access to the client id itself.
        return self.CheckClientApproval(client_id, token, requested_access)

      except KeyError:
        try:
          aff4.FACTORY.Open(session_id, token=self.super_token)

          # If we reach this point, we are opening a hunt object which should
          # be allowed.
          self.flow_cache.Put(session_id, "Hunt")
          return True
        except (IOError, flow.FlowError):
          pass

        try:
          aff4_flow = aff4.FACTORY.Open(session_id, required_type="GRRFlow",
                                        token=self.super_token)
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
        if self.CheckClientApproval(client_id, token, requested_access):
          # The user has access to the client, pre-populate the flow cache. Even
          # though this is one more roundtrip we can save a lot of round trips
          # by having the cache pre-populated here.
          fd = aff4.FACTORY.Open(client_id, mode="r", token=self.super_token,
                                 age=aff4.ALL_TIMES)
          for client_flow_urn in fd.GetValuesForAttribute(fd.Schema.FLOW):
            client_session_id = client_flow_urn.Basename()
            self.flow_cache.Put(client_session_id, client_id)

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
      requested_access: The type of access requested (can be "r", "w", "x", "q")

    Returns:
      True if the access is allowed, False otherwise.
    """

    # The ROOT_URN is always allowed.
    if not namespace:
      return True

    # Querying is not allowed for the blob namespace. Blobs are stored by hashes
    # as filename. If the user already knows the hash, they can access the blob,
    # however they must not be allowed to query for hashes. Users are not
    # allowed to write to blobs either - so they must only use "r".
    if namespace == "blobs" and self.AccessLowerThan(requested_access, "r"):
      return True

    # The fingerprint namespace typically points to blobs. As such, it follows
    # the same rules.
    if namespace == "FP" and self.AccessLowerThan(requested_access, "r"):
      return True

    # Anyone can open the users container so they can list all the users.
    if namespace == "users" and not path:
      return True

    # Anyone can read the ACL data base.
    if namespace == "ACL" and self.AccessLowerThan(requested_access, "rq"):
      return True

    # Anyone can read stats.
    stat_namespaces = ["OSBreakDown", "GRRVersionBreakDown", "LastAccessStats",
                       "ClientStatsCronJob"]
    if namespace in stat_namespaces and self.AccessLowerThan(
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

    # Anyone can read the GRR configuration space.
    if namespace == "config" and "r" in requested_access:
      return True

    return False

  def CheckClientApproval(self, client_id, token, requested_access):
    """Checks if access for this client is allowed using the given token.

    Args:
      client_id: The client to check - Can be an RDFURN or string.
      token: The token to check with.
      requested_access: The type of access requested (can be "r", "w", "x", "q")

    Returns:
      True if the access is allowed.

    Raises:
      UnauthorizedAccess: if the access is rejected.
    """
    logging.debug("Checking approval for %s, %s", client_id, token)

    if not token.username:
      raise data_store.UnauthorizedAccess(
          "Must specify a username for access.",
          subject=client_id, requested_access=requested_access)

    if not token.reason:
      raise data_store.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=client_id, requested_access=requested_access)

    # Accept either a client_id or a URN.
    client_urn = rdfvalue.RDFURN(client_id)
    client_id, _ = client_urn.Split(2)

    # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
        token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      token.is_emergency = self.acl_cache.Get(approval_urn)
      return True
    except KeyError:
      try:
        # Retrieve the approval object with superuser privileges so we can check
        # it.
        approval_request = aff4.FACTORY.Open(
            approval_urn, required_type="Approval", mode="r",
            token=self.super_token, age=aff4.ALL_TIMES)

        if approval_request.CheckAccess(token):
          # Cache this approval for fast path checking.
          self.acl_cache.Put(approval_urn, token.is_emergency)
          return True

        raise data_store.UnauthorizedAccess(
            "Approval %s was rejected." % approval_urn,
            subject=client_id, requested_access=requested_access)

      except IOError:
        # No Approval found, reject this request.
        raise data_store.UnauthorizedAccess(
            "No approval found for client %s." % client_id,
            subject=client_urn, requested_access=requested_access)

  def CheckHuntApproval(self, hunt_id, token, requested_access):
    """Find the approval for for this token and CheckAccess()."""
    logging.debug("Checking approval for hunt %s, %s", hunt_id, token)
    subject = aff4.ROOT_URN.Add("hunts").Add(hunt_id)

    if not token.username:
      raise data_store.UnauthorizedAccess(
          "Must specify a username for access.",
          subject=subject, requested_access=requested_access)

    if not token.reason:
      raise data_store.UnauthorizedAccess(
          "Must specify a reason for access.",
          subject=subject, requested_access=requested_access)

     # Build the approval URN.
    approval_urn = aff4.ROOT_URN.Add("ACL").Add("hunts").Add(
        hunt_id).Add(token.username).Add(utils.EncodeReasonString(token.reason))

    try:
      approval_request = aff4.FACTORY.Open(
          approval_urn, required_type="Approval", mode="r",
          token=self.super_token, age=aff4.ALL_TIMES)
    except IOError:
      # No Approval found, reject this request.
      raise data_store.UnauthorizedAccess(
          "No approval found for hunt %s." % hunt_id,
          subject=subject, requested_access=requested_access)

    if approval_request.CheckAccess(token):
      return True
    else:
      raise data_store.UnauthorizedAccess(
          "Approval %s was rejected." % approval_urn,
          subject=subject, requested_access=requested_access)

  def CheckHuntAccess(self, subject, token, requested_access):
    """Check whether hunt object (or anything below it) may be accessed."""

    _, hunt_id, _ = subject.Split(3)
    if not hunt_id:
      return self.AccessLowerThan(requested_access, "rq")

    hunt_urn = aff4.ROOT_URN.Add("hunts").Add(hunt_id)
    hunt_metadata = aff4.FACTORY.Stat(hunt_urn, token=self.super_token)
    if not hunt_metadata:
      return True

    if "x" in requested_access:
      return self.CheckHuntApproval(hunt_id, token, requested_access)

    if "w" in requested_access:
      hunt = aff4.FACTORY.Open(hunt_urn, token=self.super_token,
                               age=aff4.ALL_TIMES)
      return (token.username == hunt.Get(hunt.Schema.CREATOR) or
              self.CheckHuntApproval(hunt_id, token, requested_access))

    return True

  def CheckFlowAccess(self, subject, token, requested_access):
    """This is called when the user wishes to execute a flow against a client.

    Args:
      subject: The flow must be encoded as aff4:/client_id/flow_name.
      token: The access token.
      requested_access: The type of access requested (can be "r", "w", "x", "q")

    Returns:
      True is access if allowed, False otherwise.

    Raises:
      data_store.UnauthorizedAccess: On bad request.
    """
    client_id, flow_name = rdfvalue.RDFURN(subject).Split(2)
    # Flows that are executed with client_id=None won't have client_id in the
    # path. These are flows are short-lived one-state flows only. Due to
    # client_id=None, they can't be stored on AFF4 (every GRRFlow object does
    # a sanity check on it's urn and expects it to have client id
    if not flow_name:
      flow_name = client_id
      client_id = None

    flow_cls = flow.GRRFlow.NewPlugin(flow_name)

    # Flows which are not enforced can run all the time.
    if not flow_cls.ACL_ENFORCED:
      return True

    if not client_id:
      return False

    if not self.client_id_re.match(client_id):
      raise data_store.UnauthorizedAccess(
          "Malformed subject for mode 'x': %s." % subject,
          subject=client_id, requested_access=requested_access)

    return self.CheckClientApproval(client_id, token, requested_access)


class ACLInit(registry.InitHook):
  """Install the selected security manager.

  Since many security managers depend on AFF4, we must run after the AFF4
  subsystem is ready.
  """

  pre = ["StatsInit", "AFF4InitHook"]

  def RunOnce(self):
    stats.STATS.RegisterMap("acl_check_time", "times", precision=0)

  def Run(self):
    security_manager = BaseAccessControlManager.NewPlugin(
        FLAGS.security_manager)()
    data_store.DB.security_manager = security_manager
    logging.info("Using security manager %s", security_manager)


def GetApprovalForObject(namespace, object_name, token, username=""):
  """Looks for approvals for a given object and returns available valid tokens.

  Args:
    namespace: Namespace to look in, generally "clients" or "hunts"
    object_name: Name of object we want access to, e.g. hunt_id or a client_id.
    token: The token to use to lookup the ACLs.
    username: The user to get the approval for, if "" we get it from the token.

  Returns:
    A token for access to the object on success, otherwise raises.

  Raises:
    TypeError: If invalid namespace requested.
    UnauthorizedAccess: If there are no valid tokens available.

  """
  if namespace == "hunts":
    requested_object = "%s/%s" % (namespace, object_name)
  elif namespace == "clients":
    requested_object = object_name
  else:
    raise TypeError("Invalid object namespace requested")

  if not username:
    username = token.username
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(requested_object).Add(
      username)

  error = "No approvals available"
  fd = aff4.FACTORY.Open(approval_urn, mode="r", token=token)
  for auth_request in fd.OpenChildren():
    try:
      reason = utils.DecodeReasonString(auth_request.urn.Basename())
    except TypeError:
      continue

    # Check authorization using the data_store for an authoritative source.
    test_token = data_store.ACLToken(username, reason)
    try:
      if namespace == "hunts":
        # Hunts are special as they require execute permissions. These aren't
        # in the ACL model for objects yet, so we work around by scheduling a
        # fake flow to do the check for us.
        flow.FACTORY.StartFlow(None, "CheckHuntAccessFlow", token=test_token,
                               hunt_id=object_name)
      else:
        # Check if we can access a non-existent path under this one.
        aff4.FACTORY.Open(rdfvalue.RDFURN(requested_object).Add("acl_chk"),
                          mode="r", token=test_token)
      return test_token
    except data_store.UnauthorizedAccess as e:
      error = e

  # We tried all auth_requests, but got no usable results.
  raise data_store.UnauthorizedAccess(error)
