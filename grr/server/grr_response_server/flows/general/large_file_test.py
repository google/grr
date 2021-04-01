#!/usr/bin/env python
import os

from absl.testing import absltest
import responses

from grr_response_client.client_actions import large_file as large_file_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import temp
from grr_response_server.flows.general import large_file
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import gcs_test_lib
from grr.test_lib import testing_startup


class CollectLargeFileFlowTest(flow_test_lib.FlowTestsBaseclass):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  @responses.activate
  def testRandomFile(self):
    content = os.urandom(1024)

    response = responses.Response(responses.POST, "https://foo.bar/quux")
    response.status = 201
    response.headers = {
        "Location": "https://foo.bar/norf",
    }
    responses.add(response)

    handler = gcs_test_lib.FakeUploadHandler()
    responses.add_callback(responses.PUT, "https://foo.bar/norf", handler)

    with temp.AutoTempFilePath() as temp_path:
      with open(temp_path, mode="wb") as temp_file:
        temp_file.write(content)

      self._Collect(path=temp_path, signed_url="https://foo.bar/quux")

    self.assertEqual(handler.content, content)

  def _Collect(self, path: str, signed_url: str) -> str:
    """Runs the large file collection flow.

    Args:
      path: A path to the file to collect.
      signed_url: A signed URL to the where the file should be sent to.

    Returns:
      An identifier of the flow that was created.
    """
    args = large_file.CollectLargeFileFlowArgs()
    args.signed_url = signed_url
    args.path_spec.pathtype = rdf_paths.PathSpec.PathType.OS
    args.path_spec.path = path

    action_mock = action_mocks.ActionMock.With({
        "CollectLargeFile": large_file_action.CollectLargeFileAction,
    })

    flow_id = flow_test_lib.TestFlowHelper(
        large_file.CollectLargeFileFlow.__name__,
        action_mock,
        client_id=self.client_id,
        creator=self.test_username,
        args=args)

    flow_test_lib.FinishAllFlowsOnClient(self.client_id)

    return flow_id


if __name__ == "__main__":
  absltest.main()
