#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from grr_api_client import errors
from grr_response_core.lib import flags
from grr_response_proto.api import client_pb2
from grr_response_proto.api import vfs_pb2
from grr_response_proto.api.root import user_management_pb2
from grr_response_server.bin import api_shell_raw_access_lib
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class RawConnectorTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(RawConnectorTest, self).setUp()
    self.connector = api_shell_raw_access_lib.RawConnector(
        token=self.token, page_size=10)

  def testCorrectlyCallsGeneralMethod(self):
    self.SetupClients(10)

    args = client_pb2.ApiSearchClientsArgs(query=".")
    result = self.connector.SendRequest("SearchClients", args=args)
    self.assertLen(result.items, 10)

  def testCorrectlyCallsStreamingMethod(self):
    client_id = self.SetupClients(1)[0]
    fixture_test_lib.ClientFixture(client_id, self.token)

    args = vfs_pb2.ApiGetFileBlobArgs(
        client_id=client_id.Basename(), file_path="fs/tsk/c/bin/rbash")
    out = io.BytesIO()
    self.connector.SendStreamingRequest("GetFileBlob", args).WriteToStream(out)
    self.assertEqual(out.getvalue(), "Hello world")

  def testCorrectlyCallsRootGeneralMethod(self):
    acl_test_lib.CreateUser(self.token.username)

    args = user_management_pb2.ApiDeleteGrrUserArgs(
        username=self.token.username)
    self.connector.SendRequest("DeleteGrrUser", args)

  def testCorrectlyCallsAmbiguouslyNamedMethod(self):
    acl_test_lib.CreateUser(self.token.username)

    # Here arguments are provided, so root router is correctly chosen.
    args = user_management_pb2.ApiGetGrrUserArgs(username="blah")
    with self.assertRaises(errors.ResourceNotFoundError):
      self.connector.SendRequest("GetGrrUser", args)

    # Here no arguments are provided, so non-root router is correctly chosen.
    result = self.connector.SendRequest("GetGrrUser", None)
    self.assertEqual(result.username, self.token.username)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
