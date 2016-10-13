#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
"""This plugin renders the filesystem in a tree and a table."""

import cgi
import os
import socket

from django import http

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard as aff4_standard


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
<button id="{{ unique|escape }}_2" class="btn btn-default">
 Download ({{this.size|escape}} bytes)
</button>
</p>
<p>or download using command line export tool:</p>
<pre>
{{ this.export_command_str|escape }}
</pre>
<hr/>
{% endif %}
<button id="{{ unique|escape }}" class="btn btn-default">
  Get a new Version
</button>
</div>
""")

  error_template = renderers.Template("""
<div class="alert alert-danger alert-block">
  <h4>Error!</h4> {{this.path|escape}} does not appear to be a file object.
  <p><em>{{this.error_message|escape}}</em></p>
</div>
""")
  bad_extensions = [
      ".bat", ".cmd", ".exe", ".com", ".pif", ".py", ".pl", ".scr", ".vbs"
  ]

  def Layout(self, request, response):
    """Present a download form."""
    self.age = rdfvalue.RDFDatetime(request.REQ.get("age"))

    client_id = request.REQ.get("client_id")
    aff4_path = request.REQ.get("aff4_path", client_id)

    try:
      fd = aff4.FACTORY.Open(aff4_path, token=request.token, age=self.age)
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

      self.export_command_str = u" ".join([
          config_lib.CONFIG["AdminUI.export_command"], "--username",
          utils.ShellQuote(request.token.username), "file", "--path",
          utils.ShellQuote(aff4_path), "--output", "."
      ])

      response = super(DownloadView, self).Layout(request, response)
      return self.CallJavascript(
          response,
          "DownloadView.Layout",
          aff4_path=aff4_path,
          client_id=client_id,
          age_int=int(self.age),
          file_exists=self.file_exists,
          renderer=self.__class__.__name__,
          reason=request.token.reason)
    except (AttributeError, IOError) as e:
      # Render the error template instead.
      self.error_message = e.message
      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.error_template)

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
        fd = aff4.FACTORY.Open(
            self.aff4_path, token=request.token, age=self.age)

        while True:
          data = fd.Read(1000000)
          if not data:
            break

          yield data

      filename = os.path.basename(utils.SmartStr(self.aff4_path))
      if not safe_extension:
        for ext in self.bad_extensions:
          if filename.lower().endswith(ext):
            filename += ".noexec"

      response = http.StreamingHttpResponse(
          streaming_content=Generator(), content_type="binary/octet-stream")
      # This must be a string.
      response["Content-Disposition"] = ("attachment; filename=%s" % filename)

      return response


class BufferReferenceRenderer(semantic.RDFProtoRenderer):
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


class StatModeRenderer(semantic.RDFValueRenderer):
  """Renders stat mode fields."""
  classname = "StatMode"

  layout_template = renderers.Template("""
