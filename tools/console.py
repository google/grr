#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This is the GRR Console.

We can schedule a new flow for a specific client.
"""


# Import things that are useful from the console.
import collections
import csv
import os
import sys
import time



from google.protobuf import descriptor
from grr.client import conf
from grr.client import conf as flags
import logging

from grr import artifacts
from grr.lib import aff4
from grr.lib import artifact

from grr.lib import data_store
from grr.lib import fake_data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import ipshell
from grr.lib import maintenance_utils
from grr.lib import registry
from grr.lib import type_info

from grr.lib import mongo_data_store
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import reports

# Make sure we load the enroller module
from grr.lib.flows import console
from grr.lib.flows import general
from grr.lib.flows.general import memory

from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2

flags.DEFINE_string("client", None,
                    "Initialise the console with this client id "
                    "(e.g. C.1234345).")
FLAGS = flags.FLAGS


def FormatISOTime(t):
  """Format a time in epoch notation to ISO UTC."""
  return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t / 1e6))


# globals that can be used in the shell
CWD = "/"


def SearchClient(hostname_regex=None, os_regex=None, mac_regex=None, limit=100):
  """Search for clients and return as a list of dicts."""
  schema = aff4_grr.VFSGRRClient.Schema
  filters = [
      data_store.DB.Filter.HasPredicateFilter(schema.HOSTNAME),
      data_store.DB.Filter.SubjectContainsFilter("aff4:/C.[^/]+")
  ]
  if hostname_regex:
    filters.append(data_store.DB.Filter.PredicateContainsFilter(
        schema.HOSTNAME, hostname_regex))
  if os_regex:
    filters.append(data_store.DB.Filter.PredicateContainsFilter(
        schema.UNAME, os_regex))
  if mac_regex:
    filters.append(data_store.DB.Filter.PredicateContainsFilter(
        schema.MAC_ADDRES, mac_regex))
  cols = [schema.HOSTNAME, schema.UNAME, schema.MAC_ADDRESS,
          schema.INSTALL_DATE, schema.PING]

  results = {}
  for row in data_store.DB.Query(cols,
                                 data_store.DB.Filter.AndFilter(*filters),
                                 limit=(0, limit),
                                 subject_prefix="aff4:/"):
    c_id = row["subject"][0]
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


def GetFlows(client_id, limit=100):
  """Retrieve flows for a given client_id, return dict of dicts."""
  client = aff4.FACTORY.Open(client_id)
  results = {}
  for flow_obj in client.GetFlows(0, limit):
    flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB).data
    pb_dict = FlowPBToDict(flow_pb)
    results[pb_dict["session_id"]] = pb_dict

  return results


def FlowPBToDict(flow_pb, skip_attrs="pickle"):
  """Take a flow protobuf and return a formatted dict."""
  # TODO(user): This is pretty general really, where should it live?
  attrs = {}
  for f, v in flow_pb.ListFields():
    if f.name not in skip_attrs.split(","):
      if f.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
        attrs[f.name] = f.enum_type.values_by_number[v].name
      elif f.name.endswith("time"):
        attrs[f.name] = FormatISOTime(v)
      else:
        attrs[f.name] = v
  return attrs


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
    flow_pb = flow.FACTORY.FetchFlow(session_id, lock=False)
    if flow_pb.state != jobs_pb2.FlowPB.RUNNING:
      break

  return flow.FACTORY.LoadFlow(flow_pb)


def TestFlows(client_id, platform, testname=None):
  """Test a bunch of flows."""

  if platform not in ["windows", "linux", "darwin"]:
    raise RuntimeError("Requested operating system not supported.")

  # This token is not really used since there is no approval for the
  # tested client - these tests are designed for raw access - but we send it
  # anyways to have an access reason.
  token = data_store.ACLToken("test", "client testing")

  console.client_tests.RunTests(client_id, platform=platform,
                                testname=testname, token=token)


def CreateApproval(client_id, token):
  """Creates an approval for a given token.

  This method doesn't work through the Gatekeeper for obvious reasons. To use
  it, the console has to use raw datastore access.

  Args:
    client_id: The client id the approval should be created for.
    token: The token that will be used later for access.
  """
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
      token.username).Add(utils.EncodeReasonString(token.reason))

  super_token = data_store.ACLToken()
  super_token.supervisor = True

  approval_request = aff4.FACTORY.Create(approval_urn, "Approval", mode="rw",
                                         token=super_token)
  approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver1"))
  approval_request.AddAttribute(approval_request.Schema.APPROVER("Approver2"))
  approval_request.Close()


def RevokeApproval(client_id, token, remove_from_cache=False):
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

  super_token = data_store.ACLToken()
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
  username = os.getlogin()
  # Use an empty token to query the ACL system.
  token = data_store.ACLToken()

  # Now we try to find any reason which will allow the user to access this
  # client right now.
  approval_urn = aff4.ROOT_URN.Add("ACL").Add(client_id).Add(
      username)

  fd = aff4.FACTORY.Open(approval_urn, mode="r", token=token)
  for auth_request in fd.OpenChildren():
    reason = utils.DecodeReasonString(auth_request.urn.Basename())

    # Check authorization using the data_store for an authoritative source.
    token = data_store.default_token = data_store.ACLToken(username, reason)
    try:
      aff4.FACTORY.Open(aff4.RDFURN(client_id).Add("ACL_Check"),
                        mode="r", token=token)
      logging.info("Found valid approval '%s' for client %s", reason, client_id)

      # Make sure to have a client object here to return to the console
      # the client object will be set in the IPython user_ns
      client = aff4.FACTORY.Open(aff4.RDFURN(client_id), mode="r", token=token)

      return client, token
    except data_store.UnauthorizedAccess:
      pass

  logging.warning("Unable to find a valid reason for client %s. You may need "
                  "to request approval.", client_id)

  return None, None


def ListDrivers():
  urn = aff4.ROOT_URN.Add(memory.DRIVER_BASE)
  token = data_store.ACLToken()
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

  if FLAGS.verbose:
    logging.root.setLevel(logging.INFO)  # Allow for logging.

  locals_vars = {"hilfe": Help,
                 "help": Help,
                 "__name__": "GRR Console",
                 "l": Lister,
                }
  locals_vars.update(globals())   # add global variables to console
  if FLAGS.client is not None:
    locals_vars["client"], locals_vars["token"] = OpenClient(FLAGS.client)

  ipshell.IPShell(argv=[], user_ns=locals_vars, banner=banner)

if __name__ == "__main__":
  conf.StartMain(main)
