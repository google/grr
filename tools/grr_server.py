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



import threading
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.gui import admin_ui
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.tools import http_server
from grr.worker import enroller
from grr.worker import worker


flags.DEFINE_bool("start_enroller", False,
                  "Start the server as enroller.")

flags.DEFINE_bool("start_worker", False,
                  "Start the server as worker.")

flags.DEFINE_bool("start_http_server", False,
                  "Start the server as HTTP server.")

flags.DEFINE_bool("start_ui", False,
                  "Start the server as user interface.")


def main(argv):
  """Sets up all the component in their own threads."""
  flag_list = [flags.FLAGS.start_worker, flags.FLAGS.start_ui,
               flags.FLAGS.start_http_server, flags.FLAGS.start_enroller]
  enabled_flags = [f for f in flag_list if f]

  # If no start preferences were provided start everything.
  if not enabled_flags:
    flags.FLAGS.start_worker = True
    flags.FLAGS.start_enroller = True
    flags.FLAGS.start_http_server = True
    flags.FLAGS.start_ui = True

  if len(enabled_flags) != 1:
    # If we only have one flag, we are running in single component mode and we
    # want the component to do the initialization. Otherwise we initialize as
    # a SingleServer.
    config_lib.CONFIG.AddContext(
        "SingleServer Context",
        "Context applied when running all functions in a single server.")
    startup.Init()

  # Start the worker thread if necessary.
  if flags.FLAGS.start_worker:
    worker_thread = threading.Thread(target=worker.main, args=[argv],
                                     name="Worker")
    worker_thread.daemon = True
    worker_thread.start()

  # Start the enroller thread if necessary.
  if flags.FLAGS.start_enroller:
    enroller_thread = threading.Thread(target=enroller.main, args=[argv],
                                       name="Enroller")
    enroller_thread.daemon = True
    enroller_thread.start()

  # Start the HTTP server thread, that clients communicate with, if necessary.
  if flags.FLAGS.start_http_server:
    http_thread = threading.Thread(target=http_server.main, args=[argv],
                                   name="HTTP Server")
    http_thread.daemon = True
    http_thread.start()

  # Start the UI thread if necessary.
  if flags.FLAGS.start_ui:
    ui_thread = threading.Thread(target=admin_ui.main, args=[argv],
                                 name="GUI")
    ui_thread.daemon = True
    ui_thread.start()

  try:
    while True:
      time.sleep(100)
  except KeyboardInterrupt:
    pass


if __name__ == "__main__":
  flags.StartMain(main)
