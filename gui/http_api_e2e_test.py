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
from grr.lib import flags
from grr.lib import test_lib


class HTTPApiEndToEndTestProgram(test_lib.GrrTestProgram):

  server_port = None

  def setUp(self):
    # Select a free port
    port = portpicker.PickUnusedPort()
    HTTPApiEndToEndTestProgram.server_port = port
    logging.info("Picked free AdminUI port %d.", port)

    self.trd = runtests.DjangoThread(port)
    self.trd.StartAndWaitUntilServing()


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

  def testPOSTRequestWithoutCSRFTokenFails(self):
    data = {
        "client_ids": ["C.0000000000000000"],
        "labels": ["foo", "bar"]
        }

    response = requests.post(self.base_url + "/api/clients/labels/add",
                             data=json.dumps(data))

    self.assertEquals(response.status_code, 403)
    self.assertTrue("CSRF" in response.text)

  def testPOSTRequestWithCSRFTokenSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {
        "x-csrftoken": csrf_token,
        "x-requested-with": "XMLHttpRequest"
        }
    data = {
        "client_ids": ["C.0000000000000000"],
        "labels": ["foo", "bar"]
        }
    cookies = {
        "csrftoken": csrf_token
        }

    response = requests.post(self.base_url + "/api/clients/labels/add",
                             headers=headers, data=json.dumps(data),
                             cookies=cookies)
    self.assertEquals(response.status_code, 200)


def main(argv):
  HTTPApiEndToEndTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
