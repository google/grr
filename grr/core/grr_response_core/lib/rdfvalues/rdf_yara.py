#!/usr/bin/env python
"""RDFValues used with Yara."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import yara

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2


class YaraSignature(rdfvalue.RDFString):

  def GetRules(self):
    return yara.compile(source=str(self))


class YaraProcessScanRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanRequest
  rdf_deps = [YaraSignature]


class YaraProcessError(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessError
  rdf_deps = [rdf_client.Process]


class YaraStringMatch(rdf_structs.RDFProtoStruct):
  """A result of Yara string matching."""
  protobuf = flows_pb2.YaraStringMatch
  rdf_deps = []

  @classmethod
  def FromLibYaraStringMatch(cls, yara_string_match):
    # Format is described in
    # http://yara.readthedocs.io/en/v3.5.0/yarapython.html
    res = cls()
    res.offset, res.string_id, res.data = yara_string_match
    return res


class YaraMatch(rdf_structs.RDFProtoStruct):
  """A result of Yara matching."""
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


class YaraProcessScanMatch(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanMatch
  rdf_deps = [rdf_client.Process, YaraMatch]


class YaraProcessScanMiss(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanMiss
  rdf_deps = [rdf_client.Process]


class YaraProcessScanResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanResponse
  rdf_deps = [YaraProcessScanMatch, YaraProcessScanMiss, YaraProcessError]


class YaraProcessDumpArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessDumpArgs
  rdf_deps = [rdfvalue.ByteSize]


class YaraProcessDumpInformation(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessDumpInformation
  rdf_deps = [rdf_client.Process, rdf_paths.PathSpec]


class YaraProcessDumpResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessDumpResponse
  rdf_deps = [YaraProcessDumpInformation, YaraProcessError]
