#!/usr/bin/env python
"""This is a single binary that runs all the GRR components.

To use this entry point you must run "grr_config_updater initialize" first.
"""

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import server as config_server

from grr_response_server import server_startup
from grr_response_server.bin import fleetspeak_frontend
from grr_response_server.bin import fleetspeak_server_wrapper
from grr_response_server.bin import frontend
from grr_response_server.bin import grrafana
from grr_response_server.bin import worker
from grr_response_server.gui import admin_ui


_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR server version number and exit immediately.")

_COMPONENT = flags.DEFINE_string(
    "component", None,
    "Component to start: [frontend|admin_ui|worker|grrafana].")


def main(argv):
  """Sets up all the component in their own threads."""

  if _VERSION.value:
    print("GRR server {}".format(config_server.VERSION["packageversion"]))
    return

  # We use .startswith so that multiple copies of services can easily be
  # created using systemd as worker1 worker2 ... worker25 etc.

  if not _COMPONENT.value:
    raise ValueError("Need to specify which component to start.")

  # Start as a worker.
  if _COMPONENT.value.startswith("worker"):
    worker.main([argv])

  # Start as a frontend that clients communicate with.
  elif _COMPONENT.value.startswith("frontend"):
    server_startup.Init()
    if config.CONFIG["Server.fleetspeak_enabled"]:
      fleetspeak_frontend.main([argv])
    else:
      frontend.main([argv])

  # Start as an AdminUI.
  elif _COMPONENT.value.startswith("admin_ui"):
    admin_ui.main([argv])

  # Start as GRRafana.
  elif _COMPONENT.value.startswith("grrafana"):
    grrafana.main([argv])

  # Start a fleetspeak server.
  elif _COMPONENT.value.startswith("fleetspeak_server"):
    fleetspeak_server_wrapper.main(argv)

  # Raise on invalid component.
  else:
    raise ValueError("No valid component specified. Got: "
                     "%s." % _COMPONENT.value)


if __name__ == "__main__":
  app.run(main)
