#!/usr/bin/env python
"""Central registry for artifacts."""

import json
import logging
import os
import yaml

from grr import config
from grr.lib import objectfilter
from grr.lib import parser
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import structs
from grr_response_proto import artifact_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import artifact_utils
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import sequential_collection


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

    super(ArtifactDefinitionError, self).__init__(message)


class ArtifactSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about syntax problems.
    cause: An optional exception that triggered the syntax error.
  """

  def __init__(self, artifact, details, cause=None):
    super(ArtifactSyntaxError, self).__init__(artifact.name, details, cause)


class ArtifactDependencyError(ArtifactDefinitionError):
  """An exception class representing dependency errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about dependency problems.
    cause: An optional exception that triggered the dependency error.
  """

  def __init__(self, artifact, details, cause=None):
    super(ArtifactDependencyError, self).__init__(artifact.name, details, cause)


class ArtifactSourceSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact sources.

  Args:
    source: An artifact source object for which the error was encountered.
    details: A string with more details about syntax problems.
  """

  def __init__(self, source, details):
    super(ArtifactSourceSyntaxError, self).__init__(source.type, details)


class ArtifactNotRegisteredError(Exception):
  """Artifact is not present in the registry."""


class ArtifactRegistrySources(object):
  """Represents sources of the artifact registry used for getting artifacts."""

  def __init__(self):
    self._dirs = set()
    self._files = set()
    self._datastores = set()

  def AddDir(self, dirpath):
    """Adds a directory path as a source.

    Args:
      dirpath: a string representing a path to the directory.

    Returns:
      True if the directory is not an already existing source.
    """
    if dirpath not in self._dirs:
      self._dirs.add(dirpath)
      return True
    return False

  def AddFile(self, filepath):
    """Adds a file path as a source.

    Args:
      filepath: a string representing a path to the file.

    Returns:
      True if the file is not an already existing source.
    """
    if filepath not in self._files:
      self._files.add(filepath)
      return True
    return False

  def AddDatastore(self, urn):
    """Adds a datastore URN as a source.

    Args:
      urn: an RDF URN value of the datastore.

    Returns:
      True if the datastore is not an already existing source.
    """
    if urn not in self._datastores:
      self._datastores.add(urn)
      return True
    return False

  def Clear(self):
    self._dirs.clear()
    self._files.clear()
    self._datastores.clear()

  def GetDirs(self):
    """Returns an iterator over defined source directory paths."""
    return iter(self._dirs)

  def GetFiles(self):
    """Returns an iterator over defined source file paths."""
    return iter(self._files)

  def GetDatastores(self):
    """Returns an iterator over defined datastore URNs."""
    return iter(self._datastores)

  def GetAllFiles(self):
    """Yields all defined source file paths.

    This includes file paths defined directly and those defined implicitly by
    defining a directory.
    """
    for filepath in self._files:
      yield filepath

    for dirpath in self._dirs:
      for filepath in ArtifactRegistrySources._GetDirYamlFiles(dirpath):
        if filepath in self._files:
          continue
        yield filepath

  @staticmethod
  def _GetDirYamlFiles(dirpath):
    try:
      for filename in os.listdir(dirpath):
        if filename.endswith(".json") or filename.endswith(".yaml"):
          yield os.path.join(dirpath, filename)
    except (IOError, OSError) as error:
      logging.warn("problem with accessing artifact directory '%s': %s",
                   dirpath, error)


