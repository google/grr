#!/usr/bin/env python
"""An in memory database implementation used for testing."""

import os
import sys
import threading

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects
from grr.server.grr_response_server import db


class _PathRecord(object):
  """A class representing all known information about particular path.

  Attributes:
    path_type: A path type of the path that this record corresponds to.
    components: A path components of the path that this record corresponds to.
  """

  def __init__(self, path_type, components):
    self._path_info = objects.PathInfo(
        path_type=path_type, components=components)

    self._stat_entries = []
    self._children = set()

  def AddPathHistory(self, path_info):
    """Extends the path record history and updates existing information."""
    self.AddPathInfo(path_info)
    self._stat_entries.append((rdfvalue.RDFDatetime.Now(),
                               path_info.stat_entry))

  def AddPathInfo(self, path_info):
    """Updates existing path information of the path record."""
    if self._path_info.path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.path_type, path_info.path_type))
    if self._path_info.components != path_info.components:
      message = "Incompatible path components: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.components, path_info.components))

    self._path_info.directory |= path_info.directory

  def AddChild(self, path_info):
    """Makes the path aware of some child."""
    if self._path_info.path_type != path_info.path_type:
      message = "Incompatible path types: `%s` and `%s`"
      raise ValueError(
          message % (self._path_info.path_type, path_info.path_type))
    if self._path_info.components != path_info.components[:-1]:
      message = "Incompatible path components, expected `%s` but got `%s`"
      raise ValueError(
          message % (self._path_info.components, path_info.components[:-1]))

    self._children.add(path_info.GetPathID())

  def GetPathInfo(self, timestamp=None):
    """Generates a summary about the path record.

    Args:
      timestamp: A point in time from which the data should be retrieved.

    Returns:
      A `rdf_objects.PathInfo` instance.
    """
    if timestamp is None:
      timestamp = rdfvalue.RDFDatetime.Now()

    # We want to find last stat entry that has timestamp greater (or equal) to
    # the given one.
    result_stat_entry = None
    for stat_entry_timestamp, stat_entry in self._stat_entries:
      if timestamp < stat_entry_timestamp:
        break

      result_stat_entry = stat_entry

    try:
      last_path_history_timestamp, _ = self._stat_entries[-1]
    except IndexError:
      last_path_history_timestamp = None

    result = self._path_info.Copy()
    result.stat_entry = result_stat_entry
    result.last_path_history_timestamp = last_path_history_timestamp
    return result

  def GetChildren(self):
    return set(self._children)


