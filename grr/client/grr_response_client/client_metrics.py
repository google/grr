#!/usr/bin/env python
"""Metrics used by the client."""

from grr_response_core.stats import metrics

GRR_CLIENT_RECEIVED_BYTES = metrics.Counter("grr_client_received_bytes")
GRR_CLIENT_SENT_BYTES = metrics.Counter("grr_client_sent_bytes")
