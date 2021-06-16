#!/usr/bin/env python
"""A script to prepare the source tree for building."""

# This script must have no special requirements because it won't be able to
# import any GRR stuff until the protos are built.

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


def Clean():
  """Clean out compiled protos."""
  # Find all the compiled proto files and unlink them.
  for (root, _, files) in os.walk(ROOT):
    for filename in files:
      full_filename = os.path.join(root, filename)
      if full_filename.endswith("_pb2.py") or full_filename.endswith(
          "_pb2.pyc"):
        os.unlink(full_filename)


def MakeProto():
  """Make sure our protos have been compiled to python libraries."""
  # Start running from one directory above the grr directory which is found by
  # this scripts's location as __file__.
  cwd = os.path.dirname(os.path.abspath(__file__))

  # Find all the .proto files.
  protos_to_compile = []
  for (root, dirs, files) in os.walk(cwd):
    # Make sure an accidental .eggs cache is ignored.
    if ".eggs" in dirs:
      dirs.remove(".eggs")

    for filename in files:
      full_filename = os.path.join(root, filename)
      if full_filename.endswith(".proto"):
        proto_stat = os.stat(full_filename)

        pb2_path = full_filename.rsplit(".", 1)[0] + "_pb2.py"
        try:
          pb2_stat = os.stat(pb2_path)
          if pb2_stat.st_mtime >= proto_stat.st_mtime:
            continue

        except (OSError, IOError):
          pass

        protos_to_compile.append(full_filename)

  if protos_to_compile:
    for proto in protos_to_compile:
      command = [
          sys.executable,
          "-m",
          "grpc_tools.protoc",
          # Write the python files next to the .proto files.
          "--python_out",
          ROOT,
          "--proto_path=%s" % ROOT,
          proto
      ]

      if args.mypy_protobuf:
        mypy_protobuf = os.path.realpath(args.mypy_protobuf)
        command.append(f"--plugin=protoc-gen-mypy={mypy_protobuf}")
        command.append(f"--mypy_out={ROOT}")

      print(
          "Compiling %s with (cwd: %s): %s" % (proto, ROOT, " ".join(command)))
      # The protoc compiler is too dumb to deal with full paths - it expects a
      # relative path from the current working directory.
      subprocess.check_call(command, cwd=ROOT)


if __name__ == "__main__":
  if args.clean:
    Clean()
  MakeProto()
