#!/usr/bin/env python
from collections.abc import Callable
from typing import Optional
from unittest import mock

from absl.testing import absltest
import pkg_resources

from grr_api_client import api as grr_api
from grr_api_client import errors
from grr_response_proto.api import metadata_pb2 as api_metadata_pb2
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui.api_plugins import metadata
from grr.test_lib import skip
from grr.test_lib import testing_startup


def GetDistribution(name: str) -> Optional[pkg_resources.Distribution]:
  try:
    return pkg_resources.get_distribution(name)
  except pkg_resources.DistributionNotFound:
    return None


class VersionValidationTest(api_integration_test_lib.ApiIntegrationTest):

  @classmethod
  def setUpClass(cls):
    testing_startup.TestInit()
    super().setUpClass()

  def setUp(self):
    super().setUp()
    self._original_handler_handle = metadata.ApiGetGrrVersionHandler.Handle

  def testInitHttpApiWorks(self):
    # Should not raise.
    grr_api.InitHttp(api_endpoint=self.endpoint, validate_version=True)

  @skip.If(
      GetDistribution("grr-api-client") is None,
      reason="PIP `grr-api-client` package not available.",
  )
  def testInitHttpApiFailsForOutdatedVersion(self):
    handle = self._Handle()
    with mock.patch.object(metadata.ApiGetGrrVersionHandler, "Handle", handle):
      with self.assertRaises(errors.VersionMismatchError):
        grr_api.InitHttp(api_endpoint=self.endpoint, validate_version=True)

  def testInitHttpApiSucceedsForOutdatedVersionWithDisableValidation(self):
    handle = self._Handle()
    with mock.patch.object(metadata.ApiGetGrrVersionHandler, "Handle", handle):
      # Should not raise.
      grr_api.InitHttp(api_endpoint=self.endpoint, validate_version=False)

  def _Handle(self) -> Callable:  # pylint: disable=g-bare-generic
    this = self

    def Handle(
        self,
        args: None,
        context: Optional[api_call_context.ApiCallContext] = None,
    ) -> api_metadata_pb2.ApiGetGrrVersionResult:
      result = this._original_handler_handle(self, args, context=context)
      result.release += 1
      return result

    return Handle


if __name__ == "__main__":
  absltest.main()
