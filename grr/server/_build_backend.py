#!/usr/bin/env python
"""Custom PEP 517 build backend for grr-response-server."""

from collections.abc import Mapping
import os
import pathlib
import shutil
import subprocess
from typing import Any, Optional

from setuptools import build_meta as _orig

_ROOT = pathlib.Path(__file__).resolve().parent
_UI_DIR = _ROOT / "grr_response_server" / "gui" / "ui"


def _should_make_ui_files() -> bool:
  """Returns whether Angular Admin UI assets should be built."""
  if os.environ.get("GRR_NO_MAKE_UI_FILES") == "1":
    return False
  # Pre-built sdist archives already bundle compiled `gui/static` assets and
  # exclude `gui/ui` via `MANIFEST.in`, so `package.json` is only present when
  # building from a source checkout.
  return (_UI_DIR / "package.json").is_file()


def _make_ui_files() -> None:
  """Builds Admin UI JS/CSS assets from sources."""
  npm = shutil.which("npm")
  if not npm:
    raise RuntimeError("npm executable not found on PATH.")
  subprocess.check_call([npm, "ci"], cwd=_UI_DIR)
  subprocess.check_call([npm, "run", "ng", "build", "--prod"], cwd=_UI_DIR)


prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _orig.prepare_metadata_for_build_editable


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
  """Builds UI assets (unless skipped) and builds a wheel."""
  if _should_make_ui_files():
    _make_ui_files()
  return _orig.build_wheel(
      wheel_directory,
      config_settings=config_settings,
      metadata_directory=metadata_directory,
  )


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
) -> str:
  """Builds UI assets (unless skipped) and builds a source distribution."""
  if _should_make_ui_files():
    _make_ui_files()
  return _orig.build_sdist(
      sdist_directory,
      config_settings=config_settings,
  )


def build_editable(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
  """Builds UI assets (unless skipped) and builds a PEP 660 editable wheel."""
  if _should_make_ui_files():
    _make_ui_files()
  return _orig.build_editable(
      wheel_directory,
      config_settings=config_settings,
      metadata_directory=metadata_directory,
  )
