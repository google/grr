#!/usr/bin/env python
"""Tests for API client + HTTPS server integration."""
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
import io
import os
import socket
import threading


from cryptography import x509
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import oid
from http import server as http_server
import portpicker
import requests
import socketserver

from grr_api_client import api as grr_api
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_server.flows.general import processes
from grr_response_server.gui import api_auth_manager
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp_testlib
from grr.test_lib import acl_test_lib
from grr.test_lib import fixture_test_lib
from grr.test_lib import test_lib


class ApiSslServerTestBase(test_lib.GRRBaseTest, acl_test_lib.AclTestMixin):

  def setUp(self):
    super(ApiSslServerTestBase, self).setUp()

    key = rdf_crypto.RSAPrivateKey.GenerateKey()
    key_path = os.path.join(self.temp_dir, "key.pem")
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

    self.cert_path = os.path.join(self.temp_dir, "certificate.pem")
    with open(self.cert_path, "wb") as f:
      f.write(cert.public_bytes(serialization.Encoding.PEM))

    self.config_overrider = test_lib.ConfigOverrider({
        "AdminUI.enable_ssl": True,
        "AdminUI.ssl_key_file": key_path,
        "AdminUI.ssl_cert_file": self.cert_path,
    })
    self.config_overrider.Start()

    self.port = portpicker.pick_unused_port()
    self.thread = wsgiapp_testlib.ServerThread(self.port)
    self.thread.StartAndWaitUntilServing()

    api_auth_manager.APIACLInit.InitApiAuthManager()
    self.token.username = "api_test_robot_user"
    webauth.WEBAUTH_MANAGER.SetUserName(self.token.username)

    self.endpoint = "https://localhost:%s" % self.port

  def tearDown(self):
    super(ApiSslServerTestBase, self).tearDown()

    self.config_overrider.Stop()
    self.thread.keep_running = False


class ApiSslE2ETestMixin(object):

  def testGetClientWorks(self):
    # By testing GetClient we test a simple GET method.
    client_urn = self.SetupClient(0)
    c = self.api.Client(client_id=client_urn.Basename()).Get()
    self.assertEqual(c.client_id, client_urn.Basename())

  def testSearchClientWorks(self):
    # By testing SearchClients we test an iterator-based API method.
    clients = list(self.api.SearchClients(query="."))
    self.assertEqual(clients, [])

  def testPostMethodWorks(self):
    client_urn = self.SetupClient(0)
    args = processes.ListProcessesArgs(
        filename_regex="blah", fetch_binaries=True)

    client_ref = self.api.Client(client_id=client_urn.Basename())
    result_flow = client_ref.CreateFlow(
        name=processes.ListProcesses.__name__, args=args.AsPrimitiveProto())
    self.assertTrue(result_flow.client_id)

  def testDownloadingFileWorks(self):
    client_urn = self.SetupClient(0)
    fixture_test_lib.ClientFixture(client_urn, self.token)

    out = io.BytesIO()
    self.api.Client(client_id=client_urn.Basename()).File(
        "fs/tsk/c/bin/rbash").GetBlob().WriteToStream(out)

    self.assertTrue(out.getvalue())


class ApiSslWithoutCABundleTest(ApiSslServerTestBase):

  def testConnectionFails(self):
    client_urn = self.SetupClient(0)

    api = grr_api.InitHttp(api_endpoint=self.endpoint)
    with self.assertRaises(requests.exceptions.SSLError):
      api.Client(client_id=client_urn.Basename()).Get()


class ApiSslWithEnvVarWithoutMergingTest(ApiSslServerTestBase):

  def testConnectionFails(self):
    client_urn = self.SetupClient(0)

    api = grr_api.InitHttp(api_endpoint=self.endpoint, trust_env=False)
    with self.assertRaises(requests.exceptions.SSLError):
      api.Client(client_id=client_urn.Basename()).Get()


class ApiSslWithConfigurationInEnvVarsE2ETest(ApiSslServerTestBase,
                                              ApiSslE2ETestMixin):

  def setUp(self):
    super(ApiSslWithConfigurationInEnvVarsE2ETest, self).setUp()

    self.prev_environ = dict(os.environ)
    os.environ["REQUESTS_CA_BUNDLE"] = self.cert_path
    self.api = grr_api.InitHttp(api_endpoint=self.endpoint)

  def tearDown(self):
    super(ApiSslWithConfigurationInEnvVarsE2ETest, self).tearDown()

    os.environ.clear()
    os.environ.update(self.prev_environ)


class ApiSslWithWithVerifyFalseE2ETest(ApiSslServerTestBase,
                                       ApiSslE2ETestMixin):

  def setUp(self):
    super(ApiSslWithWithVerifyFalseE2ETest, self).setUp()

    self.api = grr_api.InitHttp(api_endpoint=self.endpoint, verify=False)


class ApiSslWithWithVerifyPointingToCABundleTest(ApiSslServerTestBase,
                                                 ApiSslE2ETestMixin):

  def setUp(self):
    super(ApiSslWithWithVerifyPointingToCABundleTest, self).setUp()

    self.api = grr_api.InitHttp(
        api_endpoint=self.endpoint, verify=self.cert_path)


class Proxy(http_server.SimpleHTTPRequestHandler):

  requests = []

  def do_CONNECT(self):  # pylint: disable=invalid-name
    self.__class__.requests.append(self.requestline)


class TCPServerV6(socketserver.TCPServer):
  address_family = socket.AF_INET6


class ApiSslProxyTest(ApiSslServerTestBase):

  def setUp(self):
    super(ApiSslProxyTest, self).setUp()
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

  def tearDown(self):
    super(ApiSslProxyTest, self).tearDown()
    self.proxy_server.shutdown()
    self.proxy_server.server_close()

  def testProxyConnection(self):
    client_urn = self.SetupClient(0)

    api = grr_api.InitHttp(
        api_endpoint=self.endpoint,
        proxies={"https": "localhost:%d" % self.proxy_port})
    with self.assertRaises(requests.exceptions.ConnectionError):
      api.Client(client_id=client_urn.Basename()).Get()

    # CONNECT request should point to GRR SSL server.
    self.assertEqual(Proxy.requests,
                     ["CONNECT localhost:%d HTTP/1.0" % self.port])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
