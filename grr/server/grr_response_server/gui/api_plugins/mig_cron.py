#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import cron_pb2
from grr_response_server.gui.api_plugins import cron


def ToProtoApiCronJob(rdf: cron.ApiCronJob) -> cron_pb2.ApiCronJob:
  return rdf.AsPrimitiveProto()


def ToRDFApiCronJob(proto: cron_pb2.ApiCronJob) -> cron.ApiCronJob:
  return cron.ApiCronJob.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCronJobRun(rdf: cron.ApiCronJobRun) -> cron_pb2.ApiCronJobRun:
  return rdf.AsPrimitiveProto()


def ToRDFApiCronJobRun(proto: cron_pb2.ApiCronJobRun) -> cron.ApiCronJobRun:
  return cron.ApiCronJobRun.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListCronJobsArgs(
    rdf: cron.ApiListCronJobsArgs,
) -> cron_pb2.ApiListCronJobsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobsArgs(
    proto: cron_pb2.ApiListCronJobsArgs,
) -> cron.ApiListCronJobsArgs:
  return cron.ApiListCronJobsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListCronJobsResult(
    rdf: cron.ApiListCronJobsResult,
) -> cron_pb2.ApiListCronJobsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobsResult(
    proto: cron_pb2.ApiListCronJobsResult,
) -> cron.ApiListCronJobsResult:
  return cron.ApiListCronJobsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetCronJobArgs(
    rdf: cron.ApiGetCronJobArgs,
) -> cron_pb2.ApiGetCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetCronJobArgs(
    proto: cron_pb2.ApiGetCronJobArgs,
) -> cron.ApiGetCronJobArgs:
  return cron.ApiGetCronJobArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListCronJobRunsArgs(
    rdf: cron.ApiListCronJobRunsArgs,
) -> cron_pb2.ApiListCronJobRunsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobRunsArgs(
    proto: cron_pb2.ApiListCronJobRunsArgs,
) -> cron.ApiListCronJobRunsArgs:
  return cron.ApiListCronJobRunsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListCronJobRunsResult(
    rdf: cron.ApiListCronJobRunsResult,
) -> cron_pb2.ApiListCronJobRunsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobRunsResult(
    proto: cron_pb2.ApiListCronJobRunsResult,
) -> cron.ApiListCronJobRunsResult:
  return cron.ApiListCronJobRunsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetCronJobRunArgs(
    rdf: cron.ApiGetCronJobRunArgs,
) -> cron_pb2.ApiGetCronJobRunArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetCronJobRunArgs(
    proto: cron_pb2.ApiGetCronJobRunArgs,
) -> cron.ApiGetCronJobRunArgs:
  return cron.ApiGetCronJobRunArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateCronJobArgs(
    rdf: cron.ApiCreateCronJobArgs,
) -> cron_pb2.ApiCreateCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateCronJobArgs(
    proto: cron_pb2.ApiCreateCronJobArgs,
) -> cron.ApiCreateCronJobArgs:
  return cron.ApiCreateCronJobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiForceRunCronJobArgs(
    rdf: cron.ApiForceRunCronJobArgs,
) -> cron_pb2.ApiForceRunCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiForceRunCronJobArgs(
    proto: cron_pb2.ApiForceRunCronJobArgs,
) -> cron.ApiForceRunCronJobArgs:
  return cron.ApiForceRunCronJobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiModifyCronJobArgs(
    rdf: cron.ApiModifyCronJobArgs,
) -> cron_pb2.ApiModifyCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiModifyCronJobArgs(
    proto: cron_pb2.ApiModifyCronJobArgs,
) -> cron.ApiModifyCronJobArgs:
  return cron.ApiModifyCronJobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeleteCronJobArgs(
    rdf: cron.ApiDeleteCronJobArgs,
) -> cron_pb2.ApiDeleteCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteCronJobArgs(
    proto: cron_pb2.ApiDeleteCronJobArgs,
) -> cron.ApiDeleteCronJobArgs:
  return cron.ApiDeleteCronJobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