<abbr title="Mode {{this.oct}}">{{this.mode_string|escape}}</abbr>""")

  def Layout(self, request, response):
    self.oct = oct(int(self.proxy))
    self.mode_string = unicode(self.proxy)
    return super(StatModeRenderer, self).Layout(request, response)


class StatEntryRenderer(semantic.RDFProtoRenderer):
  """Nicely format the StatEntry rdfvalue."""
  classname = "StatEntry"
  name = "Stat Entry"

  def TranslateRegistryData(self, request, registry_data):
    if registry_data.HasField("data"):
      ret = repr(registry_data.GetValue())
    else:
      ret = utils.SmartStr(registry_data.GetValue())

    # This is not escaped by the template!
    return renderers.EscapingRenderer(ret).RawHTML(request)

  translator = dict(registry_data=TranslateRegistryData)


class GrrMessageRenderer(semantic.RDFProtoRenderer):
  """Nicely format the GrrMessage rdfvalue."""
  classname = "GrrMessage"
  name = "GrrMessage"

  def RenderPayload(self, request, unused_value):
    rdf_object = self.proxy.payload
    return semantic.FindRendererForObject(rdf_object).RawHTML(request)

  translator = dict(args=RenderPayload)


class VolumeRenderer(semantic.RDFProtoRenderer):
  """Make the disk volume values human readable."""
  classname = "Volume"
  name = "Disk Volume"

  def Layout(self, request, response):
    """Render the protobuf as a table."""
    self.result = []
    for descriptor, value in self.proxy.ListSetFields():
      name = descriptor.name
      friendly_name = descriptor.friendly_name or name

      if name == "total_allocation_units" and value is not None:
        value_str = "{0} ({1:.2f} GB)".format(value,
                                              self.proxy.AUToGBytes(value))
        self.result.append((friendly_name, descriptor.description, value_str))

      elif name == "actual_available_allocation_units" and value is not None:
        value_str = "{0} ({1:.2f} GB, {2:.0f}% free)".format(
            value, self.proxy.AUToGBytes(value), self.proxy.FreeSpacePercent())
        self.result.append((friendly_name, descriptor.description, value_str))
      else:
        renderer = semantic.FindRendererForObject(value)

        self.result.append((friendly_name, descriptor.description,
                            renderer.RawHTML(request)))

    return super(semantic.RDFProtoRenderer, self).Layout(request, response)


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
          value = self.translator[name](self, request, value)

        # Regardless of what the error is, we need to escape the value.
        except StandardError:  # pylint: disable=broad-except
          value = self.FormatFromTemplate(
              self.translator_error_template, value=value)

        row.append(value)

      self.result.append(row)

    return renderers.TemplateRenderer.Layout(self, request, response)


class UsersRenderer(semantic.RDFValueArrayRenderer):
  classname = "Users"
  name = "Users"


class NetworkAddressRenderer(semantic.RDFValueRenderer):
  classname = "NetworkAddress"
  name = "Network Address"
  layout_template = renderers.Template("{{result|escape}}")

  def Layout(self, request, response):
    _ = request, response
    return self.RenderFromTemplate(
        self.layout_template,
        response,
        result=self.proxy.human_readable_address)


class InterfaceRenderer(semantic.RDFProtoRenderer):
  """Render a machine's interfaces."""
  classname = "Interface"
  name = "Interface Record"

  def TranslateIp4Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET, x) for x in value])

  def TranslateMacAddress(self, _, value):
    return value.human_readable_address

  def TranslateIp6Addresses(self, _, value):
    return " ".join([socket.inet_ntop(socket.AF_INET6, x) for x in value])

  translator = dict(
      ip4_addresses=TranslateIp4Addresses,
      ip6_addresses=TranslateIp6Addresses,
      mac_address=TranslateMacAddress)


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


class ConnectionsRenderer(semantic.RDFValueArrayRenderer):
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

  connection_template = renderers.Template("""
<td>{{type|escape}}</td>
<td>{{local_address|escape}}</td>
<td>{{remote_address|escape}}</td>
<td>{{state|escape}}</td>
<td>{{pid|escape}}</td>
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

  def Layout(self, request, response):
    """Render the connection as a table."""
    _ = request

    result = []

    for conn in self.proxy:
      try:
        conn_type = self.types[(conn.family, conn.type)]
      except KeyError:
        conn_type = "(%d,%d)" % (conn.family, conn.type)
      local_address = "%s:%d" % (conn.local_address.ip, conn.local_address.port)
      if conn.remote_address.ip:
        remote_address = "%s:%d" % (conn.remote_address.ip,
                                    conn.remote_address.port)
      else:
        if ":" in conn.local_address.ip:
          remote_address = ":::*"
        else:
          remote_address = "0.0.0.0:*"

      result.append(
          self.FormatFromTemplate(
              self.connection_template,
              type=conn_type,
              local_address=local_address,
              remote_address=remote_address,
              state=utils.SmartStr(conn.state),
              pid=conn.pid))

    return self.RenderFromTemplate(
        self.layout_template, response, result=sorted(result))


class NetworkConnections(ConnectionsRenderer):
  """Handle repeated NetworkConnection fields in protobufs."""
  classname = "NetworkConnection"


class ProcessRenderer(semantic.RDFValueArrayRenderer):
  """Renders process listings."""
  classname = "Processes"
  name = "Process Listing"

  def RenderFiles(self, request, file_list):
    return StringListRenderer(sorted(file_list)).RawHTML(request)

  translator = dict(open_files=RenderFiles)


class FilesystemRenderer(semantic.RDFValueArrayRenderer):
  classname = "FileSystem"
  name = "FileSystems"


class CertificateRenderer(semantic.RDFValueRenderer):
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
""")

  def Layout(self, request, response):
    # Present the certificate as text.
    # TODO(user): cryptography does not export x509 printing currently. We
    # show the PEM instead.
    self.cert = str(self.proxy)

    response = super(CertificateRenderer, self).RenderAjax(request, response)
    return self.CallJavascript(response, "CertificateRenderer.Layout")


