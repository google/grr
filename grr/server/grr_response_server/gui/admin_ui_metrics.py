#!/usr/bin/env python
"""AdminUI metrics."""

from grr_response_core.stats import metrics


# Metrics for tracking AdminUI URL Handling in the WSGI app.
WSGI_ROUTE = metrics.Counter("wsgi_route", fields=[("url", str)])
