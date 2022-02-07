#!/usr/bin/env python
"""Classes for exporting software package-related data."""

from typing import Iterator

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
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
      rdf_client.SoftwarePackage.InstallState.INSTALLED:
          ExportedSoftwarePackage.InstallState.INSTALLED,
      rdf_client.SoftwarePackage.InstallState.PENDING:
          ExportedSoftwarePackage.InstallState.PENDING,
      rdf_client.SoftwarePackage.InstallState.UNINSTALLED:
          ExportedSoftwarePackage.InstallState.UNINSTALLED,
      rdf_client.SoftwarePackage.InstallState.UNKNOWN:
          ExportedSoftwarePackage.InstallState.UNKNOWN
  }

  def Convert(
      self, metadata: base.ExportedMetadata,
      software_package: rdf_client.SoftwarePackage
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
        installed_by=software_package.installed_by)


class SoftwarePackagesConverter(base.ExportConverter):
  """Converter for rdf_client.SoftwarePackages structs."""

  input_rdf_type = rdf_client.SoftwarePackages

  def Convert(
      self, metadata: base.ExportedMetadata,
      software_packages: rdf_client.SoftwarePackages
  ) -> Iterator[ExportedSoftwarePackage]:
    conv = SoftwarePackageConverter(options=self.options)
    for p in software_packages.packages:
      for r in conv.Convert(metadata, p):
        yield r
