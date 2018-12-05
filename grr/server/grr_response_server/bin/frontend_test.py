#!/usr/bin/env python
"""Unittest for grr http server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import os
import socket
import threading
import time


from future.builtins import range
from future.utils import iteritems
import ipaddr
import portpicker
import requests

from google.protobuf import json_format

from grr_response_core.lib import flags
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import filestore
from grr_response_server.bin import frontend
from grr_response_server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rekall_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


@db_test_lib.DualDBTest
class GRRHTTPServerTest(test_lib.GRRBaseTest):
  """Test the http server."""

  @classmethod
  def setUpClass(cls):
    super(GRRHTTPServerTest, cls).setUpClass()

    cls.config_overrider = test_lib.ConfigOverrider({
        "Rekall.profile_server":
            rekall_test_lib.TestRekallRepositoryProfileServer.__name__,
    })
    cls.config_overrider.Start()

    # Bring up a local server for testing.
    port = portpicker.pick_unused_port()
    ip = utils.ResolveHostnameToIP("localhost", port)
    cls.httpd = frontend.GRRHTTPServer((ip, port),
                                       frontend.GRRHTTPServerHandler)

    if ipaddr.IPAddress(ip).version == 6:
      cls.address_family = socket.AF_INET6
      cls.base_url = "http://[%s]:%d/" % (ip, port)
    else:
      cls.address_family = socket.AF_INET
      cls.base_url = "http://%s:%d/" % (ip, port)

    cls.httpd_thread = threading.Thread(
        name="GRRHTTPServerTestThread", target=cls.httpd.serve_forever)
    cls.httpd_thread.daemon = True
    cls.httpd_thread.start()

  @classmethod
  def tearDownClass(cls):
    cls.config_overrider.Stop()
    cls.httpd.Shutdown()
    cls.httpd_thread.join()

  def setUp(self):
    super(GRRHTTPServerTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def tearDown(self):
    super(GRRHTTPServerTest, self).tearDown()

    # Wait until all pending http requests have been handled.
    for _ in range(100):
      if frontend.GRRHTTPServerHandler.active_counter == 0:
        return
      time.sleep(0.01)
    self.fail("HTTP server thread did not shut down in time.")

  def testServerPem(self):
    req = requests.get(self.base_url + "server.pem")
    self.assertEqual(req.status_code, 200)
    self.assertIn("BEGIN CERTIFICATE", req.content)

  def _RunClientFileFinder(self,
                           paths,
                           action,
                           network_bytes_limit=None,
                           client_id=None):
    client_id = client_id or self.SetupClient(0)
    with test_lib.ConfigOverrider({"Client.server_urls": [self.base_url]}):
      session_id = flow_test_lib.TestFlowHelper(
          file_finder.ClientFileFinder.__name__,
          action_mocks.ClientFileFinderClientMock(
              client_worker=worker_mocks.FakeClientWorker()),
          client_id=client_id,
          paths=paths,
          pathtype=rdf_paths.PathSpec.PathType.OS,
          action=action,
          process_non_regular_files=True,
          network_bytes_limit=network_bytes_limit,
          token=self.token)

      return session_id

  def testClientFileFinderUpload(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    session_id = self._RunClientFileFinder(paths, action)
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertLen(results, 5)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertCountEqual(relpaths, [
        "History.plist", "History.xml.plist", "test.plist",
        "parser_test/com.google.code.grr.plist",
        "parser_test/InstallHistory.plist"
    ])

    for r in results:
      aff4_obj = aff4.FACTORY.Open(
          r.stat_entry.pathspec.AFF4Path(self.client_id), token=self.token)
      data = open(r.stat_entry.pathspec.path, "rb").read()
      self.assertEqual(aff4_obj.Read(100), data[:100])

      if data_store.RelationalDBReadEnabled(category="filestore"):
        fd = file_store.OpenFile(
            db.ClientPath.FromPathSpec(self.client_id.Basename(),
                                       r.stat_entry.pathspec))
        self.assertEqual(fd.read(100), data[:100])

        self.assertEqual(fd.hash_id.AsBytes(), hashlib.sha256(data).digest())
      else:
        hash_obj = data_store_utils.GetFileHashEntry(aff4_obj)
        self.assertEqual(hash_obj.sha1, hashlib.sha1(data).hexdigest())
        self.assertEqual(hash_obj.sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(hash_obj.md5, hashlib.md5(data).hexdigest())

  def testClientFileFinderUploadLimit(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    # TODO(hanuszczak): Instead of catching arbitrary runtime errors, we should
    # catch specific instance that was thrown. Unfortunately, all errors are
    # intercepted in the `MockWorker` class and converted to runtime errors.
    with self.assertRaisesRegexp(RuntimeError, "exceeded network send limit"):
      with test_lib.SuppressLogs():
        self._RunClientFileFinder(paths, action, network_bytes_limit=1500)

  def testClientFileFinderUploadBound(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download(
        oversized_file_policy="DOWNLOAD_TRUNCATED", max_size=300)

    session_id = self._RunClientFileFinder(paths, action)
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)
    self.assertLen(results, 5)
    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in results
    ]
    self.assertCountEqual(relpaths, [
        "History.plist", "History.xml.plist", "test.plist",
        "parser_test/com.google.code.grr.plist",
        "parser_test/InstallHistory.plist"
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
    results = flow_test_lib.GetFlowResults(self.client_id, session_id)

    skipped = []
    uploaded = []
    for result in results:
      if result.HasField("transferred_file"):
        uploaded.append(result)
      else:
        skipped.append(result)

    self.assertLen(uploaded, 2)
    self.assertLen(skipped, 3)

    relpaths = [
        os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
        for p in uploaded
    ]
    self.assertCountEqual(relpaths, ["History.plist", "test.plist"])

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
    results_per_client = {
        c: flow_test_lib.GetFlowResults(c, session_id)
        for c, session_id in iteritems(session_ids)
    }
    for client_id, results in iteritems(results_per_client):
      self.assertLen(results, 5)
      relpaths = [
          os.path.relpath(p.stat_entry.pathspec.path, self.base_path)
          for p in results
      ]
      self.assertCountEqual(relpaths, [
          "History.plist", "History.xml.plist", "test.plist",
          "parser_test/com.google.code.grr.plist",
          "parser_test/InstallHistory.plist"
      ])

      for r in results:
        aff4_obj = aff4.FACTORY.Open(
            r.stat_entry.pathspec.AFF4Path(client_id), token=self.token)

        # When files are uploaded to the server they are stored as VFSBlobImage.
        self.assertIsInstance(aff4_obj, aff4_grr.VFSBlobImage)
        # There is a STAT entry.
        self.assertTrue(aff4_obj.Get(aff4_obj.Schema.STAT))

        # Make sure the HashFileStore has references to this file for
        # all hashes.
        hash_entry = data_store_utils.GetFileHashEntry(aff4_obj)
        fs = filestore.HashFileStore
        md5_refs = list(fs.GetReferencesMD5(hash_entry.md5, token=self.token))
        self.assertIn(aff4_obj.urn, md5_refs)
        sha1_refs = list(
            fs.GetReferencesSHA1(hash_entry.sha1, token=self.token))
        self.assertIn(aff4_obj.urn, sha1_refs)
        sha256_refs = list(
            fs.GetReferencesSHA256(hash_entry.sha256, token=self.token))
        self.assertIn(aff4_obj.urn, sha256_refs)

        # Open the file inside the file store.
        urn, _ = fs(None, token=self.token).CheckHashes([hash_entry]).next()
        filestore_fd = aff4.FACTORY.Open(urn, token=self.token)
        # This is a VFSBlobImage too.
        self.assertIsInstance(filestore_fd, aff4_grr.VFSBlobImage)
        # No STAT object attached.
        self.assertFalse(filestore_fd.Get(filestore_fd.Schema.STAT))

  def testRekallProfiles(self):
    session = requests.Session()
    req = session.get(self.base_url + "rekall_profiles")
    self.assertEqual(req.status_code, 500)

    req = session.get(self.base_url + "rekall_profiles/v1.0")
    self.assertEqual(req.status_code, 500)
    req.connection.close()

    known_profile = "F8E2A8B5C9B74BF4A6E4A48F180099942"
    unknown_profile = "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"

    req = session.get(self.base_url + "rekall_profiles/v1.0/nt/GUID/" +
                      unknown_profile)
    self.assertEqual(req.status_code, 404)
    req.connection.close()

    req = session.get(self.base_url + "rekall_profiles/v1.0/nt/GUID/" +
                      known_profile)
    self.assertEqual(req.status_code, 200)
    data = req.content
    req.connection.close()

    pb = rdf_rekall_types.RekallProfile.protobuf()
    json_format.Parse(data.lstrip(")]}'\n"), pb)
    profile = rdf_rekall_types.RekallProfile.FromSerializedString(
        pb.SerializeToString())
    self.assertEqual(profile.name, "nt/GUID/F8E2A8B5C9B74BF4A6E4A48F180099942")
    self.assertEqual(profile.version, "v1.0")
    self.assertEqual(profile.data[:2], b"\x1f\x8b")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
