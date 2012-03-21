#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""This plugin renders the filesystem in a tree and a table."""

import os
import random
import socket
import struct

from django import http
from M2Crypto import X509

from grr.gui import renderers
from grr.gui.plugins import fileview_widgets
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import utils
from grr.proto import jobs_pb2


class StatEntryRenderer(renderers.RDFProtoRenderer):
  """Nicely format the StatResponse proto."""
  ClassName = "StatEntry"
  name = "Stat Entry"

  def Translate_st_mode(self, _, st_mode):
    """Pretty print the file mode."""
    mode_template = "rwx" * 3
    mode = bin(st_mode)[-9:]

    bits = []
    for i in range(len(mode_template)):
      if mode[i] == "1":
        bit = mode_template[i]
      else:
        bit = "-"

      bits.append(bit)

    return "".join(bits)

  def TranslatePathSpecBasename(self, _, pathspec):
    """Render the basename of the pathspec."""
    return utils.Pathspec(pathspec).Basename()

  translator = dict(st_mtime=renderers.RDFProtoRenderer.Time32Bit,
                    st_atime=renderers.RDFProtoRenderer.Time32Bit,
                    st_ctime=renderers.RDFProtoRenderer.Time32Bit,
                    st_mode=Translate_st_mode,
                    pathspec=TranslatePathSpecBasename)


class CollectionRenderer(StatEntryRenderer):
  """Nicely format a Collection."""
  ClassName = "CollectionList"
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
    items = self.proxy.data.items
    for item in items:
      row = []
      for name in fields:
        value = getattr(item, name)
        try:
          value = self.translator[name](self, None, value)

        # Regardless of what the error is, we need to escape the value.
        except StandardError:
          value = self.FormatFromTemplate(self.translator_error_template,
                                          value=value)

        row.append(value)

      self.result.append(row)

    return renderers.TemplateRenderer.Layout(self, request, response)


class UserEntryRenderer(renderers.RDFProtoArrayRenderer):
  ClassName = "User"
  name = "User Record"

  translator = dict(last_logon=renderers.RDFProtoRenderer.Time)


class InterfaceRenderer(renderers.RDFProtoArrayRenderer):
  """Render a machine's interfaces."""
  ClassName = "Interfaces"
  name = "Interface Record"

  def TranslateIp4Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET, x) for x in value])

  def TranslateMacAddress(self, _, value):
    return ":".join([x.encode("hex") for x in value])

  def TranslateIp6Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET6, x) for x in value])

  def TranslateNetworkAddresses(self, _, addresses):
    """Renders the Interface probobuf."""
    output_strings = []
    for address in addresses:
      if address.human_readable:
        output_strings.append(address.human_readable)
      else:
        if address.address_type == jobs_pb2.NetworkAddress.INET:
          output_strings.append(socket.inet_ntop(socket.AF_INET,
                                                 address.packed_bytes))
        else:
          output_strings.append(socket.inet_ntop(socket.AF_INET6,
                                                 address.packed_bytes))
    return "<br>".join(output_strings)

  translator = dict(ip4_addresses=TranslateIp4Addresses,
                    ip6_addresses=TranslateIp6Addresses,
                    mac_address=TranslateMacAddress,
                    addresses=TranslateNetworkAddresses)


class ConfigRenderer(renderers.RDFProtoRenderer):
  ClassName = "GRRConfig"
  name = "GRR Configuration"

  translator = {}


class ProcessRenderer(renderers.RDFProtoArrayRenderer):
  """Renders process listings."""
  ClassName = "Processes"
  name = "Process Listing"

  translator = dict(ctime=renderers.RDFProtoRenderer.Time)


class ConnectionRenderer(renderers.RDFProtoArrayRenderer):
  """Renders connection listings."""
  ClassName = "Connections"
  name = "Connection Listing"

  def TranslateIp4Address(self, _, value):
    return socket.inet_ntop(socket.AF_INET, struct.pack(">L", value))

  translator = dict(remote_addr=TranslateIp4Address,
                    local_addr=TranslateIp4Address,
                    ctime=renderers.RDFProtoRenderer.Time)


class FilesystemRenderer(renderers.RDFProtoArrayRenderer):
  ClassName = "FileSystem"
  name = "FileSystems"


