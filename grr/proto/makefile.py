#!/usr/bin/env python
"""A script to prepare the source tree for building."""

# This script must have no special requirements because it wont be able to
# import any GRR stuff until the protos are built.

import argparse
import os
import subprocess

parser = argparse.ArgumentParser()

parser.add_argument(
    "--clean",
    action="store_true",
    default=False,
    help="Clean compiled protos.")

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
  for (root, _, files) in os.walk(cwd):
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
    # Find the protoc compiler.
    protoc = os.environ.get("PROTOC", "protoc")
    try:
      output = subprocess.check_output([protoc, "--version"])
    except (IOError, OSError):
      raise RuntimeError("Unable to launch %s protoc compiler. Please "
                         "set the PROTOC environment variable.", protoc)

    if "3.3.0" not in output:
      raise RuntimeError("Incompatible protoc compiler detected. "
                         "We need 3.3.0 not %s" % output)

    for proto in protos_to_compile:
      command = [
          protoc,
          # Write the python files next to the .proto files.
          "--python_out",
          ROOT,
          "--proto_path=%s" % ROOT,
          proto
      ]
      print "Compiling %s with (cwd: %s): %s" % (proto, ROOT, " ".join(command))
      # The protoc compiler is too dumb to deal with full paths - it expects a
      # relative path from the current working directory.
      subprocess.check_call(command, cwd=ROOT)


if __name__ == "__main__":
  if args.clean:
    Clean()
  MakeProto()
