#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr_response_proto import sysinfo_pb2


def ToProtoPlistBoolDictEntry(
    rdf: rdf_plist.PlistBoolDictEntry,
) -> sysinfo_pb2.PlistBoolDictEntry:
  return rdf.AsPrimitiveProto()


def ToRDFPlistBoolDictEntry(
    proto: sysinfo_pb2.PlistBoolDictEntry,
) -> rdf_plist.PlistBoolDictEntry:
  return rdf_plist.PlistBoolDictEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPlistStringDictEntry(
    rdf: rdf_plist.PlistStringDictEntry,
) -> sysinfo_pb2.PlistStringDictEntry:
  return rdf.AsPrimitiveProto()


def ToRDFPlistStringDictEntry(
    proto: sysinfo_pb2.PlistStringDictEntry,
) -> rdf_plist.PlistStringDictEntry:
  return rdf_plist.PlistStringDictEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLaunchdStartCalendarIntervalEntry(
    rdf: rdf_plist.LaunchdStartCalendarIntervalEntry,
) -> sysinfo_pb2.LaunchdStartCalendarIntervalEntry:
  return rdf.AsPrimitiveProto()


def ToRDFLaunchdStartCalendarIntervalEntry(
    proto: sysinfo_pb2.LaunchdStartCalendarIntervalEntry,
) -> rdf_plist.LaunchdStartCalendarIntervalEntry:
  return rdf_plist.LaunchdStartCalendarIntervalEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLaunchdKeepAlive(
    rdf: rdf_plist.LaunchdKeepAlive,
) -> sysinfo_pb2.LaunchdKeepAlive:
  return rdf.AsPrimitiveProto()


def ToRDFLaunchdKeepAlive(
    proto: sysinfo_pb2.LaunchdKeepAlive,
) -> rdf_plist.LaunchdKeepAlive:
  return rdf_plist.LaunchdKeepAlive.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLaunchdPlist(
    rdf: rdf_plist.LaunchdPlist,
) -> sysinfo_pb2.LaunchdPlist:
  return rdf.AsPrimitiveProto()


def ToRDFLaunchdPlist(
    proto: sysinfo_pb2.LaunchdPlist,
) -> rdf_plist.LaunchdPlist:
  return rdf_plist.LaunchdPlist.FromSerializedBytes(proto.SerializeToString())
