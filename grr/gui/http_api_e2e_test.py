#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""End-to-end tests for HTTP API.

HTTP API plugins are tested with their own dedicated unit-tests that are
protocol- and server-independent. Tests in this file test the full GRR server
stack with regards to the HTTP API.
"""

import json
import logging
import os
import StringIO
import threading
import zipfile

import portpicker
import requests

import unittest

from grr_api_client import api as grr_api
from grr_api_client import errors as grr_api_errors
from grr.gui import api_auth_manager
from grr.gui import api_call_router_with_approval_checks
from grr.gui import webauth
from grr.gui import wsgiapp
from grr.gui import wsgiapp_testlib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.proto import jobs_pb2
from grr.proto.api import vfs_pb2
from grr.server import aff4
from grr.server import flow
from grr.server.aff4_objects import aff4_grr
from grr.server.authorization import client_approval_auth
from grr.server.flows.general import processes
from grr.server.flows.general import processes_test
from grr.server.hunts import standard_test
from grr.server.output_plugins import csv_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import test_lib


class ApiE2ETest(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):
  """Base class for all API E2E tests."""

  def setUp(self):
    super(ApiE2ETest, self).setUp()

    api_auth_manager.APIACLInit.InitApiAuthManager()
    self.token.username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    self.port = ApiE2ETest.server_port
    self.endpoint = "http://localhost:%s" % self.port
    self.api = grr_api.InitHttp(api_endpoint=self.endpoint)

  _api_set_up_lock = threading.RLock()
  _api_set_up_done = False

  @classmethod
  def setUpClass(cls):
    super(ApiE2ETest, cls).setUpClass()
    with ApiE2ETest._api_set_up_lock:
      if not ApiE2ETest._api_set_up_done:

        # Set up HTTP server
        port = portpicker.PickUnusedPort()
        ApiE2ETest.server_port = port
        logging.info("Picked free AdminUI port for HTTP %d.", port)

        ApiE2ETest.trd = wsgiapp_testlib.ServerThread(port)
        ApiE2ETest.trd.StartAndWaitUntilServing()

        ApiE2ETest._api_set_up_done = True


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

  def testListResultsForListProcessesFlow(self):
    process = rdf_client.Process(
        pid=2,
        ppid=1,
        cmdline=["cmd.exe"],
        exe="c:\\windows\\cmd.exe",
        ctime=long(1333718907.167083 * 1e6),
        RSS_size=42)

    client_urn = self.SetupClients(1)[0]
    client_mock = processes_test.ListProcessesMock([process])

    flow_urn = flow.GRRFlow.StartFlow(
        client_id=client_urn,
        flow_name=processes.ListProcesses.__name__,
        token=self.token)
    for _ in flow_test_lib.TestFlowHelper(
        flow_urn, client_mock, client_id=client_urn, token=self.token):
      pass

    result_flow = self.api.Client(
        client_id=client_urn.Basename()).Flow(flow_urn.Basename())
    results = list(result_flow.ListResults())

    self.assertEqual(len(results), 1)
    self.assertEqual(process.AsPrimitiveProto(), results[0].payload)


class ApiClientLibHuntTest(standard_test.StandardHuntTestMixin, ApiE2ETest):
  """Tests flows-related part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibHuntTest, self).setUp()
    self.hunt_obj = self.CreateHunt()

  def testListHunts(self):
    hs = list(self.api.ListHunts())
    self.assertEqual(len(hs), 1)
    self.assertEqual(hs[0].hunt_id, self.hunt_obj.urn.Basename())
    self.assertEqual(hs[0].data.name, "GenericHunt")

  def testGetHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.hunt_id, self.hunt_obj.urn.Basename())
    self.assertEqual(h.data.name, "GenericHunt")

  def testModifyHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.client_limit, 100)

    h = h.Modify(client_limit=200)
    self.assertEqual(h.data.client_limit, 200)

    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.client_limit, 200)

  def testDeleteHunt(self):
    self.api.Hunt(self.hunt_obj.urn.Basename()).Delete()

    obj = aff4.FACTORY.Open(self.hunt_obj.urn, token=self.token)
    self.assertEqual(obj.__class__, aff4.AFF4Volume)

  def testStartHunt(self):
    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.PAUSED)

    h = h.Start()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = self.api.Hunt(self.hunt_obj.urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

  def testStopHunt(self):
    hunt_urn = self.StartHunt()

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STARTED)

    h = h.Stop()
    self.assertEqual(h.data.state, h.data.STOPPED)

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    self.assertEqual(h.data.state, h.data.STOPPED)

  def testListResults(self):
    self.client_ids = self.SetupClients(5)
    with test_lib.FakeTime(42):
      hunt_urn = self.StartHunt()
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

    h = self.api.Hunt(hunt_urn.Basename()).Get()
    results = list(h.ListResults())

    client_ids = set(r.client.client_id for r in results)
    self.assertEqual(client_ids, set(x.Basename() for x in self.client_ids))
    for r in results:
      self.assertEqual(r.timestamp, 42000000)
      self.assertEqual(r.payload.pathspec.path, "/tmp/evil.txt")

  def testListLogsWithoutClientIds(self):
    self.hunt_obj.Log("Sample message: foo.")
    self.hunt_obj.Log("Sample message: bar.")

    logs = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListLogs())
    self.assertEqual(len(logs), 2)

    self.assertEqual(logs[0].client, None)
    self.assertEqual(logs[0].data.log_message, "Sample message: foo.")
    self.assertEqual(logs[1].client, None)
    self.assertEqual(logs[1].data.log_message, "Sample message: bar.")

  def testListLogsWithClientIds(self):
    self.client_ids = self.SetupClients(2)
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    logs = list(self.api.Hunt(hunt_urn.Basename()).ListLogs())
    client_ids = set()
    for l in logs:
      client_ids.add(l.client.client_id)
    self.assertEqual(client_ids, set(x.Basename() for x in self.client_ids))

  def testListErrors(self):
    client_urn_1 = rdf_client.ClientURN("C.0000111122223333")
    with test_lib.FakeTime(52):
      self.hunt_obj.LogClientError(client_urn_1, "Error foo.")

    client_urn_2 = rdf_client.ClientURN("C.1111222233334444")
    with test_lib.FakeTime(55):
      self.hunt_obj.LogClientError(client_urn_2, "Error bar.",
                                   "<some backtrace>")

    errors = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListErrors())
    self.assertEqual(len(errors), 2)

    self.assertEqual(errors[0].log_message, "Error foo.")
    self.assertEqual(errors[0].client.client_id, client_urn_1.Basename())
    self.assertEqual(errors[0].backtrace, "")

    self.assertEqual(errors[1].log_message, "Error bar.")
    self.assertEqual(errors[1].client.client_id, client_urn_2.Basename())
    self.assertEqual(errors[1].backtrace, "<some backtrace>")

  def testListCrashes(self):
    self.hunt_obj.Run()

    client_ids = self.SetupClients(2)
    client_mocks = dict([(client_id, flow_test_lib.CrashClientMock(
        client_id, self.token)) for client_id in client_ids])
    self.AssignTasksToClients(client_ids)
    hunt_test_lib.TestHuntHelperWithMultipleMocks(client_mocks, False,
                                                  self.token)

    crashes = list(self.api.Hunt(self.hunt_obj.urn.Basename()).ListCrashes())
    self.assertEqual(len(crashes), 2)

    self.assertEqual(
        set(x.client.client_id for x in crashes),
        set(x.Basename() for x in client_ids))
    for c in crashes:
      self.assertEqual(c.crash_message, "Client killed during transaction")

  def testListClients(self):
    self.hunt_obj.Run()
    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)
    self.RunHunt(client_ids=[client_ids[-1]], failrate=0)

    h = self.api.Hunt(self.hunt_obj.urn.Basename())
    clients = list(h.ListClients(h.CLIENT_STATUS_STARTED))
    self.assertEqual(len(clients), 5)

    clients = list(h.ListClients(h.CLIENT_STATUS_OUTSTANDING))
    self.assertEqual(len(clients), 4)

    clients = list(h.ListClients(h.CLIENT_STATUS_COMPLETED))
    self.assertEqual(len(clients), 1)
    self.assertEqual(clients[0].client_id, client_ids[-1].Basename())

  def testGetClientCompletionStats(self):
    self.hunt_obj.Run()
    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)

    client_stats = self.api.Hunt(
        self.hunt_obj.urn.Basename()).GetClientCompletionStats()
    self.assertEqual(len(client_stats.start_points), 0)
    self.assertEqual(len(client_stats.complete_points), 0)

  def testGetStats(self):
    self.client_ids = self.SetupClients(5)
    self.hunt_obj.Run()
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    stats = self.api.Hunt(self.hunt_obj.urn.Basename()).GetStats()
    self.assertEqual(len(stats.worst_performers), 5)

  def testGetFilesArchive(self):
    zip_stream = StringIO.StringIO()
    self.api.Hunt(self.hunt_obj.urn.Basename()).GetFilesArchive().WriteToStream(
        zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)

  def testExportedResults(self):
    zip_stream = StringIO.StringIO()
    self.api.Hunt(self.hunt_obj.urn.Basename()).GetExportedResults(
        csv_plugin.CSVInstantOutputPlugin.plugin_name).WriteToStream(zip_stream)
    zip_fd = zipfile.ZipFile(zip_stream)

    namelist = zip_fd.namelist()
    self.assertTrue(namelist)


