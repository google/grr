#!/usr/bin/env python
"""Module containing code for user notifications reading/writing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging

from grr_response_server import aff4

from grr_response_server import data_store
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.rdfvalues import objects as rdf_objects


def _HostPrefix(client_id):
  """Build a host prefix for a notification message based on a client id."""
  if not client_id:
    return ""

  hostname = None
  if data_store.RelationalDBReadEnabled():
    client_snapshot = data_store.REL_DB.ReadClientSnapshot(client_id)
    if client_snapshot:
      hostname = client_snapshot.knowledge_base.fqdn
  else:
    client_fd = aff4.FACTORY.Open(client_id, mode="rw")
    hostname = client_fd.Get(client_fd.Schema.FQDN) or ""

  if hostname:
    return "%s: " % hostname
  else:
    return ""


def _MapLegacyArgs(nt, message, ref):
  """Maps UserNotification object to legacy GRRUser.Notify arguments."""
  unt = rdf_objects.UserNotification.Type

  if nt == unt.TYPE_CLIENT_INTERROGATED:
    return [
        "Discovery",
        aff4.ROOT_URN.Add(ref.client.client_id),
        _HostPrefix(ref.client.client_id) + message,
        "",
    ]
  elif nt == unt.TYPE_CLIENT_APPROVAL_REQUESTED:
    return [
        "GrantAccess",
        aff4.ROOT_URN.Add("ACL").Add(ref.approval_request.subject_id).Add(
            ref.approval_request.requestor_username).Add(
                ref.approval_request.approval_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_HUNT_APPROVAL_REQUESTED:
    return [
        "GrantAccess",
        aff4.ROOT_URN.Add("ACL").Add("hunts").Add(
            ref.approval_request.subject_id).Add(
                ref.approval_request.requestor_username).Add(
                    ref.approval_request.approval_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_CRON_JOB_APPROVAL_REQUESTED:
    return [
        "GrantAccess",
        aff4.ROOT_URN.Add("ACL").Add("cron").Add(
            ref.approval_request.subject_id).Add(
                ref.approval_request.requestor_username).Add(
                    ref.approval_request.approval_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_CLIENT_APPROVAL_GRANTED:
    return [
        "ViewObject",
        aff4.ROOT_URN.Add(ref.client.client_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_HUNT_APPROVAL_GRANTED:
    return [
        "ViewObject",
        aff4.ROOT_URN.Add("hunts").Add(ref.hunt.hunt_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_CRON_JOB_APPROVAL_GRANTED:
    return [
        "ViewObject",
        aff4.ROOT_URN.Add("cron").Add(ref.cron_job.cron_job_id),
        message,
        "",
    ]
  elif nt == unt.TYPE_VFS_FILE_COLLECTED:
    return [
        "ViewObject",
        ref.vfs_file.ToURN(),
        _HostPrefix(ref.vfs_file.client_id) + message,
        "",
    ]
  elif nt == unt.TYPE_VFS_FILE_COLLECTION_FAILED:
    return [
        "ViewObject",
        ref.vfs_file.ToURN(),
        _HostPrefix(ref.vfs_file.client_id) + message,
        "",
    ]
  elif nt == unt.TYPE_HUNT_STOPPED:
    urn = aff4.ROOT_URN.Add("hunts").Add(ref.hunt.hunt_id)
    return [
        "ViewObject",
        urn,
        message,
        urn,
    ]
  elif nt == unt.TYPE_FILE_ARCHIVE_GENERATED:
    return [
        "ArchiveGenerationFinished",
        None,
        message,
        "",
    ]
  elif nt == unt.TYPE_FILE_ARCHIVE_GENERATION_FAILED:
    return [
        "Error",
        None,
        message,
        "",
    ]
  elif nt == unt.TYPE_FLOW_RUN_COMPLETED:
    urn = None
    if ref.flow and ref.flow.client_id and ref.flow.flow_id:
      urn = aff4.ROOT_URN.Add(ref.flow.client_id).Add("flows").Add(
          ref.flow.flow_id)
    return [
        "ViewObject",
        urn,
        _HostPrefix(ref.flow.client_id) + message,
        "",
    ]
  elif nt == unt.TYPE_FLOW_RUN_FAILED:
    client_id = None
    urn = None
    prefix = ""
    if ref.flow is not None:
      client_id = ref.flow.client_id

      if client_id:
        prefix = _HostPrefix(client_id)

        if ref.flow.flow_id:
          urn = aff4.ROOT_URN.Add(ref.flow.client_id).Add("flows").Add(
              ref.flow.flow_id)

    return [
        "FlowStatus",
        client_id,
        prefix + message,
        urn,
    ]
  elif nt == unt.TYPE_VFS_LIST_DIRECTORY_COMPLETED:
    return [
        "ViewObject",
        ref.vfs_file.ToURN(),
        message,
        "",
    ]
  elif nt == unt.TYPE_VFS_RECURSIVE_LIST_DIRECTORY_COMPLETED:
    return [
        "ViewObject",
        ref.vfs_file.ToURN(),
        message,
        "",
    ]
  else:
    raise NotImplementedError()


def _NotifyLegacy(username, notification_type, message, object_reference):
  """Schedules a legacy AFF4 user notification."""

  try:
    with aff4.FACTORY.Open(
        aff4.ROOT_URN.Add("users").Add(username),
        aff4_type=aff4_users.GRRUser,
        mode="rw") as fd:

      args = _MapLegacyArgs(notification_type, message, object_reference)
      args[0] += ":%s" % notification_type
      fd.Notify(*args)

  except aff4.InstantiationError:
    logging.error("Trying to notify non-existent user: %s", username)


def _Notify(username, notification_type, message, object_reference):
  """Schedules a new-style REL_DB user notification."""

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


def Notify(username, notification_type, message, object_reference):
  if data_store.RelationalDBReadEnabled():
    _Notify(username, notification_type, message, object_reference)

  if data_store.AFF4Enabled():
    _NotifyLegacy(username, notification_type, message, object_reference)
