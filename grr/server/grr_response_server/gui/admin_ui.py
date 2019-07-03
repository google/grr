#!/usr/bin/env python
"""This is a development server for running the UI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server.gui import local
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_server import server_startup
from grr_response_server.gui import wsgiapp

flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR admin UI version number and exit immediately.")


def main(_):
  """Run the main test harness."""

  if flags.FLAGS.version:
    print("GRR Admin UI {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(
      contexts.ADMIN_UI_CONTEXT,
      "Context applied when running the admin user interface GUI.")
  server_startup.Init()

  if not config.CONFIG["AdminUI.headless"] and (not os.path.exists(
      os.path.join(config.CONFIG["AdminUI.document_root"],
                   "dist/grr-ui.bundle.js")) or not os.path.exists(
                       os.path.join(config.CONFIG["AdminUI.document_root"],
                                    "dist/grr-ui.bundle.css"))):
    raise RuntimeError("Can't find compiled JS/CSS bundles. "
                       "Please reinstall the PIP package using "
                       "\"pip install -e .\" to rebuild the bundles.")

  server = wsgiapp.MakeServer(multi_threaded=True)
  server_startup.DropPrivileges()

  server.serve_forever()


if __name__ == "__main__":
  app.run(main)
