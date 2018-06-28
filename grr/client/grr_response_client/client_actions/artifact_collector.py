#!/usr/bin/env python
"""The client artifact collector."""

from grr_response_client import actions
from grr.lib.rdfvalues import artifacts as rdf_artifacts


class ArtifactCollector(actions.ActionPlugin):
  """The client side artifact collector"""

  in_rdfvalue = rdf_artifacts.ArtifactCollectorArgs
  out_rdfvalue = [rdf_artifacts.ArtifactCollectorResult]

  def Run(self, args):
    return
