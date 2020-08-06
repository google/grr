# Lint as: python3
"""Tests for API client and metadata-related API calls."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import pkg_resources

from absl import app

from grr_response_server.gui import api_integration_test_lib
from grr.test_lib import skip
from grr.test_lib import test_lib


class ApiClientLibMetadataTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests metadata-related part of GRR Python API client library."""

  @skip.If(
    "openapi-spec-validator" not in {p.key for p in pkg_resources.working_set},
    "The openapi-spec-validator module used for validating the OpenAPI "
    "specification is not installed."
  )
  def testGeneratedOpenApiDescriptionIsValid(self):
    # TODO(alexandrucosminmihai): Move this import to the top as soon as GitHub
    # issue #813 (https://github.com/google/grr/issues/813) is resolved.
    import openapi_spec_validator
    openapi_dict = self.api.GetOpenApiDescription()

    # Will raise exceptions when the OpenAPI specification is invalid.
    openapi_spec_validator.validate_spec(openapi_dict)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
