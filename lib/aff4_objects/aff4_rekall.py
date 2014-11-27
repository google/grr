#!/usr/bin/env python
"""AFF4 objects for managing Rekall responses."""
import StringIO

from rekall import session
from rekall.plugins.tools import json_tools
from rekall.ui import text

from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections


class RekallResponseCollection(collections.RDFValueCollection):
  """A collection of Rekall results."""
  _rdf_type = rdfvalue.RekallResponse

  renderer = "GRRRekallRenderer"

  def __str__(self):
    return self.RenderAsText()

  def RenderAsText(self):
    """Render the Rekall responses as Text using the standard Rekall renderer.

    This is mostly useful as a quick check of the output (e.g. in the console).

    Returns:
      Text rendered Rekall plugin output.
    """
    s = session.Session()

    fd_out = StringIO.StringIO()
    renderer = text.TextRenderer(session=s, fd=fd_out)

    with renderer.start():
      for response in self:
        fd_in = StringIO.StringIO()
        fd_in.write(response.json_messages)
        fd_in.seek(0)

        rekall_json_parser = json_tools.JSONParser(session=s, fd=fd_in)
        rekall_json_parser.render(renderer)
        fd_in.close()

    return fd_out.getvalue()
