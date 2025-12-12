#!/usr/bin/env python
from unittest import mock

from absl import app

from grr_response_client import client_utils_common
from grr_response_client.client_actions import containers
from grr_response_core.lib.rdfvalues import containers as rdf_containers
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class ListContainersTest(client_test_lib.EmptyActionTest):
  """Tests for the ListContainers action."""

  def testListContainers(self):
    def MockExecute(cmd, cmdargs):
      assert isinstance(cmdargs, list)

      if cmd == "/home/kubernetes/bin/crictl":
        raise FileNotFoundError("Command not found")
      elif cmd == "/usr/bin/crictl":
        return ("""{"containers":[]}""", "", 0, 0)
      elif cmd == "/usr/bin/docker":
        return ("", "", 0, 0)
      raise FileNotFoundError("Command not found")

    with mock.patch.object(
        client_utils_common, "Execute", side_effect=MockExecute
    ):
      action_request = rdf_containers.ListContainersRequest()
      results = self.ExecuteAction(containers.ListContainers, action_request)
      self.assertNotEmpty(results)
      self.assertLen(results, 2)
      self.assertIsInstance(results[0], rdf_containers.ListContainersResult)
      self.assertLen(results[0].cli_outputs, 3)
      self.assertEqual(results[0].cli_outputs[0].binary, "crictl")
      self.assertEqual(results[0].cli_outputs[0].exit_status, 2)
      self.assertEqual(results[0].cli_outputs[1].binary, "crictl")
      self.assertEqual(results[0].cli_outputs[1].exit_status, 0)
      self.assertEqual(results[0].cli_outputs[2].binary, "docker")
      self.assertEqual(results[0].cli_outputs[2].exit_status, 0)
      self.assertEmpty(results[0].cli_outputs[2].stdout)
      self.assertIsInstance(results[1], rdf_flows.GrrStatus)
      self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
      self.assertEmpty(results[1].error_message)

  def testListContainersHostroot(self):
    def MockExecute(cmd, cmdargs):
      assert isinstance(cmdargs, list)

      if cmd == "/usr/sbin/chroot":
        return ("", "", 0, 0)
      raise FileNotFoundError("Command not found")

    with mock.patch.object(
        client_utils_common, "Execute", side_effect=MockExecute
    ):
      action_request = rdf_containers.ListContainersRequest(
          inspect_hostroot=True
      )
      results = self.ExecuteAction(containers.ListContainers, action_request)
      self.assertNotEmpty(results)
      self.assertLen(results, 2)
      self.assertIsInstance(results[0], rdf_containers.ListContainersResult)
      self.assertLen(results[0].cli_outputs, 3)
      self.assertEqual(results[0].cli_outputs[0].binary, "crictl")
      self.assertEqual(results[0].cli_outputs[0].exit_status, 0)
      self.assertEqual(results[0].cli_outputs[1].binary, "crictl")
      self.assertEqual(results[0].cli_outputs[1].exit_status, 0)
      self.assertEqual(results[0].cli_outputs[2].binary, "docker")
      self.assertEqual(results[0].cli_outputs[2].exit_status, 0)
      self.assertIsInstance(results[1], rdf_flows.GrrStatus)
      self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
      self.assertEmpty(results[1].error_message)

  def testListContainersError(self):
    def MockExecute(cmd, cmdargs):
      del cmd, cmdargs
      raise RuntimeError("Unexpected error")

    with mock.patch.object(
        client_utils_common, "Execute", side_effect=MockExecute
    ):
      action_request = rdf_containers.ListContainersRequest()
      results = self.ExecuteAction(containers.ListContainers, action_request)
      self.assertNotEmpty(results)
      self.assertLen(results, 1)
      self.assertIsInstance(results[0], rdf_flows.GrrStatus)
      self.assertEqual(
          rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR, results[0].status
      )
      self.assertNotEmpty(results[0].error_message)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
