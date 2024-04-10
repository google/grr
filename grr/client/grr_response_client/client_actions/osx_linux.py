#!/usr/bin/env python
"""Client action utils common to macOS and Linux."""

import logging
import os
import subprocess
import time

from grr_response_client.client_actions import tempfiles
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action


def RunInstallerCmd(cmd: list[str]) -> rdf_client_action.ExecuteBinaryResponse:
  """Run an installer process that is expected to kill the grr client."""
  # Remove env vars pointing into the bundled pyinstaller directory to prevent
  # system installers from loading grr libs.
  env = os.environ.copy()
  env.pop("LD_LIBRARY_PATH", None)
  env.pop("PYTHON_PATH", None)
  logging.info("Executing %s", " ".join(cmd))
  start = time.monotonic()
  stdout_filename = None
  stderr_filename = None
  try:
    with tempfiles.CreateGRRTempFile(
        filename="GRRInstallStdout.txt"
    ) as stdout_file:
      stdout_filename = stdout_file.name
      with tempfiles.CreateGRRTempFile(
          filename="GRRInstallStderr.txt"
      ) as stderr_file:
        stderr_filename = stderr_file.name
        p = subprocess.run(
            cmd,
            env=env,
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            check=False,
        )
        logging.error("Installer ran, but the old GRR client is still running")
        return rdf_client_action.ExecuteBinaryResponse(
            # Limit output to fit within 2MiB fleetspeak message limit.
            stdout=stdout_file.read(512 * 1024),
            stderr=stderr_file.read(512 * 1024),
            exit_status=p.returncode,
            # We have to return microseconds.
            time_used=int(1e6 * (time.monotonic() - start)),
        )
  finally:
    # Clean up log files. It's unlikely that apt/dpkg/installer will produce
    # more output than the cap above.
    for filename in (stdout_filename, stderr_filename):
      if filename is not None:
        try:
          os.remove(filename)
        except OSError:
          pass
