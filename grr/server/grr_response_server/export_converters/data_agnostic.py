#!/usr/bin/env python
"""Classes for exporting data as a generated flat RDFValue."""

import logging

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_server.export_converters import base


class AutoExportedProtoStruct(rdf_structs.RDFProtoStruct):
  """Special base class for auto-exported values."""


class DataAgnosticExportConverter(base.ExportConverter):
  """Export converter that yields flattened versions of passed values.

  NOTE: DataAgnosticExportConverter discards complex types: repeated
  fields and nested messages. Only the primitive types (including enums)
  are preserved.
  """

  # Cache used for generated classes.
  classes_cache = {}

  def ExportedClassNameForValue(self, value):
    return "AutoExported" + compatibility.GetName(value.__class__)

  def MakeFlatRDFClass(self, value):
    """Generates flattened RDFValue class definition for the given value."""

    def Flatten(self, metadata, value_to_flatten):
      if metadata:
        self.metadata = metadata

      for desc in value_to_flatten.type_infos:
        if desc.name == "metadata":
          continue
        if hasattr(self, desc.name) and value_to_flatten.HasField(desc.name):
          setattr(self, desc.name, getattr(value_to_flatten, desc.name))

    descriptors = []
    enums = {}

    # Metadata is always the first field of exported data.
    descriptors.append(
        rdf_structs.ProtoEmbedded(
            name="metadata", field_number=1, nested=base.ExportedMetadata))

    for number, desc in sorted(value.type_infos_by_field_number.items()):
      # Name 'metadata' is reserved to store ExportedMetadata value.
      if desc.name == "metadata":
        logging.debug("Ignoring 'metadata' field in %s.",
                      value.__class__.__name__)
        continue

      # Copy descriptors for primivie values as-is, just make sure their
      # field number is correct.
      if isinstance(desc, (rdf_structs.ProtoBinary, rdf_structs.ProtoString,
                           rdf_structs.ProtoUnsignedInteger,
                           rdf_structs.ProtoRDFValue, rdf_structs.ProtoEnum)):
        # Incrementing field number by 1, as 1 is always occuppied by metadata.
        descriptors.append(desc.Copy(field_number=number + 1))

      if (isinstance(desc, rdf_structs.ProtoEnum) and
          not isinstance(desc, rdf_structs.ProtoBoolean)):
        # Attach the enum container to the class for easy reference:
        enums[desc.enum_name] = desc.enum_container

    # Create the class as late as possible. This will modify a
    # metaclass registry, we need to make sure there are no problems.
    output_class = compatibility.MakeType(
        self.ExportedClassNameForValue(value), (AutoExportedProtoStruct,),
        dict(Flatten=Flatten))

    for descriptor in descriptors:
      output_class.AddDescriptor(descriptor)

    for name, container in enums.items():
      setattr(output_class, name, container)

    return output_class

  def Convert(self, metadata, value):
    class_name = self.ExportedClassNameForValue(value)
    try:
      cls = DataAgnosticExportConverter.classes_cache[class_name]
    except KeyError:
      cls = self.MakeFlatRDFClass(value)
      DataAgnosticExportConverter.classes_cache[class_name] = cls

    result_obj = cls()
    result_obj.Flatten(metadata, value)
    yield result_obj

  def BatchConvert(self, metadata_value_pairs):
    for metadata, value in metadata_value_pairs:
      for result in self.Convert(metadata, value):
        yield result
