#!/usr/bin/env python
"""This plugin adds artifact functionality to the UI."""

import itertools
import StringIO

from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import forms
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import artifact
from grr.lib import artifact_lib
from grr.lib import parsers
from grr.lib import rdfvalue


class ArtifactListRenderer(forms.MultiSelectListRenderer):
  """Renderer for listing the available Artifacts."""

  type = rdfvalue.ArtifactName

  artifact_template = ("""
          <div id='{{unique|escape}}_artifact_description'>
            <h4><div name='artifact_name'/></h4>
            <div name='artifact_description'/>
            <table>
              <tr><td>Labels<td><div name='artifact_labels'/></tr>
              <tr><td>Platforms<td><div name='artifact_supported_os'/></tr>
              <tr><td>Conditions<td><div name='artifact_conditions'/></tr>
              <tr><td>Dependencies<td><div name='artifact_dependencies'/></tr>
              <tr><td>Links<td><div name='artifact_links'/></tr>
              <tr><td>Output Type<td><div name='artifact_output_type'/></tr>
            </table>
            <h5>Artifact Collectors</h5>
            <table name='artifact_collectors'>
              <tbody></tbody>
            </table>
            <h5>Artifact Processors</h5>
            <table name='artifact_processors'>
              <tbody></tbody>
            </table>
          </div>""")

  layout_template = (
      """<div class="control-group">"""
      + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div id='{{unique|escape}}_artifact_renderer' class="controls">
  <div>
    <table class='artifact_table'>
      <tr>
        <td>
          <input id='{{unique|escape}}_search'
            placeholder="Search"></input><br>
          <select id='{{unique|escape}}_os_filter'
            placeholder="OS Filter"></input>
        <td>
        <td>
      </tr>
      <tr>
        <td class="artifact_table">
          <select id='{{unique|escape}}_artifact_list' class='artifact_list'
            multiple />
        <td class="artifact_table">
          <select id='{{this.prefix|escape}}' class='artifact_list' multiple/>
        <td class="artifact_table">"""
      + artifact_template + """
      </tr>
      <tr>
        <td>
          <a id='{{unique|escape}}_artifact_add'>Add</a>
          <a id='{{unique|escape}}_artifact_add_all'
            class='pull-right'>Add all  </a>
        <td>
          <a id='{{unique|escape}}_select_clear'>Clear</a>
          <a id='{{unique|escape}}_select_remove'
            class='pull-right'>Remove  </a>
        <td>
      </tr>
    </table>
  </div>
  </div>

</div>
""")

  def Layout(self, request, response):
    """Get available artifact information for display."""
    # Get all artifacts that aren't Bootstrap and aren't the base class.
    self.artifacts = {}
    artifact.LoadArtifactsFromDatastore(token=request.token)
    for name, artifact_val in artifact_lib.ArtifactRegistry.artifacts.items():
      if set(["Bootstrap"]).isdisjoint(artifact_val.labels):
        self.artifacts[name] = artifact_val
    self.labels = artifact_lib.ARTIFACT_LABELS

    # Convert artifacts into a dict usable from javascript.
    artifact_dict = {}
    for artifact_name, artifact_val in self.artifacts.items():
      artifact_dict[artifact_name] = artifact_val.ToExtendedDict()
      processors = []
      for processor in parsers.Parser.GetClassesByArtifact(artifact_name):
        processors.append({"name": processor.__name__,
                           "output_types": processor.output_types,
                           "doc": processor.GetDescription()})
      artifact_dict[artifact_name]["processors"] = processors

    # Skip the our parent and call the TypeDescriptorFormRenderer direct.
    response = renderers.TypeDescriptorFormRenderer.Layout(self, request,
                                                           response)
    return self.CallJavascript(response, "ArtifactListRenderer.Layout",
                               prefix=self.prefix,
                               artifacts=artifact_dict,
                               supported_os=artifact_lib.SUPPORTED_OS_LIST,
                               labels=self.labels)


class ArtifactRDFValueRenderer(semantic.RDFValueRenderer):
  """A special renderer for ArtifactRDFValues."""

  classname = "Artifact"

  layout_template = renderers.Template(
      """
<div id={{unique|escape}}_artifact_description>"""
      + ArtifactListRenderer.artifact_template + """
</div>
""")

  def Layout(self, request, response):
    self.artifact_str = self.proxy.ToPrettyJson()
    response = super(ArtifactRDFValueRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "ArtifactRDFValueRenderer.Layout",
                               artifact_str=self.artifact_str)


class ArtifactRawRDFValueRenderer(semantic.RDFValueRenderer):
  """A renderer for showing JSON format for ArtifactRDFValues."""

  classname = "Artifact"

  layout_template = renderers.Template(
      "<pre>{{this.artifact_str|escape}}</pre>")

  def Layout(self, request, response):
    self.artifact_str = self.proxy.ToPrettyJson(extended=True)
    super(ArtifactRawRDFValueRenderer, self).Layout(request, response)


class ArtifactManagerView(renderers.TableRenderer):
  """Artifact Manager table with toolbar."""

  description = "Artifact Manager"
  behaviours = frozenset(["Configuration"])
  order = 50

  toolbar = "ArtifactManagerToolbar"

  def __init__(self, **kwargs):
    super(ArtifactManagerView, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Artifact Name", width="5%"))
    self.AddColumn(semantic.RDFValueColumn(
        "Artifact Details", width="50%", renderer=ArtifactRDFValueRenderer))
    self.AddColumn(semantic.RDFValueColumn(
        "Artifact Raw", width="40%", renderer=ArtifactRawRDFValueRenderer))

  def BuildTable(self, start_row, end_row, request):
    """Builds table artifacts."""
    artifact_urn = rdfvalue.RDFURN("aff4:/artifact_store")
    try:
      collection = aff4.FACTORY.Open(artifact_urn,
                                     aff4_type="RDFValueCollection",
                                     token=request.token)
    except IOError:
      return

    self.size = len(collection)
    row_index = start_row
    for value in itertools.islice(collection, start_row, end_row):
      self.AddCell(row_index, "Artifact Name", value.name)
      self.AddCell(row_index, "Artifact Details", value)
      self.AddCell(row_index, "Artifact Raw", value)
      row_index += 1

  def Layout(self, request, response):
    """Populate the table state with the request."""
    if self.toolbar:
      tb_cls = renderers.Renderer.classes[self.toolbar]
      tb_cls().Layout(request, response)
    return super(ArtifactManagerView, self).Layout(request, response)


class ArtifactManagerToolbar(renderers.TemplateRenderer):
  """A navigation enhancing toolbar.

  Internal State:
    - aff4_path: The path we are viewing now in the table.
  """
  post_parameters = ["aff4_path"]
  event_queue = "file_select"

  layout_template = renderers.Template("""
<ul id="toolbar_{{unique|escape}}" class="breadcrumb">
  <li>
    <button id='{{unique|escape}}_upload' class="btn"
      title="Upload Artifacts as JSON or YAML"
      data-toggle="modal" data-target="#upload_dialog_{{unique|escape}}">
      <img src='/static/images/upload.png' class='toolbar_icon'>
    </button>
  </li>
  <li>
    <button id='{{unique|escape}}_deleteall' class="btn"
      title="Delete all uploaded artifacts" data-toggle="modal"
      data-target="#delete_confirm_dialog_{{unique|escape}}">
      <img src='/static/images/editdelete.png' class='toolbar_icon'>
    </button>
  </li>

</ul>

<div id="upload_dialog_{{unique|escape}}" class="modal hide" tabindex="-1"
  role="dialog" aria-hidden="true">
  <div class="modal-header">
    <button id="upload_artifact_btn_{{unique|escape}}" type="button"
    class="close" data-dismiss="modal" aria-hidden="true">
      x</button>
    <h3>Upload File</h3>
  </div>
  <div class="modal-body" id="upload_dialog_body_{{unique|escape}}"></div>
  <div class="modal-footer">
    <button id="upload_artifact_close_btn_{{unique|escape}}" class="btn"
    data-dismiss="modal" aria-hidden="true">Close</button>
  </div>
</div>

<div id="delete_confirm_dialog_{{unique|escape}}"
  class="modal hide" tabindex="-1" role="dialog" aria-hidden="true">
</div>

""")

  def Layout(self, request, response):
    response = super(ArtifactManagerToolbar, self).Layout(request, response)
    return self.CallJavascript(response, "ArtifactManagerToolbar.Layout")


class DeleteArtifactsConfirmationDialog(renderers.ConfirmationDialogRenderer):
  """Dialog that asks for confirmation to delete uploaded artifacts.

  Note that this only deletes artifacts that have been uploaded via the
  ArtifactManager.  Artifacts loaded from the artifacts directory are
  unaffected.
  """

  content_template = renderers.Template("""
<p>Are you sure you want to <strong>delete all</strong>
uploaded artifacts?</p>
""")

  ajax_template = renderers.Template("""
<p class="text-info">Uploaded artifacts were deleted successfully.</p>
""")

  def RenderAjax(self, request, response):
    aff4.FACTORY.Delete("aff4:/artifact_store", token=request.token)
    return self.RenderFromTemplate(self.ajax_template, response,
                                   unique=self.unique, this=self)


class ArtifactJsonUploadView(fileview.UploadView):
  """Renders a binary upload page."""
  post_parameters = []
  upload_handler = "ArtifactUploadHandler"
  storage_path = "aff4:/artifact_store"


class ArtifactUploadHandler(fileview.UploadHandler):
  """Handles upload of a binary config file such as a driver."""

  def RenderAjax(self, request, response):
    """Handle the upload via ajax."""
    try:
      self.uploaded_file = request.FILES.items()[0][1]
      content = StringIO.StringIO()
      for chunk in self.uploaded_file.chunks():
        content.write(chunk)
      self.dest_path = artifact.UploadArtifactYamlFile(
          content.getvalue(), token=request.token)

      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.success_template)
    except (IOError, artifact_lib.ArtifactDefinitionError) as e:
      self.error = "Could not write artifact to database %s" % e
    return renderers.TemplateRenderer.Layout(self, request, response,
                                             self.error_template)
