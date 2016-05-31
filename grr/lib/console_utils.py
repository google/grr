#!/usr/bin/env python
"""Utils for use from the console.

Includes functions that are used by interactive console utilities such as
approval or token handling.
"""

import getpass
import os
import time

import logging

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import security
from grr.lib.aff4_objects import users
from grr.lib.hunts import implementation as hunts_implementation
from grr.lib.rdfvalues import client as rdf_client


def FormatISOTime(t):
  """Format a time in epoch notation to ISO UTC."""
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t / 1e6))


def SearchClients(query_str, token=None, limit=1000):
  """Search indexes for clients. Returns list (client, hostname, os version)."""
  client_schema = aff4.AFF4Object.classes[aff4_grr.VFSGRRClient].SchemaCls
  index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                              aff4_type=client_index.ClientIndex,
                              mode="rw",
                              token=token)

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


def ListDrivers():
  """Print a list of drivers in the datastore."""
  aff4_paths = set()
  token = GetToken()
  for client_context in [["Platform:Darwin", "Arch:amd64"],
                         ["Platform:Windows", "Arch:i386"],
                         ["Platform:Windows", "Arch:amd64"]]:
    aff4_paths.update(config_lib.CONFIG.Get("MemoryDriver.aff4_paths",
                                            context=client_context))

  for driver in aff4.FACTORY.MultiOpen(aff4_paths, mode="r", token=token):
    print driver


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
        rdfvalue.RDFURN(client_id),
        mode="r", token=token)
    return client, token
  except access_control.UnauthorizedAccess:
    logging.warning("Unable to find a valid reason for client %s. You may need "
                    "to request approval.", client_id)
    return None, None


def GetNotifications(user=None, token=None):
  """Show pending notifications for a user."""
  if not user:
    user = getpass.getuser()
  user_obj = aff4.FACTORY.Open(
      aff4.ROOT_URN.Add("users").Add(user),
      token=token)
  return list(user_obj.Get(user_obj.Schema.PENDING_NOTIFICATIONS))


def ApprovalRequest(client_id,
                    token=None,
                    approver="approver",
                    reason="testing"):
  token = token or GetToken()
  approval_reason = reason or token.reason
  flow.GRRFlow.StartFlow(client_id=client_id,
                         flow_name="RequestClientApprovalFlow",
                         reason=approval_reason,
                         subject_urn=rdf_client.ClientURN(client_id),
                         approver=approver,
                         token=token)


# TODO(user): refactor this approval request/grant code into a separate
# module that can be used by both this and test_lib. Currently duplicated.
def RequestAndGrantClientApproval(client_id,
                                  token=None,
                                  approver="approver",
                                  reason="testing"):
  token = token or GetToken()
  ApprovalRequest(client_id, token=token, approver=approver, reason=reason)
  user = aff4.FACTORY.Create("aff4:/users/%s" % approver,
                             users.GRRUser,
                             token=token.SetUID())
  user.Flush()
  approver_token = access_control.ACLToken(username=approver)
  flow.GRRFlow.StartFlow(client_id=client_id,
                         flow_name="GrantClientApprovalFlow",
                         reason=reason,
                         delegate=token.username,
                         subject_urn=rdf_client.ClientURN(client_id),
                         token=approver_token)


def ApprovalGrant(token=None):
  """Iterate through requested access approving or not."""
  user = getpass.getuser()
  notifications = GetNotifications(user=user, token=token)
  requests = [n for n in notifications if n.type == "GrantAccess"]
  for request in requests:
    _, client_id, user, reason = rdfvalue.RDFURN(request.subject).Split()
    reason = utils.DecodeReasonString(reason)
    print request
    print "Reason: %s" % reason
    if raw_input("Do you approve this request? [y/N] ").lower() == "y":
      flow_id = flow.GRRFlow.StartFlow(client_id=client_id,
                                       flow_name="GrantClientApprovalFlow",
                                       reason=reason,
                                       delegate=user,
                                       token=token)
      # TODO(user): Remove the notification.
    else:
      print "skipping request"
    print "Approval sent: %s" % flow_id


