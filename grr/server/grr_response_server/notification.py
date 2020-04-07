#!/usr/bin/env python
# Lint as: python3
"""Module containing code for user notifications reading/writing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects


def _HostPrefix(client_id):
  """Build a host prefix for a notification message based on a client id."""
  if not client_id:
    return ""

  hostname = None
  client_snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
  if client_snapshot:
    hostname = client_snapshot.knowledge_base.fqdn

  if hostname:
    return "%s: " % hostname
  else:
    return ""


def Notify(username, notification_type, message, object_reference):
  """Schedules a new-style REL_DB user notification."""

  # Do not try to notify system users (e.g. Cron).
  if username in access_control.SYSTEM_USERS:
    return

  if object_reference:
    uc = object_reference.UnionCast()
    if hasattr(uc, "client_id"):
      message = _HostPrefix(uc.client_id) + message

  n = rdf_objects.UserNotification(
      username=username,
      notification_type=notification_type,
      state=rdf_objects.UserNotification.State.STATE_PENDING,
      message=message,
      reference=object_reference)
  data_store.REL_DB.WriteUserNotification(n)
