#!/usr/bin/env python
"""These cron flows do the datastore cleanup."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import collection
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.hunts import implementation


class CleanHuntsMixin(object):
  """Logic for the cron jobs that clean up old hunt data."""

  def CleanAff4Hunts(self):
    """Cleans up old hunt data from aff4."""

    hunts_ttl = config.CONFIG["DataRetention.hunts_ttl"]
    if not hunts_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config.CONFIG["DataRetention.hunts_ttl_exception_label"]

    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_urns = list(hunts_root.ListChildren())

    deadline = rdfvalue.RDFDatetime.Now() - hunts_ttl

    hunts_deleted = 0

    hunts = aff4.FACTORY.MultiOpen(
        hunts_urns, aff4_type=implementation.GRRHunt, token=self.token)
    for hunt in hunts:
      if exception_label in hunt.GetLabelsNames():
        continue

      runner = hunt.GetRunner()
      if runner.context.expires < deadline:
        aff4.FACTORY.Delete(hunt.urn, token=self.token)
        hunts_deleted += 1
        self.HeartBeat()
    self.Log("Deleted %d hunts." % hunts_deleted)


class CleanHunts(aff4_cronjobs.SystemCronFlow, CleanHuntsMixin):
  """Cleaner that deletes old hunts."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  def Start(self):
    self.CleanAff4Hunts()


class CleanHuntsCronJob(cronjobs.SystemCronJobBase, CleanHuntsMixin):

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  def Run(self):
    self.CleanAff4Hunts()


class CleanCronJobs(aff4_cronjobs.SystemCronFlow):
  """Cleaner that deletes old finished cron flows."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  def Start(self):
    """Cleans up old cron job data."""
    cron_jobs_ttl = config.CONFIG["DataRetention.cron_jobs_flows_ttl"]
    if not cron_jobs_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    manager = aff4_cronjobs.GetCronManager()
    cutoff_timestamp = rdfvalue.RDFDatetime.Now() - cron_jobs_ttl
    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      deletion_count = manager.DeleteOldRuns(cutoff_timestamp=cutoff_timestamp)

    else:
      deletion_count = 0
      for job in manager.ReadJobs(token=self.token):
        deletion_count += manager.DeleteOldRuns(
            job, cutoff_timestamp=cutoff_timestamp, token=self.token)
        self.HeartBeat()

    self.Log("Deleted %d cron job runs." % deletion_count)


class CleanCronJobsCronJob(cronjobs.SystemCronJobBase):
  """Cron job that deletes old cron job data."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("20h")

  def Run(self):
    cron_jobs_ttl = config.CONFIG["DataRetention.cron_jobs_flows_ttl"]
    if not cron_jobs_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    manager = aff4_cronjobs.GetCronManager()
    cutoff_timestamp = rdfvalue.RDFDatetime.Now() - cron_jobs_ttl
    deletion_count = manager.DeleteOldRuns(cutoff_timestamp=cutoff_timestamp)
    self.Log("Deleted %d cron job runs." % deletion_count)


class CleanInactiveClientsMixin(object):
  """Logic for the cron jobs that clean up old client data."""

  def CleanClients(self):
    # TODO(amoser): Support relational db here.
    self.CleanAff4Clients()

  def CleanAff4Clients(self):
    """Cleans up old client data from aff4."""

    inactive_client_ttl = config.CONFIG["DataRetention.inactive_client_ttl"]
    if not inactive_client_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config.CONFIG[
        "DataRetention.inactive_client_ttl_exception_label"]

    index = client_index.CreateClientIndex(token=self.token)

    client_urns = index.LookupClients(["."])

    deadline = rdfvalue.RDFDatetime.Now() - inactive_client_ttl
    deletion_count = 0

    for client_group in collection.Batch(client_urns, 1000):
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
      deletion_count += len(inactive_client_urns)
      self.HeartBeat()

    self.Log("Deleted %d inactive clients." % deletion_count)


class CleanInactiveClients(aff4_cronjobs.SystemCronFlow,
                           CleanInactiveClientsMixin):
  """Cleaner that deletes inactive clients."""

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("1d")

  def Start(self):
    self.CleanClients()


class CleanInactiveClientsCronJob(cronjobs.SystemCronJobBase,
                                  CleanInactiveClientsMixin):

  frequency = rdfvalue.Duration("1d")
  lifetime = rdfvalue.Duration("20h")

  def Run(self):
    self.CleanClients()
