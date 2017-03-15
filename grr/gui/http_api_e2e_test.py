#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""End-to-end tests for HTTP API.

HTTP API plugins are tested with their own dedicated unit-tests that are
protocol- and server-independent. Tests in this file test the full GRR server
stack with regards to the HTTP API.
"""

import hashlib
import json
import os
import StringIO
import zipfile

import portpicker
import requests

import logging

from grr_api_client import api as grr_api
from grr.gui import api_auth_manager
from grr.gui import webauth
from grr.gui import wsgiapp
from grr.gui import wsgiapp_testlib
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.flows.general import file_finder
from grr.lib.flows.general import processes
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import file_finder as rdf_file_finder
from grr.proto import api_pb2
from grr.proto import jobs_pb2


class ApiE2ETest(test_lib.GRRBaseTest):
  """Base class for all API E2E tests."""

  def setUp(self):
    super(ApiE2ETest, self).setUp()

    api_auth_manager.APIACLInit.InitApiAuthManager()
    self.token.username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    self.port = HTTPApiEndToEndTestProgram.server_port
    self.endpoint = "http://localhost:%s" % self.port
    self.api = grr_api.InitHttp(api_endpoint=self.endpoint)


class ApiE2ETestLoader(test_lib.GRRTestLoader):
  """Load only API E2E test cases."""
  base_class = ApiE2ETest


class HTTPApiEndToEndTestProgram(test_lib.GrrTestProgram):

  server_port = None

  def setUp(self):
    super(HTTPApiEndToEndTestProgram, self).setUp()

    # Set up HTTP server
    port = portpicker.PickUnusedPort()
    HTTPApiEndToEndTestProgram.server_port = port
    logging.info("Picked free AdminUI port for HTTP %d.", port)

    self.trd = wsgiapp_testlib.ServerThread(port)
    self.trd.StartAndWaitUntilServing()


class ApiClientLibFlowTest(ApiE2ETest):
  """Tests flows-related part of GRR Python API client library."""

  def testSearchWithNoClients(self):
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testSearchClientsWith2Clients(self):
    client_urns = sorted(self.SetupClients(2))

    clients = sorted(
        self.api.SearchClients(query="."), key=lambda c: c.client_id)
    self.assertEqual(len(clients), 2)

    for i in range(2):
      self.assertEqual(clients[i].client_id, client_urns[i].Basename())
      self.assertEqual(clients[i].data.urn, client_urns[i])

  def testListFlowsFromClientRef(self):
    client_urn = self.SetupClients(1)[0]
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)

    flows = list(self.api.Client(client_id=client_urn.Basename()).ListFlows())

    self.assertEqual(len(flows), 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_urn.Basename())
    self.assertEqual(flows[0].data.urn, flow_urn)

  def testListFlowsFromClientObject(self):
    client_urn = self.SetupClients(1)[0]
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    flows = list(client.ListFlows())

    self.assertEqual(len(flows), 1)
    self.assertEqual(flows[0].client_id, client_urn.Basename())
    self.assertEqual(flows[0].flow_id, flow_urn.Basename())
    self.assertEqual(flows[0].data.urn, flow_urn)

  def testCreateFlowFromClientRef(self):
    client_urn = self.SetupClients(1)[0]
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data.urn, token=self.token)
    self.assertEqual(result_flow_obj.args, args)

  def testCreateFlowFromClientObject(self):
    client_urn = self.SetupClients(1)[0]
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    result_flow = client.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data.urn, token=self.token)
    self.assertEqual(result_flow_obj.args, args)


class ApiClientLibVfsTest(ApiE2ETest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibVfsTest, self).setUp()
    self.client_urn = self.SetupClients(1)[0]
    test_lib.ClientFixture(self.client_urn, self.token)

  def testGetFileFromRef(self):
    file_ref = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads/a.txt")
    self.assertEqual(file_ref.path, "fs/os/c/Downloads/a.txt")

    file_obj = file_ref.Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads/a.txt")
    self.assertFalse(file_obj.is_directory)
    self.assertEqual(file_obj.data.name, "a.txt")

  def testGetFileForDirectory(self):
    file_obj = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs/os/c/Downloads").Get()
    self.assertEqual(file_obj.path, "fs/os/c/Downloads")
    self.assertTrue(file_obj.is_directory)

  def testListFiles(self):
    files_iter = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads").ListFiles()
    files_list = list(files_iter)

    self.assertEqual(
        sorted(f.data.name for f in files_list),
        sorted(
            [u"a.txt", u"b.txt", u"c.txt", u"d.txt", u"sub1", u"中国新闻网新闻中.txt"]))

  def testGetBlob(self):
    out = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/tsk/c/bin/rbash").GetBlob().WriteToStream(out)

    self.assertEqual(out.getvalue(), "Hello world")

  def testGetFilesArchive(self):
    zip_stream = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/tsk/c/bin").GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertEqual(
        sorted(namelist),
        sorted([
            "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/rbash",
            "vfs_C_1000000000000000_fs_tsk_c_bin/fs/tsk/c/bin/bash"
        ]))

  def testGetVersionTimes(self):
    vtimes = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads/a.txt").GetVersionTimes()
    self.assertEqual(len(vtimes), 1)

  def testRefresh(self):
    operation = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads").Refresh()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testCollect(self):
    operation = self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs/os/c/Downloads/a.txt").Collect()
    self.assertTrue(operation.operation_id)
    self.assertEqual(operation.GetState(), operation.STATE_RUNNING)

  def testGetTimeline(self):
    timeline = self.api.Client(
        client_id=self.client_urn.Basename()).File("fs").GetTimeline()
    self.assertTrue(timeline)
    for item in timeline:
      self.assertTrue(isinstance(item, api_pb2.ApiVfsTimelineItem))

  def testGetTimelineAsCsv(self):
    out = StringIO.StringIO()
    self.api.Client(client_id=self.client_urn.Basename()).File(
        "fs").GetTimelineAsCsv().WriteToStream(out)
    self.assertTrue(out.getvalue())


class ApiClientLibLabelsTest(ApiE2ETest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibLabelsTest, self).setUp()
    self.client_urn = self.SetupClients(1)[0]

  def testAddLabels(self):
    client_ref = self.api.Client(client_id=self.client_urn.Basename())
    self.assertEqual(list(client_ref.Get().data.labels), [])

    with test_lib.FakeTime(42):
      client_ref.AddLabels(["foo", "bar"])

    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            jobs_pb2.AFF4ObjectLabel(
                name="bar", owner=self.token.username, timestamp=42000000),
            jobs_pb2.AFF4ObjectLabel(
                name="foo", owner=self.token.username, timestamp=42000000)
        ])

  def testRemoveLabels(self):
    with test_lib.FakeTime(42):
      with aff4.FACTORY.Open(
          self.client_urn,
          aff4_type=aff4_grr.VFSGRRClient,
          mode="rw",
          token=self.token) as client_obj:
        client_obj.AddLabels("bar", "foo")

    client_ref = self.api.Client(client_id=self.client_urn.Basename())
    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            jobs_pb2.AFF4ObjectLabel(
                name="bar", owner=self.token.username, timestamp=42000000),
            jobs_pb2.AFF4ObjectLabel(
                name="foo", owner=self.token.username, timestamp=42000000)
        ])

    client_ref.RemoveLabels(["foo"])
    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            jobs_pb2.AFF4ObjectLabel(
                name="bar", owner=self.token.username, timestamp=42000000)
        ])


class CSRFProtectionTest(ApiE2ETest):
  """Tests GRR's CSRF protection logic for the HTTP API."""

  def setUp(self):
    super(CSRFProtectionTest, self).setUp()

    self.base_url = self.endpoint

  def testGETRequestWithoutCSRFTokenAndRequestedWithHeaderSucceeds(self):
    response = requests.get(self.base_url + "/api/config")
    self.assertEquals(response.status_code, 200)
    # Assert XSSI protection is in place.
    self.assertEquals(response.text[:5], ")]}'\n")

  def testHEADRequestForGETUrlWithoutTokenAndRequestedWithHeaderSucceeds(self):
    response = requests.head(self.base_url + "/api/config")
    self.assertEquals(response.status_code, 200)

  def testHEADRequestNotEnabledForPOSTUrls(self):
    response = requests.head(self.base_url + "/api/clients/labels/add")
    self.assertEquals(response.status_code, 405)

  def testHEADRequestNotEnabledForDeleteUrls(self):
    response = requests.head(self.base_url +
                             "/api/users/me/notifications/pending/0")
    self.assertEquals(response.status_code, 405)

  def testPOSTRequestWithoutCSRFTokenFails(self):
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}

    response = requests.post(
        self.base_url + "/api/clients/labels/add", data=json.dumps(data))

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPOSTRequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/clients/labels/add",
        data=json.dumps(data),
        cookies=cookies)

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPOSTRequestWithCSRFTokenInHeadersAndCookiesSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies)
    self.assertEquals(response.status_code, 200)

  def testPOSTRequestFailsIfCSRFTokenIsExpired(self):
    with test_lib.FakeTime(rdfvalue.RDFDatetime().FromSecondsFromEpoch(42)):
      index_response = requests.get(self.base_url)
      csrf_token = index_response.cookies.get("csrftoken")

      headers = {"x-csrftoken": csrf_token}
      data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
      cookies = {"csrftoken": csrf_token}

      response = requests.post(
          self.base_url + "/api/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies)
      self.assertEquals(response.status_code, 200)

    # This should still succeed as we use strict check in wsgiapp.py:
    # current_time - token_time > CSRF_TOKEN_DURATION.microseconds
    with test_lib.FakeTime(rdfvalue.RDFDatetime().FromSecondsFromEpoch(42) +
                           wsgiapp.CSRF_TOKEN_DURATION.seconds):
      response = requests.post(
          self.base_url + "/api/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies)
      self.assertEquals(response.status_code, 200)

    with test_lib.FakeTime(rdfvalue.RDFDatetime().FromSecondsFromEpoch(42) +
                           wsgiapp.CSRF_TOKEN_DURATION.seconds + 1):
      response = requests.post(
          self.base_url + "/api/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies)
      self.assertEquals(response.status_code, 403)
      self.assertTrue("Expired CSRF token" in response.text)

  def testPOSTRequestFailsIfCSRFTokenIsMalformed(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token + "BLAH"}
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies)
    self.assertEquals(response.status_code, 403)
    self.assertTrue("Malformed" in response.text)

  def testPOSTRequestFailsIfCSRFTokenDoesNotMatch(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    # This changes the default test username, meaning that encoded CSRF
    # token and the token corresponding to the next requests's user won't
    # match.
    webauth.WEBAUTH_MANAGER.SetUserName("someotheruser")
    response = requests.post(
        self.base_url + "/api/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies)
    self.assertEquals(response.status_code, 403)
    self.assertTrue("Non-matching" in response.text)

  def testDELETERequestWithoutCSRFTokenFails(self):
    response = requests.delete(self.base_url +
                               "/api/users/me/notifications/pending/0")

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testDELETERequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    cookies = {"csrftoken": csrf_token}

    response = requests.delete(
        self.base_url + "/api/users/me/notifications/pending/0",
        cookies=cookies)

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testDELETERequestWithCSRFTokenInCookiesAndHeadersSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    cookies = {"csrftoken": csrf_token}

    response = requests.delete(
        self.base_url + "/api/users/me/notifications/pending/0",
        headers=headers,
        cookies=cookies)

    self.assertEquals(response.status_code, 200)

  def testPATCHRequestWithoutCSRFTokenFails(self):
    response = requests.patch(self.base_url + "/api/hunts/H:123456")

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPATCHRequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    cookies = {"csrftoken": csrf_token}

    response = requests.patch(
        self.base_url + "/api/hunts/H:123456", cookies=cookies)

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPATCHRequestWithCSRFTokenInCookiesAndHeadersSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    cookies = {"csrftoken": csrf_token}

    response = requests.patch(
        self.base_url + "/api/hunts/H:123456", headers=headers, cookies=cookies)

    # We consider 404 to be a normal response here.
    # Hunt H:123456 doesn't exist.
    self.assertEquals(response.status_code, 404)

  def testGetPendingUserNotificationCountMethodRefreshesCSRFToken(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    # Check that calling GetGrrUser method doesn't update the cookie.
    get_user_response = requests.get(self.base_url + "/api/users/me")
    csrf_token_2 = get_user_response.cookies.get("csrftoken")

    self.assertIsNone(csrf_token_2)

    # Check that calling GetPendingUserNotificationsCount refreshes the
    # token.
    notifications_response = requests.get(
        self.base_url + "/api/users/me/notifications/pending/count")
    csrf_token_3 = notifications_response.cookies.get("csrftoken")

    self.assertTrue(csrf_token_3)
    self.assertNotEqual(csrf_token, csrf_token_3)


class ApiCallRobotRouterE2ETest(ApiE2ETest):

  FILE_FINDER_ROUTER_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
  get_flow:
    enabled: True
  list_flow_results:
    enabled: True
  get_flow_files_archive:
    enabled: True
    path_globs_whitelist:
      - "/**/*.plist"
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def InitRouterConfig(self, router_config):
    router_config_file = os.path.join(self.temp_dir, "api_acls.yaml")
    with open(router_config_file, "wb") as fd:
      fd.write(router_config)

    self.config_overrider = test_lib.ConfigOverrider({
        "API.RouterACLConfigFile": router_config_file
    })
    self.config_overrider.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def setUp(self):
    super(ApiCallRobotRouterE2ETest, self).setUp()
    self.client_id = self.SetupClients(1)[0]
    self.token.username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

  def tearDown(self):
    super(ApiCallRobotRouterE2ETest, self).tearDown()
    self.config_overrider.Stop()

  def testCreatingArbitraryFlowDoesNotWork(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_ROUTER_CONFIG %
                          self.token.username)

    client_ref = self.api.Client(client_id=self.client_id.Basename())
    with self.assertRaises(RuntimeError):
      client_ref.CreateFlow(name=processes.ListProcesses.__name__)

  def testFileFinderWorkflowWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_ROUTER_CONFIG %
                          self.token.username)

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    args = rdf_file_finder.FileFinderArgs(
        paths=[
            os.path.join(self.base_path, "test.plist"), os.path.join(
                self.base_path, "numbers.txt"), os.path.join(
                    self.base_path, "numbers.txt.ver2")
        ],
        action=rdf_file_finder.FileFinderAction(
            action_type=rdf_file_finder.FileFinderAction.Action.
            DOWNLOAD)).AsPrimitiveProto()
    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    # Now run the flow we just started.
    client_id = rdf_client.ClientURN(flow_obj.client_id)
    flow_urn = client_id.Add("flows").Add(flow_obj.flow_id)
    for _ in test_lib.TestFlowHelper(
        flow_urn,
        client_id=client_id,
        client_mock=action_mocks.FileFinderClientMock(),
        token=self.token):
      pass

    # Refresh flow.
    flow_obj = client_ref.Flow(flow_obj.flow_id).Get()
    self.assertEqual(flow_obj.data.state, flow_obj.data.TERMINATED)

    # Check that we got 3 results (we downloaded 3 files).
    results = list(flow_obj.ListResults())
    self.assertEqual(len(results), 3)
    # We expect results to be FileFinderResult.
    self.assertItemsEqual(
        [os.path.basename(r.payload.stat_entry.pathspec.path)
         for r in results], ["test.plist", "numbers.txt", "numbers.txt.ver2"])

    # Now downloads the files archive.
    zip_stream = StringIO.StringIO()
    flow_obj.GetFilesArchive().WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    # Now check that the archive has only "test.plist" file, as it's the
    # only file that matches the whitelist (see FILE_FINDER_ROUTER_CONFIG).
    # There should be 3 items in the archive: the hash of the "test.plist"
    # file, the symlink to this hash and the MANIFEST file.
    namelist = zip_fd.namelist()
    self.assertEqual(len(namelist), 3)

    # First component of every path in the archive is the containing folder,
    # we should strip it.
    namelist = [os.path.join(*n.split(os.sep)[1:]) for n in namelist]
    with open(os.path.join(self.base_path, "test.plist")) as test_plist_fd:
      test_plist_hash = hashlib.sha256(test_plist_fd.read()).hexdigest()
    self.assertEqual(
        sorted([
            # pyformat: disable
            os.path.join(self.client_id.Basename(), "fs", "os",
                         self.base_path.strip("/"), "test.plist"),
            os.path.join("hashes", test_plist_hash),
            "MANIFEST"
            # pyformat: enable
        ]),
        sorted(namelist))

  def testCheckingArbitraryFlowStateDoesNotWork(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_ROUTER_CONFIG %
                          self.token.username)
    flow_urn = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name=file_finder.FileFinder.__name__,
        token=self.token)

    flow_ref = self.api.Client(
        client_id=self.client_id.Basename()).Flow(flow_urn.Basename())
    with self.assertRaises(RuntimeError):
      flow_ref.Get()

  def testNoThrottlingDoneByDefault(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_ROUTER_CONFIG %
                          self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    # Create 60 flows in a row to check that no throttling is applied.
    for _ in range(20):
      flow_obj = client_ref.CreateFlow(
          name=file_finder.FileFinder.__name__, args=args)
      self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

  FILE_FINDER_THROTTLED_ROUTER_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
    max_flows_per_client_daily: 2
    min_interval_between_duplicate_flows: 1h
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def testFileFinderThrottlingByFlowCountWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG %
                          self.token.username)

    args = []
    for p in ["tests.plist", "numbers.txt", "numbers.txt.ver2"]:
      args.append(
          rdf_file_finder.FileFinderArgs(
              action=rdf_file_finder.FileFinderAction(action_type="STAT"),
              paths=[p]).AsPrimitiveProto())

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[0])
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args[1])
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    with self.assertRaisesRegexp(RuntimeError, "2 flows run since"):
      client_ref.CreateFlow(name=file_finder.FileFinder.__name__, args=args[2])

  def testFileFinderThrottlingByDuplicateIntervalWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_THROTTLED_ROUTER_CONFIG %
                          self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.data.state, flow_obj.data.RUNNING)

    flow_obj_2 = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    self.assertEqual(flow_obj.flow_id, flow_obj_2.flow_id)

  FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG = """
router: "ApiCallRobotRouter"
router_params:
  file_finder_flow:
    enabled: True
    max_file_size: 5000000
  robot_id: "TheRobot"
users:
  - "%s"
"""

  def testFileFinderMaxFileSizeOverrideWorks(self):
    self.InitRouterConfig(self.__class__.FILE_FINDER_MAX_SIZE_OVERRIDE_CONFIG %
                          self.token.username)

    args = rdf_file_finder.FileFinderArgs(
        action=rdf_file_finder.FileFinderAction(action_type="DOWNLOAD"),
        paths=["tests.plist"]).AsPrimitiveProto()

    client_ref = self.api.Client(client_id=self.client_id.Basename())

    flow_obj = client_ref.CreateFlow(
        name=file_finder.FileFinder.__name__, args=args)
    flow_args = self.api.types.UnpackAny(flow_obj.data.args)
    self.assertEqual(flow_args.action.download.max_size, 5000000)
    self.assertEqual(flow_args.action.download.oversized_file_policy,
                     flow_args.action.download.SKIP)


def main(argv):
  HTTPApiEndToEndTestProgram(argv=argv, testLoader=ApiE2ETestLoader())


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  flags.StartMain(main)