class BlobArrayRenderer(semantic.RDFValueRenderer):
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

    return self.RenderFromTemplate(
        self.layout_template, response, first=array[0:1], array=array[1:])


class AgeSelector(semantic.RDFValueRenderer):
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

  layout_template = (renderers.TableRenderer.layout_template + """
<div id="version_selector_dialog_{{unique|escape}}"
  class="version-selector-dialog modal wide-modal high-modal"></div>
""")

  toolbar = None  # Toolbar class to render above table.
  content_cache = None
  post_parameters = ["aff4_path"]
  root_path = "/"  # Paths will all be under this path.

  # This can restrict the view to only certain types of objects. It should be a
  # list of types to show.
  visible_types = None

  def __init__(self, **kwargs):
    super(AbstractFileTable, self).__init__(**kwargs)

    if AbstractFileTable.content_cache is None:
      AbstractFileTable.content_cache = utils.TimeBasedCache()

  def RenderAjax(self, request, response):
    response = super(AbstractFileTable, self).RenderAjax(request, response)
    return self.CallJavascript(response, "AbstractFileTable.RenderAjax")

  def Layout(self, request, response):
    """Populate the table state with the request."""
    # Draw the toolbar first
    if self.toolbar:
      tb_cls = renderers.Renderer.classes[self.toolbar]
      tb_cls().Layout(request, response)

    response = super(AbstractFileTable, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "AbstractFileTable.Layout",
        renderer=self.__class__.__name__,
        client_id=self.state.get("client_id", ""))

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
      directory_node = aff4.FACTORY.Open(
          urn, token=request.token).Upgrade(aff4_standard.VFSDirectory)
      if not directory_node:
        raise IOError()

      key += str(directory_node.Get(directory_node.Schema.LAST))
      key += ":" + str(request.token)
      try:
        children = self.content_cache.Get(key)
      except KeyError:
        # Only show the direct children.
        children = sorted(
            directory_node.Query(
                filter_string=filter_string, limit=100000))

        # Filter the children according to types.
        if self.visible_types:
          children = [
              x for x in children if x.__class__.__name__ in self.visible_types
          ]

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
        if isinstance(column, semantic.AttributeColumn):
          column.AddRowFromFd(row_index, fd)

      if "Container" in fd.behaviours:
        self.AddCell(
            row_index, "Icon", dict(
                icon="directory", description="Directory"))
      else:
        self.AddCell(
            row_index,
            "Icon",
            dict(
                icon="file", description="File Like Object"))

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

  root_path = None  # The root will be dynamically set to the client path.
  toolbar = "Toolbar"
  context_help_url = "user_manual.html#_listing_the_virtual_filesystem"

  def __init__(self, **kwargs):
    super(FileTable, self).__init__(**kwargs)

    self.AddColumn(
        semantic.RDFValueColumn(
            "Icon", renderer=semantic.IconRenderer, width="40px"))
    self.AddColumn(
        semantic.RDFValueColumn(
            "Name",
            renderer=semantic.SubjectRenderer,
            sortable=True,
            width="20%"))
    self.AddColumn(semantic.AttributeColumn("type", width="10%"))
    self.AddColumn(semantic.AttributeColumn("size", width="10%"))
    self.AddColumn(semantic.AttributeColumn("stat.st_size", width="15%"))
    self.AddColumn(semantic.AttributeColumn("stat.st_mtime", width="15%"))
    self.AddColumn(semantic.AttributeColumn("stat.st_ctime", width="15%"))
    self.AddColumn(
        semantic.RDFValueColumn(
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

  # Flows are special children which confuse users when seen, so we remove them
  # from the tree. Note that they are still visible in the table.
  hidden_branches = ["/flows"]

  def Layout(self, request, response):
    self.state["client_id"] = client_id = request.REQ.get("client_id")
    self.state["aff4_root"] = request.REQ.get("aff4_root", client_id)

    response = super(FileSystemTree, self).Layout(request, response)
    return self.CallJavascript(response, "FileSystemTree.Layout")

  def RenderBranch(self, path, request):
    """Renders tree leafs for filesystem path."""
    client_id = request.REQ["client_id"]
    aff4_root = rdfvalue.RDFURN(request.REQ.get("aff4_root", client_id))

    # Path is relative to the aff4 root specified.
    urn = aff4_root.Add(path)
    try:
      # Open the client
      directory = aff4.FACTORY.Open(
          urn, token=request.token).Upgrade(aff4_standard.VFSDirectory)

      children = [
          ch for ch in directory.OpenChildren(limit=100000)
          if "Container" in ch.behaviours
      ]

      try:
        self.message = "Directory %s Last retrieved %s" % (
            urn, directory.Get(directory.Schema.TYPE).age)
      except AttributeError:
        pass

      for child in sorted(children):
        self.AddElement(child.urn.RelativeName(urn))

    except IOError as e:
      self.message = "Error fetching %s: %s" % (urn, e)


class UploadView(renderers.TemplateRenderer):
  """Renders an upload page."""

  post_parameters = ["tree_path"]
  upload_handler = "UploadHandler"

  layout_template = renderers.Template("""
{% if grr.state.tree_path %}
<h3>Upload to {{ grr.state.tree_path|escape }}</h3>
{% endif %}
<form id="{{unique|escape}}_form" enctype="multipart/form-data">
<input class="btn btn-default btn-file" id="{{ unique|escape }}_file"
  type="file" name="uploadFile" />
</form>
<button class="btn btn-default" id="{{ unique|escape }}_upload_button">
  Upload
</button>
<br/><br/>
<div id="{{ unique|escape }}_upload_results"/>
<div id="{{ unique|escape }}_upload_progress"/>
""")

  def Layout(self, request, response):
    response = super(UploadView, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "UploadView.Layout",
        upload_handler=self.upload_handler,
        upload_state=self.state)


class UploadHandler(renderers.TemplateRenderer):
  """Handles an uploaded file."""

  # We allow a longer execution time here to be able to upload large files.
  max_execution_time = 60 * 2

  storage_path = "aff4:/config"

  error_template = renderers.Template("""
Error: {{this.error|escape}}.
""")
  success_template = renderers.Template("""
Success: File uploaded to {{this.dest_path|escape}}.
""")

  def RenderAjax(self, request, response):
    """Store the file on the server."""
    super(UploadHandler, self).RenderAjax(request, response)

    try:
      self.uploaded_file = request.FILES.items()[0][1]
      self.dest_path, aff4_type = self.GetFilePath(request)
      self.ValidateFile()

      dest_file = aff4.FACTORY.Create(
          self.dest_path, aff4_type=aff4_type, token=request.token)
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
    return path, aff4_grr.VFSFile

  def ValidateFile(self):
    """Check if a file matches what we expected to be uploaded.

    Raises:
      IOError: On validation failure.
    """
    if self.uploaded_file.size < 100:
      raise IOError("File is too small.")
