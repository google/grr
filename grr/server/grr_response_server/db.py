#!/usr/bin/env python
"""The GRR relational database abstraction.

This defines the Database abstraction, which defines the methods used by GRR on
a logical relational database model.

WIP, will eventually replace datastore.py.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import re


from future.utils import iteritems
from future.utils import itervalues
from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_server import foreman_rules
from grr_response_server import stats_values
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):

  def __init__(self, message="", cause=None):
    if cause is not None:
      message += ": %s" % cause

    super(Error, self).__init__(message)

    self.cause = cause


class NotFoundError(Error):
  pass


class UnknownArtifactError(NotFoundError):
  """An exception class for errors about unknown artifacts.

  Attributes:
    name: A name of the non-existing artifact that was referenced.
    cause: An (optional) exception instance that triggered this error.
  """

  def __init__(self, name, cause=None):
    message = "Artifact with name '%s' does not exist" % name
    super(UnknownArtifactError, self).__init__(message, cause=cause)

    self.name = name


class DuplicatedArtifactError(Error):
  """An exception class for errors about duplicated artifacts being written.

  Attributes:
    name: A name of the artifact that was referenced.
    cause: An (optional) exception instance that triggered this error.
  """

  def __init__(self, name, cause=None):
    message = "Artifact with name '%s' already exists" % name
    super(DuplicatedArtifactError, self).__init__(message, cause=cause)

    self.name = name


class UnknownClientError(NotFoundError):
  """"An exception class representing errors about uninitialized client.

  Attributes:
    client_id: An id of the non-existing client that was referenced.
    cause: An (optional) exception instance that triggered the unknown client
      error.
  """

  def __init__(self, client_id, cause=None):
    message = "Client with id '%s' does not exist" % client_id
    super(UnknownClientError, self).__init__(message, cause=cause)

    self.client_id = client_id


class AtLeastOneUnknownClientError(UnknownClientError):

  def __init__(self, client_ids, cause=None):
    message = "At least one client in '%s' does not exist" % ",".join(
        client_ids)
    super(AtLeastOneUnknownClientError, self).__init__(message, cause=cause)

    self.client_ids = client_ids


class UnknownPathError(NotFoundError):
  """An exception class representing errors about unknown paths.

  Attributes:
    client_id: An id of the client for which the path does not exists.
    path_type: A type of the path.
    path_id: An id of the path.
  """

  def __init__(self, client_id, path_type, components, cause=None):
    message = "Path '%s' of type '%s' on client '%s' does not exist"
    message %= ("/".join(components), path_type, client_id)
    super(UnknownPathError, self).__init__(message, cause=cause)

    self.client_id = client_id
    self.path_type = path_type
    self.components = components


class AtLeastOneUnknownPathError(NotFoundError):
  """An exception class raised when one of a set of paths is unknown."""

  def __init__(self, client_path_ids, cause=None):
    message = "At least one of client path ids does not exist: "
    message += ", ".join(utils.SmartStr(cpid) for cpid in client_path_ids)
    if cause is not None:
      message += ": %s" % cause
    super(AtLeastOneUnknownPathError, self).__init__(message)

    self.client_path_ids = client_path_ids
    self.cause = cause


class UnknownRuleError(NotFoundError):
  pass


class UnknownGRRUserError(NotFoundError):
  """An error thrown when no user is found for a given username."""

  def __init__(self, username):
    self.username = username
    message = "Cannot find user with username %r" % username
    super(UnknownGRRUserError, self).__init__(message)


class UnknownApprovalRequestError(NotFoundError):
  pass


class UnknownCronJobError(NotFoundError):
  pass


class UnknownCronJobRunError(NotFoundError):
  pass


class UnknownSignedBinaryError(NotFoundError):
  """Exception raised when a signed binary isn't found in the DB."""

  def __init__(self, binary_id, cause=None):
    """Initializes UnknownSignedBinaryError.

    Args:
      binary_id: rdf_objects.SignedBinaryID for the signed binary.
      cause: A lower-level Exception raised by the database driver, which might
        have more details about the error.
    """
    super(UnknownSignedBinaryError, self).__init__(
        "Signed binary of type %s and path %s was not found" %
        (binary_id.binary_type, binary_id.path),
        cause=cause)


class UnknownFlowError(NotFoundError):

  def __init__(self, client_id, flow_id, cause=None):
    message = ("Flow with client id '%s' and flow id '%s' does not exist" %
               (client_id, flow_id))
    super(UnknownFlowError, self).__init__(message, cause=cause)

    self.client_id = client_id
    self.flow_id = flow_id


class AtLeastOneUnknownFlowError(NotFoundError):

  def __init__(self, flow_keys, cause=None):
    message = ("At least one flow with client id/flow_id in '%s' does not exist"
               % (flow_keys))
    super(AtLeastOneUnknownFlowError, self).__init__(message, cause=cause)

    self.flow_keys = flow_keys


class UnknownFlowRequestError(NotFoundError):

  def __init__(self, client_id, flow_id, request_id, cause=None):
    message = ("Flow request %d for flow with client id '%s' and flow id '%s' "
               "does not exist" % (request_id, client_id, flow_id))
    super(UnknownFlowRequestError, self).__init__(message, cause=cause)

    self.client_id = client_id
    self.flow_id = flow_id
    self.request_id = request_id


class DuplicateMetricValueError(Error):
  """Exception raised if an attempt is made to write duplicate metric values."""

  def __init__(self, cause=None):
    """Constructor.

    Args:
      cause: A lower-level Exception raised by the database driver, which might
        have more details about the error.
    """
    super(DuplicateMetricValueError, self).__init__(
        "Tried to insert a duplicate StatsStoreEntry in the DB", cause=cause)


class UnknownHuntError(NotFoundError):

  def __init__(self, hunt_id, cause=None):
    message = ("Hunt with hunt id '%s' does not exist" % hunt_id)
    super(UnknownHuntError, self).__init__(message, cause=cause)
    self.hunt_id = hunt_id


# TODO(user): migrate to Python 3 enums as soon as Python 3 is default.
class HuntFlowsCondition(object):
  """Constants to be used with ReadHuntFlows/CountHuntFlows methods."""

  UNSET = 0
  FAILED_FLOWS_ONLY = 1
  SUCCEEDED_FLOWS_ONLY = 2
  COMPLETED_FLOWS_ONLY = 3
  FLOWS_IN_PROGRESS_ONLY = 4
  CRASHED_FLOWS_ONLY = 5
  FLOWS_WITH_RESULTS_ONLY = 6

  @classmethod
  def MaxValue(cls):
    return cls.FLOWS_WITH_RESULTS_ONLY


class ClientPath(object):
  """An immutable class representing certain path on a given client.

  Attributes:
    client_id: A client to which the path belongs to.
    path_type: A type of the path.
    components: A tuple of path components.
  """

  def __init__(self, client_id, path_type, components):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    _ValidatePathComponents(components)
    self._repr = (client_id, path_type, components)

  @classmethod
  def OS(cls, client_id, components):
    path_type = rdf_objects.PathInfo.PathType.OS
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def TSK(cls, client_id, components):
    path_type = rdf_objects.PathInfo.PathType.TSK
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def Registry(cls, client_id, components):
    path_type = rdf_objects.PathInfo.PathType.REGISTRY
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def Temp(cls, client_id, components):
    path_type = rdf_objects.PathInfo.PathType.Temp
    return cls(client_id=client_id, path_type=path_type, components=components)

  @classmethod
  def FromPathSpec(cls, client_id, path_spec):
    path_info = rdf_objects.PathInfo.FromPathSpec(path_spec)
    return cls.FromPathInfo(client_id, path_info)

  @classmethod
  def FromPathInfo(cls, client_id, path_info):
    return cls(
        client_id=client_id,
        path_type=path_info.path_type,
        components=tuple(path_info.components))

  @property
  def client_id(self):
    return self._repr[0]

  @property
  def path_type(self):
    return self._repr[1]

  @property
  def components(self):
    return self._repr[2]

  @property
  def vfs_path(self):
    return rdf_objects.ToCategorizedPath(self.path_type, self.components)

  def __eq__(self, other):
    return self._repr == other._repr  # pylint: disable=protected-access

  def __hash__(self):
    return hash(self._repr)

  def Path(self):
    return "/".join(self.components)

  def __repr__(self):
    return "<%s client_id=%r path_type=%r components=%r>" % (
        compatibility.GetName(
            self.__class__), self.client_id, self.path_type, self.components)


class ClientPathHistory(object):
  """A class representing stat and hash history for some path."""

  def __init__(self):
    self.stat_entries = {}
    self.hash_entries = {}

  def AddStatEntry(self, timestamp, stat_entry):
    precondition.AssertType(timestamp, rdfvalue.RDFDatetime)
    precondition.AssertType(stat_entry, rdf_client_fs.StatEntry)
    self.stat_entries[timestamp] = stat_entry

  def AddHashEntry(self, timestamp, hash_entry):
    precondition.AssertType(timestamp, rdfvalue.RDFDatetime)
    precondition.AssertType(hash_entry, rdf_crypto.Hash)
    self.hash_entries[timestamp] = hash_entry


