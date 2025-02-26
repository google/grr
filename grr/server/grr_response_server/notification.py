#!/usr/bin/env python
"""Module containing code for user notifications reading/writing."""

from typing import Optional

from grr_response_proto import objects_pb2
from grr_response_server import access_control
from grr_response_server import data_store


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


def ClientIdFromObjectReference(
    object_reference: objects_pb2.ObjectReference,
) -> Optional[str]:
  """Returns the client ID from the given object reference, or None."""
  if object_reference.reference_type == objects_pb2.ObjectReference.CLIENT:
    return object_reference.client.client_id
  elif object_reference.reference_type == objects_pb2.ObjectReference.FLOW:
    return object_reference.flow.client_id
  elif object_reference.reference_type == objects_pb2.ObjectReference.VFS_FILE:
    return object_reference.vfs_file.client_id
  elif (
      object_reference.reference_type
      == objects_pb2.ObjectReference.APPROVAL_REQUEST
      and object_reference.approval_request.approval_type
      == objects_pb2.ApprovalRequest.ApprovalType.APPROVAL_TYPE_CLIENT
  ):
    return object_reference.approval_request.subject_id
  else:
    return None


def Notify(
    username: str,
    notification_type: "objects_pb2.UserNotification.Type",
    message: str,
    object_reference: Optional[objects_pb2.ObjectReference],
) -> None:
  """Schedules a new-style REL_DB user notification."""

  # Do not try to notify system users (e.g. Cron).
  if username in access_control.SYSTEM_USERS:
    return

  if object_reference:
    client_id = ClientIdFromObjectReference(object_reference)
    if client_id:
      message = _HostPrefix(client_id) + message

  n = objects_pb2.UserNotification(
      username=username,
      notification_type=notification_type,
      state=objects_pb2.UserNotification.State.STATE_PENDING,
      message=message,
      reference=object_reference,
  )
  data_store.REL_DB.WriteUserNotification(n)
