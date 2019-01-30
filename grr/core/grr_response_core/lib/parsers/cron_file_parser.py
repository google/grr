#!/usr/bin/env python
"""Simple parsers for cron type files."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


import crontab

from future.builtins import str

from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs


class CronTabParser(parser.FileParser):
  """Parser for crontab files."""

  output_types = ["CronTabFile"]
  supported_artifacts = ["LinuxCronTabs", "MacOSCronTabs"]

  def Parse(self, stat, file_object, knowledge_base):
    """Parse the crontab file."""
    _ = knowledge_base
    entries = []

    crondata = file_object.read().decode("utf-8")
    jobs = crontab.CronTab(tab=crondata)

    for job in jobs:
      entries.append(
          rdf_cronjobs.CronTabEntry(
              minute=str(job.minute),
              hour=str(job.hour),
              dayofmonth=str(job.dom),
              month=str(job.month),
              dayofweek=str(job.dow),
              command=str(job.command),
              comment=str(job.comment)))

    try:
      source_urn = file_object.urn
    except AttributeError:
      source_urn = None

    yield rdf_cronjobs.CronTabFile(aff4path=source_urn, jobs=entries)
