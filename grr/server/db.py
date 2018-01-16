#!/usr/bin/env python
"""The GRR relational database abstraction.

This defines the Database abstraction, which defines the methods used by GRR on
a logical relational database model.

WIP, will eventually replace datastore.py.

"""
import abc


class UnknownClientError(Exception):
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
                          last_foreman=None,
                          last_crash=None):
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
      last_crash: An rdfvalues.client.ClientCrash, documenting the last recorded
        client crash event.

    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ReadClientMetadatas(self, client_ids):
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
    return self.ReadClientMetadatas([client_id]).get(client_id)

  @abc.abstractmethod
  def WriteClient(self, client_id, client):
    """Write new client snapshot.

    Writes a new snapshot of the client to the client history, typically saving
    the results of an interrogate flow.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      client: An rdfvalues.client.Client. Will be saved at the "current"
        timestamp.
    Raises:
      UnknownClientError: The client_id is not known yet.
    """

  @abc.abstractmethod
  def ReadClients(self, client_ids):
    """Reads the latest client snapshots for a list of clients.

    Args:
      client_ids: a collection of GRR client ids, e.g. ["C.ea3b2b71840d6fa7",
        "C.ea3b2b71840d6fa8"]

    Returns:
      A map from client_id to rdfvalues.client.Client.
    """

  def ReadClient(self, client_id):
    """Reads the latest client snapshots for a single client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      An rdfvalues.client.Client object.
    """
    return self.ReadClients([client_id])[client_id]

  @abc.abstractmethod
  def ReadClientHistory(self, client_id):
    """Reads the full history for a particular client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A list of rdfvalues.client.Client, newest snapshot first.
    """

  @abc.abstractmethod
  def WriteClientKeywords(self, client_id, keywords):
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
  def DeleteClientKeyword(self, client_id, keyword):
    """Deletes the association of a particular client to a keyword.

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
  def GetClientLabels(self, client_id):
    """Reads the user labels for a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".

    Returns:
      A set of labels for the given client.
    """

  @abc.abstractmethod
  def RemoveClientLabels(self, client_id, owner, labels):
    """Removes a user label from a given client.

    Args:
      client_id: A GRR client id string, e.g. "C.ea3b2b71840d6fa7".
      owner: Username string that owns the labels that should be removed.
      labels: The labels to remove as a list of strings.
    """