class ArtifactRegistry(object):
  """A global registry of artifacts."""

  def __init__(self):
    self._artifacts = {}
    self._sources = ArtifactRegistrySources()
    self._dirty = False

  def _LoadArtifactsFromDatastore(self):
    """Load artifacts from the data store."""
    loaded_artifacts = []

    # TODO(hanuszczak): Why do we have to remove anything? If some artifact
    # tries to shadow system artifact shouldn't we just ignore them and perhaps
    # issue some warning instead? The datastore being loaded should be read-only
    # during upload.

    # A collection of artifacts that shadow system artifacts and need
    # to be deleted from the data store.
    to_delete = []

    for artifact_coll_urn in self._sources.GetDatastores():
      artifact_coll = ArtifactCollection(artifact_coll_urn)
      for artifact_value in artifact_coll:
        try:
          self.RegisterArtifact(
              artifact_value,
              source="datastore:%s" % artifact_coll_urn,
              overwrite_if_exists=True)
          loaded_artifacts.append(artifact_value)
          logging.debug("Loaded artifact %s from %s", artifact_value.name,
                        artifact_coll_urn)
        except ArtifactDefinitionError as e:
          # TODO(hanuszczak): String matching on exception message is rarely
          # a good idea. Instead this should be refectored to some exception
          # class and then handled separately.
          if "system artifact" in e.message:
            to_delete.append(artifact_value.name)
          else:
            raise

    if to_delete:
      DeleteArtifactsFromDatastore(to_delete, reload_artifacts=False)
      self._dirty = True

      # TODO(hanuszczak): This is connected to the previous TODO comment. Why
      # do we throw exception at this point? Why do we delete something and then
      # abort the whole upload procedure by throwing an exception?
      detail = "system artifacts were shadowed and had to be deleted"
      raise ArtifactDefinitionError(to_delete, detail)

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
    raw_list = list(yaml.safe_load_all(yaml_content))

    # TODO(hanuszczak): I am very sceptical about that "doing the right thing"
    # below. What are the real use cases?

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
        name = artifact_dict.get("name")
        raise ArtifactDefinitionError(name, "invalid definition", cause=e)

    return valid_artifacts

  def _LoadArtifactsFromFiles(self, file_paths, overwrite_if_exists=True):
    """Load artifacts from file paths as json or yaml."""
    loaded_files = []
    loaded_artifacts = []
    for file_path in file_paths:
      try:
        with open(file_path, mode="rb") as fh:
          logging.debug("Loading artifacts from %s", file_path)
          for artifact_val in self.ArtifactsFromYaml(fh.read()):
            self.RegisterArtifact(
                artifact_val,
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
    self._sources.Clear()
    self._dirty = True

  def AddFileSource(self, filename):
    self._dirty |= self._sources.AddFile(filename)

  def AddDirSource(self, dirname):
    self._dirty |= self._sources.AddDir(dirname)

  def AddDirSources(self, dirnames):
    for dirname in dirnames:
      self.AddDirSource(dirname)

  def AddDatastoreSource(self, urn):
    self._dirty |= self._sources.AddDatastore(urn)

  def AddDatastoreSources(self, urns):
    for urn in urns:
      self.AddDatastoreSource(urn)

  def AddDefaultSources(self):
    for path in config.CONFIG["Artifacts.artifact_dirs"]:
      self.AddDirSource(path)

    self.AddDatastoreSources([aff4.ROOT_URN.Add("artifact_store")])

  def RegisterArtifact(self,
                       artifact_rdfvalue,
                       source="datastore",
                       overwrite_if_exists=False,
                       overwrite_system_artifacts=False):
    """Registers a new artifact."""
    artifact_name = artifact_rdfvalue.name
    if artifact_name in self._artifacts:
      if not overwrite_if_exists:
        details = "artifact already exists and `overwrite_if_exists` is unset"
        raise ArtifactDefinitionError(artifact_name, details)
      elif not overwrite_system_artifacts:
        artifact_obj = self._artifacts[artifact_name]
        if not artifact_obj.loaded_from.startswith("datastore:"):
          # This artifact was not uploaded to the datastore but came from a
          # file, refuse to overwrite.
          details = "system artifact cannot be overwritten"
          raise ArtifactDefinitionError(artifact_name, details)

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
    self._LoadArtifactsFromFiles(self._sources.GetAllFiles())
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
    self._LoadArtifactsFromDatastore()

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
    for artifact in self._artifacts.values():

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
        e.g. set(["WindowsRegistryProfiles", "WindowsEnvironmentVariablePath"])
      existing_expansion_deps: existing expansion dependencies to add to, for
        recursion, e.g. set(["users.userprofile", "users.homedir"])
    Returns:
      (artifact_names, expansion_names): a tuple of sets, one with artifact
          names, the other expansion names
    """
    artifact_deps = existing_artifact_deps or set()
    expansion_deps = existing_expansion_deps or set()

    artifact_objs = self.GetArtifacts(
        os_name=os_name, name_list=artifact_name_list)
    artifact_deps = artifact_deps.union([a.name for a in artifact_objs])

    for artifact in artifact_objs:
      expansions = artifact.GetArtifactPathDependencies()
      if expansions:
        expansion_deps = expansion_deps.union(set(expansions))
        # Get the names of the artifacts that provide those expansions
        new_artifact_names = self.GetArtifactNames(
            os_name=os_name, provides=expansions)
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
  rdf_deps = [
      protodict.Dict,
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

  def __init__(self, initializer=None, age=None, **kwarg):
    # Support initializing from a mapping
    if isinstance(initializer, dict):
      super(ArtifactSource, self).__init__(age=age, **initializer)
    else:
      super(ArtifactSource, self).__init__(
          initializer=initializer, age=age, **kwarg)

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
    if path and not isinstance(path, basestring):
      raise ArtifactSourceSyntaxError(self, "`path` is not a string")

  def _ValidateType(self):
    # TODO(hanuszczak): Since `type` is an enum, is this validation really
    # necessary?
    if self.type not in self.TYPE_MAP:
      raise ArtifactSourceSyntaxError(self, "invalid type '%s'" % self.type)

  def _ValidateRequiredAttributes(self):
    required = set(self.TYPE_MAP[self.type].get("required_attributes", []))
    provided = self.attributes.keys()
    missing = required.difference(provided)

    if missing:
      quoted = ("'%s'" % attribute for attribute in missing)
      detail = "missing required attributes: %s" % ", ".join(quoted)
      raise ArtifactSourceSyntaxError(self, detail)


class ArtifactName(rdfvalue.RDFString):
  pass


class Artifact(structs.RDFProtoStruct):
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
      "provides"
  ]

  # These labels represent the full set of labels that an Artifact can have.
  # This set is tested on creation to ensure our list of labels doesn't get out
  # of hand.
  # Labels are used to logicaly group Artifacts for ease of use.

  ARTIFACT_LABELS = {
      "Antivirus":
          "Antivirus related artifacts, e.g. quarantine files.",
      "Authentication":
          "Authentication artifacts.",
      "Browser":
          "Web Browser artifacts.",
      "Cloud":
          "Cloud applications artifacts.",
      "Cloud Storage":
          "Cloud Storage artifacts.",
      "Configuration Files":
          "Configuration files artifacts.",
      "Execution":
          "Contain execution events.",
      "ExternalAccount": ("Information about any users\' account, e.g."
                          " username, account ID, etc."),
      "External Media":
          "Contain external media data / events e.g. USB drives.",
      "History Files":
          "History files artifacts e.g. .bash_history.",
      "IM":
          "Instant Messaging / Chat applications artifacts.",
      "iOS":
          "Artifacts related to iOS devices connected to the system.",
      "KnowledgeBase":
          "Artifacts used in knowledgebase generation.",
      "Logs":
          "Contain log files.",
      "Mail":
          "Mail client applications artifacts.",
      "Memory":
          "Artifacts retrieved from Memory.",
      "Network":
          "Describe networking state.",
      "Processes":
          "Describe running processes.",
      "Software":
          "Installed software.",
      "System":
          "Core system artifacts.",
      "Users":
          "Information about users.",
      "Rekall":
          "Artifacts using the Rekall memory forensics framework.",
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
    processors = parser.Parser.GetClassesByArtifact(self.name)
    for p in processors:
      deps.update(p.knowledgebase_dependencies)
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
    """Validates artifact syntax.

    This method can be used to validate individual artifacts as they are loaded,
    without needing all artifacts to be loaded first, as for Validate().

    Raises:
      ArtifactSyntaxError: If artifact syntax is invalid.
    """
    if not self.doc:
      raise ArtifactSyntaxError(self, "missing doc")

    for supp_os in self.supported_os:
      valid_os = self.SUPPORTED_OS_LIST
      if supp_os not in valid_os:
        detail = "invalid `supported_os` ('%s' not in %s)" % (supp_os, valid_os)
        raise ArtifactSyntaxError(self, detail)

    for condition in self.conditions:
      # FIXME(hanuszczak): It does not look like the code below can throw
      # `ConditionException`. Do we really need it then?
      try:
        of = objectfilter.Parser(condition).Parse()
        of.Compile(objectfilter.BaseFilterImplementation)
      except ConditionError as e:
        detail = "invalid condition '%s'" % condition
        raise ArtifactSyntaxError(self, detail, e)

    for label in self.labels:
      if label not in self.ARTIFACT_LABELS:
        raise ArtifactSyntaxError(self, "invalid label '%s'" % label)

    # Anything listed in provides must be defined in the KnowledgeBase
    valid_provides = rdf_client.KnowledgeBase().GetKbFieldNames()
    for kb_var in self.provides:
      if kb_var not in valid_provides:
        detail = "broken `provides` ('%s' not in %s)" % (kb_var, valid_provides)
        raise ArtifactSyntaxError(self, detail)

    # Any %%blah%% path dependencies must be defined in the KnowledgeBase
    for dep in self.GetArtifactPathDependencies():
      if dep not in valid_provides:
        detail = "broken path dependencies ('%s' not in %s)" % (dep,
                                                                valid_provides)
        raise ArtifactSyntaxError(self, detail)

    for source in self.sources:
      try:
        source.Validate()
      except ArtifactSourceSyntaxError as e:
        raise ArtifactSyntaxError(self, "bad source", e)

  def ValidateDependencies(self):
    """Validates artifact dependencies.

    This method checks whether all dependencies of the artifact are present
    and contain no errors.

    This method can be called only after all other artifacts have been loaded.

    Raises:
      ArtifactDependencyError: If a dependency is missing or contains errors.
    """
    for dependency in self.GetArtifactDependencies():
      try:
        dependency_obj = REGISTRY.GetArtifact(dependency)
      except ArtifactNotRegisteredError as e:
        raise ArtifactDependencyError(self, "missing dependency", cause=e)

      message = dependency_obj.error_message
      if message:
        raise ArtifactDependencyError(self, "dependency error", cause=message)

  def Validate(self):
    """Attempts to validate the artifact has been well defined.

    This checks both syntax and dependencies of the artifact. Because of that,
    this method can be called only after all other artifacts have been loaded.

    Raises:
      ArtifactDefinitionError: If artifact is invalid.
    """
    self.ValidateSyntax()
    self.ValidateDependencies()


class ArtifactProcessorDescriptor(structs.RDFProtoStruct):
  """Describes artifact processor."""

  protobuf = artifact_pb2.ArtifactProcessorDescriptor


class ArtifactDescriptor(structs.RDFProtoStruct):
  """Includes artifact, its JSON source, processors and additional info."""

  protobuf = artifact_pb2.ArtifactDescriptor
  rdf_deps = [
      Artifact,
      ArtifactProcessorDescriptor,
  ]


class ArtifactCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = Artifact


def DeleteArtifactsFromDatastore(artifact_names, reload_artifacts=True):
  """Deletes a list of artifacts from the data store."""
  artifacts = sorted(
      REGISTRY.GetArtifacts(reload_datastore_artifacts=reload_artifacts))

  to_delete = set(artifact_names)
  deps = set()
  for artifact_obj in artifacts:
    if artifact_obj.name in to_delete:
      continue

    if artifact_obj.GetArtifactDependencies() & to_delete:
      deps.add(str(artifact_obj.name))

  if deps:
    raise ValueError(
        "Artifact(s) %s depend(s) on one of the artifacts to delete." %
        (",".join(deps)))

  store = ArtifactCollection(rdfvalue.RDFURN("aff4:/artifact_store"))
  all_artifacts = list(store)

  filtered_artifacts, found_artifact_names = set(), set()
  for artifact_value in all_artifacts:
    if artifact_value.name in to_delete:
      found_artifact_names.add(artifact_value.name)
    else:
      filtered_artifacts.add(artifact_value)

  if len(found_artifact_names) != len(to_delete):
    not_found = to_delete - found_artifact_names
    raise ValueError(
        "Artifact(s) to delete (%s) not found." % ",".join(not_found))

  # TODO(user): this is ugly and error- and race-condition- prone.
  # We need to store artifacts not in a *Collection, which is an
  # append-only object, but in some different way that allows easy
  # deletion. Possible option - just store each artifact in a separate object
  # in the same folder.
  store.Delete()

  with data_store.DB.GetMutationPool() as pool:
    for artifact_value in filtered_artifacts:
      store.Add(artifact_value, mutation_pool=pool)

  for artifact_value in to_delete:
    REGISTRY.UnregisterArtifact(artifact_value)
