#!/usr/bin/env python
"""File-type specific flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import flow
from grr_response_server import server_stubs


class PlistValueFilterArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.PlistValueFilterArgs
  rdf_deps = [
      rdf_plist.PlistRequest,
  ]


class PlistValueFilter(flow.GRRFlow):
  """Obtains values from a plist based on a context and a query filter.

  This function will parse a plist. Obtain all the values under the path given
  in context and then filter each of them against the given query and return
  only these that match. I.e:

  plist = {
    'values': [13, 14, 15]
    'items':
      [
        {'name': 'John',
         'age': 33,
         'children': ['John', 'Phil'],
         },
        {'name': 'Mike',
          'age': 24,
          'children': [],
        },
      ],
  }

  A call to PlistValueFilter with context "items" and query "age > 25" will
  return {'name': 'John', 'age': 33}.

  If you don't specify a context, the full plist will be matched and returned
  if the query succceeds. I,e: a call to PlistValueFilter without a context but
  query "values contains 13" will return the full plist.


  If you don't specify a query, all the values under the context parameter will
  get returned. I.e: a call to PlistValueFilter with context "items.children"
  and no query, will return [ ['John', 'Phil'], []].
  """

  category = "/FileTypes/"
  args_type = PlistValueFilterArgs

  def Start(self):
    """Issue a request to list the directory."""
    self.CallClient(
        server_stubs.PlistQuery,
        request=self.args.request,
        next_state="Receive")

  def Receive(self, responses):
    if not responses.success:
      self.Error("Could not retrieve value: %s" % responses.status)
    else:
      for response in responses.First():
        self.SendReply(response)
