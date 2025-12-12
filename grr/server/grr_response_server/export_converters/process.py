#!/usr/bin/env python
"""Classes for exporting Process."""

from collections.abc import Iterator

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import network


class ExportedProcess(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedProcess
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ExportedOpenFile(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedOpenFile
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ProcessToExportedProcessConverter(base.ExportConverter):
  """Converts Process to ExportedProcess."""

  input_rdf_type = rdf_client.Process

  def Convert(
      self, metadata: base.ExportedMetadata, process: rdf_client.Process
  ) -> list[ExportedProcess]:
    """Converts a Process into a ExportedProcess.

    Args:
      metadata: ExportedMetadata to be added to the ExportedProcess.
      process: Process to be converted.

    Returns:
      A list with a single ExportedProcess containing the converted Process.
    """

    result = ExportedProcess(
        metadata=metadata,
        pid=process.pid,
        ppid=process.ppid,
        name=process.name,
        exe=process.exe,
        cmdline=" ".join(process.cmdline),
        ctime=process.ctime,
        real_uid=process.real_uid,
        effective_uid=process.effective_uid,
        saved_uid=process.saved_uid,
        real_gid=process.real_gid,
        effective_gid=process.effective_gid,
        saved_gid=process.saved_gid,
        username=process.username,
        terminal=process.terminal,
        status=process.status,
        nice=process.nice,
        cwd=process.cwd,
        num_threads=process.num_threads,
        user_cpu_time=process.user_cpu_time,
        system_cpu_time=process.system_cpu_time,
        rss_size=process.RSS_size,
        vms_size=process.VMS_size,
        memory_percent=process.memory_percent,
    )
    return [result]


class ProcessToExportedProcessConverterProto(
    base.ExportConverterProto[sysinfo_pb2.Process]
):
  """Converts Process protos to ExportedProcess protos."""

  input_proto_type = sysinfo_pb2.Process
  output_proto_types = (export_pb2.ExportedProcess,)

  def Convert(
      self, metadata: export_pb2.ExportedMetadata, process: sysinfo_pb2.Process
  ) -> list[export_pb2.ExportedProcess]:
    """Converts a Process into a ExportedProcess.

    Args:
      metadata: ExportedMetadata to be added to the ExportedProcess.
      process: Process to be converted.

    Returns:
      A list with a single ExportedProcess containing the converted Process.
    """

    result = export_pb2.ExportedProcess(
        metadata=metadata,
        pid=process.pid,
        ppid=process.ppid,
        name=process.name,
        exe=process.exe,
        cmdline=" ".join(process.cmdline),
        ctime=process.ctime,
        real_uid=process.real_uid,
        effective_uid=process.effective_uid,
        saved_uid=process.saved_uid,
        real_gid=process.real_gid,
        effective_gid=process.effective_gid,
        saved_gid=process.saved_gid,
        username=process.username,
        terminal=process.terminal,
        status=process.status,
        nice=process.nice,
        cwd=process.cwd,
        num_threads=process.num_threads,
        user_cpu_time=process.user_cpu_time,
        system_cpu_time=process.system_cpu_time,
        rss_size=process.RSS_size,
        vms_size=process.VMS_size,
        memory_percent=process.memory_percent,
    )
    return [result]


class ProcessToExportedNetworkConnectionConverter(base.ExportConverter):
  """Converts Process to ExportedNetworkConnection."""

  input_rdf_type = rdf_client.Process

  def Convert(
      self, metadata: base.ExportedMetadata, process: rdf_client.Process
  ) -> Iterator[network.ExportedNetworkConnection]:
    """Converts a Process into a ExportedNetworkConnection.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkConnection.
      process: Process to be converted.

    Returns:
      A generator with a single ExportedNetworkConnection containing the
      converted Process.
    """

    conn_converter = (
        network.NetworkConnectionToExportedNetworkConnectionConverter(
            options=self.options
        )
    )
    return conn_converter.BatchConvert(
        [(metadata, conn) for conn in process.connections]
    )


class ProcessToExportedNetworkConnectionConverterProto(
    base.ExportConverterProto[sysinfo_pb2.Process]
):
  """Converts Process protos to ExportedNetworkConnection protos."""

  input_proto_type = sysinfo_pb2.Process
  output_proto_types = (export_pb2.ExportedNetworkConnection,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      process: sysinfo_pb2.Process,
  ) -> Iterator[export_pb2.ExportedNetworkConnection]:
    """Converts a Process into a ExportedNetworkConnection.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkConnection.
      process: Process to be converted.

    Yields:
      A generator of ExportedNetworkConnection messages.
    """

    conn_converter = (
        network.NetworkConnectionToExportedNetworkConnectionConverterProto()
    )
    for conn in process.connections:
      for converted in conn_converter.Convert(metadata, conn):
        yield converted


class ProcessToExportedOpenFileConverter(base.ExportConverter):
  """Converts Process to ExportedOpenFile."""

  input_rdf_type = rdf_client.Process

  def Convert(
      self, metadata: base.ExportedMetadata, process: rdf_client.Process
  ) -> Iterator[ExportedOpenFile]:
    """Converts a Process into a ExportedOpenFile.

    Args:
      metadata: ExportedMetadata to be added to the ExportedOpenFile.
      process: Process to be converted.

    Yields:
      A generator with a single ExportedOpenFile containing the
      converted Process.
    """

    for f in process.open_files:
      yield ExportedOpenFile(metadata=metadata, pid=process.pid, path=f)


class ProcessToExportedOpenFileConverterProto(
    base.ExportConverterProto[sysinfo_pb2.Process]
):
  """Converts Process protos to ExportedOpenFile protos."""

  input_proto_type = sysinfo_pb2.Process
  output_proto_types = (export_pb2.ExportedOpenFile,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      process: sysinfo_pb2.Process,
  ) -> Iterator[export_pb2.ExportedOpenFile]:
    """Converts a Process into a ExportedOpenFile.

    Args:
      metadata: ExportedMetadata to be added to the ExportedOpenFile.
      process: Process to be converted.

    Yields:
      A generator of ExportedOpenFile messages.
    """

    for f in process.open_files:
      yield export_pb2.ExportedOpenFile(
          metadata=metadata, pid=process.pid, path=f
      )
