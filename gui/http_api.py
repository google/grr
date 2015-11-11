#!/usr/bin/env python
"""HTTP API logic that ties API call renderers with HTTP routes."""



import json
import urllib2


# pylint: disable=g-bad-import-order,unused-import
from grr.gui import django_lib
# pylint: enable=g-bad-import-order,unused-import

from django import http

from werkzeug import exceptions as werkzeug_exceptions
from werkzeug import routing

import logging

from grr.gui import api_call_renderers
from grr.gui import api_plugins
from grr.gui import http_routing
from grr.lib import access_control
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


def BuildToken(request, execution_time):
  """Build an ACLToken from the request."""

  if request.method == "GET":
    reason = request.GET.get("reason", "")
  elif request.method == "POST":
    # The header X-GRR-REASON is set in api-service.js, which django converts to
    # HTTP_X_GRR_REASON.
    reason = utils.SmartUnicode(urllib2.unquote(
        request.META.get("HTTP_X_GRR_REASON", "")))

  token = access_control.ACLToken(
      username=request.user,
      reason=reason,
      process="GRRAdminUI",
      expiry=rdfvalue.RDFDatetime().Now() + execution_time)

  for field in ["REMOTE_ADDR", "HTTP_X_FORWARDED_FOR"]:
    remote_addr = request.META.get(field, "")
    if remote_addr:
      token.source_ips.append(remote_addr)
  return token


def StripTypeInfo(rendered_data):
  """Strips type information from rendered data. Useful for debugging."""

  if isinstance(rendered_data, (list, tuple)):
    return [StripTypeInfo(d) for d in rendered_data]
  elif isinstance(rendered_data, dict):
    if "value" in rendered_data:
      return StripTypeInfo(rendered_data["value"])
    else:
      result = {}
      for k, v in rendered_data.items():
        result[k] = StripTypeInfo(v)
      return result
  else:
    return rendered_data


def RegisterHttpRouteHandler(method, route, renderer_cls):
  """Registers given ApiCallRenderer for given method and route."""
  http_routing.HTTP_ROUTING_MAP.add(routing.Rule(
      route, methods=[method],
      endpoint=renderer_cls))


def GetRendererForHttpRequest(request):
  """Returns a renderer to handle given HTTP request."""

  matcher = http_routing.HTTP_ROUTING_MAP.bind(
      "%s:%s" % (request.environ["SERVER_NAME"],
                 request.environ["SERVER_PORT"]))
  try:
    match = matcher.match(request.path, request.method)
  except werkzeug_exceptions.NotFound:
    raise api_call_renderers.ApiCallRendererNotFoundError(
        "No API renderer was found for (%s) %s" % (request.path,
                                                   request.method))

  renderer_cls, route_args = match
  return (renderer_cls(), route_args)


def FillAdditionalArgsFromRequest(request, supported_types):
  """Creates arguments objects from a given request dictionary."""

  results = {}
  for key, value in request.items():
    try:
      request_arg_type, request_attr = key.split(".", 1)
    except ValueError:
      continue

    arg_class = None
    for key, supported_type in supported_types.items():
      if key == request_arg_type:
        arg_class = supported_type

    if arg_class:
      if request_arg_type not in results:
        results[request_arg_type] = arg_class()

      results[request_arg_type].Set(request_attr, value)

  results_list = []
  for name, arg_obj in results.items():
    additional_args = api_call_renderers.ApiCallAdditionalArgs(
        name=name, type=supported_types[name].__name__)
    additional_args.args = arg_obj
    results_list.append(additional_args)

  return results_list


class JSONEncoderWithRDFPrimitivesSupport(json.JSONEncoder):
  """Custom JSON encoder that encodes renderers output.

  Custom encoder is required to facilitate usage of primitive values -
  booleans, integers and strings - in renderers responses.

  If renderer references an RDFString, RDFInteger or and RDFBOol when building a
  response, it will lead to JSON encoding failure when response encoded,
  unless this custom encoder is used. Another way to solve this issue would be
  to explicitly call api_value_renderers.RenderValue on every value returned
  from the renderer, but it will make the code look overly verbose and dirty.
  """

  def default(self, obj):
    if isinstance(obj, (rdfvalue.RDFInteger,
                        rdfvalue.RDFBool,
                        rdfvalue.RDFString)):
      return obj.SerializeToDataStore()

    return json.JSONEncoder.default(self, obj)


def BuildResponse(status, rendered_data):
  """Builds HTTPResponse object from rendered data and HTTP status."""
  response = http.HttpResponse(status=status,
                               content_type="application/json; charset=utf-8")
  response["Content-Disposition"] = "attachment; filename=response.json"
  response["X-Content-Type-Options"] = "nosniff"

  response.write(")]}'\n")  # XSSI protection

  # To avoid IE content sniffing problems, escape the tags. Otherwise somebody
  # may send a link with malicious payload that will be opened in IE (which
  # does content sniffing and doesn't respect Content-Disposition header) and
  # IE will treat the document as html and executre arbitrary JS that was
  # passed with the payload.
  str_data = json.dumps(rendered_data, cls=JSONEncoderWithRDFPrimitivesSupport)
  response.write(str_data.replace("<", r"\u003c").replace(">", r"\u003e"))

  return response


