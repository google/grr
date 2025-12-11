#!/usr/bin/env python
"""Classes for exporting software package-related data."""

from collections.abc import Iterator

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base


class ExportedSoftwarePackage(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedSoftwarePackage
  rdf_deps = [
      base.ExportedMetadata,
  ]


class SoftwarePackageConverter(base.ExportConverter):
  """Converter for rdf_client.SoftwarePackage structs."""

  input_rdf_type = rdf_client.SoftwarePackage

  _INSTALL_STATE_MAP = {
      rdf_client.SoftwarePackage.InstallState.INSTALLED: (
          ExportedSoftwarePackage.InstallState.INSTALLED
      ),
      rdf_client.SoftwarePackage.InstallState.PENDING: (
          ExportedSoftwarePackage.InstallState.PENDING
      ),
      rdf_client.SoftwarePackage.InstallState.UNINSTALLED: (
          ExportedSoftwarePackage.InstallState.UNINSTALLED
      ),
      rdf_client.SoftwarePackage.InstallState.UNKNOWN: (
          ExportedSoftwarePackage.InstallState.UNKNOWN
      ),
  }

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      software_package: rdf_client.SoftwarePackage,
  ) -> Iterator[ExportedSoftwarePackage]:
    yield ExportedSoftwarePackage(
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


class SoftwarePackagesConverter(base.ExportConverter):
  """Converter for rdf_client.SoftwarePackages structs."""

  input_rdf_type = rdf_client.SoftwarePackages

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      software_packages: rdf_client.SoftwarePackages,
  ) -> Iterator[ExportedSoftwarePackage]:
    conv = SoftwarePackageConverter(options=self.options)
    for p in software_packages.packages:
      for r in conv.Convert(metadata, p):
        yield r


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
