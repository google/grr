#!/usr/bin/env python
"""Tests for API client + HTTPS server integration."""

import datetime
from http import server as http_server
import io
import os
import socket
import socketserver
import threading

from absl import app
from cryptography import x509
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import oid
import portpicker
import requests

from grr_api_client import api as grr_api
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.util import temp
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class ApiSslServerTestBase(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):

  _api_set_up_done = False
  _ssl_trd = None

  ssl_port = None
  ssl_endpoint = None
  ssl_cert_path = None

  # NOTE: there's no corresponding tearDownClass method for the logic
  # below, since we want to have one SSL server thread not per test
  # suite, but per process. It effectively has to survive set up/tear down
  # of all the test suites inheriting from ApiSslServerTestBase
  @classmethod
  def setUpClass(cls):
    super(ApiSslServerTestBase, cls).setUpClass()

    if ApiSslServerTestBase._api_set_up_done:
      return

    key = rdf_crypto.RSAPrivateKey.GenerateKey()
    key_path = temp.TempFilePath("key.pem")
    with open(key_path, "wb") as f:
      f.write(key.AsPEM())

    subject = issuer = x509.Name([
        x509.NameAttribute(oid.NameOID.COMMON_NAME, u"localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(
        issuer).public_key(key.GetPublicKey().GetRawPublicKey()).serial_number(
            x509.random_serial_number()).not_valid_before(
                datetime.datetime.utcnow()).not_valid_after(
                    datetime.datetime.utcnow() +
                    datetime.timedelta(days=1)).add_extension(
                        x509.SubjectAlternativeName(
                            [x509.DNSName(u"localhost")]),
                        critical=False,
                    ).sign(key.GetRawPrivateKey(), hashes.SHA256(),
                           backends.default_backend())

    ApiSslServerTestBase.ssl_cert_path = temp.TempFilePath("certificate.pem")
    with open(ApiSslServerTestBase.ssl_cert_path, "wb") as f:
      f.write(cert.public_bytes(serialization.Encoding.PEM))

    ApiSslServerTestBase.ssl_port = portpicker.pick_unused_port()
    with test_lib.ConfigOverrider({
        "AdminUI.enable_ssl": True,
        "AdminUI.ssl_key_file": key_path,
        "AdminUI.ssl_cert_file": ApiSslServerTestBase.ssl_cert_path,
    }):
      ApiSslServerTestBase._ssl_trd = wsgiapp_testlib.ServerThread(
          ApiSslServerTestBase.ssl_port, name="ApiSslServerTest")
      ApiSslServerTestBase._ssl_trd.StartAndWaitUntilServing()

    ApiSslServerTestBase.ssl_endpoint = ("https://localhost:%s" %
                                         ApiSslServerTestBase.ssl_port)

    ApiSslServerTestBase._api_set_up_done = True

  def setUp(self):
    super().setUp()

    api_auth_manager.InitializeApiAuthManager(
        api_call_router_without_checks.ApiCallRouterWithoutChecks)
    self.test_username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.test_username)


class ApiSslE2ETestMixin(object):

  def testGetClientWorks(self):
    # By testing GetClient we test a simple GET method.
    client_id = self.SetupClient(0)
    c = self.api.Client(client_id=client_id).Get()
    self.assertEqual(c.client_id, client_id)

  def testSearchClientWorks(self):
    # By testing SearchClients we test an iterator-based API method.
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testPostMethodWorks(self):
    client_id = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    client_ref = self.api.Client(client_id=client_id)
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())
    self.assertTrue(result_flow.client_id)

  def testDownloadingFileWorks(self):
    client_id = self.SetupClient(0)
    fixture_test_lib.ClientFixture(client_id)

    out = io.BytesIO()
    self.api.Client(client_id=client_id).File(
        "fs/tsk/c/bin/rbash").GetBlob().WriteToStream(out)

    self.assertTrue(out.getvalue())


class ApiSslWithoutCABundleTest(ApiSslServerTestBase):

  def testConnectionFails(self):
    client_id = self.SetupClient(0)

    # TODO: Enable version validation.
    api = grr_api.InitHttp(
        api_endpoint=self.__class__.ssl_endpoint, validate_version=False)
    with self.assertRaises(requests.exceptions.SSLError):
      api.Client(client_id=client_id).Get()


class ApiSslWithEnvVarWithoutMergingTest(ApiSslServerTestBase):

  def testConnectionFails(self):
    client_id = self.SetupClient(0)

    # TODO: Enable version validation.
    api = grr_api.InitHttp(
        api_endpoint=self.__class__.ssl_endpoint,
        trust_env=False,
        validate_version=False)
    with self.assertRaises(requests.exceptions.SSLError):
      api.Client(client_id=client_id).Get()


class ApiSslWithConfigurationInEnvVarsE2ETest(ApiSslServerTestBase,
                                              ApiSslE2ETestMixin):

  def setUp(self):
    super().setUp()

    prev_environ = dict(os.environ)

    def _CleanUpEnviron():
      os.environ.clear()
      os.environ.update(prev_environ)

    self.addCleanup(_CleanUpEnviron)

    os.environ["REQUESTS_CA_BUNDLE"] = self.__class__.ssl_cert_path
    self.api = grr_api.InitHttp(api_endpoint=self.__class__.ssl_endpoint)


class ApiSslWithWithVerifyFalseE2ETest(ApiSslServerTestBase,
                                       ApiSslE2ETestMixin):

  def setUp(self):
    super().setUp()

    self.api = grr_api.InitHttp(
        api_endpoint=self.__class__.ssl_endpoint, verify=False)


class ApiSslWithWithVerifyPointingToCABundleTest(ApiSslServerTestBase,
                                                 ApiSslE2ETestMixin):

  def setUp(self):
    super().setUp()

    self.api = grr_api.InitHttp(
        api_endpoint=self.__class__.ssl_endpoint,
        verify=self.__class__.ssl_cert_path)


class Proxy(http_server.SimpleHTTPRequestHandler):

  requests = []

  def do_CONNECT(self):  # pylint: disable=invalid-name
    self.__class__.requests.append(self.requestline)


class TCPServerV6(socketserver.TCPServer):
  address_family = socket.AF_INET6


class ApiSslProxyTest(ApiSslServerTestBase):

  def setUp(self):
    super().setUp()
    attempts_count = 0
    self.proxy_server = None
    while self.proxy_server is None:
      try:
        self.proxy_port = portpicker.pick_unused_port()
        self.proxy_server = TCPServerV6(("::", self.proxy_port), Proxy)
      except socket.error:
        attempts_count += 1
        if attempts_count == 10:
          self.fail("Can't initialize proxy server.")

    threading.Thread(target=self.proxy_server.serve_forever).start()
    self.addCleanup(self.proxy_server.server_close)
    self.addCleanup(self.proxy_server.shutdown)

  def testProxyConnection(self):
    client_id = self.SetupClient(0)

    # TODO: Enable version validation.
    api = grr_api.InitHttp(
        api_endpoint=self.__class__.ssl_endpoint,
        proxies={"https": "http://localhost:%d" % self.proxy_port},
        validate_version=False)
    with self.assertRaises(requests.exceptions.ConnectionError):
      api.Client(client_id=client_id).Get()

    # CONNECT request should point to GRR SSL server.
    self.assertEqual(
        Proxy.requests,
        ["CONNECT localhost:%d HTTP/1.0" % self.__class__.ssl_port])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
