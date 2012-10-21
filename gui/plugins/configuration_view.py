#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""This is the interface for managing the GRR configuration."""


import StringIO

from google.protobuf import message
from grr.client import conf as flags

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import maintenance_utils
from grr.lib import registry
from grr.proto import jobs_pb2

FLAGS = flags.FLAGS


class ConfigManager(renderers.TemplateRenderer):
  """Show the configuration of the GRR system."""

  description = "Settings"
  behaviours = frozenset(["Configuration"])

  layout_template = renderers.Template("""
<h2>Configuration</h2>
<p>This is a read-only view of the frontend configuration.</p>
<table style="border-spacing: 10px 2px;">
{% for f in this.flags %}
  <tr><td>{{ f.name|escape }}</td>
      <td>{{ f.type|escape }}</td>
      <td>{{ f.value|escape }}</td>
{% empty %}
  <tr><td>Could not retrieve configuration.</td></tr>
{% endfor %}
<table>
""")

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    self.flags = sorted(flags.PARSER.FlagDict().values())

    return super(ConfigManager, self).Layout(request, response)


class BinaryConfigurationView(renderers.Splitter2WayVertical):
  """This is the main view to browse files."""
  behaviours = frozenset(["Configuration"])
  description = "Manage Binaries"

  AUTHORIZED_LABELS = ["admin"]

  left_renderer = "ConfigurationTree"
  right_renderer = "ConfigFileTable"


class ConfigurationTree(renderers.TreeRenderer):
  """A FileSystem navigation Tree based at /config.

  Generated Javascript Events:
    - tree_select(aff4_path) - aff4 path for the branch the user
      selected.

  Internal State:
    - aff4_root: The aff4 node which forms the root of this tree.
  """

  publish_select_queue = "tree_select"
  root_path = "/config"

  def Layout(self, request, response):
    self.state["aff4_root"] = request.REQ.get("aff4_root", self.root_path)

    return super(ConfigurationTree, self).Layout(request, response)

  def RenderBranch(self, path, request):
    """Renders tree leafs for filesystem path."""
    aff4_root = aff4.RDFURN(request.REQ.get("aff4_root", self.root_path))
    urn = aff4_root.Add(path)
    try:
      directory = aff4.FACTORY.Create(urn, "VFSDirectory", mode="r",
                                      token=request.token)
      children = [ch for ch in directory.OpenChildren(limit=100000)
                  if "Container" in ch.behaviours]
      for child in children:
        self.AddElement(child.urn.RelativeName(urn))

    except IOError as e:
      self.message = "Error fetching %s: %s" % (urn, e)


class ConfigFileTable(fileview.AbstractFileTable):
  """A table that displays the content of a directory. Customized for binaries.

  Listening Javascript Events:
    - tree_select(aff4_path) - A selection event on the tree informing us of the
      tree path.  We re-layout the entire table on this event to show the
      directory listing of aff4_path.

  Generated Javascript Events:
    - file_select(aff4_path, age) - The full AFF4 path for the file in the
      directory which is selected. Age is the latest age we wish to see.
  """
  root_path = "/config"
  toolbar = "ConfigFileTableToolbar"

  def __init__(self):
    super(ConfigFileTable, self).__init__()

    self.AddColumn(renderers.RDFValueColumn(
        "Icon", renderer=renderers.IconRenderer, width=0))
    self.AddColumn(renderers.RDFValueColumn(
        "Name", renderer=renderers.SubjectRenderer, sortable=True))
    self.AddColumn(renderers.AttributeColumn("type"))
    self.AddColumn(ConfigDescriptionColumn())
    self.AddColumn(renderers.RDFValueColumn(
        "Age", renderer=fileview.AgeSelector))


