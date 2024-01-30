#!/usr/bin/env python
"""Module containing code for user notifications reading/writing."""
from typing import Optional

from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.rdfvalues import mig_objects
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


# TODO: Use protos in this signature instead.
def Notify(
    username: str,
    notification_type: rdf_objects.UserNotification.Type,
    message: str,
    object_reference: Optional[rdf_objects.ObjectReference],
) -> None:
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
  proto_n = mig_objects.ToProtoUserNotification(n)
  data_store.REL_DB.WriteUserNotification(proto_n)
