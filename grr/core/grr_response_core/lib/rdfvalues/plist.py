#!/usr/bin/env python
"""Plist related rdfvalues."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import sysinfo_pb2


class PlistBoolDictEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.PlistBoolDictEntry


class PlistStringDictEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.PlistStringDictEntry


class LaunchdStartCalendarIntervalEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.LaunchdStartCalendarIntervalEntry


class LaunchdKeepAlive(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.LaunchdKeepAlive
  rdf_deps = [
      PlistBoolDictEntry,
  ]


class LaunchdPlist(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.LaunchdPlist
  rdf_deps = [
      LaunchdKeepAlive,
      LaunchdStartCalendarIntervalEntry,
      PlistStringDictEntry,
  ]
