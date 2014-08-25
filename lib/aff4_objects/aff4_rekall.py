#!/usr/bin/env python
"""AFF4 objects for managing Rekall responses."""
import json
import StringIO

from rekall import session
from rekall.ui import text

from grr.client.client_actions import grr_rekall
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collections


class RekallResponseCollection(collections.RDFValueCollection):
  """A collection of Rekall results."""
  _rdf_type = rdfvalue.RekallResponse

  renderer = "GRRRekallRenderer"

  def __str__(self):
    return self.RenderAsText()

  def RenderStatement(self, statement, renderer):
    command = statement[0]

    if command == "t":
      simple_header = [dict(name=x.get("name", x.get("cname")),
                            formatstring=x.get("formatstring"))
                       for x in statement[1]]

      renderer.table_header(columns=simple_header)
      self.column_specs = statement[1]

    elif command == "e":
      renderer.report_error(statement[1])

    elif command == "r":
      data = statement[1]
      row = []
      for column in self.column_specs:
        column_name = column.get("cname", column.get("name"))
        item = data.get(column_name)
        object_renderer = grr_rekall.GRRObjectRenderer.FromEncoded(
            item, self.renderer)(renderer=self.renderer)

        row.append(object_renderer.Summary(item))

      renderer.table_row(*row)

    elif command == "m":
      renderer.section("Plugin %s" % statement[1]["plugin_name"])

    elif command == "s":
      renderer.section(statement[1])

  def RenderAsText(self):
    """Render the Rekall responses as Text using the standard Rekall renderer.

    This is mostly useful as a quick check of the output (e.g. in the console).

    Returns:
      Text rendered Rekall plugin output.
    """
    s = session.Session()

    fd = StringIO.StringIO()
    renderer = text.TextRenderer(session=s, fd=fd)
    with renderer.start():
      for response in self:
        for json_message in json.loads(response.json_messages):
          self.RenderStatement(json_message, renderer)

    return fd.getvalue()
