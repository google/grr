#!/usr/bin/env python
"""The access control classes and user management classes for the data_store.

An AccessControlManager has the following responsibilities:
  - Authorize users access to resources based on a set of internal rules

A UserManager class has the following responsibilities :
  - Check if a user has a particular label
  - Manage add/update/set password for users (optional)
  - Validate a user authentication event (optional)
"""



import time

import logging

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.proto import flows_pb2


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


class AccessControlManager(object):
  """A class for managing access to data resources.

  This class is responsible for determining which users have access to each
  resource.

  By default it delegates some of this functionality to a UserManager class
  which takes care of label management and user management components.
  """

  __metaclass__ = registry.MetaclassRegistry

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

  def CheckUserLabels(self, username, authorized_labels, token=None):
    """Subclasses verify that the username has all the authorized_labels set."""
    raise NotImplementedError()


class ACLInit(registry.InitHook):
  """Install the selected security manager.

  Since many security managers depend on AFF4, we must run after the AFF4
  subsystem is ready.
  """

  pre = ["StatsInit"]

  def RunOnce(self):
    stats.STATS.RegisterEventMetric("acl_check_time")
    stats.STATS.RegisterCounterMetric("grr_expired_tokens")
    stats.STATS.RegisterCounterMetric("grr_unauthorised_requests")

# This will register all classes into this modules's namespace regardless of
# where they are defined. This allows us to decouple the place of definition of
# a class (which might be in a plugin) from its use which will reference this
# module.
AccessControlManager.classes = globals()


class ACLToken(rdfvalue.RDFProtoStruct):
  """The access control token."""
  protobuf = flows_pb2.ACLToken

  # The supervisor flag enables us to bypass ACL checks. It can not be
  # serialized or controlled externally.
  supervisor = False

  def Copy(self):
    result = super(ACLToken, self).Copy()
    result.supervisor = False
    return result

  def CheckExpiry(self):
    if self.expiry and time.time() > self.expiry:
      raise ExpiryError("Token expired.")

  def __str__(self):
    result = ""
    if self.supervisor:
      result = "******* SUID *******\n"

    return result + super(ACLToken, self).__str__()

  def SetUID(self):
    """Elevates this token to a supervisor token."""
    result = self.Copy()
    result.supervisor = True

    return result

  def RealUID(self):
    """Returns the real token (without SUID) suitable for testing ACLs."""
    result = self.Copy()
    result.supervisor = False

    return result