class CertificateRenderer(renderers.RDFValueRenderer):
  """Render X509 Certs properly."""
  ClassName = "RDFX509Cert"
  name = "X509 Certificate"

  # Implement hide/show behaviour for certificates as they tend to be long and
  # uninteresting.
  layout_template = renderers.Template("""
<div class='certificate_viewer'>
  <ins class='fg-button ui-icon ui-icon-minus'/>
  Click to show details.
  <div class='contents'>
    <pre>
      {{ this.cert|escape }}
    </pre>
  </div>
</div>

<script>
$('.certificate_viewer').click(function () {
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
  ClassName = "BlobArray"
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
    for i in self.proxy.data:
      for field in ["integer", "string", "data", "boolean"]:
        if i.HasField(field):
          array.append(getattr(i, field))
          break

    return self.RenderFromTemplate(self.layout_template, response,
                                   first=array[0:1], array=array[1:])


class PathspecRenderer(renderers.RDFValueRenderer):
  """Renders the pathspec protobuf."""
  ClassName = "RDFPathSpec"

  template = renderers.Template("""
<pre>{{this.proxy|escape}}</pre>
""")


class FileTable(renderers.TableRenderer):
  """A table that displays the content of a directory.

  Listening Javascript Events:
    - tree_select(aff4_path) - A selection event on the tree informing us of the
      tree path.  We re-layout the entire table on this event to show the
      directory listing of aff4_path.

  Generated Javascript Events:
    - file_select(aff4_path) - The full AFF4 path for the file in the directory
      which is selected.

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
      var element = node.find("span")[0];
      if (element) {
        var filename = element.innerHTML;
        grr.publish("file_select",
                    "{{this.state.aff4_path|escapejs}}/" + filename);
      };
    };
  }, '{{ unique|escapejs }}');
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

    // If the user really clicked the tree, we reset the hash
    if (update_hash != 'no_hash') {
      grr.publish('hash_state', 'tb', undefined);
    }
  }, '{{ unique|escapejs }}');
</script>""")

  layout_template = (renderers.TableRenderer.layout_template +
                     table_selection_template +
                     tree_event_template)

  def __init__(self):
    super(FileTable, self).__init__()

    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer, width=0))
    self.AddColumn(renderers.RDFValueColumn(
        "Name", renderer=renderers.SubjectRenderer, sortable=True))
    self.AddColumn(renderers.AttributeColumn("type"))
    self.AddColumn(renderers.AttributeColumn("size"))
    self.AddColumn(renderers.RDFValueColumn("Age"))

  def Layout(self, request, response):
    """Populate the table state with the request."""
    self.state["client_id"] = client_id = request.REQ.get("client_id")
    self.state["aff4_path"] = request.REQ.get("aff4_path", client_id)

    # Draw the toolbar first
    Toolbar().Layout(request, response)

    return super(FileTable, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table."""
    # Default sort direction
    sort = request.REQ.get("sort", "Name:asc")
    try:
      reverse_sort = sort.split(":")[1] == "desc"
    except IndexError:
      reverse_sort = False

    filter_term = request.REQ.get("filter")

    filter_string = None
    if filter_term:
      column, regex = filter_term.split(":", 1)

      # The start anchor refers only to this directory.
      if regex.startswith("^"):
        regex = "/" + regex[1:]
      filter_string = "subject matches '%s'" % data_store.EscapeRegex(regex)

    # For now we just list the directory
    try:
      client_id = request.REQ.get("client_id")
      aff4_path = request.REQ.get("aff4_path", client_id)
      urn = aff4.RDFURN(aff4_path)

      # Open the directory as a directory.
      directory_node = aff4.FACTORY.Create(urn, "VFSDirectory", mode="r",
                                           token=request.token)
      if not directory_node:
        raise IOError()

      # Only show the direct children.
      children = sorted(directory_node.Query(filter_string=filter_string))
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

    for fd in children[start_row:end_row]:
      self.AddCell(row_index, "Name", fd.urn.RelativeName(directory_node.urn))

      # Add the fd to all the columns
      for column in self.columns:
        # This sets AttributeColumns directly from their fd.
        if isinstance(column, renderers.AttributeColumn):
          column.AddRowFromFd(row_index, fd)

      # We use the timestamp on the TYPE as a proxy for the last update time
      # of this object - its only an estimate.
      fd_type = fd.Get(fd.Schema.TYPE)
      if fd_type:
        self.AddCell(row_index, "Age", aff4.RDFDatetime(fd_type.age))

      if "Container" in fd.behaviours:
        self.AddCell(row_index, "Icon", "directory")
      else:
        self.AddCell(row_index, "Icon", "file")

      row_index += 1
      if row_index > end_row:
        return


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
    aff4_root = aff4.RDFURN(request.REQ.get("aff4_root", client_id))

    # Path is relative to the aff4 root specified.
    urn = aff4_root.Add(path)

    # Open the client
    try:
      directory = aff4.FACTORY.Open(urn, token=request.token)
      # Query for those objects immediately related to our urn.
      children = directory.OpenChildren()
      try:
        self.message = "Directory %s Last retrieved %s" % (
            urn, directory.Get(directory.Schema.TYPE).age)
      except AttributeError:
        pass

      # Now we only want the unique directory like children.
      directory_like = set()
      for child in children:
        if "Container" in child.behaviours:
          directory_like.add(child.urn.RelativeName(urn))

      # This actually sorts by the URN (which is UTF8) - I am not sure about the
      # correct sorting order for unicode string?
      for d in sorted(directory_like):
        self.AddElement(d)

    except IOError, e:
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
<div id="toolbar_{{unique|escape}}" class="toolbar">
  <button id='rweowned' title='Is this machine pwned?'>
    <img src='/static/images/stock_dialog_question.png' class='toolbar_icon'>
  </button>
  <div id='rweowned_dialog'></div>
  <button id='refresh_{{unique|escape}}'
    title='Refresh this directory listing.'>
    <img src='/static/images/stock_refresh.png' class='toolbar_icon'>
  </button>
  <div id='refresh_action'></div>

  {% for path, fullpath, fullpath_id, i in this.paths %}
  <button id='path_{{i|escape}}'>{{path|escape}}</button>
  {% endfor %}
