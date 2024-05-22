#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import api_call_router_pb2
from grr_response_server.gui import api_call_robot_router


def ToProtoRobotRouterSearchClientsParams(
    rdf: api_call_robot_router.RobotRouterSearchClientsParams,
) -> api_call_router_pb2.RobotRouterSearchClientsParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterSearchClientsParams(
    proto: api_call_router_pb2.RobotRouterSearchClientsParams,
) -> api_call_robot_router.RobotRouterSearchClientsParams:
  return (
      api_call_robot_router.RobotRouterSearchClientsParams.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoRobotRouterFileFinderFlowParams(
    rdf: api_call_robot_router.RobotRouterFileFinderFlowParams,
) -> api_call_router_pb2.RobotRouterFileFinderFlowParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterFileFinderFlowParams(
    proto: api_call_router_pb2.RobotRouterFileFinderFlowParams,
) -> api_call_robot_router.RobotRouterFileFinderFlowParams:
  return (
      api_call_robot_router.RobotRouterFileFinderFlowParams.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoRobotRouterArtifactCollectorFlowParams(
    rdf: api_call_robot_router.RobotRouterArtifactCollectorFlowParams,
) -> api_call_router_pb2.RobotRouterArtifactCollectorFlowParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterArtifactCollectorFlowParams(
    proto: api_call_router_pb2.RobotRouterArtifactCollectorFlowParams,
) -> api_call_robot_router.RobotRouterArtifactCollectorFlowParams:
  return api_call_robot_router.RobotRouterArtifactCollectorFlowParams.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRobotRouterGetFlowParams(
    rdf: api_call_robot_router.RobotRouterGetFlowParams,
) -> api_call_router_pb2.RobotRouterGetFlowParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterGetFlowParams(
    proto: api_call_router_pb2.RobotRouterGetFlowParams,
) -> api_call_robot_router.RobotRouterGetFlowParams:
  return api_call_robot_router.RobotRouterGetFlowParams.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRobotRouterListFlowResultsParams(
    rdf: api_call_robot_router.RobotRouterListFlowResultsParams,
) -> api_call_router_pb2.RobotRouterListFlowResultsParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterListFlowResultsParams(
    proto: api_call_router_pb2.RobotRouterListFlowResultsParams,
) -> api_call_robot_router.RobotRouterListFlowResultsParams:
  return api_call_robot_router.RobotRouterListFlowResultsParams.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRobotRouterListFlowLogsParams(
    rdf: api_call_robot_router.RobotRouterListFlowLogsParams,
) -> api_call_router_pb2.RobotRouterListFlowLogsParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterListFlowLogsParams(
    proto: api_call_router_pb2.RobotRouterListFlowLogsParams,
) -> api_call_robot_router.RobotRouterListFlowLogsParams:
  return (
      api_call_robot_router.RobotRouterListFlowLogsParams.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoRobotRouterGetFlowFilesArchiveParams(
    rdf: api_call_robot_router.RobotRouterGetFlowFilesArchiveParams,
) -> api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams:
  return rdf.AsPrimitiveProto()


def ToRDFRobotRouterGetFlowFilesArchiveParams(
    proto: api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams,
) -> api_call_robot_router.RobotRouterGetFlowFilesArchiveParams:
  return api_call_robot_router.RobotRouterGetFlowFilesArchiveParams.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCallRobotRouterParams(
    rdf: api_call_robot_router.ApiCallRobotRouterParams,
) -> api_call_router_pb2.ApiCallRobotRouterParams:
  return rdf.AsPrimitiveProto()


def ToRDFApiCallRobotRouterParams(
    proto: api_call_router_pb2.ApiCallRobotRouterParams,
) -> api_call_robot_router.ApiCallRobotRouterParams:
  return api_call_robot_router.ApiCallRobotRouterParams.FromSerializedBytes(
      proto.SerializeToString()
  )
