#!/usr/bin/env python
"""Implementation of artifact types."""

import json
import re
import yaml

from grr.lib import artifact_lib
from grr.lib import objectfilter
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr.proto import artifact_pb2
from grr.proto import flows_pb2


class ArtifactCollectorFlowArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.ArtifactCollectorFlowArgs

  def Validate(self):
    if not self.artifact_list:
      raise ValueError("No artifacts to collect.")


class Artifact(structs.RDFProtoStruct):
  """An RDFValue representation of an artifact."""
  protobuf = artifact_pb2.Artifact

  required_repeated_fields = [
      # List of object filter rules that define whether Artifact collection
      # should run. These operate as an AND operator, all conditions
      # must pass for it to run. OR operators should be implemented as their own
      # conditions.
      "conditions",
      # A list of labels that help users find artifacts. Must be in the list
      # artifact_lib.ARTIFACT_LABELS.
      "labels",
      # Which OS are supported by the Artifact e.g. Linux, Windows, Darwin
      # Note that this can be implemented by conditions as well, but this
      # provides a more obvious interface for users for common cases.
      "supported_os",
      # URLs that link to information describing what this artifact collects.
      "urls",
      # List of strings that describe knowledge_base entries that this artifact
      # can supply.
      "provides"]

  def ToJson(self):
    artifact_dict = self.ToPrimitiveDict()
    return json.dumps(artifact_dict)

  def ToDict(self):
    return self.ToPrimitiveDict()

  def ToPrimitiveDict(self):
    """Handle dict generation specifically for Artifacts."""
    artifact_dict = super(Artifact, self).ToPrimitiveDict()

    # Convert proto enum to simple strings so they get rendered in the GUI
    # properly
    for collector in artifact_dict["collectors"]:
      if "collector_type" in collector:
        collector["collector_type"] = str(collector["collector_type"])

    # Repeated fields that have not been set should return as empty lists.
    for field in self.required_repeated_fields:
      if field not in artifact_dict:
        artifact_dict[field] = []
    return artifact_dict

  def ToExtendedDict(self):
    artifact_dict = self.ToPrimitiveDict()
    artifact_dict["dependencies"] = list(self.GetArtifactPathDependencies())
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

  def ToYaml(self):
    artifact_dict = self.ToPrimitiveDict()
    # Remove redundant empty defaults.
    def ReduceDict(in_dict):
      return dict((k, v) for (k, v) in in_dict.items() if v)
    artifact_dict = ReduceDict(artifact_dict)
    artifact_dict["collectors"] = [ReduceDict(c) for c in
                                   artifact_dict["collectors"]]
    # Do some clunky stuff to put the name and doc first in the YAML.
    # Unfortunatley PYYaml makes doing this difficult in other ways.
    name = artifact_dict.pop("name")
    doc = artifact_dict.pop("doc")
    doc_str = yaml.safe_dump({"doc": doc}, allow_unicode=True, width=80)[1:-2]
    yaml_str = yaml.safe_dump(artifact_dict, allow_unicode=True, width=80)
    return "name: %s\n%s\n%s" % (name, doc_str, yaml_str)

  def GetArtifactDependencies(self, recursive=False, depth=1):
    """Return a set of artifact dependencies.

    Args:
      recursive: If True recurse into dependencies to find their dependencies.
      depth: Used for limiting recursion depth.

    Returns:
      A set of strings containing the dependent artifact names.

    Raises:
      RuntimeError: If maximum recursion depth reached.
    """
    deps = set()
    for collector in self.collectors:
      if collector.collector_type == rdfvalue.Collector.CollectorType.ARTIFACT:
        if collector.args.GetItem("artifact_list"):
          deps.update(collector.args.GetItem("artifact_list"))

    if depth > 10:
      raise RuntimeError("Max artifact recursion depth reached.")

    deps_set = set(deps)
    if recursive:
      for dep in deps:
        artifact_obj = artifact_lib.ArtifactRegistry.artifacts[dep]
        new_dep = artifact_obj.GetArtifactDependencies(True, depth=depth+1)
        if new_dep:
          deps_set.update(new_dep)

    return deps_set

  def GetArtifactParserDependencies(self):
    """Return the set of knowledgebase path dependencies required by the parser.

    Returns:
      A set of strings for the required kb objects e.g.
      ["users.appdata", "systemroot"]
    """
    deps = set()
    processors = parsers.Parser.GetClassesByArtifact(self.name)
    for parser in processors:
      deps.update(parser.knowledgebase_dependencies)
    return deps

  def GetArtifactPathDependencies(self):
    """Return a set of knowledgebase path dependencies.

    Returns:
      A set of strings for the required kb objects e.g.
      ["users.appdata", "systemroot"]
    """
    deps = set()
    for collector in self.collectors:
      for arg, value in collector.args.items():
        paths = []
        if arg in ["path", "query"]:
          paths.append(value)
        if arg in ["paths", "path_list", "content_regex_list"]:
          paths.extend(value)
        for path in paths:
          for match in artifact_lib.INTERPOLATED_REGEX.finditer(path):
            deps.add(match.group()[2:-2])   # Strip off %%.
    deps.update(self.GetArtifactParserDependencies())
    return deps

  def Validate(self):
    """Attempt to validate the artifact has been well defined.

    This is used to enforce Artifact rules.

    Raises:
      ArtifactDefinitionError: If artifact is invalid.

    """
    cls_name = self.name
    if not self.doc:
      raise artifact_lib.ArtifactDefinitionError(
          "Artifact %s has missing doc" % cls_name)

    for supp_os in self.supported_os:
      if supp_os not in artifact_lib.SUPPORTED_OS_LIST:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has invalid supported_os %s" % (cls_name, supp_os))

    for condition in self.conditions:
      try:
        of = objectfilter.Parser(condition).Parse()
        of.Compile(objectfilter.BaseFilterImplementation)
      except artifact_lib.ConditionError as e:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has invalid condition %s. %s" % (
                cls_name, condition, e))

    for label in self.labels:
      if label not in artifact_lib.ARTIFACT_LABELS:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has an invalid label %s. Please use one from "
            "ARTIFACT_LABELS." % (cls_name, label))

    # Check all path dependencies exist in the knowledge base.
    valid_fields = rdfvalue.KnowledgeBase().GetKbFieldNames()
    for dependency in self.GetArtifactPathDependencies():
      if dependency not in valid_fields:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has an invalid path dependency %s. Artifacts must use "
            "defined knowledge attributes." % (cls_name, dependency))

    # Check all artifact dependencies exist.
    for dependency in self.GetArtifactDependencies():
      if dependency not in artifact_lib.ArtifactRegistry.artifacts:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has an invalid dependency %s . Could not find artifact"
            " definition." % (cls_name, dependency))

    for collector in self.collectors:
      try:
        collector.Validate()
      except artifact_lib.Error as e:
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has bad collector. %s" % (cls_name, e))

    for kb_var in self.provides:
      if len(kb_var) < 3:   # Someone probably interpreted string as list.
        raise artifact_lib.ArtifactDefinitionError(
            "Artifact %s has broken provides. %s" % (cls_name, self.provides))


