#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner


def ToProtoRequestState(
    rdf: rdf_flow_runner.RequestState,
) -> jobs_pb2.RequestState:
  return rdf.AsPrimitiveProto()


def ToRDFRequestState(
    proto: jobs_pb2.RequestState,
) -> rdf_flow_runner.RequestState:
  return rdf_flow_runner.RequestState.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowRunnerArgs(
    rdf: rdf_flow_runner.FlowRunnerArgs,
) -> flows_pb2.FlowRunnerArgs:
  return rdf.AsPrimitiveProto()


def ToRDFFlowRunnerArgs(
    proto: flows_pb2.FlowRunnerArgs,
) -> rdf_flow_runner.FlowRunnerArgs:
  return rdf_flow_runner.FlowRunnerArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoOutputPluginState(
    rdf: rdf_flow_runner.OutputPluginState,
) -> output_plugin_pb2.OutputPluginState:
  return rdf.AsPrimitiveProto()


def ToRDFOutputPluginState(
    proto: output_plugin_pb2.OutputPluginState,
) -> rdf_flow_runner.OutputPluginState:
  return rdf_flow_runner.OutputPluginState.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowContext(
    rdf: rdf_flow_runner.FlowContext,
) -> flows_pb2.FlowContext:
  return rdf.AsPrimitiveProto()


def ToRDFFlowContext(
    proto: flows_pb2.FlowContext,
) -> rdf_flow_runner.FlowContext:
  return rdf_flow_runner.FlowContext.FromSerializedBytes(
      proto.SerializeToString()
  )
