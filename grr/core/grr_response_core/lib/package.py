#!/usr/bin/env python
"""A module with functions for working with GRR packages."""

import importlib
import importlib.metadata
import inspect
import json
import logging
import os
import sys
from typing import Optional
import urllib.parse
import urllib.request


def _GetPkgResources(package_name, filepath):
  """A wrapper for the `pkg_resource.resource_filename` function."""
  try:
    return str(
        importlib.metadata.distribution(package_name).locate_file(filepath)
    )
  except importlib.metadata.PackageNotFoundError:
    logging.error("Distribution %s not found. Is it installed?", package_name)
    return None


def _GetEditableRoot(package_name: str) -> Optional[str]:
  """Returns the editable install root from PEP 610 `direct_url.json`."""
  try:
    dist = importlib.metadata.distribution(package_name)
  except importlib.metadata.PackageNotFoundError:
    logging.error("Distribution %s not found. Is it installed?", package_name)
    return None
  direct_url_text = dist.read_text("direct_url.json")
  if direct_url_text is None:
    return None
  direct_url = json.loads(direct_url_text)
  if not direct_url.get("dir_info", {}).get("editable", False):
    return None
  url = urllib.parse.urlparse(direct_url["url"])
  if url.scheme != "file":
    raise ValueError(f"Unexpected editable URL scheme: {direct_url['url']!r}")
  return urllib.request.url2pathname(url.path)


def ResourcePath(package_name: str, filepath: str) -> Optional[str]:
  """Computes a path to the specified package resource.

  Args:
    package_name: A name of the package where the resource is located.
    filepath: A path to the resource relative to the package location.

  Returns:
    A path to the resource or `None` if the resource cannot be found.
  """
  # TODO - Remove the `sys.frozen` check once the legacy Python
  # agent (PyInstaller) code is deleted.
  # If we are running a pyinstaller-built binary we rely on the sys.prefix
  # code below and avoid running this which will generate confusing error
  # messages.
  if not getattr(sys, "frozen", None):
    target = _GetPkgResources(package_name, filepath)
    if target and os.access(target, os.R_OK):
      return target

    editable_root = _GetEditableRoot(package_name)
    if editable_root:
      target = os.path.join(editable_root, filepath)
      if os.access(target, os.R_OK):
        return target

  # Installing from a wheel places `data-files` (used by `grr-response-core`,
  # `grr-response-templates`, and `fleetspeak-server-bin`) relative to
  # `sys.prefix` rather than `site-packages`. PyInstaller-frozen binaries also
  # rely on this fallback. If we cannot find it in `site-packages`, check
  # `sys.prefix` instead.
  # https://python-packaging-user-guide.readthedocs.io/en/latest/distributing/#data-files
  target = os.path.join(sys.prefix, filepath)
  if target and os.access(target, os.R_OK):
    return target

  return None


def ModulePath(module_name) -> str:
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
