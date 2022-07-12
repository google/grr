#!/usr/bin/env python
"""OutputPlugin that sends Flow results to an Elasticsearch cluster.

Configuration values for this plugin can be found in
core/grr_response_core/config/output_plugins.py

The specification for the indexing of documents is
https://www.elastic.co/guide/en/elasticsearch/reference/7.1/docs-index_.html
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Text
from urllib import parse as urlparse

import requests

from google.protobuf import json_format
from grr_response_core import config
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util.compat import json
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import export
from grr_response_server import output_plugin
from grr_response_server.export_converters import base
from grr_response_server.gui.api_plugins import flow as api_flow

BULK_OPERATIONS_PATH = "_bulk"

# TODO(user): Use the JSON type.
JsonDict = Dict[Text, Any]


class ElasticsearchConfigurationError(Exception):
  """Error indicating a wrong or missing Elasticsearch configuration."""
  pass


class ElasticsearchOutputPluginArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the arguments of ElasticsearchOutputPlugin."""
  protobuf = output_plugin_pb2.ElasticsearchOutputPluginArgs
  rdf_deps = []


def _ToDict(rdfval: rdf_structs.RDFProtoStruct) -> JsonDict:
  return json_format.MessageToDict(rdfval.AsPrimitiveProto(), float_precision=8)


class ElasticsearchOutputPlugin(output_plugin.OutputPlugin):
  """OutputPlugin that sends Flow results to Elasticsearch."""

  name = "elasticsearch"
  description = "Send flow results to Elasticsearch."
  args_type = ElasticsearchOutputPluginArgs

  def __init__(self, *args, **kwargs):
    """Initializes the Elasticsearch output plugin."""
    super().__init__(*args, **kwargs)

    url = config.CONFIG["Elasticsearch.url"]
    if not url:
      raise ElasticsearchConfigurationError(
          "Cannot start ElasticsearchOutputPlugin, because Elasticsearch.url"
          "is not configured. Set it to the base URL of your Elasticsearch"
          "installation, e.g. 'https://myelasticsearch.example.com:9200'.")

    self._verify_https = config.CONFIG["Elasticsearch.verify_https"]
    self._token = config.CONFIG["Elasticsearch.token"]
    # Allow the Flow creator to override the index, fall back to configuration.
    self._index = self.args.index or config.CONFIG["Elasticsearch.index"]

    self._url = urlparse.urljoin(url, BULK_OPERATIONS_PATH)

  def ProcessResponses(self, state: rdf_protodict.AttributedDict,
                       responses: List[rdf_flows.GrrMessage]) -> None:
    """See base class."""
    client_id = self._GetClientId(responses)
    flow_id = self._GetFlowId(responses)

    client = self._GetClientMetadata(client_id)
    flow = self._GetFlowMetadata(client_id, flow_id)

    events = [self._MakeEvent(response, client, flow) for response in responses]
    self._SendEvents(events)

  def _GetClientId(self, responses: List[rdf_flows.GrrMessage]) -> Text:
    client_ids = {msg.source.Basename() for msg in responses}
    if len(client_ids) > 1:
      raise AssertionError((
          "ProcessResponses received messages from different Clients {}, which "
          "violates OutputPlugin constraints.").format(client_ids))
    return client_ids.pop()

  def _GetFlowId(self, responses: List[rdf_flows.GrrMessage]) -> Text:
    flow_ids = {msg.session_id.Basename() for msg in responses}
    if len(flow_ids) > 1:
      raise AssertionError(
          ("ProcessResponses received messages from different Flows {}, which "
           "violates OutputPlugin constraints.").format(flow_ids))
    return flow_ids.pop()

  def _GetClientMetadata(self, client_id: Text) -> base.ExportedMetadata:
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    metadata = export.GetMetadata(client_id, info)
    metadata.timestamp = None  # timestamp is sent outside of metadata.
    return metadata

  def _GetFlowMetadata(self, client_id: Text,
                       flow_id: Text) -> api_flow.ApiFlow:
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    return api_flow.ApiFlow().InitFromFlowObject(flow_obj)

  def _MakeEvent(self, message: rdf_flows.GrrMessage,
                 client: base.ExportedMetadata,
                 flow: api_flow.ApiFlow) -> JsonDict:

    event = {
        "client": _ToDict(client),
        "flow": _ToDict(flow),
        "resultType": message.args_rdf_name,
        "result": _ToDict(message.payload),
    }

    if self.args.tags:
      event["tags"] = list(self.args.tags)

    return event

  def _SendEvents(self, events: List[JsonDict]) -> None:
    """Uses the Elasticsearch bulk API to index all events in a single request."""
    # https://www.elastic.co/guide/en/elasticsearch/reference/7.1/docs-bulk.html

    if self._token:
      headers = {"Authorization": "Basic {}".format(self._token), "Content-Type": "application/json"}
    else:
      headers = {"Content-Type": "application/json"}

    index_command = json.Dump({"index": {"_index": self._index}}, indent=None)

    # Each index operation is two lines, the first defining the index settings,
    # the second is the actual document to be indexed
    data = "\n".join([
        "{}\n{}".format(index_command, json.Dump(event, indent=None))
        for event in events
    ]) + "\n"

    response = requests.post(
        url=self._url, verify=self._verify_https, data=data, headers=headers)
    response.raise_for_status()
