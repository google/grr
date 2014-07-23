#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#

"""This plugin renders the results from Rekall."""


import json
import time

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import utils


class StructFormatter(object):
  """Formats structs."""

  def __init__(self, state):
    self.state = state

  def __int__(self):
    try:
      return self.state["offset"]
    except KeyError:
      raise ValueError("Not an int")

  def __unicode__(self):
    return unicode(int(self))

  def __str__(self):
    return self.__unicode__()


class LiteralFormatter(StructFormatter):

  def __unicode__(self):
    return utils.SmartUnicode(self.state["value"])

  def __int__(self):
    return self.state["value"]

  def __str__(self):
    return self.__unicode__()


class AddressSpaceFormatter(StructFormatter):

  def __unicode__(self):
    return self.state["name"]


class NoneObjectFormatter(StructFormatter):

  def __unicode__(self):
    return "-"

  def __int__(self):
    return 0


class DatetimeFormatter(StructFormatter):

  def __unicode__(self):
    return time.ctime(self.state["epoch"])


class RekallTable(renderers.TemplateRenderer):
  """Renders a single Rekall Table."""

  layout_template = renderers.Template("""
  <table class="full-width">
  <thead>
  <tr>
    {% for header in this.readable_headers %}
  <th class="proto_header">{{header|escape}}</th>
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

  def __init__(self, **kwargs):
    super(RekallTable, self).__init__(**kwargs)
    self.format_hints = []
    self.rows = []

  def FormatValue(self, value, hint):
    if isinstance(value, DatetimeFormatter):
      # Datetime can be displayed as unicode and int, we prefer unicode.
      return unicode(value)
    try:
      value = int(value)
      if hint == "[addrpad]":
        return utils.FormatAsHexString(value, 12)
      return utils.FormatAsHexString(value)
    except (ValueError, TypeError):
      return unicode(value)

  def SetHeaders(self, headers):
    self.format_hints = [h[2] for h in headers]
    self.readable_headers = [h[0] for h in headers]

  def AddRow(self, values):
    row = []
    for value, hint in zip(values, self.format_hints):
      row.append(self.FormatValue(value, hint))
    self.rows.append(row)


class PluginHeader(renderers.TemplateRenderer):
  """Renders metadata about plugin execution."""

  layout_template = renderers.Template("""
<h1>{{this.metadata.plugin_name}}</h1>
""")

  def __init__(self, metadata, **kwargs):
    super(PluginHeader, self).__init__(**kwargs)
    self.metadata = metadata


class SectionHeader(renderers.TemplateRenderer):
  """Renders a section header."""

  layout_template = renderers.Template("""
<h3>{{this.header}}</h3>
""")

  def __init__(self, header=None, name=None, width=50, keep_sort=False,
               **kwargs):
    super(SectionHeader, self).__init__(**kwargs)
    self.header = header or name or ""


class FreeFormatText(renderers.TemplateRenderer):
  """Render Free formatted text."""

  layout_template = renderers.Template("""
<pre class="proto_value">{{this.data}}</pre>
""")

  def __init__(self, data, **kwargs):
    super(FreeFormatText, self).__init__(**kwargs)
    self.data = data


class RekallErrorRenderer(renderers.TemplateRenderer):
  """Render Rekall Errors."""

  layout_template = renderers.Template("""
<pre class="proto_value proto_error">{{this.data}}</pre>
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

  semantic_map = dict(
      Literal=LiteralFormatter,
      String=LiteralFormatter,
      _UNICODE_STRING=LiteralFormatter,
      Struct=StructFormatter,
      NativeType=LiteralFormatter,
      Pointer=LiteralFormatter,
      AddressSpace=AddressSpaceFormatter,
      BaseAddressSpace=AddressSpaceFormatter,
      NoneObject=NoneObjectFormatter,
      DateTime=DatetimeFormatter,
      UnixTimeStamp=DatetimeFormatter,
      )

  def __init__(self, *args, **kw):
    super(RekallResponseCollectionRenderer, self).__init__(*args, **kw)
    self.elements = []
    self.current_table = None
    self.free_text = []

  def _decode_value(self, value):
    if value is None:
      return None
    elif isinstance(value, dict):
      return self._decode(value)
    elif isinstance(value, list):
      if not value:
        return []
      if value[0] == "+":
        return self.lexicon[str(value[1])].decode("base64")
      elif value[0] == "_":
        return [self._decode(x) for x in value[1:]]
      else:
        return value

    try:
      return self.lexicon[str(value)]
    except KeyError:
      raise ValueError("Lexicon corruption: Tag %s" % value)

  def _decode(self, item):
    if not isinstance(item, dict):
      return self._decode_value(item)

    state = {}
    for k, v in item.items():
      if k == "_" and v == 1:
        continue

      decoded_key = self._decode_value(k)
      decoded_value = self._decode_value(v)
      if isinstance(decoded_value, dict):
        decoded_value = self._decode(decoded_value)

      state[decoded_key] = decoded_value

    semantic_type = state.get("type")
    if semantic_type is None:
      return state

    mro = semantic_type.split(",")
    for cls in mro:
      item_renderer = self.semantic_map.get(cls)
      if item_renderer:
        return item_renderer(state)

    raise ValueError("Unsupported Semantic type %s" % semantic_type)

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

    for rekall_response in collection:
      for statement in json.loads(rekall_response.json_messages):
        command = statement[0]
        # Reset Lexicon.
        if command == "l":
          self.lexicon = statement[1]

        # Metadata about currently running plugin.
        elif command == "m":
          # Flush any old tables.
          self._flush_table()
          self._flush_freetext()
          self.elements.append(PluginHeader(statement[1]))

        # Start new Section.
        elif command == "s":
          self._flush_table()
          self._flush_freetext()
          self.elements.append(SectionHeader(**self._decode(statement[1])))

        # Free format statement.
        elif command == "f":
          self._flush_table()
          args = [self._decode(x) for x in statement[1:]]
          format_string = args[0]
          try:
            args = args[1:]
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
          self.current_table = RekallTable()
          self.current_table.SetHeaders(statement[1]["columns"])

        # Add row to current table.
        elif command == "r":
          self._flush_freetext()
          values = [self._decode(x) for x in statement[1]]
          self.current_table.AddRow(values)

    self._flush_table()
    self._flush_freetext()

    return super(RekallResponseCollectionRenderer, self).Layout(
        request, response)
