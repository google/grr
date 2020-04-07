#!/usr/bin/env python
# Lint as: python3
"""Unittest for grr http server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import ipaddress
import os
import socket
import threading
import time

from absl import app
import portpicker
import requests

from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import file_store
from grr_response_server.bin import frontend
from grr_response_server.databases import db
from grr_response_server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


class GRRHTTPServerTest(test_lib.GRRBaseTest):
  """Test the http server."""

  @classmethod
  def setUpClass(cls):
    super(GRRHTTPServerTest, cls).setUpClass()

    # Bring up a local server for testing.
    port = portpicker.pick_unused_port()
    ip = utils.ResolveHostnameToIP("localhost", port)
    cls.httpd = frontend.GRRHTTPServer((ip, port),
                                       frontend.GRRHTTPServerHandler)

    if ipaddress.ip_address(ip).version == 6:
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
    self.assertIn(b"BEGIN CERTIFICATE", req.content)

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
      data = open(r.stat_entry.pathspec.path, "rb").read()

      fd = file_store.OpenFile(
          db.ClientPath.FromPathSpec(self.client_id, r.stat_entry.pathspec))
      self.assertEqual(fd.read(100), data[:100])

      self.assertEqual(fd.hash_id.AsBytes(), hashlib.sha256(data).digest())

  def testClientFileFinderUploadLimit(self):
    paths = [os.path.join(self.base_path, "{**,.}/*.plist")]
    action = rdf_file_finder.FileFinderAction.Download()

    # TODO(hanuszczak): Instead of catching arbitrary runtime errors, we should
    # catch specific instance that was thrown. Unfortunately, all errors are
    # intercepted in the `MockWorker` class and converted to runtime errors.
    with self.assertRaisesRegex(RuntimeError, "exceeded network send limit"):
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
        for c, session_id in session_ids.items()
    }
    for results in results_per_client.values():
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


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
