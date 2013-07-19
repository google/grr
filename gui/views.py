#!/usr/bin/env python
"""Main Django renderer."""


import os
import time


from django import http
from django import shortcuts
from django import template
from django.views.decorators import csrf
import logging

from grr import gui
from grr.gui import renderers
from grr.gui import webauth
from grr.lib import access_control
from grr.lib import flags
from grr.lib import registry
from grr.lib import stats


SERVER_NAME = "GRR Admin Console"
DOCUMENT_ROOT = os.path.join(os.path.dirname(gui.__file__), "static")


class ViewsInit(registry.InitHook):
  pre = ["StatsInit"]

  def RunOnce(self):
    """Run this once on init."""
    # Counters used here
    stats.STATS.RegisterCounterMetric("grr_admin_ui_access_denied")
    stats.STATS.RegisterCounterMetric("grr_admin_ui_slave_response")
    stats.STATS.RegisterCounterMetric("grr_admin_ui_renderer_called")
    stats.STATS.RegisterCounterMetric("grr_admin_ui_renderer_failed")
    stats.STATS.RegisterCounterMetric("grr_admin_ui_unknown_renderer")


@webauth.SecurityCheck
@csrf.ensure_csrf_cookie     # Set the csrf cookie on the homepage.
def Homepage(request):
  """Basic handler to render the index page."""
  # We build a list of all js files to include by looking at the list
  # of renderers modules. JS files are always named in accordance with
  # renderers modules names. I.e. if there's a renderers package called
  # grr.gui.plugins.acl_manager, we expect a js files called acl_manager.js.
  renderers_js_files = set()
  for cls in renderers.Renderer.classes.values():
    if cls.__module__:
      renderers_js_files.add(cls.__module__.split(".")[-1] + ".js")

  context = {"title": SERVER_NAME,
             "renderers_js": renderers_js_files}
  return shortcuts.render_to_response(
      "base.html", context, context_instance=template.RequestContext(request))


@webauth.SecurityCheck
@renderers.ErrorHandler()
def RenderGenericRenderer(request):
  """Django handler for rendering registered GUI Elements."""
  try:
    action, renderer_name = request.path.split("/")[-2:]

    renderer_cls = renderers.Renderer.NewPlugin(name=renderer_name)
  except KeyError:
    stats.STATS.IncrementCounter("grr_admin_ui_unknown_renderer")
    return AccessDenied("Error: Renderer %s not found" % renderer_name)

  # Check that the action is valid
  ["Layout", "RenderAjax", "Download"].index(action)
  renderer = renderer_cls()
  stats.STATS.IncrementCounter("grr_admin_ui_renderer_called")
  result = http.HttpResponse(mimetype="text/html")

  # Pass the request only from POST parameters
  if flags.FLAGS.debug:
    # Allow both for debugging
    request.REQ = request.REQUEST
  else:
    # Only POST in production for CSRF protections.
    request.REQ = request.POST

  # Build the security token for this request
  request.token = access_control.ACLToken(
      request.user, request.REQ.get("reason", ""),
      process="GRRAdminUI",
      expiry=time.time() + renderer.max_execution_time)

  for field in ["REMOTE_ADDR", "HTTP_X_FORWARDED_FOR"]:
    remote_addr = request.META.get(field, "")
    if remote_addr:
      request.token.source_ips.append(remote_addr)

  # Allow the renderer to check its own ACLs.
  renderer.CheckAccess(request)

  try:
    # Does this renderer support this action?
    method = getattr(renderer, action)
    result = method(request, result) or result
  except access_control.UnauthorizedAccess, e:
    result = http.HttpResponse(mimetype="text/html")
    result = renderers.Renderer.NewPlugin("UnauthorizedRenderer")().Layout(
        request, result, exception=e)

  if not isinstance(result, http.HttpResponse):
    raise RuntimeError("Renderer returned invalid response %r" % result)

  # Prepend bad json to break json script inclusion attacks.
  content_type = result.get("Content-Type", 0)
  if content_type and "json" in content_type.lower():
    result.content = ")]}\n" + result.content

  return result


def AccessDenied(message):
  """Return an access denied Response object."""
  response = shortcuts.render_to_response("404.html", {"message": message})
  logging.warn(message)
  response.status_code = 403
  stats.STATS.IncrementCounter("grr_admin_ui_access_denied")
  return response


def ServerError(unused_request, template_name="500.html"):
  """500 Error handler."""
  stats.STATS.IncrementCounter("grr_admin_ui_renderer_failed")
  response = shortcuts.render_to_response(template_name)
  response.status_code = 500
  return response
