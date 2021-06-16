#!/usr/bin/env python
"""Tests for API client and metadata-related API calls."""

from absl import app
from absl.testing import absltest

from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import test_lib


class ApiClientLibMetadataTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests metadata-related part of GRR Python API client library."""

  def testGeneratedOpenApiDescriptionIsValid(self):
    # TODO(user): Move this import to the top as soon as GitHub
    # issue #813 (https://github.com/google/grr/issues/813) is resolved.
    try:
      # pytype: disable=import-error
      # pylint: disable=g-import-not-at-top
      import openapi_spec_validator
      # pytype: enable=import-error
      # pylint: enable=g-import-not-at-top
    except ImportError:
      raise absltest.SkipTest("`openapi-spec-validator` not installed")

    openapi_dict = self.api.GetOpenApiDescription()

    # Will raise exceptions when the OpenAPI specification is invalid.
    openapi_spec_validator.validate_spec(openapi_dict)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
