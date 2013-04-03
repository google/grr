#!/usr/bin/env python
"""This is the GRR Console.

We can schedule a new flow for a specific client.
"""


# pylint: disable=W0611
# Import things that are useful from the console.
import collections
import csv
import datetime
import getpass
import os
import re
import sys
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

from grr.client import conf
from grr.client import conf as flags
import logging

from grr import artifacts
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import artifact

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import flow_utils
from grr.lib import hunts
from grr.lib import ipshell
from grr.lib import maintenance_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import type_info

from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import reports

from grr.lib.flows import console
from grr.lib.flows.general import memory
# pylint: enable=unused-import,g-bad-import-order


flags.DEFINE_string("client", None,
                    "Initialise the console with this client id "
                    "(e.g. C.1234345).")


def FormatISOTime(t):
  """Format a time in epoch notation to ISO UTC."""
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t / 1e6))


# globals that can be used in the shell
CWD = "/"


def FindClient(query_str, token=None, limit=1000):
  """Search indexes for clients. Returns list (client, hostname, os version)."""
  client_schema = aff4.AFF4Object.classes["VFSGRRClient"].SchemaCls
  index_urn = client_schema.client_index
  index = aff4.FACTORY.Create(index_urn, "AFF4Index", mode="r", token=token)
  result_set = index.Query(
      [client_schema.HOSTNAME, client_schema.USERNAMES],
      query_str.lower(), limit=(0, limit))
  results = []
  for result in result_set:
    results.append((result,
                    str(result.Get(client_schema.HOSTNAME)),
                    str(result.Get(client_schema.OS_VERSION)),
                   ))
  return results


def SearchClient(hostname_regex=None, os_regex=None, mac_regex=None, limit=100):
  """Search for clients and return as a list of dicts."""
  schema = aff4_grr.VFSGRRClient.SchemaCls
  filters = [
      data_store.DB.filter.HasPredicateFilter(schema.HOSTNAME),
      data_store.DB.filter.SubjectContainsFilter("aff4:/C.[^/]+")
  ]
  if hostname_regex:
    filters.append(data_store.DB.filter.PredicateContainsFilter(
        schema.HOSTNAME, hostname_regex))
  if os_regex:
    filters.append(data_store.DB.filter.PredicateContainsFilter(
        schema.UNAME, os_regex))
  if mac_regex:
    filters.append(data_store.DB.filter.PredicateContainsFilter(
        schema.MAC_ADDRES, mac_regex))
  cols = [schema.HOSTNAME, schema.UNAME, schema.MAC_ADDRESS,
          schema.INSTALL_DATE, schema.PING]

  results = {}
  for row in data_store.DB.Query(cols,
                                 data_store.DB.filter.AndFilter(*filters),
                                 limit=(0, limit),
                                 subject_prefix="aff4:/"):
    c_id = row["subject"][0][0]
    results[c_id] = {}
    for k, v in row.items():
      if k.startswith("metadata:"):
        results[c_id][k] = v[0]
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
    logging.info("Downloading %s to %s", child.urn, outfile)
    with open(outfile, "wb") as out_fd:
      try:
        buf = child.Read(bufsize)
        while buf:
          out_fd.write(buf)
          buf = child.Read(bufsize)
      except IOError as e:
        logging.error("Failed to read %s. Err: %s", child.urn, e)


def StartFlowAndWait(client_id, flow_name, **kwargs):
  """Launches the flow and waits for it to complete.

  Args:
     client_id: The client common name we issue the request.
     flow_name: The name of the flow to launch.
     **kwargs: passthrough to flow.

  Returns:
     A GRRFlow object.
  """
  session_id = flow.FACTORY.StartFlow(client_id, flow_name, **kwargs)
  while 1:
    time.sleep(1)
    rdf_flow = flow.FACTORY.FetchFlow(session_id, lock=False)
    if rdf_flow.state != rdfvalue.Flow.Enum("RUNNING"):
      break

  return flow.FACTORY.LoadFlow(rdf_flow)


def StartFlowAndWorker(client_id, flow_name, **kwargs):
  """Launches the flow and worker and waits for it to finish.

  Args:
     client_id: The client common name we issue the request.
     flow_name: The name of the flow to launch.
     **kwargs: passthrough to flow.

  Returns:
     A GRRFlow object.

  Note: you need raw access to run this flow as it requires running a worker.
  """
  queue = "DEBUG-%s-" % getpass.getuser()
  session_id = flow.FACTORY.StartFlow(client_id, flow_name, queue_name=queue,
                                      **kwargs)
  # Empty token, only works with raw access.
  worker_thrd = flow.GRRWorker(
      queue_name=queue, token=access_control.ACLToken(), threadpool_size=1)
  while True:
    try:
      worker_thrd.RunOnce()
    except KeyboardInterrupt:
      print "exiting"
      worker_thrd.thread_pool.Join()
    time.sleep(2)
    rdf_flow = flow.FACTORY.FetchFlow(session_id, lock=False)
    if rdf_flow.state != rdfvalue.Flow.Enum("RUNNING"):
      break

  # Terminate the worker threads
  worker_thrd.thread_pool.Stop()
  worker_thrd.thread_pool.Join()
  return flow.FACTORY.LoadFlow(rdf_flow)


def GetNotifications(user=None, token=None):
  """Show pending notifications for a user."""
  if not user:
    user = getpass.getuser()
  user_obj = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(user),
                               token=token)
  return list(user_obj.Get(user_obj.Schema.PENDING_NOTIFICATIONS))


