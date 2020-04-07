#!/usr/bin/env python
# Lint as: python3
"""Locally defined rdfvalues."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import apple_firmware_pb2


class EficheckConfig(rdf_structs.RDFProtoStruct):
  """A request to eficheck to collect the EFI hashes."""
  protobuf = apple_firmware_pb2.EficheckConfig


class CollectEfiHashesResponse(rdf_structs.RDFProtoStruct):
  """A response from eficheck with the collected hashes."""
  protobuf = apple_firmware_pb2.CollectEfiHashesResponse
  rdf_deps = [
      rdf_client_action.ExecuteBinaryResponse,
  ]


class DumpEfiImageResponse(rdf_structs.RDFProtoStruct):
  """A response from eficheck with the flash image."""
  protobuf = apple_firmware_pb2.DumpEfiImageResponse
  rdf_deps = [
      rdf_client_action.ExecuteBinaryResponse,
      rdf_paths.PathSpec,
  ]


class EficheckFlowArgs(rdf_structs.RDFProtoStruct):
  """Flow argument to dump the EFI image or collect its hashes."""
  protobuf = apple_firmware_pb2.EficheckFlowArgs


class EfiEntry(rdf_structs.RDFProtoStruct):
  """An EfiEntry."""
  protobuf = apple_firmware_pb2.EfiEntry


class EfiCollection(rdf_structs.RDFProtoStruct):
  """An EfiCollection as forwarded for verification."""
  protobuf = apple_firmware_pb2.EfiCollection
  rdf_deps = [
      EfiEntry,
  ]
