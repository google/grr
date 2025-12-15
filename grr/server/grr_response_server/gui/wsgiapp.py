#!/usr/bin/env python
"""GRR HTTP server implementation."""

import ipaddress
import logging
import os
import socket
import socketserver
import ssl
import string
from wsgiref import simple_server

import jinja2
from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import wsgi as werkzeug_wsgi

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_server import server_logging
from grr_response_server.gui import admin_ui_metrics
from grr_response_server.gui import csp
from grr_response_server.gui import csrf
from grr_response_server.gui import csrf_registry
from grr_response_server.gui import http_api
from grr_response_server.gui import http_request
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

GOOGLEFONT_OVERRIDE_STATIC_SERVING_PATH = (
    "/dist/v2/googlefonts/googlefonts_override.css"
)


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
            endpoint=EndpointWrapper(self._HandleDefaultHomepage),
        )
    )

    self.routing_map.add(
        werkzeug_routing.Rule(
            "/api/v2/<path:path>",
            methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"],
            endpoint=EndpointWrapper(self._HandleApi),
        )
    )
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/help/<path:path>",
            methods=["HEAD", "GET"],
            endpoint=EndpointWrapper(self._HandleHelp),
        )
    )

    for v2_route in ["/v2", "/v2/", "/v2/<path:path>"]:
      self.routing_map.add(
          werkzeug_routing.Rule(
              v2_route,
              methods=["HEAD", "GET"],
              endpoint=EndpointWrapper(self._HandleV2Homepage),
          )
      )

    self.csrf_token_generator = csrf_registry.CreateCSRFTokenGenerator()

  def _BuildRequest(self, environ):
    return http_request.HttpRequest(environ)

  def _HandleDefaultHomepage(self, request):
    admin_ui_metrics.WSGI_ROUTE.Increment(fields=["default"])
    return self._HandleHomepageV2(request)

  def _HandleV2Homepage(self, request):
    admin_ui_metrics.WSGI_ROUTE.Increment(fields=["v2"])
    return self._HandleHomepageV2(request)

  def _HandleHomepageV2(self, request):
    """Renders GRR home page for the next-get UI (v2)."""

    is_development = contexts.DEBUG_CONTEXT in config.CONFIG.context

    context = {
        "use_debug_bundle": (
            is_development or request.args.get("use_debug_bundle", False)
        ),
        "is_test": contexts.TEST_CONTEXT in config.CONFIG.context,
        "analytics_id": config.CONFIG["AdminUI.analytics_id"],
    }

    if config.CONFIG["AdminUI.css_font_override"]:
      context["googlefonts_override"] = (
          "/static" + GOOGLEFONT_OVERRIDE_STATIC_SERVING_PATH
      )

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(config.CONFIG["AdminUI.template_root"]),
        autoescape=True,
    )
    template = env.get_template("base-v2.html")
    response = http_response.HttpResponse(
        template.render(context), mimetype="text/html"
    )

    try:
      csrf.StoreCSRFCookie(request.user, response, self.csrf_token_generator)
    except http_request.RequestHasNoUserError:
      pass

    return response

  def _HandleApi(self, request):
    """Handles API requests."""
    # Checks CSRF token. CSRF token cookie is updated when homepage is visited
    # or via GetPendingUserNotificationsCount API call.
    csrf.ValidateCSRFTokenOrRaise(request, self.csrf_token_generator)

    response = http_api.RenderHttpResponse(request)

    # GetPendingUserNotificationsCount is an API method that is meant
    # to be invoked very often (every 10 seconds). So it's ideal
    # for updating the CSRF token.
    # We should also store the CSRF token if it wasn't yet stored at all.
    if ("csrftoken" not in request.cookies) or response.headers.get(
        "X-API-Method", ""
    ) == "GetPendingUserNotificationsCount":
      csrf.StoreCSRFCookie(request.user, response, self.csrf_token_generator)

    return response

  def _RedirectToRemoteHelp(self, path):
    """Redirect to GitHub-hosted documentation."""
    allowed_chars = set(string.ascii_letters + string.digits + "._-/")
    if not set(path) <= allowed_chars:
      raise RuntimeError(
          "Unusual chars in path %r - possible exploit attempt." % path
      )

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
        mimetype="text/html",
    )

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
      logging.info(
          "Request for non existent url: %s [%s]", request.path, request.method
      )
      return e
    except werkzeug_exceptions.HTTPException as e:
      logging.exception("http exception: %s [%s]", request.path, request.method)
      return e

  def WSGIHandler(self):
    """Returns GRR's WSGI handler."""
    sdm_dict = {
        "/": config.CONFIG["AdminUI.document_root"],
    }

    if config.CONFIG["AdminUI.css_font_override"]:
      sdm_dict[GOOGLEFONT_OVERRIDE_STATIC_SERVING_PATH] = config.CONFIG[
          "AdminUI.css_font_override"
      ]

    sdm = SharedDataMiddleware(
        self,
        sdm_dict,
    )
    # Use DispatcherMiddleware to make sure that SharedDataMiddleware is not
    # used at all if the URL path doesn't start with "/static". This is a
    # workaround for cases when unicode URLs are used on systems with
    # non-unicode filesystems (as detected by Werkzeug). In this case
    # SharedDataMiddleware may fail early while trying to convert the
    # URL into the file path and not dispatch the call further to our own
    # WSGI handler.
    dm = DispatcherMiddleware(
        self,
        {
            "/static": sdm,
        },
    )
    # Add Content Security Policy headers to the Admin UI pages.
    return csp.CspMiddleware(dm)


class SingleThreadedServerInet6(simple_server.WSGIServer):
  address_family = socket.AF_INET6


class MultiThreadedServer(
    socketserver.ThreadingMixIn, simple_server.WSGIServer
):
  pass


class MultiThreadedServerInet6(
    socketserver.ThreadingMixIn, simple_server.WSGIServer
):
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
  max_port = max_port or config.CONFIG.Get(
      "AdminUI.port_max", config.CONFIG["AdminUI.port"]
  )

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

    # See https://docs.python.org/3/library/ssl.html#ssl.Purpose.CLIENT_AUTH for
    # details about why Purpose.CLIENT_AUTH is used here:
    # CLIENT_AUTH: option for create_default_context() and
    # SSLContext.load_default_certs(). This value indicates that the context
    # may be used to authenticate web clients (therefore, it will be used to
    # create server-side sockets).
    context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_file, key_file)
    server.socket = context.wrap_socket(
        server.socket,
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
