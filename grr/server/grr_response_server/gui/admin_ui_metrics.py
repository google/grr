#!/usr/bin/env python
"""AdminUI metrics."""

from grr_response_core.stats import metrics


# Metrics for tracking AdminUI v1->v2 migration.
UI_REDIRECT = metrics.Counter(
    "ui_redirect", fields=[("direction", str), ("source", str)]
)

# Metrics for tracking AdminUI URL Handling in the WSGI app.
# Important: for the legacy UI, moving between pages should not reach the WSGI
# app, rather just handled by the AngularJS app directly. With Angular2, this
# is not the case, and "sub-routes" will go through the WSGI app. Thus, we
# expect that `v2` paths will show more times than `legacy` ones.
WSGI_ROUTE = metrics.Counter("wsgi_route", fields=[("url", str)])

# Allowlist counter metrics that can be increased through API call.
API_INCREASE_ALLOWLIST = frozenset([UI_REDIRECT.name])
