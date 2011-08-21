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


import time

from IPython import Shell

from google.protobuf import descriptor
from grr.client import conf
from grr.client import conf as flags
import logging

from grr.lib import aff4

from grr.lib import data_store
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib.aff4_objects import aff4_grr

# Make sure we load the enroller module
from grr.lib.flows import console
from grr.lib.flows import general

from grr.proto import jobs_pb2
from grr.proto import sysinfo_pb2

flags.DEFINE_string("plugin_path", None,
                    "The top level path for grr modules")
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
          schema.INSTALL_DATE, schema.CLOCK]

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
  #TODO(user): This is pretty general really, where should it live?
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
     kwargs: passthrough to flow.

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


def TestFlows(client_id, test_list):
  """Test a bunch of flows."""
  # TODO(user): Quick hack, refactor to a real test.
  for test in test_list:
    flow_class = test[0]
    expected_state = test[1]
    args = []
    if len(test) > 2:
      args = test[2]
    f = StartFlowAndWait(client_id, flow_class, **args)
    if f.flow_pb.state != expected_state:
      logging.warn("Flow %s failed on %s. Expected %s, got %s",
                   flow_class, client_id, expected_state,
                   f.flow_pb.state)
      if f.flow_pb.state == jobs_pb2.FlowPB.ERROR:
        logging.warn(f.flow_pb.backtrace)
      return


def Help():
  """Print out help information."""
  print "Help is not implemented yet"


def main(unused_argv):
  """Main."""
  banner = ("\nWelcome to the GRR console\n"
            "Type help<enter> to get help\n\n")

  aff4.AFF4Init()

  locals_vars = {"hilfe": Help,
                 "help": Help,
                 "__name__": "GRR Console"
                }
  locals_vars.update(globals())   # add global variables to console

  Shell.IPShell(argv=[],
                user_ns=locals_vars).mainloop(banner=banner)

if __name__ == "__main__":
  conf.StartMain(main)
