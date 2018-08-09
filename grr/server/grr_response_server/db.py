#!/usr/bin/env python
"""The GRR relational database abstraction.

This defines the Database abstraction, which defines the methods used by GRR on
a logical relational database model.

WIP, will eventually replace datastore.py.

"""
import abc


from future.utils import iteritems
from future.utils import itervalues
from future.utils import with_metaclass

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import foreman_rules
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects


class Error(Exception):

  def __init__(self, message="", cause=None):
    if cause is not None:
      message += ": %s" % cause

    super(Error, self).__init__(message)

    self.cause = cause


class NotFoundError(Error):
  pass


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
  pass


class UnknownApprovalRequestError(NotFoundError):
  pass


class UnknownCronJobError(NotFoundError):
  pass


class UnknownCronJobRunError(NotFoundError):
  pass


class Database(with_metaclass(abc.ABCMeta, object)):
  """The GRR relational database abstraction."""

  unchanged = "__unchanged__"

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
      last_foreman: And rdfvalue.Datetime, indicating the last time that the
        client sent a foreman message to the server.
    """

  @abc.abstractmethod
  def MultiReadClientMetadata(self, client_ids):
    """Reads ClientMetadata records for a list of clients.

    Args:
      client_ids: A collection of GRR client id strings,
        e.g. ["C.ea3b2b71840d6fa7", "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to rdfvalues.object.ClientMetadata.
    """

  def ReadClientMetadata(self, client_id):
    """Reads the ClientMetadata record for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.object.ClientMetadata object.
    """
    return self.MultiReadClientMetadata([client_id]).get(client_id)

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
    """
    return self.MultiReadClientFullInfo([client_id]).get(client_id)

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
               object should have a `timestamp` attribute specifying at which
               point this snapshot was taken. All clients should have the same
               client id.

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
      timerange: Should be either a tuple of (from, to) or None.
                 "from" and to" should be rdfvalue.RDFDatetime or None values
                 (from==None means "all record up to 'to'", to==None means
                 all records from 'from'). If both "to" and "from" are
                 None or the timerange itself is None, all history
                 items are fetched. Note: "from" and "to" are inclusive:
                 i.e. a from <= time <= to condition is applied.

    Returns:
      A list of rdfvalues.objects.ClientSnapshot, newest snapshot first.
    """

  @abc.abstractmethod
  def WriteClientStartupInfo(self, client_id, startup_info):
    """Writes a new client startup record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      startup_info: An rdfvalues.client.StartupInfo object. Will be saved at
          the "current" timestamp.

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
      timerange: Should be either a tuple of (from, to) or None.
                 "from" and to" should be rdfvalue.RDFDatetime or None values
                 (from==None means "all record up to 'to'", to==None means
                 all records from 'from'). If both "to" and "from" are
                 None or the timerange itself is None, all history
                 items are fetched. Note: "from" and "to" are inclusive:
                 i.e. a from <= time <= to condition is applied.

    Returns:
      A list of rdfvalues.client.StartupInfo objects sorted by timestamp,
      newest entry first.
    """

  @abc.abstractmethod
  def WriteClientCrashInfo(self, client_id, crash_info):
    """Writes a new client crash record.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      crash_info: An rdfvalues.objects.ClientCrash object. Will be saved at
          the "current" timestamp.

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

    Args:
      username: Name of a user to insert/update.
      password: If set, should be a string with a new encrypted user password.
      ui_mode: If set, should be a GUISettings.UIMode enum.
      canary_mode: If not None, should be a boolean indicating user's preferred
          canary mode setting.
      user_type: GRRUser.UserType enum describing user type
          (unset, standard or admin).
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
  def ReadAllGRRUsers(self):
    """Reads all GRR users.

    Returns:
      A generator yielding objects.GRRUser objects.
    """

  @abc.abstractmethod
  def WriteApprovalRequest(self, approval_request):
    """Writes an approval request object.

    Args:
      approval_request: rdfvalues.objects.ApprovalRequest object. Note:
                        approval_id and timestamps provided inside
                        the argument object will be ignored. Values generated
                        by the database will be used instead.
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
      subject_id: String identifying the subject (client id, hunt id or
                  cron job id). If not None, only approval requests for this
                  subject will be returned.
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

    for batch in utils.Grouper(all_client_ids, batch_size):
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

    for batch in utils.Grouper(all_client_ids, batch_size):
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
                 If none is provided, the latest known path information is
                 returned.

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

  def ListChildPathInfos(self, client_id, path_type, components):
    """Lists path info records that correspond to children of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve child path
                  information for.

    Returns:
      A list of `rdf_objects.PathInfo` instances sorted by path components.
    """
    return self.ListDescendentPathInfos(
        client_id, path_type, components, max_depth=1)

  @abc.abstractmethod
  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              max_depth=None):
    """Lists path info records that correspond to descendants of given path.

    Args:
      client_id: An identifier string for a client.
      path_type: A type of a path to retrieve path information for.
      components: A tuple of path components of a path to retrieve descendent
                  path information for.
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
  def InitPathInfos(self, client_id, path_infos):
    """Initializes a collection of path info records for a client.

    Unlike `WritePathInfo`, this method clears stat and hash histories of paths
    associated with path info records. This method is intended to be used only
    in the data migration scripts.

    Args:
      client_id: A client idenitfier for which the paths are to be initialized.
      path_infos: A list of `rdf_objects.PathInfo` objects to write.
    """

  # TODO(hanuszczak): Having a dictionary with mutable key as an argument is not
  # a good idea. The signature should be changed to something saner.
  @abc.abstractmethod
  def MultiWritePathHistory(self, client_id, stat_entries, hash_entries):
    """Writes a collection of hash and stat entries observed for given paths.

    Args:
      client_id: A client for which we want to write the history.
      stat_entries: An dictionary mapping path info to stat entries.
      hash_entries: An dictionary mapping path info to hash entries.
    """

  def WritePathStatHistory(self, client_id, path_info, stat_entries):
    """Writes a collection of `StatEntry` observed for particular path.

    Args:
      client_id: A client for which we want to write stat entries.
      path_info: Information about the path to write stat entries for. Note that
                 if `path_info` has some associated stat entry, it is simply
                 ignored.
      stat_entries: A dictionary with timestamps as keys and `StatEntry`
                    instances as values.
    """
    rstat_entries = {}
    for timestamp, stat_entry in iteritems(stat_entries):
      rpath_info = path_info.Copy()
      rpath_info.timestamp = timestamp
      rstat_entries[rpath_info] = stat_entry

    self.MultiWritePathHistory(client_id, rstat_entries, {})

  def WritePathHashHistory(self, client_id, path_info, hash_entries):
    """Writes a collection of `Hash` observed for particular path.

    Args:
      client_id: A client for which we want to write hash entries.
      path_info: Information about the path to write stat entries for. Note that
                 if `path_info` has some associated hash entry, it is simply
                 ignored.
      hash_entries: A dictionary with timestamps as keys and `Hash` instances
                    as values.
    """
    rhash_entries = {}
    for timestamp, hash_entry in iteritems(hash_entries):
      rpath_info = path_info.Copy()
      rpath_info.timestamp = timestamp
      rhash_entries[rpath_info] = hash_entry

    self.MultiWritePathHistory(client_id, {}, rhash_entries)

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
      timerange: Should be either a tuple of (from, to) or None.
                 "from" and to" should be rdfvalue.RDFDatetime or None values
                 (from==None means "all record up to 'to'", to==None means
                 all records from 'from'). If both "to" and "from" are
                 None or the timerange itself is None, all notifications
                 are fetched. Note: "from" and "to" are inclusive:
                 i.e. a from <= time <= to condition is applied.
    Returns:
      List of objects.UserNotification objects.
    """

  @abc.abstractmethod
  def UpdateUserNotifications(self, username, timestamps, state=None):
    """Updates existing user notification objects.

    Args:
      username: Username identifying the user.
      timestamps: List of timestamps of the notifications to be updated.
      state: objects.UserNotification.State enum value to be written into
             the notifications objects.
    """

  @abc.abstractmethod
  def ReadAllAuditEvents(self):
    """Reads all audit events stored in the database.

    The event log is sorted according to their timestamp (with the oldest
    recorded event being first).

    Returns:
      List of `rdf_events.AuditEvent` instances.
    """

  @abc.abstractmethod
  def WriteAuditEvent(self, event):
    """Writes an audit event to the database.

    Args:
      event: An `rdf_events.AuditEvent` instance.
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
  def UnregisterMessageHandler(self):
    """Unregisters any registered message handler."""

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
      cronjob_ids: A list of cronjob ids to read. If not set, returns all
                   cron jobs in the database.

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
      forced_run_requested: A boolean indicating if a forced run is pending
                            for this job.
    Raises:
      UnknownCronJobError: A cron job with the given id does not exist.
    """

  @abc.abstractmethod
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None):
    """Leases all available cron jobs.

    Args:
      cronjob_ids: A list of cronjob ids that should be leased. If None,
                   all available cronjobs will be leased.
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
  def WriteClientPathBlobReferences(self, references_by_client_path_id):
    """Writes blob references for given client path ids.

    Args:
      references_by_client_path_id: Dictionary of
          ClientPathID -> [BlobReference].

    Raises:
      AtLeastOneUnknownPathError: if one or more ClientPathIDs are not known
      to the database.
    """

  @abc.abstractmethod
  def ReadClientPathBlobReferences(self, client_path_ids):
    """Reads blob references of given client path ids.

    Args:
      client_path_ids: A list of ClientPathIDs.

    Returns:
      Dictionary of ClientPathID -> [BlobReference]. Every path id from
      the path_ids argument will be present in the result. "No blob references"
      will be expressed as empty list.
    """

  @abc.abstractmethod
  def WriteBlobs(self, blob_id_data_pairs):
    """Writes given blobs.

    Args:
      blob_id_data_pairs: An iterable of (blob_id, blob_data) tuples. Each
                          blob_id should be a blob hash (i.e. uniquely
                          idenitify the blob) expressed as bytes. blob_data
                          should be expressed in bytes.

    Raises:
      ValueError: If anything but a tuple of 2 elements is encountered in
                  blob_id_data_pairs.
    """

  @abc.abstractmethod
  def ReadBlobs(self, blob_ids):
    """Reads given blobs.

    Args:
      blob_ids: An iterable with blob hashes expressed as bytes.

    Returns:
      A map of {blob_id: blob_data} where blob_data is blob bytes previously
      written with WriteBlobs. If blob_data for particular blob are not found,
      blob_data is expressed as None.
    """

  @abc.abstractmethod
  def CheckBlobsExist(self, blob_ids):
    """Checks if given blobs exist.

    Args:
      blob_ids: An iterable with blob hashes expressed as bytes.

    Returns:
      A map of {blob_id: status} where status is a boolean (True if blob exists,
      False if it doesn't).
    """

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


class DatabaseValidationWrapper(Database):
  """Database wrapper that validates the arguments."""

  def __init__(self, delegate):
    super(DatabaseValidationWrapper, self).__init__()
    self.delegate = delegate

  @staticmethod
  def _ValidateType(value, expected_type):
    if not isinstance(value, expected_type):
      message = "Expected `%s` but got `%s` instead"
      raise TypeError(message % (expected_type, type(value)))

  @staticmethod
  def _ValidateEnumType(value, expected_enum_type):
    if value not in expected_enum_type.reverse_enum:
      message = "Expected one of `%s` but got `%s` instead"
      raise TypeError(message % (expected_enum_type.reverse_enum, value))

  def _ValidateStringId(self, id_type, id_value):
    if not isinstance(id_value, basestring):
      raise TypeError(
          "Expected %s as a string, got %s" % (id_type, type(id_value)))

    if not id_value:
      raise ValueError("Expected %s to be non-empty." % id_type)

  @classmethod
  def _ValidateString(cls, typename, value):
    if not isinstance(value, unicode):
      message = "Expected %s as a unicode string, got '%s' of type '%s' instead"
      message %= (typename, value, type(value))
      raise TypeError(message)

  def _ValidateClientId(self, client_id):
    self._ValidateStringId("client_id", client_id)

  def _ValidateClientIds(self, client_ids):
    self._ValidateType(client_ids, list)
    for client_id in client_ids:
      self._ValidateClientId(client_id)

  def _ValidateHuntId(self, hunt_id):
    self._ValidateString("hunt_id", hunt_id)

  def _ValidateCronJobId(self, cron_job_id):
    self._ValidateString("cron_job_id", cron_job_id)

  def _ValidateCronJobRunId(self, cron_job_run_id):
    if cron_job_run_id is not None:
      self._ValidateString("cron_job_run_id", cron_job_run_id)
      # Raises TypeError if cron_job_id is not a valid hex number.
      int(cron_job_run_id, 16)
      if len(cron_job_run_id) != 8:
        raise TypeError("Invalid cron job run id: %s" % cron_job_run_id)

  def _ValidateApprovalId(self, approval_id):
    self._ValidateString("approval_id", approval_id)

  def _ValidateApprovalType(self, approval_type):
    if (approval_type ==
        rdf_objects.ApprovalRequest.ApprovalType.APPROVAL_TYPE_NONE):
      raise ValueError("Unexpected approval type: %s" % approval_type)

  def _ValidateUsername(self, username):
    self._ValidateString("username", username)

  def _ValidateLabel(self, label):
    self._ValidateString("label", label)

  def _ValidatePathInfo(self, path_info):
    self._ValidateType(path_info, rdf_objects.PathInfo)
    if not path_info.path_type:
      raise ValueError(
          "Expected path_type to be set, got: %s" % str(path_info.path_type))

  def _ValidatePathInfos(self, path_infos):
    self._ValidateType(path_infos, list)

    validated = set()
    for path_info in path_infos:
      self._ValidatePathInfo(path_info)

      path_key = (path_info.path_type, path_info.GetPathID())
      if path_key in validated:
        message = "Conflicting writes for path: '{path}' ({path_type})"
        message.format(
            path="/".join(path_info.components), path_type=path_info.path_type)
        raise ValueError(message)

      validated.add(path_key)

  def _ValidatePathComponents(self, components):
    self._ValidateType(components, tuple)
    for component in components:
      self._ValidateType(component, unicode)

  def _ValidateNotificationType(self, notification_type):
    if notification_type is None:
      raise ValueError("notification_type can't be None")

    if notification_type == rdf_objects.UserNotification.Type.TYPE_UNSET:
      raise ValueError("notification_type can't be TYPE_UNSET")

  def _ValidateNotificationState(self, notification_state):
    if notification_state is None:
      raise ValueError("notification_state can't be None")

    if notification_state == rdf_objects.UserNotification.State.STATE_UNSET:
      raise ValueError("notification_state can't be STATE_UNSET")

  def _ValidateTimeRange(self, timerange):
    """Parses a timerange argument and always returns non-None timerange."""

    if timerange is None:
      return

    if len(timerange) != 2:
      raise ValueError("Timerange should be a sequence with 2 items.")

    for i in timerange:
      if i:
        self._ValidateTimestamp(i)

  def _ValidateDuration(self, duration):
    self._ValidateType(duration, rdfvalue.Duration)

  def _ValidateTimestamp(self, timestamp):
    self._ValidateType(timestamp, rdfvalue.RDFDatetime)

  def _ValidateClientPathID(self, client_path_id):
    self._ValidateType(client_path_id, rdf_objects.ClientPathID)

  def _ValidateBlobReference(self, blob_ref):
    self._ValidateType(blob_ref, rdf_objects.BlobReference)

  def _ValidateBlobID(self, blob_id):
    self._ValidateType(blob_id, rdf_objects.BlobID)

  def _ValidateBytes(self, value):
    self._ValidateType(value, bytes)

  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None):
    self._ValidateClientId(client_id)

    if certificate:
      self._ValidateType(certificate, rdf_crypto.RDFX509Cert)

    if last_ip:
      self._ValidateType(last_ip, rdf_client.NetworkAddress)

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
    self._ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientMetadata(client_ids)

  def WriteClientSnapshot(self, client):
    self._ValidateType(client, rdf_objects.ClientSnapshot)
    return self.delegate.WriteClientSnapshot(client)

  def MultiReadClientSnapshot(self, client_ids):
    self._ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientSnapshot(client_ids)

  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    self._ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientFullInfo(
        client_ids, min_last_ping=min_last_ping)

  def ReadAllClientIDs(self):
    return self.delegate.ReadAllClientIDs()

  def WriteClientSnapshotHistory(self, clients):
    if not clients:
      raise ValueError("Clients are empty")

    client_id = None
    for client in clients:
      self._ValidateType(client, rdf_objects.ClientSnapshot)

      if client.timestamp is None:
        raise AttributeError("Client without a `timestamp` attribute")

      client_id = client_id or client.client_id
      if client.client_id != client_id:
        message = "Unexpected client id '%s' instead of '%s'"
        raise ValueError(message % (client.client_id, client_id))

    return self.delegate.WriteClientSnapshotHistory(clients)

  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    self._ValidateClientId(client_id)
    self._ValidateTimeRange(timerange)

    return self.delegate.ReadClientSnapshotHistory(
        client_id, timerange=timerange)

  def WriteClientStartupInfo(self, client_id, startup_info):
    self._ValidateType(startup_info, rdf_client.StartupInfo)
    self._ValidateClientId(client_id)

    return self.delegate.WriteClientStartupInfo(client_id, startup_info)

  def ReadClientStartupInfo(self, client_id):
    self._ValidateClientId(client_id)

    return self.delegate.ReadClientStartupInfo(client_id)

  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
    self._ValidateClientId(client_id)
    self._ValidateTimeRange(timerange)

    return self.delegate.ReadClientStartupInfoHistory(
        client_id, timerange=timerange)

  def WriteClientCrashInfo(self, client_id, crash_info):
    self._ValidateType(crash_info, rdf_client.ClientCrash)
    self._ValidateClientId(client_id)

    return self.delegate.WriteClientCrashInfo(client_id, crash_info)

  def ReadClientCrashInfo(self, client_id):
    self._ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfo(client_id)

  def ReadClientCrashInfoHistory(self, client_id):
    self._ValidateClientId(client_id)

    return self.delegate.ReadClientCrashInfoHistory(client_id)

  def AddClientKeywords(self, client_id, keywords):
    self._ValidateClientId(client_id)

    return self.delegate.AddClientKeywords(client_id, keywords)

  def ListClientsForKeywords(self, keywords, start_time=None):
    keywords = set(keywords)
    keyword_mapping = {utils.SmartStr(kw): kw for kw in keywords}

    if len(keyword_mapping) != len(keywords):
      raise ValueError("Multiple keywords map to the same string "
                       "representation.")

    if start_time:
      self._ValidateTimestamp(start_time)

    return self.delegate.ListClientsForKeywords(keywords, start_time=start_time)

  def RemoveClientKeyword(self, client_id, keyword):
    self._ValidateClientId(client_id)

    return self.delegate.RemoveClientKeyword(client_id, keyword)

  def AddClientLabels(self, client_id, owner, labels):
    self._ValidateClientId(client_id)
    self._ValidateUsername(owner)
    for label in labels:
      self._ValidateLabel(label)

    return self.delegate.AddClientLabels(client_id, owner, labels)

  def MultiReadClientLabels(self, client_ids):
    self._ValidateClientIds(client_ids)
    return self.delegate.MultiReadClientLabels(client_ids)

  def RemoveClientLabels(self, client_id, owner, labels):
    self._ValidateClientId(client_id)
    for label in labels:
      self._ValidateLabel(label)

    return self.delegate.RemoveClientLabels(client_id, owner, labels)

  def ReadAllClientLabels(self):
    return self.delegate.ReadAllClientLabels()

  def WriteForemanRule(self, rule):
    self._ValidateType(rule, foreman_rules.ForemanCondition)

    if not rule.hunt_id:
      raise ValueError("Foreman rule has no hunt_id: %s" % rule)

    return self.delegate.WriteForemanRule(rule)

  def RemoveForemanRule(self, hunt_id):
    self._ValidateHuntId(hunt_id)
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
    self._ValidateUsername(username)

    return self.delegate.WriteGRRUser(
        username,
        password=password,
        ui_mode=ui_mode,
        canary_mode=canary_mode,
        user_type=user_type)

  def ReadGRRUser(self, username):
    self._ValidateUsername(username)

    return self.delegate.ReadGRRUser(username)

  def ReadAllGRRUsers(self):
    return self.delegate.ReadAllGRRUsers()

  def WriteApprovalRequest(self, approval_request):
    self._ValidateType(approval_request, rdf_objects.ApprovalRequest)
    self._ValidateUsername(approval_request.requestor_username)
    self._ValidateApprovalType(approval_request.approval_type)

    return self.delegate.WriteApprovalRequest(approval_request)

  def ReadApprovalRequest(self, requestor_username, approval_id):
    self._ValidateUsername(requestor_username)
    self._ValidateApprovalId(approval_id)

    return self.delegate.ReadApprovalRequest(requestor_username, approval_id)

  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False):
    self._ValidateUsername(requestor_username)
    self._ValidateApprovalType(approval_type)

    if subject_id is not None:
      self._ValidateStringId("approval subject id", subject_id)

    return self.delegate.ReadApprovalRequests(
        requestor_username,
        approval_type,
        subject_id=subject_id,
        include_expired=include_expired)

  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    self._ValidateUsername(requestor_username)
    self._ValidateApprovalId(approval_id)
    self._ValidateUsername(grantor_username)

    return self.delegate.GrantApproval(requestor_username, approval_id,
                                       grantor_username)

  def ReadPathInfo(self, client_id, path_type, components, timestamp=None):
    self._ValidateClientId(client_id)
    self._ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    self._ValidatePathComponents(components)

    if timestamp is not None:
      self._ValidateTimestamp(timestamp)

    return self.delegate.ReadPathInfo(
        client_id, path_type, components, timestamp=timestamp)

  def ReadPathInfos(self, client_id, path_type, components_list):
    self._ValidateClientId(client_id)
    self._ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    self._ValidateType(components_list, list)
    for components in components_list:
      self._ValidatePathComponents(components)

    return self.delegate.ReadPathInfos(client_id, path_type, components_list)

  def ListChildPathInfos(self, client_id, path_type, components):
    self._ValidateClientId(client_id)
    self._ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    self._ValidatePathComponents(components)

    return self.delegate.ListChildPathInfos(client_id, path_type, components)

  def ListDescendentPathInfos(self,
                              client_id,
                              path_type,
                              components,
                              max_depth=None):
    self._ValidateClientId(client_id)
    self._ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    self._ValidatePathComponents(components)

    return self.delegate.ListDescendentPathInfos(
        client_id, path_type, components, max_depth=max_depth)

  def FindPathInfoByPathID(self, client_id, path_type, path_id, timestamp=None):
    self._ValidateClientId(client_id)

    if timestamp is not None:
      self._ValidateTimestamp(timestamp)

    return self.delegate.FindPathInfoByPathID(
        client_id, path_type, path_id, timestamp=timestamp)

  def FindPathInfosByPathIDs(self, client_id, path_type, path_ids):
    self._ValidateClientId(client_id)

    return self.delegate.FindPathInfosByPathIDs(client_id, path_type, path_ids)

  def WritePathInfos(self, client_id, path_infos):
    self._ValidateClientId(client_id)
    self._ValidatePathInfos(path_infos)
    return self.delegate.WritePathInfos(client_id, path_infos)

  def InitPathInfos(self, client_id, path_infos):
    self._ValidateClientId(client_id)
    self._ValidatePathInfos(path_infos)
    return self.delegate.InitPathInfos(client_id, path_infos)

  def MultiWritePathHistory(self, client_id, stat_entries, hash_entries):
    self._ValidateClientId(client_id)

    for path_info, stat_entry in iteritems(stat_entries):
      self._ValidateType(path_info, rdf_objects.PathInfo)
      self._ValidateType(stat_entry, rdf_client.StatEntry)

    for path_info, hash_entry in iteritems(hash_entries):
      self._ValidateType(path_info, rdf_objects.PathInfo)
      self._ValidateType(hash_entry, rdf_crypto.Hash)

    self.delegate.MultiWritePathHistory(client_id, stat_entries, hash_entries)

  def FindDescendentPathIDs(self, client_id, path_type, path_id,
                            max_depth=None):
    self._ValidateClientId(client_id)

    return self.delegate.FindDescendentPathIDs(
        client_id, path_type, path_id, max_depth=max_depth)

  def WriteUserNotification(self, notification):
    self._ValidateType(notification, rdf_objects.UserNotification)
    self._ValidateUsername(notification.username)
    self._ValidateNotificationType(notification.notification_type)
    self._ValidateNotificationState(notification.state)

    return self.delegate.WriteUserNotification(notification)

  def ReadUserNotifications(self, username, state=None, timerange=None):
    self._ValidateUsername(username)
    self._ValidateTimeRange(timerange)
    if state is not None:
      self._ValidateNotificationState(state)

    return self.delegate.ReadUserNotifications(
        username, state=state, timerange=timerange)

  def ReadPathInfosHistories(self, client_id, path_type, components_list):
    self._ValidateClientId(client_id)
    self._ValidateEnumType(path_type, rdf_objects.PathInfo.PathType)
    self._ValidateType(components_list, list)
    for components in components_list:
      self._ValidatePathComponents(components)

    return self.delegate.ReadPathInfosHistories(client_id, path_type,
                                                components_list)

  def UpdateUserNotifications(self, username, timestamps, state=None):
    self._ValidateNotificationState(state)

    return self.delegate.UpdateUserNotifications(
        username, timestamps, state=state)

  def ReadAllAuditEvents(self):
    return self.delegate.ReadAllAuditEvents()

  def WriteAuditEvent(self, event):
    self._ValidateType(event, rdf_events.AuditEvent)
    return self.delegate.WriteAuditEvent(event)

  def WriteMessageHandlerRequests(self, requests):
    return self.delegate.WriteMessageHandlerRequests(requests)

  def DeleteMessageHandlerRequests(self, requests):
    return self.delegate.DeleteMessageHandlerRequests(requests)

  def ReadMessageHandlerRequests(self):
    return self.delegate.ReadMessageHandlerRequests()

  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    if handler is None:
      raise ValueError("handler must be provided")

    self._ValidateDuration(lease_time)
    return self.delegate.RegisterMessageHandler(
        handler, lease_time, limit=limit)

  def UnregisterMessageHandler(self):
    return self.delegate.UnregisterMessageHandler()

  def WriteCronJob(self, cronjob):
    self._ValidateType(cronjob, rdf_cronjobs.CronJob)
    return self.delegate.WriteCronJob(cronjob)

  def ReadCronJob(self, cronjob_id):
    self._ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJob(cronjob_id)

  def ReadCronJobs(self, cronjob_ids=None):
    if cronjob_ids:
      for cronjob_id in cronjob_ids:
        self._ValidateCronJobId(cronjob_id)
    return self.delegate.ReadCronJobs(cronjob_ids=cronjob_ids)

  def EnableCronJob(self, cronjob_id):
    self._ValidateCronJobId(cronjob_id)
    return self.delegate.EnableCronJob(cronjob_id)

  def DisableCronJob(self, cronjob_id):
    self._ValidateCronJobId(cronjob_id)
    return self.delegate.DisableCronJob(cronjob_id)

  def DeleteCronJob(self, cronjob_id):
    self._ValidateCronJobId(cronjob_id)
    return self.delegate.DeleteCronJob(cronjob_id)

  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=Database.unchanged,
                    last_run_time=Database.unchanged,
                    current_run_id=Database.unchanged,
                    state=Database.unchanged,
                    forced_run_requested=Database.unchanged):
    self._ValidateCronJobId(cronjob_id)
    if current_run_id != Database.unchanged:
      self._ValidateCronJobRunId(current_run_id)
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
        self._ValidateCronJobId(cronjob_id)
    self._ValidateDuration(lease_time)
    return self.delegate.LeaseCronJobs(
        cronjob_ids=cronjob_ids, lease_time=lease_time)

  def ReturnLeasedCronJobs(self, jobs):
    for job in jobs:
      self._ValidateType(job, rdf_cronjobs.CronJob)
    return self.delegate.ReturnLeasedCronJobs(jobs)

  def WriteCronJobRun(self, run_object):
    self._ValidateType(run_object, rdf_cronjobs.CronJobRun)
    return self.delegate.WriteCronJobRun(run_object)

  def ReadCronJobRun(self, job_id, run_id):
    self._ValidateCronJobId(job_id)
    self._ValidateCronJobRunId(run_id)
    return self.delegate.ReadCronJobRun(job_id, run_id)

  def ReadCronJobRuns(self, job_id):
    self._ValidateCronJobId(job_id)
    return self.delegate.ReadCronJobRuns(job_id)

  def DeleteOldCronJobRuns(self, cutoff_timestamp):
    self._ValidateTimestamp(cutoff_timestamp)
    return self.delegate.DeleteOldCronJobRuns(cutoff_timestamp)

  def WriteClientPathBlobReferences(self, references_by_client_path_id):
    for client_path_id, refs in iteritems(references_by_client_path_id):
      self._ValidateClientPathID(client_path_id)
      for ref in refs:
        self._ValidateBlobReference(ref)

    self.delegate.WriteClientPathBlobReferences(references_by_client_path_id)

  def ReadClientPathBlobReferences(self, client_path_ids):
    for p in client_path_ids:
      self._ValidateClientPathID(p)

    return self.delegate.ReadClientPathBlobReferences(client_path_ids)

  def WriteBlobs(self, blob_id_data_pairs):
    for bid, data in iteritems(blob_id_data_pairs):
      self._ValidateBlobID(bid)
      self._ValidateBytes(data)

    return self.delegate.WriteBlobs(blob_id_data_pairs)

  def ReadBlobs(self, blob_ids):
    for bid in blob_ids:
      self._ValidateBlobID(bid)

    return self.delegate.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    for bid in blob_ids:
      self._ValidateBlobID(bid)

    return self.delegate.CheckBlobsExist(blob_ids)

  def WriteClientMessages(self, messages):
    for message in messages:
      self._ValidateType(message, rdf_flows.GrrMessage)
    return self.delegate.WriteClientMessages(messages)

  def LeaseClientMessages(self, client_id, lease_time=None, limit=1000000):
    self._ValidateClientId(client_id)
    self._ValidateDuration(lease_time)
    return self.delegate.LeaseClientMessages(
        client_id, lease_time=lease_time, limit=limit)

  def ReadClientMessages(self, client_id):
    self._ValidateClientId(client_id)
    return self.delegate.ReadClientMessages(client_id)

  def DeleteClientMessages(self, messages):
    for message in messages:
      self._ValidateType(message, rdf_flows.GrrMessage)
    return self.delegate.DeleteClientMessages(messages)
