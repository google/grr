#!/usr/bin/env python
# Lint as: python3
"""Web authentication classes for the GUI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import logging

from werkzeug import utils as werkzeug_utils

from google.oauth2 import id_token

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.registry import MetaclassRegistry
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import http_response
from grr_response_server.gui import validate_iap


class BaseWebAuthManager(metaclass=MetaclassRegistry):
  """A class managing web authentication.

  This class is responsible for deciding if the user will have access to the web
  interface and for generating the token that will be passed to the functions
  that deal with data.

  Checks are done using a decorator function.
  """

  def SecurityCheck(self, func, request, *args, **kwargs):
    """A decorator applied to protected web handlers.

    Args:
      func: The wrapped function to call.
      request: The web request.
      *args: Passthrough to wrapped function.
      **kwargs: Passthrough to wrapped function.

    Returns:
      A WSGI http response object.

    This will get called for all requests that get passed through one of our
    handlers that is wrapped in @SecurityCheck.
    """

  def RedirectBase(self):
    """Return a redirect to the main GRR page."""
    return werkzeug_utils.redirect(config.CONFIG["AdminUI.url"])


class IAPWebAuthManager(BaseWebAuthManager):
  """Auth Manager for Google IAP.

  This extension pulls the x-goog-iap-jwt-assertion header and generates
  a new user for that header via the 'sub' claim. Authorization is now
  delegated to IAP.
  """

  IAP_HEADER = "x-goog-iap-jwt-assertion"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if (config.CONFIG["AdminUI.google_cloud_project_id"] is None or
        config.CONFIG["AdminUI.google_cloud_backend_service_id"] is None):
      raise RuntimeError(
          "The necessary Cloud IAP configuration options are"
          "not set. Please set your AdminUI.google_cloud_project_id"
          "or AdminUI.google_cloud_backend_service_id keys.")

    self.cloud_project_id = config.CONFIG["AdminUI.google_cloud_project_id"]
    self.backend_service_id = config.CONFIG[
        "AdminUI.google_cloud_backend_service_id"]

  def SecurityCheck(self, func, request, *args, **kwargs):
    """Wrapping function."""
    if self.IAP_HEADER not in request.headers:
      return http_response.HttpResponse("Unauthorized", status=401)

    jwt = request.headers.get(self.IAP_HEADER)
    try:
      request.user, _ = validate_iap.ValidateIapJwtFromComputeEngine(
          jwt, self.cloud_project_id, self.backend_service_id)
      return func(request, *args, **kwargs)

    except validate_iap.IAPValidationFailedError as e:
      # Return failure if IAP is not decoded correctly.
      logging.error("IAPWebAuthManager failed with: %s", e)
      return http_response.HttpResponse("Unauthorized", status=401)


class BasicWebAuthManager(BaseWebAuthManager):
  """Manager using basic auth using the config file."""

  def SecurityCheck(self, func, request, *args, **kwargs):
    """Wrapping function."""
    request.user = u""

    authorized = False
    try:
      auth_type, authorization = request.headers.get("Authorization",
                                                     " ").split(" ", 1)

      if auth_type == "Basic":
        authorization_string = base64.b64decode(authorization).decode("utf-8")
        user, password = authorization_string.split(":", 1)

        try:
          user_obj = data_store.REL_DB.ReadGRRUser(user)
          if user_obj.password.CheckPassword(password):
            authorized = True

            # The password is ok - update the user
            request.user = user

        except db.UnknownGRRUserError:
          pass

    except access_control.UnauthorizedAccess as e:
      logging.warning("UnauthorizedAccess: %s for %s", e, request)
    except (IndexError, KeyError, IOError):
      pass

    if not authorized:
      result = http_response.HttpResponse("Unauthorized", status=401)
      result.headers["WWW-Authenticate"] = "Basic realm='Secure Area'"
      return result

    # Modify this to implement additional checking (e.g. enforce SSL).
    return func(request, *args, **kwargs)


class RemoteUserWebAuthManager(BaseWebAuthManager):
  """Manager that reads remote username from HTTP headers.

  NOTE: This manager should only be used when GRR UI runs behind an
  reverse http proxy (Apache, Nginx, etc). It assumes that
  authentication is done by the reverse http proxy server and the
  authenticated username is passed to GRR via a HTTP header.
  """

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.remote_user_header = config.CONFIG["AdminUI.remote_user_header"]
    self.remote_email_header = config.CONFIG["AdminUI.remote_email_header"]
    self.trusted_ips = config.CONFIG["AdminUI.remote_user_trusted_ips"]

  def AuthError(self, message):
    return http_response.HttpResponse(message, status=403)

  def SecurityCheck(self, func, request, *args, **kwargs):
    if request.remote_addr not in self.trusted_ips:
      return self.AuthError("Request sent from an IP not in "
                            "AdminUI.remote_user_trusted_ips. "
                            "Source was %s" % request.remote_addr)

    try:
      username = request.headers[self.remote_user_header]
    except KeyError:
      return self.AuthError("No username header found.")

    if not username:
      return self.AuthError("Empty username is not allowed.")

    request.user = username

    if config.CONFIG["Email.enable_custom_email_address"]:
      try:
        request.email = request.headers[self.remote_email_header]
      except KeyError:
        pass

    return func(request, *args, **kwargs)


class FirebaseWebAuthManager(BaseWebAuthManager):
  """Manager using Firebase auth service."""

  BEARER_PREFIX = "Bearer "
  SECURE_TOKEN_PREFIX = "https://securetoken.google.com/"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    def_router = config.CONFIG["API.DefaultRouter"]
    if def_router != "DisabledApiCallRouter":
      raise RuntimeError("Using FirebaseWebAuthManager with API.DefaultRouter "
                         "being anything but DisabledApiCallRouter means "
                         "risking opening your GRR UI/API to the world. "
                         "Current setting is: %s" % def_router)

  def AuthError(self, message):
    return http_response.HttpResponse(message, status=403)

  def SecurityCheck(self, func, request, *args, **kwargs):
    """Check if access should be allowed for the request."""

    try:
      auth_header = request.headers.get("Authorization", "")
      if not auth_header.startswith(self.BEARER_PREFIX):
        raise ValueError("JWT token is missing.")

      token = auth_header[len(self.BEARER_PREFIX):]

      auth_domain = config.CONFIG["AdminUI.firebase_auth_domain"]
      project_id = auth_domain.split(".")[0]

      idinfo = id_token.verify_firebase_token(
          token, request, audience=project_id)

      if idinfo["iss"] != self.SECURE_TOKEN_PREFIX + project_id:
        raise ValueError("Wrong issuer.")

      request.user = idinfo["email"]
    except ValueError as e:
      # For a homepage, just do a pass-through, otherwise JS code responsible
      # for the Firebase auth won't ever get executed. This approach is safe,
      # because wsgiapp.HttpRequest object will raise on any attempt to
      # access uninitialized HttpRequest.user attribute.
      if request.path != "/":
        return self.AuthError("JWT token validation failed: %s" % e)

    return func(request, *args, **kwargs)


class NullWebAuthManager(BaseWebAuthManager):
  """Null web auth manager always returns test user unless set."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.username = u"gui_user"

  def SetUserName(self, username):
    self.username = username

  def SecurityCheck(self, func, request, *args, **kwargs):
    """A decorator applied to protected web handlers."""
    request.user = self.username
    request.token = access_control.ACLToken(
        username="Testing", reason="Just a test")
    return func(request, *args, **kwargs)


# Global to store the configured web auth manager.
WEBAUTH_MANAGER = None


def SecurityCheck(func):
  """A decorator applied to protected web handlers."""

  def Wrapper(request, *args, **kwargs):
    """Wrapping function."""
    if WEBAUTH_MANAGER is None:
      raise RuntimeError("Attempt to initialize before WEBAUTH_MANAGER set.")
    return WEBAUTH_MANAGER.SecurityCheck(func, request, *args, **kwargs)

  return Wrapper


def InitializeWebAuth():
  """Initializes WebAuth."""
  global WEBAUTH_MANAGER  # pylint: disable=global-statement

  # pylint: disable=g-bad-name
  WEBAUTH_MANAGER = BaseWebAuthManager.GetPlugin(
      config.CONFIG["AdminUI.webauth_manager"])()

  # pylint: enable=g-bad-name
  logging.info("Using webauth manager %s", WEBAUTH_MANAGER)


@utils.RunOnce
def InitializeWebAuthOnce():
  """Initializes WebAuth once only."""
  InitializeWebAuth()
