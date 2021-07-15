#!/usr/bin/env python
import concurrent.futures
import os
import subprocess
import sys

from absl import flags
from absl.testing import absltest

from grr_response_client.unprivileged.windows import process_test
from grr_response_client.unprivileged.windows import sandbox

flags.DEFINE_bool(
    "set_inheritance",
    default=True,
    help="If true, permission inheritance is set on directories shared with the sandbox."
)


def _SourceCodeBaseDir() -> str:
  """Returns the path to the source code tree root."""
  current_path = sandbox.__file__
  while current_path:
    if os.path.exists(os.path.join(current_path, "version.ini")):
      return current_path
    current_path = os.path.dirname(current_path)
  raise Exception("Could not find root directory of source code.")


def setUpModule():
  # All directory trees that will be shared with the sandbox.

  read_only_paths = {
      # Path to the virtualenv
      sys.prefix,
      # Path to the Python installation
      sys.base_prefix,
      # Path to the source code tree
      _SourceCodeBaseDir(),
  }

  # Note that there are 2 "virtualenv" implementations: virtualenv and venv.
  # The virtualenv implementation uses `real_prefix` instead of `base_prefix`.

  if hasattr(sys, "real_prefix"):
    read_only_paths.add(getattr(sys, "real_prefix"))

  # For permissions to be set correctly on the directory treees, inheritance
  # needs to be enabled. Otherwise, permissions don't propagate recursively.
  # This enables inheritance on all directory trees recursively.
  # Since this is a very slow operation, directories are processed in parallel.

  if flags.FLAGS.set_inheritance:
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
      for read_only_path in read_only_paths:
        futures.append(
            executor.submit(subprocess.check_call, [
                "icacls",
                read_only_path,
                "/inheritance:e",
                "/t",
                "/c",
                "/q",
            ]))

    # Check for exceptions.

    for future in futures:
      future.result()

  sandbox.InitSandbox("TheSandboxName", read_only_paths)


class SandboxTest(process_test.ProcessTest):
  pass


if __name__ == "__main__":
  absltest.main()
