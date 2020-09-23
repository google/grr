#!/usr/bin/env python
# Lint as: python3
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

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.registry import MetaclassRegistry
from grr_response_proto import flows_pb2

SYSTEM_USERS = frozenset([
    "GRRWorker", "GRRCron", "GRRSystem", "GRRFrontEnd", "GRRConsole",
    "GRRArtifactRegistry", "GRRStatsStore", "GRREndToEndTest", "GRR",
    "GRRBenchmarkTest", "Cron"
])

_SYSTEM_USERS_LOWERCASE = frozenset(
    username.lower() for username in SYSTEM_USERS)


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
    super().__init__(message)


class AccessControlManager(metaclass=MetaclassRegistry):
  """A class for managing access to data resources.

  This class is responsible for determining which users have access to each
  resource.

  By default it delegates some of this functionality to a UserManager class
  which takes care of label management and user management components.
  """

  def CheckClientAccess(self, context, client_urn):
    """Checks access to the given client.

    Args:
      context: User credentials context.
      client_urn: URN of a client to check.

    Returns:
      True if access is allowed, raises otherwise.
    """
    logging.debug("Checking %s for client %s access.", context, client_urn)
    raise NotImplementedError()

  def CheckHuntAccess(self, context, hunt_urn):
    """Checks access to the given hunt.

    Args:
      context: User credentials context.
      hunt_urn: URN of the hunt to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking %s for hunt %s access.", context, hunt_urn)
    raise NotImplementedError()

  def CheckCronJobAccess(self, context, cron_job_urn):
    """Checks access to a given cron job.

    Args:
      context: User credentials context.
      cron_job_urn: URN of the cron job to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking %s for cron job %s access.", context, cron_job_urn)
    raise NotImplementedError()

  def CheckIfCanStartFlow(self, context, flow_name):
    """Checks if the given flow can be started by the given user.

    If the flow is to be started on a particular client, it's assumed that
    CheckClientAccess passes on that client. If the flow is to be started
    as a global flow, no additional checks will be made.

    Args:
      context: User credentials context.
      flow_name: Name of the flow to check.

    Returns:
      True if access is allowed, raises otherwise.

    Raises:
      access_control.UnauthorizedAccess if access is rejected.
    """
    logging.debug("Checking %s for flow %s access.", context, flow_name)
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


def IsValidUsername(username):
  return username.lower() not in _SYSTEM_USERS_LOWERCASE
