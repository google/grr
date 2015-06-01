#!/usr/bin/env python
"""Library for processing of artifacts.

This file contains non-GRR specific pieces of artifact processing and is
intended to end up as an independent library.
"""

import itertools
import json
import os
import re
import yaml

import logging

from grr.lib import artifact_registry
from grr.lib import objectfilter
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs
from grr.proto import artifact_pb2
from grr.proto import flows_pb2


class Error(Exception):
  """Base exception."""


class ConditionError(Error):
  """An invalid artifact condition was specified."""


class ArtifactProcessingError(Error):
  """Unable to process artifact."""


class KnowledgeBaseInterpolationError(Error):
  """Unable to interpolate path using the Knowledge Base."""


class KnowledgeBaseUninitializedError(Error):
  """Attempt to process artifact without a valid Knowledge Base."""


class KnowledgeBaseAttributesMissingError(Error):
  """Knowledge Base is missing key attributes."""


class ArtifactCollectorFlowArgs(structs.RDFProtoStruct):
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

    if str(self.type) not in TYPE_MAP:
      raise artifact_registry.ArtifactDefinitionError(
          "Invalid type %s." % self.type)

    src_type = TYPE_MAP[str(self.type)]
    required_attributes = src_type.get("required_attributes", [])
    missing_attributes = set(
        required_attributes).difference(self.attributes.keys())
    if missing_attributes:
      raise artifact_registry.ArtifactDefinitionError(
          "Missing required attributes: %s." % missing_attributes)


class ArtifactName(rdfvalue.RDFString):
  type = "ArtifactName"


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
    for source in artifact_dict["sources"]:
      if "type" in source:
        source["type"] = str(source["type"])
      if "key_value_pairs" in source["attributes"]:
        outarray = []
        for indict in source["attributes"]["key_value_pairs"]:
          outarray.append(dict(indict.items()))
        source["attributes"]["key_value_pairs"] = outarray

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
    artifact_dict["sources"] = [ReduceDict(c) for c in
                                artifact_dict["sources"]]
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
    for source in self.sources:
      if source.type == ArtifactSource.SourceType.ARTIFACT:
        if source.attributes.GetItem("names"):
          deps.update(source.attributes.GetItem("names"))

    if depth > 10:
      raise RuntimeError("Max artifact recursion depth reached.")

    deps_set = set(deps)
    if recursive:
      for dep in deps:
        artifact_obj = artifact_registry.ArtifactRegistry.artifacts[dep]
        new_dep = artifact_obj.GetArtifactDependencies(True, depth=depth + 1)
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
    for source in self.sources:
      for arg, value in source.attributes.items():
        paths = []
        if arg in ["path", "query"]:
          paths.append(value)
        if arg == "key_value_pairs":
          # This is a REGISTRY_VALUE {key:blah, value:blah} dict.
          paths.extend([x["key"] for x in value])
        if arg in ["keys", "paths", "path_list", "content_regex_list"]:
          paths.extend(value)
        for path in paths:
          for match in INTERPOLATED_REGEX.finditer(path):
            deps.add(match.group()[2:-2])  # Strip off %%.
    deps.update(self.GetArtifactParserDependencies())
    return deps

  def ValidateSyntax(self):
    """Validate artifact syntax.

    This method can be used to validate individual artifacts as they are loaded,
    without needing all artifacts to be loaded first, as for Validate().

    Raises:
      ArtifactDefinitionError: If artifact is invalid.
    """
    cls_name = self.name
    if not self.doc:
      raise artifact_registry.ArtifactDefinitionError(
          "Artifact %s has missing doc" % cls_name)

    for supp_os in self.supported_os:
      if supp_os not in SUPPORTED_OS_LIST:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has invalid supported_os %s" % (cls_name, supp_os))

    for condition in self.conditions:
      try:
        of = objectfilter.Parser(condition).Parse()
        of.Compile(objectfilter.BaseFilterImplementation)
      except ConditionError as e:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has invalid condition %s. %s" % (
                cls_name, condition, e))

    for label in self.labels:
      if label not in ARTIFACT_LABELS:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has an invalid label %s. Please use one from "
            "ARTIFACT_LABELS." % (cls_name, label))

    # Anything listed in provides must be defined in the KnowledgeBase
    valid_provides = rdf_client.KnowledgeBase().GetKbFieldNames()
    for kb_var in self.provides:
      if kb_var not in valid_provides:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has broken provides: '%s' not in KB fields: %s" % (
                cls_name, kb_var, valid_provides))

    # Any %%blah%% path dependencies must be defined in the KnowledgeBase
    for dep in self.GetArtifactPathDependencies():
      if dep not in valid_provides:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has an invalid path dependency: '%s', not in KB "
            "fields: %s" % (cls_name, dep, valid_provides))

    for source in self.sources:
      try:
        source.Validate()
      except Error as e:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has bad source. %s" % (cls_name, e))

  def Validate(self):
    """Attempt to validate the artifact has been well defined.

    This is used to enforce Artifact rules. Since it checks all dependencies are
    present, this method can only be called once all artifacts have been loaded
    into the registry. Use ValidateSyntax to check syntax for each artifact on
    import.

    Raises:
      ArtifactDefinitionError: If artifact is invalid.
    """
    cls_name = self.name
    self.ValidateSyntax()

    # Check all artifact dependencies exist.
    for dependency in self.GetArtifactDependencies():
      if dependency not in artifact_registry.ArtifactRegistry.artifacts:
        raise artifact_registry.ArtifactDefinitionError(
            "Artifact %s has an invalid dependency %s . Could not find artifact"
            " definition." % (cls_name, dependency))


