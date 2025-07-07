#!/usr/bin/env python
"""OutputPlugin that sends Flow results as events to a HTTP Webhook.

Configuration values for this plugin can be found in
core/grr_response_core/config/output_plugins.py
"""

import json
from typing import Any
from urllib.parse import urlparse

import requests

from google.protobuf import json_format
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server import output_plugin
from grr_response_server.export_converters import base
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import mig_flow
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_objects

JsonDict = dict[str, Any]


class WebhookConfigurationError(Exception):
  """Error indicating a wrong or missing Webhook configuration."""


class WebhookOutputPluginArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of WebhookOutputPlugin."""

  protobuf = output_plugin_pb2.WebhookOutputPluginArgs
  rdf_deps = []


def _ToDict(rdfval: rdf_structs.RDFProtoStruct) -> JsonDict:
  return json_format.MessageToDict(rdfval.AsPrimitiveProto(), float_precision=8)


class WebhookOutputPlugin(output_plugin.OutputPlugin):
  """OutputPlugin that sends Flow results as events to a HTTP Webhook."""

  name = "webhook"
  description = "Send flow results to Webhook."
  args_type = WebhookOutputPluginArgs

  def __init__(self, *args, **kwargs):
    """See base class."""
    super().__init__(*args, **kwargs)

    url = self.args.url or config.CONFIG["Webhook.url"]
    self._verify_https = config.CONFIG["Webhook.verify_https"] or False

    if not url:
      raise WebhookConfigurationError(
          "Cannot start WebhookOutputPlugin, because Webhook.url is not "
          "configured. Set it to the base URL of your Webhook installation, "
          "e.g. 'https://mywebhookserver.example.com:8088'."
      )

    self._url = urlparse(url).geturl()

  def ProcessResponses(
      self,
      state: rdf_protodict.AttributedDict,
      responses: list[rdf_flow_objects.FlowResult],
  ) -> None:
    """See base class."""
    client_id = self._GetClientId(responses)
    flow_id = self._GetFlowId(responses)

    client = self._GetClientMetadata(client_id)
    flow = self._GetFlowMetadata(client_id, flow_id)

    events = [self._MakeEvent(response, client, flow) for response in responses]
    self._SendEvents(events)

  def _GetClientId(self, responses: list[rdf_flow_objects.FlowResult]) -> str:
    client_ids = {msg.client_id for msg in responses}
    if len(client_ids) > 1:
      raise AssertionError(
          (
              "ProcessResponses received messages from different Clients {},"
              " which violates OutputPlugin constraints."
          ).format(client_ids)
      )
    return client_ids.pop()

  def _GetFlowId(self, responses: list[rdf_flow_objects.FlowResult]) -> str:
    flow_ids = {msg.flow_id for msg in responses}
    if len(flow_ids) > 1:
      raise AssertionError(
          (
              "ProcessResponses received messages from different Flows {},"
              " which violates OutputPlugin constraints."
          ).format(flow_ids)
      )
    return flow_ids.pop()

  def _GetClientMetadata(self, client_id: str) -> base.ExportedMetadata:
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)
    metadata = export.GetMetadata(client_id, info)
    metadata.timestamp = None  # timestamp is sent outside of metadata.
    return metadata

  def _GetFlowMetadata(self, client_id: str, flow_id: str) -> api_flow.ApiFlow:
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    proto_api_flow = api_flow.InitApiFlowFromFlowObject(flow_obj)
    rdf_api_flow = mig_flow.ToRDFApiFlow(proto_api_flow)
    return rdf_api_flow

  def _MakeEvent(
      self,
      message: rdf_flow_objects.FlowResult,
      client: base.ExportedMetadata,
      flow: api_flow.ApiFlow,
  ) -> JsonDict:

    if message.timestamp:
      time = message.timestamp.AsSecondsSinceEpoch()
    else:
      time = rdfvalue.RDFDatetime.Now().AsSecondsSinceEpoch()

    event = {
        "time": time,
        "host": client.hostname or message.client_id,
        "event": {
            "client": _ToDict(client),
            "flow": _ToDict(flow),
            "resultType": message.payload.__class__.__name__,
            "result": _ToDict(message.payload),
        },
    }

    if self.args.annotations:
      event["event"]["annotations"] = list(self.args.annotations)

    return event

  def _SendEvents(self, events: list[JsonDict]) -> None:
    # Batch multiple events in one request, separated by two newlines.
    data = "\n\n".join(json.dumps(event) for event in events)

    response = requests.post(
        url=self._url, verify=self._verify_https, data=data
    )
    response.raise_for_status()
