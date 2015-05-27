#!/usr/bin/env python
"""Central registry for artifacts."""


class Error(Exception):
  """Base exception."""


class ArtifactDefinitionError(Error):
  """Artifact is not well defined."""


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
  def ClearRegistry(cls, replace_with=None):
    prev_artifacts = cls.artifacts
    cls.artifacts = replace_with or {}
    return prev_artifacts

  @classmethod
  def GetArtifacts(cls, os_name=None, name_list=None,
                   source_type=None, exclude_dependents=False,
                   provides=None):
    """Retrieve artifact classes with optional filtering.

    All filters must match for the artifact to be returned.

    Args:
      os_name: string to match against supported_os
      name_list: list of strings to match against artifact names
      source_type: rdfvalue.ArtifactSource.SourceType to match against
                      source_type
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
