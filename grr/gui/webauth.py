#!/usr/bin/env python
"""Web authentication classes for the GUI."""

import logging


from oauth2client import client
from oauth2client import crypt

from werkzeug import utils as werkzeug_utils
from werkzeug import wrappers as werkzeug_wrappers

from grr import config
from grr.lib import registry
from grr.server import access_control
from grr.server import aff4

from grr.server.aff4_objects import users as aff4_users


class BaseWebAuthManager(object):
  """A class managing web authentication.

  This class is responsible for deciding if the user will have access to the web
  interface and for generating the token that will be passed to the functions
  that deal with data.

  Checks are done using a decorator function.
  """

  __metaclass__ = registry.MetaclassRegistry

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


class BasicWebAuthManager(BaseWebAuthManager):
  """Manager using basic auth using the config file."""

  def SecurityCheck(self, func, request, *args, **kwargs):
    """Wrapping function."""
    request.user = ""

    authorized = False
    try:
      auth_type, authorization = request.headers.get("Authorization",
                                                     " ").split(" ", 1)

      if auth_type == "Basic":
        user, password = authorization.decode("base64").split(":", 1)
        token = access_control.ACLToken(username=user)

        fd = aff4.FACTORY.Open(
            "aff4:/users/%s" % user, aff4_type=aff4_users.GRRUser, token=token)
        crypted_password = fd.Get(fd.Schema.PASSWORD)
        if crypted_password and crypted_password.CheckPassword(password):
          authorized = True

          # The password is ok - update the user
          request.user = user

    except (IndexError, KeyError, IOError, access_control.UnauthorizedAccess):
      pass

    if not authorized:
      result = werkzeug_wrappers.Response("Unauthorized", status=401)
      result.headers["WWW-Authenticate"] = "Basic realm='Secure Area'"
      return result

    # Modify this to implement additional checking (e.g. enforce SSL).
    response = func(request, *args, **kwargs)
    return response


class FirebaseWebAuthManager(BaseWebAuthManager):
  """Manager using Firebase auth service."""

  BEARER_PREFIX = "Bearer "
  SECURE_TOKEN_PREFIX = "https://securetoken.google.com/"
  CERT_URI = ("https://www.googleapis.com/robot/v1/metadata/x509/"
              "securetoken@system.gserviceaccount.com")

  def __init__(self, *args, **kwargs):
    super(FirebaseWebAuthManager, self).__init__(*args, **kwargs)

    def_router = config.CONFIG["API.DefaultRouter"]
    if def_router != "DisabledApiCallRouter":
      raise RuntimeError("Using FirebaseWebAuthManager with API.DefaultRouter "
                         "being anything but DisabledApiCallRouter means "
                         "risking opening your GRR UI/API to the world. "
                         "Current setting is: %s" % def_router)

  def AuthError(self, message):
    return werkzeug_wrappers.Response(message, status=403)

  def SecurityCheck(self, func, request, *args, **kwargs):
    """Check if access should be allowed for the request."""

    try:
      auth_header = request.headers.get("Authorization", "")
      if not auth_header.startswith(self.BEARER_PREFIX):
        raise crypt.AppIdentityError("JWT token is missing.")

      token = auth_header[len(self.BEARER_PREFIX):]

      auth_domain = config.CONFIG["AdminUI.firebase_auth_domain"]
      project_id = auth_domain.split(".")[0]

      idinfo = client.verify_id_token(token, project_id, cert_uri=self.CERT_URI)

      if idinfo["iss"] != self.SECURE_TOKEN_PREFIX + project_id:
        raise crypt.AppIdentityError("Wrong issuer.")

      request.user = idinfo["email"]
    except crypt.AppIdentityError as e:
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
    super(NullWebAuthManager, self).__init__(*args, **kwargs)
    self.username = "gui_user"

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


class WebAuthInit(registry.InitHook):

  def RunOnce(self):
    """Run this once on init."""
    global WEBAUTH_MANAGER  # pylint: disable=global-statement

    # pylint: disable=g-bad-name
    WEBAUTH_MANAGER = BaseWebAuthManager.GetPlugin(
        config.CONFIG["AdminUI.webauth_manager"])()

    # pylint: enable=g-bad-name
    logging.info("Using webauth manager %s", WEBAUTH_MANAGER)
