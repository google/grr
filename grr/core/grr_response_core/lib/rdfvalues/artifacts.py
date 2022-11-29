#!/usr/bin/env python
"""rdf value representation for artifact collector parameters."""

import collections
from typing import Type

from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util.compat import json
from grr_response_core.lib.util.compat import yaml
from grr_response_proto import artifact_pb2
from grr_response_proto import flows_pb2


class ConditionError(Exception):
  """An invalid artifact condition was specified."""


class ArtifactDefinitionError(Exception):
  """An exception class thrown upon encountering malformed artifact.

  Args:
    target: A string representing object for which the error was encountered.
    details: A string with more details about the problem.
    cause: An optional exception that triggered the exception.
  """

  def __init__(self, target, details, cause=None):
    message = "%s: %s" % (target, details)
    if cause:
      message += ": %s" % cause

    super().__init__(message)


class ArtifactSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about syntax problems.
    cause: An optional exception that triggered the syntax error.
  """

  def __init__(self, artifact, details, cause=None):
    super().__init__(artifact.name, details, cause)


class ArtifactDependencyError(ArtifactDefinitionError):
  """An exception class representing dependency errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about dependency problems.
    cause: An optional exception that triggered the dependency error.
  """

  def __init__(self, artifact, details, cause=None):
    super().__init__(artifact.name, details, cause)


class ArtifactSourceSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact sources.

  Args:
    source: An artifact source object for which the error was encountered.
    details: A string with more details about syntax problems.
  """

  def __init__(self, source, details):
    super().__init__(source.type, details)


class ArtifactNotRegisteredError(Exception):
  """Artifact is not present in the registry."""


