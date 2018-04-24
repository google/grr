#!/usr/bin/env python
"""The GRR relational database abstraction.

This defines the Database abstraction, which defines the methods used by GRR on
a logical relational database model.

WIP, will eventually replace datastore.py.

"""
import abc

from grr.lib import utils
from grr.lib.rdfvalues import objects


class Error(Exception):
  pass


class NotFoundError(Error):
  pass


class UnknownClientError(NotFoundError):
  pass


class UnknownGRRUserError(NotFoundError):
  pass


class UnknownApprovalRequestError(NotFoundError):
  pass


class Database(object):
  """The GRR relational database abstraction."""
  __metaclass__ = abc.ABCMeta

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

  # TODO(hanuszczak): Should abstract methods perform input validation?
  #
  # On one hand all database implementations should have uniform API and accept
  # same arguments. Therefore validation code should be the same in every
  # concrete implementation.
  #
  # On the other hand, abstract means abstract...
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
    if not clients:
      raise ValueError("Clients are empty")

    client_id = None
    for client in clients:
      if not isinstance(client, objects.ClientSnapshot):
        message = "Unexpected '%s' instead of client instance"
        raise TypeError(message % client.__class__)

      if client.timestamp is None:
        raise AttributeError("Client without a `timestamp` attribute")

      client_id = client_id or client.client_id
      if client.client_id != client_id:
        message = "Unexpected client id '%s' instead of '%s'"
        raise ValueError(message % (client.client_id, client_id))

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
      for full_info in res.values():
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
      for snapshot in res.values():
        if snapshot:
          yield snapshot

  @abc.abstractmethod
  def FindPathInfosByPathIDs(self, client_id, path_ids):
    """Returns path info records for a client.

    Args:
      client_id: The client of interest.

      path_ids: A list of path_ids of interest. A path_id can be computed by
        db_path_utils.MakePathID.

    Returns: a map from path_id to rdfvalues.objects.PathInfo records, set only
      for paths which have been observed on the client.
    """

  @abc.abstractmethod
  def WritePathInfosRaw(self, client_id, path_infos):
    """Writes a collection of path_info records for a client.

    Note that this method should only be used when all ancestors of path_infos
    are already present in the database (or part of path_infos). In most cases,
    users of a Database implementation will WritePathInfos, defined below, while
    this is the method that Database implementations will need to provide.

    If any records are already present in the database, they will be merged -
    see db_path_utils.MergePathInfo.

    Args:
      client_id: The client of interest.
      path_infos: A list of rdfvalue.objects.PathInfo records.
    """

  @abc.abstractmethod
  def FindDescendentPathIDs(self, client_id, path_id, max_depth=None):
    """Finds all path_ids seen on a client descendent from path_id.

    Args:
      client_id: The client of interest.
      path_id: The path_id to find descendents of.
      max_depth: If set, the maximum number of generations to descend, otherwise
        unlimited.

    Returns: A list of path_id.
    """

  def WritePathInfos(self, client_id, path_infos):
    """Writes a collection of path_info records for a client.

    If any records are already present in the database, they will be merged -
    see db_path_utils.MergePathInfo.

    Args:
      client_id: The client of interest.
      path_infos: A list of rdfvalue.objects.PathInfo records.
    """
    infos_by_id = {info.path_id: info for info in path_infos}
    for info in path_infos:
      for path_id, components in objects.PathInfo.MakeAncestorPathIDs(
          info.components):
        if path_id not in infos_by_id:
          infos_by_id[path_id] = objects.PathInfo(
              components=components, directory=True)
    self.WritePathInfosRaw(client_id, infos_by_id.values())