def ApprovalRequest(client_id, reason, approvers, token=None):
  """Request approval to access a host."""
  return flow.FACTORY.StartFlow(client_id, "RequestClientApprovalFlow",
                                reason=reason, approver=approvers, token=token)


def ApprovalGrant(token=None):
  """Iterate through requested access approving or not."""
  user = getpass.getuser()
  notifications = GetNotifications(user=user, token=token)
  requests = [n for n in notifications if n.type == "GrantAccess"]
  for request in requests:
    _, client_id, user, reason = aff4.RDFURN(request.subject).Split()
    reason = utils.DecodeReasonString(reason)
    print request
    print "Reason: %s" % reason
    if raw_input("Do you approve this request? [y/N] ").lower() == "y":
      flow_id = flow.FACTORY.StartFlow(client_id, "GrantClientApprovalFlow",
                                       reason=reason, delegate=user,
                                       token=token)
      # TODO(user): Remove the notification.
    else:
      print "skipping request"
    print "Approval sent: %s" % flow_id


def ApprovalFind(object_id, token=None):
  """Find approvals issued for a specific client."""
  user = getpass.getuser()
  object_id = aff4.RDFURN(object_id)
  try:
    approved_token = aff4.Approval.GetApprovalForObject(
        object_id, token=token, username=user)
    print "Found token %s" % str(approved_token)
    return approved_token
  except access_control.UnauthorizedAccess:
    print "No token available for access to %s" % object_id


def TestFlows(client_id, platform, testname=None):
  """Test a bunch of flows."""

  if platform not in ["windows", "linux", "darwin"]:
    raise RuntimeError("Requested operating system not supported.")

  # This token is not really used since there is no approval for the
  # tested client - these tests are designed for raw access - but we send it
  # anyways to have an access reason.
  token = access_control.ACLToken("test", "client testing")

  console.client_tests.RunTests(client_id, platform=platform,
                                testname=testname, token=token)


def ApprovalCreateRaw(client_id, token, approval_type="ClientApproval"):
  """Creates an approval for a given token.

  This method doesn't work through the Gatekeeper for obvious reasons. To use
  it, the console has to use raw datastore access.

  Args:
    client_id: The client id the approval should be created for.
    token: The token that will be used later for access.
    approval_type: The type of the approval to create.

  Raises:
    RuntimeError: On bad token.
  """
  if not token.reason:
    raise RuntimeError("Cannot create approval with empty reason")
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = access_control.ACLToken()
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Create(approval_urn, approval_type,
                                         mode="rw", token=super_token)

  # Add approvals indicating they were approved by fake "raw" mode users.
  user = getpass.getuser()
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s1-raw" % user))
  approval_request.AddAttribute(
      approval_request.Schema.APPROVER("%s-raw2" % user))
  approval_request.Close()


def ApprovalRevokeRaw(client_id, token, remove_from_cache=False):
  """Revokes an approval for a given token.

  This method doesn't work through the Gatekeeper for obvious reasons. To use
  it, the console has to use raw datastore access.

  Args:
    client_id: The client id the approval should be revoked for.
    token: The token that should be revoked.
    remove_from_cache: If True, also remove the approval from the
                       security_manager cache.
  """
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = access_control.ACLToken()
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Open(approval_urn, mode="rw",
                                       token=super_token)
  approval_request.DeleteAttribute(approval_request.Schema.APPROVER)
  approval_request.Close()

  if remove_from_cache:
    data_store.DB.security_manager.acl_cache.ExpireObject(
        utils.SmartUnicode(approval_urn))


def Help():
  """Print out help information."""
  print "Help is not implemented yet"


def OpenClient(client_id=None):
  """Opens the client, getting potential approval tokens.

  Args:
    client_id: The client id the approval should be revoked for.

  Returns:
    tuple containing (client, token) objects or (None, None) on if
    no appropriate aproval tokens were found.
  """
  token = access_control.ACLToken()
  try:
    token = ApprovalFind(client_id, token=token)
  except access_control.UnauthorizedAccess as e:
    logging.warn("No authorization found for access to client: %s", e)

  try:
    # Try and open with the token we managed to retrieve or the default.
    client = aff4.FACTORY.Open(aff4.RDFURN(client_id), mode="r", token=token)
    return client, token
  except access_control.UnauthorizedAccess:
    logging.warning("Unable to find a valid reason for client %s. You may need "
                    "to request approval.", client_id)
    return None, None


def SetLabels(urn, labels, token=None):
  """Set the labels on an object."""
  fd = aff4.FACTORY.Open(urn, mode="rw", token=token)
  current_labels = fd.Get(fd.Schema.LABEL, fd.Schema.LABEL())
  for l in labels:
    current_labels.Append(l)
  fd.Set(current_labels)
  fd.Close()


def ListDrivers():
  urn = aff4.ROOT_URN.Add(memory.DRIVER_BASE)
  token = access_control.ACLToken()
  fd = aff4.FACTORY.Open(urn, mode="r", token=token)

  return list(fd.Query())


def Lister(arg):
  for x in arg:
    print x


def main(unused_argv):
  """Main."""
  banner = ("\nWelcome to the GRR console\n"
            "Type help<enter> to get help\n\n")

  registry.Init()

  locals_vars = {"hilfe": Help,
                 "help": Help,
                 "__name__": "GRR Console",
                 "l": Lister,
                }
  locals_vars.update(globals())   # add global variables to console
  if flags.FLAGS.client is not None:
    locals_vars["client"], locals_vars["token"] = OpenClient(
        client_id=flags.FLAGS.client)

  ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)


def ConsoleMain():
  """Helper function for calling with setup tools entry points."""
  conf.StartMain(main)


if __name__ == "__main__":
  ConsoleMain()
