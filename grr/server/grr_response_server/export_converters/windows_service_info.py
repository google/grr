#!/usr/bin/env python
"""Classes for exporting WindowsServiceInformation."""

from typing import Iterator

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


class ExportedWindowsServiceInformation(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedWindowsServiceInformation
  rdf_deps = [base.ExportedMetadata]


class WindowsServiceInformationConverter(base.ExportConverter):
  """Export converter for WindowsServiceInformation."""

  input_rdf_type = rdf_client.WindowsServiceInformation

  def Convert(
      self, metadata: base.ExportedMetadata,
      i: rdf_client.WindowsServiceInformation
  ) -> Iterator[ExportedWindowsServiceInformation]:
    wmi_components = []
    for key in sorted(i.wmi_information.keys()):
      value = i.wmi_information[key]
      wmi_components.append(f"{key}={value}")

    yield ExportedWindowsServiceInformation(
        metadata=metadata,
        name=i.name,
        description=i.description,
        state=i.state,
        wmi_information=",".join(wmi_components),
        display_name=i.display_name,
        driver_package_id=i.driver_package_id,
        error_control=i.error_control,
        image_path=i.image_path,
        object_name=i.object_name,
        startup_type=i.startup_type,
        service_type=i.service_type,
        group_name=i.group_name,
        service_dll=i.service_dll,
        registry_key=i.registry_key,
    )
