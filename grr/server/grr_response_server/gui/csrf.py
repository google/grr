#!/usr/bin/env python
"""CSRF token generation logic.

This module provides a CSRF token generator and validator that can be used to
protect against cross-site request forgery (CSRF) attacks.
"""

import abc
import base64
import hashlib
import hmac
import logging
from typing import Optional

from cryptography.hazmat.primitives import constant_time
from werkzeug import exceptions as werkzeug_exceptions

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server.gui import http_request
from grr_response_server.gui import http_response


CSRF_DELIMITER = b":"
CSRF_TOKEN_DURATION = rdfvalue.Duration.From(10, rdfvalue.HOURS)


class CSRFTokenGenerator(abc.ABC):
  """CSRF token generator defines the interface for generating and validating CSRF tokens."""

  @abc.abstractmethod
  def GenerateCSRFToken(
      self, user_id: str, time: Optional[rdfvalue.RDFDatetime]
  ) -> bytes:
    """Generates a CSRF token based on a secret key, id and time."""
    raise NotImplementedError()

  @abc.abstractmethod
  def ValidateCSRFTokenContents(
      self, csrf_token: bytes, user_id: str
  ) -> rdfvalue.RDFDatetime:
    """Validates that the given token is valid for the given user.

    Args:
      csrf_token: The CSRF token to validate.
      user_id: The user ID to validate the token for.

    Returns:
      The time associated with the token, generally it's creation time.
    """
    raise NotImplementedError()


class RawKeyCSRFTokenGenerator(CSRFTokenGenerator):
  """Generates and validates CSRF tokens using a raw key."""

  def GenerateCSRFToken(
      self, user_id: str, time: Optional[rdfvalue.RDFDatetime]
  ) -> bytes:
    """Generates a CSRF token based on a secret key, id and time."""

    time_usecs = (time or rdfvalue.RDFDatetime.Now()).AsMicrosecondsSinceEpoch()

    secret = config.CONFIG.Get("AdminUI.csrf_secret_key", None)
    if secret is None:
      raise ValueError("CSRF secret not available.")
    digester = hmac.new(secret.encode("ascii"), digestmod=hashlib.sha256)
    digester.update(user_id.encode("ascii"))
    digester.update(CSRF_DELIMITER)
    digester.update(str(time_usecs).encode("ascii"))
    digest = digester.digest()

    token = base64.urlsafe_b64encode(
        b"%s%s%d" % (digest, CSRF_DELIMITER, time_usecs)
    )
    return token.rstrip(b"=")

  def ValidateCSRFTokenContents(
      self, csrf_token: bytes, user_id: str
  ) -> rdfvalue.RDFDatetime:
    """Validates that the given token is valid for the given user and time.

    Args:
      csrf_token: The CSRF token to validate.
      user_id: The user ID to validate the token for.

    Returns:
      The time associated with the token, generally it's creation time.
    """
    try:
      decoded = base64.urlsafe_b64decode(csrf_token + b"==")
      _, token_time_bytes = decoded.rsplit(CSRF_DELIMITER, 1)
      token_time = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          int(token_time_bytes)
      )
    except ValueError as exc:
      logging.info("Malformed CSRF token for: %s", csrf_token)
      raise werkzeug_exceptions.Forbidden("Malformed CSRF token") from exc

    expected = self.GenerateCSRFToken(user_id, token_time)
    if not constant_time.bytes_eq(csrf_token, expected):
      raise werkzeug_exceptions.Forbidden("Non-matching CSRF token")

    return token_time


def StoreCSRFCookie(
    user: str,
    response: http_response.HttpResponse,
    csrf_token_generator: CSRFTokenGenerator,
) -> None:
  """Decorator for WSGI handler that inserts CSRF cookie into response."""

  csrf_token = csrf_token_generator.GenerateCSRFToken(user, None)
  response.set_cookie(
      "csrftoken",
      csrf_token.decode("ascii"),
      max_age=CSRF_TOKEN_DURATION.ToInt(rdfvalue.SECONDS),
  )


def ValidateCSRFTokenOrRaise(
    request: http_request.HttpRequest, csrf_token_generator: CSRFTokenGenerator
) -> None:
  """Checks CSRF cookie against the request."""

  # CSRF check doesn't make sense for GET/HEAD methods, because they can
  # (and are) used when downloading files through <a href> links - and
  # there's no way to set X-CSRFToken header in this case.
  if request.method in ("GET", "HEAD"):
    return

  # In the ideal world only JavaScript can be used to add a custom header, and
  # only within its origin. By default, browsers don't allow JavaScript to
  # make cross origin requests.
  #
  # Unfortunately, in the real world due to bugs in browsers plugins, it can't
  # be guaranteed that a page won't set an HTTP request with a custom header
  # set. That's why we also check the contents of a header via an HMAC check
  # with a server-stored secret.
  #
  # See for more details:
  # https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)_Prevention_Cheat_Sheet
  # (Protecting REST Services: Use of Custom Request Headers).
  csrf_token = request.headers.get("X-CSRFToken", "").encode("ascii")
  if not csrf_token:
    logging.info("Did not find headers CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("CSRF token is missing")

  token_time = csrf_token_generator.ValidateCSRFTokenContents(
      csrf_token, request.user
  )

  current_time = rdfvalue.RDFDatetime.Now()
  if current_time - token_time > CSRF_TOKEN_DURATION:
    logging.info("Expired CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Expired CSRF token")
