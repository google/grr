#!/usr/bin/env python
"""AFF4 objects related to file types."""

from grr.lib import aff4
from grr.lib.aff4_objects import collects
from grr.lib.rdfvalues import plist as rdf_plist


class AFF4PlistQuery(collects.RDFValueCollection):
  """The results of a Plist flow."""

  class SchemaCls(collects.RDFValueCollection.SchemaCls):
    REQUEST = aff4.Attribute("aff4:plist/query", rdf_plist.PlistRequest,
                             "The request made to obtain this result.")
