#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import jobs_pb2
from grr_response_proto import knowledge_base_pb2
from grr_response_proto import sysinfo_pb2


def ToProtoPackageRepository(
    rdf: rdf_client.PackageRepository,
) -> sysinfo_pb2.PackageRepository:
  return rdf.AsPrimitiveProto()


def ToRDFPackageRepository(
    proto: sysinfo_pb2.PackageRepository,
) -> rdf_client.PackageRepository:
  return rdf_client.PackageRepository.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoManagementAgent(
    rdf: rdf_client.ManagementAgent,
) -> sysinfo_pb2.ManagementAgent:
  return rdf.AsPrimitiveProto()


def ToRDFManagementAgent(
    proto: sysinfo_pb2.ManagementAgent,
) -> rdf_client.ManagementAgent:
  return rdf_client.ManagementAgent.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPwEntry(rdf: rdf_client.PwEntry) -> knowledge_base_pb2.PwEntry:
  return rdf.AsPrimitiveProto()


def ToRDFPwEntry(proto: knowledge_base_pb2.PwEntry) -> rdf_client.PwEntry:
  return rdf_client.PwEntry.FromSerializedBytes(proto.SerializeToString())


def ToProtoGroup(rdf: rdf_client.Group) -> knowledge_base_pb2.Group:
  return rdf.AsPrimitiveProto()


def ToRDFGroup(proto: knowledge_base_pb2.Group) -> rdf_client.Group:
  return rdf_client.Group.FromSerializedBytes(proto.SerializeToString())


def ToProtoUserFromUser(rdf: rdf_client.User) -> knowledge_base_pb2.User:
  return rdf.AsPrimitiveProto()


def ToRDFUser(proto: knowledge_base_pb2.User) -> rdf_client.User:
  return rdf_client.User.FromSerializedBytes(proto.SerializeToString())


def ToProtoUserFromKnowledgeBaseUser(
    rdf: rdf_client.KnowledgeBaseUser,
) -> knowledge_base_pb2.User:
  return rdf.AsPrimitiveProto()


def ToRDFKnowledgeBaseUser(
    proto: knowledge_base_pb2.User,
) -> rdf_client.KnowledgeBaseUser:
  return rdf_client.KnowledgeBaseUser.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoKnowledgeBase(
    rdf: rdf_client.KnowledgeBase,
) -> knowledge_base_pb2.KnowledgeBase:
  return rdf.AsPrimitiveProto()


def ToRDFKnowledgeBase(
    proto: knowledge_base_pb2.KnowledgeBase,
) -> rdf_client.KnowledgeBase:
  return rdf_client.KnowledgeBase.FromSerializedBytes(proto.SerializeToString())


def ToProtoHardwareInfo(
    rdf: rdf_client.HardwareInfo,
) -> sysinfo_pb2.HardwareInfo:
  return rdf.AsPrimitiveProto()


def ToRDFHardwareInfo(
    proto: sysinfo_pb2.HardwareInfo,
) -> rdf_client.HardwareInfo:
  return rdf_client.HardwareInfo.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientInformation(
    rdf: rdf_client.ClientInformation,
) -> jobs_pb2.ClientInformation:
  return rdf.AsPrimitiveProto()


def ToRDFClientInformation(
    proto: jobs_pb2.ClientInformation,
) -> rdf_client.ClientInformation:
  return rdf_client.ClientInformation.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoBufferReference(
    rdf: rdf_client.BufferReference,
) -> jobs_pb2.BufferReference:
  return rdf.AsPrimitiveProto()


def ToRDFBufferReference(
    proto: jobs_pb2.BufferReference,
) -> rdf_client.BufferReference:
  return rdf_client.BufferReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoProcess(rdf: rdf_client.Process) -> sysinfo_pb2.Process:
  return rdf.AsPrimitiveProto()


def ToRDFProcess(proto: sysinfo_pb2.Process) -> rdf_client.Process:
  return rdf_client.Process.FromSerializedBytes(proto.SerializeToString())


def ToProtoNamedPipe(rdf: rdf_client.NamedPipe) -> sysinfo_pb2.NamedPipe:
  return rdf.AsPrimitiveProto()


def ToRDFNamedPipe(proto: sysinfo_pb2.NamedPipe) -> rdf_client.NamedPipe:
  return rdf_client.NamedPipe.FromSerializedBytes(proto.SerializeToString())


