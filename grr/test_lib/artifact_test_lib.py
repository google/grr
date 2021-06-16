#!/usr/bin/env python
"""Decorators and helper functions for artifacts-related tests."""

import io
import os
from unittest import mock

from grr_response_core import config
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import artifact_registry


def PatchCleanArtifactRegistry(decoration_target=None):
  """Class/method decorator patching artifact registry to be an empty registry.

  This decorator is effectively a wrapper around mock.patch. This means that
  when a class or method is patched, corresponding test methods receive an
  additional argument that will be the patched artifact registry.

  For example:
  @artifact_test_lib.PatchCleanArtifactRegistry
  def testFoo(self, registry):
    ...

  Args:
    decoration_target: Class or function to be decorated if used as a decorator.

  Returns:
    mock.patch.object patcher when called without arguments or decorated
    class/method when used as a decorator.
  """
  patcher = mock.patch.object(
      artifact_registry,
      "REGISTRY",
      new_callable=artifact_registry.ArtifactRegistry)
  if decoration_target:
    return patcher(decoration_target)
  else:
    return patcher


def PatchDefaultArtifactRegistry(decoration_target=None):
  """Class/method decorator patching artifact registry to be a default registry.

  This decorator is effectively a wrapper around mock.patch. This means that
  when a class or method is patched, corresponding test methods receive an
  additional argument that will be the patched artifact registry.

  For example:
  @artifact_test_lib.PatchDefaultArtifactRegistry
  def testFoo(self, registry):
    ...

  Args:
    decoration_target: Class or function to be decorated if used as a decorator.

  Returns:
    mock.patch.object patcher when called without arguments or decorated
    class/method when used as a decorator.
  """
  patcher = mock.patch.object(
      artifact_registry, "REGISTRY", new_callable=CreateDefaultArtifactRegistry)

  if decoration_target:
    return patcher(decoration_target)
  else:
    return patcher


def PatchDatastoreOnlyArtifactRegistry(decoration_target=None):
  """Class/method decorator patching artifact registry to be datastore-only.

  This decorator is effectively a wrapper around mock.patch. This means that
  when a class or method is patched, corresponding test methods receive an
  additional argument that will be the patched artifact registry.

  For example:
  @artifact_test_lib.PatchTestArtifactRegistry
  def testFoo(self, registry):
    ...

  Args:
    decoration_target: Class or function to be decorated if used as a decorator.

  Returns:
    mock.patch.object patcher when called without arguments or decorated
    class/method when used as a decorator.
  """
  patcher = mock.patch.object(
      artifact_registry,
      "REGISTRY",
      new_callable=CreateDatastoreOnlyArtifactRegistry)

  if decoration_target:
    return patcher(decoration_target)
  else:
    return patcher


def PatchTestArtifactRegistry(decoration_target=None):
  """Class/method decorator patching artifact registry to be a test registry.

  This decorator is effectively a wrapper around mock.patch. This means that
  when a class or method is patched, corresponding test methods receive an
  additional argument that will be the patched artifact registry.

  For example:
  @artifact_test_lib.PatchTestArtifactRegistry
  def testFoo(self, registry):
    ...

  Args:
    decoration_target: Class or function to be decorated if used as a decorator.

  Returns:
    mock.patch.object patcher when called without arguments or decorated
    class/method when used as a decorator.
  """
  patcher = mock.patch.object(
      artifact_registry, "REGISTRY", new_callable=CreateTestArtifactRegistry)

  if decoration_target:
    return patcher(decoration_target)
  else:
    return patcher


def CreateDefaultArtifactRegistry():
  r = artifact_registry.ArtifactRegistry()
  r.AddDefaultSources()
  return r


def CreateDatastoreOnlyArtifactRegistry():
  return artifact_registry.ArtifactRegistry()


def CreateTestArtifactRegistry():
  r = artifact_registry.ArtifactRegistry()
  r.AddDirSource(os.path.join(config.CONFIG["Test.data_dir"], "artifacts"))
  return r


def GenFileData(paths, data, stats=None, files=None, modes=None):
  """Generate a tuple of list of stats and list of file contents."""
  if stats is None:
    stats = []
  if files is None:
    files = []
  if modes is None:
    modes = {}
  modes.setdefault("st_uid", 0)
  modes.setdefault("st_gid", 0)
  modes.setdefault("st_mode", 0o0100644)
  for path in paths:
    p = rdf_paths.PathSpec(path=path, pathtype="OS")
    stats.append(rdf_client_fs.StatEntry(pathspec=p, **modes))
  for val in data:
    files.append(io.BytesIO(val.encode("utf-8")))
  return stats, files


def GenPathspecFileData(data):
  """Gen a tuple of list of stats and list of file contents from a dict."""
  paths = []
  contents = []
  for path, content in data.items():
    paths.append(rdf_paths.PathSpec.OS(path=path))
    contents.append(io.BytesIO(content))
  return paths, contents