</div>

<script>
$('#refresh_{{unique|escapejs}}').button().click(function (){
  $('#refresh_{{unique|escapejs}}').button('disable');
  grr.layout("UpdateAttribute", "refresh_action", {
   aff4_path: "{{this.aff4_path|escapejs}}",
   attribute: "aff4:contains"
  });
});

$('#rweowned').button().click(function (){
  grr.layout("RWeOwned", "rweowned_dialog");
AttributeUpdated});

grr.dialog("RWeOwned", "rweowned_dialog", "rweowned", {
     width: "500px", height: "auto",
     title: "Is this machine pwned?",
});

// When the attribute is updated, refresh the views
grr.subscribe("AttributeUpdated", function(path, attribute) {
  if (attribute == "aff4:contains") {
    // Update the table
    grr.publish("tree_select", path);
    grr.publish("file_select", path);
  };
}, 'refresh_{{unique|escapejs}}');

{% for path, fullpath, fullpath_id, i in this.paths %}
$('#path_{{i|escapejs}}').button().click(function () {
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

    client_urn = aff4.RDFURN(client_id)

    self.paths = [("/", client_urn, "_", 0)]
    for path in aff4.RDFURN(self.aff4_path).Split()[1:]:
      previous = self.paths[-1]
      fullpath = client_urn.Add(previous[1].Add(path))

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
    self.aff4_type = request.REQ.get("aff4_type")
    self.flow_urn = request.REQ.get("flow_urn")
    # Refresh the contains attribute
    self.attribute_to_refresh = request.REQ.get(
        "attribute", str(aff4.AFF4Volume.SchemaCls.CONTAINS))

  def Layout(self, request, response):
    """Render the toolbar."""
    self.ParseRequest(request)

    fd = aff4.FACTORY.Open(self.aff4_path, mode="rw", token=request.token)
    if self.aff4_type:
      fd = fd.Upgrade(self.aff4_type)

    # Account for implicit directories.
    if fd.Get(fd.Schema.TYPE) is None:
      self.aff4_type = "VFSDirectory"

    self.flow_urn = fd.Update(self.attribute_to_refresh)
    if self.flow_urn:
      return super(UpdateAttribute, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Continue polling as long as the flow is in flight."""
    super(UpdateAttribute, self).RenderAjax(request, response)
    complete = False
    self.ParseRequest(request)

    # Check if the flow is still in flight.
    try:
      switch = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN, token=request.token)
      flow_obj = switch.OpenMember(self.flow_urn)
      flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB)
      if flow_pb and flow_pb.data.state != jobs_pb2.FlowPB.RUNNING:
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
    if not self.aff4_path: return

    try:
      fd = aff4.FACTORY.Open(self.aff4_path, token=request.token)
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
  description = "Browse Virtual Filesystem"

  left_renderer = "FileSystemTree"
  top_right_renderer = "FileTable"
  bottom_right_renderer = "FileViewTabs"


class DownloadView(renderers.TemplateRenderer):
  """Renders a download page."""

  layout_template = renderers.Template("""
<h1>{{ this.path|escape }}</h1>
<div id="{{ unique|escape }}_action"></div>
{% if this.age_int %}
<div id="{{ id|escape }}_download">
Last downloaded on {{ this.age|escape }}.<br>
{% endif %}
{% if this.hash %}
Hash was {{ this.hash|escape }}.
{% endif %}
{% if this.file_exists %}
<p>
<button id="{{ unique|escape }}_2">
 Download ({{this.size|escape}} bytes)
</button>
</p>
{% endif %}

<button id="{{ unique|escape }}">Get a new Version</button>
<form id="{{unique|escape}}_3" action="/render/Download/DownloadView"
   METHOD=post target='_blank'>
<input type=hidden name='aff4_path' value='{{this.aff4_path|escape}}'>
<input type=hidden name='reason' value='{{this.token.reason|escape}}'>
<input type=hidden name='client_id' value='{{this.client_id|escape}}'>
</form>
</div>
<script>
  var button = $("#{{ unique|escapejs }}").button();

  button.click(function () {
    $('#{{unique|escapejs}}').button('disable');
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

  button = $("#{{ unique|escapejs }}_2");
  if (button) {
    button.button().
    click(function () {
      $('#{{unique|escapejs}}_3').submit();
    });
  };
</script>""")

  error_template = renderers.Template("""
<h1>Error</h1>{{this.urn|escape}} does not appear to be a file object.
""")

  def Layout(self, request, response):
    """Present a download form."""
    self.client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", self.client_id)

    self.token = request.token

    try:
      fd = aff4.FACTORY.Open(self.aff4_path, token=request.token)
      self.path = fd.urn
      self.hash = fd.Get(fd.Schema.HASH, None)
      self.size = fd.Get(fd.Schema.SIZE)

      if self.hash:
        self.age = self.hash.age
      elif self.size > 0:
        self.age = self.size.age

      else: self.age = 0

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

    self.token = request.token

    if self.aff4_path:

      def Generator():
        fd = aff4.FACTORY.Open(self.aff4_path, token=request.token)

        while True:
          data = fd.Read(1000000)
          if not data: break

          yield data

      response = http.HttpResponse(content=Generator(),
                                   mimetype="binary/octet-stream")

      # This must be a string.
      response["Content-Disposition"] = (
          "attachment; filename=%s.noexec" % os.path.basename(
              utils.SmartStr(self.aff4_path)))

      return response


class AFF4Stats(renderers.TemplateRenderer):
  """Show stats about the currently selected AFF4 object.

  Post Parameters:
    - aff4_path: The aff4 path to update the attribute for.
  """

  # This renderer applies to this AFF4 type
  name = "Stats"
  css_class = ""
  historical_renderer = "HistoricalView"
  filtered_attributes = None

  layout_template = renderers.Template("""
<div id="{{unique|escape}}" class="{{this.css_class}}">
<h3>{{ this.path|escape }}</h3>
<table id='{{ unique|escape }}' class="display">
<thead>
<tr>
  <th class="ui-state-default" style="width: 20ex">Attribute</th>
  <th class="ui-state-default">Value</th>
  <th class="ui-state-default" style="width: 20ex">Age</th>
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

  def FindRendererForObject(self, rdf_obj):
    """Find the appropriate renderer for the class name."""
    for cls in self.classes.values():
      try:
        if cls.ClassName == rdf_obj.__class__.__name__:
          return cls(rdf_obj)
      except AttributeError:
        pass

    # Default renderer.
    return renderers.RDFValueRenderer(rdf_obj)

  def Layout(self, request, response):
    """Introspect the Schema for each object."""
    # Allow derived classes to just set the urn directly
    self.client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", self.client_id)
    if not self.aff4_path: return

    try:
      # Get all the versions of this file.
      self.fd = aff4.FACTORY.Open(self.aff4_path, token=request.token,
                                  age=aff4.ALL_TIMES)
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

    for schema in fd.SchemaCls.__mro__:
      attributes = []

      for name, attribute in sorted(schema.__dict__.items()):
        if not isinstance(attribute, aff4.Attribute): continue

        # If we already showed this attribute we move on
        if attribute.predicate in attribute_names: continue

        values = list(fd.GetValuesForAttribute(attribute))
        multi = len(values) > 1
        if values:
          attribute_names.add(attribute.predicate)
          value_renderer = self.FindRendererForObject(values[0])
          if self.filtered_attributes and name not in self.filtered_attributes:
            continue

          attributes.append((name, attribute.description,

                             # This is assumed to be in safe RawHTML and not
                             # escaped.
                             value_renderer.RawHTML(request),
                             aff4.RDFDatetime(values[0].age), multi))

      if attributes:
        name = ", ".join([cls.__name__ for cls in schema.FindAFF4Class()])
        classes.append((name, attributes))

    return classes


class HostInformation(AFF4Stats):
  """View information about the host."""
  description = "Host Information"
  behaviours = frozenset(["Host"])
  css_class = "TableBody"
  filtered_attributes = ["USERNAMES", "HOSTNAME", "MAC_ADDRESS"]

  def Layout(self, request, response):
    self.client_id = request.REQ.get("client_id")
    self.urn = aff4.RDFURN(self.client_id)

    # This verifies we have auth for deep client paths. If this raises, we
    # force the auth screen.
    aff4.FACTORY.Open(aff4.RDFURN(self.urn).Add("CheckAuth"),
                      token=request.token, mode="r")

    return super(HostInformation, self).Layout(request, response)


class FileViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected file.

  Listening Javascript Events:
    - file_select(aff4_path) - A selection event on the file table informing us
      of a new aff4 file to show. We redraw the entire tab notbook on this new
      aff4 object, maintaining the currently selected tab.

  Internal State:
    - aff4_path - The AFF4 object we are currently showing.
  """
  # When a message appears on this queue we reset to the first tab
  event_queue = "file_select"

  names = ["Stats", "Download", "TextView", "HexView"]
  delegated_renderers = ["AFF4Stats", "DownloadView", "FileTextViewer",
                         "FileHexViewer"]
  disabled = []

  # When a new file is selected we switch to the first tab.
  layout_template = renderers.TabLayout.layout_template + """
<script>
grr.subscribe("{{ this.event_queue|escapejs }}", function(aff4_path) {
  grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}",
    {aff4_path: aff4_path})
}, 'tab_contents_{{unique|escapejs}}');

// Disable the tabs which need to be disabled.
$("li a").addClass("ui-state-enabled").removeClass("ui-state-disabled");

{% for disabled in this.disabled %}
$("li a[renderer={{disabled|escapejs}}]").removeClass(
   "ui-state-enabled").addClass("ui-state-disabled");
{% endfor %}
</script>
"""

  def Layout(self, request, response):
    """Check if the file is a readable and disable the tabs."""
    client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", client_id)
    self.state = dict(aff4_path=self.aff4_path)

    data = None
    try:
      fd = aff4.FACTORY.Open(self.aff4_path, token=request.token)
      # We just check if the object has a read method.
      data = fd.Read
    except (IOError, AttributeError):
      pass

    if data is None:
      self.disabled = ["DownloadView", "FileHexViewer", "FileTextViewer"]

    return super(FileViewTabs, self).Layout(request, response)


class RWeOwned(renderers.TemplateRenderer):
  """A magic 8 ball reply to the question - Are we Owned?"""

  layout_template = renderers.Template("<h1>{{this.choice|escape}}</h1>")

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

  def __init__(self):
    super(HistoricalView, self).__init__()

    self.AddColumn(renderers.RDFValueColumn("Age"))

  def Layout(self, request, response):
    """Add the columns to the table."""
    client_id = request.REQ.get("client_id")
    if client_id is None:
      raise RuntimeError("Expected client_id")

    client_urn = aff4.RDFURN(client_id)
    path = request.REQ.get("path", "/")

    # Path is relative
    urn = client_urn.Add(path)

    # Pass the urn to our render method.
    self.state["urn"] = utils.SmartStr(urn)
    self.state["attribute"] = request.REQ.get("attribute")

    self.AddColumn(renderers.RDFValueColumn(self.state["attribute"]))

    return super(HistoricalView, self).Layout(request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table with attribute values."""
    # Path is relative
    urn = request.REQ.get("urn")
    attribute_name = request.REQ.get("attribute")

    if attribute_name is None:
      return

    self.AddColumn(renderers.RDFValueColumn(attribute_name))
    fd = aff4.FACTORY.Open(urn, token=request.token, age=aff4.ALL_TIMES)
    self.BuildTableFromAttribute(attribute_name, fd, start_row, end_row)

  def BuildTableFromAttribute(self, attribute_name, fd, start_row, end_row):
    """Build the table for the attribute."""
    attribute = getattr(fd.Schema, attribute_name)

    i = 0
    for i, value in enumerate(fd.GetValuesForAttribute(attribute)):
      if i > end_row: break
      if i < start_row: continue

      self.AddCell(i, "Age", aff4.RDFDatetime(value.age))
      self.AddCell(i, attribute_name, value)

    self.size = i + 1
