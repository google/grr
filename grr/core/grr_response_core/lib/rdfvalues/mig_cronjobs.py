#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_proto import sysinfo_pb2


def ToProtoCronTabEntry(
    rdf: rdf_cronjobs.CronTabEntry,
) -> sysinfo_pb2.CronTabEntry:
  return rdf.AsPrimitiveProto()


def ToRDFCronTabEntry(
    proto: sysinfo_pb2.CronTabEntry,
) -> rdf_cronjobs.CronTabEntry:
  return rdf_cronjobs.CronTabEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCronTabFile(
    rdf: rdf_cronjobs.CronTabFile,
) -> sysinfo_pb2.CronTabFile:
  return rdf.AsPrimitiveProto()


def ToRDFCronTabFile(
    proto: sysinfo_pb2.CronTabFile,
) -> rdf_cronjobs.CronTabFile:
  return rdf_cronjobs.CronTabFile.FromSerializedBytes(proto.SerializeToString())
