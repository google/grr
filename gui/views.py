#!/usr/bin/env python
"""Main Django renderer."""


import os
import pdb
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
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats


SERVER_NAME = "GRR Admin Console"
DOCUMENT_ROOT = os.path.join(os.path.dirname(gui.__file__), "static")


class ViewsInit(registry.InitHook):
  pre = ["StatsInit"]

  def RunOnce(self):
    """Run this once on init."""
    # Renderer-aware metrics
    stats.STATS.RegisterEventMetric(
        "ui_renderer_latency", fields=[("renderer", str)])
    stats.STATS.RegisterEventMetric(
        "ui_renderer_response_size", fields=[("renderer", str)],
        units=stats.MetricUnits.BYTES)
    stats.STATS.RegisterCounterMetric(
        "ui_renderer_failure", fields=[("renderer", str)])

    # General metrics
    stats.STATS.RegisterCounterMetric("ui_unknown_renderer")
    stats.STATS.RegisterCounterMetric("http_access_denied")
    stats.STATS.RegisterCounterMetric("http_server_error")


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
    if aff4.issubclass(cls, renderers.Renderer) and cls.__module__:
      renderers_js_files.add(cls.__module__.split(".")[-1] + ".js")

  context = {"title": SERVER_NAME,
             "renderers_js": renderers_js_files}
  return shortcuts.render_to_response(
      "base.html", context, context_instance=template.RequestContext(request))


@webauth.SecurityCheck
def RenderBinaryDownload(request):
  """Basic handler to allow downloads of aff4:/config/executables files."""
  path, filename = request.path.split("/", 2)[-1].rsplit("/", 1)
  if not path or not filename:
    return AccessDenied("Error: Invalid path.")
  request.REQ = request.REQUEST
  def Generator():
    with aff4.FACTORY.Open(aff4_path, aff4_type="GRRSignedBlob",
                           token=BuildToken(request, 60)) as fd:
      while True:
        data = fd.Read(1000000)
        if not data: break
        yield data

  base_path = rdfvalue.RDFURN("aff4:/config/executables")
  aff4_path = base_path.Add(path).Add(filename)
  if not aff4_path.RelativeName(base_path):
    # Check for path traversals.
    return AccessDenied("Error: Invalid path.")
  filename = aff4_path.Basename()
  response = http.HttpResponse(content=Generator(),
                               mimetype="binary/octet-stream")
  response["Content-Disposition"] = ("attachment; filename=%s" % filename)
  return response


@webauth.SecurityCheck
@renderers.ErrorHandler()
def RenderGenericRenderer(request):
  """Django handler for rendering registered GUI Elements."""
  try:
    action, renderer_name = request.path.split("/")[-2:]

    renderer_cls = renderers.Renderer.GetPlugin(name=renderer_name)
  except KeyError:
    stats.STATS.IncrementCounter("ui_unknown_renderer")
    return AccessDenied("Error: Renderer %s not found" % renderer_name)

  # Check that the action is valid
  ["Layout", "RenderAjax", "Download", "Validate"].index(action)
  renderer = renderer_cls()
  result = http.HttpResponse(mimetype="text/html")

  # Pass the request only from POST parameters
  if flags.FLAGS.debug:
    # Allow both for debugging
    request.REQ = request.REQUEST
  else:
    # Only POST in production for CSRF protections.
    request.REQ = request.POST

  # Build the security token for this request
  request.token = BuildToken(request, renderer.max_execution_time)

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
                              total_time, fields=[renderer_name])

  except access_control.UnauthorizedAccess, e:
    result = http.HttpResponse(mimetype="text/html")
    result = renderers.Renderer.GetPlugin("UnauthorizedRenderer")().Layout(
        request, result, exception=e)

  except Exception:
    stats.STATS.IncrementCounter("ui_renderer_failure",
                                 fields=[renderer_name])

    if flags.FLAGS.debug:
      pdb.post_mortem()

    raise

  if not isinstance(result, http.HttpResponse):
    raise RuntimeError("Renderer returned invalid response %r" % result)

  # Prepend bad json to break json script inclusion attacks.
  content_type = result.get("Content-Type", 0)
  if content_type and "json" in content_type.lower():
    result.content = ")]}\n" + result.content

  return result


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
