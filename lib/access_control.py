#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""The access control classes and user management classes for the data_store.

An AccessControlManager has the following responsibilities:
  - Authorize users access to resources based on a set of internal rules

A UserManager class has the following responsibilities :
  - Check if a user has a particular label
  - Manage add/update/set password for users (optional)
  - Validate a user authentication event (optional)
"""



import getpass
import logging
import sys
import time


from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils

config_lib.DEFINE_integer("ACL.cache_age", 600, "The number of seconds "
                          "approval objects live in the cache.")

config_lib.DEFINE_string("Datastore.security_manager",
                         "NullAccessControlManager",
                         "The ACL manager for controlling access to data.")


class Error(Exception):
  """Access control errors."""


class NotSupportedError(Error):
  """Used when a function isn't supported by a given Access Control Mananger."""


class InvalidUserError(Error):
  """Used when an action is attempted on an invalid user."""


class UnauthorizedAccess(Error):
  """Raised when a request arrived from an unauthorized source."""
  counter = "grr_unauthorised_requests"

  def __init__(self, message, subject=None, requested_access="?"):
    self.subject = subject
    self.requested_access = requested_access
    logging.warning(message)
    super(UnauthorizedAccess, self).__init__(message)


class ExpiryError(Error):
  """Raised when a token is used which is expired."""
  counter = "grr_expired_tokens"


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
    self.SetUserLabels(username, list(self.GetUserLabels(username)) + labels)

  def SetUserLabels(self, username, labels):
    """Overwrite the current set of labels with a list of labels."""

  def MakeUserAdmin(self, username):
    """Shortcut to add the Admin label to a specific user."""
    self.AddUserLabels(username, ["admin"])

  # pylint: disable=unused-argument
  def AddUser(self, username, password=None, admin=True, labels=None):
    """Add a user.

    Args:
      username: User name to create.
      password: Password to set.
      admin: Should the user be made an admin.
      labels: List of additional labels to add to the user.

    Raises:
      RuntimeError: On invalid arguments.
      NotSupportedError: If unimplemented.
    """
    raise NotSupportedError("AddUser not supported by %s" %
                            self.__class__.__name__)

  def UpdateUser(self, username, password=None, admin=True, labels=None):
    """Update the properties of an existing user."""
    self.AddUser(username, password=password, admin=admin, labels=labels)

  def CheckUserAuth(self, username, auth_obj):
    """Update the properties of an existing user."""
    raise NotSupportedError("UpdateUser not supported by %s" %
                            self.__class__.__name__)

  # pylint: enable=unused-argument


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
    logging.debug("Checking %s for hunt %s access.", token, hunt_urn)
    raise NotImplementedError()

  def CheckCronJobAccess(self, token, cron_job_urn):
    """Checks access to a given cron job.

    Args:
      token: User credentials token.
      cron_job_urn: URN of the cron job to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking %s for cron job %s access.", token, cron_job_urn)
    raise NotImplementedError()

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
    logging.debug("Checking %s for flow %s access (client: %s).", token,
                  flow_name, client_id)
    raise NotImplementedError()

  def CheckDataStoreAccess(self, token, subjects, requested_access="r"):
    """The main entry point for checking access to AFF4 resources.

    Args:
      token: An instance of ACLToken security token.

      subjects: The list of subject URNs which the user is requesting access
         to. If any of these fail, the whole request is denied.

      requested_access: A string specifying the desired level of access ("r" for
         read and "w" for write, "q" for query).

    Raises:
       UnauthorizedAccess: If the user is not authorized to perform the action
       on any of the subject URNs.
    """
    logging.debug("Checking %s: %s for %s", token, subjects, requested_access)
    raise NotImplementedError()

  def CheckUserLabels(self, username, authorized_labels):
    """Verify that the username has the authorized_labels set."""
    return self.user_manager.CheckUserLabels(username, authorized_labels)


class ACLInit(registry.InitHook):
  """Install the selected security manager.

  Since many security managers depend on AFF4, we must run after the AFF4
  subsystem is ready.
  """

  pre = ["StatsInit", "AFF4InitHook"]

  def RunOnce(self):
    stats.STATS.RegisterEventMetric("acl_check_time")
    stats.STATS.RegisterCounterMetric("grr_expired_tokens")
    stats.STATS.RegisterCounterMetric("grr_unauthorised_requests")

# This will register all classes into this modules's namespace regardless of
# where they are defined. This allows us to decouple the place of definition of
# a class (which might be in a plugin) from its use which will reference this
# module.
BaseUserManager.classes = globals()
BaseAccessControlManager.classes = globals()


class ACLToken(object):
  """The access control token."""

  is_emergency = False

  def __init__(self, username="", reason="", requested_access="r",
               source_ips=None, process=None, expiry=None):
    """Controls access to the data for the user.

    This ACL token should be provided for any access to the data store. This
    allows the data store to audit all access to data. Note that implementations
    should implement a mechanism for authenticating tokens, so they can not be
    forged.

    Args:
       username: The user which requires access to the data.
       reason: The stated reason for the access (e.g. case name/id).
       requested_access: The type of access this token is for.
       source_ips: Optional list of source IPs of the request.
       process: Optional name of the process issuing this token.
       expiry: When does this token expire (seconds since epoch)? Use of this
          token after this time will raise ExpiryError.
    """
    self.username = username or getpass.getuser()
    self.reason = reason
    self.requested_access = requested_access
    self.source_ips = source_ips or []
    self.process = process

    # This special bit indicates a privileged token for internal use. When this
    # bit is set, ACLs will be bypassed. There should be no way for an external
    # user to set this flag. IMPORTANT: This flag does not serialize to the
    # protobuf for the remote data store!
    self.supervisor = False

    # By default never expire.
    if expiry is None:
      expiry = sys.maxint

    self.expiry = expiry

  def CheckExpiry(self):
    if time.time() > self.expiry:
      raise ExpiryError("Token expired.")

  def __str__(self):
    return "Token(%s:%s)" % (utils.SmartStr(self.username),
                             utils.SmartStr(self.reason))

  def Copy(self):
    return ACLToken(username=self.username, reason=self.reason,
                    requested_access=self.requested_access,
                    source_ips=self.source_ips, process=self.process,
                    expiry=self.expiry)

  def ToRDFToken(self):
    result = rdfvalue.AccessToken(
        username=self.username,
        reason=self.reason,
        requested_access=self.requested_access,
        expiry=long(self.expiry),
        source_ips=self.source_ips)
    if self.process:
      result.process = self.process
    return result
