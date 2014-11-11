#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#

"""This plugin renders the results from Rekall."""


import json
import sets

from rekall.ui import json_renderer

import logging

from grr.client.client_actions import grr_rekall
from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import utils


class GRREProcessObjectRenderer(grr_rekall.GRRObjectRenderer):
  """Special rendering for _EPROCESS objects."""
  renders_type = "_EPROCESS"

  layout = renderers.Template("""

<div id="{{unique|escape}}" class="modal fade" role="dialog"
     aria-hidden="true">
  <div class="modal-dialog">
   <div class="modal-content">
    <div class="modal-header">
     <button type="button" class="close"
       aria-hidden="true" data-dismiss="modal">
      &times;
     </button>
     <h4 class="modal-title">Process {{this.Cybox.Name|escape}}</h4>
    </div>
      <div id="ClientInfoContent_{{unique|escape}}" class="modal-body">
        <table class="table table-hover">
         <tr><th>Key</th><th>Value</th></tr>
         {% for k, v in data %}
           <tr><td>{{k|escape}}</td><td>{{v|escape}}</td></tr>
         {% endfor %}
        </table>
      </div>
    </div>
  </div>
</div>

<a href=# data-toggle="modal" data-target="#{{unique|escape}}">
 {{this.Cybox.Name|escape}} ({{this.Cybox.PID|escape}})
</a>
""")

  def _Flatten(self, prefix, item):
    result = []
    for k, v in item.items():
      next_prefix = "%s.%s" % (prefix, k)

      if isinstance(v, dict):
        result.extend(self._Flatten(next_prefix, v))
      else:
        result.append((next_prefix, v))

    return result

  def RawHTML(self, item, **_):
    return self.layout.RawHTML(this=item, data=self._Flatten("", item))


class RekallTable(renderers.TemplateRenderer):
  """Renders a single Rekall Table."""

  layout_template = renderers.Template("""
  <table class="full-width">
  <thead>
  <tr>
    {% for column in this.column_specs %}
  <th class="proto_header">{{column.name|escape}}</th>
    {% endfor %}
  </tr>
  </thead>
  <tbody>
    {% for row in this.rows %}
      <tr>
    {% for value in row %}
        <td class="proto_value">
          {{value|escape}}
        </td>
    {% endfor %}
      </tr>
    {% endfor %}
  </tbody>
  </table>
""")

  def __init__(self, column_specs):
    super(RekallTable, self).__init__()
    self.column_specs = column_specs
    self.rows = []

  def AddRow(self, data):
    row = []
    for column in self.column_specs:
      column_name = column.get("cname", column.get("name"))
      item = data.get(column_name)
      object_renderer = json_renderer.JsonObjectRenderer.FromEncoded(
          item, "GRRRekallRenderer")("GRRRekallRenderer")

      row.append(object_renderer.RawHTML(item, **column))

    self.rows.append(row)


class PluginHeader(renderers.TemplateRenderer):
  """Renders metadata about plugin execution."""

  layout_template = renderers.Template("""
<h1>{{this.metadata.plugin_name|escape}}</h1>
""")

  def __init__(self, metadata, **kwargs):
    super(PluginHeader, self).__init__(**kwargs)
    self.metadata = metadata


class SectionHeader(renderers.TemplateRenderer):
  """Renders a section header."""

  layout_template = renderers.Template("""
<h3>{{this.header|escape}}</h3>
""")

  def __init__(self, header=None, name=None, width=50, keep_sort=False,
               **kwargs):
    super(SectionHeader, self).__init__(**kwargs)
    self.header = header or name or ""


class FreeFormatText(renderers.TemplateRenderer):
  """Render Free formatted text."""

  layout_template = renderers.Template("""
<pre class="proto_value">{{this.data|escape}}</pre>
""")

  def __init__(self, data, **kwargs):
    super(FreeFormatText, self).__init__(**kwargs)
    self.data = data


class RekallErrorRenderer(renderers.TemplateRenderer):
  """Render Rekall Errors."""

  layout_template = renderers.Template("""
<pre class="proto_value proto_error">{{this.data|escape}}</pre>
""")

  def __init__(self, data, **kwargs):
    super(RekallErrorRenderer, self).__init__(**kwargs)
    self.data = data


class RekallResponseCollectionRenderer(semantic.RDFValueRenderer):
  """A renderer for the RekallResponseCollection."""

  layout_template = renderers.Template("""
{% for element in this.elements %}
 {{element|safe}}
{% endfor %}
""")

  def __init__(self, *args, **kw):
    super(RekallResponseCollectionRenderer, self).__init__(*args, **kw)
    self.elements = []
    self.current_table = None
    self.free_text = []

  def _flush_table(self):
    if self.current_table:
      self.elements.append(self.current_table)

      self.current_table = None

  def _flush_freetext(self):
    if self.free_text:
      self.elements.append(FreeFormatText("".join(self.free_text)))

      self.free_text = []

  def Layout(self, request, response):
    if self.proxy:
      collection = self.proxy
    else:
      try:
        aff4_path = self.state.get("aff4_path") or request.REQ.get("aff4_path")
        collection = aff4.FACTORY.Open(
            aff4_path, aff4_type="RekallResponseCollection",
            token=request.token)
      except IOError:
        return

    output_directories = sets.Set()

    for rekall_response in collection:
      for statement in json.loads(rekall_response.json_messages):

        if len(statement) >= 1:
          object_renderer = json_renderer.JsonObjectRenderer.FromEncoded(
              statement[1], "DataExportRenderer")(renderer="DataExportRenderer")
          statement = [object_renderer.DecodeFromJsonSafe(s, {})
                       for s in statement]

        command = statement[0]

        # Metadata about currently running plugin.
        if command == "m":
          # Flush any old tables.
          self._flush_table()
          self._flush_freetext()
          self.elements.append(PluginHeader(statement[1]))

        # Start new Section.
        elif command == "s":
          self._flush_table()
          self._flush_freetext()
          self.elements.append(SectionHeader(**statement[1]))

        # Free format statement.
        elif command == "f":
          self._flush_table()
          format_string = statement[1]
          try:
            args = statement[2:]
          except IndexError:
            args = []

          self.free_text.append(format_string.format(*args))

        # Errors reported from Rekall.
        elif command == "e":
          self._flush_table()
          self._flush_freetext()
          self.elements.append(RekallErrorRenderer(statement[1]))

        # Start Table
        elif command == "t":
          self._flush_table()
          self._flush_freetext()

          # Create a new table.
          self.current_table = RekallTable(statement[1])

        # Add row to current table.
        elif command == "r":
          self._flush_freetext()
          if not self.current_table:
            logging.warn("Rekall plugin %s tried to write a "
                         "table row but no table was defined.",
                         rekall_response.plugin)
            # This is pretty bad but at least we can show the data somehow.
            self.free_text.append(utils.SmartStr(statement[1]))
            continue

          self.current_table.AddRow(statement[1])

        # File that was output by rekall and extracted.
        elif command == "file":
          # Currently, when we render a client URN the link leads the user to
          # the directory in the virtual file system, not the particular
          # file. So we just render one link for each output directory.
          file_urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
              rdfvalue.PathSpec(**statement[1]),
              rekall_response.client_urn)
          output_directories.add(rdfvalue.RDFURN(file_urn.Dirname()))

    self._flush_table()
    self._flush_freetext()
    for directory in output_directories:
      self.elements.append(semantic.RDFURNRenderer(directory))

    return super(RekallResponseCollectionRenderer, self).Layout(
        request, response)