# These labels represent the full set of labels that an Artifact can have.
# This set is tested on creation to ensure our list of labels doesn't get out
# of hand.
# Labels are used to logicaly group Artifacts for ease of use.

ARTIFACT_LABELS = {
    "Antivirus": "Antivirus related artifacts, e.g. quarantine files.",
    "Authentication": "Authentication artifacts.",
    "Browser": "Web Browser artifacts.",
    "Configuration Files": "Configuration files artifacts.",
    "Execution": "Contain execution events.",
    "External Media": "Contain external media data or events e.g. USB drives.",
    "KnowledgeBase": "Artifacts used in knowledgebase generation.",
    "Logs": "Contain log files.",
    "Memory": "Artifacts retrieved from Memory.",
    "Network": "Describe networking state.",
    "Processes": "Describe running processes.",
    "Software": "Installed software.",
    "System": "Core system artifacts.",
    "Users": "Information about users.",
    "Rekall": "Artifacts using the Rekall memory forensics framework.",
}

OUTPUT_UNDEFINED = "Undefined"


TYPE_MAP = {"GRR_CLIENT_ACTION": {"required_attributes": ["client_action"],
                                  "output_type": OUTPUT_UNDEFINED},
            "FILE": {"required_attributes": ["paths"],
                     "output_type": "StatEntry"},
            "GREP": {"required_attributes": ["paths", "content_regex_list"],
                     "output_type": "BufferReference"},
            "LIST_FILES": {"required_attributes": ["paths"],
                           "output_type": "StatEntry"},
            "PATH": {"required_attributes": ["paths"],
                     "output_type": "StatEntry"},
            "REGISTRY_KEY": {"required_attributes": ["keys"],
                             "output_type": "StatEntry"},
            "REGISTRY_VALUE": {"required_attributes": ["key_value_pairs"],
                               "output_type": "RDFString"},
            "WMI": {"required_attributes": ["query"],
                    "output_type": "Dict"},
            "COMMAND": {"required_attributes": ["cmd", "args"],
                        "output_type": "ExecuteResponse"},
            "REKALL_PLUGIN": {"required_attributes": ["plugin"],
                              "output_type": "RekallResponse"},
            "ARTIFACT": {"required_attributes": ["names"],
                         "output_type": OUTPUT_UNDEFINED},
            "ARTIFACT_FILES": {"required_attributes": ["artifact_list"],
                               "output_type": "StatEntry"}}


SUPPORTED_OS_LIST = ["Windows", "Linux", "Darwin"]
INTERPOLATED_REGEX = re.compile(r"%%([^%]+?)%%")

# A regex indicating if there are shell globs in this path.
GLOB_MAGIC_CHECK = re.compile("[*?[]")


