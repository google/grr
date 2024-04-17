#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import config as rdf_config
from grr_response_proto import config_pb2


def ToProtoAdminUIClientWarningRule(
    rdf: rdf_config.AdminUIClientWarningRule,
) -> config_pb2.AdminUIClientWarningRule:
  return rdf.AsPrimitiveProto()


def ToRDFAdminUIClientWarningRule(
    proto: config_pb2.AdminUIClientWarningRule,
) -> rdf_config.AdminUIClientWarningRule:
  return rdf_config.AdminUIClientWarningRule.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoAdminUIClientWarningsConfigOption(
    rdf: rdf_config.AdminUIClientWarningsConfigOption,
) -> config_pb2.AdminUIClientWarningsConfigOption:
  return rdf.AsPrimitiveProto()


def ToRDFAdminUIClientWarningsConfigOption(
    proto: config_pb2.AdminUIClientWarningsConfigOption,
) -> rdf_config.AdminUIClientWarningsConfigOption:
  return rdf_config.AdminUIClientWarningsConfigOption.FromSerializedBytes(
      proto.SerializeToString()
  )
