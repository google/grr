#!/usr/bin/env python
"""Base test classes for API handlers tests."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
# This import guarantees that all API-related RDF types will get imported
# (as they're all references by api_call_router).
# pylint: disable=unused-import
from grr_response_server.gui import api_call_router
# pylint: enable=unused-import
from grr.test_lib import acl_test_lib
from grr.test_lib import test_lib


class ApiCallHandlerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(ApiCallHandlerTest, self).setUp()
    # The user we use for API tests.
    self.token.username = u"api_test_user"
    acl_test_lib.CreateUser(self.token.username)


class SampleGetHandlerArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.SampleGetHandlerArgs
