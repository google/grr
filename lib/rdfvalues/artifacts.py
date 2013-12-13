#!/usr/bin/env python
"""Implementation of artifact types."""

import json
import re

from grr.lib import artifact_lib
from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr.proto import artifact_pb2


class Artifact(structs.RDFProtoStruct):
  """An RDFValue representation of an artifact."""
  protobuf = artifact_pb2.Artifact

  required_repeated_fields = ["conditions", "labels", "supported_os", "urls"]

  def ToJson(self):
    artifact_dict = self.ToPrimitiveDict()
    return json.dumps(artifact_dict)

  def ToPrimitiveDict(self):
    """Handle dict generation specifically for Artifacts."""
    artifact_dict = super(Artifact, self).ToPrimitiveDict()
    # Repeated fields that have not been set should return as empty lists.
    for field in self.required_repeated_fields:
      if field not in artifact_dict:
        artifact_dict[field] = []
    return artifact_dict

  def ToExtendedDict(self):
    artifact_dict = self.ToPrimitiveDict()
    # TODO(user): Temporary hack to use the class to get extended information
    #               Until we fully convert to RDFValues.
    artifact_cls = artifact_lib.GenericArtifact.FromDict(artifact_dict)
    artifact_dict["dependencies"] = ([
        str(c) for c in artifact_cls.GetArtifactPathDependencies()])
    return artifact_dict

  def ToPrettyJson(self, extended=False):
    """Print in json format but customized for pretty artifact display."""
    if extended:
      artifact_dict = self.ToExtendedDict()
    else:
      artifact_dict = self.ToPrimitiveDict()

    artifact_json = json.dumps(artifact_dict, indent=2, separators=(",", ": "))
    # Now tidy up the json for better display. Unfortunately json gives us very
    # little control over output format, so we manually tidy it up given that
    # we have a defined format.
    def CompressBraces(name, in_str):
      return re.sub(r"%s\": \[\n\s+(.*)\n\s+" % name,
                    "%s\": [ \\g<1> " % name, in_str)
    artifact_json = CompressBraces("conditions", artifact_json)
    artifact_json = CompressBraces("urls", artifact_json)
    artifact_json = CompressBraces("labels", artifact_json)
    artifact_json = CompressBraces("supported_os", artifact_json)
    artifact_json = re.sub(r"{\n\s+", "{ ", artifact_json)
    return artifact_json


class Collector(structs.RDFProtoStruct):
  """An Artifact Collector."""
  protobuf = artifact_pb2.Collector

  def __init__(self, initializer=None, age=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super(Collector, self).__init__(age=age, **initializer)
    else:
      super(Collector, self).__init__(initializer=initializer, age=age)


class ArtifactName(rdfvalue.RDFString):
  type = "ArtifactName"

