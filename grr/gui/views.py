#!/usr/bin/env python
"""Main Django renderer."""


import importlib
import os
import pdb
import string
import time


from django import http
from django import shortcuts
from django import template
from django.views.decorators import csrf
import psutil
import logging

from grr.gui import http_api
from grr.gui import renderers
from grr.gui import urls
from grr.gui import webauth
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats

from grr.lib.aff4_objects import users as aff4_users

from grr.lib.authorization import auth_manager

LEGACY_RENDERERS_AUTH_MANAGER = None


class ViewsInit(registry.InitHook):

  def RunOnce(self):
    """Run this once on init."""
    # Renderer-aware metrics
    stats.STATS.RegisterEventMetric("ui_renderer_latency",
                                    fields=[("renderer", str)])
    stats.STATS.RegisterEventMetric("ui_renderer_response_size",
                                    fields=[("renderer", str)],
                                    units=stats.MetricUnits.BYTES)
    stats.STATS.RegisterCounterMetric("ui_renderer_failure",
                                      fields=[("renderer", str)])

    # General metrics
    stats.STATS.RegisterCounterMetric("ui_unknown_renderer")
    stats.STATS.RegisterCounterMetric("http_access_denied")
    stats.STATS.RegisterCounterMetric("http_server_error")

    global LEGACY_RENDERERS_AUTH_MANAGER
    legacy_renderers_groups = config_lib.CONFIG[
        "AdminUI.legacy_renderers_allowed_groups"]
    if legacy_renderers_groups:
      LEGACY_RENDERERS_AUTH_MANAGER = auth_manager.AuthorizationManager()
      for group in legacy_renderers_groups:
        LEGACY_RENDERERS_AUTH_MANAGER.AuthorizeGroup(group, "legacy_renderers")


@webauth.SecurityCheck
@csrf.ensure_csrf_cookie  # Set the csrf cookie on the homepage.
def Homepage(request):
  """Basic handler to render the index page."""
  # DEPRECATED: renderers are now legacy, so just hardcoding the list
  # of JS files here (it's not going to expand).
  #
  # We build a list of all js files to include by looking at the list
  # of renderers modules. JS files are always named in accordance with
  # renderers modules names. I.e. if there's a renderers package called
  # grr.gui.plugins.acl_manager, we expect a js files called acl_manager.js.
  renderers_js_files = set([
      "acl_manager.js",
      "artifact_view.js",
      "configuration_view.js",
      "container_viewer.js",
      "crash_view.js",
      "cron_view.js",
      "fileview.js",
      "fileview_widgets.js",
      "flow_management.js",
      "foreman.js",
      "forms.js",
      "hunt_view.js",
      "inspect_view.js",
      "new_hunt.js",
      "notifications.js",
      "rekall_viewer.js",
      "reports_view.js",
      "searchclient.js",
      "semantic.js",
      "server_load_view.js",
      "statistics.js",
      "timeline_view.js",
      "usage.js",
      "wizards.js"
  ])  # pyformat: disable

  create_time = psutil.Process(os.getpid()).create_time()
  context = {"page_title": config_lib.CONFIG["AdminUI.page_title"],
             "heading": config_lib.CONFIG["AdminUI.heading"],
             "report_url": config_lib.CONFIG["AdminUI.report_url"],
             "help_url": config_lib.CONFIG["AdminUI.help_url"],
             "use_precompiled_js":
                 config_lib.CONFIG["AdminUI.use_precompiled_js"],
             "renderers_js": renderers_js_files,
             "timestamp": create_time}
  response = shortcuts.render_to_response(
      "base.html",
      context,
      context_instance=template.RequestContext(request))

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
def RenderBinaryDownload(request):
  """Basic handler to allow downloads of aff4:/config/executables files."""
  if (LEGACY_RENDERERS_AUTH_MANAGER and
      not LEGACY_RENDERERS_AUTH_MANAGER.CheckPermissions(request.user,
                                                         "legacy_renderers")):
    return AccessDenied("User is not allowed to use legacy renderers.")

  path, filename = request.path.split("/", 2)[-1].rsplit("/", 1)
  if not path or not filename:
    return AccessDenied("Error: Invalid path.")
  request.REQ = request.REQUEST

  def Generator():
    with aff4.FACTORY.Open(aff4_path,
                           aff4_type="GRRSignedBlob",
                           token=BuildToken(request, 60)) as fd:
      while True:
        data = fd.Read(1000000)
        if not data:
          break
        yield data

  base_path = rdfvalue.RDFURN("aff4:/config/executables")
  aff4_path = base_path.Add(path).Add(filename)
  if not aff4_path.RelativeName(base_path):
    # Check for path traversals.
    return AccessDenied("Error: Invalid path.")
  filename = aff4_path.Basename()
  response = http.StreamingHttpResponse(streaming_content=Generator(),
                                        content_type="binary/octet-stream")
  response["Content-Disposition"] = ("attachment; filename=%s" % filename)
  return response


