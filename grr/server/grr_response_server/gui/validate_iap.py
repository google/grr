#!/usr/bin/env python
"""Sample showing how to validate the Identity-Aware Proxy (IAP) JWT.

This code should be used by applications in Google Compute Engine-based
environments (such as Google App Engine flexible environment, Google
Compute Engine, or Google Container Engine) to provide an extra layer
of assurance that a request was authorized by IAP.

For applications running in the App Engine standard environment, use
App Engine's Users API instead.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import jwt
import requests

# Used to cache the Identity-Aware Proxy public keys.  This code only
# refetches the file when a JWT is signed with a key not present in
# this cache.
_KEY_CACHE = {}


class Error(Exception):
  pass


class KeysCanNotBeFetchedError(Error):
  pass


class KeyNotFoundError(Error):
  pass


class IAPValidationFailedError(Error):
  pass


def ValidateIapJwtFromComputeEngine(iap_jwt, cloud_project_number,
                                    backend_service_id):
  """Validates an IAP JWT for your (Compute|Container) Engine service.

  Args:
    iap_jwt: The contents of the X-Goog-IAP-JWT-Assertion header.
    cloud_project_number: The project *number* for your Google Cloud project.
      This is returned by 'gcloud projects describe $PROJECT_ID', or in the
      Project Info card in Cloud Console.
    backend_service_id: The ID of the backend service used to access the
      application. See https://cloud.google.com/iap/docs/signed-headers-howto
        for details on how to get this value.

  Returns:
    A tuple of (user_id, user_email).

  Raises:
    IAPValidationFailedError: if the validation has failed.
  """
  expected_audience = "/projects/{}/global/backendServices/{}".format(
      cloud_project_number, backend_service_id)
  return ValidateIapJwt(iap_jwt, expected_audience)


def ValidateIapJwt(iap_jwt, expected_audience):
  """Validates an IAP JWT."""

  try:
    key_id = jwt.get_unverified_header(iap_jwt).get("kid")
    if not key_id:
      raise IAPValidationFailedError("No key ID")
    key = GetIapKey(key_id)
    decoded_jwt = jwt.decode(
        iap_jwt, key, algorithms=["ES256"], audience=expected_audience)
    return (decoded_jwt["sub"], decoded_jwt["email"])
  except (jwt.exceptions.InvalidTokenError,
          requests.exceptions.RequestException) as e:
    raise IAPValidationFailedError(e)


def GetIapKey(key_id):
  """Retrieves a public key from the list published by Identity-Aware Proxy.

  The key file is re-fetched if necessary.

  Args:
    key_id: Key id.

  Returns:
    String with a key.

  Raises:
    KeyNotFoundError: if the key is not found in the key file.
    KeysCanNotBeFetchedError: if the key file can't be fetched.
  """
  global _KEY_CACHE
  key = _KEY_CACHE.get(key_id)
  if not key:
    # Re-fetch the key file.
    resp = requests.get("https://www.gstatic.com/iap/verify/public_key")
    if resp.status_code != 200:
      raise KeysCanNotBeFetchedError(
          "Unable to fetch IAP keys: {} / {} / {}".format(
              resp.status_code, resp.headers, resp.text))
    _KEY_CACHE = resp.json()
    key = _KEY_CACHE.get(key_id)
    if not key:
      raise KeyNotFoundError("Key {!r} not found".format(key_id))
  return key
