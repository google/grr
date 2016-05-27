#!/usr/bin/env python
"""Central registry for artifacts."""

import json
import os
import re
import yaml

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import artifact_utils
from grr.lib import objectfilter
from grr.lib import parsers
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs
from grr.proto import artifact_pb2


class Error(Exception):
  """Base exception."""


class ConditionError(Error):
  """An invalid artifact condition was specified."""


class ArtifactDefinitionError(Error):
  """Artifact is not well defined."""


class ArtifactNotRegisteredError(Error):
  """Artifact is not present in the registry."""


class ArtifactRegistry(object):
  """A global registry of artifacts."""

  _artifacts = {}
  _sources = {"dirs": [], "files": [], "datastores": []}
  _dirty = False

  def _LoadArtifactsFromDatastore(self,
                                  source_urns=None,
                                  token=None,
                                  overwrite_if_exists=True):
    """Load artifacts from the data store."""
    if token is None:
      token = access_control.ACLToken(username="GRRArtifactRegistry",
                                      reason="Managing Artifacts.")
    loaded_artifacts = []

    for artifact_coll_urn in source_urns or []:
      with aff4.FACTORY.Create(artifact_coll_urn,
                               aff4_type=collects.RDFValueCollection,
                               token=token,
                               mode="rw") as artifact_coll:
        for artifact_value in artifact_coll:
          self.RegisterArtifact(artifact_value,
                                source="datastore:%s" % artifact_coll_urn,
                                overwrite_if_exists=overwrite_if_exists)
          loaded_artifacts.append(artifact_value)
          logging.debug("Loaded artifact %s from %s", artifact_value.name,
                        artifact_coll_urn)

    # Once all artifacts are loaded we can validate.
    revalidate = True
    while revalidate:
      revalidate = False
      for artifact_obj in loaded_artifacts[:]:
        try:
          artifact_obj.Validate()
        except ArtifactDefinitionError as e:
          logging.error("Artifact %s did not validate: %s", artifact_obj.name,
                        e)
          artifact_obj.error_message = utils.SmartStr(e)
          loaded_artifacts.remove(artifact_obj)
          revalidate = True

  def ArtifactsFromYaml(self, yaml_content):
    """Get a list of Artifacts from yaml."""
    try:
      raw_list = list(yaml.safe_load_all(yaml_content))
    except (ValueError, yaml.YAMLError) as e:
      raise ArtifactDefinitionError("Invalid YAML for artifact: %s" % e)

    # Try to do the right thing with json/yaml formatted as a list.
    if (isinstance(raw_list, list) and len(raw_list) == 1 and
        isinstance(raw_list[0], list)):
      raw_list = raw_list[0]

    # Convert json into artifact and validate.
    valid_artifacts = []
    for artifact_dict in raw_list:
      # In this case we are feeding parameters directly from potentially
      # untrusted yaml/json to our RDFValue class. However, safe_load ensures
      # these are all primitive types as long as there is no other
      # deserialization involved, and we are passing these into protobuf
      # primitive types.
      try:
        artifact_value = Artifact(**artifact_dict)
        valid_artifacts.append(artifact_value)
      except (TypeError, AttributeError, type_info.TypeValueError) as e:
        raise ArtifactDefinitionError("Invalid artifact definition for %s: %s" %
                                      (artifact_dict.get("name"), e))

    return valid_artifacts

  def _LoadArtifactsFromFiles(self, file_paths, overwrite_if_exists=True):
    """Load artifacts from file paths as json or yaml."""
    loaded_files = []
    loaded_artifacts = []
    for file_path in file_paths:
      try:
        with open(file_path, mode="rb") as fh:
          logging.debug("Loading artifacts from %s", file_path)
          for artifact_val in self.ArtifactsFromYaml(fh.read(1000000)):
            self.RegisterArtifact(artifact_val,
                                  source="file:%s" % file_path,
                                  overwrite_if_exists=overwrite_if_exists)
            loaded_artifacts.append(artifact_val)
            logging.debug("Loaded artifact %s from %s", artifact_val.name,
                          file_path)

        loaded_files.append(file_path)
      except (IOError, OSError) as e:
        logging.error("Failed to open artifact file %s. %s", file_path, e)
      except ArtifactDefinitionError as e:
        logging.error("Invalid artifact found in file %s with error: %s",
                      file_path, e)
        raise

    # Once all artifacts are loaded we can validate.
    for artifact_value in loaded_artifacts:
      artifact_value.Validate()

  def ClearSources(self):
    self._sources = {"dirs": [], "files": [], "datastores": []}
    self._dirty = True

  def AddFileSource(self, filename):
    self._sources["files"].append(filename)
    self._dirty = True

  def AddDirSource(self, dirname):
    self.AddDirSources([dirname])

  def AddDirSources(self, dirnames):
    self._sources["dirs"] += dirnames
    self._dirty = True

  def AddDatastoreSources(self, datastores):
    self._sources["datastores"] += datastores
    self._dirty = True

  def RegisterArtifact(self,
                       artifact_rdfvalue,
                       source="datastore",
                       overwrite_if_exists=False):
    """Registers a new artifact."""
    if not overwrite_if_exists and artifact_rdfvalue.name in self._artifacts:
      raise ArtifactDefinitionError("Artifact named %s already exists and "
                                    "overwrite_if_exists is set to False." %
                                    artifact_rdfvalue.name)

    # Preserve where the artifact was loaded from to help debugging.
    artifact_rdfvalue.loaded_from = source
    # Clear any stale errors.
    artifact_rdfvalue.error_message = None
    self._artifacts[artifact_rdfvalue.name] = artifact_rdfvalue

  def UnregisterArtifact(self, artifact_name):
    try:
      del self._artifacts[artifact_name]
    except KeyError:
      raise ValueError("Artifact %s unknown." % artifact_name)

  def ClearRegistry(self):
    self._artifacts = {}
    self._dirty = True

  def _ReloadArtifacts(self):
    """Load artifacts from all sources."""
    self._artifacts = {}
    files_to_load = []
    for dir_path in self._sources.get("dirs", []):
      try:
        for file_name in os.listdir(dir_path):
          if (file_name.endswith(".json") or file_name.endswith(".yaml") and
              not file_name.startswith("test")):
            files_to_load.append(os.path.join(dir_path, file_name))
      except (IOError, OSError):
        logging.warn("Artifact directory not found: %s", dir_path)
    files_to_load += self._sources.get("files", [])
    logging.debug("Loading artifacts from: %s", files_to_load)
    self._LoadArtifactsFromFiles(files_to_load)

    self.ReloadDatastoreArtifacts()

  def _UnregisterDatastoreArtifacts(self):
    """Remove artifacts that came from the datastore."""
    to_remove = []
    for name, artifact in self._artifacts.iteritems():
      if artifact.loaded_from.startswith("datastore"):
        to_remove.append(name)
    for key in to_remove:
      self._artifacts.pop(key)

  def ReloadDatastoreArtifacts(self):
    # Make sure artifacts deleted by the UI don't reappear.
    self._UnregisterDatastoreArtifacts()
    self._LoadArtifactsFromDatastore(self._sources["datastores"])

  def _CheckDirty(self, reload_datastore_artifacts=False):
    if self._dirty:
      self._dirty = False
      self._ReloadArtifacts()
    else:
      if reload_datastore_artifacts:
        self.ReloadDatastoreArtifacts()

  def GetArtifacts(self,
                   os_name=None,
                   name_list=None,
                   source_type=None,
                   exclude_dependents=False,
                   provides=None,
                   reload_datastore_artifacts=False):
    """Retrieve artifact classes with optional filtering.

    All filters must match for the artifact to be returned.

    Args:
      os_name: string to match against supported_os
      name_list: list of strings to match against artifact names
      source_type: rdf_artifacts.ArtifactSource.SourceType to match against
                      source_type
      exclude_dependents: if true only artifacts with no dependencies will be
                          returned
      provides: return the artifacts that provide these dependencies
      reload_datastore_artifacts: If true, the data store sources are queried
                                  for new artifacts.
    Returns:
      set of artifacts matching filter criteria
    """
    self._CheckDirty(reload_datastore_artifacts=reload_datastore_artifacts)
    results = set()
    for artifact in self._artifacts.itervalues():

      # artifact.supported_os = [] matches all OSes
      if os_name and artifact.supported_os and (
          os_name not in artifact.supported_os):
        continue
      if name_list and artifact.name not in name_list:
        continue
      if source_type:
        source_types = [c.type for c in artifact.sources]
        if source_type not in source_types:
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

  def GetRegisteredArtifactNames(self):
    return [utils.SmartStr(x) for x in self._artifacts]

  def GetArtifact(self, name):
    """Get artifact by name.

    Args:
      name: artifact name string.

    Returns:
      artifact object.
    Raises:
      ArtifactNotRegisteredError: if artifact doesn't exist in the registy.
    """
    self._CheckDirty()
    result = self._artifacts.get(name)
    if not result:
      raise ArtifactNotRegisteredError(
          "Artifact %s missing from registry. You may need "
          "to sync the artifact repo by running make in the artifact "
          "directory." % name)
    return result

  def GetArtifactNames(self, *args, **kwargs):
    return set([a.name for a in self.GetArtifacts(*args, **kwargs)])

  def SearchDependencies(self,
                         os_name,
                         artifact_name_list,
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

    artifact_objs = self.GetArtifacts(os_name=os_name,
                                      name_list=artifact_name_list)
    artifact_deps = artifact_deps.union([a.name for a in artifact_objs])

    for artifact in artifact_objs:
      expansions = artifact.GetArtifactPathDependencies()
      if expansions:
        expansion_deps = expansion_deps.union(set(expansions))
        # Get the names of the artifacts that provide those expansions
        new_artifact_names = self.GetArtifactNames(os_name=os_name,
                                                   provides=expansions)
        missing_artifacts = new_artifact_names - artifact_deps

        if missing_artifacts:
          # Add those artifacts and any child dependencies
          new_artifacts, new_expansions = self.SearchDependencies(
              os_name,
              new_artifact_names,
              existing_artifact_deps=artifact_deps,
              existing_expansion_deps=expansion_deps)
          artifact_deps = artifact_deps.union(new_artifacts)
          expansion_deps = expansion_deps.union(new_expansions)

    return artifact_deps, expansion_deps

  def DumpArtifactsToYaml(self, sort_by_os=True):
    """Dump a list of artifacts into a yaml string."""
    artifact_list = self.GetArtifacts()
    if sort_by_os:
      # Sort so its easier to split these if necessary.
      yaml_list = []
      done_set = set()
      for os_name in Artifact.SUPPORTED_OS_LIST:
        done_set = set(a for a in artifact_list if a.supported_os == [os_name])
        # Separate into knowledge_base and non-kb for easier sorting.
        done_set = sorted(done_set, key=lambda x: x.name)
        yaml_list.extend(x.ToYaml() for x in done_set if x.provides)
        yaml_list.extend(x.ToYaml() for x in done_set if not x.provides)
        artifact_list = artifact_list.difference(done_set)
      yaml_list.extend(x.ToYaml() for x in artifact_list)  # The rest.
    else:
      yaml_list = [x.ToYaml() for x in artifact_list]

    return "---\n\n".join(yaml_list)


REGISTRY = ArtifactRegistry()


class ArtifactSource(structs.RDFProtoStruct):
  """An ArtifactSource."""
  protobuf = artifact_pb2.ArtifactSource

  OUTPUT_UNDEFINED = "Undefined"

  TYPE_MAP = {
      "GRR_CLIENT_ACTION": {"required_attributes": ["client_action"],
                            "output_type": OUTPUT_UNDEFINED},
      "FILE": {"required_attributes": ["paths"],
               "output_type": "StatEntry"},
      "GREP": {"required_attributes": ["paths", "content_regex_list"],
               "output_type": "BufferReference"},
      "DIRECTORY": {"required_attributes": ["paths"],
                    "output_type": "StatEntry"},
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
      # ARTIFACT is the legacy name for ARTIFACT_GROUP
      # per: https://github.com/ForensicArtifacts/artifacts/pull/143
      # TODO(user): remove legacy support after migration.
      "ARTIFACT": {"required_attributes": ["names"],
                   "output_type": OUTPUT_UNDEFINED},
      "ARTIFACT_FILES": {"required_attributes": ["artifact_list"],
                         "output_type": "StatEntry"},
      "ARTIFACT_GROUP": {"required_attributes": ["names"],
                         "output_type": OUTPUT_UNDEFINED}
  }

  def __init__(self, initializer=None, age=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super(ArtifactSource, self).__init__(age=age, **initializer)
    else:
      super(ArtifactSource, self).__init__(initializer=initializer,
                                           age=age,
                                           **kwarg)

  def Validate(self):
    """Check the source is well constructed."""

    if self.type == "COMMAND":
      # specifying command execution artifacts with multiple arguments as a
      # single string is a common mistake. For example the definition
      # cmd: "ls"
      # args: [-l -a]
      # will give you args as ["-l -a"] but that will not work (try ls "-l -a").
      args = self.attributes.GetItem("args")
      if args and len(args) == 1 and " " in args[0]:
        raise ArtifactDefinitionError(
            "Cannot specify a single argument containing a space: %s." % args)

    # Catch common mistake of path vs paths.
    if self.attributes.GetItem("paths"):
      if not isinstance(self.attributes.GetItem("paths"), list):
        raise ArtifactDefinitionError("Arg 'paths' that is not a list.")

    if self.attributes.GetItem("path"):
      if not isinstance(self.attributes.GetItem("path"), basestring):
        raise ArtifactDefinitionError("Arg 'path' is not a string.")

    # Check all returned types.
    if self.returned_types:
      for rdf_type in self.returned_types:
        if rdf_type not in rdfvalue.RDFValue.classes:
          raise ArtifactDefinitionError("Invalid return type %s" % rdf_type)

    src_type = self.TYPE_MAP.get(str(self.type))
    if src_type is None:
      raise ArtifactDefinitionError("Invalid type %s." % self.type)

    required_attributes = src_type.get("required_attributes", [])
    missing_attributes = set(required_attributes).difference(
        self.attributes.keys())
    if missing_attributes:
      raise ArtifactDefinitionError("Missing required attributes: %s." %
                                    missing_attributes)


class ArtifactName(rdfvalue.RDFString):
  pass


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
      "provides"
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
      "Cloud Storage": "Cloud Storage artifacts.",
      "Configuration Files": "Configuration files artifacts.",
      "Execution": "Contain execution events.",
      "ExternalAccount": ("Information about any users\' account, e.g."
                          " username, account ID, etc."),
      "External Media": "Contain external media data / events e.g. USB drives.",
      "History Files": "History files artifacts e.g. .bash_history.",
      "IM": "Instant Messaging / Chat applications artifacts.",
      "iOS": "Artifacts related to iOS devices connected to the system.",
      "KnowledgeBase": "Artifacts used in knowledgebase generation.",
      "Logs": "Contain log files.",
      "Mail": "Mail client applications artifacts.",
      "Memory": "Artifacts retrieved from Memory.",
      "Network": "Describe networking state.",
      "Processes": "Describe running processes.",
      "Software": "Installed software.",
      "System": "Core system artifacts.",
      "Users": "Information about users.",
      "Rekall": "Artifacts using the Rekall memory forensics framework.",
  }

  SUPPORTED_OS_LIST = ["Windows", "Linux", "Darwin"]

  def ToJson(self):
    artifact_dict = self.ToPrimitiveDict()
    return json.dumps(artifact_dict)

  def ToDict(self):
    return self.ToPrimitiveDict()

  def ToPrimitiveDict(self):
    """Handle dict generation specifically for Artifacts."""
    artifact_dict = super(Artifact, self).ToPrimitiveDict()

    # ArtifactName is not JSON-serializable, so convert name to string.
    artifact_dict["name"] = utils.SmartStr(self.name)

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

    artifact_json = json.dumps(artifact_dict,
                               indent=2,
                               sort_keys=True,
                               separators=(",", ": "))

    # Now tidy up the json for better display. Unfortunately json gives us very
    # little control over output format, so we manually tidy it up given that
    # we have a defined format.

    def CompressBraces(name, in_str):
      return re.sub(r"%s\": \[\n\s+(.*)\n\s+" % name, "%s\": [ \\g<1> " % name,
                    in_str)

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
    sources_dict = artifact_dict.get("sources")
    if sources_dict:
      artifact_dict["sources"] = [ReduceDict(c) for c in sources_dict]
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
      # ARTIFACT is the legacy name for ARTIFACT_GROUP
      # per: https://github.com/ForensicArtifacts/artifacts/pull/143
      # TODO(user): remove legacy support after migration.
      if source.type in (ArtifactSource.SourceType.ARTIFACT,
                         ArtifactSource.SourceType.ARTIFACT_GROUP):
        if source.attributes.GetItem("names"):
          deps.update(source.attributes.GetItem("names"))

    if depth > 10:
      raise RuntimeError("Max artifact recursion depth reached.")

    deps_set = set(deps)
    if recursive:
      for dep in deps:
        artifact_obj = REGISTRY.GetArtifact(dep)
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
          for match in artifact_utils.INTERPOLATED_REGEX.finditer(path):
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
      raise ArtifactDefinitionError("Artifact %s has missing doc" % cls_name)

    for supp_os in self.supported_os:
      if supp_os not in self.SUPPORTED_OS_LIST:
        raise ArtifactDefinitionError(
            "Artifact %s has invalid supported_os %s" % (cls_name, supp_os))

    for condition in self.conditions:
      try:
        of = objectfilter.Parser(condition).Parse()
        of.Compile(objectfilter.BaseFilterImplementation)
      except ConditionError as e:
        raise ArtifactDefinitionError(
            "Artifact %s has invalid condition %s. %s" % (cls_name, condition,
                                                          e))

    for label in self.labels:
      if label not in self.ARTIFACT_LABELS:
        raise ArtifactDefinitionError(
            "Artifact %s has an invalid label %s. Please use one from "
            "ARTIFACT_LABELS." % (cls_name, label))

    # Anything listed in provides must be defined in the KnowledgeBase
    valid_provides = rdf_client.KnowledgeBase().GetKbFieldNames()
    for kb_var in self.provides:
      if kb_var not in valid_provides:
        raise ArtifactDefinitionError(
            "Artifact %s has broken provides: '%s' not in KB fields: %s" %
            (cls_name, kb_var, valid_provides))

    # Any %%blah%% path dependencies must be defined in the KnowledgeBase
    for dep in self.GetArtifactPathDependencies():
      if dep not in valid_provides:
        raise ArtifactDefinitionError(
            "Artifact %s has an invalid path dependency: '%s', not in KB "
            "fields: %s" % (cls_name, dep, valid_provides))

    for source in self.sources:
      try:
        source.Validate()
      except Error as e:
        raise ArtifactDefinitionError("Artifact %s has bad source. %s" %
                                      (cls_name, e))

  def Validate(self):
    """Attempt to validate the artifact has been well defined.

    This is used to enforce Artifact rules. Since it checks all dependencies are
    present, this method can only be called once all artifacts have been loaded
    into the registry. Use ValidateSyntax to check syntax for each artifact on
    import.

    Raises:
      ArtifactDefinitionError: If artifact is invalid.
    """
    self.ValidateSyntax()

    try:
      # Check all artifact dependencies exist.
      for dependency in self.GetArtifactDependencies():
        dependency_obj = REGISTRY.GetArtifact(dependency)
        if dependency_obj.error_message:
          raise ArtifactDefinitionError("Dependency %s has an error!" %
                                        dependency)
    except ArtifactNotRegisteredError as e:
      raise ArtifactDefinitionError(e)


class ArtifactProcessorDescriptor(structs.RDFProtoStruct):
  """Describes artifact processor."""

  protobuf = artifact_pb2.ArtifactProcessorDescriptor


class ArtifactDescriptor(structs.RDFProtoStruct):
  """Includes artifact, its JSON source, processors and additional info."""

  protobuf = artifact_pb2.ArtifactDescriptor