def RenderHttpResponse(request):
  """Handles given HTTP request with one of the available API renderers."""

  renderer, route_args = GetRendererForHttpRequest(request)

  strip_type_info = False

  if request.method == "GET":
    if request.GET.get("strip_type_info", ""):
      strip_type_info = True

    if renderer.args_type:
      unprocessed_request = request.GET
      if hasattr(unprocessed_request, "dict"):
        unprocessed_request = unprocessed_request.dict()

      args = renderer.args_type()
      for type_info in args.type_infos:
        if type_info.name in route_args:
          args.Set(type_info.name, route_args[type_info.name])
        elif type_info.name in unprocessed_request:
          args.Set(type_info.name, unprocessed_request[type_info.name])

      if renderer.additional_args_types:
        if not hasattr(args, "additional_args"):
          raise RuntimeError("Renderer %s defines additional arguments types "
                             "but its arguments object does not have "
                             "'additional_args' field." % renderer)

        if hasattr(renderer.additional_args_types, "__call__"):
          additional_args_types = renderer.additional_args_types()
        else:
          additional_args_types = renderer.additional_args_types

        args.additional_args = FillAdditionalArgsFromRequest(
            unprocessed_request, additional_args_types)

    else:
      args = None
  elif request.method == "POST":
    try:
      args = renderer.args_type()
      for type_info in args.type_infos:
        if type_info.name in route_args:
          args.Set(type_info.name, route_args[type_info.name])

      if request.META["CONTENT_TYPE"].startswith("multipart/form-data;"):
        payload = json.loads(request.POST["_params_"])
        args.FromDict(payload)

        for name, fd in request.FILES.items():
          args.Set(name, fd.read())
      else:
        payload = json.loads(request.body)
        if payload:
          args.FromDict(payload)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(
          "Error while parsing POST request %s (%s): %s",
          request.path, request.method, e)

      return BuildResponse(500, dict(message=str(e)))
  else:
    raise RuntimeError("Unsupported method: %s." % request.method)

  token = BuildToken(request, renderer.max_execution_time)

  try:
    rendered_data = api_call_renderers.HandleApiCall(renderer, args,
                                                     token=token)

    if strip_type_info:
      rendered_data = StripTypeInfo(rendered_data)

    return BuildResponse(200, rendered_data)
  except access_control.UnauthorizedAccess as e:
    logging.exception(
        "Access denied to %s (%s) with %s: %s", request.path,
        request.method, renderer.__class__.__name__, e)

    return BuildResponse(403, dict(message="Access denied by ACL"))
  except Exception as e:  # pylint: disable=broad-except
    logging.exception(
        "Error while processing %s (%s) with %s: %s", request.path,
        request.method, renderer.__class__.__name__, e)

    return BuildResponse(500, dict(message=str(e)))


