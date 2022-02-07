#!/usr/bin/env python
"""Simple parsers for cron type files."""


from typing import IO
from typing import Iterator

import crontab

from grr_response_core.lib import parsers
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


class CronTabParser(parsers.SingleFileParser[rdf_cronjobs.CronTabFile]):
  """Parser for crontab files."""

  output_types = [rdf_cronjobs.CronTabFile]
  supported_artifacts = ["LinuxCronTabs", "MacOSCronTabs"]

  def ParseFile(
      self,
      knowledge_base: rdf_client.KnowledgeBase,
      pathspec: rdf_paths.PathSpec,
      filedesc: IO[bytes],
  ) -> Iterator[rdf_cronjobs.CronTabFile]:
    del knowledge_base  # Unused.

    entries = []

    crondata = filedesc.read().decode("utf-8")
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

    yield rdf_cronjobs.CronTabFile(
        # We're interested in the nominal file path, not the full Pathspec.
        path=pathspec.last.path,
        jobs=entries)
