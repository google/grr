#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
import mock

from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class RootApiClientManagementTest(
    api_integration_test_lib.RootApiIntegrationTest):

  @mock.patch.object(fleetspeak_connector, "CONN")
  @mock.patch.object(fleetspeak_utils, "KillFleetspeak")
  def testKillFleetspeak(self, kill_fs_mock, fs_conn):
    self.api.root.Client("C.1000000000000000").KillFleetspeak(True)
    kill_fs_mock.assert_called_with("C.1000000000000000", True)

  @mock.patch.object(fleetspeak_connector, "CONN")
  @mock.patch.object(fleetspeak_utils, "RestartFleetspeakGrrService")
  def testRestartFleetspeakGrrService(self, kill_fs_mock, fs_conn):
    self.api.root.Client("C.2000000000000000").RestartFleetspeakGrrService()
    kill_fs_mock.assert_called_with("C.2000000000000000")

  def testClientRefRepr(self):
    self.assertEqual(
        repr(self.api.root.Client("C.1000000000000000")),
        "<ClientRef client_id=C.1000000000000000>")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
