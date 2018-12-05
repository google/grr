#!/usr/bin/env python
"""The in memory database methods for client handling."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems
from future.utils import iterkeys
from future.utils import itervalues

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import db
from grr_response_server.rdfvalues import objects as rdf_objects


class InMemoryDBClientMixin(object):
  """InMemoryDB mixin for client related functions."""

  @utils.Synchronized
  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          first_seen=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None):
    """Write metadata about the client."""
    md = {}
    if certificate is not None:
      md["certificate"] = certificate

    if fleetspeak_enabled is not None:
      md["fleetspeak_enabled"] = fleetspeak_enabled

    if first_seen is not None:
      md["first_seen"] = first_seen

    if last_ping is not None:
      md["ping"] = last_ping

    if last_clock is not None:
      md["clock"] = last_clock

    if last_ip is not None:
      md["ip"] = last_ip

    if last_foreman is not None:
      md["last_foreman_time"] = last_foreman

    if not md:
      raise ValueError("NOOP write.")

    self.metadatas.setdefault(client_id, {}).update(md)

  @utils.Synchronized
  def MultiReadClientMetadata(self, client_ids):
    """Reads ClientMetadata records for a list of clients."""
    res = {}
    for client_id in client_ids:
      md = self.metadatas.get(client_id, None)
      if md is None:
        continue

      res[client_id] = rdf_objects.ClientMetadata(
          certificate=md.get("certificate"),
          fleetspeak_enabled=md.get("fleetspeak_enabled"),
          first_seen=md.get("first_seen"),
          ping=md.get("ping"),
          clock=md.get("clock"),
          ip=md.get("ip"),
          last_foreman_time=md.get("last_foreman_time"),
          last_crash_timestamp=md.get("last_crash_timestamp"),
          startup_info_timestamp=md.get("startup_info_timestamp"))

    return res

  @utils.Synchronized
  def WriteClientSnapshot(self, client):
    """Writes new client snapshot."""
    client_id = client.client_id

    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    startup_info = client.startup_info
    client.startup_info = None

    ts = rdfvalue.RDFDatetime.Now()
    history = self.clients.setdefault(client_id, {})
    history[ts] = client.SerializeToString()

    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToString()

    client.startup_info = startup_info

  @utils.Synchronized
  def MultiReadClientSnapshot(self, client_ids):
    """Reads the latest client snapshots for a list of clients."""
    res = {}
    for client_id in client_ids:
      history = self.clients.get(client_id, None)
      if not history:
        res[client_id] = None
        continue
      last_timestamp = max(history)
      last_serialized = history[last_timestamp]
      client_obj = rdf_objects.ClientSnapshot.FromSerializedString(
          last_serialized)
      client_obj.timestamp = last_timestamp
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedString(
          self.startup_history[client_id][last_timestamp])
      res[client_id] = client_obj
    return res

  @utils.Synchronized
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    """Reads full client information for a list of clients."""
    res = {}
    for client_id in client_ids:
      try:
        md = self.ReadClientMetadata(client_id)
      except db.UnknownClientError:
        continue

      if md and min_last_ping and md.ping < min_last_ping:
        continue
      res[client_id] = rdf_objects.ClientFullInfo(
          metadata=md,
          labels=self.ReadClientLabels(client_id),
          last_snapshot=self.ReadClientSnapshot(client_id),
          last_startup_info=self.ReadClientStartupInfo(client_id))
    return res

  @utils.Synchronized
  def ReadAllClientIDs(self):
    return list(iterkeys(self.metadatas))

  @utils.Synchronized
  def WriteClientSnapshotHistory(self, clients):
    """Writes the full history for a particular client."""
    if clients[0].client_id not in self.metadatas:
      raise db.UnknownClientError(clients[0].client_id)

    for client in clients:
      startup_info = client.startup_info
      client.startup_info = None

      snapshots = self.clients.setdefault(client.client_id, {})
      snapshots[client.timestamp] = client.SerializeToString()

      startup_infos = self.startup_history.setdefault(client.client_id, {})
      startup_infos[client.timestamp] = startup_info.SerializeToString()

      client.startup_info = startup_info

  @utils.Synchronized
  def ReadClientSnapshotHistory(self, client_id, timerange=None):
    """Reads the full history for a particular client."""
    from_time, to_time = self._ParseTimeRange(timerange)

    history = self.clients.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      client_obj = rdf_objects.ClientSnapshot.FromSerializedString(history[ts])
      client_obj.timestamp = ts
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedString(
          self.startup_history[client_id][ts])
      res.append(client_obj)
    return res

  @utils.Synchronized
  def AddClientKeywords(self, client_id, keywords):
    """Associates the provided keywords with the client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    keywords = [utils.SmartStr(k) for k in keywords]
    for k in keywords:
      self.keywords.setdefault(k, {})
      self.keywords[k][client_id] = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def ListClientsForKeywords(self, keywords, start_time=None):
    """Lists the clients associated with keywords."""
    keywords = set(keywords)
    keyword_mapping = {utils.SmartStr(kw): kw for kw in keywords}

    res = {}
    for k in keyword_mapping:
      res.setdefault(keyword_mapping[k], [])
      for client_id, timestamp in iteritems(self.keywords.get(k, {})):
        if start_time is not None:
          rdf_ts = timestamp
          if rdf_ts < start_time:
            continue
        res[keyword_mapping[k]].append(client_id)
    return res

  @utils.Synchronized
  def RemoveClientKeyword(self, client_id, keyword):
    """Removes the association of a particular client to a keyword."""
    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  @utils.Synchronized
  def AddClientLabels(self, client_id, owner, labels):
    """Attaches a user label to a client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.add(utils.SmartUnicode(l))

  @utils.Synchronized
  def MultiReadClientLabels(self, client_ids):
    """Reads the user labels for a list of clients."""
    res = {}
    for client_id in client_ids:
      res[client_id] = []
      owner_dict = self.labels.get(client_id, {})
      for owner, labels in iteritems(owner_dict):
        for l in labels:
          res[client_id].append(rdf_objects.ClientLabel(owner=owner, name=l))
      res[client_id].sort(key=lambda label: (label.owner, label.name))
    return res

  @utils.Synchronized
  def RemoveClientLabels(self, client_id, owner, labels):
    """Removes a list of user labels from a given client."""
    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))

  @utils.Synchronized
  def ReadAllClientLabels(self):
    """Lists all client labels known to the system."""
    result = set()
    for labels_dict in itervalues(self.labels):
      for owner, names in iteritems(labels_dict):
        for name in names:
          result.add(rdf_objects.ClientLabel(owner=owner, name=name))

    return list(result)

  @utils.Synchronized
  def WriteClientStartupInfo(self, client_id, startup_info):
    """Writes a new client startup record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["startup_info_timestamp"] = ts
    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToString()

  @utils.Synchronized
  def ReadClientStartupInfo(self, client_id):
    """Reads the latest client startup record for a single client."""
    history = self.startup_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.StartupInfo.FromSerializedString(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
    """Reads the full startup history for a particular client."""
    from_time, to_time = self._ParseTimeRange(timerange)

    history = self.startup_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      if ts < from_time or ts > to_time:
        continue

      client_data = rdf_client.StartupInfo.FromSerializedString(history[ts])
      client_data.timestamp = ts
      res.append(client_data)
    return res

  @utils.Synchronized
  def WriteClientCrashInfo(self, client_id, crash_info):
    """Writes a new client crash record."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["last_crash_timestamp"] = ts
    history = self.crash_history.setdefault(client_id, {})
    history[ts] = crash_info.SerializeToString()

  @utils.Synchronized
  def ReadClientCrashInfo(self, client_id):
    """Reads the latest client crash record for a single client."""
    history = self.crash_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.ClientCrash.FromSerializedString(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientCrashInfoHistory(self, client_id):
    """Reads the full crash history for a particular client."""
    history = self.crash_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      client_data = rdf_client.ClientCrash.FromSerializedString(history[ts])
      client_data.timestamp = ts
      res.append(client_data)
    return res