class ApiClientLibVfsTest(ApiE2ETest):
  """Tests VFS operations part of GRR Python API client library."""

  def setUp(self):
    super(ApiClientLibVfsTest, self).setUp()
    self.client_urn = self.SetupClients(1)[0]
    fixture_test_lib.ClientFixture(self.client_urn, self.token)

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
      self.assertTrue(isinstance(item, vfs_pb2.ApiVfsTimelineItem))

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
        client_obj.AddLabels(["bar", "foo"])

    client_ref = self.api.Client(client_id=self.client_urn.Basename())
    self.assertEqual(
        sorted(client_ref.Get().data.labels, key=lambda l: l.name), [
            jobs_pb2.AFF4ObjectLabel(
                name="bar", owner=self.token.username, timestamp=42000000),
            jobs_pb2.AFF4ObjectLabel(
                name="foo", owner=self.token.username, timestamp=42000000)
        ])

    client_ref.RemoveLabel("foo")
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

  def testCSRFTokenIsUpdatedIfNotPresentInCookies(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")
    self.assertTrue(csrf_token)

    # Check that calling GetGrrUser method doesn't update the cookie.
    get_user_response = requests.get(self.base_url + "/api/users/me")
    csrf_token_2 = get_user_response.cookies.get("csrftoken")
    self.assertTrue(csrf_token_2)

    self.assertNotEqual(csrf_token, csrf_token_2)

  def testCSRFTokenIsNotUpdtedIfUserIsUnknown(self):
    fake_manager = webauth.NullWebAuthManager()
    fake_manager.SetUserName("")
    with utils.Stubber(webauth, "WEBAUTH_MANAGER", fake_manager):
      index_response = requests.get(self.base_url)
      csrf_token = index_response.cookies.get("csrftoken")
      self.assertIsNone(csrf_token)

  def testGetPendingUserNotificationCountMethodRefreshesCSRFToken(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    # Check that calling GetGrrUser method doesn't update the cookie.
    get_user_response = requests.get(
        self.base_url + "/api/users/me", cookies={"csrftoken": csrf_token})
    csrf_token_2 = get_user_response.cookies.get("csrftoken")

    self.assertIsNone(csrf_token_2)

    # Check that calling GetPendingUserNotificationsCount refreshes the
    # token.
    notifications_response = requests.get(
        self.base_url + "/api/users/me/notifications/pending/count",
        cookies={"csrftoken": csrf_token})
    csrf_token_3 = notifications_response.cookies.get("csrftoken")

    self.assertTrue(csrf_token_3)
    self.assertNotEqual(csrf_token, csrf_token_3)


class ApprovalByLabelE2ETest(ApiE2ETest):

  def setUp(self):
    super(ApprovalByLabelE2ETest, self).setUp()

    # Set up clients and labels before we turn on the FullACM. We need to create
    # the client because to check labels the client needs to exist.
    client_ids = self.SetupClients(3)

    self.client_nolabel = rdf_client.ClientURN(client_ids[0])
    self.client_nolabel_id = self.client_nolabel.Basename()

    self.client_legal = rdf_client.ClientURN(client_ids[1])
    self.client_legal_id = self.client_legal.Basename()

    self.client_prod = rdf_client.ClientURN(client_ids[2])
    self.client_prod_id = self.client_prod.Basename()

    with aff4.FACTORY.Open(
        self.client_legal,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token) as client_obj:
      client_obj.AddLabel("legal_approval")

    with aff4.FACTORY.Open(
        self.client_prod,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token) as client_obj:
      client_obj.AddLabels(["legal_approval", "prod_admin_approval"])

    cls = (api_call_router_with_approval_checks.ApiCallRouterWithApprovalChecks)
    cls.ClearCache()
    self.approver = test_lib.ConfigOverrider({
        "API.DefaultRouter":
            cls.__name__,
        "ACL.approvers_config_file":
            os.path.join(self.base_path, "approvers.yaml")
    })
    self.approver.Start()

    # Get a fresh approval manager object and reload with test approvers.
    self.approval_manager_stubber = utils.Stubber(
        client_approval_auth, "CLIENT_APPROVAL_AUTH_MGR",
        client_approval_auth.ClientApprovalAuthorizationManager())
    self.approval_manager_stubber.Start()

    # Force creation of new APIAuthorizationManager, so that configuration
    # changes are picked up.
    api_auth_manager.APIACLInit.InitApiAuthManager()

  def tearDown(self):
    super(ApprovalByLabelE2ETest, self).tearDown()

    self.approval_manager_stubber.Stop()
    self.approver.Stop()

  def testClientNoLabels(self):
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get)

    # approvers.yaml rules don't get checked because this client has no
    # labels. Regular approvals still required.
    self.RequestAndGrantClientApproval(self.client_nolabel, self.token)

    # Check we now have access
    self.api.Client(self.client_nolabel_id).File("fs/os/foo").Get()

  def testClientApprovalSingleLabel(self):
    """Client requires an approval from a member of "legal_approval"."""
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    self.RequestAndGrantClientApproval(self.client_legal, self.token)
    # This approval isn't enough, we need one from legal, so it should still
    # fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_legal_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_legal,
        self.token.username,
        reason=self.token.reason,
        approver="legal1")

    # Check we now have access
    self.api.Client(self.client_legal_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabel(self):
    """Multi-label client approval test.

    This client requires one legal and two prod admin approvals. The requester
    must also be in the prod admin group.
    """
    self.token.username = "prod1"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    self.RequestAndGrantClientApproval(self.client_prod, self.token)

    # This approval from "approver" isn't enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the legal_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="legal1")

    # We have "approver", "legal1": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant an approval from a user in the prod_admin_approval list in
    # approvers.yaml
    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="prod2")

    # We have "approver", "legal1", "prod2": not enough.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3": we should have
    # access.
    self.api.Client(self.client_prod_id).File("fs/os/foo").Get()

  def testClientApprovalMultiLabelCheckRequester(self):
    """Requester must be listed as prod_admin_approval in approvals.yaml."""
    # No approvals yet, this should fail.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)

    # Grant all the necessary approvals
    self.RequestAndGrantClientApproval(self.client_prod, self.token)
    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="legal1")
    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="prod2")
    self.GrantClientApproval(
        self.client_prod,
        self.token.username,
        reason=self.token.reason,
        approver="prod3")

    # We have "approver", "legal1", "prod2", "prod3" approvals but because
    # "notprod" user isn't in prod_admin_approval and
    # requester_must_be_authorized is True it should still fail. This user can
    # never get a complete approval.
    self.assertRaises(
        grr_api_errors.AccessForbiddenError,
        self.api.Client(self.client_prod_id).File("fs/os/foo").Get)


def main(argv):
  del argv  # Unused.
  unittest.main()


def DistEntry():
  """The main entry point for packages."""
  flags.StartMain(main)


if __name__ == "__main__":
  flags.StartMain(main)
