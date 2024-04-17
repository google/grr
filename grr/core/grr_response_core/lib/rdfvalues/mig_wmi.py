#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import wmi as rdf_wmi
from grr_response_proto import sysinfo_pb2


def ToProtoWMIActiveScriptEventConsumer(
    rdf: rdf_wmi.WMIActiveScriptEventConsumer,
) -> sysinfo_pb2.WMIActiveScriptEventConsumer:
  return rdf.AsPrimitiveProto()


def ToRDFWMIActiveScriptEventConsumer(
    proto: sysinfo_pb2.WMIActiveScriptEventConsumer,
) -> rdf_wmi.WMIActiveScriptEventConsumer:
  return rdf_wmi.WMIActiveScriptEventConsumer.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoWMICommandLineEventConsumer(
    rdf: rdf_wmi.WMICommandLineEventConsumer,
) -> sysinfo_pb2.WMICommandLineEventConsumer:
  return rdf.AsPrimitiveProto()


def ToRDFWMICommandLineEventConsumer(
    proto: sysinfo_pb2.WMICommandLineEventConsumer,
) -> rdf_wmi.WMICommandLineEventConsumer:
  return rdf_wmi.WMICommandLineEventConsumer.FromSerializedBytes(
      proto.SerializeToString()
  )
