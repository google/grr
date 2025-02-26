#!/usr/bin/env python
"""The access control classes and user management classes for the data_store."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import deprecated_pb2

_SYSTEM_USERS_LIST = [
    "GRRWorker",
    "GRRCron",
    "GRRSystem",
    "GRRFrontEnd",
    "GRRConsole",
    "GRRArtifactRegistry",
    "GRRStatsStore",
    "GRREndToEndTest",
    "GRR",
    "GRRBenchmarkTest",
    "Cron",
]

SYSTEM_USERS = frozenset(_SYSTEM_USERS_LIST)

_SYSTEM_USERS_LOWERCASE = frozenset(
    username.lower() for username in SYSTEM_USERS
)


class Error(Exception):
  """Access control errors."""


class NotSupportedError(Error):
  """Used when a function isn't supported by a given Access Control Manager."""


class InvalidUserError(Error):
  """Used when an action is attempted on an invalid user."""


class UnauthorizedAccess(Error):  # pylint: disable=g-bad-exception-name
  """Raised when a request arrived from an unauthorized source."""

  counter = "grr_unauthorised_requests"

  def __init__(self, message, subject=None, requested_access="?"):
    self.subject = subject
    self.requested_access = requested_access
    super().__init__(message)


class ACLToken(rdf_structs.RDFProtoStruct):
  """Deprecated. Use ApiCallContext."""

  protobuf = deprecated_pb2.ACLToken
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


def IsValidUsername(username):
  return username.lower() not in _SYSTEM_USERS_LOWERCASE
