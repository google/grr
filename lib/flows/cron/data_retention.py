#!/usr/bin/env python
"""These cron flows do the datastore cleanup."""



from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue

from grr.lib.aff4_objects import cronjobs


class CleanHunts(cronjobs.SystemCronFlow):
  """Cleaner that deletes old hunts."""

  frequency = rdfvalue.Duration("7d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    hunts_ttl = config_lib.CONFIG["DataRetention.hunts_ttl"]
    if not hunts_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    exception_label = config_lib.CONFIG[
        "DataRetention.hunts_ttl_exception_label"]

    hunts_root = aff4.FACTORY.Open("aff4:/hunts", token=self.token)
    hunts_urns = list(hunts_root.ListChildren())

    urns_to_delete = []
    deadline = rdfvalue.RDFDatetime().Now() - hunts_ttl

    hunts = aff4.FACTORY.MultiOpen(hunts_urns, aff4_type="GRRHunt",
                                   token=self.token)
    for hunt in hunts:
      if exception_label in hunt.GetLabelsNames():
        continue

      runner = hunt.GetRunner()
      if runner.context.expires < deadline:
        urns_to_delete.append(hunt.urn)

    aff4.FACTORY.MultiDelete(urns_to_delete, token=self.token)


class CleanCronJobs(cronjobs.SystemCronFlow):
  """Cleaner that deletes old finished cron flows."""

  frequency = rdfvalue.Duration("7d")
  lifetime = rdfvalue.Duration("1d")

  @flow.StateHandler()
  def Start(self):
    cron_jobs_ttl = config_lib.CONFIG["DataRetention.cron_jobs_flows_ttl"]
    if not cron_jobs_ttl:
      self.Log("TTL not set - nothing to do...")
      return

    jobs = cronjobs.CRON_MANAGER.ListJobs(token=self.token)
    jobs_objs = aff4.FACTORY.MultiOpen(jobs, aff4_type="CronJob",
                                       mode="r", token=self.token)

    for obj in jobs_objs:
      age = rdfvalue.RDFDatetime().Now() - cron_jobs_ttl
      obj.DeleteJobFlows(age)
