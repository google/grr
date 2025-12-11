#!/usr/bin/env python
"""Flows for exporting data out of GRR."""

from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.databases import db


class Error(Exception):
  pass


class ItemNotExportableError(Error):

  def __init__(self, item):
    super().__init__("%r is not exportable" % (item,))


def FlowResultToClientPath(item: flows_pb2.FlowResult) -> db.ClientPath:
  """Converts a FlowResult to a ClientPath."""

  client_id = item.client_id
  payload_any = item.payload

  if not client_id:
    raise ValueError("Could not determine client_id.")

  if payload_any.Is(jobs_pb2.StatEntry.DESCRIPTOR):
    payload = jobs_pb2.StatEntry()
    payload_any.Unpack(payload)
    return db.ClientPath.FromPathSpec(
        client_id, mig_paths.ToRDFPathSpec(payload.pathspec)
    )
  elif payload_any.Is(flows_pb2.FileFinderResult.DESCRIPTOR):
    payload = flows_pb2.FileFinderResult()
    payload_any.Unpack(payload)
    return db.ClientPath.FromPathSpec(
        client_id, mig_paths.ToRDFPathSpec(payload.stat_entry.pathspec)
    )
  elif payload_any.Is(flows_pb2.CollectMultipleFilesResult.DESCRIPTOR):
    payload = flows_pb2.CollectMultipleFilesResult()
    payload_any.Unpack(payload)
    return db.ClientPath.FromPathSpec(
        client_id, mig_paths.ToRDFPathSpec(payload.stat.pathspec)
    )
  elif payload_any.Is(flows_pb2.CollectFilesByKnownPathResult.DESCRIPTOR):
    payload = flows_pb2.CollectFilesByKnownPathResult()
    payload_any.Unpack(payload)
    return db.ClientPath.FromPathSpec(
        client_id, mig_paths.ToRDFPathSpec(payload.stat.pathspec)
    )

  raise ItemNotExportableError(item)
