#!/usr/bin/env python
"""Central registry for artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import threading


from future.utils import iteritems
from future.utils import itervalues
import yaml

from grr_response_core import config
from grr_response_core.lib import artifact_utils
from grr_response_core.lib import objectfilter
from grr_response_core.lib import parser
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import sequential_collection


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
    # Field required by the utils.Synchronized annotation.
    self.lock = threading.RLock()

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

      if data_store.RelationalDBReadEnabled(category="artifacts"):
        artifact_list = data_store.REL_DB.ReadAllArtifacts()
      else:
        artifact_list = list(artifact_coll)

      for artifact_value in artifact_list:
        try:
          self.RegisterArtifact(
              artifact_value,
              source="datastore:%s" % artifact_coll_urn,
              overwrite_if_exists=True)
          loaded_artifacts.append(artifact_value)
          logging.debug("Loaded artifact %s from %s", artifact_value.name,
                        artifact_coll_urn)
        except rdf_artifacts.ArtifactDefinitionError as e:
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
      raise rdf_artifacts.ArtifactDefinitionError(to_delete, detail)

    # Once all artifacts are loaded we can validate.
    revalidate = True
    while revalidate:
      revalidate = False
      for artifact_obj in loaded_artifacts[:]:
        try:
          Validate(artifact_obj)
        except rdf_artifacts.ArtifactDefinitionError as e:
          logging.error("Artifact %s did not validate: %s", artifact_obj.name,
                        e)
          artifact_obj.error_message = utils.SmartStr(e)
          loaded_artifacts.remove(artifact_obj)
          revalidate = True

  @utils.Synchronized
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
        artifact_value = rdf_artifacts.Artifact(**artifact_dict)
        valid_artifacts.append(artifact_value)
      except (TypeError, AttributeError, type_info.TypeValueError) as e:
        name = artifact_dict.get("name")
        raise rdf_artifacts.ArtifactDefinitionError(
            name, "invalid definition", cause=e)

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
      except rdf_artifacts.ArtifactDefinitionError as e:
        logging.error("Invalid artifact found in file %s with error: %s",
                      file_path, e)
        raise

    # Once all artifacts are loaded we can validate.
    for artifact_value in loaded_artifacts:
      Validate(artifact_value)

  @utils.Synchronized
  def ClearSources(self):
    self._sources.Clear()
    self._dirty = True

  @utils.Synchronized
  def AddFileSource(self, filename):
    self._dirty |= self._sources.AddFile(filename)

  @utils.Synchronized
  def AddDirSource(self, dirname):
    self._dirty |= self._sources.AddDir(dirname)

  @utils.Synchronized
  def AddDirSources(self, dirnames):
    for dirname in dirnames:
      self.AddDirSource(dirname)

  @utils.Synchronized
  def AddDatastoreSource(self, urn):
    self._dirty |= self._sources.AddDatastore(urn)

  @utils.Synchronized
  def AddDatastoreSources(self, urns):
    for urn in urns:
      self.AddDatastoreSource(urn)

  @utils.Synchronized
  def AddDefaultSources(self):
    for path in config.CONFIG["Artifacts.artifact_dirs"]:
      self.AddDirSource(path)

    self.AddDatastoreSources([aff4.ROOT_URN.Add("artifact_store")])

  @utils.Synchronized
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
        raise rdf_artifacts.ArtifactDefinitionError(artifact_name, details)
      elif not overwrite_system_artifacts:
        artifact_obj = self._artifacts[artifact_name]
        if not artifact_obj.loaded_from.startswith("datastore:"):
          # This artifact was not uploaded to the datastore but came from a
          # file, refuse to overwrite.
          details = "system artifact cannot be overwritten"
          raise rdf_artifacts.ArtifactDefinitionError(artifact_name, details)

    # Preserve where the artifact was loaded from to help debugging.
    artifact_rdfvalue.loaded_from = source
    # Clear any stale errors.
    artifact_rdfvalue.error_message = None
    self._artifacts[artifact_rdfvalue.name] = artifact_rdfvalue

  @utils.Synchronized
  def UnregisterArtifact(self, artifact_name):
    try:
      del self._artifacts[artifact_name]
    except KeyError:
      raise ValueError("Artifact %s unknown." % artifact_name)

  @utils.Synchronized
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
    for name, artifact in iteritems(self._artifacts):
      if artifact.loaded_from.startswith("datastore"):
        to_remove.append(name)
    for key in to_remove:
      self._artifacts.pop(key)

  @utils.Synchronized
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

  @utils.Synchronized
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
    for artifact in itervalues(self._artifacts):

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
      if exclude_dependents and GetArtifactPathDependencies(artifact):
        continue

      if not provides:
        results.add(artifact)
      else:
        # This needs to remain the last test, if it matches the result is added
        for provide_string in artifact.provides:
          if provide_string in provides:
            results.add(artifact)
            break

    return results

  @utils.Synchronized
  def GetRegisteredArtifactNames(self):
    return [utils.SmartStr(x) for x in self._artifacts]

  @utils.Synchronized
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
      raise rdf_artifacts.ArtifactNotRegisteredError(
          "Artifact %s missing from registry. You may need to sync the "
          "artifact repo by running make in the artifact directory." % name)
    return result

  @utils.Synchronized
  def GetArtifactNames(self, *args, **kwargs):
    return set([a.name for a in self.GetArtifacts(*args, **kwargs)])

  @utils.Synchronized
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
      expansions = GetArtifactPathDependencies(artifact)
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

  @utils.Synchronized
  def DumpArtifactsToYaml(self, sort_by_os=True):
    """Dump a list of artifacts into a yaml string."""
    artifact_list = self.GetArtifacts()
    if sort_by_os:
      # Sort so its easier to split these if necessary.
      yaml_list = []
      done_set = set()
      for os_name in rdf_artifacts.Artifact.SUPPORTED_OS_LIST:
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


class ArtifactCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_artifacts.Artifact


def DeleteArtifactsFromDatastore(artifact_names, reload_artifacts=True):
  """Deletes a list of artifacts from the data store."""
  artifacts_list = sorted(
      REGISTRY.GetArtifacts(reload_datastore_artifacts=reload_artifacts))

  to_delete = set(artifact_names)
  deps = set()
  for artifact_obj in artifacts_list:
    if artifact_obj.name in to_delete:
      continue

    if GetArtifactDependencies(artifact_obj) & to_delete:
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

  if data_store.RelationalDBWriteEnabled():
    for artifact_name in to_delete:
      data_store.REL_DB.DeleteArtifact(unicode(artifact_name))

  for artifact_value in to_delete:
    REGISTRY.UnregisterArtifact(artifact_value)


def ValidateSyntax(rdf_artifact):
  """Validates artifact syntax.

  This method can be used to validate individual artifacts as they are loaded,
  without needing all artifacts to be loaded first, as for Validate().

  Args:
    rdf_artifact: RDF object artifact.

  Raises:
    ArtifactSyntaxError: If artifact syntax is invalid.
  """
  if not rdf_artifact.doc:
    raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, "missing doc")

  for supp_os in rdf_artifact.supported_os:
    valid_os = rdf_artifact.SUPPORTED_OS_LIST
    if supp_os not in valid_os:
      detail = "invalid `supported_os` ('%s' not in %s)" % (supp_os, valid_os)
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, detail)

  for condition in rdf_artifact.conditions:
    # FIXME(hanuszczak): It does not look like the code below can throw
    # `ConditionException`. Do we really need it then?
    try:
      of = objectfilter.Parser(condition).Parse()
      of.Compile(objectfilter.BaseFilterImplementation)
    except rdf_artifacts.ConditionError as e:
      detail = "invalid condition '%s'" % condition
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, detail, e)

  for label in rdf_artifact.labels:
    if label not in rdf_artifact.ARTIFACT_LABELS:
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact,
                                              "invalid label '%s'" % label)

  # Anything listed in provides must be defined in the KnowledgeBase
  valid_provides = rdf_client.KnowledgeBase().GetKbFieldNames()
  for kb_var in rdf_artifact.provides:
    if kb_var not in valid_provides:
      detail = "broken `provides` ('%s' not in %s)" % (kb_var, valid_provides)
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, detail)

  # Any %%blah%% path dependencies must be defined in the KnowledgeBase
  for dep in GetArtifactPathDependencies(rdf_artifact):
    if dep not in valid_provides:
      detail = "broken path dependencies ('%s' not in %s)" % (dep,
                                                              valid_provides)
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, detail)

  for source in rdf_artifact.sources:
    try:
      source.Validate()
    except rdf_artifacts.ArtifactSourceSyntaxError as e:
      raise rdf_artifacts.ArtifactSyntaxError(rdf_artifact, "bad source", e)


def ValidateDependencies(rdf_artifact):
  """Validates artifact dependencies.

  This method checks whether all dependencies of the artifact are present
  and contain no errors.

  This method can be called only after all other artifacts have been loaded.

  Args:
    rdf_artifact: RDF object artifact.

  Raises:
    ArtifactDependencyError: If a dependency is missing or contains errors.
  """
  for dependency in GetArtifactDependencies(rdf_artifact):
    try:
      dependency_obj = REGISTRY.GetArtifact(dependency)
    except rdf_artifacts.ArtifactNotRegisteredError as e:
      raise rdf_artifacts.ArtifactDependencyError(
          rdf_artifact, "missing dependency", cause=e)

    message = dependency_obj.error_message
    if message:
      raise rdf_artifacts.ArtifactDependencyError(
          rdf_artifact, "dependency error", cause=message)


def Validate(rdf_artifact):
  """Attempts to validate the artifact has been well defined.

  This checks both syntax and dependencies of the artifact. Because of that,
  this method can be called only after all other artifacts have been loaded.

  Args:
    rdf_artifact: RDF object artifact.

  Raises:
    ArtifactDefinitionError: If artifact is invalid.
  """
  ValidateSyntax(rdf_artifact)
  ValidateDependencies(rdf_artifact)


def GetArtifactDependencies(rdf_artifact, recursive=False, depth=1):
  """Return a set of artifact dependencies.

  Args:
    rdf_artifact: RDF object artifact.
    recursive: If True recurse into dependencies to find their dependencies.
    depth: Used for limiting recursion depth.

  Returns:
    A set of strings containing the dependent artifact names.

  Raises:
    RuntimeError: If maximum recursion depth reached.
  """
  deps = set()
  for source in rdf_artifact.sources:
    # ARTIFACT is the legacy name for ARTIFACT_GROUP
    # per: https://github.com/ForensicArtifacts/artifacts/pull/143
    # TODO(user): remove legacy support after migration.
    if source.type in (rdf_artifacts.ArtifactSource.SourceType.ARTIFACT,
                       rdf_artifacts.ArtifactSource.SourceType.ARTIFACT_GROUP):
      if source.attributes.GetItem("names"):
        deps.update(source.attributes.GetItem("names"))

  if depth > 10:
    raise RuntimeError("Max artifact recursion depth reached.")

  deps_set = set(deps)
  if recursive:
    for dep in deps:
      artifact_obj = REGISTRY.GetArtifact(dep)
      new_dep = GetArtifactDependencies(artifact_obj, True, depth=depth + 1)
      if new_dep:
        deps_set.update(new_dep)

  return deps_set


# TODO(user): Add tests for this and for all other Get* functions in this
# package.
def GetArtifactsDependenciesClosure(name_list, os_name=None):
  """For all the artifacts in the list returns them and their dependencies."""

  artifacts = set(REGISTRY.GetArtifacts(os_name=os_name, name_list=name_list))

  dependencies = set()
  for art in artifacts:
    dependencies.update(GetArtifactDependencies(art, recursive=True))
  if dependencies:
    artifacts.update(
        set(
            REGISTRY.GetArtifacts(
                os_name=os_name, name_list=list(dependencies))))

  return artifacts


def GetArtifactPathDependencies(rdf_artifact):
  """Return a set of knowledgebase path dependencies.

  Args:
    rdf_artifact: RDF artifact object.

  Returns:
    A set of strings for the required kb objects e.g.
    ["users.appdata", "systemroot"]
  """
  deps = set()
  for source in rdf_artifact.sources:
    for arg, value in iteritems(source.attributes):
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
  deps.update(GetArtifactParserDependencies(rdf_artifact))
  return deps


def GetArtifactParserDependencies(rdf_artifact):
  """Return the set of knowledgebase path dependencies required by the parser.

  Args:
    rdf_artifact: RDF artifact object.

  Returns:
    A set of strings for the required kb objects e.g.
    ["users.appdata", "systemroot"]
  """
  deps = set()
  processors = parser.Parser.GetClassesByArtifact(rdf_artifact.name)
  for p in processors:
    deps.update(p.knowledgebase_dependencies)
  return deps
