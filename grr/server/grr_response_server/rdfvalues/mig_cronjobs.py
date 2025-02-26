#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs


def ToProtoCronJobRunStatus(
    rdf: rdf_cronjobs.CronJobRunStatus,
) -> jobs_pb2.CronJobRunStatus:
  return rdf.AsPrimitiveProto()


def ToRDFCronJobRunStatus(
    proto: jobs_pb2.CronJobRunStatus,
) -> rdf_cronjobs.CronJobRunStatus:
  return rdf_cronjobs.CronJobRunStatus.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCreateCronJobFlowArgs(
    rdf: rdf_cronjobs.CreateCronJobFlowArgs,
) -> flows_pb2.CreateCronJobFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCreateCronJobFlowArgs(
    proto: flows_pb2.CreateCronJobFlowArgs,
) -> rdf_cronjobs.CreateCronJobFlowArgs:
  return rdf_cronjobs.CreateCronJobFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSystemCronAction(
    rdf: rdf_cronjobs.SystemCronAction,
) -> flows_pb2.SystemCronAction:
  return rdf.AsPrimitiveProto()


def ToRDFSystemCronAction(
    proto: flows_pb2.SystemCronAction,
) -> rdf_cronjobs.SystemCronAction:
  return rdf_cronjobs.SystemCronAction.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntCronAction(
    rdf: rdf_cronjobs.HuntCronAction,
) -> flows_pb2.HuntCronAction:
  return rdf.AsPrimitiveProto()


def ToRDFHuntCronAction(
    proto: flows_pb2.HuntCronAction,
) -> rdf_cronjobs.HuntCronAction:
  return rdf_cronjobs.HuntCronAction.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCronJobAction(
    rdf: rdf_cronjobs.CronJobAction,
) -> flows_pb2.CronJobAction:
  return rdf.AsPrimitiveProto()


def ToRDFCronJobAction(
    proto: flows_pb2.CronJobAction,
) -> rdf_cronjobs.CronJobAction:
  return rdf_cronjobs.CronJobAction.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCronJob(rdf: rdf_cronjobs.CronJob) -> flows_pb2.CronJob:
  return rdf.AsPrimitiveProto()


def ToRDFCronJob(proto: flows_pb2.CronJob) -> rdf_cronjobs.CronJob:
  return rdf_cronjobs.CronJob.FromSerializedBytes(proto.SerializeToString())


def ToProtoCronJobRun(rdf: rdf_cronjobs.CronJobRun) -> flows_pb2.CronJobRun:
  return rdf.AsPrimitiveProto()


def ToRDFCronJobRun(proto: flows_pb2.CronJobRun) -> rdf_cronjobs.CronJobRun:
  return rdf_cronjobs.CronJobRun.FromSerializedBytes(proto.SerializeToString())


def ToProtoCreateCronJobArgs(
    rdf: rdf_cronjobs.CreateCronJobArgs,
) -> flows_pb2.CreateCronJobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCreateCronJobArgs(
    proto: flows_pb2.CreateCronJobArgs,
) -> rdf_cronjobs.CreateCronJobArgs:
  return rdf_cronjobs.CreateCronJobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
