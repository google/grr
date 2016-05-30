#!/usr/bin/env python
"""Simple parsers for cron type files."""


import crontab

from grr.lib import parsers
from grr.lib import utils
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs


class CronTabParser(parsers.FileParser):
  """Parser for crontab files."""

  output_types = ["CronTabFile"]
  supported_artifacts = ["OSXCronTabs", "LinuxCronTabs"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the crontab file."""
    _ = knowledge_base
    entries = []

    crondata = file_object.read(100000)
    jobs = crontab.CronTab(tab=crondata)

    for job in jobs:
      entries.append(rdf_cronjobs.CronTabEntry(
          minute=utils.SmartStr(job.minute),
          hour=utils.SmartStr(job.hour),
          dayofmonth=utils.SmartStr(job.dom),
          month=utils.SmartStr(job.month),
          dayofweek=utils.SmartStr(job.dow),
          command=utils.SmartStr(job.command),
          comment=utils.SmartStr(job.comment)))

    yield rdf_cronjobs.CronTabFile(aff4path=stat.aff4path, jobs=entries)
