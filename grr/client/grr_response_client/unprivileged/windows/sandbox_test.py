#!/usr/bin/env python
import concurrent.futures
import contextlib
import os
import socket
import subprocess
import sys
import unittest

from absl import flags
from absl.testing import absltest

from grr_response_client.unprivileged.windows import process_test
from grr_response_client.unprivileged.windows import sandbox

try:
  # pylint: disable=g-import-not-at-top
  from grr_response_client.unprivileged.windows import process
  import winreg
  # pylint: enable=g-import-not-at-top
except ImportError:
  raise unittest.SkipTest("This is a Windows only test.")

_SET_INHERITANCE = flags.DEFINE_bool(
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
      # Path to the souce code tree
      _SourceCodeBaseDir(),
  }

  # Note that there are 2 "virtualenv" implementations: virtualenv and venv.
  # The virtualenv implementation uses `real_prefix` instead of `base_prefix`.

  if hasattr(sys, "real_prefix"):
    read_only_paths.add(getattr(sys, "real_prefix"))

  # For permissions to be set correctly on the directory treees, inhertiance
  # needs to be enabled. Otherwise, permissions don't propage recursively.
  # This enables inheritance on all directory trees recursively.
  # Since this is a very slow operation, directories are processed in parallel.

  if _SET_INHERITANCE.value:
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


class SandboxSecurityTest(absltest.TestCase):

  def testSandboxSecurity(self):
    with contextlib.ExitStack() as stack:
      port = 12395
      sock = stack.enter_context(
          socket.socket(socket.AF_INET, socket.SOCK_STREAM))
      sock.bind(("", port))
      sock.listen()

      sub_key = "Software\\SandboxTest"
      key = winreg.CreateKeyEx(
          winreg.HKEY_LOCAL_MACHINE, sub_key, access=winreg.KEY_ALL_ACCESS)
      winreg.SetValueEx(key, "foo", 0, winreg.REG_SZ, "bar")
      winreg.FlushKey(key)
      stack.callback(winreg.DeleteKey, winreg.HKEY_LOCAL_MACHINE, sub_key)
      stack.callback(winreg.CloseKey, key)
      stack.callback(winreg.DeleteValue, key, "foo")

      args = [
          sys.executable, "-m",
          "grr_response_client.unprivileged.windows.sandbox_unprivileged_test_lib",
          "--localhost_port",
          str(port), "--registry_sub_key", sub_key
      ]

      p = process.Process(args, [])
      exit_code = p.Wait()
      self.assertEqual(exit_code, 0)


if __name__ == "__main__":
  absltest.main()
