#!/usr/bin/env python
"""Utils for use from the console.

Includes functions that are used by interactive console utilities such as
approval or token handling.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import getpass
import io
import logging
import os
import time


from builtins import input  # pylint: disable=redefined-builtin
from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import string_types

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import csv
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import client_index
from grr_response_server import data_migration
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import queue_manager
from grr_response_server import worker_lib
from grr_response_server.aff4_objects import security
from grr_response_server.aff4_objects import users


def FormatISOTime(t):
  """Format a time in epoch notation to ISO UTC."""
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t / 1e6))


def SearchClients(query_str, token=None, limit=1000):
  """Search indexes for clients. Returns list (client, hostname, os version)."""
  client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
  index = client_index.CreateClientIndex(token=token)

  client_list = index.LookupClients([query_str])
  result_set = aff4.FACTORY.MultiOpen(client_list, token=token)
  results = []
  for result in result_set:
    results.append((result, str(result.Get(client_schema.HOSTNAME)),
                    str(result.Get(client_schema.OS_VERSION)),
                    str(result.Get(client_schema.PING))))
    if len(results) >= limit:
      break

  return results


def DownloadDir(aff4_path, output_dir, bufsize=8192, preserve_path=True):
  """Take an aff4 path and download all files in it to output_dir.

  Args:
    aff4_path: Any aff4 path as a string
    output_dir: A local directory to write to, will be created if not there.
    bufsize: Buffer size to use.
    preserve_path: If set all paths will be created.

  Note that this works for collections as well. It will download all
  files in the collection.

  This only downloads files that are already in the datastore, it doesn't
  queue anything on the client.
  """
  if not os.path.isdir(output_dir):
    os.makedirs(output_dir)
  fd = aff4.FACTORY.Open(aff4_path)
  for child in fd.OpenChildren():
    if preserve_path:
      # Get a full path without the aff4:
      full_dir = utils.JoinPath(output_dir, child.urn.Path())
      full_dir = os.path.dirname(full_dir)
      if not os.path.isdir(full_dir):
        os.makedirs(full_dir)
      outfile = os.path.join(full_dir, child.urn.Basename())
    else:
      outfile = os.path.join(output_dir, child.urn.Basename())
    logging.info(u"Downloading %s to %s", child.urn, outfile)
    with open(outfile, "wb") as out_fd:
      try:
        buf = child.Read(bufsize)
        while buf:
          out_fd.write(buf)
          buf = child.Read(bufsize)
      except IOError as e:
        logging.error("Failed to read %s. Err: %s", child.urn, e)


def GetToken():
  user = getpass.getuser()
  return access_control.ACLToken(username=user)


def OpenClient(client_id=None, token=None):
  """Opens the client, getting potential approval tokens.

  Args:
    client_id: The client id that should be opened.
    token: Token to use to open the client

  Returns:
    tuple containing (client, token) objects or (None, None) on if
    no appropriate aproval tokens were found.
  """
  if not token:
    try:
      token = ApprovalFind(client_id, token=token)
    except access_control.UnauthorizedAccess as e:
      logging.debug("No authorization found for access to client: %s", e)

  try:
    # Try and open with the token we managed to retrieve or the default.
    client = aff4.FACTORY.Open(
        rdfvalue.RDFURN(client_id), mode="r", token=token)
    return client, token
  except access_control.UnauthorizedAccess:
    logging.warning(
        "Unable to find a valid reason for client %s. You may need "
        "to request approval.", client_id)
    return None, None


def GetNotifications(user=None, token=None):
  """Show pending notifications for a user."""
  if not user:
    user = getpass.getuser()
  user_obj = aff4.FACTORY.Open(
      aff4.ROOT_URN.Add("users").Add(user), token=token)
  return list(user_obj.Get(user_obj.Schema.PENDING_NOTIFICATIONS))


def ApprovalRequest(client_id,
                    token=None,
                    approver="approver",
                    reason="testing"):
  token = token or GetToken()
  approval_reason = reason or token.reason
  security.ClientApprovalRequestor(
      reason=approval_reason,
      subject_urn=rdf_client.ClientURN(client_id),
      approver=approver,
      token=token).Request()


# TODO(user): refactor this approval request/grant code into a separate
# module that can be used by both this and test_lib. Currently duplicated.
def RequestAndGrantClientApproval(client_id,
                                  token=None,
                                  approver="approver",
                                  reason="testing"):
  token = token or GetToken()
  ApprovalRequest(client_id, token=token, approver=approver, reason=reason)
  user = aff4.FACTORY.Create(
      "aff4:/users/%s" % approver, users.GRRUser, token=token.SetUID())
  user.Flush()
  approver_token = access_control.ACLToken(username=approver)
  security.ClientApprovalGrantor(
      reason=reason,
      delegate=token.username,
      subject_urn=rdf_client.ClientURN(client_id),
      token=approver_token).Grant()


def ApprovalGrant(token=None):
  """Iterate through requested access approving or not."""
  user = getpass.getuser()
  notifications = GetNotifications(user=user, token=token)
  requests = [n for n in notifications if n.type == "GrantAccess"]
  for request in requests:
    _, client_id, user, reason = rdfvalue.RDFURN(request.subject).Split()
    reason = utils.DecodeReasonString(reason)
    print(request)
    print("Reason: %s" % reason)
    if input("Do you approve this request? [y/N] ").lower() == "y":
      security.ClientApprovalGrantor(
          subject_urn=client_id, reason=reason, delegate=user,
          token=token).Grant()
      # TODO(user): Remove the notification.
    else:
      print("skipping request")
    print("Approval sent")


def ApprovalFind(object_id, token=None):
  """Find approvals issued for a specific client."""
  user = getpass.getuser()
  object_id = rdfvalue.RDFURN(object_id)
  try:
    approved_token = security.Approval.GetApprovalForObject(
        object_id, token=token, username=user)
    print("Found token %s" % str(approved_token))
    return approved_token
  except access_control.UnauthorizedAccess:
    print("No token available for access to %s" % object_id)


def ApprovalCreateRaw(aff4_path,
                      reason="",
                      expire_in=60 * 60 * 24 * 7,
                      token=None,
                      approval_type="ClientApproval"):
  """Creates an approval with raw access.

  This method requires raw datastore access to manipulate approvals directly.
  This currently doesn't work for hunt or cron approvals, because they check
  that each approver has the admin label.  Since the fake users don't exist the
  check fails.

  Args:
    aff4_path: The aff4_path or client id the approval should be created for.
    reason: The reason to put in the token.
    expire_in: Expiry in seconds to use in the token.
    token: The token that will be used. If this is specified reason and expiry
        are ignored.
    approval_type: The type of the approval to create.

  Returns:
    The token.

  Raises:
    RuntimeError: On bad token.
  """
  if approval_type in ["ClientApproval", security.ClientApproval]:
    urn = rdf_client.ClientURN(aff4_path)
  else:
    urn = rdfvalue.RDFURN(aff4_path)

  if not token:
    expiry = time.time() + expire_in
    token = access_control.ACLToken(reason=reason, expiry=expiry)

  if not token.reason:
    raise RuntimeError("Cannot create approval with empty reason")
  if not token.username:
    token.username = getpass.getuser()
  approval_urn = security.ApprovalRequestor.ApprovalUrnBuilder(
      urn.Path(), token.username, token.reason)
  super_token = access_control.ACLToken(username="raw-approval-superuser")
  super_token.supervisor = True

  if isinstance(approval_type, string_types):
    approval_type_cls = aff4.AFF4Object.classes[approval_type]
  else:
    approval_type_cls = approval_type

  approval_request = aff4.FACTORY.Create(
      approval_urn, approval_type_cls, mode="rw", token=super_token)

  # Add approvals indicating they were approved by fake "raw" mode users.
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s1-raw" % token.username))
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s-raw2" % token.username))
  approval_request.Close()


def ApprovalRevokeRaw(aff4_path, token):
  """Revokes an approval for a given token.

  This method requires raw datastore access to manipulate approvals directly.

  Args:
    aff4_path: The aff4_path or client id the approval should be created for.
    token: The token that should be revoked.
  """
  try:
    urn = rdf_client.ClientURN(aff4_path)
  except type_info.TypeValueError:
    urn = rdfvalue.RDFURN(aff4_path)

  approval_urn = aff4.ROOT_URN.Add("ACL").Add(urn.Path()).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = access_control.ACLToken(username="raw-approval-superuser")
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Open(
      approval_urn, mode="rw", token=super_token)
  approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
  approval_request.Close()


def _GetHWInfos(client_list, batch_size=10000, token=None):
  """Opens the given clients in batches and returns hardware information."""

  # This function returns a dict mapping each client_id to a set of reported
  # hardware serial numbers reported by this client.
  hw_infos = {}

  logging.info("%d clients to process.", len(client_list))

  c = 0

  for batch in collection.Batch(client_list, batch_size):
    logging.info("Processing batch: %d-%d", c, c + batch_size)
    c += len(batch)

    client_objs = aff4.FACTORY.MultiOpen(batch, age=aff4.ALL_TIMES, token=token)

    for client in client_objs:
      hwi = client.GetValuesForAttribute(client.Schema.HARDWARE_INFO)

      hw_infos[client.urn] = set(["%s" % x.serial_number for x in hwi])

  return hw_infos


def FindClonedClients(token=None):
  """A script to find multiple machines reporting the same client_id.

  This script looks at the hardware serial numbers that a client reported in
  over time (they get collected with each regular interrogate). We have seen
  that sometimes those serial numbers change - for example when a disk is put
  in a new machine - so reporting multiple serial numbers does not flag a client
  immediately as a cloned machine. In order to be shown here by this script, the
  serial number has to be alternating between two values.

  Args:
    token: datastore token.
  Returns:
    A list of clients that report alternating hardware ids.
  """

  index = client_index.CreateClientIndex(token=token)

  clients = index.LookupClients(["."])

  hw_infos = _GetHWInfos(clients, token=token)

  # We get all clients that have reported more than one hardware serial
  # number over time. This doesn't necessarily indicate a cloned client - the
  # machine might just have new hardware. We need to search for clients that
  # alternate between different IDs.
  clients_with_multiple_serials = [
      client_id for client_id, serials in iteritems(hw_infos)
      if len(serials) > 1
  ]

  client_list = aff4.FACTORY.MultiOpen(
      clients_with_multiple_serials, age=aff4.ALL_TIMES, token=token)

  cloned_clients = []
  for c in client_list:
    hwis = c.GetValuesForAttribute(c.Schema.HARDWARE_INFO)

    # Here we search for the earliest and latest time each ID was reported.
    max_index = {}
    min_index = {}
    ids = set()

    for i, hwi in enumerate(hwis):
      s = hwi.serial_number
      max_index[s] = i
      if s not in min_index:
        min_index[s] = i
      ids.add(s)

    # Construct ranges [first occurrence, last occurrence] for every ID. If
    # a client just changed from one ID to the other, those ranges of IDs should
    # be disjunct. If they overlap at some point, it indicates that two IDs were
    # reported in the same time frame.
    ranges = []
    for hwid in ids:
      ranges.append((min_index[hwid], max_index[hwid]))
    # Sort ranges by first occurrence time.
    ranges.sort()

    for i in range(len(ranges) - 1):
      if ranges[i][1] > ranges[i + 1][0]:
        cloned_clients.append(c)

        msg = "Found client with multiple, overlapping serial numbers: %s"
        logging.info(msg, c.urn)
        for hwi in c.GetValuesForAttribute(c.Schema.HARDWARE_INFO):
          logging.info("%s %s", hwi.age, hwi.serial_number)
        break

  return cloned_clients


def CleanClientVersions(clients=None, dry_run=True, token=None):
  """A script to remove excessive client versions.

  Especially when a client is heavily cloned, we sometimes write an excessive
  number of versions of it. Since these version all go into the same database
  row and are displayed as a dropdown list in the adminui, it is sometimes
  necessary to clear them out.

  This deletes version from clients so that we have at most one
  version per hour.

  Args:
    clients: A list of ClientURN, if empty cleans all clients.
    dry_run: whether this is a dry run
    token: datastore token.
  """
  if not clients:
    index = client_index.CreateClientIndex(token=token)
    clients = index.LookupClients(["."])
  clients.sort()
  with data_store.DB.GetMutationPool() as pool:

    logging.info("checking %d clients", len(clients))

    # TODO(amoser): This only works on datastores that use the Bigtable scheme.
    client_infos = data_store.DB.MultiResolvePrefix(
        clients, "aff4:type", data_store.DB.ALL_TIMESTAMPS)

    for client, type_list in client_infos:
      logging.info("%s: has %d versions", client, len(type_list))
      cleared = 0
      kept = 1
      last_kept = type_list[0][2]
      for _, _, ts in type_list[1:]:
        if last_kept - ts > 60 * 60 * 1000000:  # 1 hour
          last_kept = ts
          kept += 1
        else:
          if not dry_run:
            pool.DeleteAttributes(client, ["aff4:type"], start=ts, end=ts)
          cleared += 1
          if pool.Size() > 10000:
            pool.Flush()
      logging.info("%s: kept %d and cleared %d", client, kept, cleared)


def CleanVacuousVersions(clients=None, dry_run=True):
  """A script to remove no-op client versions.

  This script removes versions of a client when it is identical to the previous,
  in the sense that no versioned attributes were changed since the previous
  client version.

  Args:
    clients: A list of ClientURN, if empty cleans all clients.
    dry_run: whether this is a dry run
  """

  if not clients:
    index = client_index.CreateClientIndex()
    clients = index.LookupClients(["."])
  clients.sort()
  with data_store.DB.GetMutationPool() as pool:

    logging.info("checking %d clients", len(clients))
    for batch in collection.Batch(clients, 10000):
      # TODO(amoser): This only works on datastores that use the Bigtable
      # scheme.
      client_infos = data_store.DB.MultiResolvePrefix(
          batch, ["aff4:", "aff4:"], data_store.DB.ALL_TIMESTAMPS)

      for client, type_list in client_infos:
        cleared = 0
        kept = 0
        updates = []
        for a, _, ts in type_list:
          if ts != 0:
            updates.append((ts, a))
        updates = sorted(updates)
        dirty = True
        for ts, a in updates:
          if a == "aff4:type":
            if dirty:
              kept += 1
              dirty = False
            else:
              cleared += 1
              if not dry_run:
                pool.DeleteAttributes(client, ["aff4:type"], start=ts, end=ts)
                if pool.Size() > 1000:
                  pool.Flush()
          else:
            dirty = True
        logging.info("%s: kept %d and cleared %d", client, kept, cleared)


def ExportClientsByKeywords(keywords, filename, token=None):
  r"""A script to export clients summaries selected by a keyword search.

  This script does a client search for machines matching all of keywords and
  writes a .csv summary of the results to filename. Multi-value fields are '\n'
  separated.

  Args:
    keywords: a list of keywords to search for

    filename: the name of the file to write to, will be replaced if already
      present

    token: datastore token.
  """
  index = client_index.CreateClientIndex(token=token)
  client_list = index.LookupClients(keywords)
  logging.info("found %d clients", len(client_list))
  if not client_list:
    return

  writer = csv.DictWriter([
      u"client_id",
      u"hostname",
      u"last_seen",
      u"os",
      u"os_release",
      u"os_version",
      u"users",
      u"ips",
      u"macs",
  ])
  writer.WriteHeader()

  for client in aff4.FACTORY.MultiOpen(client_list, token=token):
    s = client.Schema
    writer.WriteRow({
        u"client_id": client.urn.Basename(),
        u"hostname": client.Get(s.HOSTNAME),
        u"os": client.Get(s.SYSTEM),
        u"os_release": client.Get(s.OS_RELEASE),
        u"os_version": client.Get(s.OS_VERSION),
        u"ips": client.Get(s.HOST_IPS),
        u"macs": client.Get(s.MAC_ADDRESS),
        u"users": "\n".join(client.Get(s.USERNAMES, [])),
        u"last_seen": client.Get(s.PING),
    })

  with io.open(filename, "w") as csv_out:
    csv_out.write(writer.Content())


# Pull this into the console.
ConvertVFSGRRClient = data_migration.ConvertVFSGRRClient  # pylint: disable=invalid-name


def StartFlowAndWorker(client_id, flow_name, **kwargs):
  """Launches the flow and worker and waits for it to finish.

  Args:
     client_id: The client common name we issue the request.
     flow_name: The name of the flow to launch.
     **kwargs: passthrough to flow.

  Returns:
     A flow session id.

  Note: you need raw access to run this flow as it requires running a worker.
  """
  # Empty token, only works with raw access.
  queue = rdfvalue.RDFURN("DEBUG-%s-" % getpass.getuser())
  if "token" in kwargs:
    token = kwargs.pop("token")
  else:
    token = access_control.ACLToken(username="GRRConsole")

  session_id = flow.StartAFF4Flow(
      client_id=client_id,
      flow_name=flow_name,
      queue=queue,
      token=token,
      **kwargs)
  worker_thrd = worker_lib.GRRWorker(
      queues=[queue], token=token, threadpool_size=1)
  while True:
    try:
      worker_thrd.RunOnce()
    except KeyboardInterrupt:
      print("exiting")
      worker_thrd.thread_pool.Join()
      break

    time.sleep(2)
    with aff4.FACTORY.Open(session_id, token=token) as flow_obj:
      if not flow_obj.GetRunner().IsRunning():
        break

  # Terminate the worker threads
  worker_thrd.thread_pool.Join()

  return session_id


def WakeStuckFlow(session_id):
  """Wake up stuck flows.

  A stuck flow is one which is waiting for the client to do something, but the
  client requests have been removed from the client queue. This can happen if
  the system is too loaded and the client messages have TTLed out. In this case
  we reschedule the client requests for this session.

  Args:
    session_id: The session for the flow to wake.

  Returns:
    The total number of client messages re-queued.
  """
  session_id = rdfvalue.SessionID(session_id)
  woken = 0
  checked_pending = False

  with queue_manager.QueueManager() as manager:
    for request, responses in manager.FetchRequestsAndResponses(session_id):
      # We need to check if there are client requests pending.
      if not checked_pending:
        task = manager.Query(
            request.client_id, task_id="task:%s" % request.request.task_id)

        if task:
          # Client has tasks pending already.
          return

        checked_pending = True

      if (not responses or
          responses[-1].type != rdf_flows.GrrMessage.Type.STATUS):
        manager.QueueClientMessage(request.request)
        woken += 1

      if responses and responses[-1].type == rdf_flows.GrrMessage.Type.STATUS:
        manager.QueueNotification(session_id)

  return woken
