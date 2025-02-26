#!/usr/bin/env python
"""This is a backend analysis worker which will be deployed on the server."""

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector
from grr_response_server import server_startup
from grr_response_server import worker_lib


_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR worker version number and exit immediately.",
)

# TODO: Temporarily added flag to prevent new POD worker node from
# picking up work.
_DISABLE_WORKER = flags.DEFINE_bool(
    "disable_worker",
    default=False,
    allow_override=True,
    help="Disable the worker.",
)


def main(argv):
  """Main."""
  del argv  # Unused.

  if _VERSION.value:
    print("GRR worker {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(
      contexts.WORKER_CONTEXT, "Context applied when running a worker."
  )

  # Initialise flows and config_lib
  server_startup.Init(disabled=_DISABLE_WORKER.value)

  fleetspeak_connector.Init()

  worker_obj = worker_lib.GRRWorker(disabled=_DISABLE_WORKER.value)
  worker_obj.Run()


if __name__ == "__main__":
  app.run(main)
