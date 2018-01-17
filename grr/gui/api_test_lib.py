#!/usr/bin/env python
"""Base test classes for API handlers tests."""


# This import guarantees that all API-related RDF types will get imported
# (as they're all references by api_call_router).
# pylint: disable=unused-import
from grr.gui import api_call_router
# pylint: enable=unused-import
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr.test_lib import test_lib


class ApiCallHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApiCallHandlerTest, self).setUp()
    # The user we use for API tests.
    self.token.username = "api_test_user"


class SampleGetHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerArgs
