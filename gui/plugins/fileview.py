#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""This plugin renders the filesystem in a tree and a table."""

import cgi
import os
import random
import socket

from django import http
from M2Crypto import X509

from grr.gui import renderers
from grr.gui.plugins import fileview_widgets
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import utils
from grr.proto import sysinfo_pb2


# pylint: disable=g-bad-name
class BufferReferenceRenderer(renderers.RDFProtoRenderer):
  """Render the buffer reference."""
  classname = "BufferReference"
  name = "Buffer Reference"

  def Hexify(self, _, data):
    """Render a hexdump of the data."""
    results = []
    idx = 0
    while idx < len(data):
      raw = ""
      result = ""
      for _ in range(16):
        ord_value = ord(data[idx])
        result += "%02X " % ord_value
        if ord_value > 32 and ord_value < 127:
          raw += cgi.escape(data[idx])
        else:
          raw += "."

        idx += 1

        if idx >= len(data):
          break

      results.append(result + " " * (16 * 3 - len(result)) + raw)

    return "<pre>%s</pre>" % "\n".join(results)

  translator = dict(data=Hexify)


class StatEntryRenderer(renderers.RDFProtoRenderer):
  """Nicely format the StatEntry rdfvalue."""
  classname = "StatEntry"
  name = "Stat Entry"

  def TranslateRegistryData(self, _, registry_data):
    if registry_data.HasField("data"):
      ret = repr(registry_data.GetValue())
    else:
      ret = utils.SmartStr(registry_data.GetValue())

    # This is not escaped by the template!
    return renderers.EscapingRenderer(ret).RawHTML()

  translator = dict(registry_data=TranslateRegistryData,
                    registry_type=renderers.RDFProtoRenderer.Enum)


class TaskRenderer(renderers.RDFProtoRenderer):
  """Nicely format the deprecated Task rdfvalue."""
  classname = "Task"
  name = "Task"

  def RenderPayload(self, _, value):
    rdf_flow = rdfvalue.Flow(value)
    return renderers.FindRendererForObject(rdf_flow).RawHTML()

  translator = dict(value=RenderPayload)


class GrrMessageRenderer(renderers.RDFProtoRenderer):
  """Nicely format the GrrMessage rdfvalue."""
  classname = "GrrMessage"
  name = "GrrMessage"

  def RenderPayload(self, _, unused_value):
    rdf_object = self.proxy.payload
    return renderers.FindRendererForObject(rdf_object).RawHTML()

  translator = dict(args=RenderPayload)


class CollectionRenderer(StatEntryRenderer):
  """Nicely format a Collection."""
  classname = "CollectionList"
  name = "Collection Listing"

  layout_template = renderers.Template("""
<table class='proto_table'>
<thead>
<tr><th>Mode</th><th>Name</th><th>Size</th><th>Modified</th></tr>
</thead>
<tbody>
  {% for row in this.result %}
    <tr>
    {% for value in row %}
      <td class="proto_value">
        {{value|safe}}
      </td>
    {% endfor %}
    </tr>
  {% endfor %}
</tbody>
</table>
""")

  def Layout(self, request, response):
    """Render collections as a table."""
    self.result = []
    fields = "st_mode pathspec st_size st_mtime".split()
    items = self.proxy.items
    for item in items:
      row = []
      for name in fields:
        value = getattr(item, name)
        try:
          value = self.translator[name](self, None, value)

        # Regardless of what the error is, we need to escape the value.
        except StandardError:  # pylint: disable=broad-except
          value = self.FormatFromTemplate(self.translator_error_template,
                                          value=value)

        row.append(value)

      self.result.append(row)

    return renderers.TemplateRenderer.Layout(self, request, response)


class GrepResultRenderer(renderers.RDFProtoRenderer):
  """Nicely format grep results."""
  classname = "GrepResultList"
  name = "Grep Result Listing"

  layout_template = renderers.Template("""
<table class='proto_table'>
<thead>
<tr><th>Offset</th><th>Data</th></tr>
</thead>
<tbody>
  {% for row in this.results %}
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

  def Layout(self, request, response):
    self.results = []
    for row in self.proxy:
      self.results.append([row.offset, repr(row)])

    return renderers.TemplateRenderer.Layout(self, request, response)


class VolatilityFormatstringRenderer(renderers.RDFProtoRenderer):
  """Formats a volatility result string."""

  layout_template = renderers.Template("""
{% for line in this.lines %}
  {{line|safe}}
{% endfor %}
""")

  def GenerateLine(self, formatted_value):
    format_string = formatted_value.formatstring.replace("\n", "<br>")
    return format_string.format(*formatted_value.data.values)

  def Layout(self, request, response):
    """Prepare the data."""
    self.lines = []
    for formatted_value in self.proxy.formatted_values:
      self.lines.append(self.GenerateLine(formatted_value))
    return renderers.TemplateRenderer.Layout(self, request, response)


class VolatilityTableRenderer(renderers.RDFProtoRenderer):
  """Formats a volatility result table."""

  layout_template = renderers.Template("""
<table class="full-width">
<thead>
<tr>
  {% for header in this.headers %}
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

  def GenerateField(self, table, idx, field):
    if table.headers[idx].format_hint == "[addrpad]":
      return utils.FormatAsHexString(field, 12)
    try:
      int(field)
      return utils.FormatAsHexString(field)
    except ValueError:
      return field

  def GenerateRows(self, volatility_table):
    self.headers = [header.print_name for header in volatility_table.headers]
    self.rows = []
    for row in volatility_table.rows:
      this_row = []
      idx = 0
      for value in row.values:
        this_value = ""
        for field in ["svalue", "value"]:
          try:
            if value.HasField(field):
              this_value = self.GenerateField(volatility_table, idx,
                                              getattr(value, field))
              break
          except TypeError:
            pass
        this_row.append(this_value)
        idx += 1
      self.rows.append(this_row)

  def Layout(self, request, response):
    """Prepare the data."""
    self.GenerateRows(self.proxy)
    return renderers.TemplateRenderer.Layout(self, request, response)


class GenericVolatilityResultRenderer(renderers.RDFProtoRenderer):
  """Nicely format results of volatility plugins."""
  name = "Volatility Result Listing"

  layout_template = renderers.Template("""
{% for section in this.section_html %}
  {{section|safe}}
<hr>
{% endfor %}

{% if this.proxy.error %}
Error:
{{this.proxy.error|escape}}
{% endif %}
""")

  def Layout(self, request, response):
    """Layout."""
    self.section_html = []
    for section in self.proxy.sections:
      if section.HasField("table"):
        self.section_html.append(
            VolatilityTableRenderer(section.table).RawHTML())
      else:
        self.section_html.append(
            VolatilityFormatstringRenderer(
                section.formatted_value_list).RawHTML())
    return renderers.TemplateRenderer.Layout(self, request, response)


class MutantscanResultRenderer(VolatilityTableRenderer):
  """Nicely format results of the Mutexes flow."""
  name = "Mutexes Result Listing"

  layout_template = renderers.Template("""
Names:<br>
<br>
<table style="width:100%">
<tbody>
  {% for name in this.names %}
<tr>
<td class="proto_value">
{{name|escape}}
</td>
</tr>
  {% endfor %}
</tbody>
</table>
<br>
Details:<br>
<br>
{{this.details|safe}}
""")

  def Layout(self, request, response):
    """Prepare the data."""
    table = self.proxy.sections[0].table
    self.GenerateRows(table)
    self.names = sorted(set([values[-1] for values in self.rows if values[-1]]))
    self.details = VolatilityTableRenderer(table).RawHTML()
    return renderers.TemplateRenderer.Layout(self, request, response)


class VolatilityResultRenderer(renderers.RDFProtoRenderer):
  """Nicely format results of volatility plugins."""
  classname = "VolatilityResult"

  subrenderers = {
      "mutantscan": MutantscanResultRenderer,
      }

  def Layout(self, request, response):
    """Produces a layout as returned by the subrenderer."""

    # This is the standard renderer for now.
    plugin = self.proxy.plugin
    subrenderer = self.subrenderers.get(plugin, GenericVolatilityResultRenderer)

    self.layout_template = subrenderer.layout_template
    subrenderer(self.proxy).Layout(request, response)
    return super(VolatilityResultRenderer, self).Layout(request, response)


class UsersRenderer(renderers.RDFValueArrayRenderer):
  classname = "Users"
  name = "Users"


class NetworkAddressRenderer(renderers.RDFValueRenderer):
  classname = "NetworkAddress"
  name = "Network Address"
  layout_template = renderers.Template("{{result|escape}}")

  def Layout(self, request, response):
    _ = request, response
    return self.RenderFromTemplate(self.layout_template, response,
                                   result=self.proxy.HumanReadableAddress())


class InterfaceRenderer(renderers.RDFProtoRenderer):
  """Render a machine's interfaces."""
  classname = "Interface"
  name = "Interface Record"

  def TranslateIp4Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET, x) for x in value])

  def TranslateMacAddress(self, _, value):
    return ":".join([x.encode("hex") for x in value])

  def TranslateIp6Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET6, x) for x in value])

  translator = dict(ip4_addresses=TranslateIp4Addresses,
                    ip6_addresses=TranslateIp6Addresses,
                    mac_address=TranslateMacAddress)


class ConfigRenderer(renderers.RDFProtoRenderer):
  classname = "GRRConfig"
  name = "GRR Configuration"

  translator = {}


class StringListRenderer(renderers.TemplateRenderer):
  """Renders a list of strings as a proto table."""
  layout_template = renderers.Template("""
<table class='proto_table'>
<tbody>
{% for string in this.strings %}
<tr><td>
{{string|escape}}
</td></tr>
{% endfor %}
</tbody>
</table>
""")

  def __init__(self, strings, **kwargs):
    self.strings = strings
    super(StringListRenderer, self).__init__(**kwargs)


class ConnectionRenderer(renderers.RDFValueArrayRenderer):
  """Renders connection listings."""
  classname = "Connections"
  name = "Connection Listing"

  # The contents of result are safe since they were already escaped in
  # connection_template.
  layout_template = renderers.Template("""
<table class='proto_table'>
<tbody>
{% for connection in result %}
<tr>
{{connection|safe}}
</tr>
{% endfor %}
</tbody>
</table>
""")

  connection_template = renderers.Template(
      """
<td>{{type|escape}}</td>
<td>{{local_address|escape}}</td>
<td>{{remote_address|escape}}</td>
<td>{{state|escape}}</td>
""")

  types = {
      (2, 1): "tcp",
      (10, 1): "tcp6",
      (23, 1): "tcp6",
      (30, 1): "tcp6",
      (2, 2): "udp",
      (10, 2): "udp6",
      (23, 2): "udp6",
      (30, 2): "udp6",
      }

  states = {
      sysinfo_pb2.NetworkConnection.UNKNOWN: "UNKNOWN",
      sysinfo_pb2.NetworkConnection.LISTEN: "LISTEN",
      sysinfo_pb2.NetworkConnection.ESTAB: "ESTABLISHED",
      sysinfo_pb2.NetworkConnection.TIME_WAIT: "TIME_WAIT",
      sysinfo_pb2.NetworkConnection.CLOSE_WAIT: "CLOSE_WAIT",
      }

  def Layout(self, request, response):
    """Render the connection as a table."""

    _ = request

    result = []

    for conn in self.proxy:
      try:
        conn_type = self.types[(conn.family, conn.type)]
      except KeyError:
        conn_type = "(%d,%d)" % (conn.family, conn.type)
      local_address = "%s:%d" % (conn.local_address.ip,
                                 conn.local_address.port)
      if conn.remote_address.ip:
        remote_address = "%s:%d" % (conn.remote_address.ip,
                                    conn.remote_address.port)
      else:
        if ":" in conn.local_address.ip:
          remote_address = ":::*"
        else:
          remote_address = "0.0.0.0:*"

      state = self.states[conn.state]

      result.append(self.FormatFromTemplate(self.connection_template,
                                            type=conn_type,
                                            local_address=local_address,
                                            remote_address=remote_address,
                                            state=state))

    return self.RenderFromTemplate(self.layout_template, response,
                                   result=sorted(result))


class ProcessRenderer(renderers.RDFValueArrayRenderer):
  """Renders process listings."""
  classname = "Processes"
  name = "Process Listing"

  def RenderConnections(self, unused_descriptor, connection_list):
    return ConnectionRenderer(connection_list).RawHTML()

  def RenderFiles(self, unused_descriptor, file_list):
    return StringListRenderer(sorted(file_list)).RawHTML()

  translator = dict(ctime=renderers.RDFProtoRenderer.Time,
                    connections=RenderConnections,
                    open_files=RenderFiles)


class FilesystemRenderer(renderers.RDFValueArrayRenderer):
  classname = "FileSystem"
  name = "FileSystems"


class CertificateRenderer(renderers.RDFValueRenderer):
  """Render X509 Certs properly."""
  classname = "RDFX509Cert"
  name = "X509 Certificate"

  # Implement hide/show behaviour for certificates as they tend to be long and
  # uninteresting.
  layout_template = renderers.Template("""
<div class='certificate_viewer' id='certificate_viewer_{{unique|escape}}'>
  <ins class='fg-button ui-icon ui-icon-minus'/>
  Click to show details.
  <div class='contents'>
    <pre>
      {{ this.cert|escape }}
    </pre>
  </div>
</div>

<script>
$('#certificate_viewer_{{unique|escape}}').click(function () {
  $(this).find('ins').toggleClass('ui-icon-plus ui-icon-minus');
  $(this).find('.contents').toggle();
}).click();
</script>
""")

  def Layout(self, request, response):
    # Present the certificate as text
    self.cert = X509.load_cert_string(str(self.proxy)).as_text()

    return super(CertificateRenderer, self).Layout(request, response)


class BlobArrayRenderer(renderers.RDFValueRenderer):
  """Render a blob array."""
  classname = "BlobArray"
  name = "Array"

  layout_template = renderers.Template("""
{% for i in first %}
{{i|escape}}
{% endfor %}
{% for i in array %}
, {{i|escape}}
{% endfor %}
""")

  def Layout(self, _, response):
    array = []
    for i in self.proxy:
      for field in ["integer", "string", "data", "boolean"]:
        if i.HasField(field):
          array.append(getattr(i, field))
          break

    return self.RenderFromTemplate(self.layout_template, response,
                                   first=array[0:1], array=array[1:])


class AgeSelector(renderers.RDFValueRenderer):
  """Allows the user to select a different version for viewing objects."""
  layout_template = renderers.Template("""
<img src=static/images/window-duplicate.png class='grr-icon version-selector'>
<span age='{{this.int}}'><nobr>{{this.proxy|escape}}</nobr></span>
""")

  def Layout(self, request, response):
    self.int = int(self.proxy or 0)
    return super(AgeSelector, self).Layout(request, response)


class AgeRenderer(AgeSelector):
  classname = "RDFDatetime"

  layout_template = renderers.Template("""
<span age='{{this.int}}'><nobr>{{this.proxy|escape}}</nobr></span>
""")


class AbstractFileTable(renderers.TableRenderer):
  """A table that displays the content of a directory.

  Listening Javascript Events:
    - tree_select(aff4_path) - A selection event on the tree informing us of the
      tree path.  We re-layout the entire table on this event to show the
      directory listing of aff4_path.

  Generated Javascript Events:
    - file_select(aff4_path, age) - The full AFF4 path for the file in the
      directory which is selected. Age is the latest age we wish to see.

  Internal State:
    - client_id.
  """

  # When the table is selected we emit a selection event formed by combining the
  # tree with the table.
  table_selection_template = renderers.Template("""
<script>
  //Receive the selection event and emit a path
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var aff4_path = node.find("span[aff4_path]").attr("aff4_path");
      var age = node.find("span[age]").attr('age');
      grr.publish("file_select", aff4_path, age);
    };
  }, '{{ unique|escapejs }}');

  // Allow the age to be updated for a basename.
  grr.subscribe("update_age", function(aff4_path, age, age_string) {
    var cell = $("#{{unique}} span[aff4_path='" + aff4_path + "']")
      .parents("tr")
      .find("span[age]");
    cell.attr("age", age).text(age_string);
    grr.publish("file_select", aff4_path, age);
  }, '{{unique|escapejs}}');

</script>""")

  # Subscribe for the tree event queue and when events arrive refresh the table.
  tree_event_template = renderers.Template("""
<script>
  // Update the table when the tree changes
  grr.subscribe("tree_select", function(aff4_path, selected_id,
    update_hash) {
    // Replace ourselves with a new table.
    grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
      client_id: '{{this.state.client_id|escapejs}}',
      aff4_path: aff4_path,
    });
    grr.state.tree_path = aff4_path;

    // If the user really clicked the tree, we reset the hash
    if (update_hash != 'no_hash') {
      grr.publish('hash_state', 'tb', undefined);
    }
  }, '{{ unique|escapejs }}');

  // Allow the table content to be restored from the hash.
  $("span[aff4_path='" + grr.hash.aff4_path + "']").click()

</script>""")

  layout_template = (renderers.TableRenderer.layout_template +
                     table_selection_template +
                     tree_event_template)

  ajax_template = (renderers.TableRenderer.ajax_template + """
<div id="version_selector_dialog_{{unique|escape}}"
  class="version-selector-dialog modal wide-modal high-modal hide"></div>
<script>
(function () {
  $("img.version-selector").unbind("click").click(function (event) {
    $("#version_selector_{{unique|escapejs}}").modal("show");

    var aff4_path =
      $(this).parents('tr').find('span[aff4_path]').attr('aff4_path');
    var state = $.extend({
      aff4_path: aff4_path
    }, grr.state);

    grr.layout('VersionSelectorDialog',
      'version_selector_dialog_{{unique|escapejs}}', state);
    $('#version_selector_dialog_{{unique|escapejs}}').modal('show');

    event.stopPropagation();
  });
})();
</script>
""")

  toolbar = None    # Toolbar class to render above table.
  content_cache = None
  post_parameters = ["aff4_path"]
  root_path = "/"   # Paths will all be under this path.

  # This can restrict the view to only certain types of objects. It should be a
  # list of types to show.
  visible_types = None

  def __init__(self, **kwargs):
    super(AbstractFileTable, self).__init__(**kwargs)

    if AbstractFileTable.content_cache is None:
      AbstractFileTable.content_cache = utils.TimeBasedCache()

  def Layout(self, request, response):
    """Populate the table state with the request."""
    # Draw the toolbar first
    if self.toolbar:
      tb_cls = renderers.Renderer.classes[self.toolbar]
      tb_cls().Layout(request, response)
    return super(AbstractFileTable, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table."""
    # Default sort direction
    sort = request.REQ.get("sort", "Name:asc")
    try:
      reverse_sort = sort.split(":")[1] == "desc"
    except IndexError:
      reverse_sort = False

    filter_term = request.REQ.get("filter")
    aff4_path = request.REQ.get("aff4_path", self.root_path)
    urn = rdfvalue.RDFURN(aff4_path)

    filter_string = None
    if filter_term:
      column, regex = filter_term.split(":", 1)

      escaped_regex = utils.EscapeRegex(aff4_path + "/")
      # The start anchor refers only to this directory.
      if regex.startswith("^"):
        escaped_regex += utils.EscapeRegex(regex[1:])
      else:
        escaped_regex += ".*" + utils.EscapeRegex(regex)

      filter_string = "subject matches '%s'" % escaped_regex

    # For now we just list the directory
    try:
      key = utils.SmartUnicode(urn)
      if filter_string:
        key += ":" + filter_string
      # Open the directory as a directory.
      directory_node = aff4.FACTORY.Open(urn, token=request.token).Upgrade(
          "VFSDirectory")
      if not directory_node:
        raise IOError()

      key += str(directory_node.Get(directory_node.Schema.LAST))
      key += ":" + str(request.token)
      try:
        children = self.content_cache.Get(key)
      except KeyError:
        # Only show the direct children.
        children = sorted(directory_node.Query(filter_string=filter_string,
                                               limit=100000))

        # Filter the children according to types.
        if self.visible_types:
          children = [x for x in children
                      if x.__class__.__name__ in self.visible_types]

        self.content_cache.Put(key, children)

        try:
          self.message = "Directory Listing '%s' was taken on %s" % (
              aff4_path, directory_node.Get(directory_node.Schema.TYPE.age))
        except AttributeError:
          pass

    except IOError:
      children = []

    children.sort(reverse=reverse_sort)
    row_index = start_row

    # Make sure the table knows how large it is for paging.
    self.size = len(children)
    self.columns[1].base_path = urn
    for fd in children[start_row:end_row]:
      # We use the timestamp on the TYPE as a proxy for the last update time
      # of this object - its only an estimate.
      fd_type = fd.Get(fd.Schema.TYPE)
      if fd_type:
        self.AddCell(row_index, "Age", rdfvalue.RDFDatetime(fd_type.age))

      self.AddCell(row_index, "Name", fd.urn)

      # Add the fd to all the columns
      for column in self.columns:
        # This sets AttributeColumns directly from their fd.
        if isinstance(column, renderers.AttributeColumn):
          column.AddRowFromFd(row_index, fd)

      if "Container" in fd.behaviours:
        self.AddCell(row_index, "Icon", dict(icon="directory",
                                             description="Directory"))
      else:
        self.AddCell(row_index, "Icon", dict(icon="file",
                                             description="File Like Object"))

      row_index += 1
      if row_index > end_row:
        return


class FileTable(AbstractFileTable):
  """A table that displays the content of a directory.

  Listening Javascript Events:
    - tree_select(aff4_path) - A selection event on the tree informing us of the
      tree path.  We re-layout the entire table on this event to show the
      directory listing of aff4_path.

  Generated Javascript Events:
    - file_select(aff4_path, age) - The full AFF4 path for the file in the
      directory which is selected. Age is the latest age we wish to see.

  Internal State:
    - client_id.
  """

  root_path = None   # The root will be dynamically set to the client path.
  toolbar = "Toolbar"

  def __init__(self, **kwargs):
    super(FileTable, self).__init__(**kwargs)

    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer, width="40px"))
    self.AddColumn(renderers.RDFValueColumn(
        "Name", renderer=renderers.SubjectRenderer, sortable=True, width="20%"))
    self.AddColumn(renderers.AttributeColumn("type", width="10%"))
    self.AddColumn(renderers.AttributeColumn("size", width="10%"))
    self.AddColumn(renderers.AttributeColumn("stat.st_size", width="15%"))
    self.AddColumn(renderers.AttributeColumn("stat.st_mtime", width="15%"))
    self.AddColumn(renderers.AttributeColumn("stat.st_ctime", width="15%"))
    self.AddColumn(renderers.RDFValueColumn(
        "Age", renderer=AgeSelector, width="15%"))

  def Layout(self, request, response):
    """Populate the table state with the request."""
    self.state["client_id"] = client_id = request.REQ.get("client_id")
    self.root_path = client_id
    return super(FileTable, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    client_id = request.REQ.get("client_id")
    self.root_path = client_id
    return super(FileTable, self).BuildTable(start_row, end_row, request)


class FileSystemTree(renderers.TreeRenderer):
  """A FileSystem navigation Tree.

  Generated Javascript Events:
    - tree_select(aff4_path) - The full aff4 path for the branch which the user
      selected.

  Internal State:
    - client_id: The client this tree is showing.
    - aff4_root: The aff4 node which forms the root of this tree.
  """

  def Layout(self, request, response):
    self.state["client_id"] = client_id = request.REQ.get("client_id")
    self.state["aff4_root"] = request.REQ.get("aff4_root", client_id)

    return super(FileSystemTree, self).Layout(request, response)

  def RenderBranch(self, path, request):
    """Renders tree leafs for filesystem path."""
    client_id = request.REQ["client_id"]
    aff4_root = rdfvalue.RDFURN(request.REQ.get("aff4_root", client_id))

    # Path is relative to the aff4 root specified.
    urn = aff4_root.Add(path)
    try:
      # Open the client
      directory = aff4.FACTORY.Open(urn, token=request.token).Upgrade(
          "VFSDirectory")

      children = [ch for ch in directory.OpenChildren(limit=100000)
                  if "Container" in ch.behaviours]

      try:
        self.message = "Directory %s Last retrieved %s" % (
            urn, directory.Get(directory.Schema.TYPE).age)
      except AttributeError:
        pass

      for child in children:
        self.AddElement(child.urn.RelativeName(urn))

    except IOError as e:
      self.message = "Error fetching %s: %s" % (urn, e)


class Toolbar(renderers.TemplateRenderer):
  """A navigation enhancing toolbar.

  Listening Javascript Events:
    - AttributeUpdated(aff4_path, attribute): This event is fired then the
      aff4_path has updated. If the content of this event have changed, we emit
      the tree_select and file_select events to force the table to redraw.

  Generated Javascript Events:
    - file_select(aff4_path), tree_select(aff4_path) are fired when the buttons
      are clicked.

  Internal State:
    - aff4_path: The path we are viewing now in the table.
  """

  layout_template = renderers.Template("""

<ul class="breadcrumb">
  <li class="pull-right">
    <button class="btn" id='refresh_{{unique|escape}}'
      title='Refresh this directory listing.'>
      <img src='/static/images/stock_refresh.png' class="toolbar_icon" />
    </button>
  </li>
  <li class="pull-right">
    <button class="btn" id='rweowned' title='Is this machine pwned?'>
      <img src='/static/images/stock_dialog_question.png'
        class="toolbar_icon" />
    </button>
  </li>
{% for path, fullpath, fullpath_id, i, last in this.paths %}
  <li {% if forloop.last %}class="active"{% endif %}>
    {% if forloop.last %}
      {{path|escape}}
    {% else %}
    <a id="path_{{i|escape}}">{{path|escape}}</a>
    <span class="divider">&gt;</span>
    {% endif %}
  </li>
{% endfor %}
  <div class="clearfix"></div>
</ul>
<div id="refresh_action" class="hide"></div>
<div id="rweowned_dialog" class="modal hide"></div>

<script>
$('#refresh_{{unique|escapejs}}').click(function (){
  $('#refresh_{{unique|escapejs}}').attr('disabled', 'disabled');
  grr.layout("UpdateAttribute", "refresh_action", {
   aff4_path: "{{this.aff4_path|escapejs}}",
   attribute: "aff4:contains"
  });
});

$('#rweowned').click(function (){
  grr.layout("RWeOwned", "rweowned_dialog");
});

grr.dialog("RWeOwned", "rweowned_dialog", "rweowned", {
     width: "500px", height: "auto",
     title: "Is this machine pwned?",
});

// When the attribute is updated, refresh the views
grr.subscribe("AttributeUpdated", function(path, attribute) {
  $('#refresh_{{unique|escapejs}}').attr('disabled', null);
  if (attribute == "aff4:contains") {
    // Update the table
    grr.publish("tree_select", path);
    grr.publish("file_select", path);
  };
}, 'refresh_{{unique|escapejs}}');

{% for path, fullpath, fullpath_id, i in this.paths %}
$('#path_{{i|escapejs}}').click(function () {
   grr.publish("tree_select", "{{ fullpath|escapejs }}");
   grr.publish("file_select", "{{ fullpath|escapejs }}");
   grr.publish("hash_state", "t", "{{ fullpath_id|escapejs }}");
});
{% endfor %}
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    self.state["client_id"] = client_id = request.REQ.get("client_id")
    self.state["aff4_path"] = self.aff4_path = request.REQ.get(
        "aff4_path", client_id)

    client_urn = rdfvalue.ClientURN(client_id)

    self.paths = [("/", client_urn, "_", 0)]
    for path in rdfvalue.RDFURN(self.aff4_path).Split()[1:]:
      previous = self.paths[-1]
      fullpath = previous[1].Add(path)

      self.paths.append((path, fullpath,
                         renderers.DeriveIDFromPath(
                             fullpath.RelativeName(client_urn)),
                         previous[3] + 1))

    return super(Toolbar, self).Layout(request, response)


class UpdateAttribute(renderers.TemplateRenderer):
  """Reloads a directory listing from client.

  The renderer will launch the flow in the layout method, and then call its
  render method every few seconds to check if the flow is complete.

  Post Parameters:
    - aff4_path: The aff4 path to update the attribute for.
    - aff4_type: If provided, the aff4 object will be upgraded to this type
      before updating.
    - attribute: The attribute name to update.

  Generated Javascript Events:
    - AttributeUpdated(aff4_path, attribute) - When the flow is complete we emit
      this event.
  """

  # Number of ms to wait
  poll_time = 1000

  layout_template = renderers.Template("""
<script>
window.setTimeout(function () {
  grr.update('{{renderer|escapejs}}', '{{id|escapejs}}',
    {'flow_urn': '{{this.flow_urn|escapejs}}',
     'aff4_path': '{{this.aff4_path|escapejs}}',
     'attribute': '{{this.attribute_to_refresh|escapejs}}'
    });
}, {{this.poll_time|escapejs}});
</script>
""")

  completed_template = renderers.Template("""
<script>
 grr.publish("AttributeUpdated", "{{this.aff4_path|escapejs}}",
    "{{this.attribute_to_refresh|escapejs}}");
 $("#{{this.id|escapejs}}").remove();
</script>
""")

  def ParseRequest(self, request):
    """Parses parameters from the request."""
    self.aff4_path = request.REQ.get("aff4_path")
    self.flow_urn = request.REQ.get("flow_urn")
    # Refresh the contains attribute
    self.attribute_to_refresh = request.REQ.get(
        "attribute", str(aff4.AFF4Volume.SchemaCls.CONTAINS))

  def Layout(self, request, response):
    """Render the toolbar."""
    self.ParseRequest(request)

    try:
      client_id = rdfvalue.RDFURN(self.aff4_path).Split(2)[0]
      update_flow_urn = flow.GRRFlow.StartFlow(
          client_id, "UpdateVFSFile", token=request.token,
          vfs_file_urn=rdfvalue.RDFURN(self.aff4_path),
          attribute=self.attribute_to_refresh)

      update_flow = aff4.FACTORY.Open(
          update_flow_urn, aff4_type="UpdateVFSFile", token=request.token)
      self.flow_urn = update_flow.state.get_file_flow_urn
    except IOError as e:
      raise IOError("Sorry. This path cannot be refreshed due to %s" % e)

    if self.flow_urn:
      return super(UpdateAttribute, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Continue polling as long as the flow is in flight."""
    super(UpdateAttribute, self).RenderAjax(request, response)
    complete = False
    self.ParseRequest(request)

    # Check if the flow is still in flight.
    try:
      flow_obj = aff4.FACTORY.Open(self.flow_urn, token=request.token)
      if not flow_obj.IsRunning():
        complete = True
    except IOError:
      # Something went wrong, stop polling.
      complete = True

    if complete:
      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.completed_template)

    return renderers.TemplateRenderer.Layout(self, request, response,
                                             self.layout_template)


class AFF4ReaderMixin(object):
  """A helper which reads a buffer from an AFF4 object.

  This is meant to be mixed in with the HexView and TextView renderers.
  """

  def ReadBuffer(self, request, offset, length):
    """Renders the HexTable."""
    # Allow derived classes to just set the urn directly
    self.aff4_path = request.REQ.get("aff4_path")
    self.age = request.REQ.get("age")
    if not self.aff4_path: return

    try:
      fd = aff4.FACTORY.Open(self.aff4_path, token=request.token,
                             age=rdfvalue.RDFDatetime(self.age))
      self.total_size = int(fd.Get(fd.Schema.SIZE))
    except (IOError, TypeError, AttributeError):
      self.total_size = 0
      return ""

    fd.Seek(offset)
    return fd.Read(length)


class FileHexViewer(AFF4ReaderMixin, fileview_widgets.HexView):
  """A HexView renderer."""


class FileTextViewer(AFF4ReaderMixin, fileview_widgets.TextView):
  """A TextView renderer."""


class VirtualFileSystemView(renderers.Splitter):
  """This is the main view to browse files."""
  behaviours = frozenset(["Host"])
  order = 10
  description = "Browse Virtual Filesystem"

  left_renderer = "FileSystemTree"
  top_right_renderer = "FileTable"
  bottom_right_renderer = "AFF4ObjectRenderer"


class DownloadView(renderers.TemplateRenderer):
  """Renders a download page."""

  # We allow a longer execution time here to be able to download large files.
  max_execution_time = 60 * 15

  layout_template = renderers.Template("""
<h3>{{ this.path|escape }}</h3>
<div id="{{ unique|escape }}_action" class="hide"></div>
{% if this.hash %}
Hash was {{ this.hash|escape }}.
{% endif %}

{% if this.file_exists %}
As downloaded on {{ this.age|escape }}.<br>
<p>
<button id="{{ unique|escape }}_2" class="btn">
 Download ({{this.size|escape}} bytes)
</button>
</p>
{% endif %}

<button id="{{ unique|escape }}" class="btn">Get a new Version</button>
</div>
<script>
  var button = $("#{{ unique|escapejs }}").button();
  var download_button = $("#{{ unique|escapejs }}_2").button();

  button.click(function () {
    $('#{{unique|escapejs}}').attr('disabled', 'disabled');
    grr.layout("UpdateAttribute", "{{unique|escapejs}}_action", {
      attribute: 'aff4:content',
      aff4_type: 'VFSFile',
      aff4_path: '{{this.aff4_path|escapejs}}',
      reason: '{{this.token.reason|escapejs}}',
      client_id: grr.state.client_id,
    });
  });

  // When the attribute is updated, refresh the views
  grr.subscribe("AttributeUpdated", function(path, attribute) {
    if (attribute == "aff4:content") {
      // Update the download screen
      grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
        aff4_path: path,
        reason: '{{this.token.reason|escapejs}}',
      });
    };
  }, '{{unique|escapejs}}_action');

  {% if this.file_exists %}
  // Attach a handler to the Download button.
  var state = {aff4_path: '{{this.aff4_path|escapejs}}',
               reason: '{{this.token.reason|escapejs}}',
               client_id: grr.state.client_id,
               age: '{{this.age_int|escapejs}}'
              }
  grr.downloadHandler(download_button, state, false,
                      '/render/Download/DownloadView');
  {% endif %}
</script>""")

  error_template = renderers.Template("""
<h1>Error</h1>{{this.urn|escape}} does not appear to be a file object.
""")
  bad_extensions = [".bat", ".cmd", ".exe", ".com", ".pif", ".py", ".pl",
                    ".scr", ".vbs"]

  def Layout(self, request, response):
    """Present a download form."""
    self.client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", self.client_id)
    self.age = rdfvalue.RDFDatetime(request.REQ.get("age"))
    self.age_int = int(self.age)
    self.token = request.token

    try:
      fd = aff4.FACTORY.Open(self.aff4_path, token=request.token,
                             age=self.age)
      self.path = fd.urn
      self.hash = fd.Get(fd.Schema.HASH, None)
      self.size = fd.Get(fd.Schema.SIZE)

      # If data is available to read - we present the download button.
      self.file_exists = False
      try:
        if fd.Read(1):
          self.file_exists = True
      except (IOError, AttributeError):
        pass

    except (AttributeError, IOError):
      # Install the error template instead.
      self.layout_template = self.error_template

    return super(DownloadView, self).Layout(request, response)

  def Download(self, request, _):
    """Stream the file into the browser."""
    # Open the client
    client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", client_id)
    self.age = rdfvalue.RDFDatetime(request.REQ.get("age")) or aff4.NEWEST_TIME
    self.token = request.token
    # If set, we don't append .noexec to dangerous extensions.
    safe_extension = bool(request.REQ.get("safe_extension", 0))

    if self.aff4_path:

      def Generator():
        fd = aff4.FACTORY.Open(self.aff4_path, token=request.token,
                               age=self.age)

        while True:
          data = fd.Read(1000000)
          if not data: break

          yield data

      filename = os.path.basename(utils.SmartStr(self.aff4_path))
      if not safe_extension:
        for ext in self.bad_extensions:
          if filename.lower().endswith(ext):
            filename += ".noexec"

      response = http.HttpResponse(content=Generator(),
                                   mimetype="binary/octet-stream")
      # This must be a string.
      response["Content-Disposition"] = ("attachment; filename=%s" % filename)

      return response


class UploadView(renderers.TemplateRenderer):
  """Renders an upload page."""

  post_parameters = ["tree_path"]
  upload_handler = "UploadHandler"

  layout_template = renderers.Template("""
<h3>Upload to {{ grr.state.tree_path|escape }}</h3>
<form id="{{unique|escape}}_form" enctype="multipart/form-data">
<input id="{{ unique|escape }}_file" type="file" name="uploadFile" />
</form>
<button class="btn" id="{{ unique|escape }}_button">Upload</button>
<br/><br/>
<div id="{{ unique|escape }}_upload_results"/>
<div id="{{ unique|escape }}_upload_progress"/>

<script>
  var u_button = $("#{{ unique|escapejs }}_button").button();
  var u_file = $("#{{ unique|escapejs }}_file");
  var state = {{this.state_json|safe}};
  state.tree_path = grr.state.tree_path;

  u_button.click(function () {
    grr.uploadHandler("{{ this.upload_handler|escapejs }}",
      "{{ unique|escapejs }}_form",
      "{{ unique|escapejs }}_upload_progress",
      function (dat) {
        $("#{{ unique|escapejs }}_upload_results").text(dat);
      },
      state
    );
  });
</script>
""")


class UploadHandler(renderers.TemplateRenderer):
  """Handles an uploaded file."""

  # We allow a longer execution time here to be able to upload large files.
  max_execution_time = 60 * 2

  storage_path = "aff4:/config"

  error_template = renderers.Template("""
Error: {{this.error|escape}}.
""")
  success_template = renderers.Template("""
Success: File uploaded {{this.dest_path|escape}}.
""")

  def RenderAjax(self, request, response):
    """Store the file on the server."""
    super(UploadHandler, self).RenderAjax(request, response)

    try:
      self.uploaded_file = request.FILES.items()[0][1]
      self.dest_path, aff4_type = self.GetFilePath(request)
      self.ValidateFile()

      dest_file = aff4.FACTORY.Create(self.dest_path, aff4_type=aff4_type,
                                      token=request.token)
      for chunk in self.uploaded_file.chunks():
        dest_file.Write(chunk)

      dest_file.Close()
      return super(UploadHandler, self).Layout(request, response,
                                               self.success_template)
    except (IOError, IndexError) as e:
      self.error = e
      return super(UploadHandler, self).Layout(request, response,
                                               self.error_template)

  def GetFilePath(self, unused_request):
    """Get the path to write the file to and aff4 type as a tuple."""
    path = rdfvalue.RDFURN(self.storage_path).Add(self.uploaded_file.name)
    return path, "VFSFile"

  def ValidateFile(self):
    """Check if a file matches what we expected to be uploaded.

    Raises:
      IOError: On validation failure.
    """
    if self.uploaded_file.size < 100:
      raise IOError("File is too small.")


class AFF4Stats(renderers.TemplateRenderer):
  """Show stats about the currently selected AFF4 object.

  Post Parameters:
    - aff4_path: The aff4 path to update the attribute for.
    - age: The version of the AFF4 object to display.
  """

  # This renderer applies to this AFF4 type
  name = "Stats"
  css_class = ""
  historical_renderer = "HistoricalView"
  filtered_attributes = None

  layout_template = renderers.Template("""
