#!/usr/bin/env python
"""Tests for CSRF protection logic."""

import json
from unittest import mock

from absl import app
import requests

from grr_response_core.lib import rdfvalue
from grr_response_server.gui import api_integration_test_lib
from grr_response_server.gui import csrf
from grr_response_server.gui import webauth
from grr.test_lib import test_lib


class CSRFProtectionTest(api_integration_test_lib.ApiIntegrationTest):
  """Tests GRR's CSRF protection logic for the HTTP API."""

  def setUp(self):
    super().setUp()

    self.base_url = self.endpoint

  def testGETRequestWithoutCSRFTokenAndRequestedWithHeaderSucceeds(self):
    response = requests.get(self.base_url + "/api/v2/config")
    self.assertEqual(response.status_code, 200)
    # Assert XSSI protection is in place.
    self.assertEqual(response.text[:5], ")]}'\n")

  def testHEADRequestForGETUrlWithoutTokenAndRequestedWithHeaderSucceeds(self):
    response = requests.head(self.base_url + "/api/v2/config")
    self.assertEqual(response.status_code, 200)

  def testHEADRequestNotEnabledForPOSTUrls(self):
    response = requests.head(self.base_url + "/api/v2/clients/labels/add")
    self.assertEqual(response.status_code, 405)

  def testHEADRequestNotEnabledForDeleteUrls(self):
    response = requests.head(
        self.base_url + "/api/v2/users/me/notifications/pending/0"
    )
    self.assertEqual(response.status_code, 405)

  def testPOSTRequestWithoutCSRFTokenFails(self):
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}

    response = requests.post(
        self.base_url + "/api/v2/clients/labels/add", data=json.dumps(data)
    )

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testPOSTRequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/v2/clients/labels/add",
        data=json.dumps(data),
        cookies=cookies,
    )

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testPOSTRequestWithCSRFTokenInHeadersAndCookiesSucceeds(self):
    client_id = self.SetupClient(0)

    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    data = {"client_ids": [client_id], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/v2/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies,
    )
    self.assertEqual(response.status_code, 200)

  def testPOSTRequestFailsIfCSRFTokenIsExpired(self):
    client_id = self.SetupClient(0)

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)):
      index_response = requests.get(self.base_url)
      csrf_token = index_response.cookies.get("csrftoken")

      headers = {"x-csrftoken": csrf_token}
      data = {"client_ids": [client_id], "labels": ["foo", "bar"]}
      cookies = {"csrftoken": csrf_token}

      response = requests.post(
          self.base_url + "/api/v2/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies,
      )
      self.assertEqual(response.status_code, 200)

    # This should still succeed as we use strict check in wsgiapp.py:
    # current_time - token_time > CSRF_TOKEN_DURATION.microseconds
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)
        + csrf.CSRF_TOKEN_DURATION.ToInt(rdfvalue.SECONDS)
    ):
      response = requests.post(
          self.base_url + "/api/v2/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies,
      )
      self.assertEqual(response.status_code, 200)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)
        + csrf.CSRF_TOKEN_DURATION.ToInt(rdfvalue.SECONDS)
        + 1
    ):
      response = requests.post(
          self.base_url + "/api/v2/clients/labels/add",
          headers=headers,
          data=json.dumps(data),
          cookies=cookies,
      )
      self.assertEqual(response.status_code, 403)
      self.assertIn("Expired CSRF token", response.text)

  def testPOSTRequestFailsIfCSRFTokenIsMalformed(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token + "BLAH"}
    data = {"client_ids": ["C.0000000000000000"], "labels": ["foo", "bar"]}
    cookies = {"csrftoken": csrf_token}

    response = requests.post(
        self.base_url + "/api/v2/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies,
    )
    self.assertEqual(response.status_code, 403)
    self.assertIn("Malformed", response.text)

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
        self.base_url + "/api/v2/clients/labels/add",
        headers=headers,
        data=json.dumps(data),
        cookies=cookies,
    )
    self.assertEqual(response.status_code, 403)
    self.assertIn("Non-matching", response.text)

  def testDELETERequestWithoutCSRFTokenFails(self):
    response = requests.delete(
        self.base_url + "/api/v2/users/me/notifications/pending/0"
    )

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testDELETERequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    cookies = {"csrftoken": csrf_token}

    response = requests.delete(
        self.base_url + "/api/v2/users/me/notifications/pending/0",
        cookies=cookies,
    )

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testDELETERequestWithCSRFTokenInCookiesAndHeadersSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    cookies = {"csrftoken": csrf_token}

    response = requests.delete(
        self.base_url + "/api/v2/users/me/notifications/pending/0",
        headers=headers,
        cookies=cookies,
    )

    self.assertEqual(response.status_code, 200)

  def testPATCHRequestWithoutCSRFTokenFails(self):
    response = requests.patch(self.base_url + "/api/v2/hunts/H:123456")

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testPATCHRequestWithCSRFTokenInCookiesAndNotInHeadersFails(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    cookies = {"csrftoken": csrf_token}

    response = requests.patch(
        self.base_url + "/api/v2/hunts/H:123456", cookies=cookies
    )

    self.assertEqual(response.status_code, 403)
    self.assertIn("CSRF", response.text)

  def testPATCHRequestWithCSRFTokenInCookiesAndHeadersSucceeds(self):
    # Fetch csrf token from the cookie set on the main page.
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    headers = {"x-csrftoken": csrf_token}
    cookies = {"csrftoken": csrf_token}

    response = requests.patch(
        self.base_url + "/api/v2/hunts/H:123456",
        headers=headers,
        cookies=cookies,
    )

    # We consider 404 to be a normal response here.
    # Hunt H:123456 doesn't exist.
    self.assertEqual(response.status_code, 404)

  def testCSRFTokenIsUpdatedIfNotPresentInCookies(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")
    self.assertTrue(csrf_token)

    # Check that calling GetGrrUser method doesn't update the cookie.
    get_user_response = requests.get(self.base_url + "/api/v2/users/me")
    csrf_token_2 = get_user_response.cookies.get("csrftoken")
    self.assertTrue(csrf_token_2)

    self.assertNotEqual(csrf_token, csrf_token_2)

  def testCSRFTokenIsNotUpdtedIfUserIsUnknown(self):
    fake_manager = webauth.NullWebAuthManager()
    fake_manager.SetUserName("")
    with mock.patch.object(webauth, "WEBAUTH_MANAGER", fake_manager):
      index_response = requests.get(self.base_url)
      csrf_token = index_response.cookies.get("csrftoken")
      self.assertIsNone(csrf_token)

  def testGetPendingUserNotificationCountMethodRefreshesCSRFToken(self):
    index_response = requests.get(self.base_url)
    csrf_token = index_response.cookies.get("csrftoken")

    # Check that calling GetGrrUser method doesn't update the cookie.
    get_user_response = requests.get(
        self.base_url + "/api/v2/users/me", cookies={"csrftoken": csrf_token}
    )
    csrf_token_2 = get_user_response.cookies.get("csrftoken")

    self.assertIsNone(csrf_token_2)

    # Check that calling GetPendingUserNotificationsCount refreshes the
    # token.
    notifications_response = requests.get(
        self.base_url + "/api/v2/users/me/notifications/pending/count",
        cookies={"csrftoken": csrf_token},
    )
    csrf_token_3 = notifications_response.cookies.get("csrftoken")

    self.assertTrue(csrf_token_3)
    self.assertNotEqual(csrf_token, csrf_token_3)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