class InMemoryDB(db.Database):
  """An in memory database implementation used for testing."""

  def __init__(self):
    super(InMemoryDB, self).__init__()
    self._Init()
    self.lock = threading.RLock()

  def _Init(self):
    self.metadatas = {}
    self.clients = {}
    self.keywords = {}
    self.labels = {}
    self.users = {}
    self.startup_history = {}
    self.crash_history = {}
    self.approvals_by_username = {}
    self.notifications_by_username = {}
    # Maps (client_id, path_type, path_id) to a path record.
    self.path_records = {}
    self.message_handler_requests = {}
    self.message_handler_leases = {}
    self.events = []
    self.cronjobs = {}
    self.cronjob_leases = {}
    self.foreman_rules = []

  @utils.Synchronized
  def ClearTestDB(self):
    self._Init()

  def _ParseTimeRange(self, timerange):
    """Parses a timerange argument and always returns non-None timerange."""
    if timerange is None:
      timerange = (None, None)

    from_time, to_time = timerange
    if not from_time:
      from_time = rdfvalue.RDFDatetime().FromSecondsSinceEpoch(0)

    if not to_time:
      to_time = rdfvalue.RDFDatetime().FromSecondsSinceEpoch(sys.maxint)

    return (from_time, to_time)

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
      md = self.metadatas.get(client_id, {})
      res[client_id] = objects.ClientMetadata(
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
      client_obj = objects.ClientSnapshot.FromSerializedString(last_serialized)
      client_obj.timestamp = last_timestamp
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedString(
          self.startup_history[client_id][last_timestamp])
      res[client_id] = client_obj
    return res

  @utils.Synchronized
  def MultiReadClientFullInfo(self, client_ids, min_last_ping=None):
    res = {}
    for client_id in client_ids:
      md = self.ReadClientMetadata(client_id)
      if md and min_last_ping and md.ping < min_last_ping:
        continue
      res[client_id] = objects.ClientFullInfo(
          metadata=md,
          labels=self.ReadClientLabels(client_id),
          last_snapshot=self.ReadClientSnapshot(client_id),
          last_startup_info=self.ReadClientStartupInfo(client_id))
    return res

  @utils.Synchronized
  def ReadAllClientIDs(self):
    return self.metadatas.keys()

  @utils.Synchronized
  def WriteClientSnapshotHistory(self, clients):
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

      client_obj = objects.ClientSnapshot.FromSerializedString(history[ts])
      client_obj.timestamp = ts
      client_obj.startup_info = rdf_client.StartupInfo.FromSerializedString(
          self.startup_history[client_id][ts])
      res.append(client_obj)
    return res

  @utils.Synchronized
  def AddClientKeywords(self, client_id, keywords):
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    keywords = [utils.SmartStr(k) for k in keywords]
    for k in keywords:
      self.keywords.setdefault(k, {})
      self.keywords[k][client_id] = rdfvalue.RDFDatetime.Now()

  @utils.Synchronized
  def ListClientsForKeywords(self, keywords, start_time=None):
    keywords = set(keywords)
    keyword_mapping = {utils.SmartStr(kw): kw for kw in keywords}

    res = {}
    for k in keyword_mapping:
      res.setdefault(keyword_mapping[k], [])
      for client_id, timestamp in self.keywords.get(k, {}).items():
        if start_time is not None:
          rdf_ts = timestamp
          if rdf_ts < start_time:
            continue
        res[keyword_mapping[k]].append(client_id)
    return res

  @utils.Synchronized
  def RemoveClientKeyword(self, client_id, keyword):
    if keyword in self.keywords and client_id in self.keywords[keyword]:
      del self.keywords[keyword][client_id]

  @utils.Synchronized
  def AddClientLabels(self, client_id, owner, labels):
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.add(utils.SmartUnicode(l))

  @utils.Synchronized
  def MultiReadClientLabels(self, client_ids):
    res = {}
    for client_id in client_ids:
      res[client_id] = []
      owner_dict = self.labels.get(client_id, {})
      for owner, labels in owner_dict.items():
        for l in labels:
          res[client_id].append(objects.ClientLabel(owner=owner, name=l))
      res[client_id].sort(key=lambda label: (label.owner, label.name))
    return res

  @utils.Synchronized
  def RemoveClientLabels(self, client_id, owner, labels):
    labelset = self.labels.setdefault(client_id, {}).setdefault(owner, set())
    for l in labels:
      labelset.discard(utils.SmartUnicode(l))

  @utils.Synchronized
  def ReadAllClientLabels(self):
    result = set()
    for labels_dict in self.labels.values():
      for owner, names in labels_dict.items():
        for name in names:
          result.add(objects.ClientLabel(owner=owner, name=name))

    return list(result)

  @utils.Synchronized
  def WriteForemanRule(self, rule):
    self.RemoveForemanRule(rule.hunt_id)
    self.foreman_rules.append(rule)

  @utils.Synchronized
  def RemoveForemanRule(self, hunt_id):
    self.foreman_rules = [r for r in self.foreman_rules if r.hunt_id != hunt_id]

  @utils.Synchronized
  def ReadAllForemanRules(self):
    return self.foreman_rules

  @utils.Synchronized
  def RemoveExpiredForemanRules(self):
    now = rdfvalue.RDFDatetime.Now()
    self.foreman_rules = [
        r for r in self.foreman_rules if r.expiration_time >= now
    ]

  @utils.Synchronized
  def WriteGRRUser(self,
                   username,
                   password=None,
                   ui_mode=None,
                   canary_mode=None,
                   user_type=None):
    u = self.users.setdefault(username, {"username": username})
    if password is not None:
      u["password"] = password
    if ui_mode is not None:
      u["ui_mode"] = ui_mode
    if canary_mode is not None:
      u["canary_mode"] = canary_mode
    if user_type is not None:
      u["user_type"] = user_type

  @utils.Synchronized
  def ReadGRRUser(self, username):
    try:
      u = self.users[username]
      return objects.GRRUser(
          username=u["username"],
          password=u.get("password"),
          ui_mode=u.get("ui_mode"),
          canary_mode=u.get("canary_mode"),
          user_type=u.get("user_type"))
    except KeyError:
      raise db.UnknownGRRUserError("Can't find user with name: %s" % username)

  @utils.Synchronized
  def ReadAllGRRUsers(self):
    for u in self.users.values():
      yield objects.GRRUser(
          username=u["username"],
          password=u.get("password"),
          ui_mode=u.get("ui_mode"),
          canary_mode=u.get("canary_mode"),
          user_type=u.get("user_type"))

  @utils.Synchronized
  def WriteClientStartupInfo(self, client_id, startup_info):
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["startup_info_timestamp"] = ts
    history = self.startup_history.setdefault(client_id, {})
    history[ts] = startup_info.SerializeToString()

  @utils.Synchronized
  def ReadClientStartupInfo(self, client_id):
    history = self.startup_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.StartupInfo.FromSerializedString(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientStartupInfoHistory(self, client_id, timerange=None):
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
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    ts = rdfvalue.RDFDatetime.Now()
    self.metadatas[client_id]["last_crash_timestamp"] = ts
    history = self.crash_history.setdefault(client_id, {})
    history[ts] = crash_info.SerializeToString()

  @utils.Synchronized
  def ReadClientCrashInfo(self, client_id):
    history = self.crash_history.get(client_id, None)
    if not history:
      return None

    ts = max(history)
    res = rdf_client.ClientCrash.FromSerializedString(history[ts])
    res.timestamp = ts
    return res

  @utils.Synchronized
  def ReadClientCrashInfoHistory(self, client_id):
    history = self.crash_history.get(client_id)
    if not history:
      return []
    res = []
    for ts in sorted(history, reverse=True):
      client_data = rdf_client.ClientCrash.FromSerializedString(history[ts])
      client_data.timestamp = ts
      res.append(client_data)
    return res

  @utils.Synchronized
  def WriteApprovalRequest(self, approval_request):
    approvals = self.approvals_by_username.setdefault(
        approval_request.requestor_username, {})

    approval_id = os.urandom(16).encode("hex")
    cloned_request = approval_request.Copy()
    cloned_request.timestamp = rdfvalue.RDFDatetime.Now()
    cloned_request.approval_id = approval_id
    approvals[approval_id] = cloned_request

    return approval_id

  @utils.Synchronized
  def ReadApprovalRequest(self, requestor_username, approval_id):
    try:
      return self.approvals_by_username[requestor_username][approval_id]
    except KeyError:
      raise db.UnknownApprovalRequestError(
          "Can't find approval with id: %s" % approval_id)

  @utils.Synchronized
  def ReadApprovalRequests(self,
                           requestor_username,
                           approval_type,
                           subject_id=None,
                           include_expired=False):
    now = rdfvalue.RDFDatetime.Now()
    for approval in self.approvals_by_username.get(requestor_username,
                                                   {}).values():
      if approval.approval_type != approval_type:
        continue

      if subject_id and approval.subject_id != subject_id:
        continue

      if not include_expired and approval.expiration_time < now:
        continue

      yield approval

  @utils.Synchronized
  def GrantApproval(self, requestor_username, approval_id, grantor_username):
    try:
      approval = self.approvals_by_username[requestor_username][approval_id]
      approval.grants.append(
          objects.ApprovalGrant(
              grantor_username=grantor_username,
              timestamp=rdfvalue.RDFDatetime.Now()))
    except KeyError:
      raise db.UnknownApprovalRequestError(
          "Can't find approval with id: %s" % approval_id)

  @utils.Synchronized
  def FindPathInfoByPathID(self, client_id, path_type, path_id, timestamp=None):
    try:
      path_record = self.path_records[(client_id, path_type, path_id)]
      return path_record.GetPathInfo(timestamp=timestamp)
    except KeyError:
      raise db.UnknownPathError(
          client_id=client_id, path_type=path_type, path_id=path_id)

  @utils.Synchronized
  def FindPathInfosByPathIDs(self, client_id, path_type, path_ids):
    """Returns path info records for a client."""
    ret = {}
    for path_id in path_ids:
      try:
        path_record = self.path_records[(client_id, path_type, path_id)]
        ret[path_id] = path_record.GetPathInfo()
      except KeyError:
        ret[path_id] = None
    return ret

  def _GetPathRecord(self, client_id, path_info):
    path_idx = (client_id, path_info.path_type, path_info.GetPathID())
    return self.path_records.setdefault(
        path_idx,
        _PathRecord(
            path_type=path_info.path_type, components=path_info.components))

  def _WritePathInfo(self, client_id, path_info, ancestor):
    """Writes a single path info record for given client."""
    if client_id not in self.metadatas:
      raise db.UnknownClientError(client_id)

    path_record = self._GetPathRecord(client_id, path_info)
    if not ancestor:
      path_record.AddPathHistory(path_info)
    else:
      path_record.AddPathInfo(path_info)

    parent_path_info = path_info.GetParent()
    if parent_path_info is not None:
      parent_path_record = self._GetPathRecord(client_id, parent_path_info)
      parent_path_record.AddChild(path_info)

  @utils.Synchronized
  def WritePathInfos(self, client_id, path_infos):
    for path_info in path_infos:
      self._WritePathInfo(client_id, path_info, ancestor=False)
      for ancestor_path_info in path_info.GetAncestors():
        self._WritePathInfo(client_id, ancestor_path_info, ancestor=True)

  @utils.Synchronized
  def FindDescendentPathIDs(self, client_id, path_type, path_id,
                            max_depth=None):
    """Finds all path_ids seen on a client descent from path_id."""
    descendents = set()
    if max_depth == 0:
      return descendents

    next_depth = None
    if max_depth is not None:
      next_depth = max_depth - 1

    path_record = self.path_records[(client_id, path_type, path_id)]
    for child_path_id in path_record.GetChildren():
      descendents.add(child_path_id)
      descendents.update(
          self.FindDescendentPathIDs(
              client_id, path_type, child_path_id, max_depth=next_depth))

    return descendents

  @utils.Synchronized
  def WriteUserNotification(self, notification):
    """Writes a notification for a given user."""
    cloned_notification = notification.Copy()
    if not cloned_notification.timestamp:
      cloned_notification.timestamp = rdfvalue.RDFDatetime.Now()

    self.notifications_by_username.setdefault(cloned_notification.username,
                                              []).append(cloned_notification)

  @utils.Synchronized
  def ReadUserNotifications(self, username, state=None, timerange=None):
    """Reads notifications scheduled for a user within a given timerange."""
    from_time, to_time = self._ParseTimeRange(timerange)

    result = []
    for n in self.notifications_by_username.get(username, []):
      if from_time <= n.timestamp <= to_time and (state is None or
                                                  n.state == state):
        result.append(n.Copy())

    return sorted(result, key=lambda r: r.timestamp, reverse=True)

  @utils.Synchronized
  def UpdateUserNotifications(self, username, timestamps, state=None):
    """Updates existing user notification objects."""
    if not timestamps:
      return

    for n in self.notifications_by_username.get(username, []):
      if n.timestamp in timestamps:
        n.state = state

  @utils.Synchronized
  def ReadAllAuditEvents(self):
    return sorted(self.events, key=lambda event: event.timestamp)

  @utils.Synchronized
  def WriteAuditEvent(self, event):
    event = event.Copy()
    event.timestamp = rdfvalue.RDFDatetime.Now()
    self.events.append(event)

  @utils.Synchronized
  def WriteMessageHandlerRequests(self, requests):
    """Writes a list of message handler requests to the database."""
    now = rdfvalue.RDFDatetime.Now()
    for r in requests:
      flow_dict = self.message_handler_requests.setdefault(r.handler_name, {})
      cloned_request = r.Copy()
      cloned_request.timestamp = now
      flow_dict[cloned_request.request_id] = cloned_request

  @utils.Synchronized
  def ReadMessageHandlerRequests(self):
    """Reads all message handler requests from the database."""
    res = []
    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        res.append(r.Copy())
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, None)
        res[-1].leased_until = existing_lease

    return sorted(res, key=lambda r: -1 * r.timestamp)

  @utils.Synchronized
  def DeleteMessageHandlerRequests(self, requests):
    """Deletes a list of message handler requests from the database."""

    for r in requests:
      flow_dict = self.message_handler_requests.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]
      flow_dict = self.message_handler_leases.get(r.handler_name, {})
      if r.request_id in flow_dict:
        del flow_dict[r.request_id]

  @utils.Synchronized
  def LeaseMessageHandlerRequests(self, lease_time=None, limit=1000):
    """Leases a number of message handler requests up to the indicated limit."""

    leased_requests = []

    now = rdfvalue.RDFDatetime.Now()
    zero = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)
    expiration_time = now + lease_time

    leases = self.message_handler_leases
    for requests in self.message_handler_requests.values():
      for r in requests.values():
        existing_lease = leases.get(r.handler_name, {}).get(r.request_id, zero)
        if existing_lease < now:
          leases.setdefault(r.handler_name, {})[r.request_id] = expiration_time
          r.leased_until = expiration_time
          r.leased_by = utils.ProcessIdString()
          leased_requests.append(r)
          if len(leased_requests) >= limit:
            break

    return leased_requests

  @utils.Synchronized
  def WriteCronJob(self, cronjob):
    self.cronjobs[cronjob.job_id] = cronjob.Copy()

  @utils.Synchronized
  def ReadCronJobs(self, cronjob_ids=None):
    if cronjob_ids is None:
      res = [job.Copy() for job in self.cronjobs.values()]

    else:
      res = []
      for job_id in cronjob_ids:
        try:
          res.append(self.cronjobs[job_id].Copy())
        except KeyError:
          raise db.UnknownCronjobError(
              "Cron job with id %s not found." % job_id)

    for job in res:
      lease = self.cronjob_leases.get(job.job_id)
      if lease:
        job.leased_until, job.leased_by = lease
    return res

  @utils.Synchronized
  def UpdateCronJob(self,
                    cronjob_id,
                    last_run_status=db.Database.unchanged,
                    last_run_time=db.Database.unchanged,
                    current_run_id=db.Database.unchanged,
                    state=db.Database.unchanged):
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)

    if last_run_status != db.Database.unchanged:
      job.last_run_status = last_run_status
    if last_run_time != db.Database.unchanged:
      job.last_run_time = last_run_time
    if current_run_id != db.Database.unchanged:
      job.current_run_id = current_run_id
    if state != db.Database.unchanged:
      job.state = state

  @utils.Synchronized
  def EnableCronJob(self, cronjob_id):
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    job.disabled = False

  @utils.Synchronized
  def DisableCronJob(self, cronjob_id):
    job = self.cronjobs.get(cronjob_id)
    if job is None:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    job.disabled = True

  @utils.Synchronized
  def DeleteCronJob(self, cronjob_id):
    if cronjob_id not in self.cronjobs:
      raise db.UnknownCronjobError("Cron job %s not known." % cronjob_id)
    del self.cronjobs[cronjob_id]
    try:
      del self.cronjob_leases[cronjob_id]
    except KeyError:
      pass

  @utils.Synchronized
  def LeaseCronJobs(self, cronjob_ids=None, lease_time=None):
    leased_jobs = []

    now = rdfvalue.RDFDatetime.Now()
    expiration_time = now + lease_time

    for job in self.cronjobs.values():
      if cronjob_ids and job.job_id not in cronjob_ids:
        continue
      existing_lease = self.cronjob_leases.get(job.job_id)
      if existing_lease is None or existing_lease[0] < now:
        self.cronjob_leases[job.job_id] = (expiration_time,
                                           utils.ProcessIdString())
        job = job.Copy()
        job.leased_until, job.leased_by = self.cronjob_leases[job.job_id]
        leased_jobs.append(job)

    return leased_jobs

  @utils.Synchronized
  def ReturnLeasedCronJobs(self, jobs):
    errored_jobs = []

    for returned_job in jobs:
      existing_lease = self.cronjob_leases.get(returned_job.job_id)
      if existing_lease is None:
        errored_jobs.append(returned_job)
        continue

      if (returned_job.leased_until != existing_lease[0] or
          returned_job.leased_by != existing_lease[1]):
        errored_jobs.append(returned_job)
        continue

      del self.cronjob_leases[returned_job.job_id]

    if errored_jobs:
      raise ValueError("Some jobs could not be returned: %s" % ",".join(
          job.job_id for job in errored_jobs))
