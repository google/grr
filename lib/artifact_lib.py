#!/usr/bin/env python
"""Library for processing of artifacts.

This file contains non-GRR specific pieces of artifact processing and is
intended to end up as an independent library.
"""

import itertools
import os
import re
import yaml

import logging

from grr.lib import objectfilter
from grr.lib import rdfvalue


class Error(Exception):
  """Base exception."""


class ArtifactDefinitionError(Error):
  """Artifact is not well defined."""


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


TYPE_MAP = {"GRR_CLIENT_ACTION": {"required_args": ["client_action"],
                                  "output_type": OUTPUT_UNDEFINED},
            "FILE": {"required_args": ["path_list"],
                     "output_type": "StatEntry"},
            "GREP": {"required_args": ["path_list", "content_regex_list"],
                     "output_type": "BufferReference"},
            "LIST_FILES": {"required_args": ["path_list"],
                           "output_type": "StatEntry"},
            "REGISTRY_KEY": {"required_args": ["path_list"],
                             "output_type": "StatEntry"},
            "REGISTRY_VALUE": {"required_args": ["path_list"],
                               "output_type": "RDFString"},
            "WMI": {"required_args": ["query"],
                    "output_type": "Dict"},
            "COMMAND": {"required_args": ["cmd", "args"],
                        "output_type": "ExecuteResponse"},
            "REKALL_PLUGIN": {"required_args": ["plugin"],
                              "output_type": "RekallResponse"},
            "ARTIFACT": {"required_args": ["artifact_list"],
                         "output_type": OUTPUT_UNDEFINED},
            "ARTIFACT_FILES": {"required_args": ["artifact_list"],
                               "output_type": "StatEntry"},
           }


SUPPORTED_OS_LIST = ["Windows", "Linux", "Darwin"]
INTERPOLATED_REGEX = re.compile(r"%%([^%]+?)%%")

# A regex indicating if there are shell globs in this path.
GLOB_MAGIC_CHECK = re.compile("[*?[]")


class ArtifactRegistry(object):
  """A global registry of artifacts."""

  artifacts = {}

  @classmethod
  def RegisterArtifact(cls, artifact_rdfvalue, source="datastore",
                       overwrite_if_exists=False):
    if not overwrite_if_exists and artifact_rdfvalue.name in cls.artifacts:
      raise ArtifactDefinitionError("Artifact named %s already exists and "
                                    "overwrite_if_exists is set to False." %
                                    artifact_rdfvalue.name)

    # Preserve where the artifact was loaded from to help debugging.
    artifact_rdfvalue.loaded_from = source
    cls.artifacts[artifact_rdfvalue.name] = artifact_rdfvalue

  @classmethod
  def ClearRegistry(cls):
    cls.artifacts = {}

  @classmethod
  def GetArtifacts(cls, os_name=None, name_list=None,
                   collector_type=None, exclude_dependents=False,
                   provides=None):
    """Retrieve artifact classes with optional filtering.

    All filters must match for the artifact to be returned.

    Args:
      os_name: string to match against supported_os
      name_list: list of strings to match against artifact names
      collector_type: rdfvalue.Collector.CollectorType to match against
                      collector_type
      exclude_dependents: if true only artifacts with no dependencies will be
                          returned
      provides: return the artifacts that provide these dependencies
    Returns:
      set of artifacts matching filter criteria
    """
    results = set()
    for artifact in ArtifactRegistry.artifacts.values():

      # artifact.supported_os = [] matches all OSes
      if os_name and artifact.supported_os and (os_name not in
                                                artifact.supported_os):
        continue
      if name_list and artifact.name not in name_list:
        continue
      if collector_type:
        collector_types = [c.collector_type for c in artifact.collectors]
        if collector_type not in collector_types:
          continue
      if exclude_dependents and artifact.GetArtifactPathDependencies():
        continue

      # This needs to remain the last test, if it matches the result is added
      if provides:
        for provide_string in artifact.provides:
          if provide_string in provides:
            results.add(artifact)
            continue
        continue

      results.add(artifact)
    return results

  @classmethod
  def GetArtifactNames(cls, *args, **kwargs):
    return set([a.name for a in cls.GetArtifacts(*args, **kwargs)])

  @classmethod
  def SearchDependencies(cls, os_name, artifact_name_list,
                         existing_artifact_deps=None,
                         existing_expansion_deps=None):
    """Return a set of artifact names needed to fulfill dependencies.

    Search the path dependency tree for all artifacts that can fulfill
    dependencies of artifact_name_list.  If multiple artifacts provide a
    dependency, they are all included.

    Args:
      os_name: operating system string
      artifact_name_list: list of artifact names to find dependencies for.
      existing_artifact_deps: existing dependencies to add to, for recursion,
        e.g. set(["WindowsRegistryProfiles", "WinPathEnvironmentVariable"])
      existing_expansion_deps: existing expansion dependencies to add to, for
        recursion, e.g. set(["users.userprofile", "users.homedir"])
    Returns:
      (artifact_names, expansion_names): a tuple of sets, one with artifact
          names, the other expansion names
    """
    artifact_deps = existing_artifact_deps or set()
    expansion_deps = existing_expansion_deps or set()

    artifact_objs = cls.GetArtifacts(os_name=os_name,
                                     name_list=artifact_name_list)
    artifact_deps = artifact_deps.union([a.name for a in artifact_objs])

    for artifact in artifact_objs:
      expansions = artifact.GetArtifactPathDependencies()
      if expansions:
        expansion_deps = expansion_deps.union(set(expansions))
        # Get the names of the artifacts that provide those expansions
        new_artifact_names = cls.GetArtifactNames(os_name=os_name,
                                                  provides=expansions)
        missing_artifacts = new_artifact_names - artifact_deps

        if missing_artifacts:
          # Add those artifacts and any child dependencies
          new_artifacts, new_expansions = cls.SearchDependencies(
              os_name, new_artifact_names, existing_artifact_deps=artifact_deps,
              existing_expansion_deps=expansion_deps)
          artifact_deps = artifact_deps.union(new_artifacts)
          expansion_deps = expansion_deps.union(new_expansions)

    return artifact_deps, expansion_deps


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
      if "." in match.group(1):     # e.g. %%users.username%%
        base_name, attr_name = match.group(1).split(".", 1)
        kb_value = knowledge_base.Get(base_name.lower())
        if not kb_value:
          raise AttributeError(base_name.lower())
        elif isinstance(kb_value, basestring):
          alternatives.append(kb_value)
        else:
          for value in kb_value:
            sub_attr = value.Get(attr_name)
            alternatives.append(unicode(sub_attr))
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
  components.append(data_string[offset:])    # Append the final chunk.
  return "".join(components)


def CheckCondition(condition, check_object):
  """Check if a condition matches an object.

  Args:
    condition: A string condition e.g. "os == 'Windows'"
    check_object: Object to validate, e.g. an rdfvalue.KnowledgeBase()

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

  components.append(data_string[offset:])    # Append the final chunk.
  return "".join(components)


def ArtifactsFromYaml(yaml_content):
  """Get a list of Artifacts from json."""
  try:
    raw_list = list(yaml.safe_load_all(yaml_content))
  except ValueError as e:
    raise ArtifactDefinitionError("Invalid json for artifact: %s" % e)

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
      artifact_value = rdfvalue.Artifact(**artifact_dict)
      valid_artifacts.append(artifact_value)
    except (TypeError, AttributeError) as e:
      raise ArtifactDefinitionError("Invalid artifact definition for %s: %s" %
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
          ArtifactRegistry.RegisterArtifact(
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


def LoadArtifactsFromDir(dir_path):
  """Load artifacts from all .json or .yaml files in a directory."""
  try:
    files_to_load = []
    for file_name in os.listdir(dir_path):
      if (file_name.endswith(".json") or file_name.endswith(".yaml") and
          not file_name.startswith("test")):
        files_to_load.append(os.path.join(dir_path, file_name))
    return LoadArtifactsFromFiles(files_to_load)
  except (IOError, OSError):
    logging.warn("Artifact directory not found: %s", dir_path)
    return []


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
