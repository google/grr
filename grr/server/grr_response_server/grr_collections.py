#!/usr/bin/env python
"""Some collections used in multiple places."""

from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib.rdfvalues import client as rdf_client
from grr.core.grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr.core.grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.server.grr_response_server import output_plugin
from grr.server.grr_response_server import sequential_collection
from grr.server.grr_response_server.rdfvalues import hunts as rdf_hunts


class LogCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_flows.FlowLog


class CrashCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_client.ClientCrash


class ClientUrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_client.ClientURN


class RDFUrnCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdfvalue.RDFURN


class HuntErrorCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_hunts.HuntError


class PluginStatusCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = output_plugin.OutputPluginBatchProcessingStatus


class SignedBlobCollection(sequential_collection.IndexedSequentialCollection):
  RDF_TYPE = rdf_crypto.SignedBlob
