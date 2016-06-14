#!/usr/bin/env python
"""This is a backend analysis worker which will be deployed on the server.

We basically pull a new task from the task master, and run the plugin
it specifies.
"""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib import worker


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext("Worker Context",
                               "Context applied when running a worker.")

  # Initialise flows
  startup.Init()
  token = access_control.ACLToken(username="GRRWorker").SetUID()
  worker_obj = worker.GRRWorker(token=token)
  worker_obj.Run()


if __name__ == "__main__":
  flags.StartMain(main)
