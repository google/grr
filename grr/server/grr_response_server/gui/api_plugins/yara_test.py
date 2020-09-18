#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_server import data_store
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import yara as api_yara
from grr.test_lib import testing_startup


class ApiUploadYaraSignatureHandlerTest(api_test_lib.ApiCallHandlerTest):

  @classmethod
  def setUpClass(cls):
    super(ApiUploadYaraSignatureHandlerTest, cls).setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super(ApiUploadYaraSignatureHandlerTest, self).setUp()
    self.handler = api_yara.ApiUploadYaraSignatureHandler()

  def testSignatureIsUploadedToBlobStore(self):
    signature = "rule foo { condition: true };"

    args = api_yara.ApiUploadYaraSignatureArgs()
    args.signature = signature

    blob_id = self.handler.Handle(args, context=self.context).blob_id
    blob = data_store.BLOBS.ReadBlob(blob_id)

    self.assertEqual(blob.decode("utf-8"), signature)

  def testBlobIsMarkedAsYaraSignature(self):
    args = api_yara.ApiUploadYaraSignatureArgs()
    args.signature = "rule foo { condition: false };"

    blob_id = self.handler.Handle(args, context=self.context).blob_id

    self.assertTrue(data_store.REL_DB.VerifyYaraSignatureReference(blob_id))


if __name__ == "__main__":
  absltest.main()
