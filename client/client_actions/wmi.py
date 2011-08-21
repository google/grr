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

"""Actions that relate to the Windows WMI interface."""


import pythoncom
import win32com.client

from grr.client import actions
from grr.lib import utils
from grr.proto import jobs_pb2


# Properties to remove from results sent to the server.
# These properties are included with nearly every WMI object and use space.
IGNORE_PROPS = ["CSCreationClassName", "CreationClassName", "OSName",
                "OSCreationClassName", "WindowsVersion", "CSName"]


class WmiQuery(actions.ActionPlugin):
  """Runs a WMI query and returns the results to a server callback."""
  in_protobuf = jobs_pb2.WmiRequest
  out_protobuf = jobs_pb2.Dict

  def Run(self, args):
    """Run the WMI query and return the data."""
    query = args.query

    # Now return the data to the server
    for response_dict in RunWMIQuery(query):
      response = utils.ProtoDict(response_dict)
      self.SendReply(response.ToProto())


def RunWMIQuery(query, baseobj=r"winmgmts:\root\cimv2"):
  """Run a WMI query and return a result.

  Args:
    query: the WMI query to run.
    baseobj: the base object for the WMI query.

  Yields:
    A dict containing a list of key value pairs.
  """
  pythoncom.CoInitialize()   # Needs to be called if using com from a thread.
  wmi_obj = win32com.client.GetObject(baseobj)
  # This allows our WMI to do some extra things, in particular
  # it gives it access to find the executable path for all processes.
  wmi_obj.Security_.Privileges.AddAsString("SeDebugPrivilege")

  # Run query
  try:
    query_results = wmi_obj.ExecQuery(query)
  except pythoncom.com_error, e:
    raise RuntimeError("Failed to run WMI query \'%s\' err was %s" %
                       (query, e))

  # Extract results
  try:
    for result in query_results:
      response = {}
      for prop in result.Properties_:
        if prop.Name not in IGNORE_PROPS:
          if prop.Value is None:
            response[prop.Name] = u""
          else:
            # Values returned by WMI
            # We always want to return unicode strings.
            if isinstance(prop.Value, unicode):
              response[prop.Name] = prop.Value
            elif isinstance(prop.Value, str):
              response[prop.Name] = prop.Value.decode("utf8")
            else:
              # Int or other, convert it to a unicode string
              response[prop.Name] = unicode(prop.Value)

      yield response

  except pythoncom.com_error, e:
    raise RuntimeError("WMI query data error on query \'%s\' err was %s" %
                       (e, query))
