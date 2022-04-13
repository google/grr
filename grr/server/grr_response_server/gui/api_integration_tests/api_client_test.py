#!/usr/bin/env python

from unittest import mock

from absl import app

from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class ApiClientTest(api_integration_test_lib.ApiIntegrationTest):

  @mock.patch.object(fleetspeak_connector, "CONN")
  @mock.patch.object(fleetspeak_utils, "KillFleetspeak")
  def testKillFleetspeak(self, kill_fs_mock, fs_conn):
    self.api.Client("C.1000000000000000").KillFleetspeak(True)
    kill_fs_mock.assert_called_with("C.1000000000000000", True)
    self.assertIsInstance(kill_fs_mock.call_args[0][0], str)

  @mock.patch.object(fleetspeak_connector, "CONN")
  @mock.patch.object(fleetspeak_utils, "RestartFleetspeakGrrService")
  def testRestartFleetspeakGrrService(self, kill_fs_mock, fs_conn):
    self.api.Client("C.2000000000000000").RestartFleetspeakGrrService()
    kill_fs_mock.assert_called_with("C.2000000000000000")
    self.assertIsInstance(kill_fs_mock.call_args[0][0], str)

  @mock.patch.object(fleetspeak_connector, "CONN")
  @mock.patch.object(fleetspeak_utils, "DeleteFleetspeakPendingMessages")
  def testDeleteFleetspeakPendingMessages(self, delete_msgs_mock, fs_conn):
    self.api.Client("C.2000000000000000").DeleteFleetspeakPendingMessages()
    delete_msgs_mock.assert_called_with("C.2000000000000000")
    self.assertIsInstance(delete_msgs_mock.call_args[0][0], str)

  def testClientRefRepr(self):
    self.assertEqual(
        repr(self.api.Client("C.1000000000000000")),
        "ClientRef(client_id='C.1000000000000000')")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
