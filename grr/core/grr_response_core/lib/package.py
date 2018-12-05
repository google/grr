#!/usr/bin/env python
"""A module with functions for working with GRR packages."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import importlib
import inspect
import logging
import os
import sys

import pkg_resources



def _GetPkgResources(package_name, filepath):
  """A wrapper for the `pkg_resource.resource_filename` function."""
  requirement = pkg_resources.Requirement.parse(package_name)
  try:
    return pkg_resources.resource_filename(requirement, filepath)
  except pkg_resources.DistributionNotFound:
    # It may be that the working set is not in sync (e.g. if sys.path was
    # manipulated). Try to reload it just in case.
    pkg_resources.working_set = pkg_resources.WorkingSet()
    try:
      return pkg_resources.resource_filename(requirement, filepath)
    except pkg_resources.DistributionNotFound:
      logging.error("Distribution %s not found. Is it installed?", package_name)
      return None


def ResourcePath(package_name, filepath):
  """Computes a path to the specified package resource.

  Args:
    package_name: A name of the package where the resource is located.
    filepath: A path to the resource relative to the package location.

  Returns:
    A path to the resource or `None` if the resource cannot be found.
  """
  # If we are running a pyinstaller-built binary we rely on the sys.prefix
  # code below and avoid running this which will generate confusing error
  # messages.
  if not getattr(sys, "frozen", None):
    target = _GetPkgResources(package_name, filepath)
    if target and os.access(target, os.R_OK):
      return target

  # Installing from wheel places data_files relative to sys.prefix and not
  # site-packages. If we can not find in site-packages, check sys.prefix
  # instead.
  # https://python-packaging-user-guide.readthedocs.io/en/latest/distributing/#data-files
  target = os.path.join(sys.prefix, filepath)
  if target and os.access(target, os.R_OK):
    return target

  return None




def ModulePath(module_name):
  """Computes a path to the specified module.

  Args:
    module_name: A name of the module to get the path for.

  Returns:
    A path to the specified module.

  Raises:
    ImportError: If specified module cannot be imported.
  """
  module = importlib.import_module(module_name)
  path = inspect.getfile(module)

  # In case of modules with want a path to the directory rather than to the
  # `__init__.py` file itself.
  if os.path.basename(path).startswith("__init__."):
    path = os.path.dirname(path)

  # Sometimes __file__ points at a .pyc file, when we really mean the .py.
  if path.endswith(".pyc"):
    path = path[:-4] + ".py"

  return path
