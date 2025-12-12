#!/usr/bin/env python
"""This modules contains regression tests for clients API handlers."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_server import data_store
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import client as client_plugin
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
          args=api_client_pb2.ApiSearchClientsArgs(query=client_id),
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
        "GetClient", args=api_client_pb2.ApiGetClientArgs(client_id=client_id)
    )


class ApiGetClientVersionsRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

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
          args=api_client_pb2.ApiGetClientVersionsArgs(
              client_id=client_id,
              mode=api_client_pb2.ApiGetClientVersionsArgs.Mode.FULL,
          ),
      )
      self.Check(
          "GetClientVersions",
          args=api_client_pb2.ApiGetClientVersionsArgs(
              client_id=client_id,
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
              mode=api_client_pb2.ApiGetClientVersionsArgs.Mode.FULL,
          ),
      )
      self.Check(
          "GetClientVersions",
          args=api_client_pb2.ApiGetClientVersionsArgs(
              client_id=client_id,
              start=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  46
              ).AsMicrosecondsSinceEpoch(),
              mode=api_client_pb2.ApiGetClientVersionsArgs.Mode.FULL,
          ),
      )


class ApiGetClientSnapshotsRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  mode = "FULL"

  api_method = "GetClientSnapshots"
  handler = client_plugin.ApiGetClientSnapshotsHandler

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
          "GetClientSnapshots",
          args=api_client_pb2.ApiGetClientSnapshotsArgs(client_id=client_id),
      )
      self.Check(
          "GetClientSnapshots",
          args=api_client_pb2.ApiGetClientSnapshotsArgs(
              client_id=client_id,
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
          ),
      )
      self.Check(
          "GetClientSnapshots",
          args=api_client_pb2.ApiGetClientSnapshotsArgs(
              client_id=client_id,
              start=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  46
              ).AsMicrosecondsSinceEpoch(),
          ),
      )


class ApiGetClientStartupInfosRegressionTest(
    api_regression_test_lib.ApiRegressionTest
):

  mode = "FULL"

  api_method = "GetClientStartupInfos"
  handler = client_plugin.ApiGetClientStartupInfosHandler

  def _SetupTestClientStartupInfos(self):
    with test_lib.FakeTime(42):
      client_id = self.SetupClient(0, memory_size=4294967296)

    with test_lib.FakeTime(45):
      self.SetupClientStartupInfo(0, boot_time=1)

    with test_lib.FakeTime(46):
      # A client startup is written as part of the Client Snapshot.
      self.SetupClient(0, last_boot_time=2)

    return client_id

  def Run(self):
    client_id = self._SetupTestClientStartupInfos()

    with test_lib.FakeTime(47):
      self.Check(
          "GetClientStartupInfos",
          args=api_client_pb2.ApiGetClientStartupInfosArgs(client_id=client_id),
      )
      self.Check(
          "GetClientStartupInfos",
          args=api_client_pb2.ApiGetClientStartupInfosArgs(
              client_id=client_id,
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
          ),
      )
      self.Check(
          "GetClientStartupInfos",
          args=api_client_pb2.ApiGetClientStartupInfosArgs(
              client_id=client_id,
              start=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  44
              ).AsMicrosecondsSinceEpoch(),
              end=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  46
              ).AsMicrosecondsSinceEpoch(),
          ),
      )
      self.Check(
          "GetClientStartupInfos",
          args=api_client_pb2.ApiGetClientStartupInfosArgs(
              client_id=client_id,
              exclude_snapshot_collections=True,
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

    self.Check(
        "GetLastClientIPAddress",
        args=api_client_pb2.ApiGetLastClientIPAddressArgs(client_id=client_id),
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
        args=api_client_pb2.ApiListClientCrashesArgs(client_id=client_id),
        replace=replace,
    )
    self.Check(
        "ListClientCrashes",
        args=api_client_pb2.ApiListClientCrashesArgs(
            client_id=client_id, count=1
        ),
        replace=replace,
    )
    self.Check(
        "ListClientCrashes",
        args=api_client_pb2.ApiListClientCrashesArgs(
            client_id=client_id, offset=1, count=1
        ),
        replace=replace,
    )


def main(argv):
  api_regression_test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
