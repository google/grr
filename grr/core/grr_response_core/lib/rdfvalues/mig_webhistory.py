#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import webhistory as rdf_webhistory
from grr_response_proto import sysinfo_pb2


def ToProtoBrowserHistoryItem(
    rdf: rdf_webhistory.BrowserHistoryItem,
) -> sysinfo_pb2.BrowserHistoryItem:
  return rdf.AsPrimitiveProto()


def ToRDFBrowserHistoryItem(
    proto: sysinfo_pb2.BrowserHistoryItem,
) -> rdf_webhistory.BrowserHistoryItem:
  return rdf_webhistory.BrowserHistoryItem.FromSerializedBytes(
      proto.SerializeToString()
  )