@webauth.SecurityCheck
@renderers.ErrorHandler()
def RenderApi(request):
  """Handler for the /api/ requests."""
  return http_api.RenderHttpResponse(request)


@webauth.SecurityCheck
@renderers.ErrorHandler()
def RenderGenericRenderer(request):
  """Django handler for rendering registered GUI Elements."""
  if (LEGACY_RENDERERS_AUTH_MANAGER and
      not LEGACY_RENDERERS_AUTH_MANAGER.CheckPermissions(request.user,
                                                         "legacy_renderers")):
    return AccessDenied("User is not allowed to use legacy renderers.")

  try:
    action, renderer_name = request.path.split("/")[-2:]

    renderer_cls = renderers.Renderer.GetPlugin(name=renderer_name)
  except KeyError:
    stats.STATS.IncrementCounter("ui_unknown_renderer")
    return AccessDenied("Error: Renderer %s not found" % renderer_name)

  # Check that the action is valid
  ["Layout", "RenderAjax", "Download", "Validate"].index(action)
  renderer = renderer_cls()
  result = http.HttpResponse(content_type="text/html")

  # Pass the request only from POST parameters. It is much more convenient to
  # deal with normal dicts than Django's Query objects so we convert here.
  if flags.FLAGS.debug:
    # Allow both POST and GET for debugging
    request.REQ = request.POST.dict()
    request.REQ.update(request.GET.dict())
  else:
    # Only POST in production for CSRF protections.
    request.REQ = request.POST.dict()

  # Build the security token for this request
  request.token = BuildToken(request, renderer.max_execution_time)

  request.canary_mode = "canary_mode" in request.COOKIES

  # Allow the renderer to check its own ACLs.
  renderer.CheckAccess(request)

  try:
    # Does this renderer support this action?
    method = getattr(renderer, action)

    start_time = time.time()
    try:
      result = method(request, result) or result
    finally:
      total_time = time.time() - start_time
      stats.STATS.RecordEvent("ui_renderer_latency",
                              total_time,
                              fields=[renderer_name])

  except access_control.UnauthorizedAccess, e:
    result = http.HttpResponse(content_type="text/html")
    result = renderers.Renderer.GetPlugin("UnauthorizedRenderer")().Layout(
        request, result, exception=e)

  except Exception:
    stats.STATS.IncrementCounter("ui_renderer_failure", fields=[renderer_name])

    if flags.FLAGS.debug:
      pdb.post_mortem()

    raise

  if not isinstance(result, (http.HttpResponse, http.StreamingHttpResponse)):
    raise RuntimeError("Renderer returned invalid response %r" % result)

  return result


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
    return static_handler(request,
                          path,
                          document_root=config_lib.CONFIG["AdminUI.help_root"])


def BuildToken(request, execution_time):
  """Build an ACLToken from the request."""
  token = access_control.ACLToken(
      username=request.user,
      reason=request.REQ.get("reason", ""),
      process="GRRAdminUI",
      expiry=rdfvalue.RDFDatetime().Now() + execution_time)

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
