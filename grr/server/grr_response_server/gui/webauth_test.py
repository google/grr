#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for the web auth managers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

from absl import app
import mock
import requests

from werkzeug import test as werkzeug_test

from google.oauth2 import id_token

from grr_response_server import data_store
from grr_response_server.gui import http_response
from grr_response_server.gui import validate_iap
from grr_response_server.gui import webauth
from grr_response_server.gui import wsgiapp
from grr.test_lib import test_lib


class RemoteUserWebAuthManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(RemoteUserWebAuthManagerTest, self).setUp()

    self.manager = webauth.RemoteUserWebAuthManager()
    self.success_response = http_response.HttpResponse("foobar")

  def HandlerStub(self, request, *args, **kwargs):
    del request, args, kwargs  # Unused.

    return self.success_response

  def testRejectsRequestWithoutRemoteUserHeader(self):
    environ = werkzeug_test.EnvironBuilder(environ_base={
        "REMOTE_ADDR": "127.0.0.1"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True), "No username header found.")

  def testRejectsRequestFromUntrustedIp(self):
    environ = werkzeug_test.EnvironBuilder(environ_base={
        "REMOTE_ADDR": "127.0.0.2"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertRegex(
        response.get_data(as_text=True),
        "Request sent from an IP not in AdminUI.remote_user_trusted_ips. "
        "Source was .+")

  def testRejectsRequestWithEmptyUsername(self):
    environ = werkzeug_test.EnvironBuilder(environ_base={
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_X_REMOTE_USER": ""
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True), "Empty username is not allowed.")

  def testProcessesRequestWithUsernameFromTrustedIp(self):
    environ = werkzeug_test.EnvironBuilder(environ_base={
        "REMOTE_ADDR": "127.0.0.1",
        "HTTP_X_REMOTE_USER": "foo"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(response, self.success_response)

  def testProcessesRequestWithEmail_configDisabled(self):
    environ = werkzeug_test.EnvironBuilder(
        environ_base={
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_X_REMOTE_USER": "foo",
            "HTTP_X_REMOTE_EXTRA_EMAIL": "foo@bar.org",
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertIsNone(request.email)
    self.assertEqual(response, self.success_response)

  def testProcessesRequestWithEmail_configEnabled(self):
    environ = werkzeug_test.EnvironBuilder(
        environ_base={
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_X_REMOTE_USER": "foo",
            "HTTP_X_REMOTE_EXTRA_EMAIL": "foo@bar.org",
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    with test_lib.ConfigOverrider({"Email.enable_custom_email_address": True}):
      response = self.manager.SecurityCheck(self.HandlerStub, request)

    self.assertEqual(request.email, "foo@bar.org")
    self.assertEqual(response, self.success_response)


class FirebaseWebAuthManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(FirebaseWebAuthManagerTest, self).setUp()

    config_overrider = test_lib.ConfigOverrider({
        "AdminUI.firebase_auth_domain": "foo-bar.firebaseapp.com",
        "API.DefaultRouter": "DisabledApiCallRouter"
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    self.manager = webauth.FirebaseWebAuthManager()
    self.success_response = http_response.HttpResponse("foobar")

    self.checked_request = None

  def HandlerStub(self, request, *args, **kwargs):
    _ = args
    _ = kwargs

    self.checked_request = request

    return self.success_response

  def testPassesThroughHomepageWhenAuthorizationHeaderIsMissing(self):
    environ = werkzeug_test.EnvironBuilder().get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(response, self.success_response)

  def testReportsErrorOnNonHomepagesWhenAuthorizationHeaderIsMissing(self):
    environ = werkzeug_test.EnvironBuilder(path="/foo").get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True),
        "JWT token validation failed: JWT token is missing.")

  def testReportsErrorWhenBearerPrefixIsMissing(self):
    environ = werkzeug_test.EnvironBuilder(
        path="/foo", headers={
            "Authorization": "blah"
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True),
        "JWT token validation failed: JWT token is missing.")

  @mock.patch.object(
      id_token, "verify_firebase_token", side_effect=ValueError("foobar error"))
  def testPassesThroughHomepageOnVerificationFailure(self, mock_method):
    _ = mock_method

    environ = werkzeug_test.EnvironBuilder(headers={
        "Authorization": "Bearer blah"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(response, self.success_response)

  @mock.patch.object(
      id_token, "verify_firebase_token", side_effect=ValueError("foobar error"))
  def testReportsErrorOnVerificationFailureOnNonHomepage(self, mock_method):
    _ = mock_method

    environ = werkzeug_test.EnvironBuilder(
        path="/foo", headers={
            "Authorization": "Bearer blah"
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True),
        "JWT token validation failed: foobar error")

  @mock.patch.object(id_token, "verify_firebase_token")
  def testVerifiesTokenWithProjectIdFromDomain(self, mock_method):
    environ = werkzeug_test.EnvironBuilder(headers={
        "Authorization": "Bearer blah"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(mock_method.call_count, 1)
    self.assertEqual(mock_method.call_args_list[0][0], ("blah", request))
    self.assertEqual(mock_method.call_args_list[0][1], dict(audience="foo-bar"))

  @mock.patch.object(
      id_token, "verify_firebase_token", return_value={"iss": "blah"})
  def testReportsErrorIfIssuerIsWrong(self, mock_method):
    _ = mock_method
    environ = werkzeug_test.EnvironBuilder(
        path="/foo", headers={
            "Authorization": "Bearer blah"
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    response = self.manager.SecurityCheck(self.HandlerStub, request)
    self.assertEqual(
        response.get_data(as_text=True),
        "JWT token validation failed: Wrong issuer.")

  @mock.patch.object(
      id_token,
      "verify_firebase_token",
      return_value={
          "iss": "https://securetoken.google.com/foo-bar",
          "email": "foo@bar.com"
      })
  def testFillsRequestUserFromTokenEmailOnSuccess(self, mock_method):
    _ = mock_method
    environ = werkzeug_test.EnvironBuilder(headers={
        "Authorization": "Bearer blah"
    }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    self.manager.SecurityCheck(self.HandlerStub, request)

    self.assertTrue(self.checked_request)
    self.assertEqual(self.checked_request.user, "foo@bar.com")


class IAPWebAuthManagerTest(test_lib.GRRBaseTest):

  def testNoHeader(self):
    """Test requests sent to the Admin UI without an IAP Header."""

    environ = werkzeug_test.EnvironBuilder(path="/").get_environ()
    request = wsgiapp.HttpRequest(environ)

    def Handler(request, *args, **kwargs):
      del request, args, kwargs  # Unused.

      return http_response.HttpResponse("foobar", status=200)

    manager = webauth.IAPWebAuthManager()
    response = manager.SecurityCheck(Handler, request)

    self.assertEqual(response.status_code, 401)

  @mock.patch.object(requests, "get")
  def testFailedSignatureKey(self, mock_get):
    """Test requests with an invalid JWT Token."""

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "6BEeoA": (
            "-----BEGIN PUBLIC KEY-----\n"
            "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAElmi1hJdqtbvdX1INOf5B9dWvkydY\n"
            "oowHUXiw8ELWzk/YHESNr8vXQoyOuLOEtLZeCQbFkeLUqxYp1sTArKNu/A==\n"
            "-----END PUBLIC KEY-----\n"),
    }

    assertion_header = (
        "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsI"
        "mtpZCI6IjZCRWVvQSJ9.eyJpc3MiOiJodHRwczovL2Nsb3VkLmdvb2dsZS5jb20"
        "vaWFwIiwic3ViIjoiYWNjb3VudHMuZ29vZ2xlLaaaaaaaaaaaaaaaaaaaaaaaaa"
        "aaaaaaaDciLCJlbWFpbCI6ImFaaaaaaaazaaaaaaaaaaaaaaaaaaaaaa8iLCJhd"
        "WQiOiIvcHJvamVjdaaaaaaaaaaaaaaaaaayaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaayOegyMzkzOTQ2NCIsImV4cCI6MTU0Njk4MDUwNiwiaWF0Ijo"
        "xNTQ2OTc5OTA2LCJaaCI6InNwb3apaaaaaaaaaaaaaaapayJ9.NZwDs0U_fubYS"
        "OmYNJAI9ufgoC84zXOCzZkxclWBVXhb1dBVQHpO-VZW-lworDvKxX_BWqagKYTq"
        "wc4ELBcKTQ")

    environ = werkzeug_test.EnvironBuilder(
        path="/",
        headers={
            "X-Goog-IAP-JWT-Assertion": assertion_header
        },
    ).get_environ()
    request = wsgiapp.HttpRequest(environ)

    def Handler(request, *args, **kwargs):
      del request, args, kwargs  # Unused.

      self.fail("Handler shouldn't have been executed.")

    manager = webauth.IAPWebAuthManager()
    response = manager.SecurityCheck(Handler, request)

    mock_get.assert_called_once_with(
        "https://www.gstatic.com/iap/verify/public_key")
    self.assertEqual(response.status_code, 401)

  @mock.patch.object(
      validate_iap,
      "ValidateIapJwtFromComputeEngine",
      return_value=("temp", "temp"))
  def testSuccessfulKey(self, mock_method):
    """Validate account creation upon successful JWT Authentication."""

    environ = werkzeug_test.EnvironBuilder(
        path="/", headers={
            "X-Goog-IAP-JWT-Assertion": ("valid_key")
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    def Handler(request, *args, **kwargs):
      del args, kwargs  # Unused.

      self.assertEqual(request.user, "temp")
      return http_response.HttpResponse("success", status=200)

    manager = webauth.IAPWebAuthManager()
    response = manager.SecurityCheck(Handler, request)

    self.assertEqual(response.status_code, 200)


class BasicWebAuthManagerTest(test_lib.GRRBaseTest):

  def _SetupUser(self, user, password):
    data_store.REL_DB.WriteGRRUser(user, password)

  def testSecurityCheckUnicode(self):
    user = "żymścimił"
    # TODO(hanuszczak): Test password with unicode characters as well. Currently
    # this will not work because `CryptedPassword` is broken and does not work
    # with unicode objects.
    password = "quux"

    self._SetupUser(user, password)

    authorization = "{user}:{password}".format(user=user, password=password)
    token = base64.b64encode(authorization.encode("utf-8")).decode("ascii")
    environ = werkzeug_test.EnvironBuilder(
        path="/foo", headers={
            "Authorization": "Basic %s" % token,
        }).get_environ()
    request = wsgiapp.HttpRequest(environ)

    def Handler(request, *args, **kwargs):
      del args, kwargs  # Unused.

      self.assertEqual(request.user, user)
      return http_response.HttpResponse(b"foobar", status=200)

    manager = webauth.BasicWebAuthManager()
    response = manager.SecurityCheck(Handler, request)

    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.get_data(), b"foobar")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
