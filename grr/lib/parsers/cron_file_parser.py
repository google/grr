#!/usr/bin/env python
"""Simple parsers for cron type files."""


import crontab

from grr.lib import parser
from grr.lib import utils
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs


class CronTabParser(parser.FileParser):
  """Parser for crontab files."""

  output_types = ["CronTabFile"]
  supported_artifacts = ["LinuxCronTabs", "MacOSCronTabs"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the crontab file."""
    _ = knowledge_base
    entries = []

    crondata = file_object.read()
    jobs = crontab.CronTab(tab=crondata)

    for job in jobs:
      entries.append(
          rdf_cronjobs.CronTabEntry(
              minute=utils.SmartStr(job.minute),
              hour=utils.SmartStr(job.hour),
              dayofmonth=utils.SmartStr(job.dom),
              month=utils.SmartStr(job.month),
              dayofweek=utils.SmartStr(job.dow),
              command=utils.SmartStr(job.command),
              comment=utils.SmartStr(job.comment)))

    try:
      source_urn = file_object.urn
    except AttributeError:
      source_urn = None

    yield rdf_cronjobs.CronTabFile(aff4path=source_urn, jobs=entries)
