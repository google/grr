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

  def WriteClientMetadata(self,
                          client_id,
                          certificate=None,
                          fleetspeak_enabled=None,
                          last_ping=None,
                          last_clock=None,
                          last_ip=None,
                          last_foreman=None,
                          last_crash=None):
    md = {}
    if certificate is not None:
      md["certificate"] = certificate

    if fleetspeak_enabled is not None:
      md["fleetspeak_enabled"] = fleetspeak_enabled

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
      md = self.metadatas.get(client_id, {})
      res[client_id] = objects.ClientMetadata(
          certificate=md.get("certificate"),
          fleetspeak_enabled=md.get("fleetspeak_enabled"),
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

    history = self.clients.setdefault(client_id, {})
    history[time.time()] = client

  def ReadClients(self, client_ids):
    """Reads the latest client snapshots for a list of clients."""
    res = {}
    for client_id in client_ids:
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
    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  def AddClientLabels(self, client_id, owner, labels):
    if isinstance(labels, basestring):
      raise ValueError("Expected iterable, got string.")

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.add(utils.SmartUnicode(l))

  def GetClientLabels(self, client_id):
    res = []
    owner_dict = self.labels.get(client_id, {})
    for owner, labels in owner_dict.items():
      for l in labels:
        res.append(objects.ClientLabel(owner=owner, name=l))
    return sorted(res, key=lambda label: (label.owner, label.name))

  def RemoveClientLabels(self, client_id, owner, labels):
    if isinstance(labels, basestring):
      raise ValueError("Expected iterable, got string.")

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))
