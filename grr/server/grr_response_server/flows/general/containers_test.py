#!/usr/bin/env python
from absl import app

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import containers as rdf_containers
from grr_response_proto import containers_pb2
from grr_response_server.flows.general import containers
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint:mode=test


class ListContainersReturnsOnce(actions.ActionPlugin):
  """Sends a single ContainerList response."""

  in_rdfvalue = rdf_containers.ListContainersRequest
  out_rdfvalue = [rdf_containers.ListContainersResult]

  def Run(self, args: rdf_containers.ListContainersRequest) -> None:
    output = rdf_containers.ListContainersOutput()
    output.binary = "docker"
    if args.inspect_hostroot:
      output.stdout = """{"Names":"hostroot"}"""
    self.SendReply(rdf_containers.ListContainersResult(cli_outputs=[output]))


class ListContainersReturnsTwice(actions.ActionPlugin):
  """Sends more than one ContainerList response."""

  in_rdfvalue = rdf_containers.ListContainersRequest
  out_rdfvalue = [rdf_containers.ListContainersResult]

  def Run(self, args: rdf_containers.ListContainersRequest) -> None:
    self.SendReply(rdf_containers.ListContainersResult(cli_outputs=[]))
    self.SendReply(rdf_containers.ListContainersResult(cli_outputs=[]))


class ListContainersTest(flow_test_lib.FlowTestsBaseclass):
  """Tests for the ListContainers flow."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testInput(self):
    """Tests that the input is correctly passed to the client."""
    args = containers.ListContainersFlowArgs(inspect_hostroot=True)
    flow_id = flow_test_lib.StartAndRunFlow(
        containers.ListContainers,
        action_mocks.ActionMock.With(
            {"ListContainers": ListContainersReturnsOnce}
        ),
        creator=self.test_username,
        client_id=self.client_id,
        flow_args=args,
    )
    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(results[0].containers[0].names, ["hostroot"])

  def testFailsIfMultipleActionOutputs(self):
    """Tests that the flow fails if the client sends more than one response."""

    with self.assertRaisesRegex(
        RuntimeError, r".*Expected a single response.*"
    ):
      flow_test_lib.StartAndRunFlow(
          containers.ListContainers,
          action_mocks.ActionMock.With(
              {"ListContainers": ListContainersReturnsTwice}
          ),
          creator=self.test_username,
          client_id=self.client_id,
      )

  def testParseContainerList(self):
    """Tests that the flow correctly parses the container list."""

    flow_id = flow_test_lib.StartAndRunFlow(
        containers.ListContainers,
        action_mocks.ActionMock.With(
            {"ListContainers": ListContainersReturnsOnce}
        ),
        creator=self.test_username,
        client_id=self.client_id,
    )
    instance = containers.ListContainers(
        flow_test_lib.GetFlowObj(self.client_id, flow_id)
    )

    # Test crictl
    stdout = """
{
  "containers": [
    {
      "id": "test_id",
      "metadata": {
        "name": "test_name"
      },
      "image": {
        "image": "test_image"
      },
      "state": "CONTAINER_RUNNING",
      "createdAt": "1719465569878299297",
      "labels": {
        "test_label": "test_value"
      },
      "annotations": {
        "io.kubernetes.container.restartCount": "0"
      }
    }
  ]
}""".strip()
    got = instance.ParseContainerList(stdout, "crictl")
    self.assertLen(got, 1)
    self.assertEqual(got[0].container_id, "test_id")
    self.assertEqual(got[0].image_name, "test_image")
    self.assertEqual(got[0].created_at, 1719465569878299297)
    self.assertEqual(got[0].ports, [])
    self.assertEqual(got[0].names, ["test_name"])
    self.assertLen(got[0].labels, 1)
    self.assertEqual(
        got[0].labels[0],
        containers_pb2.ContainerLabel(label="test_label", value="test_value"),
    )
    self.assertEqual(
        got[0].state, containers_pb2.ContainerDetails.CONTAINER_RUNNING
    )
    self.assertEqual(
        got[0].container_cli,
        containers_pb2.ContainerDetails.ContainerCli.CRICTL,
    )

    # Test docker
    stdout = """
{"Command":"test_command","CreatedAt":"2024-06-04 04:38:19 +0000 UTC","ID":"test_id","Image":"test_image","Labels":"TEST_LABEL=test_value","LocalVolumes":"0","Mounts":"/","Names":"test_name","Networks":"host","Ports":"80/tcp, 127.0.0.1:8080-\u003e8080/tcp","RunningFor":"3 weeks ago","Size":"0B","State":"running","Status":"Up 3 weeks"}
{"Command":"another_test","CreatedAt":"2024-06-04 04:33:30 +0000 UTC","ID":"1234567","Image":"next_image","Labels":"","LocalVolumes":"5","Mounts":"123,456,789","Names":"next_test","Networks":"host","Ports":"","RunningFor":"3 weeks ago","Size":"0B","State":"running","Status":"Up 3 weeks"}
""".strip()
    got = instance.ParseContainerList(stdout=stdout, binary="docker")
    self.assertLen(got, 2)
    self.assertEqual(got[0].container_id, "test_id")
    self.assertEqual(got[0].image_name, "test_image")
    self.assertEqual(got[0].command, "test_command")
    self.assertEqual(got[0].created_at, 1717475899000000000)
    self.assertLen(got[0].ports, 2)
    self.assertEqual(got[0].names, ["test_name"])
    self.assertLen(got[0].labels, 1)
    self.assertEqual(
        got[0].labels[0],
        containers_pb2.ContainerLabel(label="TEST_LABEL", value="test_value"),
    )
    self.assertEqual(got[0].local_volumes, "0")
    self.assertEqual(got[0].mounts, ["/"])
    self.assertEqual(got[0].networks, ["host"])
    self.assertEqual(got[0].running_since, "3 weeks ago")
    self.assertEqual(
        got[0].state, containers_pb2.ContainerDetails.CONTAINER_RUNNING
    )
    self.assertEqual(got[0].status, "Up 3 weeks")
    self.assertEqual(
        got[0].container_cli, containers_pb2.ContainerDetails.DOCKER
    )

    # Test empty crictl
    stdout = """
{
  "containers": []
}""".strip()
    got = instance.ParseContainerList(stdout=stdout, binary="crictl")
    self.assertEmpty(got)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
