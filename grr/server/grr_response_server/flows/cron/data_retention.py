#!/usr/bin/env python
"""These cron flows do the datastore cleanup."""

from grr import config
from grr.lib import rdfvalue
from grr.lib import utils
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import client_index
from grr.server.grr_response_server import flow

from grr.server.grr_response_server.aff4_objects import aff4_grr
from grr.server.grr_response_server.aff4_objects import cronjobs

from grr.server.grr_response_server.hunts import implementation


class CleanHunts(cronjobs.SystemCronFlow):
  """Cleaner that deletes old hunts."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    hunts_ttl = config.CONFIG["DataRetention.hunts_ttl"]
    if not hunts_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config.CONFIG["DataRetention.hunts_ttl_exception_label"]

    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_urns = list(hunts_root.ListChildren())

    deadline = rdfvalue.RDFDatetime.Now() - hunts_ttl

    hunts = aff4.FACTORY.MultiOpen(
        hunts_urns, aff4_type=implementation.GRRHunt, token=self.token)
    for hunt in hunts:
      if exception_label in hunt.GetLabelsNames():
        continue

      runner = hunt.GetRunner()
      if runner.context.expires < deadline:
        aff4.FACTORY.Delete(hunt.urn, token=self.token)
        self.HeartBeat()


class CleanCronJobs(cronjobs.SystemCronFlow):
  """Cleaner that deletes old finished cron flows."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    cron_jobs_ttl = config.CONFIG["DataRetention.cron_jobs_flows_ttl"]
    if not cron_jobs_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    manager = cronjobs.GetCronManager()
    for job in manager.ReadJobs(token=self.token):
      age = rdfvalue.RDFDatetime.Now() - cron_jobs_ttl
      manager.DeleteRuns(job, age=age, token=self.token)
      self.HeartBeat()


class CleanTemp(cronjobs.SystemCronFlow):
  """Cleaner that deletes temp objects."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    tmp_ttl = config.CONFIG["DataRetention.tmp_ttl"]
    if not tmp_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config.CONFIG["DataRetention.tmp_ttl_exception_label"]

    tmp_root = aff4.FACTORY.Open("aff4:/tmp", mode="r", token=self.token)
    tmp_urns = list(tmp_root.ListChildren())

    deadline = rdfvalue.RDFDatetime.Now() - tmp_ttl

    for tmp_group in utils.Grouper(tmp_urns, 10000):
      expired_tmp_urns = []
      for tmp_obj in aff4.FACTORY.MultiOpen(
          tmp_group, mode="r", token=self.token):
        if exception_label in tmp_obj.GetLabelsNames():
          continue

        if tmp_obj.Get(tmp_obj.Schema.LAST) < deadline:
          expired_tmp_urns.append(tmp_obj.urn)

      aff4.FACTORY.MultiDelete(expired_tmp_urns, token=self.token)
      self.HeartBeat()


class CleanInactiveClients(cronjobs.SystemCronFlow):
  """Cleaner that deletes inactive clients."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    inactive_client_ttl = config.CONFIG["DataRetention.inactive_client_ttl"]
    if not inactive_client_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config.CONFIG[
        "DataRetention.inactive_client_ttl_exception_label"]

    index = client_index.CreateClientIndex(token=self.token)

    client_urns = index.LookupClients(["."])

    deadline = rdfvalue.RDFDatetime.Now() - inactive_client_ttl

    for client_group in utils.Grouper(client_urns, 1000):
      inactive_client_urns = []
      for client in aff4.FACTORY.MultiOpen(
          client_group,
          mode="r",
          aff4_type=aff4_grr.VFSGRRClient,
          token=self.token):
        if exception_label in client.GetLabelsNames():
          continue

        if client.Get(client.Schema.LAST) < deadline:
          inactive_client_urns.append(client.urn)

      aff4.FACTORY.MultiDelete(inactive_client_urns, token=self.token)
      self.HeartBeat()
