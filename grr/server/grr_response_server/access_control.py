#!/usr/bin/env python
"""The access control classes and user management classes for the data_store.

An AccessControlManager has the following responsibilities:
  - Authorize users access to resources based on a set of internal rules

A UserManager class has the following responsibilities :
  - Check if a user has a particular label
  - Manage add/update/set password for users (optional)
  - Validate a user authentication event (optional)
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import time


from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import flows_pb2


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


class AccessControlManager(with_metaclass(registry.MetaclassRegistry, object)):
  """A class for managing access to data resources.

  This class is responsible for determining which users have access to each
  resource.

  By default it delegates some of this functionality to a UserManager class
  which takes care of label management and user management components.
  """

  def CheckClientAccess(self, token, client_urn):
    """Checks access to the given client.

    Args:
      token: User credentials token.
      client_urn: URN of a client to check.

    Returns:
      True if access is allowed, raises otherwise.
    """
    logging.debug("Checking %s for client %s access.", token, client_urn)
    raise NotImplementedError()

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

  def CheckIfCanStartFlow(self, token, flow_name):
    """Checks if the given flow can be started by the given user.

    If the flow is to be started on a particular client, it's assumed that
    CheckClientAccess passes on that client. If the flow is to be started
    as a global flow, no additional checks will be made. See
    GRRFlow.StartAFF4Flow implementation in lib/flow.py for details.

    Args:
      token: User credentials token.
      flow_name: Name of the flow to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking %s for flow %s access.", token, flow_name)
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


class ACLToken(rdf_structs.RDFProtoStruct):
  """The access control token."""
  protobuf = flows_pb2.ACLToken
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  # The supervisor flag enables us to bypass ACL checks. It can not be
  # serialized or controlled externally.
  supervisor = False

  def Copy(self):
    result = super(ACLToken, self).Copy()
    result.supervisor = False
    return result

  def CheckExpiry(self):
    if self.expiry and time.time() > self.expiry:
      stats_collector_instance.Get().IncrementCounter("grr_expired_tokens")
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
