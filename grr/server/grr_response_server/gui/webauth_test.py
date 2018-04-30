#!/usr/bin/env python
"""Tests for the web auth managers."""


import mock

from werkzeug import test as werkzeug_test
from werkzeug import wrappers as werkzeug_wrappers

from google.oauth2 import id_token

from grr.lib import flags
from grr.server.grr_response_server.gui import webauth
from grr.server.grr_response_server.gui import wsgiapp
from grr.test_lib import test_lib


class RemoteUserWebAuthManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(RemoteUserWebAuthManagerTest, self).setUp()

    self.manager = webauth.RemoteUserWebAuthManager()
    self.success_response = werkzeug_wrappers.Response("foobar")

  def HandlerStub(self, request, *args, **kwargs):
    _ = args
    _ = kwargs

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
    self.assertEqual(
        response.get_data(as_text=True),
        "Request sent from an IP not in AdminUI.remote_user_trusted_ips.")

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


class FirebaseWebAuthManagerTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(FirebaseWebAuthManagerTest, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({
        "AdminUI.firebase_auth_domain": "foo-bar.firebaseapp.com",
        "API.DefaultRouter": "DisabledApiCallRouter"
    })
    self.config_overrider.Start()

    self.manager = webauth.FirebaseWebAuthManager()
    self.success_response = werkzeug_wrappers.Response("foobar")

    self.checked_request = None

  def HandlerStub(self, request, *args, **kwargs):
    _ = args
    _ = kwargs

    self.checked_request = request

    return self.success_response

  def tearDown(self):
    super(FirebaseWebAuthManagerTest, self).tearDown()
    self.config_overrider.Stop()

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
      id_token, "verify_firebase_token", return_value={
          "iss": "blah"
      })
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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
