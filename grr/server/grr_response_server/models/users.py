#!/usr/bin/env python
"""Provides user-related data models and helpers."""

from grr_response_core import config
from grr_response_proto import objects_pb2


def GetEmail(user: objects_pb2.GRRUser) -> str:
  """Returns the E-Mail address for the user."""
  if config.CONFIG.Get("Email.enable_custom_email_address") and user.email:
    return user.email
  domain = config.CONFIG.Get("Logging.domain")
  return f"{user.username}@{domain}"
