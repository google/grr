#!/usr/bin/env python
"""AFF4 objects related to file types."""

from grr.lib import aff4
from grr.lib import rdfvalue


class AFF4PlistQuery(aff4.RDFValueCollection):
  """The results of a Plist flow."""

  class SchemaCls(aff4.RDFValueCollection.SchemaCls):
    REQUEST = aff4.Attribute(
        "aff4:plist/query", rdfvalue.PlistRequest,
        "The request made to obtain this result.")
