#!/usr/bin/env python
"""Main Django renderer."""


import importlib
import os
import string


from django import http
from django import shortcuts
from django import template
from django.views.decorators import csrf
import psutil
import logging

from grr.gui import http_api
from grr.gui import urls
from grr.gui import webauth
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats

from grr.lib.aff4_objects import users as aff4_users


class ViewsInit(registry.InitHook):

  def RunOnce(self):
    """Run this once on init."""
    # General metrics
    stats.STATS.RegisterCounterMetric("http_access_denied")
    stats.STATS.RegisterCounterMetric("http_server_error")


@webauth.SecurityCheck
@csrf.ensure_csrf_cookie  # Set the csrf cookie on the homepage.
def Homepage(request):
  """Basic handler to render the index page."""
  create_time = psutil.Process(os.getpid()).create_time()
  context = {
      "heading": config_lib.CONFIG["AdminUI.heading"],
      "report_url": config_lib.CONFIG["AdminUI.report_url"],
      "help_url": config_lib.CONFIG["AdminUI.help_url"],
      "use_precompiled_js": config_lib.CONFIG["AdminUI.use_precompiled_js"],
      "timestamp": create_time
  }
  response = shortcuts.render_to_response(
      "base.html", context, context_instance=template.RequestContext(request))

  # Check if we need to set the canary_mode cookie.
  request.REQ = request.GET.dict()
  request.token = BuildToken(request, 60)
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

  return response


@webauth.SecurityCheck
def RenderApi(request):
  """Handler for the /api/ requests."""
  return http_api.RenderHttpResponse(request)


def RedirectToRemoteHelp(path):
  """Redirect to GitHub-hosted documentation."""
  allowed_chars = set(string.ascii_letters + string.digits + "._")
  if not set(path) <= allowed_chars:
    raise RuntimeError("Unusual chars in path %r - "
                       "possible exploit attempt." % path)

  target_path = os.path.join(config_lib.CONFIG["AdminUI.github_docs_location"],
                             path.replace(".html", ".adoc"))

  # We have to redirect via JavaScript to have access to and to preserve the
  # URL hash. We don't know the hash part of the url on the server.
  response = http.HttpResponse()
  response.write("""
<script>
var friendly_hash = window.location.hash.replace('#_', '#').replace(/_/g, '-');
window.location = '%s' + friendly_hash;
</script>
""" % target_path)
  return response


@webauth.SecurityCheck
def RenderHelp(request, path, document_root=None, content_type=None):
  """Either serves local help files or redirects to the remote ones."""
  _ = document_root
  _ = content_type

  request.REQ = request.REQUEST

  help_path = request.path.split("/", 2)[-1]
  if not help_path:
    return AccessDenied("Error: Invalid help path.")

  try:
    user_record = aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(request.user),
        aff4_users.GRRUser,
        token=BuildToken(request, 60))

    settings = user_record.Get(user_record.Schema.GUI_SETTINGS)
  except IOError:
    settings = aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

  if settings.docs_location == settings.DocsLocation.REMOTE:
    # Proxy remote documentation.
    return RedirectToRemoteHelp(help_path)
  else:
    # Serve prebuilt docs using static handler. To do that we have
    # to resolve static handler's name to an actual function object.
    static_handler_components = urls.static_handler.split(".")
    static_handler_module = importlib.import_module(".".join(
        static_handler_components[0:-1]))
    static_handler = getattr(static_handler_module,
                             static_handler_components[-1])
    return static_handler(
        request, path, document_root=config_lib.CONFIG["AdminUI.help_root"])


def BuildToken(request, execution_time):
  """Build an ACLToken from the request."""
  token = access_control.ACLToken(
      username=request.user,
      reason=request.REQ.get("reason", ""),
      process="GRRAdminUI",
      expiry=rdfvalue.RDFDatetime.Now() + execution_time)

  for field in ["REMOTE_ADDR", "HTTP_X_FORWARDED_FOR"]:
    remote_addr = request.META.get(field, "")
    if remote_addr:
      token.source_ips.append(remote_addr)
  return token


def AccessDenied(message):
  """Return an access denied Response object."""
  response = shortcuts.render_to_response("404.html", {"message": message})
  logging.warn(message)
  response.status_code = 403
  stats.STATS.IncrementCounter("http_access_denied")
  return response


def ServerError(unused_request, template_name="500.html"):
  """500 Error handler."""
  stats.STATS.IncrementCounter("http_server_error")
  response = shortcuts.render_to_response(template_name)
  response.status_code = 500
  return response
