#!/usr/bin/env python
"""GRR HTTP server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import hashlib
import hmac
import logging
import os
import string

from cryptography.hazmat.primitives import constant_time

from future.builtins import int

import jinja2
import psutil

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug import wsgi as werkzeug_wsgi

from grr_response_core import config
from grr_response_core.lib import rdfvalue

from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_server import access_control
from grr_response_server import server_logging
from grr_response_server.gui import http_api
from grr_response_server.gui import webauth

CSRF_DELIMITER = b":"
CSRF_TOKEN_DURATION = rdfvalue.Duration("10h")


def GenerateCSRFToken(user_id, time):
  """Generates a CSRF token based on a secret key, id and time."""
  precondition.AssertType(user_id, unicode)
  precondition.AssertOptionalType(time, int)

  time = time or rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

  secret = config.CONFIG.Get("AdminUI.csrf_secret_key", None)
  # TODO(amoser): Django is deprecated. Remove this at some point.
  if not secret:
    secret = config.CONFIG["AdminUI.django_secret_key"]
  digester = hmac.new(secret.encode("ascii"), digestmod=hashlib.sha256)
  digester.update(user_id.encode("ascii"))
  digester.update(CSRF_DELIMITER)
  digester.update(unicode(time).encode("ascii"))
  digest = digester.digest()

  token = base64.urlsafe_b64encode(b"%s%s%d" % (digest, CSRF_DELIMITER, time))
  return token.rstrip(b"=")


def StoreCSRFCookie(user, response):
  """Decorator for WSGI handler that inserts CSRF cookie into response."""

  csrf_token = GenerateCSRFToken(user, None)
  response.set_cookie(
      "csrftoken", csrf_token, max_age=CSRF_TOKEN_DURATION.seconds)


def ValidateCSRFTokenOrRaise(request):
  """Decorator for WSGI handler that checks CSRF cookie against the request."""

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

  try:
    decoded = base64.urlsafe_b64decode(csrf_token + b"==")
    digest, token_time = decoded.rsplit(CSRF_DELIMITER, 1)
    token_time = int(token_time)
  except (TypeError, ValueError):
    logging.info("Malformed CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Malformed CSRF token")

  if len(digest) != hashlib.sha256().digest_size:
    logging.info("Invalid digest size for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Malformed CSRF token digest")

  expected = GenerateCSRFToken(request.user, token_time)
  if not constant_time.bytes_eq(csrf_token, expected):
    logging.info("Non-matching CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Non-matching CSRF token")

  current_time = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()
  if current_time - token_time > CSRF_TOKEN_DURATION.microseconds:
    logging.info("Expired CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Expired CSRF token")


class RequestHasNoUser(AttributeError):
  """Error raised when accessing a user of an unautenticated request."""


class HttpRequest(werkzeug_wrappers.Request):
  """HTTP request object to be used in GRR."""

  def __init__(self, *args, **kwargs):
    super(HttpRequest, self).__init__(*args, **kwargs)

    self._user = None
    self.token = None

    self.timestamp = rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

    self.method_metadata = None
    self.parsed_args = None

  @property
  def user(self):
    if self._user is None:
      raise RequestHasNoUser(
          "Trying to access Request.user while user is unset.")

    if not self._user:
      raise RequestHasNoUser(
          "Trying to access Request.user while user is empty.")

    return self._user

  @user.setter
  def user(self, value):
    if not isinstance(value, unicode):
      message = "Expected instance of '%s' but got value '%s' of type '%s'"
      message %= (unicode, value, type(value))
      raise TypeError(message)

    self._user = value


def LogAccessWrapper(func):
  """Decorator that ensures that HTTP access is logged."""

  def Wrapper(request, *args, **kwargs):
    """Wrapping function."""
    try:
      response = func(request, *args, **kwargs)
      server_logging.LOGGER.LogHttpAdminUIAccess(request, response)
    except Exception:  # pylint: disable=g-broad-except
      # This should never happen: wrapped function is supposed to handle
      # all possible exceptions and generate a proper Response object.
      # Still, handling exceptions here to guarantee that the access is logged
      # no matter what.
      response = werkzeug_wrappers.Response("", status=500)
      server_logging.LOGGER.LogHttpAdminUIAccess(request, response)
      raise

    return response

  return Wrapper


def EndpointWrapper(func):
  return webauth.SecurityCheck(LogAccessWrapper(func))


class AdminUIApp(object):
  """Base class for WSGI GRR app."""

  def __init__(self):
    self.routing_map = werkzeug_routing.Map()
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/",
            methods=["HEAD", "GET"],
            endpoint=EndpointWrapper(self._HandleHomepage)))
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/api/<path:path>",
            methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"],
            endpoint=EndpointWrapper(self._HandleApi)))
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/help/<path:path>",
            methods=["HEAD", "GET"],
            endpoint=EndpointWrapper(self._HandleHelp)))

  def _BuildRequest(self, environ):
    return HttpRequest(environ)

  def _BuildToken(self, request, execution_time):
    """Build an ACLToken from the request."""
    token = access_control.ACLToken(
        username=request.user,
        reason=request.args.get("reason", ""),
        process="GRRAdminUI",
        expiry=rdfvalue.RDFDatetime.Now() + execution_time)

    for field in ["Remote_Addr", "X-Forwarded-For"]:
      remote_addr = request.headers.get(field, "")
      if remote_addr:
        token.source_ips.append(remote_addr)
    return token

  def _HandleHomepage(self, request):
    """Renders GRR home page by rendering base.html Jinja template."""

    _ = request

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.CONFIG["AdminUI.template_root"]),
        autoescape=True)

    create_time = psutil.Process(os.getpid()).create_time()
    context = {
        "heading":
            config.CONFIG["AdminUI.heading"],
        "report_url":
            config.CONFIG["AdminUI.report_url"],
        "help_url":
            config.CONFIG["AdminUI.help_url"],
        "timestamp":
            utils.SmartStr(create_time),
        "use_precompiled_js":
            config.CONFIG["AdminUI.use_precompiled_js"],
        # Used in conjunction with FirebaseWebAuthManager.
        "firebase_api_key":
            config.CONFIG["AdminUI.firebase_api_key"],
        "firebase_auth_domain":
            config.CONFIG["AdminUI.firebase_auth_domain"],
        "firebase_auth_provider":
            config.CONFIG["AdminUI.firebase_auth_provider"],
        "grr_version":
            config.CONFIG["Source.version_string"]
    }
    template = env.get_template("base.html")
    response = werkzeug_wrappers.Response(
        template.render(context), mimetype="text/html")

    # For a redirect-based Firebase authentication scheme we won't have any
    # user information at this point - therefore checking if the user is
    # present.
    try:
      StoreCSRFCookie(request.user, response)
    except RequestHasNoUser:
      pass

    return response

  def _HandleApi(self, request):
    """Handles API requests."""
    # Checks CSRF token. CSRF token cookie is updated when homepage is visited
    # or via GetPendingUserNotificationsCount API call.
    ValidateCSRFTokenOrRaise(request)

    response = http_api.RenderHttpResponse(request)

    # GetPendingUserNotificationsCount is an API method that is meant
    # to be invoked very often (every 10 seconds). So it's ideal
    # for updating the CSRF token.
    # We should also store the CSRF token if it wasn't yet stored at all.
    if (("csrftoken" not in request.cookies) or response.headers.get(
        "X-API-Method", "") == "GetPendingUserNotificationsCount"):
      StoreCSRFCookie(request.user, response)

    return response

  def _RedirectToRemoteHelp(self, path):
    """Redirect to GitHub-hosted documentation."""
    allowed_chars = set(string.ascii_letters + string.digits + "._-/")
    if not set(path) <= allowed_chars:
      raise RuntimeError("Unusual chars in path %r - "
                         "possible exploit attempt." % path)

    target_path = os.path.join(config.CONFIG["AdminUI.docs_location"], path)

    # We have to redirect via JavaScript to have access to and to preserve the
    # URL hash. We don't know the hash part of the url on the server.
    return werkzeug_wrappers.Response(
        """
