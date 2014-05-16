#!/usr/bin/env python
"""AFF4 objects for managing Rekall responses."""
import json
import StringIO

from rekall import session
from rekall.ui import text

from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections


class RekallResponseCollection(collections.RDFValueCollection):
  """A collection of Rekall results."""
  _rdf_type = rdfvalue.RekallResponse

  def __str__(self):
    return self.RenderAsText()

  def RenderAsText(self):
    """Render the Rekall responses as Text using the standard Rekall renderer.

    This is mostly useful as a quick check of the output (e.g. in the console).

    Returns:
      Text rendered Rekall plugin output.
    """
    s = session.Session()
    plugin = s.plugins.json_render()

    fd = StringIO.StringIO()
    renderer = text.TextRenderer(session=s, fd=fd)
    with renderer.start():
      for response in self:
        for json_message in json.loads(response.json_messages):
          plugin.RenderStatement(json_message, renderer)

    return fd.getvalue()
