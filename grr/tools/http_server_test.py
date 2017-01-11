#!/usr/bin/env python
"""Unittest for grr http server."""


import os
import threading


import portpicker
import requests

import logging

from grr.client import comms
from grr.client.client_actions import standard
from grr.lib import config_lib
from grr.lib import file_store
from grr.lib import flags
from grr.lib import front_end
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.tools import http_server


class GRRHTTPServerTest(test_lib.GRRBaseTest):
  """Test the http server."""

  @classmethod
  def setUpClass(cls):
    super(GRRHTTPServerTest, cls).setUpClass()
    # Frontend must be initialized to register all the stats counters.
    front_end.FrontendInit().RunOnce()

    # Bring up a local server for testing.
    cls.httpd = http_server.GRRHTTPServer(
        ("127.0.0.1", portpicker.PickUnusedPort()),
        http_server.GRRHTTPServerHandler)

    cls.httpd_thread = threading.Thread(target=cls.httpd.serve_forever)
    cls.httpd_thread.daemon = True
    cls.httpd_thread.start()

    cls.base_url = "http://%s:%s/" % cls.httpd.server_address

  @classmethod
  def tearDownClass(cls):
    cls.httpd.shutdown()

  def testServerPem(self):
    req = requests.get(self.base_url + "server.pem")
    self.assertEqual(req.status_code, 200)
    self.assertTrue("BEGIN CERTIFICATE" in req.content)

  def _UploadFile(self, args):
    self.client_id = self.SetupClients(1)[0]
    with test_lib.ConfigOverrider({"Client.server_urls": [self.base_url]}):
      client = comms.GRRHTTPClient(
          ca_cert=config_lib.CONFIG["CA.certificate"],
          private_key=config_lib.CONFIG.Get("Client.private_key", default=None))

      client.server_certificate = config_lib.CONFIG["Frontend.certificate"]

      def MockSendReply(_, reply):
        self.reply = reply

      @classmethod
      def FromPrivateKey(*_):
        """Returns the correct client id.

        The test framework does not generate valid client ids (which should be
        related to the client's private key. We therefore need to mock it and
        override.

        Returns:
          Correct client_id
        """
        return self.client_id

      with utils.MultiStubber(
          (standard.UploadFile, "SendReply", MockSendReply),
          (rdf_client.ClientURN, "FromPrivateKey", FromPrivateKey)):
        action = standard.UploadFile(client.client_worker)
        action.Run(args)

      return self.reply

  def testUpload(self):
    magic_string = "Hello world"

    test_file = os.path.join(self.temp_dir, "sample.txt")
    with open(test_file, "wb") as fd:
      fd.write(magic_string)

    args = rdf_client.UploadFileRequest()
    args.pathspec.path = test_file
    args.pathspec.pathtype = "OS"

    # Errors are logged on the server but not always provided to the client. We
    # check the server logs for the errors we inject.
    with test_lib.Instrument(logging, "error") as logger:
      # First do not provide a hmac at all.
      with self.assertRaises(IOError):
        self._UploadFile(args)

      self.assertRegexpMatches("HMAC not provided", str(logger.args))
      logger.args[:] = []

      # Now pass a rubbish HMAC but forget to give a policy.
      args.hmac = transfer.GetHMAC().HMAC("This is the wrong filename")
      with self.assertRaises(IOError):
        self._UploadFile(args)

      self.assertRegexpMatches("Policy not provided", str(logger.args))
      logger.args[:] = []

      # Ok - lets make an expired policy, Still wrong HMAC.
      policy = rdf_client.UploadPolicy(
          client_id=self.client_id,
          filename=args.pathspec.CollapsePath(),
          expires=1000)
      args.policy = policy.SerializeToString()

      with self.assertRaises(IOError):
        self._UploadFile(args)

      self.assertRegexpMatches("Signature did not match digest",
                               str(logger.args))
      logger.args[:] = []

      # Ok lets hmac the policy now, but its still too old.
      args.hmac = transfer.GetHMAC().HMAC(args.policy)
      with self.assertRaises(IOError):
        self._UploadFile(args)

      # Make sure the file is not written yet.
      rootdir = config_lib.CONFIG["FileUploadFileStore.root_dir"]
      target_filename = os.path.join(
          rootdir, self.client_id.Add(test_file).Path().lstrip(os.path.sep))

      self.assertNotEqual(target_filename, test_file)

      with self.assertRaises(IOError):
        open(target_filename)

      self.assertRegexpMatches("Client upload policy is too old",
                               str(logger.args))
      logger.args[:] = []

      # Lets expire the policy in the future.
      policy.expires = rdfvalue.RDFDatetime.Now() + 1000
      args.policy = policy.SerializeToString()
      args.hmac = transfer.GetHMAC().HMAC(args.policy)
      r = self._UploadFile(args)
      fs = file_store.FileUploadFileStore()
      # Make sure the file was uploaded correctly.
      fd = fs.OpenForReading(r.file_id)
      data = fd.read()
      # The stored data is actually gzip compressed.
      self.assertEqual(data, magic_string)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
