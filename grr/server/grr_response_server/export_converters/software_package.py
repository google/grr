#!/usr/bin/env python
"""Classes for exporting software package-related data."""

from collections.abc import Iterator

from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base


class SoftwarePackageConverterProto(
    base.ExportConverterProto[sysinfo_pb2.SoftwarePackage]
):
  """Converter for sysinfo_pb2.SoftwarePackage protos."""

  input_proto_type = sysinfo_pb2.SoftwarePackage
  output_proto_types = (export_pb2.ExportedSoftwarePackage,)

  _INSTALL_STATE_MAP = {
      sysinfo_pb2.SoftwarePackage.InstallState.INSTALLED: (
          export_pb2.ExportedSoftwarePackage.InstallState.INSTALLED
      ),
      sysinfo_pb2.SoftwarePackage.InstallState.PENDING: (
          export_pb2.ExportedSoftwarePackage.InstallState.PENDING
      ),
      sysinfo_pb2.SoftwarePackage.InstallState.UNINSTALLED: (
          export_pb2.ExportedSoftwarePackage.InstallState.UNINSTALLED
      ),
      sysinfo_pb2.SoftwarePackage.InstallState.UNKNOWN: (
          export_pb2.ExportedSoftwarePackage.InstallState.UNKNOWN
      ),
  }

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      software_package: sysinfo_pb2.SoftwarePackage,
  ) -> Iterator[export_pb2.ExportedSoftwarePackage]:
    yield export_pb2.ExportedSoftwarePackage(
        metadata=metadata,
        name=software_package.name,
        version=software_package.version,
        architecture=software_package.architecture,
        publisher=software_package.publisher,
        install_state=self._INSTALL_STATE_MAP[software_package.install_state],
        description=software_package.description,
        installed_on=software_package.installed_on,
        installed_by=software_package.installed_by,
        epoch=software_package.epoch,
        source_rpm=software_package.source_rpm,
        source_deb=software_package.source_deb,
    )


class SoftwarePackagesConverterProto(
    base.ExportConverterProto[sysinfo_pb2.SoftwarePackages]
):
  """Converter for sysinfo_pb2.SoftwarePackages protos."""

  input_proto_type = sysinfo_pb2.SoftwarePackages
  output_proto_types = (export_pb2.ExportedSoftwarePackage,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      software_packages: sysinfo_pb2.SoftwarePackages,
  ) -> Iterator[export_pb2.ExportedSoftwarePackage]:
    conv = SoftwarePackageConverterProto()
    for p in software_packages.packages:
      yield from conv.Convert(metadata, p)
