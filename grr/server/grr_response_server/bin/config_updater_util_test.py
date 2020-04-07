#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
import builtins
import getpass
import os

from absl import app

import mock
import MySQLdb
from MySQLdb import connections
from MySQLdb.constants import CR as mysql_conn_errors

from grr_response_core import config as grr_config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import signed_binary_utils
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
  def testConfigureMySQLDatastore(self, getpass_mock, connect_mock):
    # Mock user-inputs for MySQL prompts.
    self.input_mock.side_effect = [
        "",  # MySQL hostname (the default is localhost).
        "1234",  # MySQL port
        "grr-test-db",  # GRR db name.
        "grr-test-user",  # GRR db user.
        "n",  # No SSL.
    ]
    getpass_mock.return_value = "grr-test-password"  # DB password for GRR.
    connect_mock.return_value = mock.Mock(spec=connections.Connection)
    config = grr_config.CONFIG.CopyConfig()
    config_updater_util.ConfigureMySQLDatastore(config)
    connect_mock.assert_called_once_with(
        host="localhost",
        port=1234,
        db="grr-test-db",
        user="grr-test-user",
        passwd="grr-test-password",
        charset="utf8")
    self.assertEqual(config.writeback_data["Mysql.host"], "localhost")
    self.assertEqual(config.writeback_data["Mysql.port"], 1234)
    self.assertEqual(config.writeback_data["Mysql.database_name"],
                     "grr-test-db")
    self.assertEqual(config.writeback_data["Mysql.database_username"],
                     "grr-test-user")
    self.assertEqual(config.writeback_data["Mysql.database_password"],
                     "grr-test-password")

  @mock.patch.object(MySQLdb, "connect")
  @mock.patch.object(getpass, "getpass")
  def testConfigureMySQLDatastoreWithSSL(self, getpass_mock, connect_mock):
    # Mock user-inputs for MySQL prompts.
    self.input_mock.side_effect = [
        "",  # MySQL hostname (the default is localhost).
        "1234",  # MySQL port
        "grr-test-db",  # GRR db name.
        "grr-test-user",  # GRR db user.
        "Y",  # Configure SSL.
        "key_file_path",
        "cert_file_path",
        "ca_cert_file_path",
    ]
    getpass_mock.return_value = "grr-test-password"  # DB password for GRR.
    cursor_mock = mock.Mock()
    cursor_mock.fetchone = mock.Mock(return_value=["have_ssl", "YES"])
    connect_mock.return_value = mock.Mock(spec=connections.Connection)
    connect_mock.return_value.cursor = mock.Mock(return_value=cursor_mock)
    config = grr_config.CONFIG.CopyConfig()
    config_updater_util.ConfigureMySQLDatastore(config)
    connect_mock.assert_called_once_with(
        host="localhost",
        port=1234,
        db="grr-test-db",
        user="grr-test-user",
        passwd="grr-test-password",
        charset="utf8",
        ssl={
            "key": "key_file_path",
            "cert": "cert_file_path",
            "ca": "ca_cert_file_path",
        })
    self.assertEqual(config.writeback_data["Mysql.host"], "localhost")
    self.assertEqual(config.writeback_data["Mysql.port"], 1234)
    self.assertEqual(config.writeback_data["Mysql.database_name"],
                     "grr-test-db")
    self.assertEqual(config.writeback_data["Mysql.database_username"],
                     "grr-test-user")
    self.assertEqual(config.writeback_data["Mysql.database_password"],
                     "grr-test-password")
    self.assertEqual(config.writeback_data["Mysql.client_key_path"],
                     "key_file_path")
    self.assertEqual(config.writeback_data["Mysql.client_cert_path"],
                     "cert_file_path")
    self.assertEqual(config.writeback_data["Mysql.ca_cert_path"],
                     "ca_cert_file_path")

  @mock.patch.object(MySQLdb, "connect")
  @mock.patch.object(getpass, "getpass")
  @mock.patch.object(config_updater_util, "_MYSQL_MAX_RETRIES", new=1)
  @mock.patch.object(config_updater_util, "_MYSQL_RETRY_WAIT_SECS", new=0.1)
  def testConfigureMySQLDatastore_ConnectionRetry(self, getpass_mock,
                                                  connect_mock):
    # Mock user-inputs for MySQL prompts.
    self.input_mock.side_effect = [
        "Y",  # Use REL_DB as the primary data store.
        "",  # MySQL hostname (the default is localhost).
        "1234",  # MySQL port
        "grr-test-db",  # GRR db name.
        "grr-test-user",  # GRR db user.
        "n",  # No SSL.
        "n"  # Exit config initialization after retries are depleted.
    ]
    getpass_mock.return_value = "grr-test-password"  # DB password for GRR.
    connect_mock.side_effect = MySQLdb.OperationalError(
        mysql_conn_errors.CONNECTION_ERROR, "Fake connection error.")
    config = grr_config.CONFIG.CopyConfig()
    with self.assertRaises(config_updater_util.ConfigInitError):
      config_updater_util.ConfigureMySQLDatastore(config)
    self.assertEqual(connect_mock.call_count, 2)

  def testUploadPythonHack(self):
    with utils.TempDirectory() as dir_path:
      python_hack_path = os.path.join(dir_path, "hello_world.py")
      with open(python_hack_path, "wb") as f:
        f.write(b"print('Hello, world!')")
      config_updater_util.UploadSignedBinary(
          python_hack_path,
          objects_pb2.SignedBinaryID.BinaryType.PYTHON_HACK,
          "linux",
          upload_subdirectory="test")
      python_hack_urn = rdfvalue.RDFURN(
          "aff4:/config/python_hacks/linux/test/hello_world.py")
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
          python_hack_urn)
      uploaded_blobs = list(
          signed_binary_utils.StreamSignedBinaryContents(blob_iterator))
      uploaded_content = b"".join(uploaded_blobs)
      self.assertEqual(uploaded_content, b"print('Hello, world!')")

  def testUploadExecutable(self):
    with utils.TempDirectory() as dir_path:
      executable_path = os.path.join(dir_path, "foo.exe")
      with open(executable_path, "wb") as f:
        f.write(b"\xaa\xbb\xcc\xdd")
      config_updater_util.UploadSignedBinary(
          executable_path,
          objects_pb2.SignedBinaryID.BinaryType.EXECUTABLE,
          "windows",
          upload_subdirectory="anti-malware/registry-tools")
      executable_urn = rdfvalue.RDFURN(
          "aff4:/config/executables/windows/anti-malware/registry-tools/"
          "foo.exe")
      blob_iterator, _ = signed_binary_utils.FetchBlobsForSignedBinaryByURN(
          executable_urn)
      uploaded_blobs = list(
          signed_binary_utils.StreamSignedBinaryContents(blob_iterator))
      uploaded_content = b"".join(uploaded_blobs)
      self.assertEqual(uploaded_content, b"\xaa\xbb\xcc\xdd")

  def testUploadOverlyLargeSignedBinary(self):
    with mock.patch.object(config_updater_util, "_MAX_SIGNED_BINARY_BYTES", 5):
      with utils.TempDirectory() as dir_path:
        executable_path = os.path.join(dir_path, "foo.exe")
        with open(executable_path, "wb") as f:
          f.write(b"\xaa\xbb\xcc\xdd\xee\xff")
        expected_message = (
            "File [%s] is of size 6 (bytes), which exceeds the allowed maximum "
            "of 5 bytes." % executable_path)
        with self.assertRaisesWithLiteralMatch(
            config_updater_util.BinaryTooLargeError, expected_message):
          config_updater_util.UploadSignedBinary(
              executable_path, objects_pb2.SignedBinaryID.BinaryType.EXECUTABLE,
              "windows")

  @mock.patch.object(getpass, "getpass")
  def testCreateAdminUser(self, getpass_mock):
    getpass_mock.return_value = "foo_password"
    config_updater_util.CreateUser("foo_user", is_admin=True)
    self._AssertStoredUserDetailsAre("foo_user", "foo_password", True)

  def testCreateStandardUser(self):
    config_updater_util.CreateUser(
        "foo_user", password="foo_password", is_admin=False)
    self._AssertStoredUserDetailsAre("foo_user", "foo_password", False)

  def testCreateAlreadyExistingUser(self):
    config_updater_util.CreateUser("foo_user", password="foo_password1")
    with self.assertRaises(config_updater_util.UserAlreadyExistsError):
      config_updater_util.CreateUser("foo_user", password="foo_password2")

  def testUpdateUser(self):
    config_updater_util.CreateUser(
        "foo_user", password="foo_password1", is_admin=False)
    self._AssertStoredUserDetailsAre("foo_user", "foo_password1", False)
    config_updater_util.UpdateUser(
        "foo_user", password="foo_password2", is_admin=True)
    self._AssertStoredUserDetailsAre("foo_user", "foo_password2", True)

  def testGetUserSummary(self):
    config_updater_util.CreateUser(
        "foo_user", password="foo_password", is_admin=False)
    self.assertMultiLineEqual(
        config_updater_util.GetUserSummary("foo_user"),
        "Username: foo_user\nIs Admin: False")

  def testGetAllUserSummaries(self):
    config_updater_util.CreateUser(
        "foo_user1", password="foo_password1", is_admin=False)
    config_updater_util.CreateUser(
        "foo_user2", password="foo_password2", is_admin=True)
    expected_summaries = ("Username: foo_user1\nIs Admin: False\n\n"
                          "Username: foo_user2\nIs Admin: True")
    self.assertMultiLineEqual(config_updater_util.GetAllUserSummaries(),
                              expected_summaries)

  def testDeleteUser(self):
    config_updater_util.CreateUser(
        "foo_user", password="foo_password", is_admin=False)
    self.assertNotEmpty(config_updater_util.GetUserSummary("foo_user"))
    config_updater_util.DeleteUser("foo_user")
    with self.assertRaises(config_updater_util.UserNotFoundError):
      config_updater_util.GetUserSummary("foo_user")

  def _AssertStoredUserDetailsAre(self, username, password, is_admin):
    user = data_store.REL_DB.ReadGRRUser(username)
    self.assertTrue(user.password.CheckPassword(password))
    if is_admin:
      self.assertEqual(user.user_type,
                       objects_pb2.GRRUser.UserType.USER_TYPE_ADMIN)

  def testArgparseBool_CaseInsensitive(self):
    parser = argparse.ArgumentParser()
    parser.add_argument("--foo", type=config_updater_util.ArgparseBool)
    parser.add_argument("--bar", type=config_updater_util.ArgparseBool)
    namespace = parser.parse_args(["--foo", "True", "--bar", "fAlse"])
    self.assertIsInstance(namespace.foo, bool)
    self.assertIsInstance(namespace.bar, bool)
    self.assertTrue(namespace.foo)
    self.assertFalse(namespace.bar)

  def testArgparseBool_DefaultValue(self):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--foo", default=True, type=config_updater_util.ArgparseBool)
    parser.add_argument(
        "--bar", default=False, type=config_updater_util.ArgparseBool)
    namespace = parser.parse_args([])
    self.assertTrue(namespace.foo)
    self.assertFalse(namespace.bar)

  def testArgparseBool_InvalidType(self):
    expected_error = "Unexpected type: float. Expected a string."
    with self.assertRaisesWithLiteralMatch(argparse.ArgumentTypeError,
                                           expected_error):
      config_updater_util.ArgparseBool(1.23)

  def testArgparseBool_InvalidValue(self):
    expected_error = "Invalid value encountered. Expected 'True' or 'False'."
    with self.assertRaisesWithLiteralMatch(argparse.ArgumentTypeError,
                                           expected_error):
      config_updater_util.ArgparseBool("baz")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
