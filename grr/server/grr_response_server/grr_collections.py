#!/usr/bin/env python
"""Some collections used in multiple places."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import output_plugin
from grr_response_server import sequential_collection
from grr_response_server.rdfvalues import hunts as rdf_hunts


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