def ToProtoSoftwarePackage(
    rdf: rdf_client.SoftwarePackage,
) -> sysinfo_pb2.SoftwarePackage:
  return rdf.AsPrimitiveProto()


def ToRDFSoftwarePackage(
    proto: sysinfo_pb2.SoftwarePackage,
) -> rdf_client.SoftwarePackage:
  return rdf_client.SoftwarePackage.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSoftwarePackages(
    rdf: rdf_client.SoftwarePackages,
) -> sysinfo_pb2.SoftwarePackages:
  return rdf.AsPrimitiveProto()


def ToRDFSoftwarePackages(
    proto: sysinfo_pb2.SoftwarePackages,
) -> rdf_client.SoftwarePackages:
  return rdf_client.SoftwarePackages.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLogMessage(rdf: rdf_client.LogMessage) -> jobs_pb2.LogMessage:
  return rdf.AsPrimitiveProto()


def ToRDFLogMessage(proto: jobs_pb2.LogMessage) -> rdf_client.LogMessage:
  return rdf_client.LogMessage.FromSerializedBytes(proto.SerializeToString())


def ToProtoUname(rdf: rdf_client.Uname) -> jobs_pb2.Uname:
  return rdf.AsPrimitiveProto()


def ToRDFUname(proto: jobs_pb2.Uname) -> rdf_client.Uname:
  return rdf_client.Uname.FromSerializedBytes(proto.SerializeToString())


def ToProtoStartupInfo(rdf: rdf_client.StartupInfo) -> jobs_pb2.StartupInfo:
  return rdf.AsPrimitiveProto()


def ToRDFStartupInfo(proto: jobs_pb2.StartupInfo) -> rdf_client.StartupInfo:
  return rdf_client.StartupInfo.FromSerializedBytes(proto.SerializeToString())


def ToProtoOSXServiceInformation(
    rdf: rdf_client.OSXServiceInformation,
) -> sysinfo_pb2.OSXServiceInformation:
  return rdf.AsPrimitiveProto()


def ToRDFOSXServiceInformation(
    proto: sysinfo_pb2.OSXServiceInformation,
) -> rdf_client.OSXServiceInformation:
  return rdf_client.OSXServiceInformation.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoRunKey(rdf: rdf_client.RunKey) -> sysinfo_pb2.RunKey:
  return rdf.AsPrimitiveProto()


def ToRDFRunKey(proto: sysinfo_pb2.RunKey) -> rdf_client.RunKey:
  return rdf_client.RunKey.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientCrash(rdf: rdf_client.ClientCrash) -> jobs_pb2.ClientCrash:
  return rdf.AsPrimitiveProto()


def ToRDFClientCrash(proto: jobs_pb2.ClientCrash) -> rdf_client.ClientCrash:
  return rdf_client.ClientCrash.FromSerializedBytes(proto.SerializeToString())


def ToProtoEdrAgent(rdf: rdf_client.EdrAgent) -> jobs_pb2.EdrAgent:
  return rdf.AsPrimitiveProto()


def ToRDFEdrAgent(proto: jobs_pb2.EdrAgent) -> rdf_client.EdrAgent:
  return rdf_client.EdrAgent.FromSerializedBytes(proto.SerializeToString())


def ToProtoFleetspeakValidationInfoTag(
    rdf: rdf_client.FleetspeakValidationInfoTag,
) -> jobs_pb2.FleetspeakValidationInfoTag:
  return rdf.AsPrimitiveProto()


def ToRDFFleetspeakValidationInfoTag(
    proto: jobs_pb2.FleetspeakValidationInfoTag,
) -> rdf_client.FleetspeakValidationInfoTag:
  return rdf_client.FleetspeakValidationInfoTag.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFleetspeakValidationInfo(
    rdf: rdf_client.FleetspeakValidationInfo,
) -> jobs_pb2.FleetspeakValidationInfo:
  return rdf.AsPrimitiveProto()


def ToRDFFleetspeakValidationInfo(
    proto: jobs_pb2.FleetspeakValidationInfo,
) -> rdf_client.FleetspeakValidationInfo:
  return rdf_client.FleetspeakValidationInfo.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientSummary(
    rdf: rdf_client.ClientSummary,
) -> jobs_pb2.ClientSummary:
  return rdf.AsPrimitiveProto()


def ToRDFClientSummary(
    proto: jobs_pb2.ClientSummary,
) -> rdf_client.ClientSummary:
  return rdf_client.ClientSummary.FromSerializedBytes(proto.SerializeToString())
