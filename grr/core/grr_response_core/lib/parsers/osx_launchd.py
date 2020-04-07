#!/usr/bin/env python
# Lint as: python3
# Copyright 2012 Google Inc. All Rights Reserved.
"""Parser for OSX launchd jobs."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from grr_response_core.lib import parser
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import standard as rdf_standard


class OSXLaunchdJobDict(object):
  """Cleanup launchd jobs reported by the service management framework.

  Exclude some rubbish like logged requests that aren't real jobs (see
  launchctl man page).  Examples:

  Exclude 0x7f8759d30310.anonymous.launchd
  Exclude 0x7f8759d1d200.mach_init.crash_inspector
  Keep [0x0-0x21021].com.google.GoogleDrive

  We could probably just exclude anything starting with a memory address, but
  I'm being more specific here as a tradeoff between sensible results and places
  for malware to hide.
  """

  def __init__(self, launchdjobs):
    """Initialize.

    Args:
      launchdjobs: NSCFArray of NSCFDictionarys containing launchd job data from
                   the ServiceManagement framework.
    """
    self.launchdjobs = launchdjobs

    self.blacklist_regex = [
        re.compile(r"^0x[a-z0-9]+\.anonymous\..+$"),
        re.compile(r"^0x[a-z0-9]+\.mach_init\.(crash_inspector|Inspector)$"),
    ]

  def Parse(self):
    """Parse the list of jobs and yield the good ones."""
    for item in self.launchdjobs:
      if not self.FilterItem(item):
        yield item

  def FilterItem(self, launchditem):
    """Should this job be filtered.

    Args:
      launchditem: job NSCFDictionary
    Returns:
      True if the item should be filtered (dropped)
    """
    for regex in self.blacklist_regex:
      if regex.match(launchditem.get("Label", "")):
        return True
    return False


class DarwinPersistenceMechanismsParser(parser.ArtifactFilesParser):
  """Turn various persistence objects into PersistenceFiles."""
  output_types = [rdf_standard.PersistenceFile]
  supported_artifacts = ["DarwinPersistenceMechanisms"]

  def Parse(self, persistence, knowledge_base):
    """Convert persistence collector output to downloadable rdfvalues."""
    pathspec = None

    if isinstance(persistence, rdf_client.OSXServiceInformation):
      if persistence.program:
        pathspec = rdf_paths.PathSpec(
            path=persistence.program,
            pathtype=rdf_paths.PathSpec.PathType.UNSET)
      elif persistence.args:
        pathspec = rdf_paths.PathSpec(
            path=persistence.args[0],
            pathtype=rdf_paths.PathSpec.PathType.UNSET)

    if pathspec is not None:
      yield rdf_standard.PersistenceFile(pathspec=pathspec)