class HttpApiInitHook(registry.InitHook):
  """Register HTTP API renderers."""

  def RunOnce(self):
    # The list is alphabetized by route.
    RegisterHttpRouteHandler("GET", "/api/aff4/<path:aff4_path>",
                             api_plugins.aff4.ApiAff4Renderer)
    RegisterHttpRouteHandler("GET", "/api/aff4-index/<path:aff4_path>",
                             api_plugins.aff4.ApiAff4IndexRenderer)

    RegisterHttpRouteHandler("GET", "/api/artifacts",
                             api_plugins.artifact.ApiArtifactsRenderer)
    RegisterHttpRouteHandler("POST", "/api/artifacts/upload",
                             api_plugins.artifact.ApiArtifactsUploadRenderer)
    RegisterHttpRouteHandler("POST", "/api/artifacts/delete",
                             api_plugins.artifact.ApiArtifactsDeleteRenderer)

    RegisterHttpRouteHandler("GET", "/api/clients/kb-fields",
                             api_plugins.client.ApiListKbFieldsRenderer)
    RegisterHttpRouteHandler("GET", "/api/clients",
                             api_plugins.client.ApiClientSearchRenderer)
    RegisterHttpRouteHandler("GET", "/api/clients/<client_id>",
                             api_plugins.client.ApiClientSummaryRenderer)
    RegisterHttpRouteHandler("GET", "/api/clients/labels",
                             api_plugins.client.ApiClientsLabelsListRenderer)
    RegisterHttpRouteHandler("POST", "/api/clients/labels/add",
                             api_plugins.client.ApiClientsAddLabelsRenderer)
    RegisterHttpRouteHandler("POST", "/api/clients/labels/remove",
                             api_plugins.client.ApiClientsRemoveLabelsRenderer)

    RegisterHttpRouteHandler("GET", "/api/cron-jobs",
                             api_plugins.cron.ApiCronJobsListRenderer)
    RegisterHttpRouteHandler("POST", "/api/cron-jobs",
                             api_plugins.cron.ApiCreateCronJobRenderer)

    RegisterHttpRouteHandler("GET", "/api/config",
                             api_plugins.config.ApiConfigRenderer)
    RegisterHttpRouteHandler("GET", "/api/config/<name>",
                             api_plugins.config.ApiConfigOptionRenderer)

    RegisterHttpRouteHandler("GET", "/api/docs",
                             api_plugins.docs.ApiDocsRenderer)

    RegisterHttpRouteHandler("GET", "/api/flows/<client_id>/<flow_id>/status",
                             api_plugins.flow.ApiFlowStatusRenderer)
    RegisterHttpRouteHandler("GET", "/api/flows/descriptors",
                             api_plugins.flow.ApiFlowDescriptorsListRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/clients/<client_id>/flows/<flow_id>/results",
        api_plugins.flow.ApiFlowResultsRenderer)
    RegisterHttpRouteHandler(
        "GET",
        "/api/clients/<client_id>/flows/<flow_id>/results/export-command",
        api_plugins.flow.ApiFlowResultsExportCommandRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/clients/<client_id>/flows/<flow_id>/output-plugins",
        api_plugins.flow.ApiFlowOutputPluginsRenderer)
    RegisterHttpRouteHandler("GET", "/api/clients/<client_id>/flows",
                             api_plugins.flow.ApiClientFlowsListRenderer)
    RegisterHttpRouteHandler("POST",
                             "/api/clients/<client_id>/flows/remotegetfile",
                             api_plugins.flow.ApiRemoteGetFileRenderer)
    # This starts client flows.
    RegisterHttpRouteHandler("POST", "/api/clients/<client_id>/flows/start",
                             api_plugins.flow.ApiStartFlowRenderer)
    # This starts global flows.
    RegisterHttpRouteHandler("POST", "/api/flows",
                             api_plugins.flow.ApiStartFlowRenderer)
    RegisterHttpRouteHandler(
        "POST",
        "/api/clients/<client_id>/flows/<flow_id>/actions/cancel",
        api_plugins.flow.ApiCancelFlowRenderer)
    RegisterHttpRouteHandler(
        "POST",
        "/api/clients/<client_id>/flows/<flow_id>/results/archive-files",
        api_plugins.flow.ApiFlowArchiveFilesRenderer)

    RegisterHttpRouteHandler(
        "GET", "/api/output-plugins/all",
        api_plugins.output_plugin.ApiOutputPluginsListRenderer)

    RegisterHttpRouteHandler("GET", "/api/hunts",
                             api_plugins.hunt.ApiHuntsListRenderer)
    RegisterHttpRouteHandler("GET", "/api/hunts/<hunt_id>",
                             api_plugins.hunt.ApiHuntSummaryRenderer)
    RegisterHttpRouteHandler("GET", "/api/hunts/<hunt_id>/errors",
                             api_plugins.hunt.ApiHuntErrorsRenderer)
    RegisterHttpRouteHandler("GET", "/api/hunts/<hunt_id>/log",
                             api_plugins.hunt.ApiHuntLogRenderer)
    RegisterHttpRouteHandler("GET", "/api/hunts/<hunt_id>/results",
                             api_plugins.hunt.ApiHuntResultsRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/hunts/<hunt_id>/results/export-command",
        api_plugins.hunt.ApiHuntResultsExportCommandRenderer)
    RegisterHttpRouteHandler("GET", "/api/hunts/<hunt_id>/output-plugins",
                             api_plugins.hunt.ApiHuntOutputPluginsRenderer)
    RegisterHttpRouteHandler("POST", "/api/hunts/create",
                             api_plugins.hunt.ApiCreateHuntRenderer)
    RegisterHttpRouteHandler("POST",
                             "/api/hunts/<hunt_id>/results/archive-files",
                             api_plugins.hunt.ApiHuntArchiveFilesRenderer)

    RegisterHttpRouteHandler(
        "GET", "/api/reflection/aff4/attributes",
        api_plugins.reflection.ApiAff4AttributesReflectionRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/reflection/rdfvalue/<type>",
        api_plugins.reflection.ApiRDFValueReflectionRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/reflection/rdfvalue/all",
        api_plugins.reflection.ApiAllRDFValuesReflectionRenderer)

    RegisterHttpRouteHandler(
        "GET", "/api/stats/store/<component>/metadata",
        api_plugins.stats.ApiStatsStoreMetricsMetadataRenderer)
    RegisterHttpRouteHandler(
        "GET", "/api/stats/store/<component>/metrics/<metric_name>",
        api_plugins.stats.ApiStatsStoreMetricRenderer)

    RegisterHttpRouteHandler("GET", "/api/users/me/approvals/<approval_type>",
                             api_plugins.user.ApiUserApprovalsListRenderer)
    RegisterHttpRouteHandler("GET", "/api/users/me/settings",
                             api_plugins.user.ApiUserSettingsRenderer)
    RegisterHttpRouteHandler("POST", "/api/users/me/settings",
                             api_plugins.user.ApiSetUserSettingsRenderer)
