#!/usr/bin/env python
"""Decorators and helper functions for artifacts-related tests."""

import mock

from grr.server.grr_response_server import artifact_registry


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


def CreateDefaultArtifactRegistry():
  r = artifact_registry.ArtifactRegistry()
  r.AddDefaultSources()
  return r
