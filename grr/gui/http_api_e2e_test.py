#!/usr/bin/env python
"""End-to-end tests for HTTP API.

HTTP API plugins are tested with their own dedicated unit-tests that are
protocol- and server-independent. Tests in this file test the full GRR server
stack with regards to the HTTP API.
"""

import json
import portpicker
import requests

import logging

from grr.gui import runtests
from grr.gui.api_client import api as grr_api
from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import test_lib
from grr.lib.flows.general import processes


class HTTPApiEndToEndTestProgram(test_lib.GrrTestProgram):

  server_port = None

  def setUp(self):
    super(HTTPApiEndToEndTestProgram, self).setUp()

    # Select a free port
    port = portpicker.PickUnusedPort()
    HTTPApiEndToEndTestProgram.server_port = port
    logging.info("Picked free AdminUI port %d.", port)

    self.trd = runtests.DjangoThread(port)
    self.trd.StartAndWaitUntilServing()


class ApiClientTest(test_lib.GRRBaseTest):
  """Tests GRR Python API client library."""

  def setUp(self):
    super(ApiClientTest, self).setUp()

    port = HTTPApiEndToEndTestProgram.server_port
    endpoint = "http://localhost:%s" % port
    self.api = grr_api.InitHttp(api_endpoint=endpoint)

  def testSearchWithNoClients(self):
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testSearchClientsWith2Clients(self):
    client_urns = sorted(self.SetupClients(2))

    clients = sorted(
        self.api.SearchClients(query="."),
        key=lambda c: c.client_id)
    self.assertEqual(len(clients), 2)

    for i in range(2):
      self.assertEqual(clients[i].client_id, client_urns[i].Basename())
      self.assertEqual(clients[i].data["urn"], client_urns[i])

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
    self.assertEqual(flows[0].data["urn"], flow_urn)

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
    self.assertEqual(flows[0].data["urn"], flow_urn)

  def testCreateFlowFromClientRef(self):
    client_urn = self.SetupClients(1)[0]
    args = processes.ListProcessesArgs(filename_regex="blah",
                                       fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(name=processes.ListProcesses.__name__,
                                        args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data["urn"],
                                        token=self.token)
    self.assertEqual(result_flow_obj.state.args, args)

  def testCreateFlowFromClientObject(self):
    client_urn = self.SetupClients(1)[0]
    args = processes.ListProcessesArgs(filename_regex="blah",
                                       fetch_binaries=True)

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 0)

    client = self.api.Client(client_id=client_urn.Basename()).Get()
    result_flow = client.CreateFlow(name=processes.ListProcesses.__name__,
                                    args=args.AsPrimitiveProto())

    children = aff4.FACTORY.Open(client_urn, token=self.token).ListChildren()
    self.assertEqual(len(list(children)), 1)
    result_flow_obj = aff4.FACTORY.Open(result_flow.data["urn"],
                                        token=self.token)
    self.assertEqual(result_flow_obj.state.args, args)


class CSRFProtectionTest(test_lib.GRRBaseTest):
  """Tests GRR's CSRF protection logic for the HTTP API."""

  def setUp(self):
    super(CSRFProtectionTest, self).setUp()

    port = HTTPApiEndToEndTestProgram.server_port
    self.base_url = "http://localhost:%s" % port

  def testGETRequestWithoutCSRFTokenSucceeds(self):
    response = requests.get(self.base_url + "/api/config")
    self.assertEquals(response.status_code, 200)
    # Assert XSSI protection is in place.
    self.assertEquals(response.text[:5], ")]}'\n")

  def testHEADRequestForGETUrlWithoutCSRFTokenSucceeds(self):
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

    response = requests.post(self.base_url + "/api/clients/labels/add",
                             data=json.dumps(data))

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPOSTRequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(self.base_url + "/api/clients/labels/add",
                             data=json.dumps(data),
                             cookies=cookies)

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPOSTRequestWithCSRFTokenInHeadersAndCookiesSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {
        "x-csrftoken": csrf_token,
        "x-requested-with": "XMLHttpRequest"
    }
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(self.base_url + "/api/clients/labels/add",
                             headers=headers,
                             data=json.dumps(data),
                             cookies=cookies)
    self.assertEquals(response.status_code, 200)

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

    headers = {
        "x-csrftoken": csrf_token,
        "x-requested-with": "XMLHttpRequest"
    }
    cookies = {"csrftoken": csrf_token}

    response = requests.delete(
        self.base_url + "/api/users/me/notifications/pending/0",
        headers=headers,
        cookies=cookies)

    self.assertEquals(response.status_code, 200)


def main(argv):
  HTTPApiEndToEndTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
