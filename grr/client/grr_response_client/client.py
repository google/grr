#!/usr/bin/env python
"""This is the entry point for a single binary/EXE GRR client."""

import sys

from absl import app

# This code selects a main module based on the value of `sys.argv` and runs the
# main() from the that module.
#
# Since the decision has to be made before `absl.app.main` is run and flags are
# parsed, flags can't be used to make the decision. So the code resorts to
# very simple "manual" flag parsing.
#
# The respective main modules have to be imported conditionally. The reason is
# that `client_main` transitively imports modules, which don't work in
# unprivileged mode.


def _IsUnprivileged() -> bool:
  """Decides whether the unprivileged process is to be run."""
  return "--unprivileged_server_interface" in sys.argv


# pylint: disable=g-import-not-at-top
if _IsUnprivileged():
  from grr_response_client.unprivileged import server_main_lib as main_module
else:
  from grr_response_client import client_main as main_module
# pylint: enable=g-import-not-at-top

# `main` is used by other modules.
main = main_module.main

if __name__ == "__main__":
  app.run(main)
