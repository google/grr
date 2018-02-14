#!/usr/bin/env python
"""Unittest for grr http server."""

import hashlib
import logging
import os
import socket
import threading


import ipaddr
import portpicker
import requests

from google.protobuf import json_format

from grr import config
from grr_response_client import comms
from grr_response_client.client_actions import standard
from grr_response_client.components.rekall_support import rekall_types as rdf_rekall_types
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import aff4
from grr.server import file_store
from grr.server import flow
from grr.server import front_end
from grr.server.aff4_objects import filestore
from grr.server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import rekall_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks
from grr.tools import frontend


class GRRHTTPServerTest(test_lib.GRRBaseTest):
  """Test the http server."""

  @classmethod
  def setUpClass(cls):
    super(GRRHTTPServerTest, cls).setUpClass()

    cls.config_overrider = test_lib.ConfigOverrider({
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__
    })
    cls.config_overrider.Start()

    # Frontend must be initialized to register all the stats counters.
    front_end.FrontendInit().RunOnce()

    # Bring up a local server for testing.
    port = portpicker.PickUnusedPort()
    ip = utils.ResolveHostnameToIP("localhost", port)
    cls.httpd = frontend.GRRHTTPServer((ip, port),
                                       frontend.GRRHTTPServerHandler)

    if ipaddr.IPAddress(ip).version == 6:
      cls.address_family = socket.AF_INET6
      cls.base_url = "http://[%s]:%d/" % (ip, port)
    else:
      cls.address_family = socket.AF_INET
      cls.base_url = "http://%s:%d/" % (ip, port)

    cls.httpd_thread = threading.Thread(target=cls.httpd.serve_forever)
    cls.httpd_thread.daemon = True
    cls.httpd_thread.start()

  @classmethod
  def tearDownClass(cls):
    cls.httpd.shutdown()
    cls.config_overrider.Stop()

  def setUp(self):
    super(GRRHTTPServerTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def testServerPem(self):
    req = requests.get(self.base_url + "server.pem")
    self.assertEqual(req.status_code, 200)
    self.assertTrue("BEGIN CERTIFICATE" in req.content)

  def _UploadFile(self, args):
    with test_lib.ConfigOverrider({"Client.server_urls": [self.base_url]}):
      client = comms.GRRHTTPClient(
          ca_cert=config.CONFIG["CA.certificate"],
          private_key=config.CONFIG.Get("Client.private_key", default=None),
          worker_cls=worker_mocks.DisabledNannyClientWorker)

      client.server_certificate = config.CONFIG["Frontend.certificate"]

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
      hmac = args.upload_token.GetHMAC()
      args.upload_token.hmac = hmac.HMAC("This is the wrong filename")
      with self.assertRaises(IOError):
        self._UploadFile(args)

      self.assertRegexpMatches("Policy not provided", str(logger.args))
      logger.args[:] = []

      # Ok - lets make an expired policy, Still wrong HMAC.
      policy = rdf_client.UploadPolicy(client_id=self.client_id, expires=1000)
      args.upload_token.SetPolicy(policy)

      with self.assertRaises(IOError):
        self._UploadFile(args)

      self.assertRegexpMatches("Signature did not match digest", str(
          logger.args))
      logger.args[:] = []

      # Ok lets hmac the policy now, but its still too old.
      args.upload_token.SetPolicy(policy)
      with self.assertRaises(IOError):
        self._UploadFile(args)

      # Make sure the file is not written yet.
      rootdir = config.CONFIG["FileUploadFileStore.root_dir"]
      target_filename = os.path.join(
          rootdir,
          self.client_id.Add(test_file).Path().lstrip(os.path.sep))

      self.assertNotEqual(target_filename, test_file)

      with self.assertRaises(IOError):
        open(target_filename)

      self.assertRegexpMatches("Client upload policy is too old",
                               str(logger.args))
      logger.args[:] = []

      # Lets expire the policy in the future.
      policy.expires = rdfvalue.RDFDatetime.Now() + 1000
      args.upload_token.SetPolicy(policy)
      args.upload_token.GenerateHMAC()
      r = self._UploadFile(args)
      fs = file_store.FileUploadFileStore()
      # Make sure the file was uploaded correctly.
      fd = fs.OpenForReading(r.file_id)
      data = fd.read()
      self.assertEqual(data, magic_string)

  def _RunClientFileFinder(self,
                           paths,
                           action,
                           network_bytes_limit=None,
                           client_id=None):
    client_id = client_id or self.SetupClient(0)
    with test_lib.ConfigOverrider({"Client.server_urls": [self.base_url]}):
      client = comms.GRRHTTPClient(
          ca_cert=config.CONFIG["CA.certificate"],
          private_key=config.CONFIG.Get("Client.private_key", default=None),
          worker_cls=worker_mocks.DisabledNannyClientWorker)
      client.client_worker = worker_mocks.FakeThreadedWorker(client=client)
      client.server_certificate = config.CONFIG["Frontend.certificate"]

      for s in flow_test_lib.TestFlowHelper(
          file_finder.ClientFileFinder.__name__,
          action_mocks.ClientFileFinderClientMock(
              client_worker=client.client_worker),
          client_id=client_id,
          paths=paths,
          pathtype=rdf_paths.PathSpec.PathType.OS,
          action=action,
          process_non_regular_files=True,
          network_bytes_limit=network_bytes_limit,
          token=self.token):
        session_id = s

      return session_id

  def testClientFileFinderUpload(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    session_id = self._RunClientFileFinder(paths, action)
    collection = flow.GRRFlow.ResultCollectionForFID(session_id)
    results = list(collection)
    self.assertEqual(len(results), 4)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertItemsEqual(relpaths, [
        "History.plist", "History.xml.plist", "test.plist",
        "parser_test/com.google.code.grr.plist"
    ])

    for r in results:
      aff4_obj = aff4.FACTORY.Open(
          r.stat_entry.pathspec.AFF4Path(self.client_id), token=self.token)
      data = open(r.stat_entry.pathspec.path, "rb").read()
      self.assertEqual(aff4_obj.Read(100), data[:100])

      for hash_obj in [
          r.uploaded_file.hash,
          aff4_obj.Get(aff4_obj.Schema.HASH)
      ]:
        self.assertEqual(hash_obj.md5, hashlib.md5(data).hexdigest())
        self.assertEqual(hash_obj.sha1, hashlib.sha1(data).hexdigest())
        self.assertEqual(hash_obj.sha256, hashlib.sha256(data).hexdigest())

  def testClientFileFinderUploadLimit(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    with self.assertRaises(RuntimeError) as e:
      self._RunClientFileFinder(paths, action, network_bytes_limit=2000)
      self.assertIn("Action exceeded network send limit.", e.exception.message)

  def testClientFileFinderUploadBound(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download(
        oversized_file_policy="DOWNLOAD_TRUNCATED", max_size=300)

    session_id = self._RunClientFileFinder(paths, action)
    collection = flow.GRRFlow.ResultCollectionForFID(session_id)
    results = list(collection)
    self.assertEqual(len(results), 4)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertItemsEqual(relpaths, [
        "History.plist", "History.xml.plist", "test.plist",
        "parser_test/com.google.code.grr.plist"
    ])

    for r in results:
      aff4_obj = aff4.FACTORY.Open(
          r.stat_entry.pathspec.AFF4Path(self.client_id), token=self.token)
      data = aff4_obj.read()
      self.assertLessEqual(len(data), 300)
      self.assertEqual(data,
                       open(r.stat_entry.pathspec.path, "rb").read(len(data)))

  def testClientFileFinderUploadSkip(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download(
        oversized_file_policy="SKIP", max_size=300)

    session_id = self._RunClientFileFinder(paths, action)
    collection = flow.GRRFlow.ResultCollectionForFID(session_id)
    results = list(collection)

    skipped = []
    uploaded = []
    for result in results:
      if result.uploaded_file.file_id:
        uploaded.append(result)
      else:
        skipped.append(result)

    self.assertEqual(len(uploaded), 2)
    self.assertEqual(len(skipped), 2)

    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in uploaded
    ]
    self.assertItemsEqual(relpaths, ["History.plist", "test.plist"])

    for r in uploaded:
      aff4_obj = aff4.FACTORY.Open(
          r.stat_entry.pathspec.AFF4Path(self.client_id), token=self.token)
      self.assertEqual(
          aff4_obj.Read(100),
          open(r.stat_entry.pathspec.path, "rb").read(100))

  def testClientFileFinderFilestoreIntegration(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    client_ids = self.SetupClients(2)
    session_ids = {
        c: self._RunClientFileFinder(paths, action, client_id=c)
        for c in client_ids
    }
    collections = {
        c: flow.GRRFlow.ResultCollectionForFID(session_id)
        for c, session_id in session_ids.iteritems()
    }
    for client_id, collection in collections.iteritems():
      results = list(collection)
      self.assertEqual(len(results), 4)
      relpaths = [
          os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
          for p in results
      ]
      self.assertItemsEqual(relpaths, [
          "History.plist", "History.xml.plist", "test.plist",
          "parser_test/com.google.code.grr.plist"
      ])

      for r in results:
        aff4_obj = aff4.FACTORY.Open(
            r.stat_entry.pathspec.AFF4Path(client_id), token=self.token)

        # When files are uploaded to the server directly, we should get a
        # FileStoreAFF4Object.
        self.assertIsInstance(aff4_obj, file_store.FileStoreAFF4Object)
        # There is a STAT entry.
        self.assertTrue(aff4_obj.Get(aff4_obj.Schema.STAT))

        # Make sure the HashFileStore has references to this file for
        # all hashes.
        hashes = aff4_obj.Get(aff4_obj.Schema.HASH)
        fs = filestore.HashFileStore
        md5_refs = list(fs.GetReferencesMD5(hashes.md5, token=self.token))
        self.assertIn(aff4_obj.urn, md5_refs)
        sha1_refs = list(fs.GetReferencesSHA1(hashes.sha1, token=self.token))
        self.assertIn(aff4_obj.urn, sha1_refs)
        sha256_refs = list(
            fs.GetReferencesSHA256(hashes.sha256, token=self.token))
        self.assertIn(aff4_obj.urn, sha256_refs)

        # Open the file inside the file store.
        urn, _ = fs(None, token=self.token).CheckHashes(hashes).next()
        filestore_fd = aff4.FACTORY.Open(urn, token=self.token)
        # This is a FileStoreAFF4Object too.
        self.assertIsInstance(filestore_fd, file_store.FileStoreAFF4Object)
        # No STAT object attached.
        self.assertFalse(filestore_fd.Get(filestore_fd.Schema.STAT))

  def testRekallProfiles(self):
    req = requests.get(self.base_url + "rekall_profiles")
    self.assertEqual(req.status_code, 500)

    req = requests.get(self.base_url + "rekall_profiles/v1.0")
    self.assertEqual(req.status_code, 500)

    known_profile = "F8E2A8B5C9B74BF4A6E4A48F180099942"
    unknown_profile = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"

    req = requests.get(
        self.base_url + "rekall_profiles/v1.0/nt/GUID/" + unknown_profile)
    self.assertEqual(req.status_code, 404)

    req = requests.get(
        self.base_url + "rekall_profiles/v1.0/nt/GUID/" + known_profile)
    self.assertEqual(req.status_code, 200)

    pb = rdf_rekall_types.RekallProfile.protobuf()
    json_format.Parse(req.content.lstrip(")]}'\n"), pb)
    profile = rdf_rekall_types.RekallProfile.FromSerializedString(
        pb.SerializeToString())
    self.assertEqual(profile.name, "nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942")
    self.assertEqual(profile.version, "v1.0")
    self.assertEqual(profile.data[:2], "\x1f\x8b")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
