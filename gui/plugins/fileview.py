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

import json
import os
import random
import re
import socket
import stat
import time

from django import http
from django import template
from M2Crypto import X509

from grr.gui import renderers
from grr.lib import aff4
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

  translator = dict(st_mtime=renderers.RDFProtoRenderer.Time32Bit,
                    st_atime=renderers.RDFProtoRenderer.Time32Bit,
                    st_ctime=renderers.RDFProtoRenderer.Time32Bit,
                    st_mode=Translate_st_mode)


class DirectoryInodeRenderer(StatEntryRenderer):
  """Nicely format Directory Inode listing."""
  ClassName = "DirectoryInode"
  name = "Directory Listing"

  dir_template = template.Template("""
<table class='proto_table'>
<thead>
<tr><th>Mode</th><th>Name</th><th>Size</th><th>Modified</th></tr>
</thead>
<tbody>
  {% for row in data %}
    <tr>
    {% for value in row %}
      <td class="proto_value">
        {% autoescape off %}
        {{value}}
        {% endautoescape %}
      </td>
    {% endfor %}
    </tr>
  {% endfor %}
</tbody>
</table>
""")

  def Layout(self, _, response):
    """Render directories as a table."""
    result = []
    fields = "st_mode path st_size st_mtime".split()
    children = self.proxy.data.children
    for child in children:
      row = []
      for name in fields:
        value = getattr(child, name)
        try:
          value = self.translator[name](self, None, value)
        except KeyError: pass
        row.append(value)

      result.append(row)

    return self.RenderFromTemplate(self.dir_template, response, data=result)


class UserEntryRenderer(renderers.RDFProtoArrayRenderer):
  ClassName = "User"
  name = "User Record"

  translator = dict(last_logon=renderers.RDFProtoRenderer.Time)


class InterfaceRenderer(renderers.RDFProtoArrayRenderer):
  """Render a machine's interfaces."""
  ClassName = "Interface"
  name = "Interface Record"

  def TranslateIpAddress(self, _, value):
    return socket.inet_ntop(socket.AF_INET, value)

  def TranslateMacAddress(self, _, value):
    return ":".join([x.encode("hex") for x in value])

  translator = dict(ip_address=TranslateIpAddress,
                    mac_address=TranslateMacAddress)


class ProcessRenderer(renderers.RDFProtoArrayRenderer):
  """Renders process listings."""
  ClassName = "Processes"
  name = "Process Listing"

  translator = dict(ctime=renderers.RDFProtoRenderer.Time32Bit)


class FilesystemRenderer(renderers.RDFProtoArrayRenderer):
  ClassName = "FileSystem"
  name = "FileSystems"


class CertificateRenderer(renderers.RDFValueRenderer):
  """Render X509 Certs properly."""
  ClassName = "RDFX509Cert"
  name = "X509 Certificate"

  template = template.Template("""
<pre>
{{ value }}
</pre>
""")

  def Layout(self, _, response):
    # Present the certificate as text
    cert = X509.load_cert_string(str(self.proxy))

    return self.RenderFromTemplate(
        self.template, response, name=self.name, value=cert.as_text(),
        id=renderers.GetNextId())


