#!/usr/bin/env python
"""File-type specific flows."""


import time

from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.proto import flows_pb2


class PlistValueFilterArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.PlistValueFilterArgs


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

  @flow.StateHandler(next_state=["Receive"])
  def Start(self, unused_response):
    """Issue a request to list the directory."""
    output = self.args.output.format(t=time.time(), u=self.state.context.user)
    self.state.Register("output", self.client_id.Add(output))
    self.state.Register("fd", aff4.FACTORY.Create(
        self.state.output, "AFF4PlistQuery", mode="w", token=self.token))

    self.state.fd.Set(self.state.fd.SchemaCls.REQUEST, self.args.request)

    self.CallClient("PlistQuery", request=self.args.request,
                    next_state="Receive")

  @flow.StateHandler()
  def Receive(self, responses):
    if not responses.success:
      self.Error("Could not retrieve value: %s" % responses.status)
    else:
      self.state.fd.Set(self.state.fd.Schema.RESULT(responses))
      self.state.fd.Close()