class ArtifactSource(rdf_structs.RDFProtoStruct):
  """An ArtifactSource."""
  protobuf = artifact_pb2.ArtifactSource
  rdf_deps = [
      rdf_protodict.Dict,
  ]

  OUTPUT_UNDEFINED = "Undefined"

  TYPE_MAP = {
      artifact_pb2.ArtifactSource.GRR_CLIENT_ACTION: {
          "required_attributes": ["client_action"],
          "output_type": OUTPUT_UNDEFINED
      },
      artifact_pb2.ArtifactSource.FILE: {
          "required_attributes": ["paths"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.GREP: {
          "required_attributes": ["paths", "content_regex_list"],
          "output_type": "BufferReference"
      },
      # TODO(hanuszczak): `DIRECTORY` is deprecated [1], it should be removed.
      #
      # [1]: https://github.com/ForensicArtifacts/artifacts/pull/475
      artifact_pb2.ArtifactSource.DIRECTORY: {
          "required_attributes": ["paths"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.LIST_FILES: {
          "required_attributes": ["paths"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.PATH: {
          "required_attributes": ["paths"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.REGISTRY_KEY: {
          "required_attributes": ["keys"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.REGISTRY_VALUE: {
          "required_attributes": ["key_value_pairs"],
          "output_type": "RDFString"
      },
      artifact_pb2.ArtifactSource.WMI: {
          "required_attributes": ["query"],
          "output_type": "Dict"
      },
      artifact_pb2.ArtifactSource.COMMAND: {
          "required_attributes": ["cmd", "args"],
          "output_type": "ExecuteResponse"
      },
      # Running Rekall plugins is deprecated, we keep the type alive so we are
      # not surprised if an old artifact is encountered.
      # TODO(amoser): Remove this.
      artifact_pb2.ArtifactSource.REKALL_PLUGIN: {
          "required_attributes": ["plugin"],
          "output_type": "RekallResponse"
      },
      # ARTIFACT is the legacy name for ARTIFACT_GROUP
      # per: https://github.com/ForensicArtifacts/artifacts/pull/143
      # TODO(user): remove legacy support after migration.
      artifact_pb2.ArtifactSource.ARTIFACT: {
          "required_attributes": ["names"],
          "output_type": OUTPUT_UNDEFINED
      },
      artifact_pb2.ArtifactSource.ARTIFACT_FILES: {
          "required_attributes": ["artifact_list"],
          "output_type": "StatEntry"
      },
      artifact_pb2.ArtifactSource.ARTIFACT_GROUP: {
          "required_attributes": ["names"],
          "output_type": OUTPUT_UNDEFINED
      }
  }

  def __init__(self, initializer=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super().__init__(**initializer)
    else:
      super().__init__(initializer=initializer, **kwarg)

  def Validate(self):
    """Check the source is well constructed."""
    self._ValidateReturnedTypes()
    self._ValidatePaths()
    self._ValidateType()
    self._ValidateRequiredAttributes()
    self._ValidateCommandArgs()

  def _ValidateCommandArgs(self):
    if self.type != ArtifactSource.SourceType.COMMAND:
      return

    # Specifying command execution artifacts with multiple arguments as a single
    # string is a common mistake. For example, an artifact with `ls` as a
    # command and `["-l -a"]` as arguments will not work. Instead, arguments
    # need to be split into multiple elements like `["-l", "-a"]`.
    args = self.attributes.GetItem("args")
    if len(args) == 1 and " " in args[0]:
      detail = "single argument '%s' containing a space" % args[0]
      raise ArtifactSourceSyntaxError(self, detail)

  def _ValidateReturnedTypes(self):
    for rdf_type in self.returned_types:
      # TODO(hanuszczak): Why do we have to do it like this? Is a simple call
      # with `isinstance` not enough? Why do we have to use that weird metaclass
      # machinery here?
      if rdf_type not in rdfvalue.RDFValue.classes:
        detail = "invalid return type '%s'" % rdf_type
        raise ArtifactSourceSyntaxError(self, detail)

  def _ValidatePaths(self):
    # Catch common mistake of path vs paths.
    paths = self.attributes.GetItem("paths")
    if paths and not isinstance(paths, list):
      raise ArtifactSourceSyntaxError(self, "`paths` is not a list")

    # TODO(hanuszczak): It looks like no collector is using `path` attribute.
    # Is this really necessary?
    path = self.attributes.GetItem("path")
    if path and not isinstance(path, str):
      raise ArtifactSourceSyntaxError(self, "`path` is not a string")

  def _ValidateType(self):
    # TODO(hanuszczak): Since `type` is an enum, is this validation really
    # necessary?
    if self.type not in self.TYPE_MAP:
      raise ArtifactSourceSyntaxError(self, "invalid type '%s'" % self.type)

  def _ValidateRequiredAttributes(self):
    required = set(self.TYPE_MAP[self.type].get("required_attributes", []))
    provided = set(self.attributes.keys())
    missing = required.difference(provided)

    if missing:
      quoted = ("'%s'" % attribute for attribute in missing)
      detail = "missing required attributes: %s" % ", ".join(quoted)
      raise ArtifactSourceSyntaxError(self, detail)


class ArtifactName(rdfvalue.RDFString):
  pass


class Artifact(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an artifact."""
  protobuf = artifact_pb2.Artifact
  rdf_deps = [
      ArtifactName,
      ArtifactSource,
  ]

  required_repeated_fields = [
      # List of object filter rules that define whether Artifact collection
      # should run. These operate as an AND operator, all conditions
      # must pass for it to run. OR operators should be implemented as their own
      # conditions.
      "conditions",
      # A list of labels that help users find artifacts. Must be in the list
      # ARTIFACT_LABELS.
      "labels",
      # Which OS are supported by the Artifact e.g. Linux, Windows, Darwin
      # Note that this can be implemented by conditions as well, but this
      # provides a more obvious interface for users for common cases.
      "supported_os",
      # URLs that link to information describing what this artifact collects.
      "urls",
      # List of strings that describe knowledge_base entries that this artifact
      # can supply.
      "provides",
      # List of alternate names.
      "aliases"
  ]

  # These labels represent the full set of labels that an Artifact can have.
  # This set is tested on creation to ensure our list of labels doesn't get out
  # of hand.
  # Labels are used to logicaly group Artifacts for ease of use.

  ARTIFACT_LABELS = {
      "Antivirus": "Antivirus related artifacts, e.g. quarantine files.",
      "Authentication": "Authentication artifacts.",
      "Browser": "Web Browser artifacts.",
      "Cloud": "Cloud applications artifacts.",
      "Cloud Storage": "Cloud storage artifacts.",
      "Configuration Files": "Configuration files artifacts.",
      "Containerd": "Containerd artifacts",
      "Docker": "Docker artifacts.",
      "Execution": "Contain execution events.",
      "ExternalAccount": ("Information about any user accounts e.g. username, "
                          "account ID, etc."),
      "External Media":
          ("Contain external media data or events e.g. USB drives."),
      "Hadoop": "Hadoop artifacts.",
      "IM": "Instant Messaging / Chat applications artifacts.",
      "iOS": "Artifacts related to iOS devices connected to the system.",
      "History Files": "History files artifacts e.g. .bash_history.",
      "KnowledgeBase": "Artifacts used in knowledge base generation.",
      "Kubernetes": "Kubernetes artifacts",
      "Logs": "Contain log files.",
      "Mail": "Mail client applications artifacts.",
      "Memory": "Artifacts retrieved from memory.",
      "Network": "Describe networking state.",
      "Plist": "Artifact that is a plist.",
      "Processes": "Describe running processes.",
      "Rekall": "Artifacts using the Rekall memory forensics framework.",
      "Software": "Installed software.",
      "SQLiteDB": "Artifact that is a SQLite database.",
      "System": "Core system artifacts.",
      "Users": "Information about users."
  }

  SUPPORTED_OS_LIST = ["Windows", "Linux", "Darwin"]

  # GRR does not support ESXi.
  IGNORE_OS_LIST = ("ESXi",)

  def ToJson(self):
    artifact_dict = self.ToPrimitiveDict()
    return json.Dump(artifact_dict)

  def ToDict(self):
    return self.ToPrimitiveDict()

  def ToPrimitiveDict(self):
    """Handle dict generation specifically for Artifacts."""
    artifact_dict = super().ToPrimitiveDict()

    # ArtifactName is not JSON-serializable, so convert name to string.
    artifact_dict["name"] = str(self.name)

    # Convert proto enum to simple strings so they get rendered in the GUI
    # properly
    for source in artifact_dict["sources"]:
      if "type" in source:
        source["type"] = str(source["type"])
      if "key_value_pairs" in source["attributes"]:
        outarray = []
        for indict in source["attributes"]["key_value_pairs"]:
          outarray.append(dict(indict))
        source["attributes"]["key_value_pairs"] = outarray

    # Repeated fields that have not been set should return as empty lists.
    for field in self.required_repeated_fields:
      if field not in artifact_dict:
        artifact_dict[field] = []
    return artifact_dict

  def ToYaml(self):
    artifact_dict = self.ToPrimitiveDict()

    # Remove redundant empty defaults.

    def ReduceDict(in_dict):
      return dict((k, v) for (k, v) in in_dict.items() if v)

    artifact_dict = ReduceDict(artifact_dict)
    sources_dict = artifact_dict.get("sources")
    if sources_dict:
      artifact_dict["sources"] = [ReduceDict(c) for c in sources_dict]

    # Do some clunky stuff to put the name and doc first in the YAML.
    # Unfortunately PYYaml makes doing this difficult in other ways.
    ordered_artifact_dict = collections.OrderedDict()
    ordered_artifact_dict["name"] = artifact_dict.pop("name")
    ordered_artifact_dict["doc"] = artifact_dict.pop("doc")
    ordered_artifact_dict.update(artifact_dict)

    return yaml.Dump(ordered_artifact_dict)


class ArtifactProcessorDescriptor(rdf_structs.RDFProtoStruct):
  """Describes artifact processor."""

  protobuf = artifact_pb2.ArtifactProcessorDescriptor

  @classmethod
  def FromParser(
      cls, parser_cls: Type[parsers.Parser]) -> "ArtifactProcessorDescriptor":
    """Creates a descriptor corresponding to the given parser.

    Args:
      parser_cls: A parser class for which the descriptor is to be created.

    Returns:
      A parser descriptor corresponding to the given parser.
    """
    # TODO(hanuszczak): Relying on a class docstring to get a description seems
    # like a lazy hack. Lets not do that.
    if parser_cls.__doc__:
      description = parser_cls.__doc__.split("\n")[0]
    else:
      description = ""

    return cls(
        name=parser_cls.__name__,
        description=description,
        output_types=map(compatibility.GetName, parser_cls.output_types))


class ArtifactDescriptor(rdf_structs.RDFProtoStruct):
  """Includes artifact, its JSON source, processors and additional info."""

  protobuf = artifact_pb2.ArtifactDescriptor
  rdf_deps = [
      Artifact,
      ArtifactProcessorDescriptor,
  ]


class ExpandedSource(rdf_structs.RDFProtoStruct):
  """An RDFValue representing a source and everything it depends on."""
  protobuf = artifact_pb2.ExpandedSource
  rdf_deps = [ArtifactSource, rdfvalue.ByteSize, "ExpandedSource"]


class ExpandedArtifact(rdf_structs.RDFProtoStruct):
  """An RDFValue representing an artifact with its extended sources."""
  protobuf = artifact_pb2.ExpandedArtifact
  rdf_deps = [
      ExpandedSource,
      ArtifactName,
  ]


class ArtifactCollectorFlowArgs(rdf_structs.RDFProtoStruct):
  """Arguments for the artifact collector flow."""

  protobuf = flows_pb2.ArtifactCollectorFlowArgs
  rdf_deps = [
      ArtifactName,
      rdfvalue.ByteSize,
      rdf_client.KnowledgeBase,
  ]

  def Validate(self):
    if not self.artifact_list:
      raise ValueError("No artifacts to collect.")


class ArtifactProgress(rdf_structs.RDFProtoStruct):
  """Collection progress of an Artifact."""
  protobuf = flows_pb2.ArtifactProgress
  rdf_deps = []


class ArtifactCollectorFlowProgress(rdf_structs.RDFProtoStruct):
  """Collection progress of ArtifactCollectorFlow."""
  protobuf = flows_pb2.ArtifactCollectorFlowProgress
  rdf_deps = [ArtifactProgress]


class ClientArtifactCollectorArgs(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an artifact bundle."""
  protobuf = artifact_pb2.ClientArtifactCollectorArgs
  rdf_deps = [
      ExpandedArtifact,
      rdf_client.KnowledgeBase,
      rdfvalue.ByteSize,
  ]


class ClientActionResult(rdf_structs.RDFProtoStruct):
  """An RDFValue representing one type of response for a client action."""
  protobuf = artifact_pb2.ClientActionResult

  def GetValueClass(self):
    try:
      return rdfvalue.RDFValue.GetPlugin(self.type)
    except KeyError:
      raise ValueError("No class found for type %s." % self.type)


class CollectedArtifact(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of a single collected artifact."""
  protobuf = artifact_pb2.CollectedArtifact
  rdf_deps = [
      ArtifactName,
      ClientActionResult,
  ]


class ClientArtifactCollectorResult(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of the result of the collection results."""
  protobuf = artifact_pb2.ClientArtifactCollectorResult
  rdf_deps = [
      CollectedArtifact,
      rdf_client.KnowledgeBase,
  ]