class Database(with_metaclass(abc.ABCMeta, object)):
  """The GRR relational database abstraction."""

  unchanged = "__unchanged__"

  @abc.abstractmethod
  def WriteArtifact(self, artifact):
    """Writes new artifact to the database.

    Args:
      artifact: An `rdf_artifacts.Artifact` instance to write.
    """

  # TODO(hanuszczak): Consider removing this method if it proves to be useless
  # after the artifact registry refactoring.
  @abc.abstractmethod
  def ReadArtifact(self, name):
    """Looks up an artifact with given name from the database.

    Args:
      name: A name of the artifact to return.

    Raises:
      UnknownArtifactError: If an artifact with given name does not exist.
    """

  @abc.abstractmethod
  def ReadAllArtifacts(self):
    """Lists all artifacts that are stored in the database.

    Returns:
      A list of artifacts stored in the database.
    """

  @abc.abstractmethod
  def DeleteArtifact(self, name):
    """Deletes an artifact with given name from the database.

    Args:
      name: A name of the artifact to delete.

    Raises:
      UnknownArtifactError: If an artifact with given name does not exist.
    """

  @abc.abstractmethod
  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None):
    """Write metadata about the client.

    Updates one or more client metadata fields for the given client_id. Any of
    the data fields can be left as None, and in this case are not changed.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      certificate: If set, should be an rdfvalues.crypto.RDFX509 protocol
        buffer. Normally only set during initial client record creation.
      fleetspeak_enabled: A bool, indicating whether the client is connecting
        through Fleetspeak.  Normally only set during initial client record
        creation.
      first_seen: An rdfvalue.Datetime, indicating the first time the client
        contacted the server.
      last_ping: An rdfvalue.Datetime, indicating the last time the client
        contacted the server.
      last_clock: An rdfvalue.Datetime, indicating the last client clock time
        reported to the server.
      last_ip: An rdfvalues.client.NetworkAddress, indicating the last observed
        ip address for the client.
      last_foreman: An rdfvalue.Datetime, indicating the last time that the
        client sent a foreman message to the server.
    """

  @abc.abstractmethod
  def MultiReadClientMetadata(self, client_ids):
    """Reads ClientMetadata records for a list of clients.

    Note: client ids not found in the database will be omitted from the
    resulting map.

    Args:
      client_ids: A collection of GRR client id strings, e.g.
        ["C.ea3b2b71840d6fa7", "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to rdfvalues.object.ClientMetadata.
    """

  def ReadClientMetadata(self, client_id):
    """Reads the ClientMetadata record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.object.ClientMetadata object.

    Raises:
      UnknownClientError: if no client with corresponding id was found.
    """
    result = self.MultiReadClientMetadata([client_id])
    try:
      return result[client_id]
    except KeyError:
      raise UnknownClientError(client_id)

  @abc.abstractmethod
  def WriteClientSnapshot(self, client):
    """Writes new client snapshot.

    Writes a new snapshot of the client to the client history, typically saving
    the results of an interrogate flow.

    Args:
      client: An rdfvalues.objects.ClientSnapshot. Will be saved at the
        "current" timestamp.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def MultiReadClientSnapshot(self, client_ids):
    """Reads the latest client snapshots for a list of clients.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to rdfvalues.objects.ClientSnapshot.
    """

  def ReadClientSnapshot(self, client_id):
    """Reads the latest client snapshot for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.objects.ClientSnapshot object.
    """
    return self.MultiReadClientSnapshot([client_id]).get(client_id)

  @abc.abstractmethod
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    """Reads full client information for a list of clients.

    Note: client ids not found in the database will be omitted from the
    resulting map.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]
      min_last_ping: If not None, only the clients with last ping time bigger
        than min_last_ping will be returned.

    Returns:
      A map from client ids to `ClientFullInfo` instance.
    """

  def ReadClientFullInfo(self, client_id):
    """Reads full client information for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A `ClientFullInfo` instance for given client.

    Raises:
      UnknownClientError: if no client with such id was found.
    """
    result = self.MultiReadClientFullInfo([client_id])
    try:
      return result[client_id]
    except KeyError:
      raise UnknownClientError(client_id)

  @abc.abstractmethod
  def ReadAllClientIDs(self):
    """Reads client ids for all clients in the database.

    Yields:
      A string representing client id.
    """

  @abc.abstractmethod
  def WriteClientSnapshotHistory(self, clients):
    """Writes the full history for a particular client.

    Args:
      clients: A list of client objects representing snapshots in time. Each
        object should have a `timestamp` attribute specifying at which point
        this snapshot was taken. All clients should have the same client id.

    Raises:
      AttributeError: If some client does not have a `timestamp` attribute.
      TypeError: If clients are not instances of `objects.ClientSnapshot`.
      ValueError: If client list is empty or clients have non-uniform ids.
    """

  @abc.abstractmethod
  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    """Reads the full history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all history
        items are fetched. Note: "from" and "to" are inclusive: i.e. a from <=
          time <= to condition is applied.

    Returns:
      A list of rdfvalues.objects.ClientSnapshot, newest snapshot first.
    """

  @abc.abstractmethod
  def WriteClientStartupInfo(self, client_id, startup_info):
    """Writes a new client startup record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      startup_info: An rdfvalues.client.StartupInfo object. Will be saved at the
        "current" timestamp.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ReadClientStartupInfo(self, client_id):
    """Reads the latest client startup record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.client.StartupInfo object.
    """

  @abc.abstractmethod
  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
    """Reads the full startup history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all history
        items are fetched. Note: "from" and "to" are inclusive: i.e. a from <=
          time <= to condition is applied.

    Returns:
      A list of rdfvalues.client.StartupInfo objects sorted by timestamp,
      newest entry first.
    """

  @abc.abstractmethod
  def WriteClientCrashInfo(self, client_id, crash_info):
    """Writes a new client crash record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      crash_info: An rdfvalues.objects.ClientCrash object. Will be saved at the
        "current" timestamp.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ReadClientCrashInfo(self, client_id):
    """Reads the latest client crash record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.client.ClientCrash object.
    """

  @abc.abstractmethod
  def ReadClientCrashInfoHistory(self, client_id):
    """Reads the full crash history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A list of rdfvalues.client.ClientCrash objects sorted by timestamp,
      newest entry first.
    """

  @abc.abstractmethod
  def AddClientKeywords(self, client_id, keywords):
    """Associates the provided keywords with the client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      keywords: An iterable container of keyword strings to write.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ListClientsForKeywords(self, keywords, start_time=None):
    """Lists the clients associated with keywords.

    Args:
      keywords: An iterable container of keyword strings to look for.
      start_time: If set, should be an rdfvalue.RDFDatime and the function will
        only return keywords associated after this time.

    Returns:
      A dict mapping each provided keyword to a potentially empty list of client
        ids.
    """

  @abc.abstractmethod
  def RemoveClientKeyword(self, client_id, keyword):
    """Removes the association of a particular client to a keyword.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      keyword: The keyword to delete.
    """

  @abc.abstractmethod
  def AddClientLabels(self, client_id, owner, labels):
    """Attaches a user label to a client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      owner: Username string that owns the created labels.
      labels: The labels to attach as a list of strings.
    """

  @abc.abstractmethod
  def MultiReadClientLabels(self, client_ids):
    """Reads the user labels for a list of clients.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to a list of rdfvalue.objects.ClientLabel,
      sorted by owner, label name.
    """

  def ReadClientLabels(self, client_id):
    """Reads the user labels for a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A list of rdfvalue.objects.ClientLabel for the given client,
      sorted by owner, label name.
    """
    return self.MultiReadClientLabels([client_id])[client_id]

  @abc.abstractmethod
  def RemoveClientLabels(self, client_id, owner, labels):
    """Removes a list of user labels from a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      owner: Username string that owns the labels that should be removed.
      labels: The labels to remove as a list of strings.
    """

  @abc.abstractmethod
  def ReadAllClientLabels(self):
    """Lists all client labels known to the system.

    Returns:
      A list of rdfvalue.objects.ClientLabel values.
    """

  @abc.abstractmethod
  def WriteForemanRule(self, rule):
    """Writes a foreman rule to the database.

    Args:
      rule: A foreman.ForemanRule object.
    """

  @abc.abstractmethod
  def RemoveForemanRule(self, hunt_id):
    """Removes a foreman rule from the database.

    Args:
      hunt_id: Hunt id of the rule that should be removed.

    Raises:
      UnknownRuleError: No rule with the given hunt_id exists.
    """

  @abc.abstractmethod
  def ReadAllForemanRules(self):
    """Reads all foreman rules from the database.

    Returns:
      A list of foreman.ForemanCondition objects.
    """

  @abc.abstractmethod
  def RemoveExpiredForemanRules(self):
    """Removes all expired foreman rules from the database."""

  @abc.abstractmethod
  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None):
    """Writes user object for a user with a given name.

    If a user with the given username exists, it is overwritten.

    Args:
      username: Name of a user to insert/update.
      password: If set, should be a string with a new encrypted user password.
      ui_mode: If set, should be a GUISettings.UIMode enum.
      canary_mode: If not None, should be a boolean indicating user's preferred
        canary mode setting.
      user_type: GRRUser.UserType enum describing user type (unset, standard or
        admin).
    """

  @abc.abstractmethod
  def ReadGRRUser(self, username):
    """Reads a user object corresponding to a given name.

    Args:
      username: Name of a user.

    Returns:
      A rdfvalues.objects.GRRUser object.
    Raises:
      UnknownGRRUserError: if there's no user corresponding to the given name.
    """

  @abc.abstractmethod
  def ReadGRRUsers(self, offset=0, count=None):
    """Reads GRR users with optional pagination, sorted by username.

    Args:
      offset: An integer specifying an offset to be used when reading results.
      count: Maximum number of users to return. If not provided, all users will
        be returned (respecting offset).
    Returns: A List of `objects.GRRUser` objects.

    Raises:
      ValueError: if offset or count are negative.
    """

  @abc.abstractmethod
  def CountGRRUsers(self):
    """Returns the total count of GRR users."""

  @abc.abstractmethod
  def DeleteGRRUser(self, username):
    """Deletes the user with the given username.

    Args:
      username: Name of a user to insert/update.

    Raises:
      UnknownGRRUserError: if there is no user corresponding to the given name.
    """

  @abc.abstractmethod
  def WriteApprovalRequest(self, approval_request):
    """Writes an approval request object.

    Args:
      approval_request: rdfvalues.objects.ApprovalRequest object. Note:
        approval_id and timestamps provided inside the argument object will be
        ignored. Values generated by the database will be used instead.

    Returns:
      approval_id: String identifying newly created approval request.
                   Approval id is unique among approval ids for the same
                   username. I.e. there can be no 2 approvals with the same id
                   for the same username.
    """

  @abc.abstractmethod
  def ReadApprovalRequest(self, requestor_username, approval_id):
    """Reads an approval request object with a given id.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_id: String identifying approval request object.

    Returns:
      rdfvalues.objects.ApprovalRequest object.
    Raises:
      UnknownApprovalRequest: if there's no corresponding approval request
                              object.
    """

  @abc.abstractmethod
  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False):
    """Reads approval requests of a given type for a given user.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_type: Type of approvals to list.
      subject_id: String identifying the subject (client id, hunt id or cron job
        id). If not None, only approval requests for this subject will be
        returned.
      include_expired: If True, will also yield already expired approvals.

    Yields:
      rdfvalues.objects.ApprovalRequest objects.
    """

  @abc.abstractmethod
  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    """Grants approval for a given request using given username.

    Args:
      requestor_username: Username of the user who has requested the approval.
      approval_id: String identifying approval request object.
      grantor_username: String with a username of a user granting the approval.
    """

  def IterateAllClientsFullInfo(self, batch_size=50000, min_last_ping=None):
    """Iterates over all available clients and yields full info protobufs.

    Args:
      batch_size: Always reads <batch_size> client full infos at a time.
      min_last_ping: If not None, only the clients with last ping time bigger
        than min_last_ping will be returned.

    Yields:
      An rdfvalues.objects.ClientFullInfo object for each client in the db.
    """
    all_client_ids = self.ReadAllClientIDs()

    for batch in collection.Batch(all_client_ids, batch_size):
      res = self.MultiReadClientFullInfo(batch, min_last_ping=min_last_ping)
      for full_info in itervalues(res):
        yield full_info

  def IterateAllClientSnapshots(self, batch_size=50000):
    """Iterates over all available clients and yields client snapshot objects.

    Args:
      batch_size: Always reads <batch_size> snapshots at a time.

    Yields:
      An rdfvalues.objects.ClientSnapshot object for each client in the db.
    """
    all_client_ids = self.ReadAllClientIDs()

    for batch in collection.Batch(all_client_ids, batch_size):
      res = self.MultiReadClientSnapshot(batch)
      for snapshot in itervalues(res):
        if snapshot:
          yield snapshot

  @abc.abstractmethod
  def ReadPathInfo(self, client_id, path_type, components, timestamp=None):
    """Retrieves a path info record for a given path.

    The `timestamp` parameter specifies for what moment in time the path
    information is to be retrieved. For example, if (using abstract time units)
    at time 1 the path was in state A, at time 5 it was observed to be in state
    B and at time 8 it was in state C one wants to retrieve information at time
    6 the result is going to be B.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve path
        information for.
      timestamp: A moment in time for which we want to retrieve the information.
        If none is provided, the latest known path information is returned.

    Returns:
      An `rdf_objects.PathInfo` instance.
    """

  @abc.abstractmethod
  def ReadPathInfos(self, client_id, path_type, components_list):
    """Retrieves path info records for given paths.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components_list: An iterable of tuples of path components corresponding to
        paths to retrieve path information for.

    Returns:
      A dictionary mapping path components to `rdf_objects.PathInfo` instances.
    """

  def ListChildPathInfos(self, client_id, path_type, components,
                         timestamp=None):
    """Lists path info records that correspond to children of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve child path
        information for.
      timestamp: If set, lists only descendants that existed only at that
        timestamp.

    Returns:
      A list of `rdf_objects.PathInfo` instances sorted by path components.
    """
    return self.ListDescendentPathInfos(
        client_id, path_type, components, max_depth=1, timestamp=timestamp)

  @abc.abstractmethod
  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              timestamp=None,
                              max_depth=None):
    """Lists path info records that correspond to descendants of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve descendent
        path information for.
      timestamp: If set, lists only descendants that existed at that timestamp.
      max_depth: If set, the maximum number of generations to descend, otherwise
        unlimited.

    Returns:
      A list of `rdf_objects.PathInfo` instances sorted by path components.
    """

  @abc.abstractmethod
  def WritePathInfos(self, client_id, path_infos):
    """Writes a collection of path_info records for a client.

    If any records are already present in the database, they will be merged -
    see db_path_utils.MergePathInfo.

    Args:
      client_id: The client of interest.
      path_infos: A list of rdfvalue.objects.PathInfo records.
    """

  @abc.abstractmethod
  def MultiWritePathInfos(self, path_infos):
    """Writes a collection of path info records for specified clients.

    Args:
      path_infos: A dictionary mapping client ids to `rdf_objects.PathInfo`
        instances.
    """

  def InitPathInfos(self, client_id, path_infos):
    """Initializes a collection of path info records for a client.

    Unlike `WritePathInfo`, this method clears stat and hash histories of paths
    associated with path info records. This method is intended to be used only
    in the data migration scripts.

    Args:
      client_id: A client identifier for which the paths are to be initialized.
      path_infos: A list of `rdf_objects.PathInfo` objects to write.
    """
    self.ClearPathHistory(client_id, path_infos)
    self.WritePathInfos(client_id, path_infos)

  def MultiInitPathInfos(self, path_infos):
    """Initialize a collection of path info records for specified clients.

    See documentation for `InitPathInfos` for more details.

    Args:
      path_infos: A dictionary mapping client ids to `rdf_objects.PathInfo`
        instances.
    """
    self.MultiClearPathHistory(path_infos)
    self.MultiWritePathInfos(path_infos)

  @abc.abstractmethod
  def ClearPathHistory(self, client_id, path_infos):
    """Clears path history for specified paths of given client.

    Args:
      client_id: A client identifier for which the path histories are about to
        be cleared.
      path_infos: A list of `rdf_objects.PathInfo` instances corresponding to
        paths to clear the history for.
    """

  @abc.abstractmethod
  def MultiClearPathHistory(self, path_infos):
    """Clears path history for specified paths of given clients.

    Args:
      path_infos: A dictionary mapping client ids to `rdf_objects.PathInfo`
        instances corresponding to paths to clear the history for.
    """

  @abc.abstractmethod
  def MultiWritePathHistory(self, client_path_histories):
    """Writes a collection of hash and stat entries observed for given paths.

    Args:
      client_path_histories: A dictionary mapping `ClientPath` instances to
        `ClientPathHistory` objects.
    """

  def WritePathStatHistory(self, client_path, stat_entries):
    """Writes a collection of `StatEntry` observed for particular path.

    Args:
      client_path: A `ClientPath` instance.
      stat_entries: A dictionary with timestamps as keys and `StatEntry`
        instances as values.
    """
    client_path_history = ClientPathHistory()
    for timestamp, stat_entry in iteritems(stat_entries):
      client_path_history.AddStatEntry(timestamp, stat_entry)

    self.MultiWritePathHistory({client_path: client_path_history})

  def WritePathHashHistory(self, client_path, hash_entries):
    """Writes a collection of `Hash` observed for particular path.

    Args:
      client_path: A `ClientPath` instance.
      hash_entries: A dictionary with timestamps as keys and `Hash` instances as
        values.
    """
    client_path_history = ClientPathHistory()
    for timestamp, hash_entry in iteritems(hash_entries):
      client_path_history.AddHashEntry(timestamp, hash_entry)

    self.MultiWritePathHistory({client_path: client_path_history})

  @abc.abstractmethod
  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    """Reads a collection of hash and stat entries for given paths.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path history information for.
      components_list: An iterable of tuples of path components corresponding to
        paths to retrieve path information for.

    Returns:
      A dictionary mapping path components to lists of `rdf_objects.PathInfo`
      ordered by timestamp in ascending order.
    """

  def ReadPathInfoHistory(self, client_id, path_type, components):
    """Reads a collection of hash and stat entry for given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path history for.
      components: A tuple of path components corresponding to path to retrieve
        information for.

    Returns:
      A list of `rdf_objects.PathInfo` ordered by timestamp in ascending order.
    """
    histories = self.ReadPathInfosHistories(client_id, path_type, [components])
    return histories[components]

  @abc.abstractmethod
  def ReadLatestPathInfosWithHashBlobReferences(self,
                                                client_paths,
                                                max_timestamp=None):
    """Returns PathInfos that have corresponding HashBlobReferences.

    Args:
      client_paths: ClientPath objects pointing to files.
      max_timestamp: If not specified, then for every path simply the latest
        PathInfo that has a matching HashBlobReference entry will be returned.
        If specified, should be an rdfvalue.RDFDatetime, then the latest
        PathInfo with a timestamp less or equal to max_timestamp will be
        returned for every path.

    Returns:
      A dictionary mapping client paths to PathInfo objects. Every client path
      from the client_paths argument is guaranteed to be a key in the resulting
      dictionary. If a particular path won't have a PathInfo with a
      corresponding HashBlobReference entry, None will be used as a dictionary
      value.
    """

  @abc.abstractmethod
  def WriteUserNotification(self, notification):
    """Writes a notification for a given user.

    Args:
      notification: objects.UserNotification object to be written.
    """

  @abc.abstractmethod
  def ReadUserNotifications(self, username, state=None, timerange=None):
    """Reads notifications scheduled for a user within a given timerange.

    Args:
      username: Username identifying the user.
      state: If set, only return the notifications with a given state attribute.
      timerange: Should be either a tuple of (from, to) or None. "from" and to"
        should be rdfvalue.RDFDatetime or None values (from==None means "all
        record up to 'to'", to==None means all records from 'from'). If both
        "to" and "from" are None or the timerange itself is None, all
        notifications are fetched. Note: "from" and "to" are inclusive: i.e. a
          from <= time <= to condition is applied.

    Returns:
      List of objects.UserNotification objects.
    """

  @abc.abstractmethod
  def UpdateUserNotifications(self, username, timestamps, state=None):
    """Updates existing user notification objects.

    Args:
      username: Username identifying the user.
      timestamps: List of timestamps of the notifications to be updated.
      state: objects.UserNotification.State enum value to be written into the
        notifications objects.
    """

  @abc.abstractmethod
  def ReadAPIAuditEntries(self,
                          username=None,
                          router_method_name=None,
                          min_timestamp=None,
                          max_timestamp=None):
    """Returns audit entries stored in the database.

    The event log is sorted according to their timestamp (with the oldest
    recorded event being first).

    Args:
      username: username associated with the audit entries
      router_method_name: name of router method that handled the request
      min_timestamp: minimum rdfvalue.RDFDateTime (inclusive)
      max_timestamp: maximum rdfvalue.RDFDateTime (inclusive)

    Returns:
      List of `rdfvalues.objects.APIAuditEntry` instances.
    """

  @abc.abstractmethod
  def WriteAPIAuditEntry(self, entry):
    """Writes an audit entry to the database.

    Args:
      entry: An `audit.APIAuditEntry` instance.
    """

  @abc.abstractmethod
  def WriteMessageHandlerRequests(self, requests):
    """Writes a list of message handler requests to the database.

    Args:
      requests: List of objects.MessageHandlerRequest.
    """

  @abc.abstractmethod
  def ReadMessageHandlerRequests(self):
    """Reads all message handler requests from the database.

    Returns:
      A list of objects.MessageHandlerRequest, sorted by timestamp,
      newest first.
    """

  @abc.abstractmethod
  def DeleteMessageHandlerRequests(self, requests):
    """Deletes a list of message handler requests from the database.

    Args:
      requests: List of objects.MessageHandlerRequest.
    """

  @abc.abstractmethod
  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    """Registers a message handler to receive batches of messages.

    Args:
      handler: Method, which will be called repeatedly with lists of leased
        objects.MessageHandlerRequest. Required.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid. Required.
      limit: Limit for the number of leased requests to give one execution of
        handler.
    """

  @abc.abstractmethod
  def UnregisterMessageHandler(self, timeout=None):
    """Unregisters any registered message handler.

    Args:
      timeout: A timeout in seconds for joining the handler thread.
    """

  @abc.abstractmethod
  def WriteCronJob(self, cronjob):
    """Writes a cronjob to the database.

    Args:
      cronjob: A cronjobs.CronJob object.
    """

  def ReadCronJob(self, cronjob_id):
    """Reads a cronjob from the database.

    Args:
      cronjob_id: The id of the cron job to read.

    Returns:
      A list of cronjobs.CronJob objects.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """
    return self.ReadCronJobs(cronjob_ids=[cronjob_id])[0]

  @abc.abstractmethod
  def ReadCronJobs(self, cronjob_ids=None):
    """Reads all cronjobs from the database.

    Args:
      cronjob_ids: A list of cronjob ids to read. If not set, returns all cron
        jobs in the database.

    Returns:
      A list of cronjobs.CronJob objects.

    Raises:
      UnknownCronJobError: A cron job for at least one of the given ids
                           does not exist.
    """

  @abc.abstractmethod
  def EnableCronJob(self, cronjob_id):
    """Enables a cronjob.

    Args:
      cronjob_id: The id of the cron job to enable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def DisableCronJob(self, cronjob_id):
    """Disables a cronjob.

    Args:
      cronjob_id: The id of the cron job to disable.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def DeleteCronJob(self, cronjob_id):
    """Deletes a cronjob.

    Args:
      cronjob_id: The id of the cron job to delete.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=unchanged,
                    last_run_time=unchanged,
                    current_run_id=unchanged,
                    state=unchanged,
                    forced_run_requested=unchanged):
    """Updates run information for an existing cron job.

    Args:
      cronjob_id: The id of the cron job to update.
      last_run_status: A CronJobRunStatus object.
      last_run_time: The last time a run was started for this cron job.
      current_run_id: The id of the currently active run.
      state: The state dict for stateful cron jobs.
      forced_run_requested: A boolean indicating if a forced run is pending for
        this job.

    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None):
    """Leases all available cron jobs.

    Args:
      cronjob_ids: A list of cronjob ids that should be leased. If None, all
        available cronjobs will be leased.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid.

    Returns:
      A list of cronjobs.CronJob objects that were leased.
    """

  @abc.abstractmethod
  def ReturnLeasedCronJobs(self, jobs):
    """Makes leased cron jobs available for leasing again.

    Args:
      jobs: A list of leased cronjobs.

    Raises:
      ValueError: If not all of the cronjobs are leased.
    """

  @abc.abstractmethod
  def WriteCronJobRun(self, run_object):
    """Stores a cron job run object in the database.

    Args:
      run_object: A rdf_cronjobs.CronJobRun object to store.
    """

  @abc.abstractmethod
  def ReadCronJobRuns(self, job_id):
    """Reads all cron job runs for a given job id.

    Args:
      job_id: Runs will be returned for the job with the given id.

    Returns:
      A list of rdf_cronjobs.CronJobRun objects.
    """

  @abc.abstractmethod
  def ReadCronJobRun(self, job_id, run_id):
    """Reads a single cron job run from the db.

    Args:
      job_id: The job_id of the run to be read.
      run_id: The run_id of the run to be read.

    Returns:
      An rdf_cronjobs.CronJobRun object.
    """

  @abc.abstractmethod
  def DeleteOldCronJobRuns(self, cutoff_timestamp):
    """Deletes cron job runs that are older than cutoff_timestamp.

    Args:
      cutoff_timestamp: This method deletes all runs that were started before
        cutoff_timestamp.

    Returns:
      The number of deleted runs.
    """

  @abc.abstractmethod
  def WriteHashBlobReferences(self, references_by_hash):
    """Writes blob references for a given set of hashes.

    Every file known to GRR has a history of PathInfos. Every PathInfo has a
    hash_entry corresponding to a known hash of a file (or a downloaded part
    of the file) at a given moment.

    GRR collects files by collecting individual data blobs from the client.
    Thus, in the end a file contents may be described as a sequence of blobs.
    Using WriteHashBlobReferences we key this sequence of blobs not with the
    file name, but rather with a hash identifying file contents.

    This way for any given PathInfo we can look at the hash and say whether
    we have corresponding contents of the file by using ReadHashBlobRefernces.

    Args:
      references_by_hash: A dict where SHA256HashID objects are keys and lists
        of BlobReference objects are values.
    """

  @abc.abstractmethod
  def ReadHashBlobReferences(self, hashes):
    """Reads blob references of a given set of hashes.

    Every file known to GRR has a history of PathInfos. Every PathInfo has a
    hash_entry corresponding to a known hash of a file (or a downloaded part
    of the file) at a given moment.

    GRR collects files by collecting individual data blobs from the client.
    Thus, in the end a file contents may be described as a sequence of blobs.
    We key this sequence of blobs not with the file name, but rather with a
    hash identifying file contents.

    This way for any given PathInfo we can look at the hash and say whether
    we have corresponding contents of the file by using ReadHashBlobRefernces.

    Args:
      hashes: An iterable of SHA256HashID objects.

    Returns:
      A dict where SHA256HashID objects are keys and iterables of BlobReference
      objects are values. If no blob references are found for a certain hash,
      None will be used as a value instead of a list.
    """

  @abc.abstractmethod
  def WriteBlobs(self, blob_id_data_map):
    """Writes given blobs.

    Args:
      blob_id_data_map: A map of blob_id -> blob_data. Each blob_id should be a
        rdf_objects.BlobID blob hash uniquely idenitify the blob. blob_data
        should be expressed in bytes.
    """

  @abc.abstractmethod
  def ReadBlobs(self, blob_ids):
    """Reads given blobs.

    Args:
      blob_ids: An iterable with blob hashes expressed as rdf_objects.BlobID
        objects.

    Returns:
      A map of {blob_id: blob_data} where blob_data is blob bytes previously
      written with WriteBlobs. If blob_data for particular blob is not found,
      blob_data is expressed as None.
    """

  @abc.abstractmethod
  def CheckBlobsExist(self, blob_ids):
    """Checks if given blobs exist.

    Args:
      blob_ids: An iterable with blob hashes expressed as rdf_objects.BlobID
        objects.

    Returns:
      A map of {blob_id: status} where status is a boolean (True if blob exists,
      False if it doesn't).
    """

  # If we send a message unsuccessfully to a client five times, we just give up
  # and remove the message to avoid endless repetition of some broken action.
  CLIENT_MESSAGES_TTL = 5

  @abc.abstractmethod
  def WriteClientMessages(self, messages):
    """Writes messages that should go to the client to the db.

    Args:
      messages: A list of GrrMessage objects to write.
    """

  @abc.abstractmethod
  def LeaseClientMessages(self, client_id, lease_time=None, limit=None):
    """Leases available client messages for the client with the given id.

    Args:
      client_id: The client for which the messages should be leased.
      lease_time: rdfvalue.Duration indicating how long the lease should be
        valid.
      limit: Lease at most <limit> messages.

    Returns:
      A list of GrrMessage objects.
    """

  @abc.abstractmethod
  def ReadClientMessages(self, client_id):
    """Reads all client messages available for a given client_id.

    Args:
      client_id: The client for which the messages should be read.

    Returns:
      A list of GrrMessage objects.
    """

  @abc.abstractmethod
  def DeleteClientMessages(self, messages):
    """Deletes a list of client messages from the db.

    Args:
      messages: A list of GrrMessage objects to delete.
    """

  @abc.abstractmethod
  def WriteFlowObject(self, flow_obj):
    """Writes a flow object to the database.

    Args:
      flow_obj: An rdf_flow_objects.Flow object to write.

    Raises:
      UnknownClientError: The client with the flow's client_id does not exist.
    """

  @abc.abstractmethod
  def ReadFlowObject(self, client_id, flow_id):
    """Reads a flow object from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read.

    Returns:
      An rdf_flow_objects.Flow object.
    """

  @abc.abstractmethod
  def ReadAllFlowObjects(self, client_id, min_create_time=None):
    """Reads all flow objects from the database for a given client.

    Args:
      client_id: The client id.
      min_create_time: the minimum creation time (inclusive)

    Returns:
      A list of rdf_flow_objects.Flow objects.
    """

  @abc.abstractmethod
  def ReadChildFlowObjects(self, client_id, flow_id):
    """Reads flow objects that were started by a given flow from the database.

    Args:
      client_id: The client id on which the flows are running.
      flow_id: The id of the parent flow.

    Returns:
      A list of rdf_flow_objects.Flow objects.
    """

  @abc.abstractmethod
  def ReadFlowForProcessing(self, client_id, flow_id, processing_time):
    """Marks a flow as being processed on this worker and returns it.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read.
      processing_time: Duration that the worker has to finish processing before
        the flow is considered stuck.

    Raises:
      ValueError: The flow is already marked as being processed.

    Returns:
      And rdf_flow_objects.Flow object.
    """

  @abc.abstractmethod
  def ReturnProcessedFlow(self, flow_obj):
    """Returns a flow that the worker was processing to the database.

    This method will check if there are currently more requests ready for
    processing. If there are, the flow will not be written to the database and
    the method will return false.

    Args:
      flow_obj: The rdf_flow_objects.Flow object to return.

    Returns:
      A boolean indicating if it was possible to return the flow to the
      database. If there are currently more requests ready to being processed,
      this method will return false and the flow will not be written.
    """

  @abc.abstractmethod
  def UpdateFlow(self,
                 client_id,
                 flow_id,
                 flow_obj=unchanged,
                 client_crash_info=unchanged,
                 pending_termination=unchanged,
                 processing_on=unchanged,
                 processing_since=unchanged,
                 processing_deadline=unchanged):
    """Updates flow objects in the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to update.
      flow_obj: An updated rdf_flow_objects.Flow object.
      client_crash_info: A rdf_client.ClientCrash object to store with the flow.
      pending_termination: An rdf_flow_objects.PendingFlowTermination object.
        Indicates that this flow is scheduled for termination.
      processing_on: Worker this flow is currently processed on.
      processing_since: Timstamp when the worker started processing this flow.
      processing_deadline: Time after which this flow will be considered stuck
        if processing hasn't finished.
    """

  @abc.abstractmethod
  def UpdateFlows(self, client_id_flow_id_pairs, pending_termination=unchanged):
    """Updates flow objects in the database.

    Args:
      client_id_flow_id_pairs: An iterable with tuples of (client_id, flow_id)
        identifying flows to update.
      pending_termination: An rdf_flow_objects.PendingFlowTermination object.
        Indicates that this flow is scheduled for termination.
    """

  @abc.abstractmethod
  def WriteFlowRequests(self, requests):
    """Writes a list of flow requests to the database.

    Args:
      requests: List of rdf_flow_objects.FlowRequest objects.
    """

  @abc.abstractmethod
  def DeleteFlowRequests(self, requests):
    """Deletes a list of flow requests from the database.

    Note: This also deletes all corresponding responses.

    Args:
      requests: List of rdf_flow_objects.FlowRequest objects.
    """

  @abc.abstractmethod
  def WriteFlowResponses(self, responses):
    """Writes a list of flow responses to the database.

    This method not only stores the list of responses given in the database but
    also updates flow status information at the same time. Specifically, it
    updates all corresponding flow requests, setting the needs_processing flag
    in case all expected responses are available in the database after this call
    and, in case the request the flow is currently waiting on becomes available
    for processing, it also writes a FlowProcessingRequest to notify the worker.

    Args:
      responses: List of rdf_flow_objects.FlowResponse rdfvalues to write.
    """

  @abc.abstractmethod
  def ReadAllFlowRequestsAndResponses(self, client_id, flow_id):
    """Reads all requests and responses for a given flow from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read requests and responses for.

    Returns:
      A list of tuples (request, dict mapping response_id to response) for each
      request in the db.
    """

  @abc.abstractmethod
  def DeleteAllFlowRequestsAndResponses(self, client_id, flow_id):
    """Deletes all requests and responses for a given flow from the database.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to delete requests and responses for.
    """

  @abc.abstractmethod
  def ReadFlowRequestsReadyForProcessing(self,
                                         client_id,
                                         flow_id,
                                         next_needed_request=None):
    """Reads all requests for a flow that can be processed by the worker.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read requests for.
      next_needed_request: The next request id that the flow needs to process.

    Returns:
      A dict mapping flow request id to tuples (request,
      sorted list of responses for the request).
    """

  @abc.abstractmethod
  def WriteFlowProcessingRequests(self, requests):
    """Writes a list of flow processing requests to the database.

    Args:
      requests: List of rdf_flows.FlowProcessingRequest.
    """

  @abc.abstractmethod
  def ReadFlowProcessingRequests(self):
    """Reads all flow processing requests from the database.

    Returns:
      A list of rdf_flows.FlowProcessingRequest, sorted by timestamp,
      newest first.
    """

  @abc.abstractmethod
  def AckFlowProcessingRequests(self, requests):
    """Acknowledges and deletes flow processing requests.

    Args:
      requests: List of rdf_flows.FlowProcessingRequest.
    """

  @abc.abstractmethod
  def DeleteAllFlowProcessingRequests(self):
    """Deletes all flow processing requests from the database."""

  @abc.abstractmethod
  def RegisterFlowProcessingHandler(self, handler):
    """Registers a handler to receive flow processing messages.

    Args:
      handler: Method, which will be called repeatedly with lists of
        rdf_flows.FlowProcessingRequest. Required.
    """

  @abc.abstractmethod
  def UnregisterFlowProcessingHandler(self, timeout=None):
    """Unregisters any registered flow processing handler.

    Args:
      timeout: A timeout in seconds for joining the handler thread.
    """

  @abc.abstractmethod
  def WriteFlowResults(self, client_id, flow_id, results):
    """Writes flow results for a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to write results for.
      results: An iterable with FlowResult rdfvalues.
    """

  @abc.abstractmethod
  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    """Reads flow results of a given flow using given query options.

    If both with_tag and with_type and/or with_substring arguments are provided,
    they will be applied using AND boolean operator.

    Args:
      client_id: The client id on which this flow is running.
      flow_id: The id of the flow to read results for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be returned.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be returned.
      with_substring: (Optional) When specified, should be a string. Only
        results having the specified string as a substring in their serialized
        form will be returned.

    Returns:
      A list of FlowResult values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountFlowResults(self, client_id, flow_id, with_tag=None, with_type=None):
    """Counts flow results of a given flow using given query options.

    If both with_tag and with_type arguments are provided, they will be applied
    using AND boolean operator.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count results for.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be accounted for.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be accounted for.

    Returns:
      A number of flow results of a given flow matching given query options.
    """

  @abc.abstractmethod
  def WriteFlowLogEntries(self, client_id, flow_id, entries):
    """Writes flow log entries for a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to write log entries for.
      entries: An iterable of FlowLogEntry values.
    """

  @abc.abstractmethod
  def ReadFlowLogEntries(self,
                         client_id,
                         flow_id,
                         offset,
                         count,
                         with_substring=None):
    """Reads flow log entries of a given flow using given query options.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to read log entries for.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_substring filter is applied
        (if specified).
      count: Number of log entries to read. "count" is applied after the
        with_substring filter is applied (if specified).
      with_substring: (Optional) When specified, should be a string. Only log
        entries having the specified string as a message substring will be
        returned.

    Returns:
      A list of FlowLogEntry values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountFlowLogEntries(self, client_id, flow_id):
    """Returns number of flow log entries of a given flow.

    Args:
      client_id: The client id on which the flow is running.
      flow_id: The id of the flow to count log entries for.

    Returns:
      Number of flow log entries of a given flow.
    """

  @abc.abstractmethod
  def WriteStatsStoreEntries(self, stats_entries):
    """Writes an Iterable of StatsStoreEntries to the database."""

  @abc.abstractmethod
  def ReadStatsStoreEntries(self,
                            process_id_prefix,
                            metric_name,
                            time_range=None,
                            max_results=0):
    """Reads StatsStoreEntries matching given criteria from the DB.

    Args:
      process_id_prefix: String prefix used to filter process ids whose data
        should be included in the results.
      metric_name: Name of the stats metric for which to return past values.
      time_range: An optional tuple containing two RDFDateTime objects that
        represent the range of timestamps to filter for (if provided, only
        StatsStoreEntries in the range will be included).
      max_results: If > 0, indicates the maximum number of results to return.

    Returns:
      A sequence of StatsStoreEntries matching all the provided criteria.
    """

  @abc.abstractmethod
  def DeleteStatsStoreEntriesOlderThan(self, cutoff, limit):
    """Deletes StatsStoreEntries in the DB older than a given timestamp.

    Args:
      cutoff: An RDFDateTime representing the maximum age of entries that would
        remain after deleting all older entries.
      limit: The maximum number of entries to delete. Must be > 0.

    Returns:
      The number of stats-store entries that were deleted. If the number is
      equal to the limit provided, it means that there are more entries
      to delete (or that there were exactly 'limit' stale entries in the DB).
    """

  @abc.abstractmethod
  def WriteHuntObject(self, hunt_obj):
    """Writes a hunt object to the database.

    Args:
      hunt_obj: An rdf_hunt_objects.Hunt object to write.
    """

  @abc.abstractmethod
  def ReadHuntObject(self, hunt_id):
    """Reads a hunt object from the database.

    Args:
      hunt_id: The id of the hunt to read.

    Raises:
      UnknownHuntError: if there's no hunt with the corresponding id.

    Returns:
      An rdf_hunt_objects.Hunt object.
    """

  @abc.abstractmethod
  def ReadAllHuntObjects(self):
    """Reads all hunt objects from the database.

    Returns:
      A list of rdf_hunt_objects.Hunt objects.
    """

  @abc.abstractmethod
  def ReadHuntLogEntries(self, hunt_id, offset, count, with_substring=None):
    """Reads hunt log entries of a given hunt using given query options.

    Args:
      hunt_id: The id of the hunt to read log entries for.
      offset: An integer specifying an offset to be used when reading log
        entries. "offset" is applied after the with_substring filter is applied
        (if specified).
      count: Number of log entries to read. "count" is applied after the
        with_substring filter is applied (if specified).
      with_substring: (Optional) When specified, should be a string. Only log
        entries having the specified string as a message substring will be
        returned.

    Returns:
      A list of FlowLogEntry values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountHuntLogEntries(self, hunt_id):
    """Returns number of hunt log entries of a given hunt.

    Args:
      hunt_id: The id of the hunt to count log entries for.

    Returns:
      Number of hunt log entries of a given hunt.
    """

  @abc.abstractmethod
  def ReadHuntResults(self,
                      hunt_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    """Reads hunt results of a given hunt using given query options.

    If both with_tag and with_type and/or with_substring arguments are provided,
    they will be applied using AND boolean operator.

    Args:
      hunt_id: The id of the hunt to read results for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be returned.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be returned.
      with_substring: (Optional) When specified, should be a string. Only
        results having the specified string as a substring in their serialized
        form will be returned.

    Returns:
      A list of FlowResult values sorted by timestamp in ascending order.
    """

  @abc.abstractmethod
  def CountHuntResults(self, hunt_id, with_tag=None, with_type=None):
    """Counts hunt results of a given hunt using given query options.

    If both with_tag and with_type arguments are provided, they will be applied
    using AND boolean operator.

    Args:
      hunt_id: The id of the hunt to count results for.
      with_tag: (Optional) When specified, should be a string. Only results
        having specified tag will be accounted for.
      with_type: (Optional) When specified, should be a string. Only results of
        a specified type will be accounted for.

    Returns:
      A number of hunt results of a given hunt matching given query options.
    """

  @abc.abstractmethod
  def ReadHuntFlows(self,
                    hunt_id,
                    offset,
                    count,
                    filter_condition=HuntFlowsCondition.UNSET):
    """Reads hunt flows matching given conditins.

    If more than one condition is specified, all of them have to be fulfilled
    for a particular flow object to be returned (i.e. they're applied with AND).

    Args:
      hunt_id: The id of the hunt to read log entries for.
      offset: An integer specifying an offset to be used when reading results.
        "offset" is applied after with_tag/with_type/with_substring filters are
        applied.
      count: Number of results to read. "count" is applied after
        with_tag/with_type/with_substring filters are applied.
      filter_condition: One of HuntFlowsCondition constants describing a
        condition to filter ReadHuntFlows results.

    Returns:
      A list of Flow objects.
    """

  @abc.abstractmethod
  def CountHuntFlows(self, hunt_id, filter_condition=HuntFlowsCondition.UNSET):
    """Counts hunt flows matching given conditions.

    If more than one condition is specified, all of them have to be fulfilled
    for a particular flow object to be returned (i.e. they're applied with AND).

    Args:
      hunt_id: The id of the hunt to read log entries for.
        with_tag/with_type/with_substring filters are applied.
      filter_condition: One of HuntFlowsCondition constants describing a
        condition to influence CountHuntFlows results.

    Returns:
      A number of flows matching the specified condition.
    """

  @abc.abstractmethod
  def WriteSignedBinaryReferences(self, binary_id, references):
    """Writes blob references for a signed binary to the DB.

    Args:
      binary_id: rdf_objects.SignedBinaryID for the binary.
      references: rdf_objects.BlobReferences for the given binary.
    """

  @abc.abstractmethod
  def ReadSignedBinaryReferences(self, binary_id):
    """Reads blob references for the signed binary with the given id.

    Args:
      binary_id: rdf_objects.SignedBinaryID for the binary.

    Returns:
      A tuple of the signed binary's rdf_objects.BlobReferences and an
      RDFDatetime representing the time when the references were written to the
      DB.
    """

  @abc.abstractmethod
  def ReadIDsForAllSignedBinaries(self):
    """Returns ids for all signed binaries in the DB."""

  @abc.abstractmethod
  def DeleteSignedBinaryReferences(self, binary_id):
    """Deletes blob references for the given signed binary from the DB.

    Does nothing if no entry with the given id exists in the DB.

    Args:
      binary_id: rdf_objects.SignedBinaryID for the signed binary reference to
        delete.
    """


class DatabaseValidationWrapper(Database):
  """Database wrapper that validates the arguments."""

  def __init__(self, delegate):
    super(DatabaseValidationWrapper, self).__init__()
    self.delegate = delegate

  def WriteArtifact(self, artifact):
    precondition.AssertType(artifact, rdf_artifacts.Artifact)
    if not artifact.name:
      raise ValueError("Empty artifact name")

    return self.delegate.WriteArtifact(artifact)

  def ReadArtifact(self, name):
    precondition.AssertType(name, unicode)
    return self.delegate.ReadArtifact(name)

  def ReadAllArtifacts(self):
    return self.delegate.ReadAllArtifacts()

  def DeleteArtifact(self, name):
    precondition.AssertType(name, unicode)
    return self.delegate.DeleteArtifact(name)

  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None):
    _ValidateClientId(client_id)
    precondition.AssertOptionalType(certificate, rdf_crypto.RDFX509Cert)
    precondition.AssertOptionalType(last_ip, rdf_client_network.NetworkAddress)

    return self.delegate.WriteClientMetadata(
        client_id,
        certificate=certificate,
        fleetspeak_enabled=fleetspeak_enabled,
        first_seen=first_seen,
        last_ping=last_ping,
        last_clock=last_clock,
        last_ip=last_ip,
        last_foreman=last_foreman)

  def MultiReadClientMetadata(self, client_ids):
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientMetadata(client_ids)

  def WriteClientSnapshot(self, client):
    precondition.AssertType(client, rdf_objects.ClientSnapshot)
    return self.delegate.WriteClientSnapshot(client)

  def MultiReadClientSnapshot(self, client_ids):
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientSnapshot(client_ids)

  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientFullInfo(
        client_ids, min_last_ping=min_last_ping)

  def ReadAllClientIDs(self):
    return self.delegate.ReadAllClientIDs()

  def WriteClientSnapshotHistory(self, clients):
    if not clients:
      raise ValueError("Clients are empty")

    client_id = None
    for client in clients:
      precondition.AssertType(client, rdf_objects.ClientSnapshot)

      if client.timestamp is None:
        raise AttributeError("Client without a `timestamp` attribute")

      client_id = client_id or client.client_id
      if client.client_id != client_id:
        message = "Unexpected client id '%s' instead of '%s'"
        raise ValueError(message % (client.client_id, client_id))

    return self.delegate.WriteClientSnapshotHistory(clients)

  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    _ValidateClientId(client_id)
    if timerange is not None:
      _ValidateTimeRange(timerange)

    return self.delegate.ReadClientSnapshotHistory(
        client_id, timerange=timerange)

  def WriteClientStartupInfo(self, client_id, startup_info):
    precondition.AssertType(startup_info, rdf_client.StartupInfo)
    _ValidateClientId(client_id)

    return self.delegate.WriteClientStartupInfo(client_id, startup_info)

  def ReadClientStartupInfo(self, client_id):
    _ValidateClientId(client_id)

    return self.delegate.ReadClientStartupInfo(client_id)

  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
    _ValidateClientId(client_id)
    if timerange is not None:
      _ValidateTimeRange(timerange)

    return self.delegate.ReadClientStartupInfoHistory(
        client_id, timerange=timerange)

  def WriteClientCrashInfo(self, client_id, crash_info):
    precondition.AssertType(crash_info, rdf_client.ClientCrash)
    _ValidateClientId(client_id)

    return self.delegate.WriteClientCrashInfo(client_id, crash_info)

  def ReadClientCrashInfo(self, client_id):
    _ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfo(client_id)

  def ReadClientCrashInfoHistory(self, client_id):
    _ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfoHistory(client_id)

  def AddClientKeywords(self, client_id, keywords):
    _ValidateClientId(client_id)

    return self.delegate.AddClientKeywords(client_id, keywords)

  def ListClientsForKeywords(self, keywords, start_time=None):
    keywords = set(keywords)
    keyword_mapping = {utils.SmartStr(kw): kw for kw in keywords}

    if len(keyword_mapping) != len(keywords):
      raise ValueError("Multiple keywords map to the same string "
                       "representation.")

    if start_time:
      _ValidateTimestamp(start_time)

    return self.delegate.ListClientsForKeywords(keywords, start_time=start_time)

  def RemoveClientKeyword(self, client_id, keyword):
    _ValidateClientId(client_id)

    return self.delegate.RemoveClientKeyword(client_id, keyword)

  def AddClientLabels(self, client_id, owner, labels):
    _ValidateClientId(client_id)
    _ValidateUsername(owner)
    for label in labels:
      _ValidateLabel(label)

    return self.delegate.AddClientLabels(client_id, owner, labels)

  def MultiReadClientLabels(self, client_ids):
    _ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientLabels(client_ids)

  def RemoveClientLabels(self, client_id, owner, labels):
    _ValidateClientId(client_id)
    for label in labels:
      _ValidateLabel(label)

    return self.delegate.RemoveClientLabels(client_id, owner, labels)

  def ReadAllClientLabels(self):
    return self.delegate.ReadAllClientLabels()

  def WriteForemanRule(self, rule):
    precondition.AssertType(rule, foreman_rules.ForemanCondition)

    if not rule.hunt_id:
      raise ValueError("Foreman rule has no hunt_id: %s" % rule)

    return self.delegate.WriteForemanRule(rule)

  def RemoveForemanRule(self, hunt_id):
    _ValidateHuntId(hunt_id)
    return self.delegate.RemoveForemanRule(hunt_id)

  def ReadAllForemanRules(self):
    return self.delegate.ReadAllForemanRules()

  def RemoveExpiredForemanRules(self):
    return self.delegate.RemoveExpiredForemanRules()

  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None):
    _ValidateUsername(username)

    if password is not None and not isinstance(password, rdf_crypto.Password):
      password_str = password
      password = rdf_crypto.Password()
      password.SetPassword(password_str)

    return self.delegate.WriteGRRUser(
        username,
        password=password,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type)

  def ReadGRRUser(self, username):
    _ValidateUsername(username)

    return self.delegate.ReadGRRUser(username)

  def ReadGRRUsers(self, offset=0, count=None):
    if offset < 0:
      raise ValueError("offset has to be non-negative.")

    if count is not None and count < 0:
      raise ValueError("count has to be non-negative or None.")

    return self.delegate.ReadGRRUsers(offset=offset, count=count)

  def CountGRRUsers(self):
    return self.delegate.CountGRRUsers()

  def DeleteGRRUser(self, username):
    _ValidateUsername(username)

    return self.delegate.DeleteGRRUser(username)

  def WriteApprovalRequest(self, approval_request):
    precondition.AssertType(approval_request, rdf_objects.ApprovalRequest)
    _ValidateUsername(approval_request.requestor_username)
    _ValidateApprovalType(approval_request.approval_type)

    return self.delegate.WriteApprovalRequest(approval_request)

  def ReadApprovalRequest(self, requestor_username, approval_id):
    _ValidateUsername(requestor_username)
    _ValidateApprovalId(approval_id)

    return self.delegate.ReadApprovalRequest(requestor_username, approval_id)

  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False):
    _ValidateUsername(requestor_username)
    _ValidateApprovalType(approval_type)

    if subject_id is not None:
      _ValidateStringId("approval subject id", subject_id)

    return self.delegate.ReadApprovalRequests(
        requestor_username,
        approval_type,
        subject_id=subject_id,
        include_expired=include_expired)

  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    _ValidateUsername(requestor_username)
    _ValidateApprovalId(approval_id)
    _ValidateUsername(grantor_username)

    return self.delegate.GrantApproval(requestor_username, approval_id,
                                       grantor_username)

  def ReadPathInfo(self, client_id, path_type, components, timestamp=None):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    _ValidatePathComponents(components)

    if timestamp is not None:
      _ValidateTimestamp(timestamp)

    return self.delegate.ReadPathInfo(
        client_id, path_type, components, timestamp=timestamp)

  def ReadPathInfos(self, client_id, path_type, components_list):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    precondition.AssertType(components_list, list)
    for components in components_list:
      _ValidatePathComponents(components)

    return self.delegate.ReadPathInfos(client_id, path_type, components_list)

  def ListChildPathInfos(self, client_id, path_type, components,
                         timestamp=None):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    _ValidatePathComponents(components)
    precondition.AssertOptionalType(timestamp, rdfvalue.RDFDatetime)

    return self.delegate.ListChildPathInfos(
        client_id, path_type, components, timestamp=timestamp)

  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              timestamp=None,
                              max_depth=None):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    _ValidatePathComponents(components)
    precondition.AssertOptionalType(timestamp, rdfvalue.RDFDatetime)
    precondition.AssertOptionalType(max_depth, int)

    return self.delegate.ListDescendentPathInfos(
        client_id,
        path_type,
        components,
        timestamp=timestamp,
        max_depth=max_depth)

  def FindPathInfoByPathID(self, client_id, path_type, path_id, timestamp=None):
    _ValidateClientId(client_id)

    if timestamp is not None:
      _ValidateTimestamp(timestamp)

    return self.delegate.FindPathInfoByPathID(
        client_id, path_type, path_id, timestamp=timestamp)

  def FindPathInfosByPathIDs(self, client_id, path_type, path_ids):
    _ValidateClientId(client_id)

    return self.delegate.FindPathInfosByPathIDs(client_id, path_type, path_ids)

  def WritePathInfos(self, client_id, path_infos):
    _ValidateClientId(client_id)
    _ValidatePathInfos(path_infos)
    return self.delegate.WritePathInfos(client_id, path_infos)

  def MultiWritePathInfos(self, path_infos):
    precondition.AssertType(path_infos, dict)
    for client_id, client_path_infos in iteritems(path_infos):
      _ValidateClientId(client_id)
      _ValidatePathInfos(client_path_infos)

    return self.delegate.MultiWritePathInfos(path_infos)

  def InitPathInfos(self, client_id, path_infos):
    _ValidateClientId(client_id)
    _ValidatePathInfos(path_infos)
    return self.delegate.InitPathInfos(client_id, path_infos)

  def MultiInitPathInfos(self, path_infos):
    precondition.AssertType(path_infos, dict)
    for client_id, client_path_infos in iteritems(path_infos):
      _ValidateClientId(client_id)
      _ValidatePathInfos(client_path_infos)

    return self.delegate.MultiInitPathInfos(path_infos)

  def ClearPathHistory(self, client_id, path_infos):
    _ValidateClientId(client_id)
    _ValidatePathInfos(path_infos)

    return self.delegate.ClearPathHistory(client_id, path_infos)

  def MultiClearPathHistory(self, path_infos):
    precondition.AssertType(path_infos, dict)
    for client_id, client_path_infos in iteritems(path_infos):
      _ValidateClientId(client_id)
      _ValidatePathInfos(client_path_infos)

    return self.delegate.MultiClearPathHistory(path_infos)

  def MultiWritePathHistory(self, client_path_histories):
    precondition.AssertType(client_path_histories, dict)
    for client_path, client_path_history in iteritems(client_path_histories):
      precondition.AssertType(client_path, ClientPath)
      precondition.AssertType(client_path_history, ClientPathHistory)

    self.delegate.MultiWritePathHistory(client_path_histories)

  def FindDescendentPathIDs(self, client_id, path_type, path_id,
                            max_depth=None):
    _ValidateClientId(client_id)

    return self.delegate.FindDescendentPathIDs(
        client_id, path_type, path_id, max_depth=max_depth)

  def WriteUserNotification(self, notification):
    precondition.AssertType(notification, rdf_objects.UserNotification)
    _ValidateUsername(notification.username)
    _ValidateNotificationType(notification.notification_type)
    _ValidateNotificationState(notification.state)

    return self.delegate.WriteUserNotification(notification)

  def ReadUserNotifications(self, username, state=None, timerange=None):
    _ValidateUsername(username)
    if timerange is not None:
      _ValidateTimeRange(timerange)
    if state is not None:
      _ValidateNotificationState(state)

    return self.delegate.ReadUserNotifications(
        username, state=state, timerange=timerange)

  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    _ValidateClientId(client_id)
    _ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    precondition.AssertType(components_list, list)
    for components in components_list:
      _ValidatePathComponents(components)

    return self.delegate.ReadPathInfosHistories(client_id, path_type,
                                                components_list)

  def ReadLatestPathInfosWithHashBlobReferences(self,
                                                client_paths,
                                                max_timestamp=None):
    precondition.AssertIterableType(client_paths, ClientPath)
    precondition.AssertOptionalType(max_timestamp, rdfvalue.RDFDatetime)
    return self.delegate.ReadLatestPathInfosWithHashBlobReferences(
        client_paths, max_timestamp=max_timestamp)

  def UpdateUserNotifications(self, username, timestamps, state=None):
    _ValidateNotificationState(state)

    return self.delegate.UpdateUserNotifications(
        username, timestamps, state=state)

  def ReadAPIAuditEntries(self,
                          username=None,
                          router_method_name=None,
                          min_timestamp=None,
                          max_timestamp=None):
    return self.delegate.ReadAPIAuditEntries(
        username=username,
        router_method_name=router_method_name,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp)

  def WriteAPIAuditEntry(self, entry):
    precondition.AssertType(entry, rdf_objects.APIAuditEntry)
    return self.delegate.WriteAPIAuditEntry(entry)

  def WriteMessageHandlerRequests(self, requests):
    precondition.AssertIterableType(requests, rdf_objects.MessageHandlerRequest)
    return self.delegate.WriteMessageHandlerRequests(requests)

  def DeleteMessageHandlerRequests(self, requests):
    return self.delegate.DeleteMessageHandlerRequests(requests)

  def ReadMessageHandlerRequests(self):
    return self.delegate.ReadMessageHandlerRequests()

  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    if handler is None:
      raise ValueError("handler must be provided")

    _ValidateDuration(lease_time)
    return self.delegate.RegisterMessageHandler(
        handler, lease_time, limit=limit)

  def UnregisterMessageHandler(self, timeout=None):
    return self.delegate.UnregisterMessageHandler(timeout=timeout)

  def WriteCronJob(self, cronjob):
    precondition.AssertType(cronjob, rdf_cronjobs.CronJob)
    return self.delegate.WriteCronJob(cronjob)

  def ReadCronJob(self, cronjob_id):
    _ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJob(cronjob_id)

  def ReadCronJobs(self, cronjob_ids=None):
    if cronjob_ids is not None:
      for cronjob_id in cronjob_ids:
        _ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJobs(cronjob_ids=cronjob_ids)

  def EnableCronJob(self, cronjob_id):
    _ValidateCronJobId(cronjob_id)
    return self.delegate.EnableCronJob(cronjob_id)

  def DisableCronJob(self, cronjob_id):
    _ValidateCronJobId(cronjob_id)
    return self.delegate.DisableCronJob(cronjob_id)

  def DeleteCronJob(self, cronjob_id):
    _ValidateCronJobId(cronjob_id)
    return self.delegate.DeleteCronJob(cronjob_id)

  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=Database.unchanged,
                    last_run_time=Database.unchanged,
                    current_run_id=Database.unchanged,
                    state=Database.unchanged,
                    forced_run_requested=Database.unchanged):
    _ValidateCronJobId(cronjob_id)
    if current_run_id is not None and current_run_id != Database.unchanged:
      _ValidateCronJobRunId(current_run_id)
    return self.delegate.UpdateCronJob(
        cronjob_id,
        last_run_status=last_run_status,
        last_run_time=last_run_time,
        current_run_id=current_run_id,
        state=state,
        forced_run_requested=forced_run_requested)

  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None):
    if cronjob_ids:
      for cronjob_id in cronjob_ids:
        _ValidateCronJobId(cronjob_id)
    _ValidateDuration(lease_time)
    return self.delegate.LeaseCronJobs(
        cronjob_ids=cronjob_ids, lease_time=lease_time)

  def ReturnLeasedCronJobs(self, jobs):
    for job in jobs:
      precondition.AssertType(job, rdf_cronjobs.CronJob)
    return self.delegate.ReturnLeasedCronJobs(jobs)

  def WriteCronJobRun(self, run_object):
    precondition.AssertType(run_object, rdf_cronjobs.CronJobRun)
    return self.delegate.WriteCronJobRun(run_object)

  def ReadCronJobRun(self, job_id, run_id):
    _ValidateCronJobId(job_id)
    _ValidateCronJobRunId(run_id)
    return self.delegate.ReadCronJobRun(job_id, run_id)

  def ReadCronJobRuns(self, job_id):
    _ValidateCronJobId(job_id)
    return self.delegate.ReadCronJobRuns(job_id)

  def DeleteOldCronJobRuns(self, cutoff_timestamp):
    _ValidateTimestamp(cutoff_timestamp)
    return self.delegate.DeleteOldCronJobRuns(cutoff_timestamp)

  def WriteHashBlobReferences(self, references_by_hash):
    for h, refs in references_by_hash.items():
      _ValidateSHA256HashID(h)
      precondition.AssertIterableType(refs, rdf_objects.BlobReference)

    self.delegate.WriteHashBlobReferences(references_by_hash)

  def ReadHashBlobReferences(self, hashes):
    precondition.AssertIterableType(hashes, rdf_objects.SHA256HashID)
    return self.delegate.ReadHashBlobReferences(hashes)

  def WriteBlobs(self, blob_id_data_map):
    for bid, data in iteritems(blob_id_data_map):
      _ValidateBlobID(bid)
      _ValidateBytes(data)

    return self.delegate.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    for bid in blob_ids:
      _ValidateBlobID(bid)

    return self.delegate.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    for bid in blob_ids:
      _ValidateBlobID(bid)

    return self.delegate.CheckBlobsExist(blob_ids)

  def WriteClientMessages(self, messages):
    for message in messages:
      precondition.AssertType(message, rdf_flows.GrrMessage)
    return self.delegate.WriteClientMessages(messages)

  def LeaseClientMessages(self, client_id, lease_time=None, limit=1000000):
    _ValidateClientId(client_id)
    _ValidateDuration(lease_time)
    return self.delegate.LeaseClientMessages(
        client_id, lease_time=lease_time, limit=limit)

  def ReadClientMessages(self, client_id):
    _ValidateClientId(client_id)
    return self.delegate.ReadClientMessages(client_id)

  def DeleteClientMessages(self, messages):
    for message in messages:
      precondition.AssertType(message, rdf_flows.GrrMessage)
    return self.delegate.DeleteClientMessages(messages)

  def WriteFlowObject(self, flow_obj):
    precondition.AssertType(flow_obj, rdf_flow_objects.Flow)
    precondition.AssertType(flow_obj.create_time, rdfvalue.RDFDatetime)
    return self.delegate.WriteFlowObject(flow_obj)

  def ReadFlowObject(self, client_id, flow_id):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    return self.delegate.ReadFlowObject(client_id, flow_id)

  def ReadAllFlowObjects(self, client_id, min_create_time=None):
    _ValidateClientId(client_id)
    return self.delegate.ReadAllFlowObjects(
        client_id, min_create_time=min_create_time)

  def ReadChildFlowObjects(self, client_id, flow_id):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    return self.delegate.ReadChildFlowObjects(client_id, flow_id)

  def ReadFlowForProcessing(self, client_id, flow_id, processing_time):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    _ValidateDuration(processing_time)
    return self.delegate.ReadFlowForProcessing(client_id, flow_id,
                                               processing_time)

  def ReturnProcessedFlow(self, flow_obj):
    precondition.AssertType(flow_obj, rdf_flow_objects.Flow)
    return self.delegate.ReturnProcessedFlow(flow_obj)

  def UpdateFlow(self,
                 client_id,
                 flow_id,
                 flow_obj=Database.unchanged,
                 client_crash_info=Database.unchanged,
                 pending_termination=Database.unchanged,
                 processing_on=Database.unchanged,
                 processing_since=Database.unchanged,
                 processing_deadline=Database.unchanged):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    if flow_obj != Database.unchanged:
      precondition.AssertType(flow_obj, rdf_flow_objects.Flow)
    if client_crash_info != Database.unchanged:
      precondition.AssertType(client_crash_info, rdf_client.ClientCrash)
    if pending_termination != Database.unchanged:
      precondition.AssertType(pending_termination,
                              rdf_flow_objects.PendingFlowTermination)
    if processing_since != Database.unchanged:
      if processing_since is not None:
        _ValidateTimestamp(processing_since)
    if processing_deadline != Database.unchanged:
      if processing_since is not None:
        _ValidateTimestamp(processing_deadline)
    return self.delegate.UpdateFlow(
        client_id,
        flow_id,
        flow_obj=flow_obj,
        client_crash_info=client_crash_info,
        pending_termination=pending_termination,
        processing_on=processing_on,
        processing_since=processing_since,
        processing_deadline=processing_deadline)

  def UpdateFlows(self,
                  client_id_flow_id_pairs,
                  pending_termination=Database.unchanged):
    for client_id, flow_id in client_id_flow_id_pairs:
      _ValidateClientId(client_id)
      _ValidateFlowId(flow_id)

    if pending_termination != Database.unchanged:
      precondition.AssertType(pending_termination,
                              rdf_flow_objects.PendingFlowTermination)

    return self.delegate.UpdateFlows(
        client_id_flow_id_pairs, pending_termination=pending_termination)

  def WriteFlowRequests(self, requests):
    precondition.AssertIterableType(requests, rdf_flow_objects.FlowRequest)
    return self.delegate.WriteFlowRequests(requests)

  def DeleteFlowRequests(self, requests):
    precondition.AssertIterableType(requests, rdf_flow_objects.FlowRequest)
    return self.delegate.DeleteFlowRequests(requests)

  def WriteFlowResponses(self, responses):
    precondition.AssertIterableType(responses, (rdf_flow_objects.FlowMessage))
    return self.delegate.WriteFlowResponses(responses)

  def ReadAllFlowRequestsAndResponses(self, client_id, flow_id):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    return self.delegate.ReadAllFlowRequestsAndResponses(client_id, flow_id)

  def DeleteAllFlowRequestsAndResponses(self, client_id, flow_id):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    return self.delegate.DeleteAllFlowRequestsAndResponses(client_id, flow_id)

  def ReadFlowRequestsReadyForProcessing(self,
                                         client_id,
                                         flow_id,
                                         next_needed_request=None):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    if next_needed_request is None:
      raise ValueError("next_needed_request must be provided.")
    return self.delegate.ReadFlowRequestsReadyForProcessing(
        client_id, flow_id, next_needed_request=next_needed_request)

  def WriteFlowProcessingRequests(self, requests):
    precondition.AssertIterableType(requests, rdf_flows.FlowProcessingRequest)
    return self.delegate.WriteFlowProcessingRequests(requests)

  def ReadFlowProcessingRequests(self):
    return self.delegate.ReadFlowProcessingRequests()

  def AckFlowProcessingRequests(self, requests):
    precondition.AssertIterableType(requests, rdf_flows.FlowProcessingRequest)
    return self.delegate.AckFlowProcessingRequests(requests)

  def DeleteAllFlowProcessingRequests(self):
    return self.delegate.DeleteAllFlowProcessingRequests()

  def RegisterFlowProcessingHandler(self, handler):
    if handler is None:
      raise ValueError("handler must be provided")
    return self.delegate.RegisterFlowProcessingHandler(handler)

  def UnregisterFlowProcessingHandler(self, timeout=None):
    return self.delegate.UnregisterFlowProcessingHandler(timeout=timeout)

  def WriteFlowResults(self, client_id, flow_id, results):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    precondition.AssertIterableType(results, rdf_flow_objects.FlowResult)

    return self.delegate.WriteFlowResults(client_id, flow_id, results)

  def ReadFlowResults(self,
                      client_id,
                      flow_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, unicode)
    precondition.AssertOptionalType(with_type, unicode)
    precondition.AssertOptionalType(with_substring, unicode)

    return self.delegate.ReadFlowResults(
        client_id,
        flow_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_substring=with_substring)

  def CountFlowResults(
      self,
      client_id,
      flow_id,
      with_tag=None,
      with_type=None,
  ):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_tag, unicode)
    precondition.AssertOptionalType(with_type, unicode)

    return self.delegate.CountFlowResults(
        client_id, flow_id, with_tag=with_tag, with_type=with_type)

  def WriteFlowLogEntries(self, client_id, flow_id, entries):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    precondition.AssertIterableType(entries, rdf_flow_objects.FlowLogEntry)

    return self.delegate.WriteFlowLogEntries(client_id, flow_id, entries)

  def ReadFlowLogEntries(self,
                         client_id,
                         flow_id,
                         offset,
                         count,
                         with_substring=None):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)
    precondition.AssertOptionalType(with_substring, unicode)

    return self.delegate.ReadFlowLogEntries(
        client_id, flow_id, offset, count, with_substring=with_substring)

  def CountFlowLogEntries(self, client_id, flow_id):
    _ValidateClientId(client_id)
    _ValidateFlowId(flow_id)

    return self.delegate.CountFlowLogEntries(client_id, flow_id)

  def WriteStatsStoreEntries(self, stats_entries):
    _ValidateStatsStoreEntries(stats_entries)

    self.delegate.WriteStatsStoreEntries(stats_entries)

  def ReadStatsStoreEntries(self,
                            process_id_prefix,
                            metric_name,
                            time_range=None,
                            max_results=0):
    precondition.AssertType(process_id_prefix, unicode)
    precondition.AssertType(metric_name, unicode)
    if time_range is not None:
      # Both start- and end-timestamps must be provided if a time_range is
      # given.
      time_range_start, time_range_end = time_range
      _ValidateTimestamp(time_range_start)
      _ValidateTimestamp(time_range_end)
      if time_range_start > time_range_end:
        raise ValueError("Invalid time-range: %d > %d." %
                         (time_range_start.AsMicrosecondsSinceEpoch(),
                          time_range_end.AsMicrosecondsSinceEpoch()))

    return self.delegate.ReadStatsStoreEntries(
        process_id_prefix,
        metric_name,
        time_range=time_range,
        max_results=max_results)

  def DeleteStatsStoreEntriesOlderThan(self, cutoff, limit):
    _ValidateTimestamp(cutoff)
    if limit <= 0:
      raise ValueError("Limit must be > 0.")

    return self.delegate.DeleteStatsStoreEntriesOlderThan(cutoff, limit)

  def WriteHuntObject(self, hunt_obj):
    precondition.AssertType(hunt_obj, rdf_hunt_objects.Hunt)
    self.delegate.WriteHuntObject(hunt_obj)

  def ReadHuntObject(self, hunt_id):
    _ValidateHuntId(hunt_id)
    return self.delegate.ReadHuntObject(hunt_id)

  def ReadAllHuntObjects(self):
    return self.delegate.ReadAllHuntObjects()

  def ReadHuntLogEntries(self, hunt_id, offset, count, with_substring=None):
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_substring, unicode)

    return self.delegate.ReadHuntLogEntries(
        hunt_id, offset, count, with_substring=with_substring)

  def CountHuntLogEntries(self, hunt_id):
    _ValidateHuntId(hunt_id)
    return self.delegate.CountHuntLogEntries(hunt_id)

  def ReadHuntResults(self,
                      hunt_id,
                      offset,
                      count,
                      with_tag=None,
                      with_type=None,
                      with_substring=None):
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_tag, unicode)
    precondition.AssertOptionalType(with_type, unicode)
    precondition.AssertOptionalType(with_substring, unicode)
    return self.delegate.ReadHuntResults(
        hunt_id,
        offset,
        count,
        with_tag=with_tag,
        with_type=with_type,
        with_substring=with_substring)

  def CountHuntResults(self, hunt_id, with_tag=None, with_type=None):
    _ValidateHuntId(hunt_id)
    precondition.AssertOptionalType(with_tag, unicode)
    precondition.AssertOptionalType(with_type, unicode)
    return self.delegate.CountHuntResults(
        hunt_id, with_tag=with_tag, with_type=with_type)

  def ReadHuntFlows(self,
                    hunt_id,
                    offset,
                    count,
                    filter_condition=HuntFlowsCondition.UNSET):
    _ValidateHuntId(hunt_id)
    _ValidateHuntFlowCondition(filter_condition)
    return self.delegate.ReadHuntFlows(
        hunt_id, offset, count, filter_condition=filter_condition)

  def CountHuntFlows(self, hunt_id, filter_condition=HuntFlowsCondition.UNSET):
    _ValidateHuntId(hunt_id)
    _ValidateHuntFlowCondition(filter_condition)
    return self.delegate.CountHuntFlows(
        hunt_id, filter_condition=filter_condition)

  def WriteSignedBinaryReferences(self, binary_id, references):
    precondition.AssertType(binary_id, rdf_objects.SignedBinaryID)
    precondition.AssertType(references, rdf_objects.BlobReferences)
    if not references.items:
      raise ValueError("No actual blob references provided.")

    self.delegate.WriteSignedBinaryReferences(binary_id, references)

  def ReadSignedBinaryReferences(self, binary_id):
    precondition.AssertType(binary_id, rdf_objects.SignedBinaryID)
    return self.delegate.ReadSignedBinaryReferences(binary_id)

  def ReadIDsForAllSignedBinaries(self):
    return self.delegate.ReadIDsForAllSignedBinaries()

  def DeleteSignedBinaryReferences(self, binary_id):
    precondition.AssertType(binary_id, rdf_objects.SignedBinaryID)
    return self.delegate.DeleteSignedBinaryReferences(binary_id)


def _ValidateEnumType(value, expected_enum_type):
  if value not in expected_enum_type.reverse_enum:
    message = "Expected one of `%s` but got `%s` instead"
    raise TypeError(message % (expected_enum_type.reverse_enum, value))


def _ValidateStringId(typename, value):
  precondition.AssertType(value, unicode)
  if not value:
    message = "Expected %s `%s` to be non-empty" % (typename, value)
    raise ValueError(message)


def _ValidateClientId(client_id):
  _ValidateStringId("client_id", client_id)
  # TODO(hanuszczak): Eventually, we should allow only either lower or upper
  # case letters in the client id.
  if re.match(r"^C\.[0-9A-Z]{16}$", client_id, re.IGNORECASE) is None:
    raise ValueError("Client id has incorrect format: `%s`" % client_id)


def _ValidateClientIds(client_ids):
  precondition.AssertIterableType(client_ids, unicode)
  for client_id in client_ids:
    _ValidateClientId(client_id)


def _ValidateFlowId(flow_id):
  _ValidateStringId("flow_id", flow_id)


def _ValidateHuntId(hunt_id):
  _ValidateStringId("hunt_id", hunt_id)


def _ValidateCronJobId(cron_job_id):
  _ValidateStringId("cron_job_id", cron_job_id)


def _ValidateCronJobRunId(cron_job_run_id):
  _ValidateStringId("cron_job_run_id", cron_job_run_id)
  # Raises TypeError if cron_job_id is not a valid hex number.
  int(cron_job_run_id, 16)
  if len(cron_job_run_id) != 8:
    raise ValueError("Invalid cron job run id: %s" % cron_job_run_id)


def _ValidateApprovalId(approval_id):
  _ValidateStringId("approval_id", approval_id)


def _ValidateApprovalType(approval_type):
  if (approval_type ==
      rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_NONE):
    raise ValueError("Unexpected approval type: %s" % approval_type)


def _ValidateUsername(username):
  _ValidateStringId("username", username)


def _ValidateLabel(label):
  _ValidateStringId("label", label)


def _ValidatePathInfo(path_info):
  precondition.AssertType(path_info, rdf_objects.PathInfo)
  if not path_info.path_type:
    raise ValueError(
        "Expected path_type to be set, got: %s" % path_info.path_type)


def _ValidatePathInfos(path_infos):
  """Validates a sequence of path infos."""
  precondition.AssertIterableType(path_infos, rdf_objects.PathInfo)

  validated = set()
  for path_info in path_infos:
    _ValidatePathInfo(path_info)

    path_key = (path_info.path_type, path_info.GetPathID())
    if path_key in validated:
      message = "Conflicting writes for path: '{path}' ({path_type})"
      message.format(
          path="/".join(path_info.components), path_type=path_info.path_type)
      raise ValueError(message)

    validated.add(path_key)


def _ValidatePathComponents(components):
  precondition.AssertIterableType(components, unicode)


def _ValidateNotificationType(notification_type):
  if notification_type is None:
    raise ValueError("notification_type can't be None")

  if notification_type == rdf_objects.UserNotification.Type.TYPE_UNSET:
    raise ValueError("notification_type can't be TYPE_UNSET")


def _ValidateNotificationState(notification_state):
  if notification_state is None:
    raise ValueError("notification_state can't be None")

  if notification_state == rdf_objects.UserNotification.State.STATE_UNSET:
    raise ValueError("notification_state can't be STATE_UNSET")


def _ValidateTimeRange(timerange):
  """Parses a timerange argument and always returns non-None timerange."""
  if len(timerange) != 2:
    raise ValueError("Timerange should be a sequence with 2 items.")

  (start, end) = timerange
  precondition.AssertOptionalType(start, rdfvalue.RDFDatetime)
  precondition.AssertOptionalType(end, rdfvalue.RDFDatetime)


def _ValidateDuration(duration):
  precondition.AssertType(duration, rdfvalue.Duration)


def _ValidateTimestamp(timestamp):
  precondition.AssertType(timestamp, rdfvalue.RDFDatetime)


def _ValidateClientPathID(client_path_id):
  precondition.AssertType(client_path_id, rdf_objects.ClientPathID)


def _ValidateBlobReference(blob_ref):
  precondition.AssertType(blob_ref, rdf_objects.BlobReference)


def _ValidateBlobID(blob_id):
  precondition.AssertType(blob_id, rdf_objects.BlobID)


def _ValidateBytes(value):
  precondition.AssertType(value, bytes)


def _ValidateSHA256HashID(sha256_hash_id):
  precondition.AssertType(sha256_hash_id, rdf_objects.SHA256HashID)


def _ValidateStatsStoreEntries(stats_entries):
  """Validates an Iterable of StatsStoreEntries."""
  for stats_entry in stats_entries:
    precondition.AssertType(stats_entry, stats_values.StatsStoreEntry)
    if not stats_entry.process_id:
      raise ValueError("StatsStoreEntry must have a process_id set.")
    if not stats_entry.metric_name:
      raise ValueError("StatsStoreEntry must have a metric_name set.")
    if not stats_entry.metric_value:
      raise ValueError("StatsStoreEntry must have a metric_value set.")
    if not stats_entry.timestamp:
      raise ValueError("StatsStoreEntry must have a timestamp set.")

    metric_metadata = stats_collector_instance.Get().GetMetricMetadata(
        stats_entry.metric_name)
    num_field_values = len(stats_entry.metric_value.fields_values)
    expected_num_field_values = len(metric_metadata.fields_defs)
    if num_field_values != expected_num_field_values:
      raise ValueError(
          "Value for metric %s had %d field values, yet the metric was "
          "defined to have %d fields." % (stats_entry.metric_name,
                                          num_field_values,
                                          expected_num_field_values))


def _ValidateHuntFlowCondition(value):
  if value < 0 or value > HuntFlowsCondition.MaxValue():
    raise ValueError("Invalid hunt flow condition: %d" % value)
