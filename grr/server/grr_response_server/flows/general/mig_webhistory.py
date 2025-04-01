#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.flows.general import webhistory


def ToProtoCollectBrowserHistoryArgs(
    rdf: webhistory.CollectBrowserHistoryArgs,
) -> flows_pb2.CollectBrowserHistoryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCollectBrowserHistoryArgs(
    proto: flows_pb2.CollectBrowserHistoryArgs,
) -> webhistory.CollectBrowserHistoryArgs:
  return webhistory.CollectBrowserHistoryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCollectBrowserHistoryResult(
    rdf: webhistory.CollectBrowserHistoryResult,
) -> flows_pb2.CollectBrowserHistoryResult:
  return rdf.AsPrimitiveProto()


def ToRDFCollectBrowserHistoryResult(
    proto: flows_pb2.CollectBrowserHistoryResult,
) -> webhistory.CollectBrowserHistoryResult:
  return webhistory.CollectBrowserHistoryResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoBrowserProgress(
    rdf: webhistory.BrowserProgress,
) -> flows_pb2.BrowserProgress:
  return rdf.AsPrimitiveProto()


def ToRDFBrowserProgress(
    proto: flows_pb2.BrowserProgress,
) -> webhistory.BrowserProgress:
  return webhistory.BrowserProgress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCollectBrowserHistoryProgress(
    rdf: webhistory.CollectBrowserHistoryProgress,
) -> flows_pb2.CollectBrowserHistoryProgress:
  return rdf.AsPrimitiveProto()


def ToRDFCollectBrowserHistoryProgress(
    proto: flows_pb2.CollectBrowserHistoryProgress,
) -> webhistory.CollectBrowserHistoryProgress:
  return webhistory.CollectBrowserHistoryProgress.FromSerializedBytes(
      proto.SerializeToString()
  )
