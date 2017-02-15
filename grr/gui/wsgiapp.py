#!/usr/bin/env python
"""GRR HTTP server implementation."""



import base64
import hashlib
import hmac
import os
import string


from cryptography.hazmat.primitives import constant_time

import jinja2
import psutil

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing as werkzeug_routing
from werkzeug import utils as werkzeug_utils
from werkzeug import wrappers as werkzeug_wrappers
from werkzeug import wsgi as werkzeug_wsgi

import logging

from grr.gui import http_api
from grr.gui import webauth

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils

from grr.lib.aff4_objects import users as aff4_users

CSRF_DELIMITER = ":"
CSRF_TOKEN_DURATION = rdfvalue.Duration("10h")


def GenerateCSRFToken(user_id, time):
  """Generates a CSRF token based on a secret key, id and time."""
  time = time or rdfvalue.RDFDatetime.Now().AsMicroSecondsFromEpoch()

  digester = hmac.new(
      utils.SmartStr(config_lib.CONFIG["AdminUI.django_secret_key"]),
      digestmod=hashlib.sha256)
  digester.update(utils.SmartStr(user_id))
  digester.update(CSRF_DELIMITER)
  digester.update(str(time))
  digest = digester.digest()

  token = base64.urlsafe_b64encode("%s%s%d" % (digest, CSRF_DELIMITER, time))
  return token.rstrip("=")


def StoreCSRFCookie(request, response):
  """Decorator for WSGI handler that inserts CSRF cookie into response."""

  csrf_token = GenerateCSRFToken(request.user, None)
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
  csrf_token = utils.SmartStr(request.headers.get("X-CSRFToken", ""))
  if not csrf_token:
    logging.info("Did not find headers CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("CSRF token is missing")

  try:
    decoded = base64.urlsafe_b64decode(csrf_token + "==")
    digest, token_time = decoded.rsplit(CSRF_DELIMITER, 1)
    token_time = long(token_time)
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

  current_time = rdfvalue.RDFDatetime.Now().AsMicroSecondsFromEpoch()
  if current_time - token_time > CSRF_TOKEN_DURATION.microseconds:
    logging.info("Expired CSRF token for: %s", request.path)
    raise werkzeug_exceptions.Forbidden("Expired CSRF token")


class HttpRequest(werkzeug_wrappers.Request):
  """HTTP request object to be used in GRR."""

  def __init__(self, *args, **kwargs):
    super(HttpRequest, self).__init__(*args, **kwargs)

    self.user = None
    self.event_id = None
    self.token = None

  @property
  def user(self):
    if self._user is None:
      raise ValueError("Trying to access Request.user while user is unset.")

    if not self._user:
      raise ValueError("Trying to access Request.user while user is empty.")

    return self._user

  @user.setter
  def user(self, value):
    self._user = value


class AdminUIApp(object):
  """Base class for WSGI GRR app."""

  def __init__(self):
    self.routing_map = werkzeug_routing.Map()
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/",
            methods=["HEAD", "GET"],
            endpoint=webauth.SecurityCheck(self._HandleHomepage)))
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/api/<path:path>",
            methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"],
            endpoint=webauth.SecurityCheck(self._HandleApi)))
    self.routing_map.add(
        werkzeug_routing.Rule(
            "/help/<path:path>",
            methods=["HEAD", "GET"],
            endpoint=webauth.SecurityCheck(self._HandleHelp)))

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
        loader=jinja2.FileSystemLoader(
            config_lib.CONFIG["AdminUI.template_root"]),
        autoescape=True)

    create_time = psutil.Process(os.getpid()).create_time()
    context = {
        "heading": config_lib.CONFIG["AdminUI.heading"],
        "report_url": config_lib.CONFIG["AdminUI.report_url"],
        "help_url": config_lib.CONFIG["AdminUI.help_url"],
        "timestamp": utils.SmartStr(create_time),
        "use_precompiled_js": config_lib.CONFIG["AdminUI.use_precompiled_js"]
    }
    template = env.get_template("base.html")
    response = werkzeug_wrappers.Response(
        template.render(context), mimetype="text/html")

    # Check if we need to set the canary_mode cookie.
    request.token = self._BuildToken(request, 60)
    user_record = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(request.user),
        aff4_type=aff4_users.GRRUser,
        mode="r",
        token=request.token)
    canary_mode = user_record.Get(user_record.Schema.GUI_SETTINGS).canary_mode

    if canary_mode:
      response.set_cookie("canary_mode", "true")
    else:
      response.delete_cookie("canary_mode")

    StoreCSRFCookie(request, response)
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
    if response.headers.get("X-API-Method",
                            "") == "GetPendingUserNotificationsCount":
      StoreCSRFCookie(request, response)

    return response

  def _RedirectToRemoteHelp(self, path):
    """Redirect to GitHub-hosted documentation."""
    allowed_chars = set(string.ascii_letters + string.digits + "._")
    if not set(path) <= allowed_chars:
      raise RuntimeError("Unusual chars in path %r - "
                         "possible exploit attempt." % path)

    target_path = os.path.join(
        config_lib.CONFIG["AdminUI.github_docs_location"],
        path.replace(".html", ".adoc"))

    # We have to redirect via JavaScript to have access to and to preserve the
    # URL hash. We don't know the hash part of the url on the server.
    return werkzeug_wrappers.Response(
        """
<script>
var friendly_hash = window.location.hash.replace('#_', '#').replace(/_/g, '-');
window.location = '%s' + friendly_hash;
</script>
""" % target_path,
        mimetype="text/html")

  def _HandleHelp(self, request):
    """Handles help requests."""
    help_path = request.path.split("/", 2)[-1]
    if not help_path:
      raise werkzeug_exceptions.Forbidden("Error: Invalid help path.")

    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(request.user),
          aff4_users.GRRUser,
          token=self._BuildToken(request, 60))

      settings = user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      settings = aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

    if settings.docs_location == settings.DocsLocation.REMOTE:
      # Proxy remote documentation.
      return self._RedirectToRemoteHelp(help_path)
    else:
      return werkzeug_utils.redirect("/local/help/%s" % help_path)

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
    return werkzeug_wsgi.SharedDataMiddleware(self, {
        "/static": config_lib.CONFIG["AdminUI.document_root"],
        "/local/static": config_lib.CONFIG["AdminUI.local_document_root"],
        "/local/help": config_lib.CONFIG["AdminUI.help_root"]
    })


class GuiPluginsInit(registry.InitHook):
  """Initialize the GUI plugins."""

  def RunOnce(self):
    """Import the plugins once only."""
    # pylint: disable=unused-variable,g-import-not-at-top
    from grr.gui import gui_plugins
    # pylint: enable=unused-variable,g-import-not-at-top
