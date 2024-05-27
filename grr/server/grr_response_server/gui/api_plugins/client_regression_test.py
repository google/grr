#!/usr/bin/env python
"""This modules contains regression tests for clients API handlers."""

import ipaddress

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import data_store
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
from grr_response_server.models import clients
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiSearchClientsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  api_method = "SearchClients"
  handler = client_plugin.ApiSearchClientsHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

      self.Check(
          "SearchClients",
          args=client_plugin.ApiSearchClientsArgs(query=client_id),
      )


class ApiGetClientHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  api_method = "GetClient"
  handler = client_plugin.ApiGetClientHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0, memory_size=4294967296)

    self.Check(
        "GetClient", args=client_plugin.ApiGetClientArgs(client_id=client_id)
    )


class ApiGetClientVersionsRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  mode = "FULL"

  api_method = "GetClientVersions"
  handler = client_plugin.ApiGetClientVersionsHandler

  def _SetupTestClient(self):
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0, memory_size=4294967296)

    with test_lib.FakeTime(45):
      self.SetupClient(
          0, fqdn="some-other-hostname.org", memory_size=4294967296
      )

    return client_id

  def Run(self):
    client_id = self._SetupTestClient()

    with test_lib.FakeTime(47):
      self.Check(
          "GetClientVersions",
          args=client_plugin.ApiGetClientVersionsArgs(
              client_id=client_id, mode=self.mode
          ),
      )
      self.Check(
          "GetClientVersions",
          args=client_plugin.ApiGetClientVersionsArgs(
              client_id=client_id,
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(44),
              mode=self.mode,
          ),
      )
      self.Check(
          "GetClientVersions",
          args=client_plugin.ApiGetClientVersionsArgs(
              client_id=client_id,
              start=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(44),
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(46),
              mode=self.mode,
          ),
      )


class ApiGetLastClientIPAddressHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  api_method = "GetLastClientIPAddress"
  handler = client_plugin.ApiGetLastClientIPAddressHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0)

      ip = clients.NetworkAddressFromIPAddress(
          ipaddress.IPv4Address("192.168.100.42")
      )
      data_store.REL_DB.WriteClientMetadata(client_id, last_ip=ip)

    self.Check(
        "GetLastClientIPAddress",
        args=client_plugin.ApiGetLastClientIPAddressArgs(client_id=client_id),
    )


class ApiListClientsLabelsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  api_method = "ListClientsLabels"
  handler = client_plugin.ApiListClientsLabelsHandler

  def Run(self):
    # Fix the time to avoid regressions.
    with test_lib.FakeTime(42):
      client_ids = self.SetupClients(2)

      self.AddClientLabel(client_ids[0], self.test_username, "foo")
      self.AddClientLabel(client_ids[0], self.test_username, "bar")

    self.Check("ListClientsLabels")


class ApiListKbFieldsHandlerTest(api_regression_test_lib.ApiRegressionTest):

  api_method = "ListKbFields"
  handler = client_plugin.ApiListKbFieldsHandler

  def Run(self):
    self.Check("ListKbFields")


class ApiListClientCrashesHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest,
    hunt_test_lib.StandardHuntTestMixin,
):

  api_method = "ListClientCrashes"
  handler = client_plugin.ApiListClientCrashesHandler

  def Run(self):
    client_id = self.SetupClient(0)

    client_mock = flow_test_lib.CrashClientMock(client_id)

    with test_lib.FakeTime(42):
      hunt_id = self.StartHunt(description="the hunt")

    with test_lib.FakeTime(45):
      self.AssignTasksToClients([client_id])
      hunt_test_lib.TestHuntHelperWithMultipleMocks({client_id: client_mock})

    crashes = data_store.REL_DB.ReadClientCrashInfoHistory(str(client_id))
    crash = list(crashes)[0]
    replace = {hunt_id: "H:123456", str(crash.session_id): "<some session id>"}

    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(client_id=client_id),
        replace=replace,
    )
    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(
            client_id=client_id, count=1
        ),
        replace=replace,
    )
    self.Check(
        "ListClientCrashes",
        args=client_plugin.ApiListClientCrashesArgs(
            client_id=client_id, offset=1, count=1
        ),
        replace=replace,
    )


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
