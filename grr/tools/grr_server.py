#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""This is a single binary that runs all the GRR components.

This binary can be used to very easily start up all the different components
of GRR at the same time. For performance reasons, the different parts
should usually be run in different processes for best results but to get
a quick idea how GRR works, this helper program can show very quick results.

The minimal command line to start up everything is:

grr_config_updater.py add_user --username=<username>
then enter a password for the user when prompted.

python grr/tools/grr_server.py \
    --config grr/config/grr_test.yaml
"""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import admin_ui
from grr.lib import flags
from grr.server.data_server import data_server
from grr.tools import http_server
from grr.worker import worker


flags.DEFINE_bool("start_worker", False,
                  "Start the server as worker.")

flags.DEFINE_bool("start_http_server", False,
                  "Start the server as HTTP server.")

flags.DEFINE_bool("start_ui", False,
                  "Start the server as user interface.")

flags.DEFINE_bool("start_dataserver", False,
                  "Start the dataserver.")


def main(argv):
  """Sets up all the component in their own threads."""

  # Start as a worker.
  if flags.FLAGS.start_worker:
    worker.main([argv])

  # Start as a HTTP server that clients communicate with.
  elif flags.FLAGS.start_http_server:
    http_server.main([argv])

  # Start as an AdminUI.
  elif flags.FLAGS.start_ui:
    admin_ui.main([argv])

  # Start as the data server.
  elif flags.FLAGS.start_dataserver:
    data_server.main([argv])

  # If no flags were set then raise.
  else:
    raise RuntimeError("No component specified to start")


if __name__ == "__main__":
  flags.StartMain(main)