def ApprovalFind(object_id, token=None):
  """Find approvals issued for a specific client."""
  user = getpass.getuser()
  object_id = rdfvalue.RDFURN(object_id)
  try:
    approved_token = security.Approval.GetApprovalForObject(object_id,
                                                            token=token,
                                                            username=user)
    print "Found token %s" % str(approved_token)
    return approved_token
  except access_control.UnauthorizedAccess:
    print "No token available for access to %s" % object_id


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
  if approval_type == "ClientApproval":
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
  approval_urn = flow.GRRFlow.RequestApprovalWithReasonFlow.ApprovalUrnBuilder(
      urn.Path(), token.username, token.reason)
  super_token = access_control.ACLToken(username="raw-approval-superuser")
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Create(approval_urn,
                                         approval_type,
                                         mode="rw",
                                         token=super_token)

  # Add approvals indicating they were approved by fake "raw" mode users.
  approval_request.AddAttribute(approval_request.Schema.APPROVER(
      "%s1-raw" % token.username))
  approval_request.AddAttribute(approval_request.Schema.APPROVER(
      "%s-raw2" % token.username))
  approval_request.Close(sync=True)


def ApprovalRevokeRaw(aff4_path, token, remove_from_cache=False):
  """Revokes an approval for a given token.

  This method requires raw datastore access to manipulate approvals directly.

  Args:
    aff4_path: The aff4_path or client id the approval should be created for.
    token: The token that should be revoked.
    remove_from_cache: If True, also remove the approval from the
                       security_manager cache.
  """
  try:
    urn = rdf_client.ClientURN(aff4_path)
  except type_info.TypeValueError:
    urn = rdfvalue.RDFURN(aff4_path)

  approval_urn = aff4.ROOT_URN.Add("ACL").Add(urn.Path()).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = access_control.ACLToken(username="raw-approval-superuser")
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Open(approval_urn,
                                       mode="rw",
                                       token=super_token)
  approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
  approval_request.Close()

  if remove_from_cache:
    data_store.DB.security_manager.acl_cache.ExpireObject(utils.SmartUnicode(
        approval_urn))


# TODO(user): remove as soon as migration is complete.
def MigrateObjectsLabels(root_urn, obj_type, label_suffix=None, token=None):
  """Migrates labels of object under given root (non-recursive)."""

  root = aff4.FACTORY.Create(root_urn, aff4.AFF4Volume, mode="r", token=token)
  children_urns = list(root.ListChildren())

  if label_suffix:
    children_urns = [urn.Add(label_suffix) for urn in children_urns]

  print "Found %d children." % len(children_urns)

  updated_objects = 0
  ignored_objects = 0
  for child in aff4.FACTORY.MultiOpen(children_urns,
                                      mode="rw",
                                      token=token,
                                      age=aff4.NEWEST_TIME):

    if isinstance(child, obj_type):
      print "Current state: %d updated, %d ignored." % (updated_objects,
                                                        ignored_objects)

      old_labels = child.Get(child.Schema.DEPRECATED_LABEL, [])
      if not old_labels:
        ignored_objects += 1
        continue

      if label_suffix:
        child = aff4.FACTORY.Open(child.urn.Dirname(), mode="rw", token=token)
      labels = [utils.SmartStr(label) for label in old_labels]
      child.AddLabels(*labels, owner="GRR")
      child.Close(sync=False)
      updated_objects += 1

  aff4.FACTORY.Flush()


def MigrateClientsAndUsersLabels(token=None):
  """Migrates clients and users labels."""

  print "Migrating clients."
  MigrateObjectsLabels(aff4.ROOT_URN, aff4_grr.VFSGRRClient, token=token)
  print "\nMigrating users."
  MigrateObjectsLabels(
      aff4.ROOT_URN.Add("users"),
      users.GRRUser,
      label_suffix="labels",
      token=token)


