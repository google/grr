#!/usr/bin/env python
# Lint as: python3
"""GRR HTTP server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64
import hashlib
import hmac
import ipaddress
import logging
import os
import socket
import socketserver
import ssl
import string
from typing import Text
from wsgiref import simple_server

from cryptography.hazmat.primitives import constant_time
import jinja2
import psutil
from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug import wsgi as werkzeug_wsgi

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import precondition
from grr_response_server import access_control
from grr_response_server import server_logging
from grr_response_server.gui import http_api
from grr_response_server.gui import http_response
from grr_response_server.gui import webauth

# pylint: disable=g-import-not-at-top
try:
  # Werkzeug 0.16.0
  from werkzeug.wsgi import SharedDataMiddleware
  from werkzeug.wsgi import DispatcherMiddleware
except ImportError:
  # Werkzeug 1.0.1
  from werkzeug.middleware.shared_data import SharedDataMiddleware
  from werkzeug.middleware.dispatcher import DispatcherMiddleware
# pylint: enable=g-import-not-at-top

CSRF_DELIMITER = b":"
CSRF_TOKEN_DURATION = rdfvalue.Duration.From(10, rdfvalue.HOURS)


def GenerateCSRFToken(user_id, time):
  """Generates a CSRF token based on a secret key, id and time."""
  precondition.AssertType(user_id, Text)
  precondition.AssertOptionalType(time, int)

  time = time or rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch()

  secret = config.CONFIG.Get("AdminUI.csrf_secret_key", None)
  if secret is None:
    raise ValueError("CSRF secret not available.")
  digester = hmac.new(secret.encode("ascii"), digestmod=hashlib.sha256)
  digester.update(user_id.encode("ascii"))
  digester.update(CSRF_DELIMITER)
  digester.update(str(time).encode("ascii"))
  digest = digester.digest()

  token = base64.urlsafe_b64encode(b"%s%s%d" % (digest, CSRF_DELIMITER, time))
  return token.rstrip(b"=")


def StoreCSRFCookie(user, response):
  """Decorator for WSGI handler that inserts CSRF cookie into response."""

  csrf_token = GenerateCSRFToken(user, None)
  response.set_cookie(
      "csrftoken",
      csrf_token,
      max_age=CSRF_TOKEN_DURATION.ToInt(rdfvalue.SECONDS))


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

  charset = "utf-8"
  encoding_errors = "strict"

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self._user = None
    self.token = None
    self.email = None

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
    if not isinstance(value, Text):
      message = "Expected instance of '%s' but got value '%s' of type '%s'"
      message %= (Text, value, type(value))
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
      response = http_response.HttpResponse("", status=500)
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

    for v2_route in ["/v2", "/v2/", "/v2/<path:path>"]:
      self.routing_map.add(
          werkzeug_routing.Rule(
              v2_route,
              methods=["HEAD", "GET"],
              endpoint=EndpointWrapper(self._HandleHomepageV2)))

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
    template_context = {
        "heading":
            config.CONFIG["AdminUI.heading"],
        "report_url":
            config.CONFIG["AdminUI.report_url"],
        "help_url":
            config.CONFIG["AdminUI.help_url"],
        "timestamp":
            "%.2f" % create_time,
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
    response = http_response.HttpResponse(
        template.render(template_context), mimetype="text/html")

    # For a redirect-based Firebase authentication scheme we won't have any
    # user information at this point - therefore checking if the user is
    # present.
    try:
      StoreCSRFCookie(request.user, response)
    except RequestHasNoUser:
      pass

    return response

  def _HandleHomepageV2(self, request):
    """Renders GRR home page for the next-get UI (v2)."""

    del request  # Unused.

    context = {
        "is_development": contexts.DEBUG_CONTEXT in config.CONFIG.context,
        "is_test": contexts.TEST_CONTEXT in config.CONFIG.context,
    }

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.CONFIG["AdminUI.template_root"]),
        autoescape=True)
    template = env.get_template("base-v2.html")
    response = http_response.HttpResponse(
        template.render(context), mimetype="text/html")

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
    return http_response.HttpResponse(
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
    except werkzeug_exceptions.NotFound as e:
      logging.info("Request for non existent url: %s [%s]", request.path,
                   request.method)
      return e
    except werkzeug_exceptions.HTTPException as e:
      logging.exception("http exception: %s [%s]", request.path, request.method)
      return e

  def WSGIHandler(self):
    """Returns GRR's WSGI handler."""
    sdm = SharedDataMiddleware(self, {
        "/": config.CONFIG["AdminUI.document_root"],
    })
    # Use DispatcherMiddleware to make sure that SharedDataMiddleware is not
    # used at all if the URL path doesn't start with "/static". This is a
    # workaround for cases when unicode URLs are used on systems with
    # non-unicode filesystems (as detected by Werkzeug). In this case
    # SharedDataMiddleware may fail early while trying to convert the
    # URL into the file path and not dispatch the call further to our own
    # WSGI handler.
    return DispatcherMiddleware(self, {
        "/static": sdm,
    })


class SingleThreadedServerInet6(simple_server.WSGIServer):
  address_family = socket.AF_INET6


class MultiThreadedServer(socketserver.ThreadingMixIn,
                          simple_server.WSGIServer):
  pass


class MultiThreadedServerInet6(socketserver.ThreadingMixIn,
                               simple_server.WSGIServer):
  address_family = socket.AF_INET6


def MakeServer(host=None, port=None, max_port=None, multi_threaded=False):
  """Create WSGI server."""
  bind_address = host or config.CONFIG["AdminUI.bind"]
  ip = ipaddress.ip_address(bind_address)
  if ip.version == 4:
    if multi_threaded:
      server_cls = MultiThreadedServer
    else:
      server_cls = simple_server.WSGIServer
  else:
    if multi_threaded:
      server_cls = MultiThreadedServerInet6
    else:
      server_cls = SingleThreadedServerInet6

  port = port or config.CONFIG["AdminUI.port"]
  max_port = max_port or config.CONFIG.Get("AdminUI.port_max",
                                           config.CONFIG["AdminUI.port"])

  for p in range(port, max_port + 1):
    # Make a simple reference implementation WSGI server
    try:
      server = simple_server.make_server(
          bind_address,
          p,
          AdminUIApp().WSGIHandler(),
          server_class=server_cls,
      )
      break
    except socket.error as e:
      if e.errno == socket.errno.EADDRINUSE and p < max_port:
        logging.info("Port %s in use, trying %s", p, p + 1)
      else:
        raise

  proto = "HTTP"

  if config.CONFIG["AdminUI.enable_ssl"]:
    cert_file = config.CONFIG["AdminUI.ssl_cert_file"]
    if not cert_file:
      raise ValueError("Need a valid cert file to enable SSL.")

    key_file = config.CONFIG["AdminUI.ssl_key_file"]
    server.socket = ssl.wrap_socket(
        server.socket,
        certfile=cert_file,
        keyfile=key_file,
        server_side=True,
    )
    proto = "HTTPS"

    # SSL errors are swallowed by the WSGIServer so if your configuration does
    # not work, uncomment the line below, point your browser at the gui and look
    # at the log file to see why SSL complains:
    # server.socket.accept()

  sa = server.socket.getsockname()
  logging.info("Serving %s on %s port %d ...", proto, sa[0], sa[1])

  return server
