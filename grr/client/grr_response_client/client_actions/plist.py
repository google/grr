#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Client actions related to plist files."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import types


from binplist import binplist
from grr_response_client import actions
from grr_response_client import vfs
from grr_response_core.lib import plist as plist_lib
from grr_response_core.lib.rdfvalues import plist as rdf_plist
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


class PlistQuery(actions.ActionPlugin):
  """Parses the plist request specified and returns the results.

  PlistQuery allows you to obtain data from a plist, optionally only if it
  matches the given filter.

  Querying for a plist is done in two steps. First, its contents are
  retrieved.

  For plists where the top level element is a dict, you can use the key
  parameter of the PlistRequest to specify a path into the dict to retrieve.
  When specifying a key, the requested key values are places under a dictionary
  key called "key".

  Whether you've specified a key or not, the query parameter allows you to
  filter based on the
  """

  in_rdfvalue = rdf_plist.PlistRequest
  out_rdfvalues = [rdf_protodict.RDFValueArray]
  MAX_PLIST_SIZE = 1024 * 1024 * 100  # 100 MB

  def Run(self, args):
    # TODO(hanuszczak): Why are these an instance variables?
    self.context = args.context
    self.filter_query = args.query

    with vfs.VFSOpen(args.pathspec, progress_callback=self.Progress) as fd:
      data = fd.Read(self.MAX_PLIST_SIZE)
      plist = binplist.readPlist(io.BytesIO(data))

      # Create the query parser
      parser = plist_lib.PlistFilterParser(unicode(self.filter_query)).Parse()
      filter_imp = plist_lib.PlistFilterImplementation
      matcher = parser.Compile(filter_imp)

      if self.context:
        # Obtain the values for the context using the value expander
        value_expander = filter_imp.FILTERS["ValueExpander"]
        iterator = value_expander().Expand(plist, self.context)
      else:
        # If we didn't get a context, the context is the whole plist
        iterator = [plist]

      reply = rdf_protodict.RDFValueArray()
      for item in iterator:
        # As we're setting the context manually, we need to account for types
        if isinstance(item, types.ListType):
          for sub_item in item:
            partial_plist = plist_lib.PlistValueToPlainValue(sub_item)
            if matcher.Matches(partial_plist):
              reply.Append(sub_item)
        else:
          partial_plist = plist_lib.PlistValueToPlainValue(item)
          if matcher.Matches(partial_plist):
            reply.Append(partial_plist)
      self.SendReply(reply)