<div class="container-fluid">
<div class="row-fluid">

<div id="{{unique|escape}}" class="{{this.css_class}}">
<h3>{{ this.path|escape }} @ {{this.age|escape}}</h3>
<table id='{{ unique|escape }}'
  class="table table-condensed table-bordered table-fullwidth fixed-columns">
<colgroup>
  <col style="width: 20ex" />
  <col style="width: 100%" />
  <col style="width: 20ex" />
</colgroup>
<thead>
<tr>
  <th class="ui-state-default">Attribute</th>
  <th class="ui-state-default">Value</th>
  <th class="ui-state-default">Age</th>
</tr>
</thead>
<tbody>
{% for name, attributes in this.classes %}
 <tr>
   <td colspan=3 class="grr_aff4_type_header"><b>{{ name|escape }}</b></td>
 </tr>
 {% for attribute, description, value, age, multi in attributes %}
 <tr>
   <td class='attribute_opener' attribute="{{attribute|escape}}">
      {% if multi %}
        <ins class='fg-button ui-icon ui-icon-plus'/>
      {% endif %}
      <b title='{{ description|escape }}'>{{ attribute|escape }}</b>
   </td>
   <td>
     <div class="default_view">{{ value|safe }}</div>
     <div id="content_{{unique|escape}}_{{attribute|escape}}"
       class="historical_view"></div>
   </td>
   <td><div class='non-breaking'>{{ age|escape }}</div></td>
 </tr>
 {% endfor %}
{% endfor %}
</tbody>
</table>
</div>

</div>
</div>

<script>
$('.attribute_opener').click(function () {
  var jthis = $(this);
  var ins = jthis.children("ins");
  var value = jthis.next("td");
  var historical = value.children(".historical_view");
  var historical_id = historical.attr("id");

  if(ins.hasClass('ui-icon-plus')) {
    ins.removeClass('ui-icon-plus').addClass('ui-icon-minus');
    historical.show();
    var state = {{this.state_json|safe}};
    state.attribute = jthis.attr("attribute");

    grr.layout("{{this.historical_renderer|escapejs}}", historical_id, state);
    value.children(".default_view").hide();
  } else {
    ins.removeClass('ui-icon-minus').addClass('ui-icon-plus');
    value.children(".default_view").show();
    historical.html('').hide();
  };
});
</script>
""")

  def Layout(self, request, response, client_id=None, aff4_path=None, age=None):
    """Introspect the Schema for each object."""
    # Allow derived classes to just set the client_id/aff4_path/age directly
    self.client_id = client_id or request.REQ.get("client_id")
    self.aff4_path = aff4_path or request.REQ.get("aff4_path")
    self.age = request.REQ.get("age")
    if self.age is None:
      self.age = rdfvalue.RDFDatetime().Now()
    else:
      self.age = rdfvalue.RDFDatetime(self.age)

    if not self.aff4_path: return

    try:
      self.fd = aff4.FACTORY.Open(self.aff4_path, token=request.token,
                                  age=age or self.age)
      self.classes = self.RenderAFF4Attributes(self.fd, request)
      self.state["path"] = self.path = utils.SmartStr(self.fd.urn)
    except IOError:
      self.path = "Unable to open %s" % self.urn
      self.classes = []

    return super(AFF4Stats, self).Layout(request, response)

  def RenderAFF4Attributes(self, fd, request=None):
    """Returns attributes rendered by class."""
    classes = []
    attribute_names = set()

    for flow_cls in fd.__class__.__mro__:

      if not hasattr(flow_cls, "SchemaCls"):
        continue

      schema = flow_cls.SchemaCls
      attributes = []

      for name, attribute in sorted(schema.__dict__.items()):
        if not isinstance(attribute, aff4.Attribute): continue

        # If we already showed this attribute we move on
        if attribute.predicate in attribute_names: continue

        values = list(fd.GetValuesForAttribute(attribute))
        multi = len(values) > 1

        if values:
          attribute_names.add(attribute.predicate)
          value_renderer = renderers.FindRendererForObject(values[0])
          if self.filtered_attributes and name not in self.filtered_attributes:
            continue

          attributes.append((name, attribute.description,

                             # This is assumed to be in safe RawHTML and not
                             # escaped.
                             value_renderer.RawHTML(request),
                             rdfvalue.RDFDatetime(values[0].age), multi))

      if attributes:
        classes.append((flow_cls.__name__, attributes))

    return classes


class HostInformation(AFF4Stats):
  """View information about the host."""
  description = "Host Information"
  behaviours = frozenset(["Host"])
  order = 0
  css_class = "TableBody"
  filtered_attributes = ["USERNAMES", "HOSTNAME", "MAC_ADDRESS", "INSTALL_DATE",
                         "SYSTEM", "CLOCK", "CLIENT_INFO", "UNAME", "ARCH",
                         "FIRST_SEEN"]

  def Layout(self, request, response, client_id=None):
    client_id = client_id or request.REQ.get("client_id")
    urn = rdfvalue.RDFURN(client_id)

    # This verifies we have auth for deep client paths. If this raises, we
    # force the auth screen.
    aff4.FACTORY.Open(rdfvalue.RDFURN(urn).Add("CheckAuth"),
                      token=request.token, mode="r")

    return super(HostInformation, self).Layout(request, response,
                                               client_id=client_id,
                                               aff4_path=urn)


class AFF4ObjectRenderer(renderers.TemplateRenderer):
  """This renderer delegates to the correct subrenderer based on the request.

  Listening Javascript Events:
    - file_select(aff4_path, age) - A selection event on the file table
      informing us of a new aff4 file to show. We redraw the entire bottom right
      side using a new renderer.

  """

  layout_template = renderers.Template("""
