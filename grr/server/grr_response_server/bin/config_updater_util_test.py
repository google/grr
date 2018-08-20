#!/usr/bin/env python
import getpass

import builtins
import mock
import MySQLdb
from MySQLdb import connections
from MySQLdb.constants import CR as mysql_conn_errors

from grr_response_core import config as grr_config
from grr_response_core.lib import flags
from grr_response_server.bin import config_updater_util
from grr.test_lib import test_lib


class ConfigUpdaterLibTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ConfigUpdaterLibTest, self).setUp()
    input_patcher = mock.patch.object(builtins, "input")
    self.input_mock = input_patcher.start()
    self.addCleanup(input_patcher.stop)

  @mock.patch.object(MySQLdb, "connect")
  @mock.patch.object(getpass, "getpass")
  def testConfigureDatastore(self, getpass_mock, connect_mock):
    # Mock user-inputs for MySQL prompts.
    self.input_mock.side_effect = [
        "",  # MySQL hostname (the default is localhost).
        "1234",  # MySQL port
        "grr-test-db",  # GRR db name.
        "grr-test-user",  # GRR db user.
    ]
    getpass_mock.return_value = "grr-test-password"  # DB password for GRR.
    connect_mock.return_value = mock.Mock(spec=connections.Connection)
    config = grr_config.CONFIG.CopyConfig()
    config_updater_util.ConfigureDatastore(config)
    connect_mock.assert_called_once_with(
        host="localhost",
        port=1234,
        db="grr-test-db",
        user="grr-test-user",
        passwd="grr-test-password",
        charset="utf8")
    self.assertEqual(config.writeback_data["Mysql.host"], "localhost")
    self.assertEqual(config.writeback_data["Mysql.port"], "1234")
    self.assertEqual(config.writeback_data["Mysql.database_name"],
                     "grr-test-db")
    self.assertEqual(config.writeback_data["Mysql.database_username"],
                     "grr-test-user")
    self.assertEqual(config.writeback_data["Mysql.database_password"],
                     "grr-test-password")

  @mock.patch.object(MySQLdb, "connect")
  @mock.patch.object(getpass, "getpass")
  @mock.patch.object(config_updater_util, "_MYSQL_MAX_RETRIES", new=1)
  @mock.patch.object(config_updater_util, "_MYSQL_RETRY_WAIT_SECS", new=0.1)
  def testConfigureDatastore_ConnectionRetry(self, getpass_mock, connect_mock):
    # Mock user-inputs for MySQL prompts.
    self.input_mock.side_effect = [
        "",  # MySQL hostname (the default is localhost).
        "1234",  # MySQL port
        "grr-test-db",  # GRR db name.
        "grr-test-user",  # GRR db user.
        "n"  # Exit config initialization after retries are depleted.
    ]
    getpass_mock.return_value = "grr-test-password"  # DB password for GRR.
    connect_mock.side_effect = MySQLdb.OperationalError(
        mysql_conn_errors.CONNECTION_ERROR, "Fake connection error.")
    config = grr_config.CONFIG.CopyConfig()
    with self.assertRaises(config_updater_util.ConfigInitError):
      config_updater_util.ConfigureDatastore(config)
    self.assertEqual(connect_mock.call_count, 2)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
