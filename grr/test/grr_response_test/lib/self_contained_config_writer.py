#!/usr/bin/env python
"""Generator for server and client configs for self-contained testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io

from absl import app
from absl import flags
import portpicker

from grr_response_client_builder import build
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_server.bin import config_updater_keys_util

flags.DEFINE_string("dest_server_config_path", None,
                    "Where to write generated server configuration.")
flags.DEFINE_string("dest_client_config_path", None,
                    "Where to write generated client configuration.")

# We want the config writer to be a standalone executable and also to be
# importable from run_self_contained.py. As run_self_contained.py already
# defines --mysql_database, --mysql_username and --mysql_password flags,
# we avoid name clash by using the "config_" prefix.
flags.DEFINE_string("config_mysql_database", None,
                    "MySQL database name to use.")

flags.DEFINE_string("config_mysql_username", None, "MySQL username to use.")
flags.mark_flag_as_required("config_mysql_username")

flags.DEFINE_string("config_mysql_password", None, "MySQL password to use.")

flags.DEFINE_string("config_logging_path", None,
                    "Base logging path for server components to use.")


def main(argv):
  del argv  # Unused.

  if not flags.FLAGS.dest_server_config_path:
    raise ValueError("dest_server_config_path flag has to be provided.")

  if not flags.FLAGS.dest_client_config_path:
    raise ValueError("dest_client_config_path flag has to be provided.")

  admin_ui_port = portpicker.pick_unused_port()
  frontend_port = portpicker.pick_unused_port()

  source_server_config_path = package.ResourcePath(
      "grr-response-core", "install_data/etc/grr-server.yaml")
  config_lib.LoadConfig(config.CONFIG, source_server_config_path)
  config.CONFIG.SetWriteBack(flags.FLAGS.dest_server_config_path)

  # TODO(user): remove when AFF4 is gone.
  config.CONFIG.Set("Database.aff4_enabled", False)
  config.CONFIG.Set("Database.enabled", True)

  config.CONFIG.Set("Blobstore.implementation", "DbBlobStore")
  config.CONFIG.Set("Database.implementation", "MysqlDB")
  config.CONFIG.Set("Mysql.database", flags.FLAGS.config_mysql_database)
  if flags.FLAGS.config_mysql_username is not None:
    config.CONFIG.Set("Mysql.username", flags.FLAGS.config_mysql_username)
  if flags.FLAGS.config_mysql_password is not None:
    config.CONFIG.Set("Mysql.password", flags.FLAGS.config_mysql_password)
  config.CONFIG.Set("AdminUI.port", admin_ui_port)
  config.CONFIG.Set("AdminUI.headless", True)
  config.CONFIG.Set("Frontend.bind_address", "127.0.0.1")
  config.CONFIG.Set("Frontend.bind_port", frontend_port)
  config.CONFIG.Set("Server.initialized", True)
  config.CONFIG.Set("Client.poll_max", 1)
  config.CONFIG.Set("Client.server_urls",
                    ["http://localhost:%d/" % frontend_port])
  if flags.FLAGS.config_logging_path is not None:
    config.CONFIG.Set("Logging.path", flags.FLAGS.config_logging_path)

  config_updater_keys_util.GenerateKeys(config.CONFIG)
  config.CONFIG.Write()

  config_lib.SetPlatformArchContext()
  context = list(config.CONFIG.context)
  context.append("Client Context")
  deployer = build.ClientRepacker()
  config_data = deployer.GetClientConfig(
      context, validate=False, deploy_timestamp=False)
  with io.open(flags.FLAGS.dest_client_config_path, "w") as fd:
    fd.write(config_data)


if __name__ == "__main__":
  app.run(main)
