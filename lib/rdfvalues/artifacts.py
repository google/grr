#!/usr/bin/env python
"""Implementation of artifact types."""

from grr.lib import artifact_lib
from grr.lib import artifact_registry
from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr.proto import artifact_pb2
from grr.proto import flows_pb2


class ArtifactCollectorFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactCollectorFlowArgs

  def Validate(self):
    if not self.artifact_list:
      raise ValueError("No artifacts to collect.")


class ArtifactSource(structs.RDFProtoStruct):
  """An ArtifactSource."""
  protobuf = artifact_pb2.ArtifactSource

  def __init__(self, initializer=None, age=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super(ArtifactSource, self).__init__(age=age, **initializer)
    else:
      super(ArtifactSource, self).__init__(initializer=initializer, age=age,
                                           **kwarg)

  def Validate(self):
    """Check the source is well constructed."""
    # Catch common mistake of path vs paths.
    if self.attributes.GetItem("paths"):
      if not isinstance(self.attributes.GetItem("paths"), list):
        raise artifact_registry.ArtifactDefinitionError(
            "Arg 'paths' that is not a list.")

    if self.attributes.GetItem("path"):
      if not isinstance(self.attributes.GetItem("path"), basestring):
        raise artifact_registry.ArtifactDefinitionError(
            "Arg 'path' is not a string.")

    # Check all returned types.
    if self.returned_types:
      for rdf_type in self.returned_types:
        if rdf_type not in rdfvalue.RDFValue.classes:
          raise artifact_registry.ArtifactDefinitionError(
              "Invalid return type %s" % rdf_type)

    if str(self.type) not in artifact_lib.TYPE_MAP:
      raise artifact_registry.ArtifactDefinitionError(
          "Invalid type %s." % self.type)

    src_type = artifact_lib.TYPE_MAP[str(self.type)]
    required_attributes = src_type.get("required_attributes", [])
    missing_attributes = set(
        required_attributes).difference(self.attributes.keys())
    if missing_attributes:
      raise artifact_registry.ArtifactDefinitionError(
          "Missing required attributes: %s." % missing_attributes)


class ArtifactName(rdfvalue.RDFString):
  type = "ArtifactName"
