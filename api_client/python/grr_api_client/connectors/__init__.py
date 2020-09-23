#!/usr/bin/env python
"""Python GRR API connectors library."""
from grr_api_client.connectors import abstract
from grr_api_client.connectors import http

# Re-export useful connectors.
Connector = abstract.Connector
HttpConnector = http.HttpConnector