class Collector(structs.RDFProtoStruct):
  """An Artifact Collector."""
  protobuf = artifact_pb2.Collector

  def __init__(self, initializer=None, age=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super(Collector, self).__init__(age=age, **initializer)
    else:
      super(Collector, self).__init__(initializer=initializer, age=age, **kwarg)

  def Validate(self):
    """Check the collector is well constructed."""
    # Catch common mistake of path vs paths.
    if self.args.GetItem("path_list"):
      if not isinstance(self.args.GetItem("path_list"), list):
        raise artifact_lib.ArtifactDefinitionError(
            "Arg 'path_list' that is not a list.")
    if self.args.GetItem("path"):
      if not isinstance(self.args.GetItem("path"), basestring):
        raise artifact_lib.ArtifactDefinitionError(
            "Arg 'path' is not a string.")

    # Check all returned types.
    if self.returned_types:
      for rdf_type in self.returned_types:
        if rdf_type not in rdfvalue.RDFValue.classes:
          raise artifact_lib.ArtifactDefinitionError(
              "Invalid return type %s" % rdf_type)

    if str(self.collector_type) not in artifact_lib.TYPE_MAP:
      raise artifact_lib.ArtifactDefinitionError(
          "Invalid collector_type %s." % self.collector_type)

    collector_type = artifact_lib.TYPE_MAP[str(self.collector_type)]
    required_args = collector_type.get("required_args", [])
    missing_args = set(required_args).difference(self.args.keys())
    if missing_args:
      raise artifact_lib.ArtifactDefinitionError(
          "Missing required args: %s." % missing_args)


class ArtifactName(rdfvalue.RDFString):
  type = "ArtifactName"