class BlobArrayRenderer(renderers.RDFValueRenderer):
  """Render a blob array."""
  ClassName = "BlobArray"
  name = "Array"

  layout_template = template.Template("""
{% for i in first %}
{{i}}
{% endfor %}
{% for i in array %}
, {{i}}
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


class FileTable(renderers.TableRenderer):
  """A table that displays the content of a directory."""

  # We receive change path events from this queue
  event_queue = "tree_select"
  # Set the first column to be zero width
  table_options = {
      "aoColumnDefs": [
          {"sWidth": "1px", "aTargets": [0]}
          ],
      "bAutoWidth": False,
      "table_hash": "tb",
      "sSearch": "Search",
      "oFeatures": {"bFilter": True},
      }

  # We publish selected paths to this queue
  selection_publish_queue = "file_select"
  format = template.Template("""
<"TableHeader"<"H"lrp>><"TableBody_{{unique}}"t><"TableFooter"<"F"pf>>""")

  # Subscribe for the event queue and when events arrive refresh the
  # table.
  vfs_table_template = template.Template("""<script>
  // Update the table when the tree changes
  grr.subscribe("{{ event_queue|escapejs }}", function(path, selected_id,
    update_hash) {
          grr.state.path = path;

          //Redraw the table
          grr.redrawTable("table_{{unique}}");

          // Update the toolbar
          grr.layout("Toolbar", "toolbar_{{unique}}");

          // If the user really clicked the tree, we reset the hash
          if (update_hash != 'no_hash') {
            grr.publish('hash_state', 'tb', undefined);
          }
      }, 'table_{{ unique }}');

  //Receive the selection event and emit a path
  grr.subscribe("table_selection_{{ id|escapejs }}", function(node) {
    var path = grr.state.path || "";
    if (node) {
      var element = node.find("span")[0];
      if (element) {
        var filename = element.innerHTML;
        grr.publish("{{ selection_publish_queue|escapejs }}",
                     path + "/" + filename);
      };
    };
  }, 'table_{{ unique }}');
  grr.layout("Toolbar", "toolbar_{{unique}}");

  $(".TableBody_{{unique}}").addClass("TableBody");

   </script>""")

  def __init__(self):
    super(FileTable, self).__init__()

    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer))
    self.AddColumn(renderers.RDFValueColumn(
        "Name", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.AttributeColumn("type"))
    self.AddColumn(renderers.AttributeColumn("size"))
    self.AddColumn(renderers.RDFValueColumn("Age"))

  def Layout(self, request, response):
    """The table lists files in the directory and allow file selection."""
    response = super(FileTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.vfs_table_template, response,
        id=self.id, event_queue=self.event_queue, unique=self.unique,
        selection_publish_queue=self.selection_publish_queue,
        )

  def BuildTable(self, start_row, end_row, request):
    """Populate the table."""
    sort_direction = request.REQ.get("sSortDir_0", "asc") == "desc"
    filter_term = request.REQ.get("sSearch")

    # For now we just list the directory
    try:
      # TODO(user): Think about permission for access to this client
      client_id = request.REQ.get("client_id")
      client_urn = aff4.RDFURN(client_id)
      path = request.REQ.get("path", "/")

      # Path is relative
      urn = client_urn.Add(path)

      # Open the client
      directory_node = aff4.FACTORY.Open(urn)
      if not directory_node:
        raise IOError()

      children, age = directory_node.ListChildren()
      self.message = "Directory Listing '%s' was taken on %s" % (
          path, aff4.RDFDatetime(age))
    except IOError:
      children = {}
      age = 0

    child_names = [k.RelativeName(urn) for k, _ in children.items()]
    if filter_term:
      try:
        filter_term = re.compile(filter_term, re.I)
        child_names = [c for c in child_names if filter_term.search(c)]
      except re.error:
        child_names = [c for c in child_names if filter_term in c]

    child_names.sort(reverse=sort_direction)

    row_index = start_row

    # Make sure the table knows how large it is for paging.
    self.size = len(child_names)

    if children:
      for fd in directory_node.OpenChildren(
          children=child_names[start_row:end_row]):
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


class FileSystem(renderers.TreeRenderer):
  """A FileSystem navigation Tree."""

  renderer_template = template.Template("""
<script>
grr.grrTree("{{ renderer }}", "{{ id }}",
            "{{ publish_select_queue }}", {{ state|escapejs }},
            function (data, textStatus, jqXHR) {
              if (!data.id) return;

              if (data.message) {
                // Publish the message if it exist
                grr.publish('grr_messages', data.message);
              };
             });
</script>""")

  def RenderAjax(self, request, response):
    """Renders tree leafs for filesystem path."""
    response = super(FileSystem, self).RenderAjax(request, response)

    result = []

    # TODO(user): Think about permission for access to this client
    client_urn = aff4.RDFURN(request.REQ["client_id"])

    # Path is relative
    urn = client_urn.Add(request.REQ.get("path", ""))

    # Open the client
    try:
      client = aff4.FACTORY.Open(urn)
      children, age = client.ListChildren()
      message = "Directory %s Last retrieved %s" % (urn, aff4.RDFDatetime(age))

      # Now we only want the directory like children.
      directory_like = []
      for name in children:
        cls = aff4.AFF4Volume.classes[children[name]]
        if "Container" in cls.behaviours:
          directory_like.append(name)

      # This actually sorts by the URN (which is UTF8) - I am not sure about the
      # correct sorting order for unicode string?
      directory_like.sort(key=str)

      for d in directory_like:
        result.append(
            dict(data=d.RelativeName(urn),
                 attr=dict(id=renderers.DeriveIDFromPath(
                     d.RelativeName(client_urn))),
                 children=[],
                 state="closed"))
    except IOError, e:
      message = "Error fetching %s: %s" % (urn, e)

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(dict(data=result, message=message,
                                                 id=self.id)),
                             mimetype="application/json")


class CheckFreshness(renderers.Renderer):
  """Checks if the AFF4 object needs refreshing."""

  def RenderAjax(self, request, _):
    """The browser polls this function to see if the path is fresh."""
    client_instruction = "stop"

    path = request.REQ.get("path")
    if path:
      try:
        freshness = int(request.REQ.get("freshness", 3000))
        acceptable_age = (time.time() - freshness) * 1000000

        fd = aff4.FACTORY.Open(path)
        _, age = fd.ListChildren()

        # Directory listing is still too old
        if age < acceptable_age:
          client_instruction = "poll"
      except IOError:
        client_instruction = "error"

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(client_instruction),
                             mimetype="application/json")


class Toolbar(renderers.Renderer):
  """A navigation enhancing toolbar."""

  template = template.Template("""
<button id='rweowned' title='Is this machine pwned?'>
  <img src='/static/images/stock_dialog_question.png' class='toolbar_icon'>
</button>
<div id='rweowned_dialog'></div>
<button id='refresh_{{unique}}' title='Refresh this directory listing.'>
  <img src='/static/images/stock_refresh.png' class='toolbar_icon'>
</button>
<div id='refresh_action'></div>
{% for path, fullpath, fullpath_id, i in paths %}
<button id='path_{{i}}'>{{path}}</button>
{% endfor %}
<script>
$('#refresh_{{unique}}').button().click(function (){
  $('#refresh_{{unique}}').button('disable');
  grr.layout("UpdateAttribute", "refresh_action", {
   path: "{{base_path}}",
   attribute: "aff4:directory_listing",
   client_id: grr.state.client_id,
  });
});

$('#rweowned').button().click(function (){
  grr.layout("RWeOwned", "rweowned_dialog");
});

grr.dialog("RWeOwned", "rweowned_dialog", "rweowned", {
     width: "500px",
     title: "Is this machine pwned?",
});

// When the attribute is updated, refresh the views
grr.subscribe("AttributeUpdated", function(path, attribute) {
  if (attribute == "aff4:directory_listing") {
    // Update the table
    grr.publish("tree_select", path);
    grr.publish("file_select", path);
  };
}, 'refresh_{{unique}}');

{% for path, fullpath, fullpath_id, i in paths %}
$('#path_{{i}}').button().click(function () {
   grr.publish("tree_select", "{{ fullpath }}");
   grr.publish("file_select", "{{ fullpath }}");
   grr.publish("hash_state", "t", "{{ fullpath_id }}");
});
{% endfor %}
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    response = super(Toolbar, self).Layout(request, response)
    client_id = request.REQ.get("client_id")
    fd = aff4.FACTORY.Open(client_id)

    path = request.REQ.get("path", "/")
    urn = aff4.RDFURN(client_id).Add(path)

    paths = [("/", "", "_", 0)]
    for path in urn.RelativeName(fd.urn).split("/"):
      if not path: continue
      previous = paths[-1]
      fullpath = previous[1] + "/" + path

      paths.append((path, fullpath,
                    renderers.DeriveIDFromPath(fullpath), previous[3] + 1))

    return self.RenderFromTemplate(
        self.template, response, paths=paths,
        client=client_id, base_path=urn,
        unique=self.unique, id=self.id)


class UpdateAttribute(renderers.Renderer):
  """Reloads a directory listing from client."""

  template = template.Template("""
<script>
  grr.poll('{{renderer}}', '{{id}}', function (data) {
  if (!data || !data.complete) {
    return true;
  } else {
    grr.publish("AttributeUpdated", "{{fullpath}}", "{{attribute}}");
  };
}, 10, {'flow_urn': '{{flow_urn}}'}, 'json');
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    response = super(UpdateAttribute, self).Layout(request, response)

    client_id = request.REQ.get("client_id")
    path = request.REQ.get("path", "/")
    aff4_type = request.REQ.get("aff4_type")

    # Open the client
    fullpath = aff4.RDFURN(client_id).Add(path)

    fd = aff4.FACTORY.Open(fullpath)
    if aff4_type:
      fd = fd.Upgrade(aff4_type)

    # Refresh the contains attribute
    attribute_to_refresh = request.REQ.get("attribute",
                                           str(aff4.AFF4Volume.Schema.CONTAINS))

    attribute_to_refresh = fd.Schema.GetAttribute(
        attribute_to_refresh)

    user = request.META.get("REMOTE_USER")
    flow_urn = fd.Update(attribute_to_refresh, user=user)
    if flow_urn:
      return self.RenderFromTemplate(
          self.template, response,
          renderer=self.__class__.__name__,
          fullpath=fullpath, flow_urn=flow_urn,
          attribute=attribute_to_refresh,
          unique=self.unique, id=self.id)

  def RenderAjax(self, request, response):
    """Continue polling as long as the flow is in flight."""
    super(UpdateAttribute, self).RenderAjax(request, response)
    response = dict(complete=0)

    # Check if the flow is still in flight.
    flow_urn = request.REQ.get("flow_urn")
    if flow_urn == "None":
      response["complete"] = 1

    elif flow_urn:
      flow_obj = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN.Add(flow_urn))
      flow_pb = flow_obj.Get(flow_obj.Schema.FLOW_PB)
      if flow_pb and flow_pb.data.state != jobs_pb2.FlowPB.RUNNING:
        response["complete"] = 1

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(response),
                             mimetype="application/json")


class HexView(renderers.TableRenderer):
  """Display a HexView of a file."""
  # How many bytes we write to each row
  row_size = 48

  def __init__(self):
    super(HexView, self).__init__([
        renderers.HexColumn("Offset"),
        renderers.StringColumn("Hex", cls="monospace"),
        renderers.StringColumn("ASCII", cls="monospace"),
        ])

  def Layout(self, request, response):
    path = request.REQ.get("path", "/")
    path = "/etc/passwd"

    # Only show something here if it is not a directory
    statinfo = os.stat(path)
    if stat.S_ISDIR(statinfo.st_mode):
      return

    return renderers.TableRenderer.Layout(self, request, response)

  def RenderAjax(self, request, response):
    """Renders the HexTable."""
    path = request.REQ.get("path", "/")
    client_id = request.REQ.get("client_id", "/")

    try:
      fd = aff4.FACTORY.Open(aff4.RDFURN(client_id).Add(path))
    except (IOError, OSError):
      return

    start_row = int(request.REQ.get("iDisplayStart", 0))
    limit_row = int(request.REQ.get("iDisplayLength", 10))

    # How large is the file? (How many rows)
    fd.seek(0, 2)
    self.size = fd.tell() / self.row_size + 1

    row_count = 0
    fd.seek(start_row * self.row_size)
    while row_count < limit_row:
      offset = fd.tell()
      row = fd.read(self.row_size)
      if not row: break

      row_count += 1
      self.AddRow(dict(
          Offset=offset,
          Hex="".join(["%02X" % ord(x) for x in row]),
          # Filter non printables (Replace with .)
          ASCII="".join(
              [x if ord(x) > 32 and ord(x) < 127 else "." for x in row]
              )
          ), row_index=start_row + row_count)

    # Call our superclass to complete this
    return renderers.TableRenderer.RenderAjax(self, request, response)


class VirtualFileSystemView(renderers.Splitter):
  """This is the main view to browse files."""
  category = "Inspect Client"
  description = "Browse Virtual Filesystem"

  search_client_template = template.Template("""
<h1 id="{{unique}}">Select a client</h1>
Please search for a client above.

<script>
   grr.subscribe("client_selection", function (cn) {
      grr.layout("{{renderer}}", "{{id}}", {client_id: cn});
   }, "{{unique}}");
</script>
""")

  def __init__(self):
    self.left_renderer = "FileSystem"
    self.top_right_renderer = "FileTable"
    self.bottom_right_renderer = "FileViewTabs"

    super(VirtualFileSystemView, self).__init__()

  def Layout(self, request, response):
    """Show the main view only if we have a client_id."""
    renderers.Renderer.Layout(self, request, response)

    client_id = request.REQ.get("client_id")
    if not client_id:
      return self.RenderFromTemplate(
          self.search_client_template, response,
          renderer=self.__class__.__name__, unique=self.unique, id=self.id)

    return super(VirtualFileSystemView, self).Layout(request, response)


class DownloadView(renderers.Renderer):
  """Renders a download page."""

  # The queue we should subscribe to
  subscribe_queue = "file_select"

  template = template.Template("""
<h1>{{ fullpath }}</h1>
<div id="{{ unique }}_action"></div>
{% if age_int %}
<div id="{{ id }}_download">
Last downloaded on {{ age }}.<br>
{% endif %}
{% if hash %}
Hash was {{ hash }}.
{% endif %}
{% if age_int %}
<p>
<button id="{{ unique }}_2">Download</button>
</p>
{% endif %}

<button id="{{ unique }}">Get a new Version</button>
<form id="{{unique}}_3" action="/render/Download/DownloadView" target='_blank'>
<input type=hidden name='fullpath' value='{{fullpath}}'>
</form>
</div>
<script>
  var button = $("#{{ unique }}").button();

  button.click(function () {
    $('#{{unique}}').button('disable');
    grr.layout("UpdateAttribute", "{{unique}}_action", {
      'attribute': 'aff4:content',
      'aff4_type': 'VFSFile',
      'path': '{{fullpath}}',
      client_id: grr.state.client_id,
    });
  });

  // When the attribute is updated, refresh the views
  grr.subscribe("AttributeUpdated", function(path, attribute) {
    if (attribute == "aff4:content") {
      // Update the download screen
      var tab = $('#{{tab}}');
      tab.tabs("load", tab.tabs('option', 'selected'));
    };
  }, '{{unique}}_action');

  button = $("#{{ unique }}_2");
  if (button) {
    button.button().
    click(function () {
      $('#{{unique}}_3').submit();
    });
  };
</script>""")

  def GetFullPath(self, request):
    client_id = request.REQ.get("client_id")
    path = request.REQ.get("file_view_path", "/")
    return aff4.RDFURN(client_id).Add(path)

  def Layout(self, request, response):
    """Present a download form."""
    response = super(DownloadView, self).Layout(request, response)
    fullpath = self.GetFullPath(request)

    tab = request.REQ.get("tab", "unknown")

    fd = aff4.FACTORY.Open(fullpath)
    try:
      sha_hash = fd.Get(fd.Schema.HASH)
      size = fd.Get(fd.Schema.SIZE)
      if sha_hash:
        age = aff4.RDFDatetime(sha_hash.age)
      else: age = 0
    except AttributeError:
      return self.FormatFromString("<h1>Error</h1>{{urn}} does not "
                                   "appear to be a file object.", urn=fullpath)

    return self.RenderFromTemplate(
        self.template, response, renderer=self.__class__.__name__,
        fullpath=fullpath, tab=tab,
        age_int=int(age), id=self.id, unique=self.unique, age=age,
        size=size, hash=sha_hash)

  def Download(self, request, _):
    """Stream the file into the browser."""
    # Open the client
    fullpath = request.REQ.get("fullpath")
    if fullpath:

      def Generator():
        fd = aff4.FACTORY.Open(fullpath)

        while True:
          data = fd.Read(1000000)
          if not data: break

          yield data

      response = http.HttpResponse(content=Generator(),
                                   mimetype="binary/octet-stream")

      # This must be a string.
      response["Content-Disposition"] = (
          "attachment; filename=%s.noexec" % os.path.basename(
              utils.SmartStr(fullpath)))

      return response


class AFF4Stats(renderers.Renderer):
  """Show stats about the currently selected AFF4 object."""

  # This renderer applies to this AFF4 type
  aff4_type = "AFF4Object"
  name = "Stats"

  layout_template = template.Template("""
<div>
<h3>{{ path }}</h3>
<table id='{{ unique }}' class="display">
<thead>
<tr>
  <th class="ui-state-default" style="width: 20ex">Attribute</th>
  <th class="ui-state-default">Value</th>
  <th class="ui-state-default" style="width: 20ex">Age</th>
</tr>
</thead>
<tbody>
{% for name, attributes in classes %}
 <tr>
   <td colspan=3 class="grr_aff4_type_header"><b>{{ name }}</b></td>
 </tr>
 {% for attribute, description, value, age in attributes %}
 <tr>
   <td><b title='{{ description }}'> {{ attribute }} </b></td>
{% autoescape off %}
   <td>{{ value }}</td>
   <td>{{ age }}</td>
{%endautoescape %}
 </tr>
 {% endfor %}
{% endfor %}
</tbody>
</table>
</div>
<script>
  $('#{{ unique }} [title]').tooltip();
</script>
""")

  def FindRendererForObject(self, rdf_obj):
    """Find the appropriate renderer for the class name."""
    for cls in self.classes.values():
      try:
        if cls.ClassName == rdf_obj.__class__.__name__:
          return cls(rdf_obj)
      except AttributeError: pass

    # Default renderer.
    return renderers.RDFValueRenderer(rdf_obj)

  def Layout(self, request, response):
    """Introspect the Schema for each object."""
    response = super(AFF4Stats, self).Layout(request, response)
    path = request.REQ.get("file_view_path", "/")
    client_id = request.REQ.get("client_id")
    if not client_id: return

    fd = aff4.FACTORY.Open(aff4.RDFURN(client_id).Add(path))
    classes = self.RenderAFF4Attributes(fd, request)

    return self.RenderFromTemplate(
        self.layout_template,
        response, classes=classes, id=self.id, unique=self.unique,
        path=fd.urn)

  def RenderAFF4Attributes(self, fd, request=None):
    """Returns attributes rendered by class."""
    classes = []
    for cls in fd.__class__.__mro__:
      try:
        schema = cls.Schema
      except AttributeError: continue

      attributes = []

      for name, attribute in schema.__dict__.items():
        if not isinstance(attribute, aff4.Attribute): continue
        value = fd.Get(attribute)
        if value:
          value_renderer = self.FindRendererForObject(value)
          attributes.append((name, attribute.description,
                             value_renderer.RawHTML(request),
                             aff4.RDFDatetime(value.age)))

      if attributes:
        classes.append((cls.__name__, attributes))

    return classes


class FileViewTabs(renderers.TabLayout):
  """Show a tabset to inspect the selected file."""
  # When a message appears on this queue we reset to the first tab
  event_queue = "file_select"

  aff4_renderers = [AFF4Stats, DownloadView]

  names = ["Stats", "Download"]
  renderers = ["AFF4Stats", "DownloadView"]

  # When a new file is selected we switch to the first tab
  file_tab_layout_template = template.Template("""
<script>
grr.subscribe("{{ event_queue|escapejs }}", function(path) {
  grr.state.file_view_path = path;
  grr.layout('{{ renderer }}', '{{ id }}');
}, 'tab_container_{{ unique }}');
</script>
""")

  def Layout(self, request, response):
    """Automatically assemble tabs bases on the object type."""

    response = super(FileViewTabs, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.file_tab_layout_template,
        response, unique=self.unique,
        event_queue=self.event_queue,
        renderer=self.__class__.__name__,
        id=self.id)


class RWeOwned(renderers.Renderer):
  """A magic 8 ball reply to the question - Are we Owned?"""

  def Layout(self, request, response):
    """Render a magic 8 ball easter-egg."""
    response = super(RWeOwned, self).Layout(request, response)
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

    response.write("<h1>%s</h1>" %
                   options[random.randint(0, len(options) - 1)])

    return response