<div id="{{unique|escape}}"></div>
<script>
grr.subscribe("{{ this.event_queue|escapejs }}", function(aff4_path, age) {
  grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}",
    {aff4_path: aff4_path, age: age})
}, '{{unique|escape}}');
</script>
""")

  # When a message appears on this queue we choose a new renderer.
  event_queue = "file_select"

  def Layout(self, request, response):
    """Produces a layout as returned by the subrenderer."""

    # This is the standard renderer for now.
    subrenderer = FileViewTabs
    client_id = request.REQ.get("client_id")
    aff4_path = request.REQ.get("aff4_path", client_id)
    if not aff4_path:
      raise RuntimeError("No valid aff4 path or client id provided")

    fd = aff4.FACTORY.Open(aff4_path, token=request.token)
    fd_type = fd.Get(fd.Schema.TYPE)
    if fd_type:
      for cls in self.classes.values():
        if getattr(cls, "aff4_type", None) == fd_type:
          subrenderer = cls

    subrenderer(fd).Layout(request, response)
    return super(AFF4ObjectRenderer, self).Layout(request, response)


class FileViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected file.

  Internal State:
    - aff4_path - The AFF4 object we are currently showing.
    - age: The version of the AFF4 object to display.
  """
  names = ["Stats", "Download", "TextView", "HexView"]
  delegated_renderers = ["AFF4Stats", "DownloadView", "FileTextViewer",
                         "FileHexViewer"]

  def __init__(self, fd=None, **kwargs):
    if fd:
      self.fd = fd
    super(FileViewTabs, self).__init__(**kwargs)

  def Layout(self, request, response):
    """Check if the file is a readable and disable the tabs."""
    client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", client_id)
    self.age = request.REQ.get("age", rdfvalue.RDFDatetime().Now())
    self.state = dict(aff4_path=self.aff4_path, age=int(self.age))

    try:
      if not self.fd:
        self.fd = aff4.FACTORY.Open(self.aff4_path, token=request.token)
      # We just check if the object has a read method.
      _ = self.fd.Read
    except (IOError, AttributeError):
      self.disabled = ["DownloadView", "FileHexViewer", "FileTextViewer"]

    return super(FileViewTabs, self).Layout(request, response)


class RWeOwned(renderers.TemplateRenderer):
  """A magic 8 ball reply to the question - Are we Owned?"""

  layout_template = renderers.Template("""
  <div class="modal-header">
<button type="button" class="close" data-dismiss="modal" aria-hidden="true">
   x
</button>
<h3>Are we owned?</h3>
</div>
  <div class="modal-body">
    <p class="text-info">
{{this.choice|escape}}
</div>
""")

  def Layout(self, request, response):
    """Render a magic 8 ball easter-egg."""
    options = u"""It is certain
You were eaten by a Grue!
中国 got you!!
All your bases are belong to us!
Maybe it was the Russians?
It is decidedly so
Without a doubt
Yes - definitely
You may rely on it
As I see it, yes
Most likely
Outlook good
Signs point to yes
Yes
Reply hazy, try again
Ask again later
Better not tell you now
Cannot predict now
Concentrate and ask again
Don't count on it
My reply is no
My sources say no
Outlook not so good
Very doubtful""".splitlines()

    self.choice = options[random.randint(0, len(options) - 1)]

    return super(RWeOwned, self).Layout(request, response)


class HistoricalView(renderers.TableRenderer):
  """Show historical view for an attribute."""

  def __init__(self, **kwargs):
    super(HistoricalView, self).__init__(**kwargs)

    self.AddColumn(renderers.RDFValueColumn("Age"))

  def Layout(self, request, response):
    """Add the columns to the table."""
    self.AddColumn(renderers.RDFValueColumn(request.REQ.get("attribute")))

    return super(HistoricalView, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table with attribute values."""
    attribute_name = request.REQ.get("attribute")
    if attribute_name is None:
      return

    urn = request.REQ.get("urn")
    client_id = request.REQ.get("client_id")
    path = request.REQ.get("path")

    self.AddColumn(renderers.RDFValueColumn(attribute_name))
    fd = aff4.FACTORY.Open(urn or path or client_id,
                           token=request.token, age=aff4.ALL_TIMES)
    self.BuildTableFromAttribute(attribute_name, fd, start_row, end_row)

  def BuildTableFromAttribute(self, attribute_name, fd, start_row, end_row):
    """Build the table for the attribute."""
    attribute = getattr(fd.Schema, attribute_name)

    i = 0
    for i, value in enumerate(fd.GetValuesForAttribute(attribute)):
      if i > end_row: break
      if i < start_row: continue

      self.AddCell(i, "Age", rdfvalue.RDFDatetime(value.age))
      self.AddCell(i, attribute_name, value)

    self.size = i + 1


class VersionSelectorDialog(renderers.TableRenderer):
  """Renders the version available for this object."""

  table_selection_template = renderers.Template("""
<script>
  // Receive the selection event and update the age of this aff4 object
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var aff4_path = "{{this.state.aff4_path|escapejs}}";
      var age = node.find("span[age]").attr('age');
      var age_string = node.find("span[age]").text();
      grr.publish("update_age", aff4_path, age, age_string);
      $(".version-selector-dialog").modal("hide");
    };
  }, '{{ unique|escapejs }}');
</script>
""")

  layout_template = renderers.Template("""
<div class="modal-header">
  <button type="button" class="close" data-dismiss="modal" aria-hidden="true">
    x</button>
  <h4>Versions of {{this.state.aff4_path}}</h4>
</div>
<div class="modal-body">
  <div class="padded">
""") + table_selection_template + """
""" + renderers.TableRenderer.layout_template + """
  </div>
</div>
<div class="modal-footer">
  <button class="btn" data-dismiss="modal" name="Ok"
    aria-hidden="true">Ok</button>
</div>
"""

  def __init__(self, **kwargs):
    super(VersionSelectorDialog, self).__init__(**kwargs)

    self.AddColumn(renderers.RDFValueColumn("Age"))
    self.AddColumn(renderers.RDFValueColumn("Type"))

  def Layout(self, request, response):
    """Populates the table state with the request."""
    self.state["aff4_path"] = request.REQ.get("aff4_path")
    return super(VersionSelectorDialog, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populates the table with attribute values."""
    aff4_path = request.REQ.get("aff4_path")
    if aff4_path is None: return

    fd = aff4.FACTORY.Open(aff4_path, age=aff4.ALL_TIMES, token=request.token)
    i = 0
    for i, type_attribute in enumerate(
        fd.GetValuesForAttribute(fd.Schema.TYPE)):
      if i < start_row or i > end_row:
        continue

      self.AddCell(i, "Age", rdfvalue.RDFDatetime(type_attribute.age))
      self.AddCell(i, "Type", type_attribute)

    return i + 1
