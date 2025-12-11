#!/usr/bin/env python
"""A registry of CSRF token generators."""

import logging

from grr_response_core import config
from grr_response_server.gui import csrf

CSRF_REGISTRY = {
    "RawKeyCSRFTokenGenerator": csrf.RawKeyCSRFTokenGenerator,
}


def CreateCSRFTokenGenerator() -> csrf.CSRFTokenGenerator:
  csrf_token_generator_cls = config.CONFIG["AdminUI.csrf_token_generator"]
  try:
    cls = CSRF_REGISTRY[csrf_token_generator_cls]
  except KeyError as exc:
    raise ValueError(
        "CSRF token generator %s not found." % csrf_token_generator_cls
    ) from exc
  logging.info("Using CSRF token generator: %s", csrf_token_generator_cls)
  return cls()
