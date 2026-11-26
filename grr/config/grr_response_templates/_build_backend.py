#!/usr/bin/env python
"""Custom PEP 517 build backend for grr-response-templates."""

from collections.abc import Mapping
import os
import pathlib
import re
from typing import Any, Optional

from setuptools import build_meta as _orig

_ROOT = pathlib.Path(__file__).resolve().parent
REQUIRED_TEMPLATES = (
    "GRR_maj.minor_amd64.msi.zip",
    "grr_maj.minor_amd64.deb.zip",
    "grr_maj.minor_amd64.xar.zip",
    "grr_maj.minor_amd64.rpm.zip",
)


def _get_version() -> str:
  """Reads `[project].version` from `pyproject.toml`."""
  pyproject_path = _ROOT / "pyproject.toml"
  match = re.search(
      r'^version\s*=\s*["\']([^"\']+)["\']',
      pyproject_path.read_text(encoding="utf-8"),
      re.MULTILINE,
  )
  if not match:
    raise RuntimeError(f"Couldn't find version in {pyproject_path}")
  return match.group(1)


def check_templates() -> None:
  """Verifies that required client template archives exist for `maj.minor`."""
  version = _get_version()
  major_minor = ".".join(version.split(".")[0:2])
  templates = (_ROOT / "templates").glob(f"*{major_minor}*.zip")
  required_templates = {
      t.replace("maj.minor", major_minor) for t in REQUIRED_TEMPLATES
  }
  templates_present = {
      re.sub(
          rf"_{re.escape(major_minor)}[^_]+_",
          f"_{major_minor}_",
          t.name,
      )
      for t in templates
  }
  difference = required_templates - templates_present
  if difference:
    raise RuntimeError(f"Missing templates {sorted(difference)}")


prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _orig.prepare_metadata_for_build_editable
build_wheel = _orig.build_wheel
build_editable = _orig.build_editable


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
) -> str:
  """Validates client template archives (unless skipped) and builds an sdist."""
  if os.environ.get("GRR_SKIP_CHECK_TEMPLATES") != "1":
    check_templates()
  result = _orig.build_sdist(
      sdist_directory,
      config_settings=config_settings,
  )
  print("To upload a release, run upload.sh [version]")
  return result