def InterpolateKbAttributes(pattern, knowledge_base):
  """Interpolate all knowledgebase attributes in pattern.

  Args:
    pattern: A string with potential interpolation markers. For example:
      "/home/%%users.username%%/Downloads/"
    knowledge_base: The knowledge_base to interpolate parameters from.

  Yields:
    All unique strings generated by expanding the pattern.
  """
  components = []
  offset = 0

  for match in INTERPOLATED_REGEX.finditer(pattern):
    components.append([pattern[offset:match.start()]])
    # Expand the attribute into the set of possibilities:
    alternatives = []

    try:
      if "." in match.group(1):  # e.g. %%users.username%%
        base_name, attr_name = match.group(1).split(".", 1)
        kb_value = knowledge_base.Get(base_name.lower())
        if not kb_value:
          raise AttributeError(base_name.lower())
        elif isinstance(kb_value, basestring):
          alternatives.append(kb_value)
        else:
          # Iterate over repeated fields (e.g. users)
          sub_attrs = []
          for value in kb_value:
            sub_attr = value.Get(attr_name)
            # Ignore empty results
            if sub_attr:
              sub_attrs.append(unicode(sub_attr))

          # If we got some results we use them. On Windows it is common for
          # users.temp to be defined for some users, but not all users.
          if sub_attrs:
            alternatives.extend(sub_attrs)
          else:
            # If there were no results we raise
            raise AttributeError(match.group(1).lower())
      else:
        kb_value = knowledge_base.Get(match.group(1).lower())
        if not kb_value:
          raise AttributeError(match.group(1).lower())
        elif isinstance(kb_value, basestring):
          alternatives.append(kb_value)
    except AttributeError as e:
      raise KnowledgeBaseInterpolationError("Failed to interpolate %s with the "
                                            "knowledgebase. %s" % (pattern, e))

    components.append(set(alternatives))
    offset = match.end()

  components.append([pattern[offset:]])

  # Now calculate the cartesian products of all these sets to form all strings.
  for vector in itertools.product(*components):
    yield "".join(vector)


def ExpandWindowsEnvironmentVariables(data_string, knowledge_base):
  """Take a string and expand any windows environment variables.

  Args:
    data_string: A string, e.g. "%SystemRoot%\\LogFiles"
    knowledge_base: A knowledgebase object.

  Returns:
    A string with available environment variables expanded.
  """
  win_environ_regex = re.compile(r"%([^%]+?)%")
  components = []
  offset = 0
  for match in win_environ_regex.finditer(data_string):
    components.append(data_string[offset:match.start()])

    # KB environment variables are prefixed with environ_.
    kb_value = getattr(knowledge_base, "environ_%s" % match.group(1).lower(),
                       None)
    if isinstance(kb_value, basestring) and kb_value:
      components.append(kb_value)
    else:
      components.append("%%%s%%" % match.group(1))
    offset = match.end()
  components.append(data_string[offset:])  # Append the final chunk.
  return "".join(components)


def CheckCondition(condition, check_object):
  """Check if a condition matches an object.

  Args:
    condition: A string condition e.g. "os == 'Windows'"
    check_object: Object to validate, e.g. an rdf_client.KnowledgeBase()

  Returns:
    True or False depending on whether the condition matches.

  Raises:
    ConditionError: If condition is bad.
  """
  try:
    of = objectfilter.Parser(condition).Parse()
    compiled_filter = of.Compile(objectfilter.BaseFilterImplementation)
    return compiled_filter.Matches(check_object)
  except objectfilter.Error as e:
    raise ConditionError(e)


def ExpandWindowsUserEnvironmentVariables(data_string, knowledge_base, sid=None,
                                          username=None):
  """Take a string and expand windows user environment variables based.

  Args:
    data_string: A string, e.g. "%TEMP%\\LogFiles"
    knowledge_base: A knowledgebase object.
    sid: A Windows SID for a user to expand for.
    username: A Windows user name to expand for.

  Returns:
    A string with available environment variables expanded.
  """
  win_environ_regex = re.compile(r"%([^%]+?)%")
  components = []
  offset = 0
  for match in win_environ_regex.finditer(data_string):
    components.append(data_string[offset:match.start()])
    kb_user = knowledge_base.GetUser(sid=sid, username=username)
    kb_value = None
    if kb_user:
      kb_value = getattr(kb_user, match.group(1).lower(), None)
    if isinstance(kb_value, basestring) and kb_value:
      components.append(kb_value)
    else:
      components.append("%%%s%%" % match.group(1))
    offset = match.end()

  components.append(data_string[offset:])  # Append the final chunk.
  return "".join(components)


