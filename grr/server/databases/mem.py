#!/usr/bin/env python
"""An in memory database implementation used for testing."""

import time

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects
from grr.server import db


class InMemoryDB(db.Database):
  """An in memory database implementation used for testing."""

  def __init__(self):
    super(InMemoryDB, self).__init__()
    self._Init()

  def _Init(self):
    self.metadatas = {}
    self.clients = {}
    self.keywords = {}
    self.labels = {}

  def ClearTestDB(self):
    self._Init()

  def _ValidateClientId(self, client_id):
    if not isinstance(client_id, basestring):
      raise ValueError(
          "Expected client_id as a string, got %s" % type(client_id))

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
    self._ValidateClientId(client_id)

    md = {}
    if certificate is not None:
      md["certificate"] = certificate

    if fleetspeak_enabled is not None:
      md["fleetspeak_enabled"] = fleetspeak_enabled
    else:
      # This is an update to an existing client. Raise if the client
      # is not known.
      if client_id not in self.metadatas:
        raise db.UnknownClientError()

    if first_seen is not None:
      md["first_seen"] = first_seen

    if last_ping is not None:
      md["ping"] = last_ping

    if last_clock is not None:
      md["clock"] = last_clock

    if last_ip is not None:
      if not isinstance(last_ip, rdf_client.NetworkAddress):
        raise ValueError(
            "last_ip must be client.NetworkAddress, got: %s" % type(last_ip))
      md["ip"] = last_ip

    if last_foreman is not None:
      md["last_foreman_time"] = last_foreman

    if last_crash is not None:
      if not isinstance(last_crash, rdf_client.ClientCrash):
        raise ValueError(
            "last_crash must be client.ClientCrash, got: %s" % type(last_crash))

      md["last_crash"] = last_crash

    if not md:
      raise ValueError("NOOP write.")

    self.metadatas.setdefault(client_id, {}).update(md)

  def ReadClientMetadatas(self, client_ids):
    """Reads ClientMetadata records for a list of clients."""
    res = {}
    for client_id in client_ids:
      self._ValidateClientId(client_id)
      md = self.metadatas.get(client_id, {})
      res[client_id] = objects.ClientMetadata(
          certificate=md.get("certificate"),
          fleetspeak_enabled=md.get("fleetspeak_enabled"),
          first_seen=md.get("first_seen"),
          ping=md.get("ping"),
          clock=md.get("clock"),
          ip=md.get("ip"),
          last_foreman_time=md.get("last_foreman_time"),
          last_crash=md.get("last_crash"))
    return res

  def WriteClient(self, client_id, client):
    """Write new client snapshot."""
    if not isinstance(client, objects.Client):
      raise ValueError("WriteClient requires rdfvalues.objects.Client, got: %s"
                       % type(client))

    self._ValidateClientId(client_id)

    if client_id not in self.metadatas:
      raise db.UnknownClientError()

    history = self.clients.setdefault(client_id, {})
    history[time.time()] = client

  def ReadClients(self, client_ids):
    """Reads the latest client snapshots for a list of clients."""
    res = {}
    for client_id in client_ids:
      self._ValidateClientId(client_id)
      history = self.clients.get(client_id, None)
      if not history:
        res[client_id] = None
      else:
        last_timestamp = max(history)
        res[client_id] = history[last_timestamp]
        res[client_id].timestamp = last_timestamp
    return res

  def ReadClientHistory(self, client_id):
    """Reads the full history for a particular client."""
    self._ValidateClientId(client_id)

    history = self.clients.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      client_data = history[ts]
      client_data.timestamp = ts
      res.append(client_data)
    return res

  def WriteClientKeywords(self, client_id, keywords):

    self._ValidateClientId(client_id)

    if client_id not in self.metadatas:
      raise db.UnknownClientError()

    keywords = [utils.SmartStr(k) for k in keywords]
    for k in keywords:
      self.keywords.setdefault(k, {})
      self.keywords[k][client_id] = time.time()

  def ListClientsForKeywords(self, keywords, start_time=None):
    keywords = set(keywords)
    keyword_mapping = {utils.SmartStr(kw): kw for kw in keywords}

    if start_time and not isinstance(start_time, rdfvalue.RDFDatetime):
      raise ValueError(
          "Time value must be rdfvalue.RDFDatetime, got: %s" % type(start_time))

    res = {}
    for k in keyword_mapping:
      res.setdefault(keyword_mapping[k], [])
      for client_id, timestamp in self.keywords.get(k, {}).items():
        if start_time is not None:
          rdf_ts = rdfvalue.RDFDatetime().FromSecondsFromEpoch(timestamp)
          if rdf_ts < start_time:
            continue
        res[keyword_mapping[k]].append(client_id)
    return res

  def DeleteClientKeyword(self, client_id, keyword):
    self._ValidateClientId(client_id)

    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  def AddClientLabels(self, client_id, owner, labels):
    self._ValidateClientId(client_id)

    if isinstance(labels, basestring):
      raise ValueError("Expected iterable, got string.")

    if client_id not in self.metadatas:
      raise db.UnknownClientError()

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.add(utils.SmartUnicode(l))

  def GetClientLabels(self, client_id):
    self._ValidateClientId(client_id)

    res = []
    owner_dict = self.labels.get(client_id, {})
    for owner, labels in owner_dict.items():
      for l in labels:
        res.append(objects.ClientLabel(owner=owner, name=l))
    return sorted(res, key=lambda label: (label.owner, label.name))

  def RemoveClientLabels(self, client_id, owner, labels):
    self._ValidateClientId(client_id)

    if isinstance(labels, basestring):
      raise ValueError("Expected iterable, got string.")

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))
