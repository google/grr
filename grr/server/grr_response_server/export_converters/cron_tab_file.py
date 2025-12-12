#!/usr/bin/env python
"""Classes for exporting CronTabFile."""

from collections.abc import Iterator

from grr_response_core.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base


class ExportedCronTabEntry(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedCronTabEntry
  rdf_deps = [base.ExportedMetadata]


class CronTabFileConverter(base.ExportConverter):
  """Converter for rdf_client.SoftwarePackages structs."""

  input_rdf_type = rdf_cronjobs.CronTabFile

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      cron_tab_file: rdf_cronjobs.CronTabFile,
  ) -> Iterator[ExportedCronTabEntry]:
    for j in cron_tab_file.jobs:
      yield ExportedCronTabEntry(
          metadata=metadata,
          cron_file_path=cron_tab_file.path,
          minute=j.minute,
          hour=j.hour,
          dayofmonth=j.dayofmonth,
          month=j.month,
          dayofweek=j.dayofweek,
          command=j.command,
          comment=j.comment,
      )


class CronTabFileToExportedCronTabEntryProto(
    base.ExportConverterProto[sysinfo_pb2.CronTabFile]
):
  """Converter for sysinfo_pb2.CronTabFile."""

  input_proto_type = sysinfo_pb2.CronTabFile
  output_proto_types = (export_pb2.ExportedCronTabEntry,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      cron_tab_file: sysinfo_pb2.CronTabFile,
  ) -> Iterator[export_pb2.ExportedCronTabEntry]:
    for j in cron_tab_file.jobs:
      yield export_pb2.ExportedCronTabEntry(
          metadata=metadata,
          cron_file_path=cron_tab_file.path,
          minute=j.minute,
          hour=j.hour,
          dayofmonth=j.dayofmonth,
          month=j.month,
          dayofweek=j.dayofweek,
          command=j.command,
          comment=j.comment,
      )
