#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""This is a single binary that runs all the GRR components.

To use this entry point you must run "grr_config_updater initialize" first.
"""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import admin_ui
from grr.lib import flags
from grr.tools import frontend
from grr.worker import worker

flags.DEFINE_string(
    "component", None,
    "Component to start: [frontend|admin_ui|worker|dataserver].")


def main(argv):
  """Sets up all the component in their own threads."""

  # We use .startswith so that multiple copies of services can easily be
  # created using systemd as worker1 worker2 ... worker25 etc.

  # Start as a worker.
  if flags.FLAGS.component.startswith("worker"):
    worker.main([argv])

  # Start as a frontend that clients communicate with.
  elif flags.FLAGS.component.startswith("frontend"):
    frontend.main([argv])

  # Start as an AdminUI.
  elif flags.FLAGS.component.startswith("admin_ui"):
    admin_ui.main([argv])

  # If no flags were set then raise.
  else:
    raise RuntimeError("No valid component specified. Got: "
                       "%s." % flags.FLAGS.component)


if __name__ == "__main__":
  flags.StartMain(main)
