#!/usr/bin/env python
"""Flows for exporting data out of GRR."""


from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import flows as rdf_flows
from grr.server.grr_response_server.flows.general import collectors


class Error(Exception):
  pass


class ItemNotExportableError(Error):
  pass


def CollectionItemToAff4Path(item, client_id=None):
  """Converts given RDFValue to an RDFURN of a file to be downloaded."""
  if isinstance(item, rdf_flows.GrrMessage):
    client_id = item.source
    item = item.payload
  if not client_id:
    raise ValueError("Could not determine client_id.")

  if isinstance(item, rdf_client.StatEntry):
    return item.AFF4Path(client_id)
  elif isinstance(item, rdf_file_finder.FileFinderResult):
    return item.stat_entry.AFF4Path(client_id)
  elif isinstance(item, collectors.ArtifactFilesDownloaderResult):
    if item.HasField("downloaded_file"):
      return item.downloaded_file.AFF4Path(client_id)

  raise ItemNotExportableError()
