#!/usr/bin/env python
"""This is a development server for running the UI."""

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server.gui import local
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_server import server_startup
from grr_response_server.gui import wsgiapp

_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR admin UI version number and exit immediately.",
)


def main(_):
  """Run the main test harness."""

  if _VERSION.value:
    print("GRR Admin UI {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(
      contexts.ADMIN_UI_CONTEXT,
      "Context applied when running the admin user interface GUI.")
  server_startup.Init()

  fleetspeak_connector.Init()

  server = wsgiapp.MakeServer(multi_threaded=True)
  server_startup.DropPrivileges()

  server.serve_forever()


if __name__ == "__main__":
  app.run(main)
