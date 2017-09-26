#!/usr/bin/env python
"""RDFValues used with Yara."""

import yara

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs
from grr.proto import flows_pb2


class YaraSignature(rdfvalue.RDFString):

  def GetRules(self):
    return yara.compile(source=str(self))


class YaraProcessScanRequest(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanRequest
  rdf_deps = [YaraSignature]


class YaraProcessScanError(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanError
  rdf_deps = [rdf_client.Process]


class YaraStringMatch(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraStringMatch
  rdf_deps = []

  @classmethod
  def FromLibYaraStringMatch(cls, yara_string_match):
    # Format is described in
    # http://yara.readthedocs.io/en/v3.5.0/yarapython.html
    res = cls()
    res.offset, res.string_id, res.data = yara_string_match
    return res


class YaraMatch(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraMatch
  rdf_deps = [YaraStringMatch]

  @classmethod
  def FromLibYaraMatch(cls, yara_match):
    res = cls()
    res.rule_name = yara_match.rule
    res.string_matches = [
        YaraStringMatch.FromLibYaraStringMatch(sm) for sm in yara_match.strings
    ]
    return res


class YaraProcessScanMatch(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanMatch
  rdf_deps = [rdf_client.Process, YaraMatch]


class YaraProcessScanResponse(structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanResponse
  rdf_deps = [YaraProcessScanMatch, YaraProcessScanError, rdf_client.Process]
