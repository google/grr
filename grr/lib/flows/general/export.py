#!/usr/bin/env python
"""Flows for exporting data out of GRR."""



from grr.lib.flows.general import collectors
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


class Error(Exception):
  pass


class ItemNotExportableError(Error):
  pass


def CollectionItemToAff4Path(item):
  """Converts given RDFValue to an RDFURN of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    item = item.payload

  if isinstance(item, rdf_client.StatEntry):
    return item.aff4path
  elif isinstance(item, file_finder.FileFinderResult):
    return item.stat_entry.aff4path
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return item.downloaded_file.aff4path

  raise ItemNotExportableError()
