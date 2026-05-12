#!/usr/bin/env python
"""Generator for server and client configs for self-contained testing."""

import io

from absl import app
from absl import flags
import portpicker

from grr_response_client_builder import build_helpers
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_server.bin import config_updater_keys_util

_DEST_SERVER_CONFIG_PATH = flags.DEFINE_string(
    "dest_server_config_path",
    None,
    "Where to write generated server configuration.",
)
_DEST_CLIENT_CONFIG_PATH = flags.DEFINE_string(
    "dest_client_config_path",
    None,
    "Where to write generated client configuration.",
)

# We want the config writer to be a standalone executable and also to be
# importable from run_self_contained.py. As run_self_contained.py already
# defines --mysql_database, --mysql_username and --mysql_password flags,
# we avoid name clash by using the "config_" prefix.
_CONFIG_MYSQL_DATABASE = flags.DEFINE_string(
    "config_mysql_database", None, "MySQL database name to use."
)

_CONFIG_MYSQL_USERNAME = flags.DEFINE_string(
    "config_mysql_username", None, "MySQL username to use."
)
flags.mark_flag_as_required("config_mysql_username")

_CONFIG_MYSQL_PASSWORD = flags.DEFINE_string(
    "config_mysql_password", None, "MySQL password to use."
)

_CONFIG_LOGGING_PATH = flags.DEFINE_string(
    "config_logging_path",
    None,
    "Base logging path for server components to use.",
)

flags.DEFINE_string(
    name="config_osquery_path",
    default="",
    help="A path to the osquery executable.",
)

_CONFIG_COMMAND_SIGNING_KEY_PATH = flags.DEFINE_string(
    name="config_command_signing_key_path",
    default="",
    help="Path to the file with command signing key.",
)


def main(argv):
  del argv  # Unused.

  if not _DEST_SERVER_CONFIG_PATH.value:
    raise ValueError("dest_server_config_path flag has to be provided.")

  if not _DEST_CLIENT_CONFIG_PATH.value:
    raise ValueError("dest_client_config_path flag has to be provided.")

  admin_ui_port = portpicker.pick_unused_port()

  source_server_config_path = package.ResourcePath(
      "grr-response-core", "install_data/etc/grr-server.yaml")
  config_lib.LoadConfig(config.CONFIG, source_server_config_path)
  config.CONFIG.SetWriteBack(_DEST_SERVER_CONFIG_PATH.value)

  # Make sure to not overload the machine running the self-contained tests.
  # Threadpool.size currently influences the size of the Fleetspeak Frontend's
  # threadpool that handles incoming gRPC requests from Fleetspeak.
  config.CONFIG.Set("Threadpool.size", 5)
  config.CONFIG.Set("Blobstore.implementation", "DbBlobStore")
  config.CONFIG.Set("Database.implementation", "MysqlDB")
  config.CONFIG.Set("Mysql.database", _CONFIG_MYSQL_DATABASE.value)
  if _CONFIG_MYSQL_USERNAME.value is not None:
    config.CONFIG.Set("Mysql.username", _CONFIG_MYSQL_USERNAME.value)
  if _CONFIG_MYSQL_PASSWORD.value is not None:
    config.CONFIG.Set("Mysql.password", _CONFIG_MYSQL_PASSWORD.value)
  config.CONFIG.Set("AdminUI.port", admin_ui_port)
  config.CONFIG.Set("AdminUI.headless", True)
  # Because end-to-end tests depend on signed commands, we need the root router
  # to be able to do the signing. We just modify the default router to avoid
  # setting up a separate user just for that.
  config.CONFIG.Set("API.DefaultRouter", "ApiRootAndNonRootRouter")

  config.CONFIG.Set("Server.initialized", True)
  config.CONFIG.Set("Cron.active", False)

  fleetspeak_frontend_port = portpicker.pick_unused_port()
  fleetspeak_admin_port = portpicker.pick_unused_port()

  config.CONFIG.Set(
      "Server.fleetspeak_message_listen_address",
      "localhost:%d" % fleetspeak_frontend_port,
  )
  config.CONFIG.Set(
      "Server.fleetspeak_server", "localhost:%d" % fleetspeak_admin_port
  )

  if _CONFIG_LOGGING_PATH.value is not None:
    config.CONFIG.Set("Logging.path", _CONFIG_LOGGING_PATH.value)
  config.CONFIG.Set("Logging.verbose", True)
  config.CONFIG.Set("Logging.engines", "file,stderr")

  if flags.FLAGS.config_osquery_path:
    config.CONFIG.Set("Osquery.path", flags.FLAGS.config_osquery_path)

  # TODO - Refactor command signer not to depend on the GRR config.
  # Then we can just pass the key path to the tool and the tool also becomes
  # independent of the Python codebase.
  if _CONFIG_COMMAND_SIGNING_KEY_PATH.value:
    config.CONFIG.Set(
        "CommandSigning.ed25519_private_key_file",
        _CONFIG_COMMAND_SIGNING_KEY_PATH.value,
    )

  config_updater_keys_util.GenerateKeys(config.CONFIG)
  config.CONFIG.Write()

  config_lib.SetPlatformArchContext()
  context = list(config.CONFIG.context)
  context.append("Client Context")
  config_data = build_helpers.GetClientConfig(
      context, validate=False, deploy_timestamp=False)
  with io.open(_DEST_CLIENT_CONFIG_PATH.value, "w") as fd:
    fd.write(config_data)


if __name__ == "__main__":
  app.run(main)