def MigrateHuntFinishedAndErrors(hunt_or_urn, token=None):
  """Migrates given hunt to collection-stored clients/errors lists."""
  if hasattr(hunt_or_urn, "Schema"):
    hunt = hunt_or_urn
    if hunt.age_policy != aff4.ALL_TIMES:
      raise RuntimeError("Hunt object should have ALL_TIMES age policy.")
  else:
    hunt = aff4.FACTORY.Open(hunt_or_urn,
                             aff4_type=hunts_implementation.GRRHunt,
                             token=token,
                             age=aff4.ALL_TIMES)

  print "Migrating hunt %s." % hunt.urn

  print "Processing all clients list."
  aff4.FACTORY.Delete(hunt.all_clients_collection_urn, token=token)
  with aff4.FACTORY.Create(hunt.all_clients_collection_urn,
                           aff4_type=collects.PackedVersionedCollection,
                           mode="w",
                           token=token) as all_clients_collection:
    clients = set(hunt.GetValuesForAttribute(hunt.Schema.DEPRECATED_CLIENTS))
    for client in reversed(sorted(clients, key=lambda x: x.age)):
      all_clients_collection.Add(client)

  print "Processing completed clients list."
  aff4.FACTORY.Delete(hunt.completed_clients_collection_urn, token=token)
  with aff4.FACTORY.Create(hunt.completed_clients_collection_urn,
                           aff4_type=collects.PackedVersionedCollection,
                           mode="w",
                           token=token) as comp_clients_collection:
    clients = set(hunt.GetValuesForAttribute(hunt.Schema.DEPRECATED_FINISHED))
    for client in reversed(sorted(clients, key=lambda x: x.age)):
      comp_clients_collection.Add(client)

  print "Processing errors list."
  aff4.FACTORY.Delete(hunt.clients_errors_collection_urn, token=token)
  with aff4.FACTORY.Create(hunt.clients_errors_collection_urn,
                           aff4_type=collects.PackedVersionedCollection,
                           mode="w",
                           token=token) as errors_collection:
    for error in hunt.GetValuesForAttribute(hunt.Schema.DEPRECATED_ERRORS):
      errors_collection.Add(error)


def MigrateAllHuntsFinishedAndError(token=None):
  """Migrates all hunts to collection-stored clients/errors lists."""
  hunts_list = list(aff4.FACTORY.Open("aff4:/hunts", token=token).ListChildren(
  ))
  all_hunts = aff4.FACTORY.MultiOpen(hunts_list,
                                     aff4_type=hunts_implementation.GRRHunt,
                                     mode="r",
                                     age=aff4.ALL_TIMES,
                                     token=token)

  index = 0
  for hunt in all_hunts:
    MigrateHuntFinishedAndErrors(hunt, token=token)

    index += 1
    print ""
    print "Done %d out of %d hunts." % (index, len(hunts_list))


def ClientIdToHostname(client_id, token=None):
  """Quick helper for scripts to get a hostname from a client ID."""
  client = OpenClient(client_id, token=token)[0]
  if client and client.Get("Host"):
    return client.Get("Host").Summary()


def _GetHWInfos(client_list, batch_size=10000, token=None):
  """Opens the given clients in batches and returns hardware information."""

  # This function returns a dict mapping each client_id to a set of reported
  # hardware serial numbers reported by this client.
  hw_infos = {}

  logging.info("%d clients to process.", len(client_list))

  c = 0

  for batch in utils.Grouper(client_list, batch_size):
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

  index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                              aff4_type=client_index.ClientIndex,
                              mode="rw",
                              object_exists=True,
                              token=token)

  clients = index.LookupClients(["."])

  hw_infos = _GetHWInfos(clients, token=token)

  # We get all clients that have reported more than one hardware serial
  # number over time. This doesn't necessarily indicate a cloned client - the
  # machine might just have new hardware. We need to search for clients that
  # alternate between different IDs.
  clients_with_multiple_serials = [
      client_id for client_id, serials in hw_infos.iteritems()
      if len(serials) > 1
  ]

  client_list = aff4.FACTORY.MultiOpen(clients_with_multiple_serials,
                                       age=aff4.ALL_TIMES,
                                       token=token)

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

    for i in xrange(len(ranges) - 1):
      if ranges[i][1] > ranges[i + 1][0]:
        cloned_clients.append(c)

        msg = "Found client with multiple, overlapping serial numbers: %s"
        logging.info(msg, c.urn)
        for hwi in c.GetValuesForAttribute(c.Schema.HARDWARE_INFO):
          logging.info("%s %s", hwi.age, hwi.serial_number)
        break

  return cloned_clients
