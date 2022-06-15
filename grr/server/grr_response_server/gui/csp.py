#!/usr/bin/env python
"""WSGI compliant middleware that adds CSP headers to all responses."""
import json
from typing import Iterable, Mapping
from wsgiref import headers as wsgi_headers

import six

from grr_response_core import config

HEADER_KEY_REPORT_ONLY = "Content-Security-Policy-Report-Only"
HEADER_KEY_ENFORCE = "Content-Security-Policy"


def GetCspHeaderKey(report_only: bool) -> str:
  """Returns the right CSP header key (report-only or enforcing mode)."""
  if report_only:
    return HEADER_KEY_REPORT_ONLY
  else:
    return HEADER_KEY_ENFORCE


def BuildPolicy(policy: Mapping[str, Iterable[str]]) -> str:
  """Builds the CSP policy string from the internal representation."""
  csp_directives = [
      k + " " + " ".join(v) for k, v in six.iteritems(policy) if v is not None
  ]
  return "; ".join(csp_directives)


def CspMiddleware(application):
  """WSGI middleware for adding CSP header to response.

  Args:
      application: A WSGIApplication instance.

  Returns:
      A WSGIApplication instance.

  Raises:
      RuntimeError: If a report URI is specified in both AdminUI.csp_report_uri
      and AdminUI.csp_policy.
  """

  csp_header_enabled = config.CONFIG["AdminUI.csp_enabled"]
  csp_report_only = config.CONFIG["AdminUI.csp_report_only"]
  trusted_types_enabled = config.CONFIG["AdminUI.trusted_types_enabled"]
  trusted_types_report_only = config.CONFIG["AdminUI.trusted_types_report_only"]
  report_uri = config.CONFIG["AdminUI.csp_report_uri"]

  # CSP is enabled for the following URL path prefixes.
  include_url_prefixes = config.CONFIG["AdminUI.csp_include_url_prefixes"]

  # CSP is disabled for the following URL path prefixes.
  exclude_url_prefixes = config.CONFIG["AdminUI.csp_exclude_url_prefixes"]

  csp_policy = json.loads(config.CONFIG["AdminUI.csp_policy"])
  trusted_types_policy = {"require-trusted-types-for": ["'script'"]}

  if report_uri and "report-uri" in csp_policy:
    raise RuntimeError(
        "Report URI specified in both AdminUI.csp_report_uri and AdminUI.csp_policy."
    )

  if report_uri:
    csp_policy["report-uri"] = [report_uri]
    trusted_types_policy["report-uri"] = [report_uri]

  csp_directives = BuildPolicy(csp_policy)
  tt_directives = BuildPolicy(trusted_types_policy)

  def WsgiApp(environ, start_response):
    """Outer wrapper function around the WSGI protocol."""
    csp_enabled = csp_header_enabled
    csp_header_key = GetCspHeaderKey(csp_report_only)
    tt_enabled = trusted_types_enabled
    tt_header_key = GetCspHeaderKey(trusted_types_report_only)
    path_info = environ.get("PATH_INFO", "")

    # Enable CSP only on certain paths.
    if include_url_prefixes and not path_info.startswith(
        tuple(include_url_prefixes)):
      csp_enabled = False
      tt_enabled = False

    # Disable CSP on certain paths.
    if path_info.startswith(tuple(exclude_url_prefixes)):
      csp_enabled = False
      tt_enabled = False

    def CspStartResponse(status, headers, exc_info=None):
      """Add the CSP header to the response. Signature determined by WSGI."""
      # If the headers are given to us as a list or a dict, convert that to a
      # Headers object which can correctly support duplicate headers.
      if isinstance(headers, list):
        headers = wsgi_headers.Headers(headers)
      elif isinstance(headers, dict):
        headers = wsgi_headers.Headers(list(headers.items()))
      # Set CSP header if CSP is enabled.
      if csp_enabled:
        headers.add_header(csp_header_key, csp_directives)
      # Set Trusted Types CSP header if Trusted Types are enabled.
      if tt_enabled:
        headers.add_header(tt_header_key, tt_directives)

      # Pass the headers to the next middleware as a List[Tuple[str, str]] since
      # gunicorn needs them in that format.
      return start_response(status, headers.items(), exc_info)

    return application(environ, CspStartResponse)

  return WsgiApp