def ArtifactsFromYaml(yaml_content):
  """Get a list of Artifacts from json."""
  try:
    raw_list = list(yaml.safe_load_all(yaml_content))
  except (ValueError, yaml.YAMLError) as e:
    raise artifact_registry.ArtifactDefinitionError(
        "Invalid YAML for artifact: %s" % e)

  # Try to do the right thing with json/yaml formatted as a list.
  if (isinstance(raw_list, list) and len(raw_list) == 1 and
      isinstance(raw_list[0], list)):
    raw_list = raw_list[0]

  # Convert json into artifact and validate.
  valid_artifacts = []
  for artifact_dict in raw_list:
    # In this case we are feeding parameters directly from potentially
    # untrusted yaml/json to our RDFValue class. However, safe_load ensures
    # these are all primitive types as long as there is no other deserialization
    # involved, and we are passing these into protobuf primitive types.
    try:
      artifact_value = Artifact(**artifact_dict)
      valid_artifacts.append(artifact_value)
    except (TypeError, AttributeError) as e:
      raise artifact_registry.ArtifactDefinitionError(
          "Invalid artifact definition for %s: %s" %
          (artifact_dict.get("name"), e))

  return valid_artifacts


def LoadArtifactsFromFiles(file_paths, overwrite_if_exists=True):
  """Load artifacts from file paths as json or yaml."""
  loaded_files = []
  loaded_artifacts = []
  for file_path in file_paths:
    try:
      with open(file_path, mode="rb") as fh:
        logging.debug("Loading artifacts from %s", file_path)
        for artifact_val in ArtifactsFromYaml(fh.read(1000000)):
          artifact_registry.ArtifactRegistry.RegisterArtifact(
              artifact_val, source="file:%s" % file_path,
              overwrite_if_exists=overwrite_if_exists)
          loaded_artifacts.append(artifact_val)
          logging.debug("Loaded artifact %s from %s", artifact_val.name,
                        file_path)

      loaded_files.append(file_path)
    except (IOError, OSError) as e:
      logging.error("Failed to open artifact file %s. %s", file_path, e)

  # Once all artifacts are loaded we can validate, as validation of dependencies
  # requires the group are all loaded before doing the validation.
  for artifact_value in loaded_artifacts:
    artifact_value.Validate()

  return loaded_files


def LoadArtifactsFromDirs(directories):
  """Load artifacts from all .json or .yaml files in a list of directories."""
  files_to_load = []
  for directory in directories:
    try:
      for file_name in os.listdir(directory):
        if (file_name.endswith(".json") or file_name.endswith(".yaml") and
            not file_name.startswith("test")):
          files_to_load.append(os.path.join(directory, file_name))
    except (IOError, OSError):
      logging.warn("Error loading artifacts from %s", directory)

  if not files_to_load:
    return []
  return LoadArtifactsFromFiles(files_to_load)


def DumpArtifactsToYaml(artifact_list, sort_by_os=True):
  """Dump a list of artifacts into a yaml string."""
  artifact_list = set(artifact_list)  # Save list in case it is a generator.
  if sort_by_os:
    # Sort so its easier to split these if necessary.
    yaml_list = []
    done_set = set()
    for os_name in SUPPORTED_OS_LIST:
      done_set = set(a for a in artifact_list if a.supported_os == [os_name])
      # Separate into knowledge_base and non-knowledge base for easier sorting.
      done_set = sorted(done_set, key=lambda x: x.name)
      yaml_list.extend(x.ToYaml() for x in done_set if x.provides)
      yaml_list.extend(x.ToYaml() for x in done_set if not x.provides)
      artifact_list = artifact_list.difference(done_set)
    yaml_list.extend(x.ToYaml() for x in artifact_list)  # The rest.
  else:
    yaml_list = [x.ToYaml() for x in artifact_list]

  return "---\n\n".join(yaml_list)
