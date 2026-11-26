#!/usr/bin/env python
"""Custom PEP 517 build backend for grr-response-proto.

Compiles all `.proto` definitions into `*_pb2.py` files using `grpcio-tools`
(or a custom `PROTOC` binary) when `*_pb2.py` files are missing or
`GRR_FORCE_COMPILE_PROTOS=1` is set.
"""

from collections.abc import Mapping
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Optional

from setuptools import build_meta as _orig

_ROOT = pathlib.Path(__file__).resolve().parent
_PACKAGE_DIR = _ROOT / "grr_response_proto"


def _find_proto_files() -> list[pathlib.Path]:
  """Returns paths of all `.proto` files in the package."""
  return list(_PACKAGE_DIR.rglob("*.proto"))


def _expected_pb2_path(proto_path: pathlib.Path) -> pathlib.Path:
  stem = proto_path.stem.replace("-", "_")
  return proto_path.with_name(f"{stem}_pb2.py")


def _missing_pb2_files() -> list[pathlib.Path]:
  return [
      proto_path
      for proto_path in _find_proto_files()
      if not _expected_pb2_path(proto_path).is_file()
  ]


def _needs_protoc() -> bool:
  """Returns whether `.proto` sources must be compiled."""
  return (
      bool(_missing_pb2_files())
      or os.environ.get("GRR_FORCE_COMPILE_PROTOS") == "1"
  )


def _resolve_protoc() -> Optional[list[str]]:
  """Returns the command prefix to invoke `protoc`, or `None` if unavailable."""
  protoc_env = os.environ.get("PROTOC")
  if protoc_env:
    # Resolve paths relative to the caller's working directory before
    # running subprocesses with `cwd=_ROOT`.
    protoc_path = shutil.which(protoc_env) or protoc_env
    return [str(pathlib.Path(protoc_path).resolve())]
  if importlib.util.find_spec("grpc_tools") is not None:
    return [sys.executable or "python3", "-m", "grpc_tools.protoc"]
  return None


def _clean_pb2_files() -> None:
  for pattern in ("*_pb2.py", "*_pb2.pyc"):
    for path in _PACKAGE_DIR.rglob(pattern):
      path.unlink()


def _compile_protos_if_needed() -> None:
  """Compiles `.proto` files into `*_pb2.py` when missing or forced."""
  if not _needs_protoc():
    return

  protoc_cmd = _resolve_protoc()
  if protoc_cmd is None:
    raise RuntimeError(
        "Compiled *_pb2.py files are missing and neither PROTOC nor "
        "grpcio-tools is available to compile .proto definitions."
    )

  _clean_pb2_files()

  proto_rel_paths = [
      proto.relative_to(_ROOT).as_posix() for proto in _find_proto_files()
  ]
  subprocess.check_call(
      [*protoc_cmd, "--proto_path=.", "--python_out=.", *proto_rel_paths],
      cwd=_ROOT,
  )


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
) -> str:
  """Prepares `.dist-info` metadata for building a wheel."""
  _compile_protos_if_needed()
  return _orig.prepare_metadata_for_build_wheel(
      metadata_directory,
      config_settings=config_settings,
  )


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
) -> str:
  """Prepares `.dist-info` metadata for building an editable wheel."""
  _compile_protos_if_needed()
  return _orig.prepare_metadata_for_build_editable(
      metadata_directory,
      config_settings=config_settings,
  )


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
  """Compiles protos if needed and builds a wheel."""
  if metadata_directory is None:
    _compile_protos_if_needed()
  return _orig.build_wheel(
      wheel_directory,
      config_settings=config_settings,
      metadata_directory=metadata_directory,
  )


def build_sdist(
    sdist_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
) -> str:
  """Compiles protos if needed and builds a source distribution."""
  _compile_protos_if_needed()
  return _orig.build_sdist(
      sdist_directory,
      config_settings=config_settings,
  )


def build_editable(
    wheel_directory: str,
    config_settings: Optional[Mapping[str, Any]] = None,
    metadata_directory: Optional[str] = None,
) -> str:
  """Compiles protos if needed and builds a PEP 660 editable wheel."""
  if metadata_directory is None:
    _compile_protos_if_needed()
  return _orig.build_editable(
      wheel_directory,
      config_settings=config_settings,
      metadata_directory=metadata_directory,
  )
