#!/usr/bin/env python
"""Basic GRR rdfvalue definitions."""

from grr.lib import rdfvalue


class LabelList(rdfvalue.RDFValueArray):
  """A list of labels."""
  rdf_type = rdfvalue.RDFString