<script>
var friendly_hash = window.location.hash;
window.location = '%s' + friendly_hash;
</script>
""" % target_path,
        mimetype="text/html")

  def _HandleHelp(self, request):
    """Handles help requests."""
    help_path = request.path.split("/", 2)[-1]
    if not help_path:
      raise werkzeug_exceptions.Forbidden("Error: Invalid help path.")

    # Proxy remote documentation.
    return self._RedirectToRemoteHelp(help_path)

  @werkzeug_wsgi.responder
  def __call__(self, environ, start_response):
    """Dispatches a request."""
    request = self._BuildRequest(environ)

    matcher = self.routing_map.bind_to_environ(environ)
    try:
      endpoint, _ = matcher.match(request.path, request.method)
      return endpoint(request)
    except werkzeug_exceptions.HTTPException as e:
      logging.exception("http exception: %s [%s]", request.path, request.method)
      return e

  def WSGIHandler(self):
    """Returns GRR's WSGI handler."""
    sdm = werkzeug_wsgi.SharedDataMiddleware(self, {
        "/": config.CONFIG["AdminUI.document_root"],
    })
    # Use DispatcherMiddleware to make sure that SharedDataMiddleware is not
    # used at all if the URL path doesn't start with "/static". This is a
    # workaround for cases when unicode URLs are used on systems with
    # non-unicode filesystems (as detected by Werkzeug). In this case
    # SharedDataMiddleware may fail early while trying to convert the
    # URL into the file path and not dispatch the call further to our own
    # WSGI handler.
    return werkzeug_wsgi.DispatcherMiddleware(self, {
        "/static": sdm,
    })


class GuiPluginsInit(registry.InitHook):
  """Initialize the GUI plugins."""

  def RunOnce(self):
    """Import the plugins once only."""
    # pylint: disable=unused-variable,g-import-not-at-top
    from grr_response_server.gui import gui_plugins
    # pylint: enable=unused-variable,g-import-not-at-top

    if config.CONFIG.Get("AdminUI.django_secret_key", None):
      logging.warn("The AdminUI.django_secret_key option has been deprecated, "
                   "please use AdminUI.csrf_secret_key instead.")