class ConfigDescriptionColumn(renderers.AttributeColumn):
  """An AttributeColumn for Details which is different depending on type."""

  def __init__(self, **kwargs):
    # The below is a set of attributes, we'll try each of them until one works
    # for the details column.
    self.attrs = [aff4.Attribute.GetAttributeByName("installation"),
                  aff4.Attribute.GetAttributeByName("size")]
    renderers.RDFValueColumn.__init__(self, name="Details", **kwargs)

  def AddRowFromFd(self, index, fd):
    """Add a new value from the fd customizing for the type."""
    for attr in self.attrs:
      if fd.IsAttributeSet(attr):
        val = fd.Get(attr)
        if val:
          self.rows[index] = val
          break


class ConfigFileTableToolbar(renderers.TemplateRenderer):
  """A navigation enhancing toolbar.

  Internal State:
    - aff4_path: The path we are viewing now in the table.
  """
  post_parameters = ["aff4_path"]
  event_queue = "file_select"

  layout_template = renderers.Template("""
<div id='toolbar_{{unique|escape}}'' class='toolbar'>
  <button id='{{unique|escape}}_upload' title='Upload Binary'>
    <img src='/static/images/upload.png' class='toolbar_icon'>
  </button>
  <button id='{{unique|escape}}_download' title='Download Binary'>
    <img src='/static/images/download.png' class='toolbar_icon'>
  </button>
  <div id='{{unique|escape}}_upload_dialog'/>
</div>

<script>
grr.subscribe('file_select', function(aff4_path, age) {
  var state = {aff4_path: aff4_path};
  grr.downloadHandler($('#{{unique|escapejs}}_download'), state);
}, 'toolbar_{{unique|escapejs}}');

grr.dialog('ConfigBinaryUploadView', '{{unique|escapejs}}_upload_dialog',
           '{{unique|escapejs}}_upload',
           { width: '600px', height: 'auto', title: 'Upload file'});

</script>
""")


class ConfigBinaryUploadView(fileview.UploadView):
  """Renders a binary upload page."""

  post_parameters = []
  upload_handler = "ConfigBinaryUploadHandler"


class ConfigBinaryUploadHandler(fileview.UploadHandler):
  """Handles upload of a binary config file such as a driver."""

  storage_path = "aff4:/config"

  def RenderAjax(self, request, response):
    """Handle the upload via ajax."""
    try:
      self.uploaded_file = request.FILES.items()[0][1]
      self.dest_path, aff4_type = self.GetFilePath(request)

      content = StringIO.StringIO()
      for chunk in self.uploaded_file.chunks():
        content.write(chunk)
      blob_pb = jobs_pb2.SignedBlob.FromString(content.getvalue())

      if aff4_type == "GRRMemoryDriver":
        # TODO(user): Add support for driver parameters.
        self.dest_path = maintenance_utils.UploadSignedDriverBlob(
            blob_pb, aff4_path=self.dest_path, token=request.token)
      else:
        self.dest_path = maintenance_utils.UploadSignedConfigBlob(
            blob_pb, aff4_path=self.dest_path, token=request.token)

      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.success_template)
    except (IOError) as e:
      self.error = "Could not write file to database %s" % e
    except (IndexError) as e:
      self.error = "No file provided."
    except message.DecodeError as e:
      self.error = ("Could not decode driver. This should be a signed protobuf"
                    " generated with sign_blob")
    return renderers.TemplateRenderer.Layout(self, request, response,
                                             self.error_template)

  def GetFilePath(self, request):
    aff4_path = request.REQ.get("tree_path")
    if not aff4_path:
      raise IOError("No tree_path specified")

    aff4_path = aff4.RDFURN(aff4_path).Add(self.uploaded_file.name)
    bin_type = maintenance_utils.GetConfigBinaryPathType(aff4_path)
    if not bin_type:
      raise IOError("Cannot upload to this path")
    else:
      return (aff4_path, bin_type)


class ConfigurationViewInitHook(registry.InitHook):
  """Init hook run on load of UI to initialize config directories."""

  pre = ["AFF4InitHook"]

  def Run(self):
    """Create the necessary directories."""
    maintenance_utils.CreateBinaryConfigPaths()
