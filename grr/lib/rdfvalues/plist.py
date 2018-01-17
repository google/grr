#!/usr/bin/env python
"""Plist related rdfvalues."""

from grr.lib import lexer
from grr.lib import plist
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


class FilterString(rdfvalue.RDFString):
  """An argument that is a valid filter string parsed by query_parser_cls.

  The class member query_parser_cls should be overriden by derived classes.
  """
  # A subclass of lexer.Searchparser able to parse textual queries.
  query_parser_cls = lexer.SearchParser

  def ParseFromString(self, value):
    super(FilterString, self).ParseFromString(value)
    try:
      self.query_parser_cls(self._value).Parse()
    except lexer.ParseError, e:
      raise type_info.TypeValueError("Malformed filter: %s" % (e))


class PlistQuery(FilterString):
  query_parser_cls = plist.PlistFilterParser


class PlistBoolDictEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.PlistBoolDictEntry


class PlistStringDictEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.PlistStringDictEntry


class PlistRequest(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.PlistRequest
  rdf_deps = [
      paths.PathSpec,
      PlistQuery,
  ]


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
      rdfvalue.RDFURN,
  ]
