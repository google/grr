#!/usr/bin/env python
"""Script that compiles proto files."""

import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser()

parser.add_argument(
    "--clean",
    action="store_true",
    default=False,
    help="Clean compiled protos.")

parser.add_argument(
    "--mypy-protobuf",
    default="",
    help="A path to the mypy protobuf generator plugin.")

args = parser.parse_args()

ROOT = os.path.dirname(os.path.abspath(__file__))

PROTOS = [
    ("grr_response_client/unprivileged/proto", "filesystem"),
    ("grr_response_client/unprivileged/proto", "memory"),
]


def Clean():
  for directory, base_name in PROTOS:
    for suffix in ("pb2.py", "pb2.pyc", "pb2_grpc.py", "pb2_grpc.pyc"):
      path = os.path.join(ROOT, directory, f"{base_name}_{suffix}")
      if os.path.exists(path):
        os.unlink(path)


def MakeProto():
  """Compiles proto files."""
  for directory, base_name in PROTOS:
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        # Write the python files next to the .proto files.
        "--python_out",
        ROOT,
        "--proto_path",
        ROOT,
        os.path.join(ROOT, directory, f"{base_name}.proto"),
    ]

    if args.mypy_protobuf:
      mypy_protobuf = os.path.realpath(args.mypy_protobuf)
      command.append(f"--plugin=protoc-gen-mypy={mypy_protobuf}")
      command.append(f"--mypy_out={ROOT}")

    subprocess.check_call(command, cwd=ROOT)


if __name__ == "__main__":
  if args.clean:
    Clean()
  MakeProto()
